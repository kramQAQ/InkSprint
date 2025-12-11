from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QListWidget, QLabel,
                             QGraphicsDropShadowEffect, QListWidgetItem, QFrame)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QBrush, QFont


class FloatGroupWindow(QWidget):
    def __init__(self, parent_controller):
        super().__init__()
        self.controller = parent_controller

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 400)

        self.drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame { background-color: rgba(40, 40, 45, 0.95); border-radius: 10px; border: 1px solid #555; }
            QLabel { color: white; font-weight: bold; }
            QTextEdit { background: transparent; border: none; color: white; font-size: 13px; }
            QListWidget { background: transparent; border: none; color: white; font-weight: bold; }
        """)

        con_layout = QVBoxLayout(self.container)
        con_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        self.lbl_title = QLabel("Group Chat")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        con_layout.addWidget(self.lbl_title)

        # Stacked widgets manually
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.rank_view = QListWidget()

        con_layout.addWidget(self.chat_view)
        con_layout.addWidget(self.rank_view)

        self.layout.addWidget(self.container)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)

    def show_chat(self):
        self.lbl_title.setText("💬 Group Chat")
        self.chat_view.show()
        self.rank_view.hide()
        self.show()

    def show_rank(self):
        self.lbl_title.setText("🏆 Leaderboard")
        self.chat_view.hide()
        self.rank_view.show()
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
                c = QColor("#00ff00")
            elif color_name == "orange":
                c = QColor("#ffa500")

            item.setForeground(QBrush(c))
            self.rank_view.addItem(item)

    # Move logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseDoubleClickEvent(self, event):
        self.close()