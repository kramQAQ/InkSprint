import socket
import threading
import struct
import json
import sys
import os
import base64
import time
import random
from datetime import date, timedelta, datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security import SecurityManager
from database import db_manager, User, DailyReport, DetailRecord
from email_utils import EmailManager

HOST = '0.0.0.0'
PORT = 23456
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")

if not os.path.exists(AVATAR_DIR):
    os.makedirs(AVATAR_DIR)

verification_codes = {}


class ClientHandler(threading.Thread):
    def __init__(self, conn, addr, server_private_key, server_public_key_bytes):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.server_private_key = server_private_key
        self.server_public_key_bytes = server_public_key_bytes
        self.aes_key = None
        self.running = True
        self.user_id = None

    def send_packet(self, plain_text_dict):
        if not self.aes_key: return
        try:
            json_str = json.dumps(plain_text_dict)
            encrypted_bytes = SecurityManager.encrypt_aes(self.aes_key, json_str)
            header = struct.pack('>I', len(encrypted_bytes))
            self.conn.sendall(header + encrypted_bytes)
        except Exception as e:
            print(f"[Send Error] {e}")

    def receive_exact_bytes(self, num_bytes):
        data = b''
        while len(data) < num_bytes:
            try:
                packet = self.conn.recv(num_bytes - len(data))
                if not packet: return None
                data += packet
            except:
                return None
        return data

    def perform_handshake(self):
        try:
            print(f"[Handshake] Client {self.addr} connected.")
            pub_len = struct.pack('>I', len(self.server_public_key_bytes))
            self.conn.sendall(pub_len + self.server_public_key_bytes)
            len_bytes = self.receive_exact_bytes(4)
            if not len_bytes: return False
            msg_len = struct.unpack('>I', len_bytes)[0]
            encrypted_aes_key = self.receive_exact_bytes(msg_len)
            self.aes_key = SecurityManager.decrypt_with_rsa(self.server_private_key, encrypted_aes_key)
            return True
        except Exception as e:
            print(f"[Handshake] Error: {e}")
            return False

    def handle_login(self, request):
        username = request.get('username')
        password_hash = request.get('password')
        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return {"type": "login_response", "status": "fail", "msg": "用户不存在"}

            if user.password_hash == password_hash:
                self.user_id = user.id

                # 1. 获取头像
                avatar_data = ""
                if user.avatar_url and user.avatar_url != "default.jpg":
                    path = os.path.join(AVATAR_DIR, user.avatar_url)
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            avatar_data = base64.b64encode(f.read()).decode('utf-8')

                # 2. 【新增】获取今日已写字数
                today = date.today()
                daily_report = session.query(DailyReport).filter_by(user_id=user.id, report_date=today).first()
                today_total = daily_report.total_words if daily_report else 0

                return {
                    "type": "login_response",
                    "status": "success",
                    "nickname": user.nickname or user.username,
                    "username": user.username,
                    "email": user.email or "",
                    "avatar_data": avatar_data,
                    "today_total": today_total  # 返回今日数据
                }
            else:
                return {"type": "login_response", "status": "fail", "msg": "密码错误"}
        except Exception as e:
            print(f"[Login Error] {e}")
            return {"type": "login_response", "status": "error", "msg": "系统错误"}
        finally:
            session.close()

    def handle_register(self, request):
        username = request.get('username')
        password_hash = request.get('password')
        email = request.get('email', '')

        session = db_manager.get_session()
        try:
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                return {"type": "register_response", "status": "fail", "msg": "用户名已存在"}

            new_user = User(username=username, password_hash=password_hash, nickname=username,
                            email=email if email else None)
            session.add(new_user)
            session.commit()
            return {"type": "register_response", "status": "success", "msg": "注册成功，请登录"}
        except Exception as e:
            return {"type": "register_response", "status": "error", "msg": str(e)}
        finally:
            session.close()

    def handle_sync_data(self, request):
        """【新增】处理客户端数据同步请求"""
        if not self.user_id: return None
        increment = request.get('increment', 0)
        duration = request.get('duration', 0)

        # 如果没有增量且时长很短，忽略
        if increment <= 0 and duration <= 0:
            return None

        session = db_manager.get_session()
        try:
            # 1. 插入明细记录
            new_record = DetailRecord(
                user_id=self.user_id,
                word_increment=increment,
                duration_seconds=duration,
                source_type="client_sync",  # 标记为客户端同步
                source_path="Session Data",
                end_time=datetime.now()
            )
            session.add(new_record)

            # 2. 更新或创建当日报表
            today = date.today()
            daily = session.query(DailyReport).filter_by(user_id=self.user_id, report_date=today).first()
            if not daily:
                daily = DailyReport(user_id=self.user_id, report_date=today, total_words=0)
                session.add(daily)

            daily.total_words += increment
            session.commit()

            print(f"[Sync] User {self.user_id}: +{increment} words, {duration}s")
            return {"type": "response", "status": "ok", "msg": "Synced"}
        except Exception as e:
            print(f"[Sync Error] {e}")
            return {"type": "response", "status": "error", "msg": str(e)}
        finally:
            session.close()

    def handle_get_analytics(self, request):
        """【新增】获取热力图数据"""
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            # 获取过去一年的日报表
            one_year_ago = date.today() - timedelta(days=365)
            reports = session.query(DailyReport).filter(
                DailyReport.user_id == self.user_id,
                DailyReport.report_date >= one_year_ago
            ).all()

            # 转换为 { "2023-10-01": 500, ... } 格式
            heatmap = {str(r.report_date): r.total_words for r in reports}
            return {"type": "analytics_data", "heatmap": heatmap}
        finally:
            session.close()

    def handle_get_details(self, request):
        """【新增】获取最近明细记录"""
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            # 获取最近 20 条记录
            records = session.query(DetailRecord).filter_by(user_id=self.user_id) \
                .order_by(DetailRecord.end_time.desc()) \
                .limit(20).all()

            data = []
            for r in records:
                data.append({
                    "time": r.end_time.strftime("%Y-%m-%d %H:%M"),
                    "increment": r.word_increment,
                    "duration": r.duration_seconds
                })
            return {"type": "details_data", "data": data}
        finally:
            session.close()

    def handle_send_reset_code(self, request):
        username = request.get('username')
        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user or not user.email:
                return {"type": "code_response", "status": "fail", "msg": "用户不存在或未绑定邮箱"}

            code = str(random.randint(100000, 999999))
            verification_codes[username] = {'code': code, 'time': time.time()}

            if EmailManager.send_verification_code(user.email, code):
                return {"type": "code_response", "status": "success", "msg": "已发送"}
            else:
                return {"type": "code_response", "status": "fail", "msg": "发送失败"}
        finally:
            session.close()

    def handle_reset_password(self, request):
        username = request.get('username')
        code = request.get('code')
        new_pw = request.get('new_password')

        record = verification_codes.get(username)
        if not record or time.time() - record['time'] > 600 or record['code'] != code:
            return {"type": "reset_response", "status": "fail", "msg": "验证码无效或已过期"}

        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user:
                user.password_hash = new_pw
                session.commit()
                del verification_codes[username]
                return {"type": "reset_response", "status": "success", "msg": "重置成功"}
            return {"type": "reset_response", "status": "fail", "msg": "用户错误"}
        finally:
            session.close()

    def handle_update_profile(self, request):
        if not self.user_id: return None
        new_nick = request.get('nickname')
        new_email = request.get('email')
        avatar_b64 = request.get('avatar_data')

        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=self.user_id).first()
            if user:
                if new_nick: user.nickname = new_nick
                if new_email is not None: user.email = new_email.strip() or None
                if avatar_b64:
                    fname = f"user_{self.user_id}.png"
                    path = os.path.join(AVATAR_DIR, fname)
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(avatar_b64))
                    user.avatar_url = fname
                session.commit()
                return {"type": "profile_updated", "status": "success"}
            return {"type": "response", "status": "error"}
        finally:
            session.close()

    def run(self):
        if not self.perform_handshake():
            self.conn.close()
            return

        while self.running:
            try:
                header = self.receive_exact_bytes(4)
                if not header: break
                body_len = struct.unpack('>I', header)[0]
                body_bytes = self.receive_exact_bytes(body_len)
                if not body_bytes: break

                plain_json = SecurityManager.decrypt_aes(self.aes_key, body_bytes)
                request = json.loads(plain_json)
                print(f"[Recv] {request.get('type')}")

                response = None
                rtype = request.get('type')

                # 路由分发
                if rtype == 'login':
                    response = self.handle_login(request)
                elif rtype == 'register':
                    response = self.handle_register(request)
                elif rtype == 'sync_data':
                    response = self.handle_sync_data(request)
                elif rtype == 'get_analytics':
                    response = self.handle_get_analytics(request)
                elif rtype == 'get_details':
                    response = self.handle_get_details(request)
                elif rtype == 'send_code':
                    response = self.handle_send_reset_code(request)
                elif rtype == 'reset_password':
                    response = self.handle_reset_password(request)
                elif rtype == 'update_profile':
                    response = self.handle_update_profile(request)
                else:
                    response = {"type": "response", "status": "ok", "msg": "Ack"}

                if response:
                    self.send_packet(response)

            except Exception as e:
                print(f"[Conn Error] {e}")
                break

        self.conn.close()


class InkServer:
    def __init__(self):
        self.private_key, self.public_key = SecurityManager.generate_rsa_keys()
        self.public_key_bytes = SecurityManager.public_key_to_bytes(self.public_key)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        try:
            self.socket.bind((HOST, PORT))
            self.socket.listen(10)
            print(f"[Server] Running on {HOST}:{PORT}")
            while True:
                conn, addr = self.socket.accept()
                ClientHandler(conn, addr, self.private_key, self.public_key_bytes).start()
        except Exception as e:
            print(f"[Server Crash] {e}")
        finally:
            self.socket.close()


if __name__ == '__main__':
    print("[Startup] Checking database...")
    try:
        db_manager.init_db()
        print("[Startup] Database ready.")
    except Exception as e:
        print(f"[Startup] Database init failed: {e}")

    server = InkServer()
    server.start()