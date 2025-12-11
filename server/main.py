import socket
import threading
import struct
import json
import sys
import os
import base64
import time
import random
import traceback
from datetime import date, timedelta, datetime
from sqlalchemy import func, or_

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security import SecurityManager
from database import db_manager, User, DailyReport, DetailRecord, Friend, Group, GroupMember, GroupMessage
from email_utils import EmailManager

HOST = '0.0.0.0'
PORT = 23456
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")

if not os.path.exists(AVATAR_DIR):
    os.makedirs(AVATAR_DIR)

verification_codes = {}

# 全局在线客户端映射 {user_id: client_handler_instance}
connected_clients = {}
clients_lock = threading.Lock()


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
        self.username = None

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

    def broadcast_to_users(self, user_ids, message_dict):
        with clients_lock:
            for uid in user_ids:
                if uid in connected_clients:
                    try:
                        connected_clients[uid].send_packet(message_dict)
                    except:
                        pass

    # --- 业务处理函数 ---

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
                self.username = user.username

                with clients_lock:
                    connected_clients[user.id] = self

                avatar_data = ""
                if user.avatar_url and user.avatar_url != "default.jpg":
                    path = os.path.join(AVATAR_DIR, user.avatar_url)
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            avatar_data = base64.b64encode(f.read()).decode('utf-8')

                today = date.today()
                daily_report = session.query(DailyReport).filter_by(user_id=user.id, report_date=today).first()
                today_total = daily_report.total_words if daily_report else 0

                # Check if user is already in a group
                current_group = session.query(GroupMember).filter_by(user_id=user.id).first()
                group_info = {}
                if current_group:
                    g = session.query(Group).get(current_group.group_id)
                    if g:
                        group_info = {"id": g.id, "name": g.name, "owner_id": g.owner_id}

                print(f"[Login] User {username} logged in successfully.")
                return {
                    "type": "login_response",
                    "status": "success",
                    "nickname": user.nickname or user.username,
                    "username": user.username,
                    "user_id": user.id,
                    "email": user.email or "",
                    "avatar_data": avatar_data,
                    "today_total": today_total,
                    "current_group": group_info
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
            if existing: return {"type": "register_response", "status": "fail", "msg": "用户名已存在"}
            new_user = User(username=username, password_hash=password_hash, nickname=username, email=email or None)
            session.add(new_user)
            session.commit()
            return {"type": "register_response", "status": "success", "msg": "注册成功"}
        finally:
            session.close()

    def handle_sync_data(self, request):
        if not self.user_id: return None
        increment = request.get('increment', 0)
        duration = request.get('duration', 0)
        if increment <= 0 and duration <= 0: return None

        session = db_manager.get_session()
        try:
            new_record = DetailRecord(
                user_id=self.user_id,
                word_increment=increment,
                duration_seconds=duration,
                source_type="client_sync",
                end_time=datetime.now()
            )
            session.add(new_record)
            today = date.today()
            daily = session.query(DailyReport).filter_by(user_id=self.user_id, report_date=today).first()
            if not daily:
                daily = DailyReport(user_id=self.user_id, report_date=today, total_words=0)
                session.add(daily)
            daily.total_words += increment
            session.commit()
            return {"type": "response", "status": "ok", "msg": "Synced"}
        finally:
            session.close()

    def handle_get_analytics(self, request):
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            one_year_ago = date.today() - timedelta(days=365)
            reports = session.query(DailyReport).filter(
                DailyReport.user_id == self.user_id,
                DailyReport.report_date >= one_year_ago
            ).all()
            heatmap = {str(r.report_date): r.total_words for r in reports}
            return {"type": "analytics_data", "heatmap": heatmap}
        finally:
            session.close()

    def handle_get_details(self, request):
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
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

    # --- Social: Friends ---

    def handle_search_user(self, request):
        target_uid_or_name = request.get('query')
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(
                (User.username == target_uid_or_name) | (User.id == target_uid_or_name)
            ).first()

            if user:
                return {
                    "type": "search_user_response",
                    "status": "success",
                    "data": {"id": user.id, "username": user.username, "nickname": user.nickname}
                }
            return {"type": "search_user_response", "status": "fail", "msg": "User not found"}
        finally:
            session.close()

    def handle_add_friend(self, request):
        if not self.user_id: return None
        friend_id = request.get('friend_id')
        session = db_manager.get_session()
        try:
            if friend_id == self.user_id:
                return {"type": "response", "status": "fail", "msg": "Cannot add yourself"}

            # 检查是否已经是好友
            exists = session.query(Friend).filter_by(user_id=self.user_id, friend_id=friend_id,
                                                     status='accepted').first()
            if exists:
                return {"type": "response", "status": "fail", "msg": "Already friends"}

            # 检查是否已经发送过请求
            pending = session.query(Friend).filter_by(user_id=self.user_id, friend_id=friend_id,
                                                      status='pending').first()
            if pending:
                return {"type": "response", "status": "fail", "msg": "Request already sent"}

            # 创建申请记录 (User -> Friend)
            new_request = Friend(user_id=self.user_id, friend_id=friend_id, status="pending")
            session.add(new_request)
            session.commit()

            # 通知对方有新请求 (刷新对方的请求列表)
            self.broadcast_to_users([friend_id], {"type": "refresh_friend_requests"})

            return {"type": "response", "status": "success", "msg": "Request sent"}
        finally:
            session.close()

    def handle_get_friend_requests(self, request):
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            # 查询所有发送给我的请求 (friend_id = me, status = pending)
            reqs = session.query(Friend).filter_by(friend_id=self.user_id, status='pending').all()
            data = []
            for r in reqs:
                sender = session.query(User).get(r.user_id)
                if sender:
                    data.append({
                        "request_id": r.id,
                        "user_id": sender.id,
                        "username": sender.username,
                        "nickname": sender.nickname
                    })
            return {"type": "friend_requests_response", "data": data}
        finally:
            session.close()

    def handle_respond_friend(self, request):
        if not self.user_id: return None
        request_id = request.get('request_id')
        action = request.get('action')  # 'accept' or 'reject'

        session = db_manager.get_session()
        try:
            friend_req = session.query(Friend).get(request_id)
            if not friend_req or friend_req.friend_id != self.user_id:
                return {"type": "response", "status": "fail", "msg": "Invalid request"}

            sender_id = friend_req.user_id

            if action == 'accept':
                friend_req.status = 'accepted'
                # 创建双向关系 (Me -> Sender) 也设为 accepted
                reverse_rel = Friend(user_id=self.user_id, friend_id=sender_id, status='accepted')
                session.add(reverse_rel)
                session.commit()

                # 通知双方刷新好友列表
                self.broadcast_to_users([self.user_id, sender_id], {"type": "refresh_friends"})

            else:
                session.delete(friend_req)
                session.commit()
                self.broadcast_to_users([self.user_id], {"type": "refresh_friend_requests"})

            return {"type": "response", "status": "success"}
        finally:
            session.close()

    def handle_get_friends(self, request):
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            # 只获取 accepted 的好友
            friends_rels = session.query(Friend).filter_by(user_id=self.user_id, status='accepted').all()
            friend_list = []
            for rel in friends_rels:
                u = session.query(User).get(rel.friend_id)
                if u:
                    status = "Online" if u.id in connected_clients else "Offline"
                    friend_list.append({
                        "id": u.id,
                        "username": u.username,
                        "nickname": u.nickname,
                        "status": status
                    })
            return {"type": "get_friends_response", "data": friend_list}
        finally:
            session.close()

    # --- Social: Groups ---

    def handle_create_group(self, request):
        if not self.user_id: return None
        name = request.get('name')
        is_private = request.get('is_private', False)

        session = db_manager.get_session()
        try:
            # 1. 检查是否已经在其他群
            current = session.query(GroupMember).filter_by(user_id=self.user_id).first()
            if current:
                return {"type": "create_group_response", "status": "fail",
                        "msg": "You are already in a group. Please leave it first."}

            # 2. 创建新群
            new_group = Group(name=name, owner_id=self.user_id, is_private=is_private)
            session.add(new_group)
            session.flush()

            # 3. 加入新群
            member = GroupMember(group_id=new_group.id, user_id=self.user_id)
            session.add(member)
            session.commit()

            return {"type": "create_group_response", "status": "success", "group_id": new_group.id, "group_name": name}
        finally:
            session.close()

    def handle_get_public_groups(self, request):
        session = db_manager.get_session()
        try:
            groups = session.query(Group).filter_by(is_private=False).order_by(Group.updated_at.desc()).limit(50).all()
            data = []
            for g in groups:
                count = session.query(GroupMember).filter_by(group_id=g.id).count()
                data.append({
                    "id": g.id,
                    "name": g.name,
                    "member_count": count,
                    "updated_at": g.updated_at.strftime("%H:%M")
                })
            return {"type": "group_list_response", "data": data}
        finally:
            session.close()

    def handle_join_group(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        session = db_manager.get_session()
        try:
            # 1. 检查是否已经在群 (排他性)
            current = session.query(GroupMember).filter_by(user_id=self.user_id).first()
            if current:
                if current.group_id == group_id:
                    return {"type": "join_group_response", "status": "success", "group_id": group_id}  # 已经在里面了，视为成功重连
                else:
                    return {"type": "join_group_response", "status": "fail", "msg": "You are already in another group."}

            # 2. 检查人数
            count = session.query(GroupMember).filter_by(group_id=group_id).count()
            if count >= 10:
                return {"type": "join_group_response", "status": "fail", "msg": "Group is full (Max 10)"}

            # 3. 加入
            new_mem = GroupMember(group_id=group_id, user_id=self.user_id)
            session.add(new_mem)

            group = session.query(Group).get(group_id)
            if group:
                group.updated_at = datetime.now()
            session.commit()

            return {"type": "join_group_response", "status": "success", "group_id": group_id}
        finally:
            session.close()

    def handle_leave_group(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        session = db_manager.get_session()
        try:
            session.query(GroupMember).filter_by(user_id=self.user_id, group_id=group_id).delete()

            # 如果群里没人了，是否删除群？(可选，这里暂时不删，或者可以标记为inactive)
            # count = session.query(GroupMember).filter_by(group_id=group_id).count()
            # if count == 0: session.delete(...)

            session.commit()
            return {"type": "leave_group_response", "status": "success"}
        finally:
            session.close()

    def handle_send_group_msg(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        content = request.get('content')

        session = db_manager.get_session()
        try:
            # 验证用户是否在群里
            member = session.query(GroupMember).filter_by(group_id=group_id, user_id=self.user_id).first()
            if not member: return

            user = session.query(User).get(self.user_id)
            msg = GroupMessage(group_id=group_id, user_id=self.user_id, user_nickname=user.nickname, content=content)
            session.add(msg)

            group = session.query(Group).get(group_id)
            group.updated_at = datetime.now()
            session.commit()

            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            member_ids = [m.user_id for m in members]

            push_msg = {
                "type": "group_msg_push",
                "group_id": group_id,
                "sender": user.nickname,
                "content": content,
                "time": datetime.now().strftime("%H:%M")
            }
            self.broadcast_to_users(member_ids, push_msg)
        finally:
            session.close()

    def handle_get_group_detail(self, request):
        group_id = request.get('group_id')
        if not group_id: return None

        session = db_manager.get_session()
        try:
            group = session.query(Group).get(group_id)
            if not group: return None

            two_days_ago = datetime.now() - timedelta(days=2)
            msgs = session.query(GroupMessage).filter(
                GroupMessage.group_id == group_id,
                GroupMessage.timestamp >= two_days_ago
            ).order_by(GroupMessage.timestamp.asc()).all()

            chat_history = [{
                "sender": m.user_nickname,
                "content": m.content,
                "time": m.timestamp.strftime("%H:%M")
            } for m in msgs]

            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            leaderboard = []

            for m in members:
                user = session.query(User).get(m.user_id)
                word_count = 0

                if group.sprint_active and group.sprint_start_time:
                    total = session.query(func.sum(DetailRecord.word_increment)).filter(
                        DetailRecord.user_id == m.user_id,
                        DetailRecord.end_time >= group.sprint_start_time
                    ).scalar()
                    word_count = total if total else 0

                is_online = m.user_id in connected_clients

                leaderboard.append({
                    "nickname": user.nickname,
                    "word_count": word_count,
                    "is_online": is_online,
                    "reached_target": (word_count >= group.sprint_target_words) if group.sprint_active else False
                })

            leaderboard.sort(key=lambda x: x['word_count'], reverse=True)

            return {
                "type": "group_detail_response",
                "group_id": group_id,
                "name": group.name,
                "owner_id": group.owner_id,
                "sprint_active": group.sprint_active,
                "sprint_target": group.sprint_target_words,
                "chat_history": chat_history,
                "leaderboard": leaderboard
            }
        finally:
            session.close()

    def handle_sprint_control(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        action = request.get('action')
        target = request.get('target', 0)

        session = db_manager.get_session()
        try:
            group = session.query(Group).get(group_id)
            if group.owner_id != self.user_id:
                return {"type": "response", "msg": "Only owner can control sprint"}

            if action == 'start':
                group.sprint_active = True
                group.sprint_start_time = datetime.now()
                group.sprint_target_words = target
                msg_content = f"📢 拼字开始！目标: {target}字"
            else:
                group.sprint_active = False
                msg_content = f"🛑 拼字结束。"

            session.commit()

            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            member_ids = [m.user_id for m in members]

            push_msg = {
                "type": "group_msg_push",
                "group_id": group_id,
                "sender": "SYSTEM",
                "content": msg_content,
                "time": datetime.now().strftime("%H:%M")
            }
            self.broadcast_to_users(member_ids, push_msg)

            self.broadcast_to_users(member_ids, {"type": "sprint_status_push", "group_id": group_id})

            return {"type": "response", "status": "success"}
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

                rtype = request.get('type')
                response = None

                print(f"[Processing Request] Type: {rtype}, User: {self.username or 'Unauthenticated'}")

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
                elif rtype == 'search_user':
                    response = self.handle_search_user(request)
                elif rtype == 'add_friend':
                    response = self.handle_add_friend(request)
                elif rtype == 'get_friend_requests':
                    response = self.handle_get_friend_requests(request)  # 新增
                elif rtype == 'respond_friend':
                    response = self.handle_respond_friend(request)  # 新增
                elif rtype == 'get_friends':
                    response = self.handle_get_friends(request)
                elif rtype == 'create_group':
                    response = self.handle_create_group(request)
                elif rtype == 'get_public_groups':
                    response = self.handle_get_public_groups(request)
                elif rtype == 'join_group':
                    response = self.handle_join_group(request)
                elif rtype == 'leave_group':
                    response = self.handle_leave_group(request)  # 新增
                elif rtype == 'group_chat':
                    self.handle_send_group_msg(request)
                elif rtype == 'get_group_detail':
                    response = self.handle_get_group_detail(request)
                elif rtype == 'sprint_control':
                    response = self.handle_sprint_control(request)
                else:
                    response = {"type": "response", "status": "ok", "msg": "Ack"}

                if response:
                    self.send_packet(response)

            except json.JSONDecodeError:
                print(f"[Handler Error] JSON Decode Failed. Possible decryption error.")
                break
            except Exception as e:
                print(f"[Handler Error] {e}")
                traceback.print_exc()
                break

        with clients_lock:
            if self.user_id and self.user_id in connected_clients:
                del connected_clients[self.user_id]
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
    db_manager.init_db()
    server = InkServer()
    server.start()