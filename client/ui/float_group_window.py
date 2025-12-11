from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QListWidget, QLabel,
                             QGraphicsDropShadowEffect, QListWidgetItem, QFrame, QLineEdit)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont


class FloatGroupWindow(QWidget):
    # 新增信号：发送消息
    msg_sent = pyqtSignal(str)

    def __init__(self, parent_controller):
        super().__init__()
        self.controller = parent_controller

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 450)  # 稍微加高一点给输入框留位置

        self.drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)  # 给阴影留空间

        self.container = QFrame()
        # 背景透明度 80% 的黑 -> rgba(0, 0, 0, 204)
        self.container.setStyleSheet("""
            QFrame { background-color: rgba(0, 0, 0, 204); border-radius: 10px; border: 1px solid #555; }
            QLabel { color: white; font-weight: bold; font-family: 'Segoe UI'; }
            QTextEdit { background: transparent; border: none; color: white; font-size: 13px; font-family: 'Segoe UI'; }
            QListWidget { background: transparent; border: none; color: white; font-weight: bold; font-family: 'Segoe UI'; }
            QLineEdit { background: rgba(255, 255, 255, 0.15); color: white; border-radius: 5px; padding: 5px; selection-background-color: #555; }
        """)

        con_layout = QVBoxLayout(self.container)
        con_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        self.lbl_title = QLabel("Group Chat")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 14px; margin-bottom: 5px;")
        con_layout.addWidget(self.lbl_title)

        # Stacked widgets manually
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)

        self.rank_view = QListWidget()

        con_layout.addWidget(self.chat_view)
        con_layout.addWidget(self.rank_view)

        # Input Field (始终显示在底部，或者仅在聊天模式显示)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type message...")
        self.input_field.returnPressed.connect(self.on_send_msg)
        con_layout.addWidget(self.input_field)

        self.layout.addWidget(self.container)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

    def show_chat(self):
        self.lbl_title.setText("💬 Group Chat")
        self.chat_view.show()
        self.rank_view.hide()
        self.input_field.show()  # 聊天模式显示输入框
        self.show()

    def show_rank(self):
        self.lbl_title.setText("🏆 Leaderboard")
        self.chat_view.hide()
        self.rank_view.show()
        self.input_field.hide()  # 排行榜模式隐藏输入框，保持界面整洁
        self.show()

    def update_chat(self, html):
        self.chat_view.setHtml(html)
        self.chat_view.moveCursor(self.chat_view.textCursor().MoveOperation.End)

    def append_chat(self, html_line):
        self.chat_view.append(html_line)

    def update_rank(self, items):
        # items = [(text, color_name), ...]
        self.rank_view.clear()
        for text, color_name in items:
            item = QListWidgetItem(text)
            # Adjust colors for dark theme float window
            c = QColor("white")
            if color_name == "green":
                c = QColor("#40C463")  # Green
            elif color_name == "orange":
                c = QColor("#FFD700")  # Gold

            item.setForeground(QBrush(c))
            self.rank_view.addItem(item)

    def on_send_msg(self):
        text = self.input_field.text().strip()
        if text:
            self.msg_sent.emit(text)
            self.input_field.clear()

    # Move logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        self.close()