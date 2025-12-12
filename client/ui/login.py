from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QHBoxLayout, QGraphicsDropShadowEffect,
                             QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIntValidator
from .theme import ThemeManager
from .localization import STRINGS  # 导入汉化配置


class LoginWindow(QWidget):
    # 信号定义
    login_signal = pyqtSignal(str, str)  # (username, password)
    register_signal = pyqtSignal(str, str, str)  # (username, password, email)
    send_code_signal = pyqtSignal(str)  # (username) - 请求发送验证码
    reset_pwd_signal = pyqtSignal(str, str, str)  # (username, code, new_password)

    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["window_title_auth"])
        self.resize(380, 560)

        self.is_night = False
        self.current_theme = ThemeManager.get_theme(self.is_night)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 主卡片
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(30, 40, 30, 40)
        self.card_layout.setSpacing(10)

        # 阴影
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setYOffset(5)
        self.card.setGraphicsEffect(self.shadow_effect)

        # 顶部控制栏 (主题切换 & 关闭)
        top_bar = QHBoxLayout()
        icon_text = "☀" if self.is_night else "🌙"
        self.btn_theme = QPushButton(icon_text)
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
        self.card_layout.addLayout(top_bar)

        # 头部 Logo
        self.lbl_logo = QLabel("InkSprint")
        self.lbl_logo.setObjectName("Logo")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addWidget(self.lbl_logo)

        self.lbl_slogan = QLabel("Focus & Create")
        self.lbl_slogan.setObjectName("Slogan")
        self.lbl_slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addWidget(self.lbl_slogan)
        self.card_layout.addSpacing(20)

        # --- 多页面区域 ---
        self.stack = QStackedWidget()

        # Page 0: 登录
        self.page_login = QWidget()
        self.init_login_page()
        self.stack.addWidget(self.page_login)

        # Page 1: 注册
        self.page_register = QWidget()
        self.init_register_page()
        self.stack.addWidget(self.page_register)

        # Page 2: 找回密码
        self.page_forgot = QWidget()
        self.init_forgot_page()
        self.stack.addWidget(self.page_forgot)

        self.card_layout.addWidget(self.stack)
        main_layout.addWidget(self.card)

    # --- 页面初始化 ---

    def init_login_page(self):
        layout = QVBoxLayout(self.page_login)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input_login_user = QLineEdit()
        self.input_login_user.setPlaceholderText(STRINGS["placeholder_user"])
        self.input_login_user.setFixedHeight(45)

        self.input_login_pwd = QLineEdit()
        self.input_login_pwd.setPlaceholderText(STRINGS["placeholder_pwd"])
        self.input_login_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_login_pwd.setFixedHeight(45)

        btn_login = QPushButton(STRINGS["login_btn"])
        btn_login.setFixedHeight(50)
        btn_login.setObjectName("BtnPrimary")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self.on_login_clicked)

        # 底部链接
        links_layout = QHBoxLayout()
        btn_to_reg = QPushButton(STRINGS["create_account_link"])
        btn_to_reg.setObjectName("BtnLink")
        btn_to_reg.clicked.connect(lambda: self.switch_page(1))

        btn_to_forgot = QPushButton(STRINGS["forgot_password_link"])
        btn_to_forgot.setObjectName("BtnLink")
        btn_to_forgot.clicked.connect(lambda: self.switch_page(2))

        links_layout.addWidget(btn_to_reg)
        links_layout.addStretch()
        links_layout.addWidget(btn_to_forgot)

        layout.addWidget(self.input_login_user)
        layout.addWidget(self.input_login_pwd)
        layout.addSpacing(10)
        layout.addWidget(btn_login)
        layout.addSpacing(5)
        layout.addLayout(links_layout)
        layout.addStretch()

    def init_register_page(self):
        layout = QVBoxLayout(self.page_register)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(STRINGS["register_header"])
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("PageHeader")
        layout.addWidget(lbl)

        self.input_reg_user = QLineEdit()
        self.input_reg_user.setPlaceholderText(STRINGS["placeholder_user_req"])
        self.input_reg_user.setFixedHeight(45)

        self.input_reg_pwd = QLineEdit()
        self.input_reg_pwd.setPlaceholderText(STRINGS["placeholder_pwd_req"])
        self.input_reg_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_reg_pwd.setFixedHeight(45)

        self.input_reg_email = QLineEdit()
        self.input_reg_email.setPlaceholderText(STRINGS["placeholder_email"])
        self.input_reg_email.setFixedHeight(45)

        btn_reg = QPushButton(STRINGS["register_btn"])
        btn_reg.setFixedHeight(50)
        btn_reg.setObjectName("BtnPrimary")
        btn_reg.clicked.connect(self.on_register_clicked)

        btn_back = QPushButton(STRINGS["back_login_link"])
        btn_back.setObjectName("BtnLink")
        btn_back.clicked.connect(lambda: self.switch_page(0))

        layout.addWidget(self.input_reg_user)
        layout.addWidget(self.input_reg_pwd)
        layout.addWidget(self.input_reg_email)
        layout.addSpacing(10)
        layout.addWidget(btn_reg)
        layout.addWidget(btn_back)
        layout.addStretch()

    def init_forgot_page(self):
        layout = QVBoxLayout(self.page_forgot)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(STRINGS["reset_header"])
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("PageHeader")
        layout.addWidget(lbl)

        self.input_reset_user = QLineEdit()
        self.input_reset_user.setPlaceholderText(STRINGS["placeholder_user"])
        self.input_reset_user.setFixedHeight(40)

        # 发送验证码区
        code_layout = QHBoxLayout()
        self.input_reset_code = QLineEdit()
        self.input_reset_code.setPlaceholderText(STRINGS["placeholder_code"])
        self.input_reset_code.setFixedHeight(40)

        self.btn_send_code = QPushButton(STRINGS["send_code_btn"])
        self.btn_send_code.setFixedHeight(40)
        self.btn_send_code.setFixedWidth(100)
        self.btn_send_code.setObjectName("BtnSecondary")
        self.btn_send_code.clicked.connect(self.on_send_code_clicked)

        code_layout.addWidget(self.input_reset_code)
        code_layout.addWidget(self.btn_send_code)

        self.input_new_pwd = QLineEdit()
        self.input_new_pwd.setPlaceholderText(STRINGS["placeholder_new_pwd"])
        self.input_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_new_pwd.setFixedHeight(40)

        btn_reset = QPushButton(STRINGS["reset_btn"])
        btn_reset.setFixedHeight(45)
        btn_reset.setObjectName("BtnPrimary")
        btn_reset.clicked.connect(self.on_reset_clicked)

        btn_back = QPushButton(STRINGS["back_login_link"])
        btn_back.setObjectName("BtnLink")
        btn_back.clicked.connect(lambda: self.switch_page(0))

        layout.addWidget(self.input_reset_user)
        layout.addLayout(code_layout)
        layout.addWidget(self.input_new_pwd)
        layout.addSpacing(10)
        layout.addWidget(btn_reset)
        layout.addWidget(btn_back)
        layout.addStretch()

    # --- 逻辑处理 ---

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def on_login_clicked(self):
        u = self.input_login_user.text().strip()
        p = self.input_login_pwd.text().strip()
        if u and p:
            self.login_signal.emit(u, p)
        else:
            self.show_error(STRINGS["warn_enter_all"])

    def on_register_clicked(self):
        u = self.input_reg_user.text().strip()
        p = self.input_reg_pwd.text().strip()
        e = self.input_reg_email.text().strip()
        if u and p:
            self.register_signal.emit(u, p, e)
        else:
            self.show_error(STRINGS["warn_user_pwd_req"])

    def on_send_code_clicked(self):
        u = self.input_reset_user.text().strip()
        if not u:
            self.show_error(STRINGS["warn_enter_user_first"])
            return
        self.send_code_signal.emit(u)
        self.btn_send_code.setEnabled(False)
        self.btn_send_code.setText(STRINGS["send_code_btn_sent"])

    def reset_send_btn(self):
        self.btn_send_code.setEnabled(True)
        self.btn_send_code.setText(STRINGS["send_code_btn"])

    def on_reset_clicked(self):
        u = self.input_reset_user.text().strip()
        c = self.input_reset_code.text().strip()
        np = self.input_new_pwd.text().strip()
        if u and c and np:
            self.reset_pwd_signal.emit(u, c, np)
        else:
            self.show_error(STRINGS["warn_fields_req"])

    def show_error(self, msg):
        QMessageBox.warning(self, STRINGS["warn_title"], msg)

    # --- 主题与样式 ---

    def toggle_theme(self):
        self.is_night = not self.is_night
        self.current_theme = ThemeManager.get_theme(self.is_night)
        self.btn_theme.setText("☀" if self.is_night else "🌙")
        self.theme_changed.emit(self.is_night)
        self.apply_theme()

    def apply_theme(self):
        t = self.current_theme
        self.shadow_effect.setColor(Qt.GlobalColor.black if t["name"] == "dark" else Qt.GlobalColor.gray)

        close_btn_color = "#E4E4E7" if t["name"] == "dark" else "#000000"

        style = f"""
            LoginWindow {{ background: transparent; }}
            QFrame#LoginCard {{ background-color: {t['card_bg']}; border-radius: 20px; }}

            QLabel {{ color: {t['text_main']}; }}
            QLabel#Logo {{ font-family: 'Segoe UI'; font-size: 28px; font-weight: 800; color: {t['text_main']}; }}
            QLabel#Slogan {{ font-family: 'Segoe UI'; font-size: 14px; color: {t['accent']}; letter-spacing: 2px; }}
            QLabel#PageHeader {{ font-size: 18px; font-weight: bold; color: {t['text_sub']}; margin-bottom: 10px; }}

            QLineEdit {{ 
                background-color: {t['input_bg']}; 
                border: 1px solid {t['input_bg']}; 
                border-radius: 12px; 
                padding: 0 15px; 
                color: {t['text_main']}; 
            }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; background-color: {t['card_bg']}; }}

            QPushButton {{ border: none; font-size: 14px; background: transparent; }}

            QPushButton[text="×"] {{ color: {close_btn_color}; font-size: 20px; }}

            QPushButton#BtnPrimary {{ 
                background-color: {t['accent']}; color: #FFFFFF; font-weight: bold; border-radius: 25px; 
            }}
            QPushButton#BtnPrimary:hover {{ background-color: {t['accent_hover']}; }}

            QPushButton#BtnSecondary {{ 
                background-color: {t['input_bg']}; color: {t['text_main']}; border-radius: 10px; border: 1px solid {t['border']};
            }}
            QPushButton#BtnSecondary:hover {{ background-color: {t['border']}; }}

            QPushButton#BtnLink {{ color: {t['text_sub']}; }}
            QPushButton#BtnLink:hover {{ color: {t['accent']}; text-decoration: underline; }}

            QMessageBox {{ background-color: {t['card_bg']}; }}
            QMessageBox QLabel {{ color: {t['text_main']}; }}
            QMessageBox QPushButton {{ 
                background-color: {t['input_bg']}; 
                color: {t['text_main']}; 
                border: 1px solid {t['border']};
                padding: 5px 15px;
                border-radius: 5px;
            }}
        """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()