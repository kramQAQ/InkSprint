import colorsys

# 默认主题色 (用户提到的豆沙绿)
DEFAULT_ACCENT = "#9DC88D"


class ThemeManager:
    """简单的主题管理器，用于动态生成主题字典"""

    @staticmethod
    def get_theme(is_night, accent_color=DEFAULT_ACCENT):
        if is_night:
            return {
                "name": "dark",
                "window_bg": "#18181B",  # 深色背景
                "card_bg": "#27272A",  # 深灰卡片
                "text_main": "#E4E4E7",  # 亮灰文字
                "text_sub": "#A1A1AA",  # 暗灰副文字
                "accent": accent_color,  # 动态主题色
                # 暗色模式下，Hover 时让颜色变亮一点 (Factor > 1)
                "accent_hover": ThemeManager.adjust_color(accent_color, 1.15),
                "input_bg": "#3F3F46",
                "border": "#3F3F46",
                "shadow": "rgba(0, 0, 0, 0.4)",
                "danger": "#F87171"
            }
        else:
            return {
                "name": "light",
                "window_bg": "#F3F4F6",  # 极淡的灰背景
                "card_bg": "#FFFFFF",  # 纯白卡片
                "text_main": "#374151",  # 深灰主文字
                "text_sub": "#9CA3AF",  # 浅灰副文字
                "accent": accent_color,  # 动态主题色
                # 亮色模式下，Hover 时让颜色变暗一点 (Factor < 1) 以增加对比
                "accent_hover": ThemeManager.adjust_color(accent_color, 0.9),
                "input_bg": "#F9FAFB",
                "border": "#E5E7EB",
                "shadow": "rgba(0, 0, 0, 0.05)",
                "danger": "#EF4444"
            }

    @staticmethod
    def adjust_color(hex_color, factor):
        """
        调整 Hex 颜色的亮度
        :param hex_color: 颜色字符串 (e.g. "#9DC88D")
        :param factor: 亮度系数 (1.0 = 原色, <1.0 = 变暗, >1.0 = 变亮)
        :return: 调整后的 Hex 字符串
        """
        try:
            # 1. 移除 '#' 并解析 RGB
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6:
                return hex_color

            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

            # 2. RGB (0-255) 转 HLS (0-1)
            # colorsys 需要 0-1 的输入
            h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

            # 3. 调整亮度 (Lightness)
            # 限制在 0.0 到 1.0 之间
            new_l = max(0.0, min(1.0, l * factor))

            # 4. HLS 转回 RGB
            r_new, g_new, b_new = colorsys.hls_to_rgb(h, new_l, s)

            # 5. 转回 Hex
            return f"#{int(r_new * 255):02X}{int(g_new * 255):02X}{int(b_new * 255):02X}"

        except Exception as e:
            print(f"[Theme] Color adjust error: {e}")
            return hex_color