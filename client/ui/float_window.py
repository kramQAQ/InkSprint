from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class FloatWindow(QWidget):
    """
    统一悬浮窗：
    - 基础模式：[ WPH | +Count ]
    - 专注模式：[ WPH | +Count ] | [ Timer ]
    """
    restore_signal = pyqtSignal()

    def __init__(self, accent_color):
        super().__init__()
        self.accent_color = accent_color
        self.has_pomodoro = False  # 当前是否显示番茄钟部分

        # 窗口属性：无边框、置顶、工具窗口、透明背景(用于画圆角)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.drag_pos = None
        self.setup_ui()
        self.update_style()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 主容器 (背景色载体)
        self.container = QFrame()
        self.container.setObjectName("FloatContainer")

        # 容器内部布局
        self.content_layout = QHBoxLayout(self.container)
        self.content_layout.setContentsMargins(15, 10, 15, 10)
        self.content_layout.setSpacing(15)

        # --- 左侧：数据区 ---
        data_layout = QVBoxLayout()
        data_layout.setSpacing(2)

        self.lbl_wph = QLabel("0 WPH")
        self.lbl_wph.setObjectName("FloatMainText")
        self.lbl_wph.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_count = QLabel("+0 words")
        self.lbl_count.setObjectName("FloatSubText")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignLeft)

        data_layout.addWidget(self.lbl_wph)
        data_layout.addWidget(self.lbl_count)

        self.content_layout.addLayout(data_layout)

        # --- 分割线 (仅在开启番茄钟时显示) ---
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.VLine)
        self.divider.setObjectName("FloatDivider")
        self.divider.setFixedWidth(1)
        self.divider.hide()  # 默认隐藏

        self.content_layout.addWidget(self.divider)

        # --- 右侧：番茄钟区 (默认隐藏) ---
        self.timer_widget = QWidget()
        self.timer_widget.hide()
        timer_layout = QVBoxLayout(self.timer_widget)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setSpacing(0)
        timer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setObjectName("FloatTimerText")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        timer_layout.addWidget(self.lbl_timer)

        self.content_layout.addWidget(self.timer_widget)

        self.main_layout.addWidget(self.container)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)

    def set_theme_color(self, color_hex):
        self.accent_color = color_hex
        self.update_style()

    def update_style(self):
        # 纯色背景风格
        self.setStyleSheet(f"""
            #FloatContainer {{
                background-color: {self.accent_color};
                border-radius: 12px;
            }}
            QLabel {{ color: white; font-family: 'Segoe UI'; }}
            #FloatMainText {{ font-size: 16px; font-weight: bold; }}
            #FloatSubText {{ font-size: 11px; opacity: 0.8; }}
            #FloatTimerText {{ font-size: 22px; font-weight: bold; }}
            #FloatDivider {{ background-color: rgba(255, 255, 255, 0.3); border: none; }}
        """)

    def set_mode(self, show_pomodoro):
        """切换是否显示番茄钟"""
        self.has_pomodoro = show_pomodoro
        if show_pomodoro:
            self.divider.show()
            self.timer_widget.show()
        else:
            self.divider.hide()
            self.timer_widget.hide()

        # 调整大小策略以适应内容
        self.adjustSize()

    def update_data(self, total, increment, wph):
        self.lbl_wph.setText(f"{wph} WPH")
        self.lbl_count.setText(f"+{increment} words")

    def update_timer(self, time_str):
        self.lbl_timer.setText(time_str)

    # --- 拖动逻辑 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.restore_signal.emit()