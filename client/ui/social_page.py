from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QTabWidget,
                             QInputDialog, QMessageBox, QFrame, QSplitter, QTextEdit,
                             QCheckBox, QDialog, QFormLayout, QSpinBox, QStackedWidget,
                             QSizePolicy, QButtonGroup)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from .float_group_window import FloatGroupWindow


class SocialPage(QWidget):
    def __init__(self, network_manager, user_id=0):
        super().__init__()
        self.network = network_manager
        self.my_user_id = user_id

        self.current_group_id = None
        self.is_group_owner = False

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
        if self.my_user_id > 0 and not self.list_timer.isActive():
            self.list_timer.start()
            self.refresh_group_list()

    def restore_group_state(self, group_info):
        """登录时如果已经在群里，直接恢复到群界面"""
        print(f"[Social] Attempting restore group: {group_info}")
        if group_info and 'id' in group_info:
            gid = group_info['id']
            name = group_info.get('name', 'Unknown Room')
            owner_id = group_info.get('owner_id', 0)
            self.enter_room_view(gid, name, owner_id)

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
        self.btn_tab_groups = QPushButton("💬 Groups")
        self.btn_tab_friends = QPushButton("👥 Friends")

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
        self.search_input.setPlaceholderText("Search User ID or Name")
        btn_search = QPushButton("Add Friend")
        btn_search.clicked.connect(self.search_and_add_friend)

        self.btn_friend_requests = QPushButton("Friend Requests")
        self.btn_friend_requests.clicked.connect(self.show_friend_requests)

        btn_refresh = QPushButton("Refresh List")
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

    def create_groups_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.group_stack = QStackedWidget()

        # 1. Lobby
        self.lobby_widget = QWidget()
        lobby_layout = QVBoxLayout(self.lobby_widget)

        l_top = QHBoxLayout()
        btn_create = QPushButton("➕ Create Group")
        btn_create.clicked.connect(self.show_create_group_dialog)
        btn_refresh_g = QPushButton("🔄 Refresh Lobby")
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

        btn_leave = QPushButton("Leave Room")
        btn_leave.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        btn_leave.clicked.connect(self.leave_room)

        btn_float_chat = QPushButton("Float Chat")
        btn_float_chat.clicked.connect(lambda: self.toggle_float_window("chat"))
        btn_float_rank = QPushButton("Float Rank")
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
        self.chat_input.setPlaceholderText("Type message...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        btn_send = QPushButton("Send")
        btn_send.clicked.connect(self.send_chat_message)

        input_h = QHBoxLayout()
        input_h.addWidget(self.chat_input)
        input_h.addWidget(btn_send)

        chat_v.addWidget(self.chat_display)
        chat_v.addLayout(input_h)

        rank_container = QWidget()
        rank_v = QVBoxLayout(rank_container)

        self.sprint_ctrl_frame = QFrame()
        sprint_l = QVBoxLayout(self.sprint_ctrl_frame)
        self.btn_start_sprint = QPushButton("Start Sprint")
        self.btn_start_sprint.clicked.connect(self.start_sprint_dialog)
        self.btn_stop_sprint = QPushButton("Stop Sprint")
        self.btn_stop_sprint.clicked.connect(self.stop_sprint)
        self.lbl_sprint_status = QLabel("Sprint: Inactive")

        sprint_l.addWidget(QLabel("Owner Controls"))
        sprint_l.addWidget(self.lbl_sprint_status)
        sprint_l.addWidget(self.btn_start_sprint)
        sprint_l.addWidget(self.btn_stop_sprint)
        self.sprint_ctrl_frame.hide()

        self.rank_list = QListWidget()

        rank_v.addWidget(QLabel("🏆 Leaderboard"))
        rank_v.addWidget(self.rank_list)
        rank_v.addWidget(self.sprint_ctrl_frame)

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
        if self.my_user_id > 0:
            print("[Social] Sending get_friends request...")
            self.network.send_request({"type": "get_friends"})

    def search_and_add_friend(self):
        query = self.search_input.text().strip()
        if not query: return
        self.network.send_request({"type": "search_user", "query": query})

    def show_friend_requests(self):
        self.network.send_request({"type": "get_friend_requests"})
        # 恢复按钮样式
        if self.btn_friend_requests:
            self.btn_friend_requests.setStyleSheet("")

    def open_request_dialog(self, requests):
        dlg = QDialog(self)
        dlg.setWindowTitle("Friend Requests")
        dlg.resize(400, 300)
        vbox = QVBoxLayout(dlg)

        lst = QListWidget()
        if not requests:
            lst.addItem("No pending requests.")

        for r in requests:
            text = f"{r['nickname']} ({r['username']})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r['request_id'])
            lst.addItem(item)

        vbox.addWidget(QLabel("Double click to respond:"))
        vbox.addWidget(lst)

        def on_item_dbl_click(item):
            req_id = item.data(Qt.ItemDataRole.UserRole)
            if not req_id: return

            reply = QMessageBox.question(dlg, "Respond", f"Accept request from {item.text()}?",
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
        if self.my_user_id > 0:
            self.network.send_request({"type": "get_public_groups"})

    def show_create_group_dialog(self):
        name, ok = QInputDialog.getText(self, "Create Group", "Group Name:")
        if ok and name:
            reply = QMessageBox.question(self, "Private?", "Make this group private?",
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
        self.is_group_owner = (owner_id == self.my_user_id)
        if self.lbl_room_name:
            self.lbl_room_name.setText(f"Room: {name}")
        self.group_stack.setCurrentIndex(1)

        if self.is_group_owner:
            self.sprint_ctrl_frame.show()
        else:
            self.sprint_ctrl_frame.hide()

        self.chat_display.clear()
        self.rank_list.clear()

        self.refresh_current_group_data()
        self.update_timer.start()

    def leave_room(self):
        if self.current_group_id:
            self.network.send_request({"type": "leave_group", "group_id": self.current_group_id})

        self.update_timer.stop()
        self.current_group_id = None
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
        target, ok = QInputDialog.getInt(self, "Start Sprint", "Target Words:", 500, 10, 100000)
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
                reply = QMessageBox.question(self, "Found User", f"Add {u['nickname']} ({u['username']}) as friend?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.network.send_request({"type": "add_friend", "friend_id": u['id']})
            else:
                QMessageBox.warning(self, "Not Found", "User not found.")

        elif dtype == "refresh_friends":
            self.load_friends()

        elif dtype == "refresh_friend_requests":
            if self.btn_friend_requests:
                self.btn_friend_requests.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
            QMessageBox.information(self, "Notification", "You have a new friend request!")

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

        elif dtype == "create_group_response":
            if data['status'] == 'success':
                if 'group_id' in data:
                    self.enter_room_view(data['group_id'], data.get('group_name', 'New Group'), self.my_user_id)
            else:
                self._handle_group_error(data)

        elif dtype == "join_group_response":
            if data['status'] == 'success':
                self.enter_room_view(data['group_id'], "Loading...", 0)
            else:
                self._handle_group_error(data)

        elif dtype == "group_detail_response":
            if self.current_group_id != data['group_id']: return

            self.lbl_room_name.setText(f"Room: {data['name']}")
            self.is_group_owner = (data['owner_id'] == self.my_user_id)
            if self.is_group_owner:
                self.sprint_ctrl_frame.show()
            else:
                self.sprint_ctrl_frame.hide()

            if data['sprint_active']:
                self.lbl_sprint_status.setText(f"🔥 Sprint: {data['sprint_target']} words")
                self.lbl_sprint_status.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.lbl_sprint_status.setText("Sprint: Inactive")
                self.lbl_sprint_status.setStyleSheet("color: gray;")

            html = ""
            for msg in data['chat_history']:
                html += f"<p><b>[{msg['time']}] {msg['sender']}:</b> {msg['content']}</p>"
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
                line = f"<p><b>[{data['time']}] {data['sender']}:</b> {data['content']}</p>"
                self.chat_display.append(line)
                if self.float_group_win:
                    self.float_group_win.append_chat(line)

        elif dtype == "sprint_status_push":
            if self.current_group_id == data['group_id']:
                self.refresh_current_group_data()

    def _handle_group_error(self, data):
        if 'current_group_id' in data:
            gid = data['current_group_id']
            self.enter_room_view(gid, "Restoring Room...", 0)
        else:
            QMessageBox.warning(self, "Failed", data.get('msg', 'Unknown error'))