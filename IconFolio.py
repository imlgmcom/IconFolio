import os
import sys
import subprocess
import configparser
import time
import msvcrt
import shutil
import datetime
import ctypes
from ctypes import wintypes
import win32api
import win32con
from win32com.shell.shell import SHChangeNotify
from win32com.shell import shellcon

# 版本信息
VERSION = "IconFolio v25.9.6 by DouBaoAi"  # 版本号更新

# 全局变量
OPERATE_DIR = ""
FOLDERS_TXT_NAME = "folders.txt"
EXCLUDE_KEYWORDS = ["uninstall", "step"]
FOLDERS_ENCODING = "gbk"  # Windows中文系统ANSI编码对应gbk
# 确定系统编码（扩展常见映射版）
try:
    # 调用Windows API获取ANSI代码页
    cp = ctypes.windll.kernel32.GetACP()
    
    # 常见代码页与编码的映射关系（扩展至10个主要语言区域）
    code_page_map = {
        936: "gbk",        # 简体中文
        65001: "utf-8",    # Unicode (UTF-8)
        1252: "cp1252",    # 西欧语言（英语、法语、德语等）
        950: "big5",       # 繁体中文
        932: "shift_jis",  # 日语
        949: "cp949",      # 韩语
        1251: "cp1251",    # 俄语
        1250: "cp1250",    # 中欧语言（波兰语、捷克语等）
        1254: "cp1254",    # 土耳其语
        874: "cp874"       # 泰语
    }
    
    # 查找对应的编码，如果没有则使用默认
    FOLDERS_ENCODING = code_page_map.get(cp, "gbk")
    print(f"✅ 自动检测到系统编码: {FOLDERS_ENCODING} (代码页: {cp})")
except Exception as e:
    # 其他异常情况使用默认编码
    FOLDERS_ENCODING = "gbk"
    print(f"❌ 获取系统编码时发生错误: {e}，使用默认编码: {FOLDERS_ENCODING}")

# ------------------------------
# Windows API 基础定义
# ------------------------------
user32 = ctypes.WinDLL('user32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)

# 用于图标缓存的结构体和常量
class SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", ctypes.c_char * 260),
        ("szTypeName", ctypes.c_char * 80),
    ]

SHGFI_ICON = 0x000000100
SHGFI_SMALLICON = 0x000000001
SHGFI_LARGEICON = 0x000000000
SHGFI_USEFILEATTRIBUTES = 0x000000010
FILE_ATTRIBUTE_DIRECTORY = 0x00000010


# ------------------------------
# 基础工具函数
# ------------------------------
def wait_for_space():
    """等待空格键确认，统一交互体验"""
    print("按空格键继续...", end='', flush=True)
    while True:
        if msvcrt.getch() == b' ':
            print()
            break


def check_dependency():
    """检查并自动安装pywin32依赖"""
    required = [
        ("win32api", "pywin32"),
        ("win32com.shell", "pywin32")
    ]

    for module, install_name in required:
        try:
            __import__(module)
            print(f"✅ {module} 已安装")
        except ImportError:
            print(f"⚠️  缺失 {install_name}，正在自动安装...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", install_name],
                    timeout=30,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                __import__(module)
                print(f"✅ {install_name} 安装成功")
            except Exception as e:
                print(f"❌ 安装失败，请手动执行：pip install {install_name}")
                return False
    return True


def select_operate_directory():
    """选择操作目录并保存到全局变量"""
    global OPERATE_DIR
    print("=" * 40)
    print("          请选择操作目录          ")
    print("=" * 40)
    while True:
        try:
            print(f"1. 使用当前目录（{os.getcwd()}）")
            print("2. 手动指定路径")
            choice = input("请输入选择（1/2）：").strip()
            
            if choice == '1':
                current_dir = os.getcwd()
                print(f"\n✅ 已选择当前目录：{current_dir}")
                OPERATE_DIR = current_dir
                return current_dir
            elif choice == '2':
                path = input("\n请输入目录路径：").strip().strip('"')
                if os.path.isdir(path):
                    print(f"✅ 已选择目录：{path}")
                    OPERATE_DIR = path
                    return path
                else:
                    print("❌ 路径无效，请重新输入")
            else:
                print("❌ 请输入 1 或 2")
        except Exception as e:
            print(f"❌ 目录选择出错：{str(e)}")
            wait_for_space()


