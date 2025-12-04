import sys
import os
import json
import hashlib

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
from ui.login import LoginWindow
from ui.main_window import MainWindow
from ui.float_window import FloatWindow, PomodoroFloatWindow
from core.network import NetworkManager


class InkApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.network = NetworkManager(port=23456)
        self.network.message_received.connect(self.on_server_message)

        self.login_window = LoginWindow()
        self.main_window = None
        self.float_window = FloatWindow()
        self.pomo_float = PomodoroFloatWindow()

        self.login_window.login_signal.connect(self.handle_login_request)
        self.login_window.theme_changed.connect(self.on_theme_changed)

        self.float_window.restore_signal.connect(self.restore_from_float)

        self.is_night_mode = False

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
                "❌ 无法连接到服务器 (127.0.0.1:23456)\n\n"
                "常见原因：\n"
                "1. server/main.py 未运行。\n"
                "2. 端口被旧的 Python 进程占用 (僵尸进程)。"
            )
            print(error_msg)
            QMessageBox.critical(None, "连接失败", error_msg)
            return

        print("✅ 服务器连接成功")
        self.network.start()
        self.login_window.show()
        sys.exit(self.app.exec())

    def on_theme_changed(self, is_night):
        self.is_night_mode = is_night
        # 更新悬浮窗主题
        self.float_window.set_theme_style(is_night)
        self.pomo_float.set_theme_style(is_night)
        # 如果主窗口存在，它会自动处理，不需要手动调

    def handle_login_request(self, username, password):
        print(f"[GUI] 发送登录请求: {username}")
        self.current_attempt_user = username
        pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        login_req = {
            "type": "login",
            "username": username,
            "password": pwd_hash
        }
        self.network.send_request(login_req)

    def on_server_message(self, data):
        msg_type = data.get("type")
        if msg_type == "response":
            self.login_window.hide()
            self.init_main_window()

    def init_main_window(self):
        if not self.main_window:
            self.main_window = MainWindow(is_night=self.is_night_mode)
            self.main_window.set_user_info(self.current_attempt_user)

            self.main_window.switch_float_signal.connect(self.switch_to_float)
            self.main_window.monitor_thread.stats_updated.connect(self.float_window.update_data)

            self.main_window.pomo_update_signal.connect(self.pomo_float.update_time)
            self.main_window.pomo_float_toggle_signal.connect(self.toggle_pomo_float)

            # 同步主题
            self.on_theme_changed(self.is_night_mode)

        self.main_window.show()
        print("[GUI] 进入主界面")

    def switch_to_float(self):
        if self.main_window:
            self.main_window.hide()
        self.float_window.show()

        screen = self.app.primaryScreen().geometry()
        fx = screen.width() - 200
        fy = 100
        self.float_window.move(fx, fy)

        if self.main_window.chk_pomo_float.isChecked():
            self.pomo_float.show()
            self.update_pomo_float_position()

        print("[GUI] 切换到悬浮窗模式")

    def restore_from_float(self):
        self.float_window.hide()
        self.pomo_float.hide()
        if self.main_window:
            self.main_window.show()
            self.main_window.activateWindow()
        print("[GUI] 返回主界面")

    def toggle_pomo_float(self, enabled):
        if self.float_window.isVisible():
            if enabled:
                self.pomo_float.show()
                self.update_pomo_float_position()
            else:
                self.pomo_float.hide()

    def update_pomo_float_position(self):
        main_geo = self.float_window.geometry()
        px = main_geo.x() - self.pomo_float.width() - 10
        py = main_geo.y() + (main_geo.height() - self.pomo_float.height()) // 2
        self.pomo_float.move(px, py)

    def quit_app(self):
        if self.main_window:
            self.main_window.monitor_thread.stop()
        self.app.quit()


if __name__ == '__main__':
    ink_app = InkApplication()
    ink_app.start()