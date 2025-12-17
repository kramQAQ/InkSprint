from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QListWidget, QLabel, QPushButton, QHBoxLayout,
                             QGraphicsDropShadowEffect, QListWidgetItem, QFrame, QLineEdit, QStackedWidget)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon
from .localization import STRINGS  # 导入汉化配置


class FloatGroupWindow(QWidget):
    # 新增信号：发送消息
    msg_sent = pyqtSignal(str)

    def __init__(self, parent_controller):
        super().__init__()
        self.controller = parent_controller
        self.current_mode = "chat"  # chat or rank

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 450)

        self.drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        # 背景透明度 80% 的黑
        self.container.setStyleSheet("""
            QFrame { background-color: rgba(0, 0, 0, 204); border-radius: 10px; border: 1px solid #555; }
            QLabel { color: white; font-weight: bold; font-family: 'Segoe UI'; border: none; background: transparent; }
            QTextEdit { background: transparent; border: none; color: white; font-size: 13px; font-family: 'Segoe UI'; }
            QListWidget { background: transparent; border: none; color: white; font-weight: bold; font-family: 'Segoe UI'; }
            QLineEdit { background: rgba(255, 255, 255, 0.15); color: white; border-radius: 5px; padding: 5px; selection-background-color: #555; }
            QPushButton { background: transparent; color: #ccc; border: none; font-size: 14px; }
            QPushButton:hover { color: white; }
        """)

        con_layout = QVBoxLayout(self.container)
        con_layout.setContentsMargins(10, 10, 10, 10)

        # Header with Switch Button
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel(STRINGS["float_group_chat"])
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 【新功能】切换按钮
        self.btn_switch = QPushButton("⇄ 切换")
        self.btn_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_switch.clicked.connect(self.toggle_view)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedWidth(20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)

        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_switch)
        header_layout.addWidget(self.btn_close)

        con_layout.addLayout(header_layout)

        # Stacked widgets for easy switching
        self.stack = QStackedWidget()

        # Page 1: Chat
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.stack.addWidget(self.chat_view)

        # Page 2: Rank
        self.rank_view = QListWidget()
        self.stack.addWidget(self.rank_view)

        con_layout.addWidget(self.stack)

        # Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(STRINGS["chat_placeholder"])
        self.input_field.returnPressed.connect(self.on_send_msg)
        con_layout.addWidget(self.input_field)

        self.layout.addWidget(self.container)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

    def toggle_view(self):
        if self.current_mode == "chat":
            self.show_rank()
        else:
            self.show_chat()

    def show_chat(self):
        self.current_mode = "chat"
        self.lbl_title.setText(STRINGS["float_group_chat"])
        self.stack.setCurrentWidget(self.chat_view)
        self.input_field.show()
        self.show()

    def show_rank(self):
        self.current_mode = "rank"
        self.lbl_title.setText(STRINGS["float_leaderboard"])
        self.stack.setCurrentWidget(self.rank_view)
        self.input_field.hide()
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
            c = QColor("white")
            if color_name == "green":
                c = QColor("#40C463")
            elif color_name == "orange":
                c = QColor("#FFD700")

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