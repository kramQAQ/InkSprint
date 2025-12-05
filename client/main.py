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
# [修改] 导入 FloatWindow 和 默认颜色
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
        self.main_window = None  # 登录成功后再创建

        # [修改] 初始化悬浮窗 (传入默认颜色)
        # 注意：这里创建一个全局悬浮窗实例，或者也可以后续委托给 MainWindow 管理
        # 为了避免逻辑冲突，这里我们先初始化一个，后续如果 MainWindow 接管了，可以隐藏这个
        self.float_window = FloatWindow(DEFAULT_ACCENT)

        # 信号连接
        self.login_window.login_signal.connect(self.handle_login_request)
        # self.login_window.theme_changed.connect(self.on_theme_changed) # 登录页主题切换暂时不需要同步到未创建的主窗口

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
            # 简单处理：收到响应即认为登录成功
            self.login_window.hide()
            self.init_main_window()

    def init_main_window(self):
        if not self.main_window:
            # 获取登录窗口最后的主题状态（可选）
            self.is_night_mode = self.login_window.is_night

            # 创建主窗口
            self.main_window = MainWindow(is_night=self.is_night_mode)
            self.main_window.set_user_info(self.current_attempt_user)

            # [关键] 主窗口内部已经实例化了自己的 FloatWindow (在 MainWindow.__init__ 中)
            # 并且处理了所有信号连接（模式切换、数据更新等）
            # 所以为了避免重复和冲突，我们销毁 main.py 里的这个临时 float_window
            # 转而使用 main_window.float_window
            if self.float_window:
                self.float_window.close()
                self.float_window = None

            # 重新绑定系统托盘的“恢复”操作到主窗口的逻辑
            # 注意：这里我们通过调用 main_window 的方法来间接控制
            # MainWindow 内部的 float_window.restore_signal 已经连接到了它的 restore_from_float
            pass

        self.main_window.show()
        print("[GUI] 进入主界面")

    def switch_to_float(self):
        """切换到悬浮窗模式 (委托给 MainWindow)"""
        if self.main_window:
            self.main_window.switch_to_float()
        else:
            # 如果还没登录进主界面，暂不支持
            pass

    def restore_from_float(self):
        """从悬浮窗恢复 (委托给 MainWindow)"""
        if self.main_window:
            self.main_window.restore_from_float()

    def quit_app(self):
        if self.main_window:
            self.main_window.monitor_thread.stop()
        self.app.quit()


if __name__ == '__main__':
    ink_app = InkApplication()
    ink_app.start()