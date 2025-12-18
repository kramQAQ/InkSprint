import PyInstaller.__main__
import os
import sys

# 获取项目根目录 (client 的上一级)，以便找到 'shared' 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# 检查 logo.png 是否存在
logo_path = "logo.png"
if not os.path.exists(logo_path):
    print("Warning: logo.png not found. Using default icon.")
    icon_arg = []
    add_data_arg = []
else:
    icon_arg = [f'--icon={logo_path}']
    # Windows 使用分号 ; 分隔，Linux/Mac 使用冒号 :
    separator = ';' if os.name == 'nt' else ':'
    # 将 logo.png 打包到 exe 内部的根目录 (.)
    add_data_arg = [f'--add-data={logo_path}{separator}.']

print("🚀 Starting build process...")

# PyInstaller 参数
args = [
    'main.py',  # 主程序入口
    '--name=InkSprint',  # exe 名称
    '--noconsole',  # 无控制台 (GUI模式)
    '--clean',  # 清理临时文件
    '--noconfirm',  # 不询问确认直接覆盖

    # --- 关键修复 1：添加搜索路径 ---
    # 确保 PyInstaller 能找到 ../shared 目录下的模块
    f'--paths={project_root}',

    # --- 关键修复 2：解决 DLL 缺失问题 ---
    # 使用 --collect-all 强制收集库的所有依赖文件（包括 DLL、资源等）
    # 这会增加包的大小，但能最大程度确保运行环境完整，解决 "Failed to load DLL" 错误
    '--collect-all=PyQt6',
    '--collect-all=sqlalchemy',
    '--collect-all=cryptography',

    # --- 关键修复 3：显式隐式导入 ---
    # 防止静态分析遗漏这些模块
    '--hidden-import=PyQt6.QtCore',
    '--hidden-import=PyQt6.QtGui',
    '--hidden-import=PyQt6.QtWidgets',
    '--hidden-import=sqlite3',
    '--hidden-import=shared',
    '--hidden-import=shared.security',

    # 注意：默认打包为 "文件夹模式" (onedir)，方便排查 DLL 问题。
    # 如果您必须要是单文件 (onefile)，请取消下一行的注释，但在解决 DLL 问题前建议保持注释。
    # '--onefile',

    *icon_arg,  # 图标
    *add_data_arg,  # 数据文件
]

try:
    PyInstaller.__main__.run(args)
    print("\n✅ Build complete!")
    print(f"Check the 'dist/InkSprint' folder for your executable.")
    print(f"Run 'InkSprint.exe' to start.")
except Exception as e:
    print(f"\n❌ Build failed: {e}")