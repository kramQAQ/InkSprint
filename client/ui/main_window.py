from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QFileDialog, QInputDialog, QListWidget, QAbstractItemView, QMenu,
                             QSizePolicy, QSpinBox, QCheckBox)
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QAction, QColor, QPixmap
import os
import sys

# === 🛡️ 路径与导入修复区 ===
client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

try:
    from .theme import LIGHT_THEME, DARK_THEME
    from core.file_monitor import FileMonitor
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    raise e


# ============================

class MainWindow(QWidget):
    switch_float_signal = pyqtSignal()
    pomo_float_toggle_signal = pyqtSignal(bool)
    pomo_update_signal = pyqtSignal(str)

    def __init__(self, is_night=False):
        super().__init__()
        self.setWindowTitle("InkSprint Dashboard")
        self.resize(1050, 720)

        self.current_theme = DARK_THEME if is_night else LIGHT_THEME

        self.monitor_thread = FileMonitor()
        self.monitor_thread.stats_updated.connect(self.update_dashboard)
        self.monitor_thread.start()

        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.update_pomodoro)
        self.pomo_seconds = 25 * 60
        self.pomo_is_running = False
        self.pomo_mode = "timer"

        self.setup_ui()
        self.apply_theme()
        self.load_avatar()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. 侧边栏 ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 40, 20, 40)

        # [修改] 顶部放置头像和用户名 (原Logo位置)
        user_profile = QFrame()
        user_profile.setObjectName("UserProfile")
        user_layout = QHBoxLayout(user_profile)
        user_layout.setContentsMargins(0, 0, 0, 0)  # 紧凑布局
        user_layout.setSpacing(12)

        self.lbl_avatar = QLabel()
        self.lbl_avatar.setObjectName("UserAvatar")
        self.lbl_avatar.setFixedSize(48, 48)  # 稍微加大头像
        self.lbl_avatar.setScaledContents(True)

        self.lbl_username = QLabel("Guest")
        self.lbl_username.setObjectName("SidebarUserName")  # 使用新ID以便独立样式

        user_layout.addWidget(self.lbl_avatar)
        user_layout.addWidget(self.lbl_username)
        user_layout.addStretch()

        side_layout.addWidget(user_profile)
        side_layout.addSpacing(40)  # 头像和导航栏之间的间距

        # 导航按钮
        for text in ["🏠  Dashboard", "📊  Analytics", "👥  Friends", "⚙️  Settings"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            side_layout.addWidget(btn)

        side_layout.addStretch()

        # 底部留空或放其他信息，原用户信息已移至顶部
        # ...

        # --- 2. 内容区 ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # [修改] 标题从 Overview 改为 Hi, User
        self.lbl_title = QLabel("Hi, Guest")
        self.lbl_title.setObjectName("PageTitle")
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        self.btn_float = QPushButton("🚀")
        self.btn_float.setFixedSize(40, 40)
        self.btn_float.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_float.setToolTip("Float Mode")
        self.btn_float.setObjectName("FloatButton")
        self.btn_float.clicked.connect(self.switch_float_signal.emit)
        header_layout.addWidget(self.btn_float)

        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(40, 40)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip("Always on Top")
        self.btn_pin.setObjectName("PinButton")
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.btn_pin)

        header_layout.addSpacing(8)

        self.btn_theme_toggle = QPushButton("🌙 Mode")
        self.btn_theme_toggle.setObjectName("ThemeToggle")
        self.btn_theme_toggle.setFixedSize(100, 40)
        self.btn_theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        content_layout.addLayout(header_layout)

        # Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        self.card_main = self.create_stat_card("Session Words", "0", "Keep pushing!", True)
        self.card_sub = self.create_stat_card("Speed (WPH)", "0", "Words per hour", False)

        cards_layout.addWidget(self.card_main, 2)
        cards_layout.addWidget(self.card_sub, 1)
        content_layout.addLayout(cards_layout)

        # Bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        sources_card = QFrame()
        sources_card.setObjectName("SourcesCard")
        self.add_shadow(sources_card)
        sources_layout = QVBoxLayout(sources_card)
        sources_layout.setContentsMargins(20, 20, 20, 20)
        sources_layout.setSpacing(15)

        self.lbl_list_title = QLabel("Active Sources (0/10)")
        self.lbl_list_title.setObjectName("ListTitle")
        sources_layout.addWidget(self.lbl_list_title)

        self.list_sources = QListWidget()
        self.list_sources.setObjectName("SourceList")
        self.list_sources.setFrameShape(QFrame.Shape.NoFrame)
        self.list_sources.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.list_sources.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_sources.customContextMenuRequested.connect(self.show_list_context_menu)
        self.list_sources.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        sources_layout.addWidget(self.list_sources)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)
        self.btn_local = QPushButton("➕ Local")
        self.btn_local.setObjectName("ActionBtnLocal")
        self.btn_local.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_local.clicked.connect(self.add_local_source)
        self.btn_local.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_web = QPushButton("🌐 Tencent")
        self.btn_web.setObjectName("ActionBtnWeb")
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(self.add_web_source)
        self.btn_web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        for btn in [self.btn_local, self.btn_web]:
            btn.setFixedHeight(45)
            action_layout.addWidget(btn)
        sources_layout.addLayout(action_layout)

        # Pomodoro Card
        self.card_pomodoro = self.create_pomodoro_card()

        bottom_layout.addWidget(sources_card, 2)
        bottom_layout.addWidget(self.card_pomodoro, 1)

        content_layout.addLayout(bottom_layout)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_container)

        self.sources_card = sources_card

    def eventFilter(self, source, event):
        if source == self.lbl_pomo_time and event.type() == QEvent.Type.MouseButtonDblClick:
            if self.pomo_mode == "timer" and not self.pomo_is_running:
                self.set_custom_time()
            return True
        return super().eventFilter(source, event)

    def set_custom_time(self):
        mins, ok = QInputDialog.getInt(self, "Set Timer", "Minutes (0-99):", 25, 0, 99)
        if ok:
            self.pomo_seconds = mins * 60
            self.update_display_time()

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

    def create_pomodoro_card(self):
        card = QFrame()
        card.setObjectName("PomodoroCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)

        # 顶部：标题 + (减/加按钮) + 悬浮窗开关
        top_bar = QHBoxLayout()
        lbl_title = QLabel("Focus Timer")
        lbl_title.setObjectName("PomoTitle")
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()

        # 模式切换按钮 (-)
        self.btn_mode_timer = QPushButton("-")
        self.btn_mode_timer.setFixedSize(30, 30)
        self.btn_mode_timer.setObjectName("PomoModeBtn")
        self.btn_mode_timer.setToolTip("Timer Mode")
        self.btn_mode_timer.clicked.connect(lambda: self.set_pomodoro_mode("timer"))

        # 模式切换按钮 (+)
        self.btn_mode_stopwatch = QPushButton("+")
        self.btn_mode_stopwatch.setFixedSize(30, 30)
        self.btn_mode_stopwatch.setObjectName("PomoModeBtn")
        self.btn_mode_stopwatch.setToolTip("Stopwatch Mode")
        self.btn_mode_stopwatch.clicked.connect(lambda: self.set_pomodoro_mode("stopwatch"))

        top_bar.addWidget(self.btn_mode_timer)
        top_bar.addWidget(self.btn_mode_stopwatch)

        top_bar.addSpacing(5)

        # Float Checkbox
        self.chk_pomo_float = QCheckBox("Float")
        self.chk_pomo_float.setObjectName("PomoFloatCheck")
        self.chk_pomo_float.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_pomo_float.toggled.connect(self.pomo_float_toggle_signal.emit)
        top_bar.addWidget(self.chk_pomo_float)

        layout.addLayout(top_bar)

        layout.addStretch()

        # 时间显示
        self.lbl_pomo_time = QLabel("25:00")
        self.lbl_pomo_time.setObjectName("PomoTime")
        self.lbl_pomo_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pomo_time.setToolTip("Double click to set time")
        self.lbl_pomo_time.installEventFilter(self)
        self.lbl_pomo_time.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.lbl_pomo_time)

        layout.addStretch()

        # 控制按钮
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(15)

        self.btn_pomo_start = QPushButton("▶")
        self.btn_pomo_start.setObjectName("PomoStartBtn")
        self.btn_pomo_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomo_start.setFixedSize(50, 50)
        self.btn_pomo_start.clicked.connect(self.toggle_pomodoro)

        self.btn_pomo_reset = QPushButton("↺")
        self.btn_pomo_reset.setObjectName("PomoResetBtn")
        self.btn_pomo_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomo_reset.setFixedSize(50, 50)
        self.btn_pomo_reset.clicked.connect(self.reset_pomodoro)

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_pomo_start)
        ctrl_layout.addWidget(self.btn_pomo_reset)
        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

        self.add_shadow(card)
        return card

    def set_pomodoro_mode(self, mode):
        self.pomo_mode = mode
        self.reset_pomodoro()
        t = self.current_theme
        active_style = f"background-color: {t['accent']}; color: white; border: none; border-radius: 5px; font-weight: bold;"
        inactive_style = f"background-color: {t['input_bg']}; color: {t['text_main']}; border: none; border-radius: 5px;"

        if mode == "timer":
            self.btn_mode_timer.setStyleSheet(active_style)
            self.btn_mode_stopwatch.setStyleSheet(inactive_style)
        else:
            self.btn_mode_timer.setStyleSheet(inactive_style)
            self.btn_mode_stopwatch.setStyleSheet(active_style)

    def toggle_pomodoro(self):
        if self.pomo_is_running:
            self.pomo_timer.stop()
            self.btn_pomo_start.setText("▶")
            self.pomo_is_running = False
        else:
            self.pomo_timer.start(1000)
            self.btn_pomo_start.setText("⏸")
            self.pomo_is_running = True

    def reset_pomodoro(self):
        self.pomo_timer.stop()
        self.pomo_is_running = False
        self.btn_pomo_start.setText("▶")
        if self.pomo_mode == "timer":
            self.pomo_seconds = 25 * 60
            self.update_display_time()
        else:
            self.pomo_seconds = 0
            self.update_display_time()

    def update_pomodoro(self):
        if self.pomo_mode == "timer":
            if self.pomo_seconds > 0:
                self.pomo_seconds -= 1
            else:
                self.pomo_timer.stop()
                self.pomo_is_running = False
                self.btn_pomo_start.setText("▶")
        else:
            self.pomo_seconds += 1
        self.update_display_time()

    def update_display_time(self):
        mins, secs = divmod(self.pomo_seconds, 60)
        hours, mins_remainder = divmod(mins, 60)
        if hours > 0:
            time_str = f"{hours:02d}:{mins_remainder:02d}:{secs:02d}"
        else:
            time_str = f"{mins:02d}:{secs:02d}"
        self.lbl_pomo_time.setText(time_str)
        self.pomo_update_signal.emit(time_str)

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)
        widget._shadow_effect = shadow

    def toggle_always_on_top(self):
        if self.btn_pin.isChecked():
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()

    def show_list_context_menu(self, pos):
        item = self.list_sources.itemAt(pos)
        if item:
            menu = QMenu()
            bg = "#2d2d2d" if self.current_theme['name'] == 'dark' else "#ffffff"
            fg = "white" if self.current_theme['name'] == 'dark' else "black"
            menu.setStyleSheet(f"QMenu {{ background-color: {bg}; color: {fg}; border: 1px solid #555; }}")

            del_action = QAction("🗑️ Remove", self)
            del_action.triggered.connect(lambda: self.delete_source(item))
            menu.addAction(del_action)
            menu.exec(self.list_sources.mapToGlobal(pos))

    def delete_source(self, item):
        text = item.text()
        path = text.split("  ", 1)[1] if "  " in text else text
        self.monitor_thread.remove_source(path)
        row = self.list_sources.row(item)
        self.list_sources.takeItem(row)
        current_count = self.list_sources.count()
        self.lbl_list_title.setText(f"Active Sources ({current_count}/10)")

    def add_local_source(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Document", "", "Documents (*.docx *.txt)")
        if file_path:
            self._perform_add(file_path, is_web=False)

    def add_web_source(self):
        text, ok = QInputDialog.getText(self, "Add Tencent Doc", "Paste Public URL:")
        if ok and text:
            self._perform_add(text.strip(), is_web=True)

    def _perform_add(self, path, is_web):
        success = self.monitor_thread.add_source(path, is_web)
        if success:
            icon = "🌐" if is_web else "📄"
            self.list_sources.addItem(f"{icon}  {path}")
            count = self.list_sources.count()
            self.lbl_list_title.setText(f"Active Sources ({count}/10)")

    def update_dashboard(self, total, increment, wph):
        self.lbl_main_count.setText(str(increment))
        self.lbl_speed.setText(str(wph))

    def toggle_theme(self):
        if self.current_theme == LIGHT_THEME:
            self.current_theme = DARK_THEME
            self.btn_theme_toggle.setText("☀ Light")
        else:
            self.current_theme = LIGHT_THEME
            self.btn_theme_toggle.setText("🌙 Dark")
        self.apply_theme()

    def load_avatar(self):
        avatar_path = "default_avatar.jpg"
        if os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path)
            self.lbl_avatar.setPixmap(pixmap)
        else:
            # 默认灰色圆形占位符
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            self.lbl_avatar.setStyleSheet("background-color: #cccccc; border-radius: 24px;")
            # 如果有图片会覆盖背景色

    def set_user_info(self, username):
        self.lbl_username.setText(username)
        # [新增] 更新主标题
        self.lbl_title.setText(f"Hi, {username}")

    def apply_theme(self):
        t = self.current_theme
        shadow_color = QColor(0, 0, 0, 30) if t['name'] == 'light' else QColor(0, 0, 0, 180)
        for widget in [self.card_main, self.card_sub, self.card_pomodoro, self.sources_card]:
            if hasattr(widget, '_shadow_effect'):
                widget._shadow_effect.setColor(shadow_color)

        val_color = "#2D3436" if t['name'] == 'light' else "#FFFFFF"
        sub_color = t['text_sub']
        scrollbar_track = "#ffffff" if t['name'] == 'light' else "#000000"

        self.setStyleSheet(f"""
            QWidget {{ background-color: {t['window_bg']}; font-family: 'Segoe UI', sans-serif; }}
            QFrame#Sidebar {{ background-color: {t['card_bg']}; border-right: 1px solid {t['border']}; }}

            /* Sidebar User Info (Top Left) */
            QLabel#UserAvatar {{ background-color: #cccccc; border-radius: 24px; }}
            QFrame#UserProfile {{ background-color: transparent; border: none; }}
            QLabel#SidebarUserName {{ 
                color: {t['accent']}; /* 绿色文字 */
                font-weight: 900; 
                font-size: 20px; 
                background-color: transparent; 
            }}

            QPushButton#NavButton {{ text-align: left; padding: 12px 20px; border-radius: 10px; border: none; color: {t['text_sub']}; font-weight: 600; font-size: 15px; background: transparent; }}
            QPushButton#NavButton:hover {{ background-color: {t['input_bg']}; color: {t['text_main']}; }}
            QPushButton#NavButton:checked {{ background-color: {t['input_bg']}; color: {t['accent']}; }}

            /* Main Header Title */
            QLabel#PageTitle {{ font-size: 32px; font-weight: bold; color: {t['text_main']}; }}

            QLabel#ListTitle {{ font-weight: bold; font-size: 16px; margin-top: 5px; margin-bottom: 5px; color: {t['text_main']}; background-color: transparent; }}

            QPushButton#ThemeToggle, QPushButton#PinButton, QPushButton#FloatButton, QPushButton#PomoSwitch {{ 
                border: 1px solid {t['border']}; 
                border-radius: 10px; 
                color: {t['text_main']}; 
                background-color: {t['card_bg']}; 
                text-align: center; margin: 0px; padding: 0px;
            }}
            QPushButton#PinButton:checked {{ background-color: {t['accent']}; color: white; border: none; }}

            QFrame#StatCard, QFrame#SourcesCard, QFrame#PomodoroCard {{ 
                background-color: {t['card_bg']}; border-radius: 20px; 
            }}
            QFrame#StatCardPrimary {{ background-color: {t['accent']}; border-radius: 20px; color: white; }}

            QFrame#StatCard QLabel, QFrame#StatCardPrimary QLabel, QFrame#PomodoroCard QLabel {{ background-color: transparent; }}

            QFrame#StatCardPrimary QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: white; }}
            QFrame#StatCardPrimary QLabel#CardTitle {{ font-size: 16px; opacity: 0.9; color: white; }}
            QFrame#StatCardPrimary QLabel#CardSub {{ font-size: 14px; opacity: 0.8; color: white; }}

            QFrame#StatCard QLabel#CardValue {{ font-size: 60px; font-weight: bold; color: {val_color}; }}
            QFrame#StatCard QLabel#CardTitle {{ font-size: 16px; color: {sub_color}; }}
            QFrame#StatCard QLabel#CardSub {{ font-size: 14px; color: {sub_color}; }}

            QLabel#PomoTitle {{ font-size: 16px; color: {sub_color}; font-weight: bold; }}
            QLabel#PomoTime {{ font-size: 56px; font-weight: bold; color: {t['accent']}; }}
            QPushButton#PomoStartBtn {{ background-color: {t['accent']}; color: white; border-radius: 25px; font-size: 20px; border: none; }}
            QPushButton#PomoResetBtn {{ background-color: {t['input_bg']}; color: {t['text_main']}; border-radius: 25px; font-size: 20px; border: none; }}
            QPushButton#PomoStartBtn:hover {{ background-color: {t['accent_hover']}; }}

            QCheckBox#PomoFloatCheck {{ color: {t['text_sub']}; spacing: 5px; }}
            QCheckBox::indicator {{ width: 15px; height: 15px; }}
            QCheckBox::indicator:unchecked {{ border: 1px solid {t['text_sub']}; background: transparent; border-radius: 3px; }}
            QCheckBox::indicator:checked {{ background-color: {t['accent']}; border: 1px solid {t['accent']}; border-radius: 3px; }}

            QListWidget#SourceList {{ background-color: transparent; border: none; color: {t['text_main']}; font-size: 14px; outline: 0; }}
            QListWidget::item {{ padding: 8px; border-radius: 5px; border: none; }}
            QListWidget::item:selected {{ background-color: {t['input_bg']}; color: {t['accent']}; border: none; }}

            QScrollBar:vertical {{ border: none; background: {scrollbar_track}; width: 8px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: #bdc3c7; min-height: 20px; border-radius: 4px; }}
            QScrollBar::handle:vertical:hover {{ background: #a6acb3; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: none; height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {scrollbar_track}; }}

            QScrollBar:horizontal {{ border: none; background: {scrollbar_track}; height: 8px; margin: 0px; }}
            QScrollBar::handle:horizontal {{ background: #bdc3c7; min-width: 20px; border-radius: 4px; }}
            QScrollBar::handle:horizontal:hover {{ background: #a6acb3; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: none; width: 0px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {scrollbar_track}; }}

            QPushButton#ActionBtnLocal, QPushButton#ActionBtnWeb {{ background-color: {t['input_bg']}; color: {t['text_main']}; border: 1px solid {t['border']}; border-radius: 10px; font-size: 14px; font-weight: bold; }}
            QPushButton#ActionBtnLocal:hover, QPushButton#ActionBtnWeb:hover {{ background-color: {t['card_bg']}; color: {t['accent']}; border: 1px solid {t['accent']}; }}
        """)
        # 刷新模式按钮样式
        self.set_pomodoro_mode(self.pomo_mode)