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
from ui.localization import STRINGS  # 导入汉化接口


class InkApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # 【重要修改】设置为 True，这样关闭窗口时会自动退出应用
        # 之前的 False 是导致进程在 PyCharm 中无法结束的直接原因
        self.app.setQuitOnLastWindowClosed(True)

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

        # 确保退出时清理资源
        self.app.aboutToQuit.connect(self.quit_app)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)
        tray_menu = QMenu()

        # 使用 STRINGS 字典中的键
        action_show = QAction(STRINGS["tray_show"], self.app)
        action_show.triggered.connect(self.restore_from_float)

        action_float = QAction(STRINGS["tray_float"], self.app)
        action_float.triggered.connect(self.switch_to_float)

        action_quit = QAction(STRINGS["tray_quit"], self.app)
        action_quit.triggered.connect(self.app.quit)  # 直接调用 app.quit

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
            QMessageBox.critical(None, STRINGS["msg_conn_fail_title"], STRINGS["msg_conn_fail_text"])
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
                # 【修复 1.1】确保 current_group 被保存
                self.current_user_info = {
                    "nickname": data.get("nickname"),
                    "username": data.get("username"),
                    "email": data.get("email"),
                    "avatar_data": data.get("avatar_data"),
                    "today_total": data.get("today_total", 0),  # 传递今日数据
                    "current_group": data.get("current_group", {}),  # 确保房间信息被传递
                    "user_id": data.get("user_id", 0)  # 确保 user_id 被传递
                }
                self.login_window.hide()
                self.init_main_window()
            else:
                QMessageBox.warning(self.login_window, STRINGS["title_login_fail"], msg)

        elif msg_type == "register_response":
            if status == "success":
                QMessageBox.information(self.login_window, STRINGS["title_reg_success"], msg)
                self.login_window.switch_page(0)
            else:
                QMessageBox.warning(self.login_window, STRINGS["title_reg_fail"], msg)

        elif msg_type == "code_response":
            if status == "success":
                QMessageBox.information(self.login_window, STRINGS["title_sent"], msg)
            else:
                self.login_window.reset_send_btn()
                QMessageBox.warning(self.login_window, STRINGS["error_title"], msg)

        elif msg_type == "reset_response":
            if status == "success":
                QMessageBox.information(self.login_window, STRINGS["success_title"], msg)
                self.login_window.switch_page(0)
            else:
                QMessageBox.warning(self.login_window, STRINGS["title_reset_fail"], msg)

        # 将其他消息转发给主窗口（以便 SocialPage 接收）
        elif self.main_window:
            self.main_window.dispatch_network_message(data)

    def init_main_window(self):
        if not self.main_window:
            self.is_night_mode = self.login_window.is_night
            self.main_window = MainWindow(is_night=self.is_night_mode, network_manager=self.network)

            # 【修复 1.2】传递 current_group 信息，以便 MainWindow 中的 SocialPage 进行恢复
            user_data = self.current_user_info.copy()

            # MainWindow 期望接收 user_id, nickname 等
            self.main_window.set_user_info(user_data)

        self.main_window.show()

    def switch_to_float(self):
        if self.main_window:
            self.main_window.switch_to_float()

    def restore_from_float(self):
        if self.main_window:
            self.main_window.restore_from_float()

    def quit_app(self):
        print("[App] Quitting clean up...")
        if self.main_window:
            if hasattr(self.main_window, 'monitor_thread'):
                print("[App] Stopping monitor thread...")
                self.main_window.monitor_thread.stop()
                self.main_window.monitor_thread.wait()  # 必须等待线程完全结束
        if self.network:
            self.network.close()


if __name__ == '__main__':
    ink_app = InkApplication()
    ink_app.start()