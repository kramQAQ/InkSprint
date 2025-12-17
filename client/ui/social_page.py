from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QTabWidget,
                             QInputDialog, QMessageBox, QFrame, QSplitter, QTextEdit,
                             QCheckBox, QDialog, QFormLayout, QSpinBox, QStackedWidget,
                             QSizePolicy, QButtonGroup, QGraphicsDropShadowEffect, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QBrush, QFont, QPixmap, QIcon, QAction
import base64
from datetime import datetime
from .float_group_window import FloatGroupWindow
from .localization import STRINGS


# --- 【自定义 UI 组件】卡片式 Item ---

class FriendItemWidget(QWidget):
    def __init__(self, avatar_data, nickname, username, signature, is_online):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 头像
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(40, 40)
        self.lbl_avatar.setStyleSheet("background-color: #ddd; border-radius: 20px;")
        self.lbl_avatar.setScaledContents(True)
        if avatar_data:
            try:
                pix = QPixmap()
                pix.loadFromData(base64.b64decode(avatar_data))
                self.lbl_avatar.setPixmap(pix)
            except:
                pass

        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_line = QHBoxLayout()
        lbl_nick = QLabel(nickname)
        lbl_nick.setStyleSheet("font-weight: bold; font-size: 14px;")
        lbl_uid = QLabel(f"@{username}")
        lbl_uid.setStyleSheet("color: #888; font-size: 12px;")
        name_line.addWidget(lbl_nick)
        name_line.addWidget(lbl_uid)
        name_line.addStretch()

        lbl_sig = QLabel(signature if signature else "No signature")
        lbl_sig.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")

        info_layout.addLayout(name_line)
        info_layout.addWidget(lbl_sig)

        # 在线状态点
        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {'#40C463' if is_online else '#ccc'}; font-size: 12px;")

        layout.addWidget(self.lbl_avatar)
        layout.addLayout(info_layout)
        layout.addWidget(status_dot)


