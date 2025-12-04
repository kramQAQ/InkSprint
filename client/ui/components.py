from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QFont


class RoundedFrame(QFrame):
    """通用圆角卡片基类"""

    def __init__(self, theme, radius=20):
        super().__init__()
        self.radius = radius
        self.theme = theme
        self.apply_shadow()
        self.update_theme(theme)

    def apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5)
        # 初始颜色
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)

    def update_theme(self, theme):
        self.theme = theme
        if self.graphicsEffect():
            self.graphicsEffect().setColor(QColor(theme['shadow']))

        self.setStyleSheet(f"""
            RoundedFrame {{
                background-color: {theme['card_bg']};
                border-radius: {self.radius}px;
                border: 1px solid {theme['border']};
            }}
            QLabel {{ background-color: transparent; border: none; }}
        """)


class AvatarWidget(QLabel):
    """自动裁剪圆形的头像组件"""

    def __init__(self, size=60, text="G", theme=None):
        super().__init__()
        self.setFixedSize(size, size)
        self.text_avatar = text
        self.pixmap_avatar = None
        self.theme = theme
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_image(self, image_path):
        if image_path:
            self.pixmap_avatar = QPixmap(image_path)
            self.update()

    def set_text(self, text):
        self.text_avatar = text[0].upper() if text else "G"
        self.pixmap_avatar = None
        self.update()

    def update_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 核心：绘制圆形裁剪路径
        path = QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        painter.setClipPath(path)

        if self.pixmap_avatar:
            # 绘制图片 (保持比例填充)
            painter.drawPixmap(self.rect(), self.pixmap_avatar.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation))
        else:
            # 绘制默认的彩色背景和文字
            bg = QColor(self.theme['accent']) if self.theme else QColor("#cccccc")
            painter.fillRect(self.rect(), bg)
            painter.setPen(Qt.GlobalColor.white)
            font = self.font()
            font.setPixelSize(int(self.height() * 0.5))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text_avatar)


class StatCard(RoundedFrame):
    """数据展示卡片 (Session Words / Speed)"""

    def __init__(self, title, sub_text, theme, is_primary=False):
        self.is_primary = is_primary
        super().__init__(theme)
        self.init_ui(title, sub_text)

    def init_ui(self, title, sub_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 600; opacity: 0.8;")

        self.lbl_value = QLabel("0")
        self.lbl_value.setStyleSheet("font-size: 56px; font-weight: bold;")

        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setStyleSheet("font-size: 13px; opacity: 0.7;")

        layout.addWidget(self.lbl_title)
        layout.addStretch()
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_sub)

    def update_value(self, value):
        self.lbl_value.setText(str(value))

    def update_theme(self, theme):
        super().update_theme(theme)

        if self.is_primary:
            # 绿色主卡片样式
            bg = theme['accent']
            text_c = "#FFFFFF"
            self.setStyleSheet(f"""
                RoundedFrame {{
                    background-color: {bg};
                    border-radius: 20px;
                    border: none;
                }}
                QLabel {{ color: {text_c}; background: transparent; }}
            """)
        else:
            # 白色/深色副卡片样式
            self.setStyleSheet(f"""
                RoundedFrame {{
                    background-color: {theme['card_bg']};
                    border-radius: 20px;
                    border: 1px solid {theme['border']};
                }}
                QLabel {{ color: {theme['text_main']}; background: transparent; }}
            """)


class PomodoroCard(RoundedFrame):
    """番茄钟卡片"""
    mode_switched = pyqtSignal(str)
    toggle_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    float_toggled = pyqtSignal(bool)

    def __init__(self, theme):
        super().__init__(theme)
        self.init_ui()
        self.update_theme(theme)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 顶部布局
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel("Focus Timer")

        # 右上角按钮组
        btn_box = QHBoxLayout()
        btn_box.setSpacing(5)

        def create_tool_btn(text):
            b = QPushButton(text)
            b.setFixedSize(30, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            return b

        self.btn_minus = create_tool_btn("-")  # 切换倒计时
        self.btn_plus = create_tool_btn("+")  # 切换正计时
        self.btn_float = create_tool_btn("🚀")  # 悬浮窗开关
        self.btn_float.setCheckable(True)

        btn_box.addWidget(self.btn_minus)
        btn_box.addWidget(self.btn_plus)
        btn_box.addWidget(self.btn_float)

        top_layout.addWidget(self.lbl_title)
        top_layout.addStretch()
        top_layout.addLayout(btn_box)
        layout.addLayout(top_layout)

        layout.addStretch()

        # 时间显示
        self.lbl_time = QLabel("25:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)

        layout.addStretch()

        # 底部控制按钮
        ctrl_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶")
        self.btn_reset = QPushButton("↺")

        for btn in [self.btn_start, self.btn_reset]:
            btn.setFixedSize(50, 50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addSpacing(15)
        ctrl_layout.addWidget(self.btn_reset)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # 信号连接
        self.btn_minus.clicked.connect(lambda: self.mode_switched.emit("timer"))
        self.btn_plus.clicked.connect(lambda: self.mode_switched.emit("stopwatch"))
        self.btn_start.clicked.connect(self.toggle_clicked)
        self.btn_reset.clicked.connect(self.reset_clicked)
        self.btn_float.toggled.connect(self.float_toggled)

    def update_time_display(self, text):
        self.lbl_time.setText(text)

    def set_running_state(self, is_running):
        self.btn_start.setText("⏸" if is_running else "▶")

    def update_theme(self, theme):
        super().update_theme(theme)

        btn_bg = theme['input_bg']
        text_main = theme['text_main']
        accent = theme['accent']

        self.setStyleSheet(f"""
            RoundedFrame {{
                background-color: {theme['card_bg']};
                border-radius: 20px;
                border: 1px solid {theme['border']};
            }}
            QLabel {{ color: {text_main}; background: transparent; font-weight: bold; }}

            /* 时间特大号绿色字体 */
            QLabel[text="25:00"], QLabel[text="00:00"] {{ 
                font-size: 48px; color: {accent}; 
            }}

            QPushButton {{
                border-radius: 8px;
                background-color: {btn_bg};
                color: {text_main};
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {theme['border']}; }}
            QPushButton:checked {{ background-color: {accent}; color: white; }}

            /* 开始按钮 (绿色实心) */
            QPushButton[text="▶"], QPushButton[text="⏸"] {{
                background-color: {accent};
                color: white;
                border-radius: 25px;
                font-size: 20px;
            }}

            /* 重置按钮 (空心圆) */
            QPushButton[text="↺"] {{
                background-color: transparent;
                border: 2px solid {theme['border']};
                border-radius: 25px;
                color: {theme['text_sub']};
                font-size: 20px;
            }}
        """)
        # 强制更新时间 Label 样式
        self.lbl_time.setStyleSheet(f"font-size: 48px; color: {accent}; font-weight: bold;")