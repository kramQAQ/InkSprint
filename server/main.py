import socket
import threading
import struct
import json
import sys
import os
import base64
import time
import random
from datetime import date, datetime, timedelta
from sqlalchemy import func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security import SecurityManager
# [修复] 移除了 UserSource 导入，解决了 ImportError
from database import db_manager, User, DailyReport, DetailRecord
from email_utils import EmailManager

HOST = '0.0.0.0'
PORT = 23456
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")

if not os.path.exists(AVATAR_DIR):
    os.makedirs(AVATAR_DIR)

# 内存中临时存储验证码: {username: {'code': '123456', 'time': timestamp}}
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
            packet = self.conn.recv(num_bytes - len(data))
            if not packet: return None
            data += packet
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
            print(f"[Handshake] Success with {self.addr}")
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

                # [修改] 移除了头像数据的读取和返回
                # 仅获取今日统计数据
                today = date.today()
                daily_rep = session.query(DailyReport).filter_by(user_id=user.id, report_date=today).first()
                today_total = daily_rep.total_words if daily_rep else 0

                return {
                    "type": "login_response",
                    "status": "success",
                    "nickname": user.nickname or user.username,
                    "username": user.username,
                    "email": user.email or "",
                    "today_total": today_total
                    # "avatar_data": ... 已移除
                }
            else:
                return {"type": "login_response", "status": "fail", "msg": "密码错误"}
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

            new_user = User(
                username=username,
                password_hash=password_hash,
                nickname=username,
                email=email if email else None
            )
            session.add(new_user)
            session.commit()
            return {"type": "register_response", "status": "success", "msg": "注册成功，请登录"}
        except Exception as e:
            return {"type": "register_response", "status": "error", "msg": str(e)}
        finally:
            session.close()

    def handle_send_reset_code(self, request):
        username = request.get('username')
        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return {"type": "code_response", "status": "fail", "msg": "用户不存在"}

            if not user.email:
                return {"type": "code_response", "status": "fail", "msg": "该账号未绑定邮箱，无法找回密码"}

            code = str(random.randint(100000, 999999))
            verification_codes[username] = {
                'code': code,
                'time': time.time()
            }

            if EmailManager.send_verification_code(user.email, code):
                return {"type": "code_response", "status": "success", "msg": f"验证码已发送至 {user.email}"}
            else:
                return {"type": "code_response", "status": "fail", "msg": "邮件发送失败，请稍后重试"}
        finally:
            session.close()

    def handle_reset_password(self, request):
        username = request.get('username')
        code = request.get('code')
        new_password_hash = request.get('new_password')

        record = verification_codes.get(username)
        if not record:
            return {"type": "reset_response", "status": "fail", "msg": "请先获取验证码"}

        if time.time() - record['time'] > 600:
            return {"type": "reset_response", "status": "fail", "msg": "验证码已过期"}

        if record['code'] != code:
            return {"type": "reset_response", "status": "fail", "msg": "验证码错误"}

        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user:
                user.password_hash = new_password_hash
                session.commit()
                del verification_codes[username]
                return {"type": "reset_response", "status": "success", "msg": "密码重置成功"}
            else:
                return {"type": "reset_response", "status": "fail", "msg": "用户异常"}
        finally:
            session.close()

    def handle_update_profile(self, request):
        if not self.user_id:
            return {"type": "response", "status": "error", "msg": "未登录"}

        new_nickname = request.get('nickname')
        new_email = request.get('email')
        avatar_b64 = request.get('avatar_data')

        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=self.user_id).first()
            if user:
                if new_nickname: user.nickname = new_nickname
                if new_email is not None: user.email = new_email if new_email.strip() else None

                if avatar_b64:
                    file_name = f"user_{self.user_id}.png"
                    file_path = os.path.join(AVATAR_DIR, file_name)
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(avatar_b64))
                    user.avatar_url = file_name

                session.commit()
                return {"type": "profile_updated", "status": "success"}
            return {"type": "response", "status": "error", "msg": "用户不存在"}
        except Exception as e:
            return {"type": "response", "status": "error", "msg": str(e)}
        finally:
            session.close()

    def handle_sync_data(self, request):
        if not self.user_id: return

        increment = request.get('increment', 0)
        duration = request.get('duration', 0)

        if increment <= 0 and duration <= 0: return

        session = db_manager.get_session()
        try:
            today = date.today()
            daily = session.query(DailyReport).filter_by(user_id=self.user_id, report_date=today).first()
            if not daily:
                daily = DailyReport(user_id=self.user_id, report_date=today, total_words=0)
                session.add(daily)

            daily.total_words += increment

            detail = DetailRecord(
                user_id=self.user_id,
                word_increment=increment,
                duration_seconds=duration,
                start_time=datetime.now() - timedelta(seconds=duration),
                end_time=datetime.now()
            )
            session.add(detail)
            session.commit()
            return {"type": "sync_response", "status": "success"}
        except Exception as e:
            print(f"Sync error: {e}")
            return {"type": "sync_response", "status": "error"}
        finally:
            session.close()

    def handle_get_analytics(self, request):
        if not self.user_id: return
        session = db_manager.get_session()
        try:
            one_year_ago = date.today() - timedelta(days=365)
            daily_records = session.query(DailyReport).filter(
                DailyReport.user_id == self.user_id,
                DailyReport.report_date >= one_year_ago
            ).all()

            heatmap_data = {str(r.report_date): r.total_words for r in daily_records}

            return {
                "type": "analytics_data",
                "heatmap": heatmap_data,
                "status": "success"
            }
        finally:
            session.close()

    def handle_get_details(self, request):
        if not self.user_id: return
        session = db_manager.get_session()
        try:
            three_days_ago = datetime.now() - timedelta(days=3)
            records = session.query(DetailRecord).filter(
                DetailRecord.user_id == self.user_id,
                DetailRecord.start_time >= three_days_ago
            ).order_by(DetailRecord.start_time.desc()).all()

            details = []
            for r in records:
                details.append({
                    "time": r.start_time.strftime("%Y-%m-%d %H:%M"),
                    "increment": r.word_increment,
                    "duration": r.duration_seconds
                })
            return {
                "type": "details_data",
                "data": details,
                "status": "success"
            }
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

                if rtype == 'login':
                    response = self.handle_login(request)
                elif rtype == 'register':
                    response = self.handle_register(request)
                elif rtype == 'send_code':
                    response = self.handle_send_reset_code(request)
                elif rtype == 'reset_password':
                    response = self.handle_reset_password(request)
                elif rtype == 'update_profile':
                    response = self.handle_update_profile(request)
                elif rtype == 'sync_data':
                    response = self.handle_sync_data(request)
                elif rtype == 'get_analytics':
                    response = self.handle_get_analytics(request)
                elif rtype == 'get_details':
                    response = self.handle_get_details(request)
                # handle_sync_sources 已移除
                else:
                    response = {"type": "response", "status": "ok", "msg": "Received"}

                if response:
                    self.send_packet(response)

            except Exception as e:
                print(f"[Conn Error] {e}")
                break

        self.conn.close()


class InkServer:
    def __init__(self):
        print("[Init] Generating RSA Keys...")
        self.private_key, self.public_key = SecurityManager.generate_rsa_keys()
        self.public_key_bytes = SecurityManager.public_key_to_bytes(self.public_key)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
    server = InkServer()
    server.start()