class GroupItemWidget(QWidget):
    def __init__(self, group_id, name, owner_name, member_count, updated_at, has_password, sprint_active, is_private):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 第一行：房间名 + 锁图标
        top = QHBoxLayout()
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("font-weight: bold; font-size: 16px;")
        top.addWidget(lbl_name)

        if has_password:
            lbl_lock = QLabel("🔒")
            top.addWidget(lbl_lock)

        if is_private:
            lbl_priv = QLabel("👁️‍🗨️")
            top.addWidget(lbl_priv)

        top.addStretch()

        # 状态标签
        if sprint_active:
            lbl_status = QLabel("🔥 拼字中")
            lbl_status.setStyleSheet(
                "background-color: #ffeaea; color: #d63031; padding: 2px 5px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            top.addWidget(lbl_status)
        else:
            lbl_status = QLabel("🟢 可加入")
            lbl_status.setStyleSheet(
                "background-color: #eafef1; color: #27ae60; padding: 2px 5px; border-radius: 4px; font-size: 10px;")
            top.addWidget(lbl_status)

        # 第二行：ID | 房主 | 人数 | 时间
        bottom = QHBoxLayout()
        info_text = f"ID: {group_id} | 房主: {owner_name} | 👥 {member_count}/10"
        lbl_info = QLabel(info_text)
        lbl_info.setStyleSheet("color: #666; font-size: 12px;")

        lbl_time = QLabel(updated_at)
        lbl_time.setStyleSheet("color: #999; font-size: 11px;")

        bottom.addWidget(lbl_info)
        bottom.addStretch()
        bottom.addWidget(lbl_time)

        layout.addLayout(top)
        layout.addLayout(bottom)


class SocialPage(QWidget):
    def __init__(self, network_manager, user_id=0):
        super().__init__()
        self.network = network_manager
        self.my_user_id = user_id

        self.current_group_id = None
        self.is_group_owner = False
        self.current_group_name = None

        self.float_group_win = None

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
        self.lbl_owner_avatar = None

        self.btn_friend_requests = None
        self.btn_group = None

        self.setup_ui()

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(20000)
        self.update_timer.timeout.connect(self.refresh_current_group_data)

        self.list_timer = QTimer(self)
        self.list_timer.setInterval(60000)  # 改为1分钟刷新一次列表
        self.list_timer.timeout.connect(self.refresh_group_list)
        if self.my_user_id > 0:
            self.list_timer.start()

    def set_user_id(self, user_id):
        self.my_user_id = user_id
        if self.my_user_id > 0:
            if not self.list_timer.isActive():
                self.list_timer.start()
            if not self.current_group_id:
                self.refresh_group_list()

    def restore_group_state(self, group_info):
        print(f"[Social] Attempting restore group: {group_info}")
        if group_info and 'id' in group_info:
            gid = group_info['id']
            name = group_info.get('name', STRINGS["lbl_loading"])
            owner_id = group_info.get('owner_id', 0)
            self.enter_room_view(gid, name, owner_id)
            self.refresh_current_group_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # --- Top Switch Buttons ---
        top_bar = QFrame()
        top_bar.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.btn_group = QButtonGroup(self)
        self.btn_tab_groups = QPushButton(STRINGS["tab_groups"])
        self.btn_tab_friends = QPushButton(STRINGS["tab_friends"])

        for idx, btn in enumerate([self.btn_tab_groups, self.btn_tab_friends]):
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: transparent;
                    font-weight: bold;
                    font-size: 16px;
                    border-bottom: 3px solid transparent;
                    color: #888;
                }
                QPushButton:checked {
                    color: #9DC88D;
                    border-bottom: 3px solid #9DC88D;
                }
                QPushButton:hover { color: #666; }
            """)
            self.btn_group.addButton(btn, idx)
            top_layout.addWidget(btn)
            btn.clicked.connect(lambda _, i=idx: self.main_stack.setCurrentIndex(i))

        layout.addWidget(top_bar)

        self.main_stack = QStackedWidget()
        self.main_stack.addWidget(self.create_groups_tab())
        self.main_stack.addWidget(self.create_friends_tab())
        layout.addWidget(self.main_stack)

        self.btn_tab_groups.setChecked(True)
        self.main_stack.setCurrentIndex(0)

    def create_friends_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(STRINGS["search_placeholder"])
        self.search_input.setFixedHeight(35)

        btn_style = """
            QPushButton { background-color: white; border: 1px solid #ddd; border-radius: 5px; padding: 5px 15px; }
            QPushButton:hover { background-color: #f5f5f5; }
        """

        btn_search = QPushButton(STRINGS["btn_search_user"])
        btn_search.clicked.connect(self.search_user_to_add)
        btn_search.setStyleSheet(btn_style)

        self.btn_friend_requests = QPushButton(STRINGS["btn_friend_reqs"])
        self.btn_friend_requests.clicked.connect(self.show_friend_requests)
        self.btn_friend_requests.setStyleSheet(btn_style)

        btn_refresh = QPushButton(STRINGS["btn_refresh_list"])
        btn_refresh.clicked.connect(self.load_friends)
        btn_refresh.setStyleSheet(btn_style)

        top.addWidget(self.search_input)
        top.addWidget(btn_search)
        top.addWidget(self.btn_friend_requests)
        top.addWidget(btn_refresh)
        layout.addLayout(top)

        # 【修改】开启右键菜单
        self.friend_list = QListWidget()
        self.friend_list.setStyleSheet("QListWidget { border: none; background: transparent; }")
        self.friend_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.friend_list.customContextMenuRequested.connect(self.show_friend_context_menu)
        layout.addWidget(self.friend_list)

        return widget

    def show_friend_context_menu(self, pos):
        item = self.friend_list.itemAt(pos)
        if not item: return

        friend_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu()
        del_action = QAction("🗑️ 删除好友", self)
        del_action.triggered.connect(lambda: self.delete_friend(friend_id))
        menu.addAction(del_action)

        menu.exec(self.friend_list.mapToGlobal(pos))

    def delete_friend(self, friend_id):
        reply = QMessageBox.question(self, "确认", "确定要删除该好友吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.network.send_request({"type": "delete_friend", "friend_id": friend_id})

    def search_user_to_add(self):
        query = self.search_input.text().strip()
        if not query: return
        self.network.send_request({"type": "search_user", "query": query})

    def create_groups_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 0, 20, 20)

        self.group_stack = QStackedWidget()

        # 1. Lobby
        self.lobby_widget = QWidget()
        lobby_layout = QVBoxLayout(self.lobby_widget)
        lobby_layout.setSpacing(15)

        l_top = QHBoxLayout()
        btn_create = QPushButton(STRINGS["btn_create_group"])
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.clicked.connect(self.show_create_group_dialog)

        btn_refresh_g = QPushButton(STRINGS["btn_refresh_lobby"])
        btn_refresh_g.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_g.clicked.connect(self.refresh_group_list)

        for btn in [btn_create, btn_refresh_g]:
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton { background-color: white; border: 1px solid #ddd; border-radius: 8px; font-weight: bold; color: #555; padding: 0 15px; }
                QPushButton:hover { background-color: #f0f0f0; color: #333; }
            """)

        l_top.addWidget(btn_create)
        l_top.addWidget(btn_refresh_g)
        l_top.addStretch()
        lobby_layout.addLayout(l_top)

        self.group_list_widget = QListWidget()
        self.group_list_widget.setStyleSheet("QListWidget { background: transparent; border: none; }")
        self.group_list_widget.itemDoubleClicked.connect(self.join_selected_group)
        lobby_layout.addWidget(self.group_list_widget)

        # 2. Active Room (UI Refined)
        self.room_widget = QWidget()
        room_layout = QVBoxLayout(self.room_widget)
        room_layout.setSpacing(15)

        # Room Card Container
        room_card = QFrame()
        room_card.setStyleSheet("QFrame { background: white; border-radius: 15px; }")
        room_card_layout = QVBoxLayout(room_card)
        room_card_layout.setContentsMargins(20, 20, 20, 20)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        room_card.setGraphicsEffect(shadow)

        # Header
        r_header = QHBoxLayout()

        # 房主头像
        self.lbl_owner_avatar = QLabel()
        self.lbl_owner_avatar.setFixedSize(40, 40)
        self.lbl_owner_avatar.setStyleSheet("background: #eee; border-radius: 20px; border: 2px solid #9DC88D;")
        self.lbl_owner_avatar.setScaledContents(True)
        r_header.addWidget(self.lbl_owner_avatar)

        self.lbl_room_name = QLabel("Room Name")
        self.lbl_room_name.setStyleSheet("font-size: 20px; font-weight: 800; color: #333; background: transparent;")

        btn_leave = QPushButton(STRINGS["btn_leave_room"])
        btn_leave.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_leave.setStyleSheet(
            "QPushButton { background-color: #ffeaea; color: #d63031; border-radius: 8px; padding: 5px 10px; font-weight: bold; border: none; } QPushButton:hover { background-color: #ffcccc; }")
        btn_leave.clicked.connect(self.leave_room_confirm)

        float_btns_layout = QHBoxLayout()
        for txt, cb in [(STRINGS["btn_float_chat"], lambda: self.toggle_float_window("chat")),
                        (STRINGS["btn_float_rank"], lambda: self.toggle_float_window("rank"))]:
            b = QPushButton(txt)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(cb)
            b.setStyleSheet(
                "QPushButton { background: #f0f0f0; border-radius: 8px; padding: 5px 10px; color: #555; border: none; } QPushButton:hover { background: #e0e0e0; }")
            float_btns_layout.addWidget(b)

        r_header.addWidget(self.lbl_room_name)
        r_header.addStretch()
        r_header.addLayout(float_btns_layout)
        r_header.addSpacing(10)
        r_header.addWidget(btn_leave)
        room_card_layout.addLayout(r_header)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #eee;")
        room_card_layout.addWidget(div)

        # Content Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #eee; }")

        # Chat Area
        chat_container = QWidget()
        chat_v = QVBoxLayout(chat_container)
        chat_v.setContentsMargins(0, 0, 10, 0)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "background: #fdfdfd; border: 1px solid #eee; border-radius: 8px; padding: 5px;")

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(STRINGS["chat_placeholder"])
        self.chat_input.setFixedHeight(40)
        self.chat_input.setStyleSheet(
            "background: #fdfdfd; border: 1px solid #ddd; border-radius: 20px; padding: 0 15px;")
        self.chat_input.returnPressed.connect(self.send_chat_message)

        btn_send = QPushButton(STRINGS["btn_send"])
        btn_send.setFixedSize(60, 40)
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setStyleSheet(
            "background: #9DC88D; color: white; border-radius: 20px; font-weight: bold; border: none;")
        btn_send.clicked.connect(self.send_chat_message)

        input_h = QHBoxLayout()
        input_h.addWidget(self.chat_input)
        input_h.addWidget(btn_send)

        chat_v.addWidget(self.chat_display)
        chat_v.addLayout(input_h)

        # Rank Area
        rank_container = QWidget()
        rank_v = QVBoxLayout(rank_container)
        rank_v.setContentsMargins(10, 0, 0, 0)

        # Control Panel
        self.sprint_ctrl_frame = QFrame()
        self.sprint_ctrl_frame.setStyleSheet("background: #f9f9f9; border-radius: 10px; padding: 10px;")
        sprint_l = QVBoxLayout(self.sprint_ctrl_frame)

        self.lbl_sprint_status = QLabel(STRINGS["status_sprint_inactive"])
        self.lbl_sprint_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sprint_status.setStyleSheet("font-weight: bold; color: #555; background: transparent;")

        ctrl_label = QLabel(STRINGS["lbl_owner_ctrl"])
        ctrl_label.setStyleSheet("color: #888; font-size: 12px; font-weight: bold; background: transparent;")

        self.btn_start_sprint = QPushButton(STRINGS["btn_start_sprint"])
        self.btn_start_sprint.clicked.connect(self.start_sprint_dialog)
        self.btn_start_sprint.setStyleSheet(
            "background: #9DC88D; color: white; border-radius: 5px; padding: 5px; font-weight: bold; border: none;")

        self.btn_stop_sprint = QPushButton(STRINGS["btn_stop_sprint"])
        self.btn_stop_sprint.clicked.connect(self.stop_sprint)
        self.btn_stop_sprint.setStyleSheet(
            "background: #e74c3c; color: white; border-radius: 5px; padding: 5px; font-weight: bold; border: none;")

        sprint_l.addWidget(ctrl_label)
        sprint_l.addWidget(self.lbl_sprint_status)
        sprint_l.addWidget(self.btn_start_sprint)
        sprint_l.addWidget(self.btn_stop_sprint)
        self.sprint_ctrl_frame.hide()

        # 【修改】开启排行榜右键菜单
        self.rank_list = QListWidget()
        self.rank_list.setStyleSheet(
            "QListWidget { background: transparent; border: none; } QListWidget::item { padding: 5px; }")
        self.rank_list.setIconSize(QSize(32, 32))
        self.rank_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rank_list.customContextMenuRequested.connect(self.show_rank_context_menu)

        rank_v.addWidget(self.sprint_ctrl_frame)
        rank_v.addWidget(QLabel(STRINGS["lbl_leaderboard"]))
        rank_v.addWidget(self.rank_list)
        rank_v.addStretch()

        splitter.addWidget(chat_container)
        splitter.addWidget(rank_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        room_card_layout.addWidget(splitter)
        room_layout.addWidget(room_card)

        self.group_stack.addWidget(self.lobby_widget)
        self.group_stack.addWidget(self.room_widget)

        main_layout.addWidget(self.group_stack)
        return widget

    def show_rank_context_menu(self, pos):
        item = self.rank_list.itemAt(pos)
        if not item: return

        user_id = item.data(Qt.ItemDataRole.UserRole)
        # 不能加自己
        if user_id == self.my_user_id: return

        menu = QMenu()
        add_friend_action = QAction("➕ 加为好友", self)
        add_friend_action.triggered.connect(lambda: self.add_friend_request(user_id))
        menu.addAction(add_friend_action)

        menu.exec(self.rank_list.mapToGlobal(pos))

    def load_friends(self):
        if self.my_user_id > 0:
            print("[Social] Sending get_friends request...")
            self.network.send_request({"type": "get_friends"})

    def show_friend_requests(self):
        self.network.send_request({"type": "get_friend_requests"})
        if self.btn_friend_requests:
            self.btn_friend_requests.setStyleSheet(
                "background-color: white; border: 1px solid #ddd; border-radius: 5px; padding: 5px 15px;")

    def add_friend_request(self, friend_id):
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

    def refresh_group_list(self):
        if self.my_user_id > 0:
            print("[Social] Sending get_public_groups request...")
            self.network.send_request({"type": "get_public_groups"})

    def show_create_group_dialog(self):
        # 创建一个自定义 Dialog 包含 名称、密码、私密 选项
        dlg = QDialog(self)
        dlg.setWindowTitle(STRINGS["dialog_create_group_title"])
        layout = QFormLayout(dlg)

        name_edit = QLineEdit()
        layout.addRow(STRINGS["dialog_group_name_label"], name_edit)

        pwd_edit = QLineEdit()
        pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_edit.setPlaceholderText("可选，留空则公开")
        layout.addRow("房间密码:", pwd_edit)

        private_check = QCheckBox("私密房间 (仅好友可见)")
        layout.addRow("", private_check)

        btns = QHBoxLayout()
        btn_ok = QPushButton("创建")
        btn_ok.clicked.connect(dlg.accept)
        btns.addWidget(btn_ok)
        layout.addRow(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if name:
                self.network.send_request({
                    "type": "create_group",
                    "name": name,
                    "is_private": private_check.isChecked(),
                    "password": pwd_edit.text().strip()
                })

    def join_selected_group(self, item):
        group_id = item.data(Qt.ItemDataRole.UserRole)
        is_sprint = item.data(Qt.ItemDataRole.UserRole + 1)
        has_password = item.data(Qt.ItemDataRole.UserRole + 2)

        if is_sprint:
            QMessageBox.warning(self, "无法加入", "该房间正在拼字中，请稍后再试。")
            return

        pwd = ""
        if has_password:
            text, ok = QInputDialog.getText(self, "输入密码", "该房间已上锁，请输入密码:", QLineEdit.EchoMode.Password)
            if not ok: return
            pwd = text.strip()

        if group_id is not None:
            self.network.send_request({"type": "join_group", "group_id": group_id, "password": pwd})

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

        # 重置房主头像显示
        self.lbl_owner_avatar.clear()
        self.lbl_owner_avatar.setStyleSheet("background: #eee; border-radius: 20px;")

        self.refresh_current_group_data()
        self.update_timer.start()

    def leave_room_confirm(self):
        msg = STRINGS["msg_leave_confirm"].format(self.current_group_name or self.current_group_id)
        if self.is_group_owner:
            msg += "\n\n⚠️ 警告：你是房主，离开后房间将自动解散！"

        reply = QMessageBox.question(self, STRINGS["confirm_title"], msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.leave_room()

    def leave_room(self):
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

    def handle_network_msg(self, data):
        dtype = data.get("type")

        if dtype == "search_user_response":
            if data['status'] == 'success':
                u = data['data']
                reply = QMessageBox.question(self, STRINGS["msg_found_user_title"],
                                             STRINGS["msg_add_confirm_fmt"].format(u['nickname'], u['username']),
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.add_friend_request(u['id'])
            else:
                QMessageBox.warning(self, STRINGS["msg_not_found_title"], STRINGS["msg_user_not_found"])

        elif dtype == "refresh_friends":
            self.load_friends()
            # QMessageBox.information(self, STRINGS["success_title"], STRINGS["msg_friend_list_updated"]) # 避免频繁弹窗

        elif dtype == "refresh_friend_requests":
            if self.btn_friend_requests:
                self.btn_friend_requests.setStyleSheet(
                    "background-color: #ff6b6b; color: white; border-radius: 5px; padding: 5px 15px; font-weight: bold;")
            QMessageBox.information(self, STRINGS["warn_title"], STRINGS["msg_new_req"])

        elif dtype == "friend_requests_response":
            self.open_request_dialog(data.get("data", []))

        elif dtype == "get_friends_response":
            print(f"[Social] Received friends: {data.get('data')}")
            self.friend_list.clear()
            for f in data.get("data", []):
                # 使用自定义 Widget
                item = QListWidgetItem(self.friend_list)
                item.setSizeHint(QSize(200, 60))
                item.setData(Qt.ItemDataRole.UserRole, f['id'])

                widget = FriendItemWidget(
                    f.get('avatar_data'),
                    f['nickname'],
                    f['username'],
                    f.get('signature', ''),
                    f['status'] == 'Online'
                )
                self.friend_list.setItemWidget(item, widget)

        elif dtype == "refresh_groups":
            self.refresh_group_list()

        elif dtype == "group_list_response":
            self.group_list_widget.clear()
            for g in data.get("data", []):
                item = QListWidgetItem(self.group_list_widget)
                item.setSizeHint(QSize(200, 70))
                item.setData(Qt.ItemDataRole.UserRole, g['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, g['sprint_active'])
                item.setData(Qt.ItemDataRole.UserRole + 2, g['has_password'])

                widget = GroupItemWidget(
                    g['id'],
                    g['name'],
                    g['owner_name'],
                    g['member_count'],
                    g['updated_at'],
                    g['has_password'],
                    g['sprint_active'],
                    g['is_private']
                )
                self.group_list_widget.setItemWidget(item, widget)

        elif dtype in ["create_group_response", "join_group_response"]:
            if data['status'] == 'success':
                self.enter_room_view(data['group_id'], data.get('group_name', STRINGS["lbl_loading"]), self.my_user_id)
                self.refresh_current_group_data()
            else:
                self._handle_group_error(data)

        elif dtype == "group_disbanded":
            if self.current_group_id == data.get('group_id'):
                QMessageBox.warning(self, STRINGS["warn_title"], "房间已被房主解散。")
                self.leave_room()

        elif dtype == "leave_group_response":
            if data.get("msg") == "Group disbanded":
                QMessageBox.information(self, STRINGS["success_title"], "房间已解散。")
            else:
                pass  # 静默离开
            self.leave_room()

        elif dtype == "group_detail_response":
            if self.current_group_id != data['group_id']: return

            self.current_group_name = data['name']
            self.lbl_room_name.setText(STRINGS["lbl_room_name_fmt"].format(data['name']))

            # 更新房主头像
            owner_av_b64 = data.get('owner_avatar', '')
            if owner_av_b64:
                try:
                    pix = QPixmap()
                    pix.loadFromData(base64.b64decode(owner_av_b64))
                    self.lbl_owner_avatar.setPixmap(pix)
                except:
                    pass

            self.is_group_owner = (data['owner_id'] == self.my_user_id)
            if self.is_group_owner:
                self.sprint_ctrl_frame.show()
            else:
                self.sprint_ctrl_frame.hide()

            if data['sprint_active']:
                self.lbl_sprint_status.setText(STRINGS["status_sprint_active_fmt"].format(data['sprint_target']))
                self.lbl_sprint_status.setStyleSheet(
                    "color: #e67e22; font-weight: bold; font-size: 14px; background: transparent;")
            else:
                self.lbl_sprint_status.setText(STRINGS["status_sprint_inactive"])
                self.lbl_sprint_status.setStyleSheet("color: #7f8c8d; font-size: 14px; background: transparent;")

            html = ""
            for msg in data['chat_history']:
                try:
                    ts = float(msg.get('time', 0))
                    local_time = datetime.fromtimestamp(ts).strftime("%H:%M")
                except:
                    local_time = "??:??"

                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')

                if sender == "SYSTEM":
                    html += f"<p style='color: #888; text-align: center; font-size: 12px;'><i>[{local_time}] {content}</i></p>"
                else:
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
                    color = "#27ae60"  # Green
                elif idx == 0 and r['word_count'] > 0:
                    color = "#d35400"  # Orange

                text = f"{prefix} {r['nickname']}: {r['word_count']}"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor(color)))
                item.setData(Qt.ItemDataRole.UserRole, r['user_id'])  # 存储 ID 供右键使用

                if r['reached_target']:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                if r.get('avatar_data'):
                    try:
                        pix = QPixmap()
                        pix.loadFromData(base64.b64decode(r['avatar_data']))
                        icon = QIcon(pix)
                        item.setIcon(icon)
                    except:
                        pass

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

                if data['sender'] == "SYSTEM":
                    line = f"<p style='color: #888; text-align: center; font-size: 12px;'><i>[{local_time}] {data['content']}</i></p>"
                else:
                    line = f"<p><b>[{local_time}] {data['sender']}:</b> {data['content']}</p>"

                self.chat_display.append(line)
                if self.float_group_win:
                    self.float_group_win.append_chat(line)

        elif dtype == "sprint_status_push":
            if self.current_group_id == data['group_id']:
                self.refresh_current_group_data()

    def _handle_group_error(self, data):
        msg = data.get('msg', STRINGS["msg_unknown_err"])

        # 处理密码错误
        if data.get("need_password"):
            text, ok = QInputDialog.getText(self, "输入密码", "密码错误，请重新输入:", QLineEdit.EchoMode.Password)
            if ok and text:
                self.network.send_request({"type": "join_group", "group_id": data.get(
                    "current_group_id") or self.group_list_widget.currentItem().data(Qt.ItemDataRole.UserRole),
                                           "password": text.strip()})
            return

        if "You are already in another group" in msg and 'current_group_id' in data:
            gid = data['current_group_id']
            reply = QMessageBox.question(self, STRINGS["warn_title"],
                                         STRINGS["msg_in_other_room"].format(gid),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.enter_room_view(gid, STRINGS["lbl_loading"], 0)
                self.refresh_current_group_data()
            else:
                pass
        else:
            QMessageBox.warning(self, STRINGS["msg_failed"], msg)