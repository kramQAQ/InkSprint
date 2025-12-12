from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QFileDialog, QInputDialog, QListWidget, QAbstractItemView, QMenu,
                             QSizePolicy, QCheckBox, QLineEdit, QStackedWidget, QColorDialog, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QBuffer, QByteArray, QDate
from PyQt6.QtGui import QAction, QColor, QPixmap, QImage
import os
import sys
import base64
import time
import json

client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

try:
    from .localization import STRINGS
    from .theme import ThemeManager, DEFAULT_ACCENT
    from .float_window import FloatWindow
    from .analytics import AnalyticsPage
    from .social_page import SocialPage
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
        self.setWindowTitle(STRINGS["window_title_dash"])
        self.resize(1100, 720)
        self.network = network_manager

        self.is_night = is_night
        self.current_accent = DEFAULT_ACCENT
        self.current_theme = ThemeManager.get_theme(self.is_night, self.current_accent)

        # 数据状态
        self.user_data = {"nickname": "Guest", "username": "guest", "avatar": None, "email": ""}

        # 【关键变量】
        self.today_base_count = 0  # 从服务器获取的“今天已完成字数”（不含本次运行期间的增量）
        self.session_increment = 0  # 本次运行期间的总增量
        self.last_synced_increment = 0

        # 跨天修正：如果运行过程中跨天，我们需要减去属于昨天的部分增量
        self.daily_increment_offset = 0

        self.session_start_time = time.time()
        self.current_report_date = QDate.currentDate()
        self.user_id = 0

        self.config_path = os.path.join(client_dir, "sources_config.json")

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

        self.page_dashboard = None
        self.page_analytics = None
        self.page_social = None
        self.page_settings = None

        self.setup_ui()
        self.apply_theme()
        self.load_local_sources()
        self.monitor_thread.start()

        if self.network:
            self.network.message_received.connect(self.dispatch_network_message)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 40, 20, 40)

        user_profile = QFrame()
        user_profile.setObjectName("UserProfile")
        user_layout = QHBoxLayout(user_profile)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(12)

        self.lbl_avatar = QLabel()
        self.lbl_avatar.setObjectName("UserAvatar")
        self.lbl_avatar.setFixedSize(48, 48)
        self.lbl_avatar.setScaledContents(True)

        self.lbl_app_name = QLabel(STRINGS["app_name"])
        self.lbl_app_name.setObjectName("SidebarAppName")

        user_layout.addWidget(self.lbl_avatar)
        user_layout.addWidget(self.lbl_app_name)
        user_layout.addStretch()
        side_layout.addWidget(user_profile)
        side_layout.addSpacing(40)

        self.nav_btns = {}
        nav_items = [
            (f"🏠  {STRINGS['nav_dashboard']}", 0),
            (f"📊  {STRINGS['nav_analytics']}", 1),
            (f"👥  {STRINGS['nav_social']}", 2),
            (f"⚙️  {STRINGS['nav_settings']}", 3)
        ]

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

        self.content_stack = QStackedWidget()

        self.page_dashboard = self.create_dashboard_page()
        self.content_stack.addWidget(self.page_dashboard)

        self.page_analytics = AnalyticsPage(self.network)
        self.content_stack.addWidget(self.page_analytics)

        self.page_social = SocialPage(self.network, user_id=0)
        self.content_stack.addWidget(self.page_social)

        self.page_settings = self.create_settings_page()
        self.content_stack.addWidget(self.page_settings)

        main_layout.addWidget(self.content_stack)

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(20)

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

        btn_text = STRINGS["theme_dark"] if not self.is_night else STRINGS["theme_light"]
        self.btn_theme_toggle = QPushButton(btn_text)
        self.btn_theme_toggle.setObjectName("ThemeToggle")
        self.btn_theme_toggle.setFixedSize(100, 40)
        self.btn_theme_toggle.clicked.connect(self.toggle_theme_mode)
        header_layout.addWidget(self.btn_theme_toggle)

        layout.addLayout(header_layout)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        self.card_main = self.create_stat_card(STRINGS["stat_today"], "0", STRINGS["stat_session"].format(0), True)
        self.card_sub = self.create_stat_card(STRINGS["stat_speed"], "0", STRINGS["unit_wph"], False)
        cards_layout.addWidget(self.card_main, 2)
        cards_layout.addWidget(self.card_sub, 1)
        layout.addLayout(cards_layout)

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

        lbl = QLabel(STRINGS["settings_title"])
        lbl.setObjectName("PageTitle")
        layout.addWidget(lbl)
        layout.addSpacing(30)

        form_card = QFrame()
        form_card.setObjectName("SettingsCard")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(20)

        lbl_profile = QLabel(STRINGS["profile_header"])
        lbl_profile.setStyleSheet("font-weight: bold; font-size: 16px; color: #888;")
        form_layout.addRow(lbl_profile)

        self.lbl_id_display = QLabel("Loading...")
        self.lbl_id_display.setStyleSheet("color: #666; font-family: monospace;")
        form_layout.addRow(STRINGS["lbl_uid"], self.lbl_id_display)

        self.edit_nickname = QLineEdit()
        self.edit_nickname.setPlaceholderText(STRINGS["placeholder_nick"])
        form_layout.addRow(STRINGS["lbl_nick"], self.edit_nickname)

        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText(STRINGS["placeholder_bind_email"])
        form_layout.addRow(STRINGS["lbl_email"], self.edit_email)

        self.btn_avatar_pick = QPushButton(STRINGS["btn_change_avatar"])
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
        form_layout.addRow(STRINGS["lbl_avatar"], av_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ddd;")
        form_layout.addRow(line)

        lbl_theme = QLabel(STRINGS["appearance_header"])
        lbl_theme.setStyleSheet("font-weight: bold; font-size: 16px; color: #888;")
        form_layout.addRow(lbl_theme)

        self.btn_color_pick = QPushButton(self.current_accent)
        self.btn_color_pick.setFixedSize(120, 35)
        self.btn_color_pick.clicked.connect(self.open_color_picker)
        form_layout.addRow(STRINGS["lbl_accent"], self.btn_color_pick)

        self.btn_save_settings = QPushButton(STRINGS["btn_save"])
        self.btn_save_settings.setFixedSize(150, 45)
        self.btn_save_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_settings.setObjectName("SaveButton")
        self.btn_save_settings.clicked.connect(self.save_profile_changes)

        layout.addWidget(form_card)
        layout.addSpacing(20)
        layout.addWidget(self.btn_save_settings, 0, Qt.AlignmentFlag.AlignRight)

        self.pending_avatar_b64 = None
        return page

    def load_local_sources(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sources = data.get("sources", [])
                for src in sources:
                    path = src.get('path')
                    stype = src.get('type', 'local')
                    if path:
                        is_web = (stype == 'web')
                        self.monitor_thread.add_source(path, is_web)
                        self.list_sources.addItem(f"{path}")
                self.lbl_list_title.setText(STRINGS["sources_title"].format(self.list_sources.count()))
        except Exception as e:
            print(f"[Config Error] Failed to load local sources: {e}")

    def save_local_sources(self):
        sources = []
        for i in range(self.list_sources.count()):
            item_text = self.list_sources.item(i).text()
            path = item_text.strip()
            stype = 'web' if (path.startswith('http://') or path.startswith('https://')) else 'local'
            sources.append({"path": path, "type": stype})
        data = {"sources": sources, "last_updated": time.time()}
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Config Error] Failed to save local sources: {e}")

    def set_user_info(self, data):
        self.user_data = data
        self.user_id = data.get("user_id", 0)
        nickname = data.get("nickname", "Writer")
        username = data.get("username", "unknown")
        email = data.get("email", "")

        # 设置基础数据（这是服务器已记录的今日字数）
        self.today_base_count = data.get("today_total", 0)
        # 重置偏移量，因为我们刚登录，session_increment 还是 0
        self.daily_increment_offset = 0

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

        if self.page_social:
            self.page_social.set_user_id(self.user_id)
            if self.user_id:
                self.page_social.load_friends()
                self.page_social.refresh_group_list()
                if 'current_group' in data and data['current_group']:
                    self.page_social.restore_group_state(data['current_group'])

    def update_dashboard_stats(self, total_in_monitor, increment, wph):
        self.session_increment = increment

        # 检查是否跨天
        now_date = QDate.currentDate()
        if now_date != self.current_report_date:
            print("[DateChange] New day detected! Resetting daily base.")
            # 跨天了，服务器的 today_base_count 对于新的一天来说应该是 0
            self.today_base_count = 0
            # 关键：我们需要把截至昨天的增量作为偏移量扣除
            # 否则 increment 是从软件启动开始累计的，会把昨天的字数也算进今天
            self.daily_increment_offset = increment

            self.current_report_date = now_date

        # 计算今日实际显示的字数：
        # 服务器原有(0) + (当前总增量 - 今日起始时的总增量)
        real_today_increment = increment - self.daily_increment_offset
        daily_total = self.today_base_count + real_today_increment

        self.lbl_main_count.setText(str(daily_total))
        self.card_main.findChild(QLabel, "CardSub").setText(STRINGS["stat_session"].format(increment))
        self.lbl_speed.setText(str(wph))

    def on_nav_clicked(self, page_idx, btn):
        for b in self.nav_btns.values(): b.setChecked(False)
        btn.setChecked(True)
        self.content_stack.setCurrentIndex(page_idx)

        if page_idx == 1:
            self.sync_data_incrementally()
            self.page_analytics.load_data()
        elif page_idx == 2 and self.page_social and self.user_id:
            self.page_social.load_friends()
            self.page_social.refresh_group_list()

    def sync_data_incrementally(self):
        if not self.network: return

        delta = self.session_increment - self.last_synced_increment
        if delta > 0:
            print(f"[Sync] Sending incremental sync: +{delta}")
            # 【关键修复】发送本地时间戳，让服务器知道这是几点产生的数据
            self.network.send_request({
                "type": "sync_data",
                "increment": delta,
                "duration": 0,
                "timestamp": time.time(),  # 发送客户端时间戳
                # 【新增】明确告诉服务器，这是属于“哪一天”的数据（客户端本地日期）
                "local_date": self.current_report_date.toString(Qt.DateFormat.ISODate)
            })
            self.last_synced_increment = self.session_increment

    def dispatch_network_message(self, data):
        rtype = data.get("type", "")
        if rtype in ["analytics_data", "details_data"]:
            self.page_analytics.handle_response(data)
        elif rtype in ["search_user_response", "get_friends_response",
                       "group_list_response", "create_group_response", "join_group_response",
                       "group_detail_response", "group_msg_push", "sprint_status_push",
                       "refresh_friends", "refresh_friend_requests", "friend_requests_response",
                       "respond_friend_response", "refresh_groups"]:
            if self.page_social:
                self.page_social.handle_network_msg(data)

    def closeEvent(self, event):
        self.save_local_sources()
        if self.network:
            self.sync_data_incrementally()
        import time as t
        t.sleep(0.2)
        event.accept()

    def open_avatar_picker(self):
        file_path, _ = QFileDialog.getOpenFileName(self, STRINGS["dialog_select_avatar"], "",
                                                   STRINGS["dialog_img_files"])
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
            QMessageBox.warning(self, STRINGS["warn_title"], STRINGS["msg_nick_empty"])
            return
        payload = {"type": "update_profile", "nickname": new_nickname, "email": new_email}
        if self.pending_avatar_b64: payload["avatar_data"] = self.pending_avatar_b64
        if self.network:
            self.network.send_request(payload)
            self.lbl_title.setText(f"Hi, {new_nickname}")
            if self.pending_avatar_b64: self.lbl_avatar.setPixmap(self.lbl_avatar_preview.pixmap())
            QMessageBox.information(self, STRINGS["title_sent"], STRINGS["msg_profile_sent"])

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
        self.btn_theme_toggle.setText(STRINGS["theme_light"] if self.is_night else STRINGS["theme_dark"])
        self.apply_theme()

    def add_local_source(self):
        file_path, _ = QFileDialog.getOpenFileName(self, STRINGS["dialog_select_doc"], "", STRINGS["dialog_doc_files"])
        if file_path:
            self._perform_add(file_path, False)
            self.save_local_sources()

    def add_web_source(self):
        text, ok = QInputDialog.getText(self, STRINGS["dialog_add_web_title"], STRINGS["dialog_add_web_label"])
        if ok and text:
            self._perform_add(text.strip(), True)
            self.save_local_sources()

    def _perform_add(self, path, is_web):
        if self.monitor_thread.add_source(path, is_web):
            self.list_sources.addItem(f"{path}")
            self.lbl_list_title.setText(STRINGS["sources_title"].format(self.list_sources.count()))

    def show_list_context_menu(self, pos):
        item = self.list_sources.itemAt(pos)
        if item:
            menu = QMenu()
            menu.addAction(f"🗑️ {STRINGS['menu_remove']}").triggered.connect(lambda: self.delete_source(item))
            menu.exec(self.list_sources.mapToGlobal(pos))

    def delete_source(self, item):
        path = item.text()
        self.monitor_thread.remove_source(path)
        self.list_sources.takeItem(self.list_sources.row(item))
        self.lbl_list_title.setText(STRINGS["sources_title"].format(self.list_sources.count()))
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
        self.lbl_list_title = QLabel(STRINGS["sources_title"].format("0"))
        self.lbl_list_title.setObjectName("ListTitle")
        layout.addWidget(self.lbl_list_title)
        self.list_sources = QListWidget()
        self.list_sources.setObjectName("SourceList")
        self.list_sources.setFrameShape(QFrame.Shape.NoFrame)
        self.list_sources.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_sources.customContextMenuRequested.connect(self.show_list_context_menu)
        layout.addWidget(self.list_sources)
        btns_layout = QHBoxLayout()
        self.btn_local = QPushButton(STRINGS["btn_local"])
        self.btn_local.setObjectName("ActionBtnLocal")
        self.btn_local.clicked.connect(self.add_local_source)
        self.btn_web = QPushButton(STRINGS["btn_online"])
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
        top_bar.addWidget(QLabel(STRINGS["timer_title"]))
        top_bar.addStretch()
        self.chk_pomo_float = QCheckBox(STRINGS["check_float"])
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