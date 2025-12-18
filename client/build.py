import PyInstaller.__main__
import os
import sys
import shutil

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

# 清理旧的 dist 和 build 文件夹，防止混淆
dist_path = os.path.join(current_dir, 'dist')
build_path = os.path.join(current_dir, 'build')

print("🧹 Cleaning up old build directories...")
if os.path.exists(dist_path):
    try:
        shutil.rmtree(dist_path)
    except Exception as e:
        print(f"Warning: Could not clean dist folder: {e}")

if os.path.exists(build_path):
    try:
        shutil.rmtree(build_path)
    except Exception as e:
        print(f"Warning: Could not clean build folder: {e}")

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
    '--collect-all=PyQt6',
    '--collect-all=sqlalchemy',
    '--collect-all=cryptography',

    # --- 关键修复 3：显式隐式导入 ---
    '--hidden-import=PyQt6.QtCore',
    '--hidden-import=PyQt6.QtGui',
    '--hidden-import=PyQt6.QtWidgets',
    '--hidden-import=sqlite3',
    '--hidden-import=shared',
    '--hidden-import=shared.security',

    # --- 用户便利性：单文件模式 ---
    # 这会在 dist 目录下直接生成一个 .exe 文件
    '--onefile',

    *icon_arg,  # 图标
    *add_data_arg,  # 数据文件
]

try:
    PyInstaller.__main__.run(args)

    # 检查最终文件位置
    exe_name = "InkSprint.exe" if os.name == 'nt' else "InkSprint"
    final_path = os.path.join(dist_path, exe_name)

    print("\n" + "=" * 50)
    if os.path.exists(final_path):
        print("✅ 打包成功! (Build Success)")
        print(f"文件位置: {final_path}")
        print("您可以直接将此 .exe 文件发送给用户。")
        # 尝试自动打开文件夹 (仅 Windows)
        if os.name == 'nt':
            os.startfile(dist_path)
    else:
        print("❌ 打包看似完成，但在 dist 目录下未找到 exe 文件。")
        print("请检查上方日志是否有错误信息。")
    print("=" * 50 + "\n")

except Exception as e:
    print(f"\n❌ Build failed with exception: {e}")