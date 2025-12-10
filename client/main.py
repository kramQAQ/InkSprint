import sys
import os
import json
import hashlib

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from ui.login import LoginWindow
from ui.main_window import MainWindow
from ui.float_window import FloatWindow
from ui.theme import DEFAULT_ACCENT
from core.network import NetworkManager


class InkApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.network = NetworkManager(port=23456)
        self.network.message_received.connect(self.on_server_message)

        # 初始化窗口
        self.login_window = LoginWindow()
        self.main_window = None
        self.float_window = FloatWindow(DEFAULT_ACCENT)

        # 信号连接
        self.login_window.login_signal.connect(self.handle_login_request)
        self.float_window.restore_signal.connect(self.restore_from_float)

        self.is_night_mode = False
        self.current_user_info = {}  # 存储登录用户信息

        self.setup_tray()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)
        tray_menu = QMenu()

        action_show = QAction("Show Dashboard", self.app)
        action_show.triggered.connect(self.restore_from_float)

        action_float = QAction("Float Mode", self.app)
        action_float.triggered.connect(self.switch_to_float)

        action_quit = QAction("Quit", self.app)
        action_quit.triggered.connect(self.quit_app)

        tray_menu.addAction(action_show)
        tray_menu.addAction(action_float)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def start(self):
        print("-" * 30)
        print("🚀 客户端正在启动...")
        if not self.network.connect_and_handshake():
            error_msg = (
                "❌ 无法连接到服务器 \n"
                "请先运行 server/main.py"
            )
            print(error_msg)
            QMessageBox.critical(None, "连接失败", error_msg)
            return

        print("✅ 服务器连接成功")
        self.network.start()
        self.login_window.show()
        sys.exit(self.app.exec())

    def handle_login_request(self, username, password):
        print(f"[GUI] 发送登录请求: {username}")
        # SHA256 哈希
        pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        login_req = {
            "type": "login",
            "username": username,
            "password": pwd_hash
        }
        self.network.send_request(login_req)

    def on_server_message(self, data):
        msg_type = data.get("type")

        if msg_type == "login_response":
            status = data.get("status")
            if status == "success":
                # 保存用户信息
                self.current_user_info = {
                    "nickname": data.get("nickname"),
                    "username": data.get("username"),
                    "avatar_data": data.get("avatar_data")
                }
                self.login_window.hide()
                self.init_main_window()
            else:
                QMessageBox.warning(self.login_window, "Login Failed", data.get("msg", "Unknown error"))

        elif msg_type == "profile_updated":
            # 资料更新成功，不做强弹窗干扰，MainWin已乐观更新
            print("[App] Profile updated successfully")

    def init_main_window(self):
        if not self.main_window:
            self.is_night_mode = self.login_window.is_night

            # 传入 network_manager 以便主窗口能发送请求
            self.main_window = MainWindow(is_night=self.is_night_mode, network_manager=self.network)

            # 设置用户信息
            self.main_window.set_user_info(self.current_user_info)

            # 销毁临时悬浮窗
            if self.float_window:
                self.float_window.close()
                self.float_window = None

        self.main_window.show()

    def switch_to_float(self):
        if self.main_window:
            self.main_window.switch_to_float()

    def restore_from_float(self):
        if self.main_window:
            self.main_window.restore_from_float()

    def quit_app(self):
        if self.main_window:
            self.main_window.monitor_thread.stop()
        self.app.quit()


if __name__ == '__main__':
    ink_app = InkApplication()
    ink_app.start()