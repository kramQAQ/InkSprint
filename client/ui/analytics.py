from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QPushButton, QButtonGroup, QScrollArea, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont
import datetime
import csv
from .localization import STRINGS


class HeatmapWidget(QWidget):
    """Github 风格的贡献热力图"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(140)
        self.data = {}
        self.text_color = QColor("#333")  # 默认文字颜色
        self.is_dark = False  # 明确的主题模式标志

    def set_data(self, data):
        self.data = data
        self.update()

    def set_text_color(self, color):
        """设置文字颜色"""
        self.text_color = QColor(color)
        self.update()

    def set_theme_mode(self, is_dark):
        """明确设置是否为深色模式"""
        self.is_dark = is_dark
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = [
            QColor("#EBEDF0"),  # 0
            QColor("#9BE9A8"),  # 1-499
            QColor("#40C463"),  # 500-1499
            QColor("#30A14E"),  # 1500-2999
            QColor("#216E39")  # 3000+
        ]

        # 修复：明确根据黑夜模式标志调整基础色，而不是猜测文字亮度
        if self.is_dark:
            colors[0] = QColor("#3F3F46")  # 深灰色底

        today = datetime.date.today()
        one_year_ago = today - datetime.timedelta(days=365)

        start_date = one_year_ago - datetime.timedelta(days=one_year_ago.weekday() + 1)
        if start_date.weekday() != 6:
            start_date = one_year_ago - datetime.timedelta(days=(one_year_ago.weekday() + 1) % 7)

        cell_size = 12
        spacing = 3

        for col in range(53):
            for row in range(7):
                current_date = start_date + datetime.timedelta(days=col * 7 + row)
                if current_date > today: continue

                date_str = str(current_date)
                count = self.data.get(date_str, 0)

                color_idx = 0
                if count >= 3000:
                    color_idx = 4
                elif count >= 1500:
                    color_idx = 3
                elif count >= 500:
                    color_idx = 2
                elif count >= 1:
                    color_idx = 1

                painter.setBrush(QBrush(colors[color_idx]))
                painter.setPen(Qt.PenStyle.NoPen)

                x = col * (cell_size + spacing)
                y = row * (cell_size + spacing) + 20

                painter.drawRoundedRect(x, y, cell_size, cell_size, 2, 2)

                if row == 0 and current_date.day <= 7:
                    painter.setPen(QPen(self.text_color))  # 使用适配颜色
                    painter.drawText(x, 15, current_date.strftime("%b"))


class SimpleChartWidget(QWidget):
    """自定义绘制的柱状图"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(250)
        self.mode = "Week"
        self.data = {}
        self.accent_color = QColor("#9DC88D")
        self.text_color = QColor("#555")  # 默认
        self.line_color = QColor("#CCCCCC")  # 默认

    def set_colors(self, accent, text, line):
        self.accent_color = QColor(accent)
        self.text_color = QColor(text)
        self.line_color = QColor(line)
        self.update()

    def set_data(self, labels, values, mode):
        self.mode = mode
        self.data = {"labels": labels, "values": values}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        padding = 40

        painter.setPen(QPen(self.line_color, 1))
        painter.drawLine(padding, h - padding, w - padding, h - padding)

        if not self.data.get("values"): return

        values = self.data["values"]
        labels = self.data["labels"]
        max_val = max(values) if values else 100
        if max_val == 0: max_val = 100

        count = len(values)
        if count == 0: return
        step_x = (w - 2 * padding) / count

        painter.setBrush(QBrush(self.accent_color))

        for i, val in enumerate(values):
            bar_h = (val / max_val) * (h - 2 * padding)
            x = padding + i * step_x + (step_x * 0.2)
            y = h - padding - bar_h
            bar_w = step_x * 0.6

            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 4, 4)

            painter.setPen(QPen(self.text_color))
            painter.drawText(int(x), int(y) - 5, int(bar_w), 20, Qt.AlignmentFlag.AlignCenter, str(val))

            painter.drawText(int(x - 10), int(h - padding + 5), int(bar_w + 20), 20, Qt.AlignmentFlag.AlignCenter,
                             labels[i])