# ------------------------------
# 缓存生成与刷新核心功能
# ------------------------------
def trigger_icon_cache(folder_path):
    """触发单个文件夹的图标缓存生成"""
    folder_path = os.path.abspath(folder_path)
    success = False
    
    try:
        # 方法1：获取小图标和大图标，强制系统缓存
        shfi_small = SHFILEINFO()
        shfi_large = SHFILEINFO()
        folder_path_bytes = os.fsencode(folder_path)
        
        # 获取小图标
        result_small = shell32.SHGetFileInfo(
            folder_path_bytes,
            FILE_ATTRIBUTE_DIRECTORY,
            ctypes.byref(shfi_small),
            ctypes.sizeof(shfi_small),
            SHGFI_ICON | SHGFI_SMALLICON | SHGFI_USEFILEATTRIBUTES
        )
        
        # 获取大图标
        result_large = shell32.SHGetFileInfo(
            folder_path_bytes,
            FILE_ATTRIBUTE_DIRECTORY,
            ctypes.byref(shfi_large),
            ctypes.sizeof(shfi_large),
            SHGFI_ICON | SHGFI_LARGEICON | SHGFI_USEFILEATTRIBUTES
        )
        
        # 释放图标资源
        if shfi_small.hIcon:
            user32.DestroyIcon(shfi_small.hIcon)
        if shfi_large.hIcon:
            user32.DestroyIcon(shfi_large.hIcon)
            
        success = result_small != 0 or result_large != 0
        
        # 方法2：修改文件夹属性触发缓存（如果方法1失败）
        if not success:
            attr = win32api.GetFileAttributes(folder_path)
            # 先设置为只读
            win32api.SetFileAttributes(folder_path, win32con.FILE_ATTRIBUTE_READONLY)
            time.sleep(0.1)  # 短暂延迟确保系统捕获变化
            # 恢复原属性
            win32api.SetFileAttributes(folder_path, attr)
            success = True
            
        # 方法3：创建并删除临时文件触发目录刷新（如果前两种方法失败）
        if not success:
            temp_file = os.path.join(folder_path, "temp_icon_refresh.tmp")
            try:
                with open(temp_file, 'w') as f:
                    f.write("temp file to trigger refresh")
                os.remove(temp_file)
                success = True
            except:
                pass
                
        return success
        
    except Exception as e:
        print(f"   ⚠️  缓存触发异常: {str(e)}")
        return False


