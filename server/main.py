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
from sqlalchemy import func, or_, and_
from sqlalchemy.orm.exc import NoResultFound

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.security import SecurityManager
from database import db_manager, User, DailyReport, DetailRecord, \
    FriendRequest, Friendship, Group, GroupMember, GroupMessage, SprintScore
from email_utils import EmailManager

HOST = '0.0.0.0'
PORT = 23456
AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "avatars")

if not os.path.exists(AVATAR_DIR):
    os.makedirs(AVATAR_DIR)

verification_codes = {}
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

    def broadcast_to_all(self, message_dict):
        with clients_lock:
            for uid, client in connected_clients.items():
                try:
                    client.send_packet(message_dict)
                except:
                    pass

    def load_avatar_base64(self, avatar_url):
        if avatar_url and avatar_url != "default.jpg":
            path = os.path.join(AVATAR_DIR, avatar_url)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        return ""

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

                avatar_data = self.load_avatar_base64(user.avatar_url)

                today = date.today()
                daily_report = session.query(DailyReport).filter_by(user_id=user.id, report_date=today).first()
                today_total = daily_report.total_words if daily_report else 0

                current_group_member = session.query(GroupMember).filter_by(user_id=user.id).first()
                group_info = {}
                if current_group_member:
                    g = session.query(Group).get(current_group_member.group_id)
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
                    "signature": user.signature or "",
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
            print(f"[Register] New user {username} created.")
            return {"type": "register_response", "status": "success", "msg": "注册成功"}
        except Exception as e:
            print(f"[Register Logic Error] {e}")
            raise e
        finally:
            session.close()

    def handle_sync_data(self, request):
        if not self.user_id: return None
        increment = request.get('increment', 0)
        duration = request.get('duration', 0)
        client_ts = request.get('timestamp')
        client_date_str = request.get('local_date')

        if increment <= 0 and duration <= 0: return None

        session = db_manager.get_session()
        try:
            if client_ts:
                record_time = datetime.fromtimestamp(client_ts)
            else:
                record_time = datetime.now()

            new_record = DetailRecord(
                user_id=self.user_id,
                word_increment=increment,
                duration_seconds=duration,
                source_type="client_sync",
                end_time=record_time
            )
            session.add(new_record)

            if client_date_str:
                try:
                    today = datetime.strptime(client_date_str, "%Y-%m-%d").date()
                except ValueError:
                    today = date.today()
            else:
                today = date.today()

            daily = session.query(DailyReport).filter_by(user_id=self.user_id, report_date=today).first()
            if not daily:
                daily = DailyReport(user_id=self.user_id, report_date=today, total_words=0)
                session.add(daily)
            daily.total_words += increment

            # 更新拼字房间进度
            current_group_member = session.query(GroupMember).filter_by(user_id=self.user_id).first()
            if current_group_member:
                group_id = current_group_member.group_id
                group = session.query(Group).get(group_id)

                if group and group.sprint_active:
                    sprint_score = session.query(SprintScore).filter_by(
                        group_id=group_id, user_id=self.user_id
                    ).first()

                    if not sprint_score:
                        sprint_score = SprintScore(group_id=group_id, user_id=self.user_id, current_score=0)
                        session.add(sprint_score)

                    sprint_score.current_score += increment

                    members = session.query(GroupMember).filter_by(group_id=group_id).all()
                    member_ids = [m.user_id for m in members]

                    self.broadcast_to_users(member_ids, {"type": "sprint_status_push", "group_id": group_id})

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
        new_signature = request.get('signature')
        avatar_b64 = request.get('avatar_data')
        session = db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=self.user_id).first()
            if user:
                if new_nick: user.nickname = new_nick
                if new_email is not None: user.email = new_email.strip() or None
                if new_signature is not None: user.signature = new_signature.strip()
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

    def handle_search_user(self, request):
        target_query = request.get('query')
        session = db_manager.get_session()
        try:
            try:
                target_id = int(target_query)
                is_numeric = True
            except ValueError:
                target_id = None
                is_numeric = False

            filter_conditions = (User.username == target_query) | (User.nickname == target_query)
            if is_numeric:
                filter_conditions = filter_conditions | (User.id == target_id)

            user = session.query(User).filter(filter_conditions).first()

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

            id1, id2 = sorted([self.user_id, friend_id])
            is_friend = session.query(Friendship).filter_by(user_a_id=id1, user_b_id=id2).first()
            if is_friend:
                return {"type": "response", "status": "fail", "msg": "Already friends"}

            pending = session.query(FriendRequest).filter(
                ((FriendRequest.sender_id == self.user_id) & (FriendRequest.receiver_id == friend_id)) |
                ((FriendRequest.sender_id == friend_id) & (FriendRequest.receiver_id == self.user_id))
            ).first()
            if pending:
                return {"type": "response", "status": "fail", "msg": "Request already sent or pending response"}

            new_request = FriendRequest(sender_id=self.user_id, receiver_id=friend_id)
            session.add(new_request)
            session.commit()

            self.broadcast_to_users([friend_id], {"type": "refresh_friend_requests"})

            return {"type": "response", "status": "success", "msg": "Request sent"}
        finally:
            session.close()

    def handle_delete_friend(self, request):
        if not self.user_id: return None
        friend_id = request.get('friend_id')
        session = db_manager.get_session()
        try:
            id1, id2 = sorted([self.user_id, friend_id])
            session.query(Friendship).filter_by(user_a_id=id1, user_b_id=id2).delete()
            session.commit()
            return {"type": "delete_friend_response", "status": "success", "msg": "Friend deleted"}
        finally:
            session.close()

    def handle_get_friend_requests(self, request):
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            reqs = session.query(FriendRequest).filter_by(receiver_id=self.user_id).all()
            data = []
            for r in reqs:
                sender = session.query(User).get(r.sender_id)
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
        action = request.get('action')
        session = db_manager.get_session()
        try:
            friend_req = session.query(FriendRequest).get(request_id)
            if not friend_req or friend_req.receiver_id != self.user_id:
                return {"type": "response", "status": "fail", "msg": "Invalid request"}

            sender_id = friend_req.sender_id

            if action == 'accept':
                id1, id2 = sorted([self.user_id, sender_id])
                existing_friendship = session.query(Friendship).filter_by(user_a_id=id1, user_b_id=id2).first()
                if not existing_friendship:
                    new_friendship = Friendship(user_a_id=id1, user_b_id=id2)
                    session.add(new_friendship)
                session.delete(friend_req)
                session.commit()
                self.broadcast_to_users([self.user_id, sender_id], {"type": "refresh_friends"})

            elif action == 'reject':
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
            friends_rels = session.query(Friendship).filter(
                (Friendship.user_a_id == self.user_id) | (Friendship.user_b_id == self.user_id)
            ).all()

            friend_list = []
            for rel in friends_rels:
                friend_id = rel.user_b_id if rel.user_a_id == self.user_id else rel.user_a_id
                u = session.query(User).get(friend_id)
                if u:
                    status = "Online" if u.id in connected_clients else "Offline"
                    avatar_data = self.load_avatar_base64(u.avatar_url)
                    friend_list.append({
                        "id": u.id,
                        "username": u.username,
                        "nickname": u.nickname,
                        "signature": u.signature,  # 返回个性签名
                        "avatar_data": avatar_data,  # 返回头像
                        "status": status
                    })
            return {"type": "get_friends_response", "data": friend_list}
        finally:
            session.close()

    def handle_create_group(self, request):
        if not self.user_id: return None
        name = request.get('name')
        is_private = request.get('is_private', False)
        password = request.get('password', None)  # 接收密码

        if is_private == "true" or is_private == 1:
            is_private = True
        elif is_private == "false" or is_private == 0:
            is_private = False

        if password and not password.strip():
            password = None

        session = db_manager.get_session()
        try:
            current = session.query(GroupMember).filter_by(user_id=self.user_id).first()
            if current:
                return {
                    "type": "create_group_response",
                    "status": "fail",
                    "msg": "You are already in a group.",
                    "current_group_id": current.group_id
                }

            new_group = Group(name=name, owner_id=self.user_id, is_private=is_private, password=password)
            session.add(new_group)
            session.flush()

            member = GroupMember(group_id=new_group.id, user_id=self.user_id)
            session.add(member)
            session.commit()

            # 无论是否私密，创建成功后可能都需要更新客户端列表（私密对好友可见）
            self.broadcast_to_all({"type": "refresh_groups"})

            return {"type": "create_group_response", "status": "success", "group_id": new_group.id, "group_name": name}
        finally:
            session.close()

    def handle_join_group(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        input_password = request.get('password')

        session = db_manager.get_session()
        try:
            current = session.query(GroupMember).filter_by(user_id=self.user_id).first()
            if current:
                if current.group_id == group_id:
                    return {"type": "join_group_response", "status": "success", "group_id": group_id}
                else:
                    return {
                        "type": "join_group_response",
                        "status": "fail",
                        "msg": "You are already in another group.",
                        "current_group_id": current.group_id
                    }

            group = session.query(Group).get(group_id)
            if not group:
                return {"type": "join_group_response", "status": "fail", "msg": "Group not found"}

            # 1. 检查是否正在拼字 (Sprint Active)
            if group.sprint_active:
                return {"type": "join_group_response", "status": "fail", "msg": "Room is currently sprinting"}

            # 2. 检查密码
            if group.password:
                if not input_password or input_password != group.password:
                    return {"type": "join_group_response", "status": "fail",
                            "msg": "password_required" if not input_password else "Incorrect password"}

            count = session.query(GroupMember).filter_by(group_id=group_id).count()
            if count >= 10:
                return {"type": "join_group_response", "status": "fail", "msg": "Group is full (Max 10)"}

            new_mem = GroupMember(group_id=group_id, user_id=self.user_id)
            session.add(new_mem)

            group.updated_at = datetime.now()
            session.commit()

            self.broadcast_to_all({"type": "refresh_groups"})

            return {"type": "join_group_response", "status": "success", "group_id": group_id}
        finally:
            session.close()

    def handle_leave_group(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        session = db_manager.get_session()
        try:
            group = session.query(Group).get(group_id)
            if group and group.owner_id == self.user_id:
                # 房主离开，解散房间
                session.delete(group)
                session.commit()
                # 获取该房间所有成员并通知
                members = session.query(GroupMember).filter_by(group_id=group_id).all()
                member_ids = [m.user_id for m in members]  # 此时已被级联删除，需注意逻辑
                # 因为 delete group 会级联删除 members，所以需要在 delete 前获取 members
                # 但上面 session.delete(group) 已经执行，但只要没 commit，session 内可能还有状态
                # 最好的方式是先把 IDs 查出来
                # 上面代码逻辑有点问题，session.delete(group) 后 members 可能访问不到。
                # 修正：应该在 delete 前查 ID。
                # 这里做简化，假设客户端收到 group_disbanded 会自己处理
                self.broadcast_to_all({"type": "refresh_groups"})
                # 这里发送解散广播有点晚了，因为 member 记录已被删。
                # 客户端轮询或收到 refresh_groups 发现自己不在房间即可。
                # 或者在 delete 前查询 member_ids
                return {"type": "leave_group_response", "status": "success", "msg": "Group disbanded"}

            # 普通成员离开
            session.query(GroupMember).filter_by(user_id=self.user_id, group_id=group_id).delete()
            session.query(SprintScore).filter_by(user_id=self.user_id, group_id=group_id).delete()
            session.commit()

            self.broadcast_to_all({"type": "refresh_groups"})
            self.broadcast_to_users(
                [m.user_id for m in session.query(GroupMember).filter_by(group_id=group_id).all()],
                {"type": "sprint_status_push", "group_id": group_id}
            )

            return {"type": "leave_group_response", "status": "success"}
        finally:
            session.close()

    def handle_get_lobby_data(self, request):
        """获取大厅数据：公开房间 + 自己的私密房间 + 好友的私密房间"""
        if not self.user_id: return None
        session = db_manager.get_session()
        try:
            # 1. 获取好友 ID 列表
            friends_rels = session.query(Friendship).filter(
                (Friendship.user_a_id == self.user_id) | (Friendship.user_b_id == self.user_id)
            ).all()
            friend_ids = []
            for rel in friends_rels:
                friend_ids.append(rel.user_b_id if rel.user_a_id == self.user_id else rel.user_a_id)

            # 包括自己
            allowed_ids = friend_ids + [self.user_id]

            # 2. 查询所有符合条件的房间
            # 条件：(公开) OR (私密 AND 房主是好友或自己)
            groups = session.query(Group).filter(
                or_(
                    Group.is_private == False,
                    and_(Group.is_private == True, Group.owner_id.in_(allowed_ids))
                )
            ).order_by(Group.updated_at.desc()).limit(50).all()

            data = []
            for g in groups:
                count = session.query(GroupMember).filter_by(group_id=g.id).count()
                owner = session.query(User).get(g.owner_id)
                owner_nick = owner.nickname if owner else "Unknown"
                owner_avatar = self.load_avatar_base64(owner.avatar_url) if owner else ""

                data.append({
                    "id": g.id,
                    "name": g.name,
                    "member_count": count,
                    "updated_at": g.updated_at.strftime("%H:%M"),
                    "owner_nickname": owner_nick,
                    "owner_avatar": owner_avatar,
                    "has_password": True if g.password else False,
                    "is_private": g.is_private,
                    "sprint_active": g.sprint_active
                })
            return {"type": "group_list_response", "data": data}
        finally:
            session.close()

    def handle_send_group_msg(self, request):
        if not self.user_id: return None
        group_id = request.get('group_id')
        content = request.get('content')
        session = db_manager.get_session()
        try:
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
                "time": time.time()
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
                "time": m.timestamp.timestamp()
            } for m in msgs]

            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            member_ids = [m.user_id for m in members]
            scores = session.query(SprintScore).filter(
                SprintScore.group_id == group_id,
                SprintScore.user_id.in_(member_ids)
            ).all()
            score_map = {s.user_id: s.current_score for s in scores}

            leaderboard = []
            owner_avatar_data = ""
            for m in members:
                user = session.query(User).get(m.user_id)
                word_count = score_map.get(m.user_id, 0)
                avatar_data = self.load_avatar_base64(user.avatar_url)

                if user.id == group.owner_id:
                    owner_avatar_data = avatar_data

                is_online = m.user_id in connected_clients
                leaderboard.append({
                    "user_id": user.id,  # 关键：返回 ID 以便添加好友
                    "nickname": user.nickname,
                    "word_count": word_count,
                    "is_online": is_online,
                    "avatar_data": avatar_data,
                    "reached_target": (word_count >= group.sprint_target_words) if group.sprint_active else False
                })

            leaderboard.sort(key=lambda x: x['word_count'], reverse=True)

            return {
                "type": "group_detail_response",
                "group_id": group_id,
                "name": group.name,
                "owner_id": group.owner_id,
                "owner_avatar": owner_avatar_data,
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
                session.query(SprintScore).filter_by(group_id=group_id).delete()
                group.sprint_active = True
                group.sprint_start_time = datetime.now()
                group.sprint_target_words = target
                msg_content = f"📢 拼字开始！目标: {target}字"
            else:
                group.sprint_active = False
                msg_content = f"🛑 拼字结束。"

            sys_msg = GroupMessage(
                group_id=group_id,
                user_id=None,
                user_nickname="SYSTEM",
                content=msg_content,
                timestamp=datetime.now()
            )
            session.add(sys_msg)
            session.commit()

            members = session.query(GroupMember).filter_by(group_id=group_id).all()
            member_ids = [m.user_id for m in members]

            push_msg = {
                "type": "group_msg_push",
                "group_id": group_id,
                "sender": "SYSTEM",
                "content": msg_content,
                "time": time.time()
            }
            self.broadcast_to_users(member_ids, push_msg)
            self.broadcast_to_users(member_ids, {"type": "sprint_status_push", "group_id": group_id})

            # 更新大厅状态 (拼字中不可加入)
            self.broadcast_to_all({"type": "refresh_groups"})

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
                elif rtype == 'delete_friend':  # 新增
                    response = self.handle_delete_friend(request)
                elif rtype == 'get_friend_requests':
                    response = self.handle_get_friend_requests(request)
                elif rtype == 'respond_friend':
                    response = self.handle_respond_friend(request)
                elif rtype == 'get_friends':
                    response = self.handle_get_friends(request)
                elif rtype == 'create_group':
                    response = self.handle_create_group(request)
                elif rtype == 'get_public_groups':
                    response = self.handle_get_lobby_data(request)  # 替换为新逻辑
                elif rtype == 'join_group':
                    response = self.handle_join_group(request)
                elif rtype == 'leave_group':
                    response = self.handle_leave_group(request)
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
                print(f"[Handler Error] JSON Decode Failed.")
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