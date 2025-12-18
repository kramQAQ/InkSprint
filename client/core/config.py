import json
import os
import sys

# 默认配置
# 【修改】将默认字体改为 "Microsoft YaHei" (微软雅黑)，这是更符合中文阅读习惯的黑体
DEFAULT_CONFIG = {
    "language": "CN",
    "font_family": "Microsoft YaHei",
    "theme_accent": "#9DC88D",
    "theme_history": ["#9DC88D", "#70A1D7", "#F47C7C"],
    "pomo_state": {
        "seconds": 1500,
        "mode": "timer",
        "is_running": False
    }
}

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "user_config.json"
            )
            cls._instance.data = DEFAULT_CONFIG.copy()
            cls._instance.load()
        return cls._instance

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Config] Load error: {e}")

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Save error: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

Config = ConfigManager()