from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QFileDialog, QInputDialog, QListWidget, QAbstractItemView, QMenu,
                             QSizePolicy, QCheckBox, QLineEdit, QStackedWidget, QColorDialog, QFormLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QRegularExpression
from PyQt6.QtGui import QAction, QColor, QPixmap, QRegularExpressionValidator
import os
import sys

# === 🛡️ 路径与导入修复区 ===
client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

try:
    from .theme import ThemeManager, DEFAULT_ACCENT
    from .float_window import FloatWindow
    from core.file_monitor import FileMonitor
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    raise e


class MainWindow(QWidget):
    switch_float_signal = pyqtSignal()
    pomo_float_toggle_signal = pyqtSignal(bool)
    pomo_update_signal = pyqtSignal(str)

    def __init__(self, is_night=False):
        super().__init__()
        self.setWindowTitle("InkSprint Dashboard")
        self.resize(1050, 720)

        # 初始化主题状态
        self.is_night = is_night
        self.current_accent = DEFAULT_ACCENT
        self.current_theme = ThemeManager.get_theme(self.is_night, self.current_accent)

        # 核心线程
        self.monitor_thread = FileMonitor()
        self.monitor_thread.stats_updated.connect(self.update_dashboard_stats)
        self.monitor_thread.start()

        # 番茄钟
        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.update_pomodoro_tick)
        self.pomo_seconds = 25 * 60
        self.pomo_is_running = False
        self.pomo_mode = "timer"

        # 悬浮窗
        self.float_window = FloatWindow(self.current_accent)
        self.float_window.restore_signal.connect(self.restore_from_float)

        # 连接信号
        self.switch_float_signal.connect(self.switch_to_float)
        self.pomo_float_toggle_signal.connect(self.float_window.set_mode)
        self.monitor_thread.stats_updated.connect(self.float_window.update_data)
        self.pomo_update_signal.connect(self.float_window.update_timer)

        self.setup_ui()
        self.apply_theme()
        self.load_avatar()

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

        # 导航按钮组
        self.nav_btns = {}
        nav_items = [("🏠  Dashboard", 0), ("📊  Analytics", 0), ("👥  Friends", 0), ("⚙️  Settings", 1)]

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

        # === 右侧内容区 (Stack) ===
        self.content_stack = QStackedWidget()

        # 页面 0: Dashboard
        self.page_dashboard = self.create_dashboard_page()
        self.content_stack.addWidget(self.page_dashboard)

        # 页面 1: Settings
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
        self.lbl_title = QLabel("Hi, Guest")
        self.lbl_title.setObjectName("PageTitle")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        # 功能按钮
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

        # 数据卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        self.card_main = self.create_stat_card("Session Words", "0", "Keep pushing!", True)
        self.card_sub = self.create_stat_card("Speed (WPH)", "0", "Words per hour", False)
        cards_layout.addWidget(self.card_main, 2)
        cards_layout.addWidget(self.card_sub, 1)
        layout.addLayout(cards_layout)

        # 底部 (源列表 + 番茄钟)
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
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)

        self.btn_color_pick = QPushButton(self.current_accent)
        self.btn_color_pick.setFixedSize(120, 35)
        self.btn_color_pick.clicked.connect(self.open_color_picker)

        lbl_hint = QLabel("Choose your theme accent color")
        lbl_hint.setStyleSheet("color: #888;")

        form_layout.addRow("Theme Accent Color:", self.btn_color_pick)
        form_layout.addRow("", lbl_hint)

        layout.addWidget(form_card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 50))
        form_card.setGraphicsEffect(shadow)

        return page

    # --- UI 组件创建辅助函数 ---

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
        self.lbl_pomo_title = QLabel("Focus Timer")
        self.lbl_pomo_title.setObjectName("PomoTitle")
        top_bar.addWidget(self.lbl_pomo_title)
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

    # --- 逻辑处理 ---

    def on_nav_clicked(self, page_idx, btn):
        for b in self.nav_btns.values():
            b.setChecked(False)
        btn.setChecked(True)
        self.content_stack.setCurrentIndex(page_idx)

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

    def update_dashboard_stats(self, total, increment, wph):
        self.lbl_main_count.setText(str(increment))
        self.lbl_speed.setText(str(wph))

    def add_local_source(self):
        # [修改] 使用 getOpenFileNames 替换 getOpenFileName 以支持多选
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Docs", "", "Documents (*.docx *.txt)")
        if file_paths:
            # 遍历选中的文件列表
            for path in file_paths:
                self._perform_add(path, False)

    def add_web_source(self):
        text, ok = QInputDialog.getText(self, "Add Web", "URL:")
        if ok and text: self._perform_add(text.strip(), True)

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
        top = self.btn_pin.isChecked()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, top)
        self.show()

    def set_user_info(self, username):
        self.lbl_title.setText(f"Hi, {username}")

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)
        widget._shadow = shadow

    def load_avatar(self):
        if os.path.exists("default_avatar.jpg"):
            self.lbl_avatar.setPixmap(QPixmap("default_avatar.jpg"))
        else:
            self.lbl_avatar.setStyleSheet("background-color: #cccccc; border-radius: 24px;")

    def apply_pomo_btn_style(self):
        t = self.current_theme
        active = f"background-color: {t['accent']}; color: white; border:none; border-radius: 5px; font-weight: bold;"
        inactive = f"background-color: {t['input_bg']}; color: {t['text_main']}; border:none; border-radius: 5px;"

        self.btn_mode_timer.setStyleSheet(active if self.pomo_mode == "timer" else inactive)
        self.btn_mode_stopwatch.setStyleSheet(active if self.pomo_mode == "stopwatch" else inactive)

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

        # 滚动条颜色定义
        sb_handle = "#555555" if t['name'] == 'light' else "#AAAAAA"
        sb_track = "transparent"

        self.setStyleSheet(f"""
            QWidget {{ background-color: {t['window_bg']}; color: {t['text_main']}; font-family: 'Segoe UI', sans-serif; }}
            QFrame#Sidebar {{ background-color: {t['card_bg']}; border-right: 1px solid {t['border']}; }}

            QLabel#UserAvatar {{ background-color: #ccc; border-radius: 24px; }}
            QLabel#SidebarAppName {{ color: {t['accent']}; font-weight: 900; font-size: 22px; background: transparent; }}

            /* Navigation */
            QPushButton#NavButton {{ text-align: left; padding: 12px 20px; border-radius: 10px; border: none; color: {t['text_sub']}; font-weight: 600; font-size: 15px; background: transparent; }}
            QPushButton#NavButton:hover {{ background-color: {t['input_bg']}; color: {t['text_main']}; }}
            QPushButton#NavButton:checked {{ background-color: {t['input_bg']}; color: {t['accent']}; }}

            QLabel#PageTitle {{ font-size: 32px; font-weight: bold; color: {t['text_main']}; }}
            QLabel#ListTitle {{ font-weight: bold; font-size: 16px; margin: 5px 0; color: {t['text_main']}; background: transparent; }}

            /* Buttons */
            QPushButton#ThemeToggle, QPushButton#PinButton, QPushButton#FloatButton, QPushButton#PomoSwitch {{ 
                border: 1px solid {t['border']}; border-radius: 10px; color: {t['text_main']}; background: {t['card_bg']}; 
            }}
            QPushButton#PinButton:checked {{ background: {t['accent']}; color: white; border: none; }}

            /* Cards */
            QFrame#StatCard, QFrame#SourcesCard, QFrame#PomodoroCard, QFrame#SettingsCard {{ background: {t['card_bg']}; border-radius: 20px; }}
            QFrame#StatCardPrimary {{ background: {t['accent']}; border-radius: 20px; color: white; }}

            /* Card Text */
            QFrame#StatCard QLabel, QFrame#StatCardPrimary QLabel, QFrame#PomodoroCard QLabel {{ background: transparent; }}
            QFrame#StatCardPrimary QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: white; }}
            QFrame#StatCardPrimary QLabel#CardTitle {{ font-size: 16px; opacity: 0.9; color: white; }}
            QFrame#StatCardPrimary QLabel#CardSub {{ font-size: 14px; opacity: 0.8; color: white; }}

            QFrame#StatCard QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: {val_color}; }}
            QFrame#StatCard QLabel#CardTitle {{ font-size: 16px; color: {sub_color}; }}

            QLabel#PomoTitle {{ font-size: 16px; color: {t['text_main']}; font-weight: bold; }}

            QLineEdit#PomoTimeEdit {{ font-size: 42px; font-weight: bold; color: {t['accent']}; background: transparent; border: none; }}

            QPushButton#PomoStartBtn {{ background: {t['accent']}; color: white; border-radius: 25px; font-size: 20px; border: none; }}
            QPushButton#PomoResetBtn {{ background: {t['input_bg']}; color: {t['text_main']}; border-radius: 25px; font-size: 20px; border: none; }}

            /* Checkbox */
            QCheckBox#PomoFloatCheck {{ color: {t['text_sub']}; spacing: 5px; }}
            QCheckBox::indicator:checked {{ background: {t['accent']}; border: 1px solid {t['accent']}; border-radius: 3px; }}

            /* List */
            QListWidget#SourceList {{ 
                background: transparent; 
                border: none; 
                color: {t['text_main']}; 
                font-size: 14px; 
                outline: 0px;  /* 关键：去除焦点虚线框/黑白框 */
            }}
            QListWidget::item {{ padding: 8px; border-radius: 5px; border: none; }}
            QListWidget::item:selected {{ 
                background: {t['input_bg']}; 
                color: {t['accent']}; 
                border: none; /* 再次确保无边框 */
            }}

            /* ScrollBar Customization */
            QScrollBar:vertical {{ border: none; background: {sb_track}; width: 8px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {sb_handle}; min-height: 20px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

            /* Horizontal ScrollBar */
            QScrollBar:horizontal {{ border: none; background: {sb_track}; height: 8px; margin: 0px; }}
            QScrollBar::handle:horizontal {{ background: {sb_handle}; min-width: 20px; border-radius: 4px; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

            /* Actions */
            QPushButton#ActionBtnLocal, QPushButton#ActionBtnWeb {{ background: {t['input_bg']}; color: {t['text_main']}; border: 1px solid {t['border']}; border-radius: 10px; font-weight: bold; }}
            QPushButton#ActionBtnLocal:hover {{ background: {t['card_bg']}; color: {t['accent']}; border: 1px solid {t['accent']}; }}
        """)
        self.apply_pomo_btn_style()