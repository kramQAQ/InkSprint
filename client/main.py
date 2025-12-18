import sys
import os
import hashlib

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon
from ui.login import LoginWindow
from ui.main_window import MainWindow
from ui.float_window import FloatWindow
from ui.theme import DEFAULT_ACCENT
from core.network import NetworkManager
from ui.localization import STRINGS, update_language
from core.config import Config


# --- 【新增】路径处理辅助函数 ---
def get_base_path():
    """
    获取程序运行的基础路径（用于存放配置文件等可读写数据）。
    如果是打包后的 exe，返回 exe 所在目录；
    如果是脚本运行，返回 main.py 所在目录。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径（用于图标等静态资源）。
    打包后，资源文件位于 sys._MEIPASS 中。
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


# --------------------------------

class InkApplication:
    def __init__(self):
        # 【修复】设置 Windows 任务栏图标 ID，防止显示默认 Python 图标
        if os.name == 'nt':
            try:
                import ctypes
                myappid = 'kramqaq.inksprint.client.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        self.app = QApplication(sys.argv)

        # 确保退出时清理
        self.app.setQuitOnLastWindowClosed(True)

        # 【修改】使用资源路径加载图标
        self.icon_path = get_resource_path("logo.png")
        print(f"[Init] Searching for icon at: {self.icon_path}")

        if os.path.exists(self.icon_path):
            print("[Init] Icon file found. Setting application icon.")
            self.app_icon = QIcon(self.icon_path)
            self.app.setWindowIcon(self.app_icon)
        else:
            print("[Init] Warning: 'logo.png' not found. Using default icon.")
            self.app_icon = None

        # 【核心修改】重定向 Config 保存路径到 EXE 同级目录
        # 这样用户生成的配置文件就会保存在 exe 旁边，方便查找和备份
        base_path = get_base_path()
        Config.config_path = os.path.join(base_path, "user_config.json")
        print(f"[Init] Config path set to: {Config.config_path}")

        self.load_app_config()

        self.network = NetworkManager(port=23456)
        self.network.message_received.connect(self.on_server_message)

        # 初始化窗口
        self.login_window = LoginWindow()
        if self.app_icon:
            self.login_window.setWindowIcon(self.app_icon)

        self.main_window = None

        # 悬浮窗颜色从配置读
        accent = Config.get("theme_accent", DEFAULT_ACCENT)
        self.float_window = FloatWindow(accent)
        if self.app_icon:
            self.float_window.setWindowIcon(self.app_icon)

        # 信号连接
        self.login_window.login_signal.connect(self.handle_login_request)
        self.login_window.register_signal.connect(self.handle_register_request)
        self.login_window.send_code_signal.connect(self.handle_send_code_request)
        self.login_window.reset_pwd_signal.connect(self.handle_reset_pwd_request)
        self.float_window.restore_signal.connect(self.restore_from_float)

        self.is_night_mode = False
        self.current_user_info = {}

        self.setup_tray()

        self.app.aboutToQuit.connect(self.quit_app)

    def load_app_config(self):
        """加载全局配置并应用语言"""
        # 加载配置前，Config.load() 会被自动调用，或者我们需要手动 reload
        # 因为我们在 __init__ 里修改了 path，这里最好显式 load 一次
        Config.load()
        lang = Config.get("language", "CN")
        update_language(lang)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)

        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)

        tray_menu = QMenu()

        action_show = QAction(STRINGS["tray_show"], self.app)
        action_show.triggered.connect(self.restore_from_float)

        action_float = QAction(STRINGS["tray_float"], self.app)
        action_float.triggered.connect(self.switch_to_float)

        action_quit = QAction(STRINGS["tray_quit"], self.app)
        action_quit.triggered.connect(self.app.quit)

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
                self.current_user_info = {
                    "nickname": data.get("nickname"),
                    "username": data.get("username"),
                    "email": data.get("email"),
                    "avatar_data": data.get("avatar_data"),
                    "today_total": data.get("today_total", 0),
                    "current_group": data.get("current_group", {}),
                    "user_id": data.get("user_id", 0)
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

        elif self.main_window:
            self.main_window.dispatch_network_message(data)

    def init_main_window(self):
        if not self.main_window:
            self.is_night_mode = self.login_window.is_night
            self.main_window = MainWindow(is_night=self.is_night_mode, network_manager=self.network)
            user_data = self.current_user_info.copy()
            self.main_window.set_user_info(user_data)

            if self.app_icon:
                self.main_window.setWindowIcon(self.app_icon)

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
                self.main_window.monitor_thread.stop()
                self.main_window.monitor_thread.wait()
            # 退出前保存一下主窗口状态
            self.main_window.close()

        if self.network:
            self.network.close()


if __name__ == '__main__':
    ink_app = InkApplication()
    ink_app.start()