def refresh_folder(folder_path):
    """刷新单个文件夹并触发缓存生成"""
    try:
        # 确保路径规范化
        folder_path = os.path.abspath(folder_path)
        folder_path = os.path.normpath(folder_path)
        folder_name = os.path.basename(folder_path)
        
        # 初始化缓存成功标志（默认设为False）
        cache_success = False  # 关键修复：在函数开始处定义变量
        
        # 步骤1：通知系统文件夹属性已更新
        SHChangeNotify(
            shellcon.SHCNE_UPDATEDIR,
            shellcon.SHCNF_PATH | shellcon.SHCNF_FLUSH,
            os.fsencode(folder_path),
            None
        )
        
        # 步骤2：设置为系统文件夹属性
        try:
            original_attr = win32api.GetFileAttributes(folder_path)
            win32api.SetFileAttributes(folder_path, original_attr | win32con.FILE_ATTRIBUTE_SYSTEM)
            time.sleep(0.2)
        except Exception as e:
            print(f"   ⚠️ 属性设置警告：{str(e)}")
            try:
                subprocess.run(
                    f'attrib +s "{folder_path}"',
                    shell=True,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(0.2)
            except Exception as e2:
                print(f"   ❌ 属性设置失败：{str(e2)}")
                return False, cache_success  # 现在可以安全返回了
        
        # 步骤3：多次尝试触发图标缓存生成
        for attempt in range(3):
            cache_success = trigger_icon_cache(folder_path)
            if cache_success:
                break
            time.sleep(0.2)
            
        # 步骤4：恢复原始属性
        time.sleep(0.2)
        win32api.SetFileAttributes(folder_path, original_attr)
        
        # 步骤5：再次通知系统更新
        SHChangeNotify(
            shellcon.SHCNE_UPDATEDIR,
            shellcon.SHCNF_PATH | shellcon.SHCNF_FLUSH,
            os.fsencode(folder_path),
            None
        )
        
        return True, cache_success
    except Exception as e:
        print(f"   ❌ 刷新失败: {str(e)}")
        return False, False  # 这里也能安全返回


def refresh_system_icon_cache():
    """刷新系统图标缓存"""
    try:
        print("\n" + "-" * 40)
        print("          刷新系统图标缓存          ")
        print("-" * 40)
        
        # 缓存文件路径
        cache_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "IconCache.db"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData\\Local\\Microsoft\\Windows\\Explorer\\iconcache*")
        ]
        
        # 终止资源管理器进程
        print("   终止资源管理器进程...")
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        
        # 删除缓存文件
        for path in cache_paths:
            try:
                if "*" in path:
                    import glob
                    for f in glob.glob(path):
                        if os.path.exists(f):
                            os.remove(f)
                            print(f"   删除缓存：{f}")
                elif os.path.exists(path):
                    os.remove(path)
                    print(f"   删除缓存：{path}")
            except Exception as e:
                print(f"   缓存删除失败 {path}：{str(e)}")
        time.sleep(2)
        print("   重启资源管理器（系统外壳）...")
        subprocess.Popen(["explorer.exe"])  
        # 额外清理：重建图标缓存数据库
        print("   重建系统图标缓存...")
        subprocess.run(
            ["ie4uinit.exe", "-ClearIconCache"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        # 单独打开工作目录
        if OPERATE_DIR and os.path.isdir(OPERATE_DIR):
            print(f"   打开工作目录：{OPERATE_DIR}")
            subprocess.Popen(["explorer.exe", OPERATE_DIR])
            time.sleep(2)
        print("✅ 系统图标缓存已重建，任务栏已恢复")
        return True
    except Exception as e:
        print(f"⚠️  系统缓存刷新失败：{str(e)}")
        # 确保资源管理器重启
        subprocess.Popen(["explorer.exe"])
        time.sleep(2)
        subprocess.Popen(["explorer.exe", OPERATE_DIR])
        return False


# ------------------------------
# 文件操作相关函数
# ------------------------------
def ensure_file_writable(file_path):
    """确保文件可写"""
    try:
        if os.path.exists(file_path):
            attrs = win32api.GetFileAttributes(file_path)
            win32api.SetFileAttributes(
                file_path, 
                attrs & ~(win32con.FILE_ATTRIBUTE_READONLY | win32con.FILE_ATTRIBUTE_SYSTEM)
            )
        return True
    except Exception as e:
        print(f"⚠️  无法修改属性 {os.path.basename(file_path)}：{str(e)}")
        return False


def get_valid_exes(folder_path):
    """获取有效EXE文件（返回绝对路径和相对路径的元组）"""
    exes = []
    folder_abs = os.path.abspath(folder_path)
    for root, _, files in os.walk(folder_abs):
        for file in files:
            if file.lower().endswith('.exe') and not any(kw in file.lower() for kw in EXCLUDE_KEYWORDS):
                abs_path = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(abs_path, folder_abs)
                exes.append( (abs_path, rel_path) )
    # 去重（基于绝对路径）
    seen = set()
    return [ (abs_p, rel_p) for abs_p, rel_p in exes if not (abs_p in seen or seen.add(abs_p)) ]


# ------------------------------
# 备份功能
# ------------------------------
def backup_folders_txt():
    current_dir = OPERATE_DIR
    txt_path = os.path.join(current_dir, FOLDERS_TXT_NAME)
    
    if os.path.exists(txt_path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(current_dir, f"folders-{timestamp}.txt")
        try:
            shutil.copy2(txt_path, backup_path)
            print(f"✅ 已备份 {FOLDERS_TXT_NAME} 到：{backup_path}")
        except Exception as e:
            print(f"⚠️  备份失败：{str(e)}，仍将继续操作")
    else:
        print("ℹ️  未找到现有配置文件，无需备份")


# ------------------------------
# folders.txt 生成与更新功能
# ------------------------------
def generate_folders_txt_interactive():
    """交互生成folders.txt（存储相对路径）"""
    try:
        print("\n" + "-" * 40)
        print("          交互生成 folders.txt（相对路径版）          ")
        print("-" * 40)
        backup_folders_txt()
        
        current_dir = OPERATE_DIR
        txt_path = os.path.join(current_dir, FOLDERS_TXT_NAME)
        folders = [
            f for f in os.listdir(current_dir)
            if os.path.isdir(os.path.join(current_dir, f)) and not f.startswith('.')
        ]
        if not folders:
            print("ℹ️  没有找到可处理的文件夹")
            return

        if os.path.exists(txt_path):
            confirm = input(f"⚠️  即将覆盖现有 {FOLDERS_TXT_NAME}，是否继续？(y/n)：").strip().lower()
            if confirm != 'y':
                print("ℹ️  已取消生成")
                return

        with open(txt_path, 'w', encoding=FOLDERS_ENCODING) as f:
            f.write("# 文件夹图标配置文件（存储相对路径）\n")
            f.write("# 格式：\n")
            f.write("# [文件夹名]\n")
            f.write("# LocalizedResourceName=显示名（别名，可修改）\n")
            f.write("# IconResource=EXE文件相对路径（相对于文件夹本身）\n\n")
            
            total = len(folders)
            for i, folder in enumerate(folders, 1):
                print(f"\n[{i}/{total}] 处理文件夹：{folder}")
                folder_path = os.path.join(current_dir, folder)
                exes = get_valid_exes(folder_path)
                
                if not exes:
                    print(f"   ⚠️  未找到有效EXE，跳过")
                    continue
                
                selected_abs = None
                selected_rel = None
                if len(exes) == 1:
                    abs_path, rel_path = exes[0]
                    print(f"   找到1个有效EXE（相对路径）：{rel_path}")
                    print(f"   对应绝对路径：{abs_path}")
                    selected_abs = abs_path
                    selected_rel = rel_path
                else:
                    print(f"   找到{len(exes)}个有效EXE，请选择：")
                    for j, (abs_path, rel_path) in enumerate(exes, 1):
                        print(f"   {j}. 相对路径：{rel_path}")
                        print(f"      绝对路径：{abs_path}")
                    while True:
                        try:
                            choice = input(f"   请输入序号（1-{len(exes)}，0=跳过）：").strip()
                            num = int(choice)
                            if num == 0:
                                break
                            if 1 <= num <= len(exes):
                                selected_abs, selected_rel = exes[num-1]
                                print(f"   已选择相对路径：{selected_rel}")
                                break
                            else:
                                print(f"   请输入1到{len(exes)}之间的数字")
                        except ValueError:
                            print("   请输入有效数字")
                
                if selected_rel:
                    f.write(f"[{folder}]\n")
                    f.write(f"LocalizedResourceName={folder}\n")
                    f.write(f"IconResource={selected_rel}\n\n")
                    print(f"   ✅ 已添加到配置")
        
        print(f"\n✅ 成功生成 {txt_path}（编码：{FOLDERS_ENCODING}）")
    except Exception as e:
        print(f"❌ 生成失败：{str(e)}")
    finally:
        wait_for_space()


def generate_folders_txt_auto():
    """自动生成folders.txt（存储相对路径）"""
    try:
        print("\n" + "-" * 40)
        print("          自动生成 folders.txt（相对路径版）          ")
        print("-" * 40)
        backup_folders_txt()
        
        current_dir = OPERATE_DIR
        txt_path = os.path.join(current_dir, FOLDERS_TXT_NAME)
        folders = [
            f for f in os.listdir(current_dir)
            if os.path.isdir(os.path.join(current_dir, f)) and not f.startswith('.')
        ]
        if not folders:
            print("ℹ️  没有找到可处理的文件夹")
            return

        if os.path.exists(txt_path):
            confirm = input(f"⚠️  即将覆盖现有 {FOLDERS_TXT_NAME}，是否继续？(y/n)：").strip().lower()
            if confirm != 'y':
                print("ℹ️  已取消生成")
                return

        with open(txt_path, 'w', encoding=FOLDERS_ENCODING) as f:
            f.write("# 文件夹图标配置文件（自动生成，存储相对路径）\n")
            f.write("# 格式：\n")
            f.write("# [文件夹名]\n")
            f.write("# LocalizedResourceName=显示名\n")
            f.write("# IconResource=EXE文件相对路径（相对于文件夹本身）\n\n")
            
            total = len(folders)
            processed = 0
            for folder in folders:
                folder_path = os.path.join(current_dir, folder)
                exes = get_valid_exes(folder_path)
                
                if exes:
                    selected_abs, selected_rel = exes[0]
                    f.write(f"[{folder}]\n")
                    f.write(f"LocalizedResourceName={folder}\n")
                    f.write(f"IconResource={selected_rel}\n\n")
                    processed += 1
                    print(f"✅ 处理：{folder}（相对路径：{selected_rel}）")
                else:
                    print(f"⚠️  跳过：{folder}（无有效EXE）")
        
        print(f"\n✅ 成功生成 {txt_path}（编码：{FOLDERS_ENCODING}）")
    except Exception as e:
        print(f"❌ 生成失败：{str(e)}")
    finally:
        wait_for_space()


def update_folders_txt_interactive():
    """交互更新folders.txt（仅添加新文件夹）"""
    try:
        print("\n" + "-" * 40)
        print("          交互更新 folders.txt（相对路径版）          ")
        print("-" * 40)
        backup_folders_txt()
        
        current_dir = OPERATE_DIR
        txt_path = os.path.join(current_dir, FOLDERS_TXT_NAME)
        existing_folders = set()
        
        if os.path.exists(txt_path):
            config = configparser.ConfigParser()
            config.optionxform = str
            try:
                with open(txt_path, 'r', encoding=FOLDERS_ENCODING) as f:
                    config.read_file(f)
                existing_folders = set(config.sections())
                print(f"ℹ️  检测到现有配置，包含 {len(existing_folders)} 个文件夹")
            except Exception as e:
                print(f"⚠️  读取现有配置失败：{str(e)}，将创建新文件")
        
        all_folders = [
            f for f in os.listdir(current_dir)
            if os.path.isdir(os.path.join(current_dir, f)) and not f.startswith('.')
        ]
        new_folders = [f for f in all_folders if f not in existing_folders]
        
        if not new_folders:
            print("ℹ️  没有检测到新文件夹，无需更新")
            return

        with open(txt_path, 'a', encoding=FOLDERS_ENCODING) as f:
            if not os.path.exists(txt_path) or os.path.getsize(txt_path) == 0:
                f.write("# 文件夹图标配置文件（存储相对路径）\n")
                f.write("# 格式：\n")
                f.write("# [文件夹名]\n")
                f.write("# LocalizedResourceName=显示名\n")
                f.write("# IconResource=EXE文件相对路径\n\n")
            elif new_folders:
                f.write("\n")
            
            total = len(new_folders)
            for i, folder in enumerate(new_folders, 1):
                print(f"\n[{i}/{total}] 处理新文件夹：{folder}")
                folder_path = os.path.join(current_dir, folder)
                exes = get_valid_exes(folder_path)
                
                if not exes:
                    print(f"   ⚠️  未找到有效EXE，跳过")
                    continue
                
                selected_abs = None
                selected_rel = None
                if len(exes) == 1:
                    abs_path, rel_path = exes[0]
                    print(f"   找到1个有效EXE（相对路径）：{rel_path}")
                    print(f"   对应绝对路径：{abs_path}")
                    selected_abs = abs_path
                    selected_rel = rel_path
                else:
                    print(f"   找到{len(exes)}个有效EXE，请选择：")
                    for j, (abs_path, rel_path) in enumerate(exes, 1):
                        print(f"   {j}. 相对路径：{rel_path}")
                        print(f"      绝对路径：{abs_path}")
                    while True:
                        try:
                            choice = input(f"   请输入序号（1-{len(exes)}，0=跳过）：").strip()
                            num = int(choice)
                            if num == 0:
                                break
                            if 1 <= num <= len(exes):
                                selected_abs, selected_rel = exes[num-1]
                                print(f"   已选择相对路径：{selected_rel}")
                                break
                            else:
                                print(f"   请输入1到{len(exes)}之间的数字")
                        except ValueError:
                            print("   请输入有效数字")
                
                if selected_rel:
                    f.write(f"[{folder}]\n")
                    f.write(f"LocalizedResourceName={folder}\n")
                    f.write(f"IconResource={selected_rel}\n\n")
                    print(f"   ✅ 已添加到配置")
        
        print(f"\n✅ 成功更新 {txt_path}（编码：{FOLDERS_ENCODING}）")
    except Exception as e:
        print(f"❌ 更新失败：{str(e)}")
    finally:
        wait_for_space()


# ------------------------------
# desktop.ini 生成与清理功能
# ------------------------------
def generate_desktop_ini():
    """生成desktop.ini"""
    try:
        print("\n" + "-" * 60)
        print("          生成 desktop.ini（直接生成方式）          ")
        print("-" * 60)
        current_dir = OPERATE_DIR
        txt_path = os.path.join(current_dir, FOLDERS_TXT_NAME)
        
        if not os.path.exists(txt_path):
            print(f"❌ 错误：未找到配置文件 {txt_path}")
            return

        config = configparser.ConfigParser(allow_no_value=True)
        config.optionxform = str  # 保持大小写
        try:
            with open(txt_path, 'r', encoding=FOLDERS_ENCODING) as f:
                config.read_file(f)
            print(f"✅ 成功读取配置（编码：{FOLDERS_ENCODING}）：{txt_path}")
        except UnicodeDecodeError:
            print(f"❌ 编码错误：请将 {FOLDERS_TXT_NAME} 保存为 {FOLDERS_ENCODING} 格式")
            return
        except Exception as e:
            print(f"❌ 读取配置失败：{str(e)}")
            return

        folder_names = config.sections()
        total = len(folder_names)
        if total == 0:
            print(f"❌ 配置文件中没有任何文件夹")
            return

        processed = 0
        for folder_name in folder_names:
            print(f"\n{'-'*40}")
            print(f"📂 正在处理文件夹：[{folder_name}]")
            
            folder_path = os.path.join(current_dir, folder_name)
            folder_abs_path = os.path.abspath(folder_path)
            print(f"   文件夹绝对路径：{folder_abs_path}")
            if not os.path.isdir(folder_abs_path):
                print(f"   ⚠️  跳过：文件夹不存在")
                continue
            
            try:
                display_name = config.get(folder_name, 'LocalizedResourceName', fallback=folder_name).strip()
                icon_rel_path = config.get(folder_name, 'IconResource', fallback='').strip()
                print(f"   显示名：{display_name}")
                print(f"   配置的相对路径：{icon_rel_path}")
            except Exception as e:
                print(f"   ⚠️  跳过：配置项错误 - {str(e)}")
                continue
            
            if not icon_rel_path or not icon_rel_path.lower().endswith('.exe'):
                print(f"   ⚠️  跳过：IconResource无效（非EXE文件）")
                continue
            
            final_icon_path = os.path.normpath(os.path.join(folder_abs_path, icon_rel_path))
            print(f"   拼接后的绝对路径：{final_icon_path}")
            
            if not os.path.exists(final_icon_path) or not os.path.isfile(final_icon_path):
                print(f"   ⚠️  跳过：EXE文件不存在或不是有效文件")
                continue
            
            ini_path = os.path.join(folder_abs_path, "desktop.ini")
            if ensure_file_writable(ini_path):
                try:
                    with open(ini_path, 'w', encoding='ANSI', newline='\r\n') as f:
                        f.write("[.ShellClassInfo]\r\n")
                        f.write(f"LocalizedResourceName={display_name}\r\n")
                        f.write(f"IconResource={final_icon_path},0\r\n")
                    
                    win32api.SetFileAttributes(
                        ini_path,
                        win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
                    )
                    print(f"   ✅ 成功生成desktop.ini")
                    processed += 1
                except Exception as e:
                    print(f"   ❌ 生成失败：{str(e)}")
        
        print(f"\n{'-'*60}")
        print(f"📊 处理结果：成功 {processed}/{total} 个文件夹")
        print(f"⚠️  提示：请等待直到手动刷新后显示别名")
    except Exception as e:
        print(f"❌ 总错误：{str(e)}")
    finally:
        wait_for_space()


def move_existing_desktop_ini():
    """移动已生成的desktop.ini以触发缓存刷新"""
    try:
        print("\n" + "-" * 60)
        print("          移动已生成的desktop.ini（触发刷新）          ")
        print("-" * 60)
        current_dir = OPERATE_DIR
        
        # 查找所有包含desktop.ini的子文件夹
        target_folders = []
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                ini_path = os.path.join(item_path, "desktop.ini")
                if os.path.exists(ini_path):
                    target_folders.append((item, item_path, ini_path))
        
        total = len(target_folders)
        if total == 0:
            print("ℹ️  未找到任何已生成的desktop.ini文件")
            return

        print(f"找到 {total} 个包含desktop.ini的文件夹，准备执行移动操作...\n")
        processed = 0
        
        # 创建临时目录用于移动操作
        temp_dir = os.path.join(current_dir, ".temp_ini_move")
        os.makedirs(temp_dir, exist_ok=True)
        
        for folder_name, folder_path, ini_path in target_folders:
            print(f"\n{'-'*40}")
            print(f"📂 处理文件夹：[{folder_name}]")
            print(f"   原文件路径：{ini_path}")
            
            try:
                # 1. 确保文件可写
                if not ensure_file_writable(ini_path):
                    print(f"   ⚠️  无法修改文件属性，跳过")
                    continue
                
                # 2. 生成临时文件名
                temp_ini_name = f"temp_{hash(folder_name)}_{int(time.time())}_desktop.ini"
                temp_ini_path = os.path.join(temp_dir, temp_ini_name)
                
                # 3. 移动到临时目录
                shutil.move(ini_path, temp_ini_path)
                print(f"   已移动到临时位置：{temp_ini_path}")
                
                # 4. 移回原位置
                shutil.move(temp_ini_path, ini_path)
                print(f"   已移回原位置：{ini_path}")
                
                # 5. 恢复文件属性（系统+隐藏）
                win32api.SetFileAttributes(
                    ini_path,
                    win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
                )
                
                # 6. 立即触发刷新
                refresh_success, cache_success = refresh_folder(folder_path)
                if refresh_success:
                    processed += 1
                    print(f"   ✅ 移动并刷新成功")
                else:
                    print(f"   ⚠️  移动成功但刷新失败")
                
                time.sleep(0.2)  # 控制节奏
                
            except Exception as e:
                print(f"   ❌ 处理失败：{str(e)}")
                # 尝试恢复文件（如果临时文件存在）
                if os.path.exists(temp_ini_path):
                    try:
                        shutil.move(temp_ini_path, ini_path)
                        print(f"   ℹ️  已恢复文件到原位置")
                    except:
                        pass
        
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        print(f"\n{'-'*60}")
        print(f"📊 处理结果：成功 {processed}/{total} 个文件")
        print(f"⚠️  提示：请手动刷新一次当前文件夹")
    except Exception as e:
        print(f"❌ 总错误：{str(e)}")
    finally:
        wait_for_space()

def clean_desktop_ini():
    """清理desktop.ini"""
    try:
        print("\n" + "-" * 40)
        print("          清理 desktop.ini          ")
        print("-" * 40)
        current_dir = OPERATE_DIR
        deleted = 0
        
        for root, _, files in os.walk(current_dir):
            for file in files:
                if file == "desktop.ini":
                    file_path = os.path.join(root, file)
                    if ensure_file_writable(file_path):
                        try:
                            os.remove(file_path)
                            deleted += 1
                            print(f"✅ 已删除：{os.path.relpath(file_path, current_dir)}")
                        except Exception as e:
                            print(f"❌ 删除失败 {file_path}：{str(e)}")
        
        print(f"\n📊 清理完成：共删除 {deleted} 个文件")
        print(f"⚠️  提示：建议执行选项9一次")
    except Exception as e:
        print(f"❌ 清理失败：{str(e)}")
    finally:
        wait_for_space()


# ------------------------------
# 手动刷新功能（核心流程）
# ------------------------------
def manual_refresh_all():
    """循环处理文件夹（含缓存生成）+ 最终系统缓存清理"""
    try:
        print("\n" + "-" * 60)
        print("          刷新所有文件夹并清理系统缓存          ")
        print("-" * 60)
        
        current_dir = OPERATE_DIR
        folders = [
            f for f in os.listdir(current_dir)
            if os.path.isdir(os.path.join(current_dir, f)) and not f.startswith('.')
        ]
        
        total = len(folders)
        if total == 0:
            print("ℹ️  没有找到可刷新的文件夹")
            return
        
        print(f"即将处理 {total} 个文件夹（含缓存生成）...\n")
        success_count = 0
        cache_fail_count = 0  # 统计缓存生成失败次数
        
        for i, folder in enumerate(folders, 1):
            folder_path = os.path.join(current_dir, folder)
            print(f"[{i}/{total}] 处理文件夹：{folder}")
            
            # 刷新文件夹并触发缓存生成（返回两个状态：整体刷新成功/缓存生成成功）
            refresh_success, cache_success = refresh_folder(folder_path)
            
            if refresh_success:
                success_count += 1
                if not cache_success:
                    cache_fail_count += 1
                    # 仅在失败次数较少时提示，避免刷屏
                    if cache_fail_count <= 5:
                        print(f"   ⚠️  缓存生成临时失败，最终清理会修复")
                    elif cache_fail_count == 6:
                        print(f"   ⚠️  更多缓存失败将不再提示，最终清理会统一处理")
                else:
                    print(f"   ✅ 刷新及缓存生成成功")
            else:
                print(f"   ⚠️  文件夹刷新失败")
            
            time.sleep(0.1)  # 控制节奏，避免系统压力
        
        print(f"\n{'-'*40}")
        print(f"📊 文件夹处理结果：成功 {success_count}/{total} 个")
        if cache_fail_count > 0:
            print(f"   ℹ️  缓存生成临时失败 {cache_fail_count} 次，将通过最终清理修复")
        
        # 最终系统级缓存清理（确保所有图标生效）
        refresh_system_icon_cache()
        
        print(f"\n{'-'*60}")
        print("✅ 所有操作已完成")
    except Exception as e:
        print(f"❌ 刷新失败：{str(e)}")
        subprocess.Popen(["explorer.exe", OPERATE_DIR])
        time.sleep(1)
        subprocess.Popen(["explorer.exe"])  # 确保系统外壳启动
    finally:
        wait_for_space()

# ------------------------------
# 主函数
# ------------------------------
def main():
    try:
        if not check_dependency():
            wait_for_space()
            return
        
        select_operate_directory()
        if not OPERATE_DIR:
            print("❌ 未选择有效目录，退出")
            return

        while True:
            print(f"\n" + "=" * 60)
            print(f"            文件夹图标工具 {VERSION}")
            print(f"            （当前目录：{OPERATE_DIR}）")
            print("=" * 60)
            print("1. 自动清理 desktop.ini")
            print("2. 交互生成 folders.txt")
            print("3. ⚠️手动修改 folders.txt")
            print("4. 批量生成 desktop.ini")
            print("5. ⚠️等待直到手动刷新后显示别名，或者用功能9")
            print("6. 批量移动一次 desktop.ini 刷新缓存")
            print("")
            print("7. 自动生成 folders.txt [自动选择可执行文件]")
            print("8. 交互更新 folders.txt [仅加入新添加文件夹]")
            print("")
            print("9. ⚠️终极大招，多种方式刷新缓存")
            print("")
            print("0. 退出")
            print("")
            print("⚠️ 建议执行顺序1>9>2>3>4>5>6")
            print("⚠️ 如需修改文件夹名（非别名）建议先删除desktop.ini")
            
            choice = input("\n请输入操作序号（0-9）：").strip()
            if choice == '1':
                clean_desktop_ini()
            elif choice == '2':
                generate_folders_txt_interactive()
            elif choice == '4':
                generate_desktop_ini()
            elif choice == '6':  # 新增选项
                move_existing_desktop_ini()
            elif choice == '7':
                generate_folders_txt_auto()
            elif choice == '8':
                update_folders_txt_interactive()
            elif choice == '9':
                manual_refresh_all()
            elif choice == '0':  # 原退出选项
                print("\n✅ 程序退出，感谢使用！")
                break
            else:
                print("❌ 请输入 1-8 之间的数字")
                wait_for_space()
    except Exception as e:
        print(f"❌ 程序出错：{str(e)}")
        wait_for_space()


# ------------------------------
# 程序入口
# ------------------------------
if __name__ == "__main__":
    if os.name != 'nt':
        print("❌ 错误：该工具仅支持 Windows 系统")
        wait_for_space()
        sys.exit(1)
    
    print(f"\n✅ 文件夹图标工具 {VERSION} ")
    print(f"\n✅ 正在检查依赖...")
    main()
