from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QFileDialog, QInputDialog, QListWidget, QAbstractItemView, QMenu,
                             QSizePolicy, QCheckBox, QLineEdit, QStackedWidget, QColorDialog, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QBuffer, QByteArray
from PyQt6.QtGui import QAction, QColor, QPixmap, QImage
import os
import sys
import base64
import time
import json  # 新增 json 导入

client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

try:
    from .theme import ThemeManager, DEFAULT_ACCENT
    from .float_window import FloatWindow
    from .analytics import AnalyticsPage
    from .social_page import SocialPage  # ✅ 新增：导入社交页面
    from core.file_monitor import FileMonitor
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    raise e


class MainWindow(QWidget):
    switch_float_signal = pyqtSignal()
    pomo_float_toggle_signal = pyqtSignal(bool)
    pomo_update_signal = pyqtSignal(str)
    update_profile_signal = pyqtSignal(dict)

    def __init__(self, is_night=False, network_manager=None):
        super().__init__()
        self.setWindowTitle("InkSprint Dashboard")
        self.resize(1100, 720)  # ✅ 调整宽度以适应社交界面
        self.network = network_manager

        self.is_night = is_night
        self.current_accent = DEFAULT_ACCENT
        self.current_theme = ThemeManager.get_theme(self.is_night, self.current_accent)

        # 数据状态
        self.user_data = {"nickname": "Guest", "username": "guest", "avatar": None, "email": ""}
        self.today_base_count = 0  # 从服务器获取的今日已存字数
        self.session_increment = 0  # 本次运行新增字数
        self.session_start_time = time.time()
        self.user_id = 0  # ✅ 新增：存储用户ID

        # 本地配置路径
        self.config_path = os.path.join(client_dir, "sources_config.json")

        # 核心组件
        self.monitor_thread = FileMonitor()
        self.monitor_thread.stats_updated.connect(self.update_dashboard_stats)

        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.update_pomodoro_tick)
        self.pomo_seconds = 25 * 60
        self.pomo_is_running = False
        self.pomo_mode = "timer"

        self.float_window = FloatWindow(self.current_accent)
        self.float_window.restore_signal.connect(self.restore_from_float)

        self.switch_float_signal.connect(self.switch_to_float)
        self.pomo_float_toggle_signal.connect(self.float_window.set_mode)
        self.monitor_thread.stats_updated.connect(self.float_window.update_data)
        self.pomo_update_signal.connect(self.float_window.update_timer)

        # ✅ 初始化所有页面引用
        self.page_dashboard = None
        self.page_analytics = None
        self.page_social = None
        self.page_settings = None

        self.setup_ui()
        self.apply_theme()

        # 加载本地源配置
        self.load_local_sources()

        self.monitor_thread.start()

        # 监听网络消息以更新分析页面
        if self.network:
            self.network.message_received.connect(self.dispatch_network_message)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 左侧边栏 ===
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 40, 20, 40)

        # 用户信息区
        user_profile = QFrame()
        user_profile.setObjectName("UserProfile")
        user_layout = QHBoxLayout(user_profile)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(12)

        self.lbl_avatar = QLabel()
        self.lbl_avatar.setObjectName("UserAvatar")
        self.lbl_avatar.setFixedSize(48, 48)
        self.lbl_avatar.setScaledContents(True)

        self.lbl_app_name = QLabel("InkSprint")
        self.lbl_app_name.setObjectName("SidebarAppName")

        user_layout.addWidget(self.lbl_avatar)
        user_layout.addWidget(self.lbl_app_name)
        user_layout.addStretch()
        side_layout.addWidget(user_profile)
        side_layout.addSpacing(40)

        # 导航按钮
        self.nav_btns = {}
        # ✅ 更新导航项，加入 Social (Index 2)
        nav_items = [("🏠  Dashboard", 0), ("📊  Analytics", 1), ("👥  Social", 2), ("⚙️  Settings", 3)]

        for text, page_idx in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=page_idx, b=btn: self.on_nav_clicked(idx, b))
            side_layout.addWidget(btn)
            self.nav_btns[text] = btn

        list(self.nav_btns.values())[0].setChecked(True)
        side_layout.addStretch()
        main_layout.addWidget(self.sidebar)

        # === 右侧内容区 ===
        self.content_stack = QStackedWidget()

        # Page 0: Dashboard
        self.page_dashboard = self.create_dashboard_page()
        self.content_stack.addWidget(self.page_dashboard)

        # Page 1: Analytics
        self.page_analytics = AnalyticsPage(self.network)
        self.content_stack.addWidget(self.page_analytics)

        # Page 2: Social (✅ 静态初始化，避免动态崩溃)
        self.page_social = SocialPage(self.network, user_id=0)
        self.content_stack.addWidget(self.page_social)

        # Page 3: Settings
        self.page_settings = self.create_settings_page()
        self.content_stack.addWidget(self.page_settings)

        main_layout.addWidget(self.content_stack)

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel(f"Hi, Guest")
        self.lbl_title.setObjectName("PageTitle")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        self.btn_float = QPushButton("🚀")
        self.btn_float.setFixedSize(40, 40)
        self.btn_float.setObjectName("FloatButton")
        self.btn_float.clicked.connect(self.switch_float_signal.emit)
        header_layout.addWidget(self.btn_float)

        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(40, 40)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setObjectName("PinButton")
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.btn_pin)

        header_layout.addSpacing(8)

        btn_text = "🌙 Dark" if not self.is_night else "☀ Light"
        self.btn_theme_toggle = QPushButton(btn_text)
        self.btn_theme_toggle.setObjectName("ThemeToggle")
        self.btn_theme_toggle.setFixedSize(100, 40)
        self.btn_theme_toggle.clicked.connect(self.toggle_theme_mode)
        header_layout.addWidget(self.btn_theme_toggle)

        layout.addLayout(header_layout)

        # Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        self.card_main = self.create_stat_card("Today's Total", "0", "Session: +0", True)
        self.card_sub = self.create_stat_card("Current Speed", "0", "Words per hour", False)
        cards_layout.addWidget(self.card_main, 2)
        cards_layout.addWidget(self.card_sub, 1)
        layout.addLayout(cards_layout)

        # Bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        self.sources_card = self.create_sources_card()
        self.card_pomodoro = self.create_pomodoro_card()
        bottom_layout.addWidget(self.sources_card, 2)
        bottom_layout.addWidget(self.card_pomodoro, 1)
        layout.addLayout(bottom_layout)

        return page

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl = QLabel("Settings")
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)
        layout.addSpacing(30)

        form_card = QFrame()
        form_card.setObjectName("SettingsCard")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(20)

        lbl_profile = QLabel("Profile Settings")
        lbl_profile.setStyleSheet("font-weight: bold; font-size: 16px; color: #888;")
        form_layout.addRow(lbl_profile)

        self.lbl_id_display = QLabel("Loading...")
        self.lbl_id_display.setStyleSheet("color: #666; font-family: monospace;")
        form_layout.addRow("User ID:", self.lbl_id_display)

        self.edit_nickname = QLineEdit()
        self.edit_nickname.setPlaceholderText("Display name")
        form_layout.addRow("Nickname:", self.edit_nickname)

        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("Bind email")
        form_layout.addRow("Email:", self.edit_email)

        self.btn_avatar_pick = QPushButton("Change Avatar")
        self.btn_avatar_pick.setFixedSize(120, 35)
        self.btn_avatar_pick.clicked.connect(self.open_avatar_picker)
        self.lbl_avatar_preview = QLabel()
        self.lbl_avatar_preview.setFixedSize(60, 60)
        self.lbl_avatar_preview.setStyleSheet("background: #eee; border-radius: 30px;")
        self.lbl_avatar_preview.setScaledContents(True)
        av_layout = QHBoxLayout()
        av_layout.addWidget(self.lbl_avatar_preview)
        av_layout.addWidget(self.btn_avatar_pick)
        av_layout.addStretch()
        form_layout.addRow("Avatar:", av_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ddd;")
        form_layout.addRow(line)

        lbl_theme = QLabel("Appearance")
        lbl_theme.setStyleSheet("font-weight: bold; font-size: 16px; color: #888;")
        form_layout.addRow(lbl_theme)

        self.btn_color_pick = QPushButton(self.current_accent)
        self.btn_color_pick.setFixedSize(120, 35)
        self.btn_color_pick.clicked.connect(self.open_color_picker)
        form_layout.addRow("Accent Color:", self.btn_color_pick)

        self.btn_save_settings = QPushButton("Save Changes")
        self.btn_save_settings.setFixedSize(150, 45)
        self.btn_save_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_settings.setObjectName("SaveButton")
        self.btn_save_settings.clicked.connect(self.save_profile_changes)

        layout.addWidget(form_card)
        layout.addSpacing(20)
        layout.addWidget(self.btn_save_settings, 0, Qt.AlignmentFlag.AlignRight)

        self.pending_avatar_b64 = None
        return page

    # --- 本地配置管理 ---

    def load_local_sources(self):
        """从本地 JSON 加载文件源配置"""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sources = data.get("sources", [])

                # 仅加载属于当前用户的配置（如果需要多用户支持，这里可以加个判断）
                # 这里简化为直接加载，假设单机用户或不区分

                for src in sources:
                    path = src.get('path')
                    stype = src.get('type', 'local')
                    if path:
                        is_web = (stype == 'web')
                        self.monitor_thread.add_source(path, is_web)
                        # 界面上也要添加
                        icon = "🌐" if is_web else "📄"
                        self.list_sources.addItem(f"{icon}  {path}")

                self.lbl_list_title.setText(f"Active Sources ({self.list_sources.count()}/10)")
                print(f"[Config] Loaded {len(sources)} sources from local config.")
        except Exception as e:
            print(f"[Config Error] Failed to load local sources: {e}")

    def save_local_sources(self):
        """保存当前文件源配置到本地 JSON"""
        sources = []
        for i in range(self.list_sources.count()):
            item_text = self.list_sources.item(i).text()
            # item_text 格式: "📄  C:/path/to/doc"
            parts = item_text.split("  ", 1)
            if len(parts) == 2:
                icon, path = parts
                stype = 'web' if '🌐' in icon else 'local'
                sources.append({"path": path, "type": stype})

        data = {"sources": sources, "last_updated": time.time()}

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("[Config] Sources saved locally.")
        except Exception as e:
            print(f"[Config Error] Failed to save local sources: {e}")

    # --- 核心逻辑 ---

    def set_user_info(self, data):
        """登录成功后设置数据"""
        self.user_data = data
        self.user_id = data.get("user_id", 0)  # ✅ 获取用户ID
        nickname = data.get("nickname", "Writer")
        username = data.get("username", "unknown")
        email = data.get("email", "")

        # 1. 恢复今日累计字数
        self.today_base_count = data.get("today_total", 0)

        self.lbl_title.setText(f"Hi, {nickname}")
        self.lbl_id_display.setText(username)
        self.edit_nickname.setText(nickname)
        self.edit_email.setText(email)

        if data.get("avatar_data"):
            try:
                img_data = base64.b64decode(data["avatar_data"])
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                self.lbl_avatar.setPixmap(pixmap)
                self.lbl_avatar_preview.setPixmap(pixmap)
            except:
                self.load_default_avatar()
        else:
            self.load_default_avatar()

        # ✅ 激活社交页面
        if self.page_social:
            self.page_social.set_user_id(self.user_id)
            if self.user_id:
                self.page_social.load_friends()
                self.page_social.refresh_group_list()

                # 【新增】如果服务端返回了 current_group，自动恢复房间视图
                if 'current_group' in data and data['current_group']:
                    self.page_social.restore_group_state(data['current_group'])

    def update_dashboard_stats(self, total_in_monitor, increment, wph):
        self.session_increment = increment
        daily_total = self.today_base_count + increment
        self.lbl_main_count.setText(str(daily_total))
        self.card_main.findChild(QLabel, "CardSub").setText(f"Session: +{increment}")
        self.lbl_speed.setText(str(wph))

    def on_nav_clicked(self, page_idx, btn):
        for b in self.nav_btns.values(): b.setChecked(False)
        btn.setChecked(True)
        self.content_stack.setCurrentIndex(page_idx)

        # 如果切换到分析页，触发数据加载
        if page_idx == 1:
            self.page_analytics.load_data()
        # ✅ 如果切换到社交页，刷新数据
        elif page_idx == 2 and self.page_social and self.user_id:
            self.page_social.load_friends()
            self.page_social.refresh_group_list()

    def dispatch_network_message(self, data):
        """分发网络消息到各个子页面"""
        rtype = data.get("type", "")
        if rtype in ["analytics_data", "details_data"]:
            self.page_analytics.handle_response(data)

        # ✅ 社交消息处理
        elif rtype in ["search_user_response", "get_friends_response",
                       "group_list_response", "create_group_response", "join_group_response",
                       "group_detail_response", "group_msg_push", "sprint_status_push",
                       "refresh_friends", "refresh_friend_requests", "friend_requests_response",
                       "respond_friend_response"]:
            if self.page_social:
                self.page_social.handle_network_msg(data)

    def closeEvent(self, event):
        """窗口关闭时的操作"""

        # 1. 【新增】保存本地文件配置
        self.save_local_sources()

        # 2. 同步字数记录到云端（可选，依然保留以记录数据）
        if self.network:
            duration = int(time.time() - self.session_start_time)
            # 只有当有数据变化时才上传
            if self.session_increment > 0 or duration > 60:
                self.network.send_request({
                    "type": "sync_data",
                    "increment": self.session_increment,
                    "duration": duration
                })

            # 【已移除】不再同步 sources 到服务器
            # self.network.send_request({"type": "sync_sources", "sources": sources})

        # 等待一小会儿确保发送完成
        import time as t
        t.sleep(0.2)
        event.accept()

    # --- 其他辅助函数 ---

    def open_avatar_picker(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Avatar", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.lbl_avatar_preview.setPixmap(scaled)
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            scaled.save(buffer, "PNG")
            self.pending_avatar_b64 = byte_array.toBase64().data().decode()

    def save_profile_changes(self):
        new_nickname = self.edit_nickname.text().strip()
        new_email = self.edit_email.text().strip()
        if not new_nickname:
            QMessageBox.warning(self, "Warning", "Nickname cannot be empty!")
            return
        payload = {"type": "update_profile", "nickname": new_nickname, "email": new_email}
        if self.pending_avatar_b64: payload["avatar_data"] = self.pending_avatar_b64
        if self.network:
            self.network.send_request(payload)
            self.lbl_title.setText(f"Hi, {new_nickname}")
            if self.pending_avatar_b64: self.lbl_avatar.setPixmap(self.lbl_avatar_preview.pixmap())
            QMessageBox.information(self, "Sent", "Profile update request sent.")

    def open_color_picker(self):
        color = QColorDialog.getColor(QColor(self.current_accent), self, "Select Accent Color")
        if color.isValid():
            new_hex = color.name().upper()
            self.current_accent = new_hex
            self.btn_color_pick.setText(new_hex)
            self.current_theme = ThemeManager.get_theme(self.is_night, self.current_accent)
            self.apply_theme()
            self.float_window.set_theme_color(self.current_accent)

    def toggle_theme_mode(self):
        self.is_night = not self.is_night
        self.current_theme = ThemeManager.get_theme(self.is_night, self.current_accent)
        self.btn_theme_toggle.setText("☀ Light" if self.is_night else "🌙 Dark")
        self.apply_theme()

    def add_local_source(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Doc", "", "Documents (*.docx *.txt)")
        if file_path:
            self._perform_add(file_path, False)
            # 添加后立即保存配置
            self.save_local_sources()

    def add_web_source(self):
        text, ok = QInputDialog.getText(self, "Add Web", "URL:")
        if ok and text:
            self._perform_add(text.strip(), True)
            # 添加后立即保存配置
            self.save_local_sources()

    def _perform_add(self, path, is_web):
        if self.monitor_thread.add_source(path, is_web):
            icon = "🌐" if is_web else "📄"
            self.list_sources.addItem(f"{icon}  {path}")
            self.lbl_list_title.setText(f"Active Sources ({self.list_sources.count()}/10)")

    def show_list_context_menu(self, pos):
        item = self.list_sources.itemAt(pos)
        if item:
            menu = QMenu()
            menu.addAction("🗑️ Remove").triggered.connect(lambda: self.delete_source(item))
            menu.exec(self.list_sources.mapToGlobal(pos))

    def delete_source(self, item):
        path = item.text().split("  ", 1)[1]
        self.monitor_thread.remove_source(path)
        self.list_sources.takeItem(self.list_sources.row(item))
        self.lbl_list_title.setText(f"Active Sources ({self.list_sources.count()}/10)")
        # 删除后立即保存配置
        self.save_local_sources()

    def on_pomo_time_edited(self):
        if self.pomo_is_running: return
        try:
            parts = list(map(int, self.edit_pomo_time.text().split(':')))
            if len(parts) == 3:
                s = parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                s = parts[0] * 60 + parts[1]
            else:
                return
            self.pomo_seconds = s
            self.update_display_time()
        except:
            self.update_display_time()

    def set_pomodoro_mode(self, mode):
        self.pomo_mode = mode
        self.reset_pomodoro()
        self.apply_pomo_btn_style()

    def toggle_pomodoro(self):
        if self.pomo_is_running:
            self.pomo_timer.stop()
            self.btn_pomo_start.setText("▶")
            self.pomo_is_running = False
            self.edit_pomo_time.setReadOnly(False)
        else:
            self.pomo_timer.start(1000)
            self.btn_pomo_start.setText("⏸")
            self.pomo_is_running = True
            self.edit_pomo_time.setReadOnly(True)

    def reset_pomodoro(self):
        self.pomo_timer.stop()
        self.pomo_is_running = False
        self.btn_pomo_start.setText("▶")
        self.edit_pomo_time.setReadOnly(False)
        self.pomo_seconds = 25 * 60 if self.pomo_mode == "timer" else 0
        self.update_display_time()

    def update_pomodoro_tick(self):
        if self.pomo_mode == "timer":
            if self.pomo_seconds > 0:
                self.pomo_seconds -= 1
            else:
                self.reset_pomodoro()
        else:
            self.pomo_seconds += 1
        self.update_display_time()

    def update_display_time(self):
        m, s = divmod(self.pomo_seconds, 60)
        h, m = divmod(m, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        self.edit_pomo_time.setText(time_str)
        self.pomo_update_signal.emit(f"{m:02d}:{s:02d}" if h == 0 else time_str)

    def switch_to_float(self):
        self.hide()
        self.float_window.show()
        screen = self.screen().geometry()
        self.float_window.move(screen.width() - 300, 100)

    def restore_from_float(self):
        self.float_window.hide()
        self.show()
        self.activateWindow()

    def toggle_always_on_top(self):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.btn_pin.isChecked())
        self.show()

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)
        widget._shadow = shadow

    def apply_pomo_btn_style(self):
        t = self.current_theme
        active = f"background-color: {t['accent']}; color: white; border:none; border-radius: 5px; font-weight: bold;"
        inactive = f"background-color: {t['input_bg']}; color: {t['text_main']}; border:none; border-radius: 5px;"
        self.btn_mode_timer.setStyleSheet(active if self.pomo_mode == "timer" else inactive)
        self.btn_mode_stopwatch.setStyleSheet(active if self.pomo_mode == "stopwatch" else inactive)

    def load_default_avatar(self):
        self.lbl_avatar.setStyleSheet("background-color: #cccccc; border-radius: 24px;")
        self.lbl_avatar_preview.setStyleSheet("background-color: #cccccc; border-radius: 30px;")

    def create_stat_card(self, title, value, sub, is_primary):
        card = QFrame()
        card.setObjectName("StatCardPrimary" if is_primary else "StatCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 25, 30, 25)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("CardTitle")
        lbl_val = QLabel(value)
        lbl_val.setObjectName("CardValue")
        if is_primary:
            self.lbl_main_count = lbl_val
        else:
            self.lbl_speed = lbl_val
        lbl_sub = QLabel(sub)
        lbl_sub.setObjectName("CardSub")
        layout.addWidget(lbl_title)
        layout.addStretch()
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        self.add_shadow(card)
        return card

    def create_sources_card(self):
        card = QFrame()
        card.setObjectName("SourcesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.lbl_list_title = QLabel("Active Sources (0/10)")
        self.lbl_list_title.setObjectName("ListTitle")
        layout.addWidget(self.lbl_list_title)
        self.list_sources = QListWidget()
        self.list_sources.setObjectName("SourceList")
        self.list_sources.setFrameShape(QFrame.Shape.NoFrame)
        self.list_sources.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_sources.customContextMenuRequested.connect(self.show_list_context_menu)
        layout.addWidget(self.list_sources)
        btns_layout = QHBoxLayout()
        self.btn_local = QPushButton("➕ Local")
        self.btn_local.setObjectName("ActionBtnLocal")
        self.btn_local.clicked.connect(self.add_local_source)
        self.btn_web = QPushButton("🌐 Tencent")
        self.btn_web.setObjectName("ActionBtnWeb")
        self.btn_web.clicked.connect(self.add_web_source)
        for b in [self.btn_local, self.btn_web]:
            b.setFixedHeight(45)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btns_layout.addWidget(b)
        layout.addLayout(btns_layout)
        self.add_shadow(card)
        return card

    def create_pomodoro_card(self):
        card = QFrame()
        card.setObjectName("PomodoroCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Focus Timer"))
        top_bar.addStretch()
        self.chk_pomo_float = QCheckBox("Float")
        self.chk_pomo_float.setObjectName("PomoFloatCheck")
        self.chk_pomo_float.toggled.connect(self.pomo_float_toggle_signal.emit)
        top_bar.addWidget(self.chk_pomo_float)
        top_bar.addSpacing(10)
        self.btn_mode_timer = QPushButton("-")
        self.btn_mode_timer.setFixedSize(30, 30)
        self.btn_mode_timer.setObjectName("PomoModeBtn")
        self.btn_mode_timer.clicked.connect(lambda: self.set_pomodoro_mode("timer"))
        self.btn_mode_stopwatch = QPushButton("+")
        self.btn_mode_stopwatch.setFixedSize(30, 30)
        self.btn_mode_stopwatch.setObjectName("PomoModeBtn")
        self.btn_mode_stopwatch.clicked.connect(lambda: self.set_pomodoro_mode("stopwatch"))
        top_bar.addWidget(self.btn_mode_timer)
        top_bar.addWidget(self.btn_mode_stopwatch)
        layout.addLayout(top_bar)
        layout.addStretch()
        self.edit_pomo_time = QLineEdit("00:25:00")
        self.edit_pomo_time.setObjectName("PomoTimeEdit")
        self.edit_pomo_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_pomo_time.editingFinished.connect(self.on_pomo_time_edited)
        layout.addWidget(self.edit_pomo_time)
        layout.addStretch()
        ctrl_layout = QHBoxLayout()
        self.btn_pomo_start = QPushButton("▶")
        self.btn_pomo_start.setObjectName("PomoStartBtn")
        self.btn_pomo_start.setFixedSize(50, 50)
        self.btn_pomo_start.clicked.connect(self.toggle_pomodoro)
        self.btn_pomo_reset = QPushButton("↺")
        self.btn_pomo_reset.setObjectName("PomoResetBtn")
        self.btn_pomo_reset.setFixedSize(50, 50)
        self.btn_pomo_reset.clicked.connect(self.reset_pomodoro)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_pomo_start)
        ctrl_layout.addWidget(self.btn_pomo_reset)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        self.add_shadow(card)
        return card

    # ... (Theme and Styling functions remain same) ...
    def apply_theme(self):
        t = self.current_theme
        self.btn_color_pick.setStyleSheet(
            f"background-color: {t['accent']}; color: white; border-radius: 5px; font-weight: bold;")
        self.btn_color_pick.setText(self.current_accent)

        shadow_c = QColor(0, 0, 0, 30) if t['name'] == 'light' else QColor(0, 0, 0, 180)
        for w in [self.card_main, self.card_sub, self.card_pomodoro, self.sources_card]:
            if hasattr(w, '_shadow'): w._shadow.setColor(shadow_c)

        val_color = "#2D3436" if t['name'] == 'light' else "#FFFFFF"
        sub_color = t['text_sub']

        self.setStyleSheet(f"""
            QWidget {{ background-color: {t['window_bg']}; color: {t['text_main']}; font-family: 'Segoe UI', sans-serif; }}
            QFrame#Sidebar {{ background-color: {t['card_bg']}; border-right: 1px solid {t['border']}; }}
            QFrame#UserProfile {{ background: transparent; }}
            QLabel#UserAvatar {{ background-color: #ccc; border-radius: 24px; }}
            QLabel#SidebarAppName {{ color: {t['accent']}; font-weight: 900; font-size: 22px; background: transparent; }}
            QPushButton#NavButton {{ text-align: left; padding: 12px 20px; border-radius: 10px; border: none; color: {t['text_sub']}; font-weight: 600; font-size: 15px; background: transparent; }}
            QPushButton#NavButton:hover {{ background-color: {t['input_bg']}; color: {t['text_main']}; }}
            QPushButton#NavButton:checked {{ background-color: {t['input_bg']}; color: {t['accent']}; }}
            QLabel#PageTitle {{ font-size: 32px; font-weight: bold; color: {t['text_main']}; }}
            QLabel#ListTitle {{ font-weight: bold; font-size: 16px; margin: 5px 0; color: {t['text_main']}; background: transparent; }}
            QPushButton#ThemeToggle, QPushButton#PinButton, QPushButton#FloatButton, QPushButton#SaveButton,
            QPushButton#ActionBtnLocal, QPushButton#ActionBtnWeb {{ 
                border: 1px solid {t['border']}; border-radius: 10px; color: {t['text_main']}; background: {t['card_bg']}; 
            }}
            QPushButton#PinButton:checked, QPushButton#SaveButton:hover, QPushButton#ActionBtnLocal:hover, QPushButton#ActionBtnWeb:hover {{ 
                background: {t['accent']}; color: white; border: none; 
            }}
            QPushButton#ActionBtnLocal:hover, QPushButton#ActionBtnWeb:hover {{
                background-color: {t['input_bg']}; color: {t['text_main']}; border: 1px solid {t['accent']};
            }}
            QFrame#StatCard, QFrame#SourcesCard, QFrame#PomodoroCard {{ background: {t['card_bg']}; border-radius: 20px; }}
            QFrame#StatCardPrimary {{ background: {t['accent']}; border-radius: 20px; color: white; }}
            QFrame#SettingsCard {{ background: transparent; border: none; }}
            QFrame#StatCard QLabel, QFrame#StatCardPrimary QLabel, QFrame#PomodoroCard QLabel {{ background: transparent; }}
            QFrame#StatCardPrimary QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: white; }}
            QFrame#StatCardPrimary QLabel#CardTitle {{ font-size: 16px; opacity: 0.9; color: white; }}
            QFrame#StatCardPrimary QLabel#CardSub {{ font-size: 14px; opacity: 0.8; color: white; }}
            QFrame#StatCard QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: {val_color}; }}
            QFrame#StatCard QLabel#CardTitle {{ font-size: 16px; color: {sub_color}; }}
            QFrame#StatCard QLabel#CardSub {{ font-size: 14px; color: {sub_color}; }}
            QLineEdit {{ background-color: {t['input_bg']}; border: 1px solid {t['input_bg']}; border-radius: 8px; padding: 8px; color: {t['text_main']}; }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; background-color: {t['card_bg']}; }}
            QLineEdit#PomoTimeEdit {{ font-size: 56px; font-weight: bold; color: {t['accent']}; background: transparent; border: none; }}
            QPushButton#PomoStartBtn {{ background: {t['accent']}; color: white; border-radius: 25px; font-size: 20px; border: none; }}
            QPushButton#PomoResetBtn {{ background: {t['input_bg']}; color: {t['text_main']}; border-radius: 25px; font-size: 20px; border: none; }}
            QCheckBox {{ color: {t['text_main']}; spacing: 5px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {t['text_main']}; border-radius: 4px; background: transparent; }}
            QCheckBox::indicator:checked {{ background-color: {t['accent']}; border: 2px solid {t['accent']}; }}
            QListWidget#SourceList {{ background: transparent; border: none; color: {t['text_main']}; font-size: 14px; }}
            QListWidget::item:selected {{ background: {t['input_bg']}; color: {t['accent']}; }}
            QMessageBox {{ background-color: {t['card_bg']}; }}
            QMessageBox QLabel {{ color: {t['text_main']}; }}
            QMessageBox QPushButton {{ background-color: {t['input_bg']}; color: {t['text_main']}; border: 1px solid {t['border']}; padding: 5px 15px; border-radius: 5px; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ background: {t['card_bg']}; color: {t['text_main']}; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {t['accent']}; color: white; }}
            QTextEdit {{ background-color: {t['input_bg']}; border-radius: 8px; border: 1px solid {t['border']}; padding: 5px; }}
        """)
        self.apply_pomo_btn_style()