class AnalyticsPage(QWidget):
    def __init__(self, network_manager):
        super().__init__()
        self.network = network_manager
        self.full_heatmap_data = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        top_bar = QHBoxLayout()
        self.lbl_title = QLabel(STRINGS["analytics_title_header"])
        # Initial style, will be overridden by apply_theme
        self.lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        top_bar.addWidget(self.lbl_title)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(35, 35)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setToolTip("刷新数据 (Refresh)")
        self.btn_refresh.clicked.connect(self.load_data)
        top_bar.addWidget(self.btn_refresh)

        top_bar.addStretch()

        self.btn_group = QButtonGroup(self)
        modes = [("Week", STRINGS["btn_week"]), ("Month", STRINGS["btn_month"]), ("Year", STRINGS["btn_year"])]
        self.mode_btns = {}
        for code, label in modes:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(80, 30)
            btn.clicked.connect(lambda _, mode=code: self.update_chart_view(mode))
            self.btn_group.addButton(btn)
            self.mode_btns[code] = btn
            top_bar.addWidget(btn)

        self.mode_btns["Week"].setChecked(True)
        layout.addLayout(top_bar)

        self.chart = SimpleChartWidget()
        layout.addWidget(self.chart)

        layout.addSpacing(20)
        self.lbl_contrib = QLabel(STRINGS["graph_title"])
        self.lbl_contrib.setStyleSheet("font-size: 16px; font-weight: bold; color: #555;")
        layout.addWidget(self.lbl_contrib)

        self.heatmap = HeatmapWidget()
        layout.addWidget(self.heatmap)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_details = QPushButton(STRINGS["btn_view_details"])
        self.btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_details.setFixedHeight(40)
        self.btn_details.clicked.connect(self.show_details_dialog)
        btn_layout.addWidget(self.btn_details)
        layout.addLayout(btn_layout)

    def apply_theme(self, t):
        """应用黑夜/白天模式"""
        # 1. 标题和文字颜色
        self.lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {t['text_main']};")
        self.lbl_contrib.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {t['text_sub']};")

        # 2. 按钮样式 (普通)
        btn_style = f"""
            QPushButton {{ 
                border: 1px solid {t['border']}; 
                border-radius: 5px; 
                background: {t['card_bg']}; 
                color: {t['text_main']};
                font-size: 14px; 
            }}
            QPushButton:hover {{ background-color: {t['input_bg']}; }}
            QPushButton:checked {{ background-color: {t['accent']}; color: white; border: none; }}
        """
        self.btn_refresh.setStyleSheet(btn_style)
        for btn in self.mode_btns.values():
            btn.setStyleSheet(btn_style)

        # 3. 详情按钮 (主题色)
        self.btn_details.setStyleSheet(f"""
            QPushButton {{ background-color: {t['accent']}; color: white; border-radius: 8px; font-weight: bold; padding: 0 20px; }}
            QPushButton:hover {{ background-color: {t['accent_hover']}; }}
        """)

        # 4. 图表重绘
        self.chart.set_colors(t['accent'], t['text_main'], t['border'])
        self.heatmap.set_text_color(t['text_sub'])
        # 关键修复：传递 explicitly 的明暗模式标志
        self.heatmap.set_theme_mode(t['name'] == 'dark')

    def load_data(self):
        if self.network:
            print("[Analytics] Manually refreshing data...")
            self.network.send_request({"type": "get_analytics"})
            self.btn_refresh.setEnabled(False)
            QTimer.singleShot(1000, lambda: self.btn_refresh.setEnabled(True))

    def handle_response(self, data):
        if data.get("type") == "analytics_data":
            self.full_heatmap_data = data.get("heatmap", {})
            self.heatmap.set_data(self.full_heatmap_data)
            mode = "Week"
            if self.mode_btns["Month"].isChecked(): mode = "Month"
            if self.mode_btns["Year"].isChecked(): mode = "Year"
            self.update_chart_view(mode)
        elif data.get("type") == "details_data":
            self.open_details_dialog(data.get("data", []))

    def update_chart_view(self, mode):
        today = datetime.date.today()
        labels = []
        values = []

        if mode == "Week":
            for i in range(6, -1, -1):
                d = today - datetime.timedelta(days=i)
                d_str = str(d)
                labels.append(d.strftime("%a"))
                values.append(self.full_heatmap_data.get(d_str, 0))

        elif mode == "Month":
            for i in range(29, -1, -1):
                d = today - datetime.timedelta(days=i)
                d_str = str(d)
                labels.append(str(d.day) if i % 5 == 0 else "")
                values.append(self.full_heatmap_data.get(d_str, 0))

        elif mode == "Year":
            for i in range(11, -1, -1):
                month_start = (today.replace(day=1) - datetime.timedelta(days=i * 30)).replace(day=1)
                month_key = month_start.strftime("%Y-%m")
                labels.append(month_start.strftime("%b"))
                total = 0
                for date_str, count in self.full_heatmap_data.items():
                    if date_str.startswith(month_key):
                        total += count
                values.append(total)

        self.chart.set_data(labels, values, mode)

    def show_details_dialog(self):
        if self.network:
            self.network.send_request({"type": "get_details"})

    def open_details_dialog(self, records):
        dlg = QDialog(self)
        dlg.setWindowTitle(STRINGS["dialog_details_title"])
        dlg.resize(500, 400)

        layout = QVBoxLayout(dlg)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([STRINGS["col_time"], STRINGS["col_added"], STRINGS["col_duration"]])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(records))
        for i, row in enumerate(records):
            table.setItem(i, 0, QTableWidgetItem(row['time']))
            table.setItem(i, 1, QTableWidgetItem(f"+{row['increment']}"))
            table.setItem(i, 2, QTableWidgetItem(str(row['duration'])))
        layout.addWidget(table)

        # 新增：导出按钮
        btn_export = QPushButton("💾 导出 CSV / Export to CSV")
        # 设置简单样式
        btn_export.setStyleSheet("""
            QPushButton { background-color: #eee; border: 1px solid #ccc; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #ddd; }
        """)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(lambda: self.export_records(records))
        layout.addWidget(btn_export)

        dlg.exec()

    def export_records(self, records):
        """将记录导出为本地 CSV 文件"""
        if not records:
            QMessageBox.information(self, STRINGS["warn_title"], "没有数据可导出 / No data to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "ink_records.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                # 使用 utf-8-sig 以便 Excel 正确识别中文
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # 写入表头
                    writer.writerow(["Time", "Increment (Words)", "Duration (Seconds)"])
                    # 写入数据
                    for r in records:
                        writer.writerow([r['time'], r['increment'], r['duration']])

                QMessageBox.information(self, STRINGS["success_title"], f"导出成功！\nSaved to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, STRINGS["error_title"], f"导出失败: {str(e)}")