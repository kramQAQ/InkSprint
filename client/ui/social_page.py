from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QTabWidget,
                             QInputDialog, QMessageBox, QFrame, QSplitter, QTextEdit,
                             QCheckBox, QDialog, QFormLayout, QSpinBox, QStackedWidget,
                             QSizePolicy, QButtonGroup, QGraphicsDropShadowEffect, QScrollArea,
                             QGridLayout, QMenu)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QColor, QBrush, QFont, QPixmap, QIcon, QPainter, QPainterPath
import base64
from datetime import datetime
from .float_group_window import FloatGroupWindow
from .localization import STRINGS


class FlowLayout(QGridLayout):
    """简单的流式布局 (Grid based)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items_list = []

    def add_widget(self, widget):
        self.items_list.append(widget)
        self.reflow()

    def clear_widgets(self):
        for w in self.items_list:
            w.setParent(None)
            w.deleteLater()
        self.items_list = []

    def reflow(self, width=None):
        # 简单实现：假定每行2列或3列，取决于宽度
        # 这里简化为固定列数，自适应宽度
        cols = 2
        for i, w in enumerate(self.items_list):
            row = i // cols
            col = i % cols
            self.addWidget(w, row, col)


class FriendCard(QFrame):
    """好友卡片组件"""
    delete_clicked = pyqtSignal(int, str)  # id, name

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            FriendCard { background-color: white; border-radius: 10px; border: 1px solid #eee; }
            FriendCard:hover { background-color: #f9f9f9; border: 1px solid #ddd; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 头像
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(50, 50)
        self.lbl_avatar.setStyleSheet("background: #eee; border-radius: 25px;")
        self.lbl_avatar.setScaledContents(True)
        self.load_avatar(self.data.get('avatar_data'))
        layout.addWidget(self.lbl_avatar)

        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_layout = QHBoxLayout()
        lbl_nick = QLabel(self.data['nickname'])
        lbl_nick.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        lbl_id = QLabel(f"@{self.data['username']}")
        lbl_id.setStyleSheet("color: #888; font-size: 12px;")
        name_layout.addWidget(lbl_nick)
        name_layout.addWidget(lbl_id)
        name_layout.addStretch()

        lbl_sig = QLabel(self.data.get('signature') or "No signature")
        lbl_sig.setStyleSheet("color: #666; font-style: italic; font-size: 13px;")

        info_layout.addLayout(name_layout)
        info_layout.addWidget(lbl_sig)
        layout.addLayout(info_layout)

        # 状态
        status_color = "#2ecc71" if self.data['status'] == 'Online' else "#95a5a6"
        lbl_status = QLabel("●")
        lbl_status.setStyleSheet(f"color: {status_color}; font-size: 12px;")
        layout.addWidget(lbl_status)

    def load_avatar(self, b64_data):
        if b64_data:
            try:
                pix = QPixmap()
                pix.loadFromData(base64.b64decode(b64_data))

                # 圆形遮罩
                size = 50
                rounded = QPixmap(size, size)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, size, size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, size, size,
                                   pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                              Qt.TransformationMode.SmoothTransformation))
                painter.end()

                self.lbl_avatar.setPixmap(rounded)
            except:
                pass

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        del_action = menu.addAction(f"🗑️ {STRINGS['menu_delete_friend']}")
        action = menu.exec(event.globalPos())
        if action == del_action:
            self.delete_clicked.emit(self.data['id'], self.data['nickname'])


class RoomCard(QFrame):
    """房间卡片组件"""
    join_clicked = pyqtSignal(int, bool)  # id, has_password

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setup_ui()

    def setup_ui(self):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            RoomCard { background-color: white; border-radius: 12px; border: 1px solid #e0e0e0; }
            RoomCard:hover { background-color: #fbfbfb; border: 1px solid #9DC88D; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Top: Name + Lock/Private
        top_layout = QHBoxLayout()
        lbl_name = QLabel(self.data['name'])
        lbl_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        top_layout.addWidget(lbl_name)
        top_layout.addStretch()

        if self.data.get('is_private'):
            lbl_priv = QLabel("🔒")  # 私密图标
            lbl_priv.setToolTip("Private Room")
            top_layout.addWidget(lbl_priv)

        if self.data.get('has_password'):
            lbl_lock = QLabel("🔑")  # 密码锁图标
            lbl_lock.setToolTip("Password Protected")
            top_layout.addWidget(lbl_lock)

        layout.addLayout(top_layout)

        # Middle: Owner
        mid_layout = QHBoxLayout()
        lbl_owner_av = QLabel()
        lbl_owner_av.setFixedSize(24, 24)
        lbl_owner_av.setStyleSheet("background: #eee; border-radius: 12px;")
        lbl_owner_av.setScaledContents(True)
        if self.data.get('owner_avatar'):
            try:
                pix = QPixmap()
                pix.loadFromData(base64.b64decode(self.data['owner_avatar']))
                lbl_owner_av.setPixmap(pix)
            except:
                pass

        lbl_owner = QLabel(self.data['owner_nickname'])
        lbl_owner.setStyleSheet("color: #7f8c8d; font-size: 13px;")

        mid_layout.addWidget(lbl_owner_av)
        mid_layout.addWidget(lbl_owner)
        mid_layout.addStretch()
        layout.addLayout(mid_layout)

        # Bottom: Status
        bot_layout = QHBoxLayout()

        count = self.data['member_count']
        lbl_count = QLabel(f"👥 {count}/10")
        lbl_count.setStyleSheet("color: #7f8c8d; font-size: 12px;")

        bot_layout.addWidget(lbl_count)
        bot_layout.addStretch()

        if self.data.get('sprint_active'):
            lbl_status = QLabel("🔥 SPRINTING")
            lbl_status.setStyleSheet(
                "color: white; background: #e74c3c; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;")
            self.setEnabled(False)  # Disable click
            self.setStyleSheet("RoomCard { background-color: #f0f0f0; border-radius: 12px; border: 1px solid #ddd; }")
            bot_layout.addWidget(lbl_status)
        else:
            lbl_status = QLabel("🟢 WAITING")
            lbl_status.setStyleSheet(
                "color: white; background: #2ecc71; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;")
            bot_layout.addWidget(lbl_status)

        layout.addLayout(bot_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.join_clicked.emit(self.data['id'], self.data.get('has_password', False))


class SocialPage(QWidget):
    def __init__(self, network_manager, user_id=0):
        super().__init__()
        self.network = network_manager
        self.my_user_id = user_id

        self.current_group_id = None
        self.is_group_owner = False
        self.current_group_name = None

        self.float_group_win = None

        # 【新增】用于存储因“已在房间中”而失败的创建请求，以便在退出旧房间后自动重试
        self.pending_create_payload = None

        # UI Elements
        self.lobby_scroll = None
        self.lobby_layout = None  # The FlowLayout
        self.friend_scroll = None
        self.friend_layout = None  # QVBoxLayout for friend cards

        self.room_widget = None
        self.chat_display = None
        self.rank_list = None
        self.sprint_ctrl_frame = None
        self.lbl_room_name = None
        self.lbl_sprint_status = None
        self.lbl_owner_avatar = None
        self.btn_friend_requests = None

        self.setup_ui()

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(5000)  # 房间内轮询加快
        self.update_timer.timeout.connect(self.refresh_current_group_data)

        self.list_timer = QTimer(self)
        self.list_timer.setInterval(30000)  # 列表轮询
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
        if group_info and 'id' in group_info:
            gid = group_info['id']
            name = group_info.get('name', STRINGS["lbl_loading"])
            owner_id = group_info.get('owner_id', 0)
            self.enter_room_view(gid, name, owner_id)

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

    # ---------------- FRIENDS TAB ----------------
    def create_friends_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Controls
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(STRINGS["search_placeholder"])
        self.search_input.setFixedHeight(35)
        self.search_input.setStyleSheet("border-radius: 5px; border: 1px solid #ddd; padding: 0 10px;")

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

        # Friend List (Scroll Area with VBox)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        self.friend_layout = QVBoxLayout(content)
        self.friend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.friend_layout.setSpacing(10)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def load_friends(self):
        if self.my_user_id > 0:
            self.network.send_request({"type": "get_friends"})

    def on_delete_friend_clicked(self, fid, fname):
        reply = QMessageBox.question(self, STRINGS["confirm_title"],
                                     STRINGS["msg_delete_friend_confirm"].format(fname),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.network.send_request({"type": "delete_friend", "friend_id": fid})

    # ---------------- GROUPS/LOBBY TAB ----------------
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

        # Lobby Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        self.lobby_layout = QGridLayout(content)
        self.lobby_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lobby_layout.setSpacing(15)

        scroll.setWidget(content)
        lobby_layout.addWidget(scroll)

        # 2. Room View
        self.room_widget = self.create_room_view()

        self.group_stack.addWidget(self.lobby_widget)
        self.group_stack.addWidget(self.room_widget)
        main_layout.addWidget(self.group_stack)

        return widget

    def refresh_group_list(self):
        if self.my_user_id > 0:
            self.network.send_request({"type": "get_public_groups"})

    def on_join_room_clicked(self, group_id, has_password):
        if has_password:
            pwd, ok = QInputDialog.getText(self, STRINGS["dialog_password_title"], STRINGS["dialog_password_label"],
                                           QLineEdit.EchoMode.Password)
            if ok:
                self.network.send_request({"type": "join_group", "group_id": group_id, "password": pwd})
        else:
            self.network.send_request({"type": "join_group", "group_id": group_id})

    # ---------------- ROOM VIEW ----------------
    def create_room_view(self):
        widget = QWidget()
        room_layout = QVBoxLayout(widget)
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

        self.rank_list = QListWidget()
        self.rank_list.setStyleSheet(
            "QListWidget { background: transparent; border: none; } QListWidget::item { padding: 5px; }")
        self.rank_list.setIconSize(QSize(32, 32))
        # Context Menu for Add Friend
        self.rank_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rank_list.customContextMenuRequested.connect(self.show_member_context_menu)

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
        return widget

    def show_member_context_menu(self, pos):
        item = self.rank_list.itemAt(pos)
        if not item: return
        user_id = item.data(Qt.ItemDataRole.UserRole)
        if user_id == self.my_user_id: return  # Don't add self

        menu = QMenu()
        add_action = menu.addAction(f"➕ {STRINGS['menu_add_friend']}")
        action = menu.exec(self.rank_list.mapToGlobal(pos))

        if action == add_action:
            self.add_friend_request(user_id)

    # ---------------- LOGIC ----------------

    def search_user_to_add(self):
        query = self.search_input.text().strip()
        if not query: return
        self.network.send_request({"type": "search_user", "query": query})

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

    def show_create_group_dialog(self):
        # 自定义创建房间对话框，支持密码
        dialog = QDialog(self)
        dialog.setWindowTitle(STRINGS["dialog_create_group_title"])
        layout = QFormLayout(dialog)

        edit_name = QLineEdit()
        edit_pwd = QLineEdit()
        edit_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        chk_private = QCheckBox(STRINGS["dialog_private_msg"])

        layout.addRow(STRINGS["dialog_group_name_label"], edit_name)
        layout.addRow(STRINGS["dialog_group_pwd_label"], edit_pwd)
        layout.addRow("", chk_private)

        btns = QHBoxLayout()
        btn_ok = QPushButton(STRINGS["confirm_title"])
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addRow(btns)

        if dialog.exec():
            name = edit_name.text().strip()
            if not name: return

            # 保存创建请求数据
            payload = {
                "type": "create_group",
                "name": name,
                "password": edit_pwd.text().strip(),
                "is_private": chk_private.isChecked()
            }
            self.network.send_request(payload)

    def enter_room_view(self, group_id, name, owner_id):
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
        if not isinstance(text, str): text = None
        if not text:
            text = self.chat_input.text().strip()
            self.chat_input.clear()

        if text and self.current_group_id:
            self.network.send_request({"type": "group_chat", "group_id": self.current_group_id, "content": text})

    def start_sprint_dialog(self):
        target, ok = QInputDialog.getInt(self, STRINGS["dialog_sprint_title"], STRINGS["dialog_sprint_target"], 500, 10,
                                         100000)
        if ok:
            self.network.send_request(
                {"type": "sprint_control", "action": "start", "group_id": self.current_group_id, "target": target})

    def stop_sprint(self):
        self.network.send_request({"type": "sprint_control", "action": "stop", "group_id": self.current_group_id})

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

        elif dtype == "delete_friend_response":
            self.load_friends()
            QMessageBox.information(self, STRINGS["success_title"], STRINGS["msg_friend_deleted"])

        elif dtype == "get_friends_response":
            # Clear layout
            while self.friend_layout.count():
                item = self.friend_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()

            for f in data.get("data", []):
                card = FriendCard(f)
                card.delete_clicked.connect(self.on_delete_friend_clicked)
                self.friend_layout.addWidget(card)

        elif dtype == "refresh_friend_requests":
            if self.btn_friend_requests:
                self.btn_friend_requests.setStyleSheet(
                    "background-color: #ff6b6b; color: white; border-radius: 5px; padding: 5px 15px; font-weight: bold;")
            QMessageBox.information(self, STRINGS["warn_title"], STRINGS["msg_new_req"])

        elif dtype == "friend_requests_response":
            self.open_request_dialog(data.get("data", []))

        elif dtype == "refresh_groups":
            self.refresh_group_list()

        elif dtype == "group_list_response":
            # Clear grid
            while self.lobby_layout.count():
                item = self.lobby_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()

            # Add Cards
            groups = data.get("data", [])
            cols = 2  # 2 columns grid
            for i, g in enumerate(groups):
                card = RoomCard(g)
                card.join_clicked.connect(self.on_join_room_clicked)
                self.lobby_layout.addWidget(card, i // cols, i % cols)

        elif dtype in ["create_group_response", "join_group_response"]:
            if data['status'] == 'success':
                # Create: We are owner. Join: We assume not owner until detailed info.
                owner_id = self.my_user_id if dtype == "create_group_response" else 0
                self.enter_room_view(data['group_id'], data.get('group_name', STRINGS["lbl_loading"]), owner_id)
                self.refresh_current_group_data()
                # 成功加入或创建后，清除 pending payload
                self.pending_create_payload = None
            else:
                msg = data.get('msg', STRINGS["msg_unknown_err"])

                # 【重要修复】自动处理 "You are already in a group" 错误
                if "already in a group" in msg or "already in another group" in msg:
                    # 如果有 pending_create_payload，说明是用户尝试创建新房间时失败
                    # 询问是否退出旧房间并继续创建
                    if self.pending_create_payload and dtype == "create_group_response":
                        gid = data.get('current_group_id', 'Unknown')
                        reply = QMessageBox.question(self, STRINGS["warn_title"],
                                                     f"你当前已在房间 (ID: {gid}) 中。\n是否退出该房间并创建新房间？",
                                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.Yes:
                            # 发送离开请求，注意：我们不清除 pending_create_payload，
                            # 这样在 leave_group_response 中可以检测到并触发创建
                            self.network.send_request({"type": "leave_group", "group_id": gid})
                            return  # 等待 leave_group_response

                    # 如果是加入房间失败（没有 payload），则只是提示切回旧房间
                    if 'current_group_id' in data:
                        gid = data['current_group_id']
                        reply = QMessageBox.question(self, STRINGS["warn_title"],
                                                     STRINGS["msg_in_other_room"].format(gid),
                                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.Yes:
                            self.enter_room_view(gid, STRINGS["lbl_loading"], 0)
                            self.refresh_current_group_data()
                        else:
                            # 用户选择不切回，那也没办法，只能留在 lobby
                            pass
                    else:
                        QMessageBox.warning(self, STRINGS["msg_failed"], msg)

                elif msg == "password_required":
                    pwd, ok = QInputDialog.getText(self, STRINGS["dialog_password_title"],
                                                   STRINGS["dialog_password_label"], QLineEdit.EchoMode.Password)
                    if ok:
                        self.network.send_request(
                            {"type": "join_group", "group_id": data.get("group_id"), "password": pwd})
                elif msg == "Incorrect password":
                    QMessageBox.warning(self, STRINGS["error_title"], "密码错误！")
                else:
                    QMessageBox.warning(self, STRINGS["msg_failed"], msg)

        elif dtype == "group_disbanded":
            if self.current_group_id == data.get('group_id'):
                QMessageBox.warning(self, STRINGS["warn_title"], "房间已被房主解散。")
                self.leave_room()

        elif dtype == "leave_group_response":
            if data.get("msg") == "Group disbanded":
                QMessageBox.information(self, STRINGS["success_title"], "房间已解散。")
            else:
                # 只有在不是自动重试的情况下才弹窗
                if not self.pending_create_payload:
                    QMessageBox.information(self, STRINGS["success_title"], STRINGS["msg_leave_success"])

            self.leave_room()

            # 【重要修复】如果是因为要创建新房间而强制退出的，现在重新发送创建请求
            if self.pending_create_payload:
                print("[Social] Auto-retrying create group after leave...")
                self.network.send_request(self.pending_create_payload)
                # 注意：不要在这里清空 payload，要等到 create_group_response 成功后再清空

        elif dtype == "group_detail_response":
            if self.current_group_id != data['group_id']: return

            self.current_group_name = data['name']
            self.lbl_room_name.setText(STRINGS["lbl_room_name_fmt"].format(data['name']))

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
            if self.float_group_win: self.float_group_win.update_chat(html)

            self.rank_list.clear()
            rank_data_for_float = []
            for idx, r in enumerate(data['leaderboard']):
                prefix = f"#{idx + 1}"
                color = "black"
                if r['reached_target']:
                    color = "#27ae60"
                elif idx == 0 and r['word_count'] > 0:
                    color = "#d35400"
                text = f"{prefix} {r['nickname']}: {r['word_count']}"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor(color)))
                item.setData(Qt.ItemDataRole.UserRole, r['user_id'])  # Store ID for context menu
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

            if self.float_group_win: self.float_group_win.update_rank(rank_data_for_float)

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
                if self.float_group_win: self.float_group_win.append_chat(line)

        elif dtype == "sprint_status_push":
            if self.current_group_id == data['group_id']:
                self.refresh_current_group_data()