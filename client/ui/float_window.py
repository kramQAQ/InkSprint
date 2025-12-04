from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class BaseFloatWindow(QWidget):
    """悬浮窗基类"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def set_theme_style(self, is_night):
        """统一的黑白透明+绿字风格"""
        if is_night:
            bg_color = "rgba(0, 0, 0, 0.85)"
            border_color = "rgba(255, 255, 255, 0.1)"
        else:
            bg_color = "rgba(255, 255, 255, 0.9)"
            border_color = "rgba(0, 0, 0, 0.1)"

        # 统一绿色 #82C99B (与新主题一致)
        text_color = "#82C99B"

        self.setStyleSheet(f"""
            #FloatContainer {{
                background-color: {bg_color};
                border-radius: 15px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_color};
                font-family: 'Segoe UI';
                font-weight: bold;
                background-color: transparent;
            }}
            #FloatValue {{ font-size: 20px; }}
            #FloatLabel {{ font-size: 12px; opacity: 0.9; }}
        """)


class FloatWindow(BaseFloatWindow):
    restore_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 80)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.container = QLabel(self)
        self.container.setObjectName("FloatContainer")

        inner = QVBoxLayout(self.container)
        inner.setSpacing(0)
        inner.setContentsMargins(10, 5, 10, 5)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_speed = QLabel("0 WPH")
        self.lbl_speed.setObjectName("FloatValue")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_count = QLabel("+0 words")
        self.lbl_count.setObjectName("FloatLabel")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)

        inner.addWidget(self.lbl_speed)
        inner.addWidget(self.lbl_count)
        layout.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

    def update_data(self, total, increment, wph):
        self.lbl_speed.setText(f"{wph} WPH")
        self.lbl_count.setText(f"+{increment} words")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.restore_signal.emit()


class PomodoroFloatWindow(BaseFloatWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(90, 90)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.container = QLabel(self)
        self.container.setObjectName("FloatContainer")

        inner = QVBoxLayout(self.container)
        inner.setSpacing(0)
        inner.setContentsMargins(5, 5, 5, 5)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel("🍅")
        self.lbl_icon.setStyleSheet("font-size: 20px;")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_time = QLabel("25:00")
        self.lbl_time.setObjectName("FloatValue")
        self.lbl_time.setStyleSheet("font-size: 18px;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        inner.addWidget(self.lbl_icon)
        inner.addWidget(self.lbl_time)
        layout.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

    def update_time(self, time_str):
        self.lbl_time.setText(time_str)