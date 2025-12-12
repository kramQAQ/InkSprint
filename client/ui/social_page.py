from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QTabWidget,
                             QInputDialog, QMessageBox, QFrame, QSplitter, QTextEdit,
                             QCheckBox, QDialog, QFormLayout, QSpinBox, QStackedWidget,
                             QSizePolicy, QButtonGroup)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from datetime import datetime  # 【新增】用于时间格式化
from .float_group_window import FloatGroupWindow
from .localization import STRINGS  # 导入汉化配置


class SocialPage(QWidget):
    def __init__(self, network_manager, user_id=0):
        super().__init__()
        self.network = network_manager
        self.my_user_id = user_id

        self.current_group_id = None
        self.is_group_owner = False
        self.current_group_name = None  # 新增：缓存房间名称

        # 悬浮窗实例
        self.float_group_win = None

        # 初始化界面元素引用
        self.friend_list = None
        self.group_stack = None
        self.lobby_widget = None
        self.room_widget = None
        self.group_list_widget = None
        self.chat_display = None
        self.rank_list = None
        self.sprint_ctrl_frame = None
        self.lbl_room_name = None
        self.lbl_sprint_status = None

        # 按钮引用以便加红点
        self.btn_friend_requests = None
        self.tab_btns = {}  # 存储顶部切换按钮

        self.setup_ui()

        # 计时器：每20秒更新群详情（排行榜）
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(20000)  # 20s
        self.update_timer.timeout.connect(self.refresh_current_group_data)

        # 计时器：每1小时更新房间列表
        self.list_timer = QTimer(self)
        self.list_timer.setInterval(3600 * 1000)
        self.list_timer.timeout.connect(self.refresh_group_list)
        if self.my_user_id > 0:
            self.list_timer.start()

    def set_user_id(self, user_id):
        """延迟设置用户ID，并启动相关服务"""
        self.my_user_id = user_id
        if self.my_user_id > 0:
            if not self.list_timer.isActive():
                self.list_timer.start()

            # 【修复 3】确保在登录后立即刷新大厅列表，而不是等待 1 小时
            if not self.current_group_id:  # 只有当不在房间内时才请求大厅列表
                self.refresh_group_list()

    def restore_group_state(self, group_info):
        """登录时如果已经在群里，直接恢复到群界面"""
        print(f"[Social] Attempting restore group: {group_info}")
        if group_info and 'id' in group_info:
            gid = group_info['id']
            name = group_info.get('name', STRINGS["lbl_loading"])
            owner_id = group_info.get('owner_id', 0)

            # 【修复 1.5】直接调用 enter_room_view 进入房间视图
            self.enter_room_view(gid, name, owner_id)
            # 立即获取详情，覆盖 Loading Name
            self.refresh_current_group_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Top Switch Buttons (Tiled Row) ---
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.btn_group = QButtonGroup(self)

        # 交换顺序：先 Groups 后 Friends
        self.btn_tab_groups = QPushButton(STRINGS["tab_groups"])
        self.btn_tab_friends = QPushButton(STRINGS["tab_friends"])

        for idx, btn in enumerate([self.btn_tab_groups, self.btn_tab_friends]):
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(45)
            # 基础样式，选中样式在 Main Window theme 中统一或者这里简单处理
            # 为了简单，这里直接使用setStyleSheet模拟Tab效果
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: transparent;
                    font-weight: bold;
                    font-size: 15px;
                    border-bottom: 2px solid transparent;
                }
                QPushButton:checked {
                    color: #9DC88D;
                    border-bottom: 2px solid #9DC88D;
                }
            """)
            self.btn_group.addButton(btn, idx)
            top_layout.addWidget(btn)
            btn.clicked.connect(lambda _, i=idx: self.main_stack.setCurrentIndex(i))

        layout.addWidget(top_bar)

        # --- Content Stack ---
        self.main_stack = QStackedWidget()

        # 1. Groups Page
        self.main_stack.addWidget(self.create_groups_tab())

        # 2. Friends Page
        self.main_stack.addWidget(self.create_friends_tab())

        layout.addWidget(self.main_stack)

        # 默认选中 Groups
        self.btn_tab_groups.setChecked(True)
        self.main_stack.setCurrentIndex(0)

    def create_friends_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Top Bar
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(STRINGS["search_placeholder"])

        # 搜索按钮
        btn_search = QPushButton(STRINGS["btn_search_user"])  # 修改文案
        btn_search.clicked.connect(self.search_user_to_add)

        self.btn_friend_requests = QPushButton(STRINGS["btn_friend_reqs"])
        self.btn_friend_requests.clicked.connect(self.show_friend_requests)
        self.btn_friend_requests.setStyleSheet("background-color: transparent;")  # 初始样式

        btn_refresh = QPushButton(STRINGS["btn_refresh_list"])
        btn_refresh.clicked.connect(self.load_friends)

        top.addWidget(self.search_input)
        top.addWidget(btn_search)
        top.addWidget(self.btn_friend_requests)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        # List
        self.friend_list = QListWidget()
        layout.addWidget(self.friend_list)

        return widget

    def search_user_to_add(self):
        """执行搜索并弹出添加确认对话框"""
        query = self.search_input.text().strip()
        if not query: return
        # 搜索是第一步，添加是第二步，这里只执行搜索
        self.network.send_request({"type": "search_user", "query": query})

    def create_groups_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.group_stack = QStackedWidget()

        # 1. Lobby
        self.lobby_widget = QWidget()
        lobby_layout = QVBoxLayout(self.lobby_widget)

        l_top = QHBoxLayout()
        btn_create = QPushButton(STRINGS["btn_create_group"])
        btn_create.clicked.connect(self.show_create_group_dialog)
        btn_refresh_g = QPushButton(STRINGS["btn_refresh_lobby"])
        btn_refresh_g.clicked.connect(self.refresh_group_list)

        l_top.addWidget(btn_create)
        l_top.addWidget(btn_refresh_g)
        l_top.addStretch()
        lobby_layout.addLayout(l_top)

        self.group_list_widget = QListWidget()
        self.group_list_widget.itemDoubleClicked.connect(self.join_selected_group)
        lobby_layout.addWidget(self.group_list_widget)

        # 2. Active Room
        self.room_widget = QWidget()
        room_layout = QVBoxLayout(self.room_widget)

        # Room Header
        r_header = QHBoxLayout()
        self.lbl_room_name = QLabel("Room Name")
        self.lbl_room_name.setStyleSheet("font-size: 18px; font-weight: bold;")

        btn_leave = QPushButton(STRINGS["btn_leave_room"])
        btn_leave.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        btn_leave.clicked.connect(self.leave_room_confirm)  # 离开前确认

        btn_float_chat = QPushButton(STRINGS["btn_float_chat"])
        btn_float_chat.clicked.connect(lambda: self.toggle_float_window("chat"))
        btn_float_rank = QPushButton(STRINGS["btn_float_rank"])
        btn_float_rank.clicked.connect(lambda: self.toggle_float_window("rank"))

        r_header.addWidget(self.lbl_room_name)
        r_header.addStretch()
        r_header.addWidget(btn_float_chat)
        r_header.addWidget(btn_float_rank)
        r_header.addWidget(btn_leave)
        room_layout.addLayout(r_header)

        # Room Content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        chat_container = QWidget()
        chat_v = QVBoxLayout(chat_container)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(STRINGS["chat_placeholder"])
        self.chat_input.returnPressed.connect(self.send_chat_message)
        btn_send = QPushButton(STRINGS["btn_send"])
        btn_send.clicked.connect(self.send_chat_message)

        input_h = QHBoxLayout()
        input_h.addWidget(self.chat_input)
        input_h.addWidget(btn_send)

        chat_v.addWidget(self.chat_display)
        chat_v.addLayout(input_h)

        rank_container = QWidget()
        rank_v = QVBoxLayout(rank_container)

        # 【布局修改】将控制按钮放在列表上方，确保它不会被列表内容挤压
        self.sprint_ctrl_frame = QFrame()
        sprint_l = QVBoxLayout(self.sprint_ctrl_frame)
        self.lbl_sprint_status = QLabel(STRINGS["status_sprint_inactive"])
        self.btn_start_sprint = QPushButton(STRINGS["btn_start_sprint"])
        self.btn_start_sprint.clicked.connect(self.start_sprint_dialog)
        self.btn_stop_sprint = QPushButton(STRINGS["btn_stop_sprint"])
        self.btn_stop_sprint.clicked.connect(self.stop_sprint)

        # 增加一个 QLabel 作为 Sprint 控制区的标题
        sprint_l.addWidget(QLabel(STRINGS["lbl_owner_ctrl"]))
        sprint_l.addWidget(self.lbl_sprint_status)
        sprint_l.addWidget(self.btn_start_sprint)
        sprint_l.addWidget(self.btn_stop_sprint)
        self.sprint_ctrl_frame.hide()

        self.rank_list = QListWidget()

        # 调整 rank_v 的addWidget顺序：控制区 -> 排行榜标题 -> 排行榜列表 -> 伸缩器
        rank_v.addWidget(self.sprint_ctrl_frame)  # 放在最前面
        rank_v.addWidget(QLabel(STRINGS["lbl_leaderboard"]))
        rank_v.addWidget(self.rank_list)
        rank_v.addStretch()  # 确保排行榜列表可以自动伸缩

        splitter.addWidget(chat_container)
        splitter.addWidget(rank_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        room_layout.addWidget(splitter)

        self.group_stack.addWidget(self.lobby_widget)
        self.group_stack.addWidget(self.room_widget)

        main_layout.addWidget(self.group_stack)
        return widget

    # --- Logic: Friends ---

    def load_friends(self):
        """请求好友列表"""
        if self.my_user_id > 0:
            print("[Social] Sending get_friends request...")
            self.network.send_request({"type": "get_friends"})

    def show_friend_requests(self):
        self.network.send_request({"type": "get_friend_requests"})
        # 恢复按钮样式
        if self.btn_friend_requests:
            self.btn_friend_requests.setStyleSheet("")

    def add_friend_request(self, friend_id):
        """发送添加好友请求"""
        self.network.send_request({"type": "add_friend", "friend_id": friend_id})

    def open_request_dialog(self, requests):
        dlg = QDialog(self)
        dlg.setWindowTitle(STRINGS["dialog_friend_req_title"])
        dlg.resize(400, 300)
        vbox = QVBoxLayout(dlg)

        lst = QListWidget()
        if not requests:
            lst.addItem(STRINGS["item_no_reqs"])

        for r in requests:
            text = f"{r['nickname']} ({r['username']})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r['request_id'])
            lst.addItem(item)

        vbox.addWidget(QLabel(STRINGS["lbl_dbl_click"]))
        vbox.addWidget(lst)

        def on_item_dbl_click(item):
            req_id = item.data(Qt.ItemDataRole.UserRole)
            if not req_id: return

            reply = QMessageBox.question(dlg, STRINGS["msg_req_confirm_title"],
                                         STRINGS["msg_req_confirm_fmt"].format(item.text()),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

            action = None
            if reply == QMessageBox.StandardButton.Yes:
                action = 'accept'
            elif reply == QMessageBox.StandardButton.No:
                action = 'reject'

            if action:
                self.network.send_request({"type": "respond_friend", "request_id": req_id, "action": action})
                lst.takeItem(lst.row(item))

        lst.itemDoubleClicked.connect(on_item_dbl_click)
        dlg.exec()

    # --- Logic: Groups ---

    def refresh_group_list(self):
        """请求刷新公共房间列表"""
        if self.my_user_id > 0:
            print("[Social] Sending get_public_groups request...")
            self.network.send_request({"type": "get_public_groups"})

    def show_create_group_dialog(self):
        name, ok = QInputDialog.getText(self, STRINGS["dialog_create_group_title"], STRINGS["dialog_group_name_label"])
        if ok and name:
            reply = QMessageBox.question(self, STRINGS["dialog_private_title"], STRINGS["dialog_private_msg"],
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            is_private = (reply == QMessageBox.StandardButton.Yes)
            self.network.send_request({
                "type": "create_group",
                "name": name,
                "is_private": is_private
            })

    def join_selected_group(self, item):
        group_id = item.data(Qt.ItemDataRole.UserRole)
        if group_id is not None:
            self.network.send_request({"type": "join_group", "group_id": group_id})

    def enter_room_view(self, group_id, name, owner_id):
        print(f"[Social] Entering room view: {name} ({group_id})")
        self.current_group_id = group_id
        self.current_group_name = name
        self.is_group_owner = (owner_id == self.my_user_id)
        if self.lbl_room_name:
            self.lbl_room_name.setText(STRINGS["lbl_room_name_fmt"].format(name))
        self.group_stack.setCurrentIndex(1)

        if self.is_group_owner:
            self.sprint_ctrl_frame.show()
        else:
            self.sprint_ctrl_frame.hide()

        self.chat_display.clear()
        self.rank_list.clear()

        self.refresh_current_group_data()
        self.update_timer.start()

    def leave_room_confirm(self):
        """确认离开房间"""
        if self.current_group_id and self.current_group_name:  # 确保房间名称已加载
            reply = QMessageBox.question(self, STRINGS["confirm_title"],
                                         STRINGS["msg_leave_confirm"].format(self.current_group_name),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.leave_room()
        elif self.current_group_id:
            # 如果名称未加载完成，使用 ID
            reply = QMessageBox.question(self, STRINGS["confirm_title"],
                                         STRINGS["msg_leave_confirm"].format(f"ID: {self.current_group_id}"),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.leave_room()

    def leave_room(self):
        """执行离开房间的请求和UI清理"""
        if self.current_group_id:
            self.network.send_request({"type": "leave_group", "group_id": self.current_group_id})

        self.update_timer.stop()
        self.current_group_id = None
        self.current_group_name = None
        self.group_stack.setCurrentIndex(0)
        if self.float_group_win:
            self.float_group_win.close()
            self.float_group_win = None
        self.refresh_group_list()

    def refresh_current_group_data(self):
        if self.current_group_id:
            self.network.send_request({"type": "get_group_detail", "group_id": self.current_group_id})

    def send_chat_message(self, text=None):
        if not isinstance(text, str):
            text = None
        if not text:
            text = self.chat_input.text().strip()
            self.chat_input.clear()

        if text and self.current_group_id:
            self.network.send_request({
                "type": "group_chat",
                "group_id": self.current_group_id,
                "content": text
            })

    # --- Logic: Sprint ---

    def start_sprint_dialog(self):
        target, ok = QInputDialog.getInt(self, STRINGS["dialog_sprint_title"], STRINGS["dialog_sprint_target"], 500, 10,
                                         100000)
        if ok:
            self.network.send_request({
                "type": "sprint_control",
                "action": "start",
                "group_id": self.current_group_id,
                "target": target
            })

    def stop_sprint(self):
        self.network.send_request({
            "type": "sprint_control",
            "action": "stop",
            "group_id": self.current_group_id
        })

    def toggle_float_window(self, mode):
        if not self.float_group_win:
            self.float_group_win = FloatGroupWindow(self)
            self.float_group_win.msg_sent.connect(self.send_chat_message)

        if mode == 'chat':
            self.float_group_win.show_chat()
        else:
            self.float_group_win.show_rank()

    # --- Network Handling ---

    def handle_network_msg(self, data):
        dtype = data.get("type")

        if dtype == "search_user_response":
            if data['status'] == 'success':
                u = data['data']
                reply = QMessageBox.question(self, STRINGS["msg_found_user_title"],
                                             STRINGS["msg_add_confirm_fmt"].format(u['nickname'], u['username']),
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.add_friend_request(u['id'])  # 调用新的添加好友请求函数
            else:
                QMessageBox.warning(self, STRINGS["msg_not_found_title"], STRINGS["msg_user_not_found"])

        elif dtype == "refresh_friends":
            # 【修复 2】接收到刷新好友列表的推送时，请求好友列表
            self.load_friends()
            QMessageBox.information(self, STRINGS["success_title"], STRINGS["msg_friend_list_updated"])

        elif dtype == "refresh_friend_requests":
            if self.btn_friend_requests:
                # 给好友请求按钮一个醒目的提示
                self.btn_friend_requests.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
            QMessageBox.information(self, STRINGS["warn_title"], STRINGS["msg_new_req"])

        elif dtype == "friend_requests_response":
            self.open_request_dialog(data.get("data", []))

        elif dtype == "get_friends_response":
            print(f"[Social] Received friends: {data.get('data')}")  # Debug Log
            self.friend_list.clear()
            for f in data.get("data", []):
                status_icon = "🟢" if f['status'] == 'Online' else "⚫"
                self.friend_list.addItem(f"{status_icon} {f['nickname']} ({f['username']})")

        elif dtype == "refresh_groups":
            self.refresh_group_list()

        elif dtype == "group_list_response":
            self.group_list_widget.clear()
            for g in data.get("data", []):
                item = QListWidgetItem(f"🏠 {g['name']} (👥 {g['member_count']}/10) - 🕒 {g['updated_at']}")
                item.setData(Qt.ItemDataRole.UserRole, g['id'])
                self.group_list_widget.addItem(item)

        elif dtype in ["create_group_response", "join_group_response"]:
            if data['status'] == 'success':
                # 成功加入或创建，立即获取房间详情（详情响应会设置 self.current_group_name）
                self.enter_room_view(data['group_id'], data.get('group_name', STRINGS["lbl_loading"]), self.my_user_id)
                self.refresh_current_group_data()
            else:
                self._handle_group_error(data)

        elif dtype == "leave_group_response":
            QMessageBox.information(self, STRINGS["success_title"], STRINGS["msg_leave_success"])
            self.leave_room()  # 执行UI清理

        elif dtype == "group_detail_response":
            if self.current_group_id != data['group_id']: return

            # 房间名称可能在恢复房间状态时被设置为 Loading...，这里更新
            self.current_group_name = data['name']
            self.lbl_room_name.setText(STRINGS["lbl_room_name_fmt"].format(data['name']))

            self.is_group_owner = (data['owner_id'] == self.my_user_id)
            if self.is_group_owner:
                self.sprint_ctrl_frame.show()
            else:
                self.sprint_ctrl_frame.hide()

            if data['sprint_active']:
                self.lbl_sprint_status.setText(STRINGS["status_sprint_active_fmt"].format(data['sprint_target']))
                self.lbl_sprint_status.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.lbl_sprint_status.setText(STRINGS["status_sprint_inactive"])
                self.lbl_sprint_status.setStyleSheet("color: gray;")

            html = ""
            for msg in data['chat_history']:
                try:
                    ts = float(msg.get('time', 0))
                    local_time = datetime.fromtimestamp(ts).strftime("%H:%M")
                except:
                    local_time = "??:??"

                # 确保 sender 和 content 存在
                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')

                html += f"<p><b>[{local_time}] {sender}:</b> {content}</p>"

            self.chat_display.setHtml(html)
            self.chat_display.moveCursor(self.chat_display.textCursor().MoveOperation.End)

            if self.float_group_win:
                self.float_group_win.update_chat(html)

            self.rank_list.clear()
            rank_data_for_float = []
            for idx, r in enumerate(data['leaderboard']):
                prefix = f"#{idx + 1}"
                color = "black"
                if r['reached_target']:
                    color = "green"
                elif idx == 0 and r['word_count'] > 0:
                    color = "orange"

                text = f"{prefix} {r['nickname']}: {r['word_count']}"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor(color)))
                if r['reached_target']:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self.rank_list.addItem(item)
                rank_data_for_float.append((text, "green" if r['reached_target'] else (
                    "orange" if idx == 0 and r['word_count'] > 0 else "white")))

            if self.float_group_win:
                self.float_group_win.update_rank(rank_data_for_float)

        elif dtype == "group_msg_push":
            if self.current_group_id == data['group_id']:
                try:
                    ts = float(data.get('time', 0))
                    local_time = datetime.fromtimestamp(ts).strftime("%H:%M")
                except:
                    local_time = "??:??"

                line = f"<p><b>[{local_time}] {data['sender']}:</b> {data['content']}</p>"
                self.chat_display.append(line)
                if self.float_group_win:
                    self.float_group_win.append_chat(line)

        elif dtype == "sprint_status_push":
            if self.current_group_id == data['group_id']:
                self.refresh_current_group_data()  # 排行榜有更新，重新请求详情

    def _handle_group_error(self, data):
        msg = data.get('msg', STRINGS["msg_unknown_err"])

        # 处理单人群组限制的错误
        if "You are already in another group" in msg and 'current_group_id' in data:
            gid = data['current_group_id']
            # 用户已经在另一个房间，提醒用户是否要进入该房间
            reply = QMessageBox.question(self, STRINGS["warn_title"],
                                         STRINGS["msg_in_other_room"].format(gid),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # 重新进入旧房间（无需网络请求，直接进入UI，并请求刷新详情）
                self.enter_room_view(gid, STRINGS["lbl_loading"], 0)
                self.refresh_current_group_data()
            else:
                # 允许用户停留在大厅界面
                pass
        else:
            QMessageBox.warning(self, STRINGS["msg_failed"], msg)