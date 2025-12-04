from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.theme import LIGHT_THEME, DARK_THEME


class LoginWindow(QWidget):
    # 信号定义：
    # login_signal: 发送 (用户名, 密码)
    # theme_changed: 发送 (是否是黑夜模式: bool)
    login_signal = pyqtSignal(str, str)
    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("InkSprint")
        self.resize(360, 520)

        # 默认主题
        self.current_theme = LIGHT_THEME

        # 无边框设置
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 卡片容器
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 40, 30, 40)
        card_layout.setSpacing(20)

        # 阴影
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setYOffset(5)
        self.card.setGraphicsEffect(self.shadow_effect)

        # 顶部栏
        top_bar = QHBoxLayout()
        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setFixedSize(30, 30)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)

        top_bar.addWidget(self.btn_theme)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_close)
        card_layout.addLayout(top_bar)

        # Logo
        self.lbl_logo = QLabel("InkSprint")
        self.lbl_logo.setObjectName("Logo")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_logo)

        self.lbl_slogan = QLabel("Focus & Create")
        self.lbl_slogan.setObjectName("Slogan")
        self.lbl_slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_slogan)

        card_layout.addSpacing(20)

        # 输入框
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Username")
        self.input_user.setFixedHeight(45)

        self.input_pwd = QLineEdit()
        self.input_pwd.setPlaceholderText("Password")
        self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pwd.setFixedHeight(45)

        card_layout.addWidget(self.input_user)
        card_layout.addWidget(self.input_pwd)

        card_layout.addSpacing(10)

        # 登录按钮
        self.btn_login = QPushButton("LOGIN")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.on_login_clicked)
        card_layout.addWidget(self.btn_login)

        card_layout.addStretch()
        main_layout.addWidget(self.card)

    def toggle_theme(self):
        if self.current_theme == LIGHT_THEME:
            self.current_theme = DARK_THEME
            self.btn_theme.setText("☀")
            self.theme_changed.emit(True)  # 发送信号：切换到了黑夜
        else:
            self.current_theme = LIGHT_THEME
            self.btn_theme.setText("🌙")
            self.theme_changed.emit(False)  # 发送信号：切换到了白天
        self.apply_theme()

    def apply_theme(self):
        t = self.current_theme

        # 阴影颜色随主题变化
        self.shadow_effect.setColor(Qt.GlobalColor.black if t["name"] == "dark" else Qt.GlobalColor.gray)

        style = f"""
            LoginWindow {{ background: transparent; }}
            QFrame#LoginCard {{ background-color: {t['card_bg']}; border-radius: 20px; }}
            QLabel#Logo {{ font-family: 'Segoe UI'; font-size: 28px; font-weight: 800; color: {t['text_main']}; }}
            QLabel#Slogan {{ font-family: 'Segoe UI'; font-size: 14px; color: {t['accent']}; letter-spacing: 2px; }}
            QLineEdit {{ background-color: {t['input_bg']}; border: 1px solid {t['input_bg']}; border-radius: 12px; padding: 0 15px; color: {t['text_main']}; }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; background-color: {t['card_bg']}; }}
            QPushButton {{ border: none; color: {t['text_sub']}; font-size: 16px; background: transparent; }}
            QPushButton:hover {{ background-color: {t['input_bg']}; color: {t['text_main']}; }}
            QPushButton[text="LOGIN"] {{ background-color: {t['accent']}; color: #FFFFFF; font-weight: bold; border-radius: 25px; margin-top: 10px; }}
            QPushButton[text="LOGIN"]:hover {{ background-color: {t['accent_hover']}; }}
        """
        self.setStyleSheet(style)

    def on_login_clicked(self):
        username = self.input_user.text().strip()
        password = self.input_pwd.text().strip()
        if username and password:
            self.login_signal.emit(username, password)

    # 窗口拖动逻辑
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()