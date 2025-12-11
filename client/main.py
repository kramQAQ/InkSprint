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
        self.login_window.register_signal.connect(self.handle_register_request)
        self.login_window.send_code_signal.connect(self.handle_send_code_request)
        self.login_window.reset_pwd_signal.connect(self.handle_reset_pwd_request)

        self.float_window.restore_signal.connect(self.restore_from_float)

        self.is_night_mode = False
        self.current_user_info = {}

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

    # --- 请求处理 ---

    def _hash_pwd(self, pwd):
        return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

    def handle_login_request(self, username, password):
        print(f"[GUI] 发送登录请求: {username}")
        self.network.send_request({
            "type": "login",
            "username": username,
            "password": self._hash_pwd(password)
        })

    def handle_register_request(self, username, password, email):
        print(f"[GUI] 发送注册请求: {username}")
        self.network.send_request({
            "type": "register",
            "username": username,
            "password": self._hash_pwd(password),
            "email": email
        })

    def handle_send_code_request(self, username):
        print(f"[GUI] 请求发送验证码: {username}")
        self.network.send_request({
            "type": "send_code",
            "username": username
        })

    def handle_reset_pwd_request(self, username, code, new_password):
        print(f"[GUI] 请求重置密码: {username}")
        self.network.send_request({
            "type": "reset_password",
            "username": username,
            "code": code,
            "new_password": self._hash_pwd(new_password)
        })

    # --- 响应处理 ---

    def on_server_message(self, data):
        msg_type = data.get("type")
        msg = data.get("msg", "")
        status = data.get("status")

        if msg_type == "login_response":
            if status == "success":
                self.current_user_info = {
                    "nickname": data.get("nickname"),
                    "username": data.get("username"),
                    "email": data.get("email"),
                    "avatar_data": data.get("avatar_data")
                }
                self.login_window.hide()
                self.init_main_window()
            else:
                QMessageBox.warning(self.login_window, "Login Failed", msg)

        elif msg_type == "register_response":
            if status == "success":
                QMessageBox.information(self.login_window, "Success", msg)
                self.login_window.switch_page(0)  # 注册成功跳回登录页
            else:
                QMessageBox.warning(self.login_window, "Register Failed", msg)

        elif msg_type == "code_response":
            if status == "success":
                QMessageBox.information(self.login_window, "Sent", msg)
            else:
                self.login_window.reset_send_btn()
                QMessageBox.warning(self.login_window, "Error", msg)

        elif msg_type == "reset_response":
            if status == "success":
                QMessageBox.information(self.login_window, "Success", msg)
                self.login_window.switch_page(0)
            else:
                QMessageBox.warning(self.login_window, "Reset Failed", msg)

        elif msg_type == "profile_updated":
            print("[App] Profile updated successfully")

    def init_main_window(self):
        if not self.main_window:
            self.is_night_mode = self.login_window.is_night
            self.main_window = MainWindow(is_night=self.is_night_mode, network_manager=self.network)
            self.main_window.set_user_info(self.current_user_info)

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