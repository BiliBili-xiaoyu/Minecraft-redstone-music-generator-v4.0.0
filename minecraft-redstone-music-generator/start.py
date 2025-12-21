#!/usr/bin/env python3
"""
Minecraft红石音乐投影生成器 - 通用启动脚本
支持Windows、macOS、Linux全平台
"""

import os
import sys
import platform
import subprocess
import venv
import webbrowser
from pathlib import Path

def print_header():
    """打印项目标题"""
    print("=" * 60)
    print("Minecraft红石音乐投影生成器 v2.5.0")
    print("=" * 60)
    print(f"系统: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print("=" * 60)

def check_python_version():
    """检查Python版本"""
    print("[1/6] 检查Python版本...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"[错误] Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("需要Python 3.11或更高版本")
        print("请访问 https://www.python.org/downloads/ 下载最新版")
        return False
    print(f"[通过] Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_project_structure():
    """检查项目结构"""
    print("[2/6] 检查项目结构...")
    
    current_dir = Path.cwd()
    backend_dir = current_dir / "backend"
    
    # 检查backend目录
    if not backend_dir.exists():
        print(f"[错误] 未找到backend目录: {backend_dir}")
        print("请确保在项目根目录运行此脚本")
        return False
    
    # 检查server.py
    server_file = backend_dir / "server.py"
    if not server_file.exists():
        print(f"[错误] 未找到server.py: {server_file}")
        return False
    
    print(f"[通过] 项目结构完整")
    return True

def setup_virtual_environment():
    """设置虚拟环境"""
    print("[3/6] 设置虚拟环境...")
    
    backend_dir = Path.cwd() / "backend"
    venv_dir = backend_dir / "venv"
    
    # 创建虚拟环境
    if not venv_dir.exists():
        print(f"[信息] 创建虚拟环境: {venv_dir}")
        try:
            venv.create(venv_dir, with_pip=True)
            print("[通过] 虚拟环境创建成功")
        except Exception as e:
            print(f"[错误] 虚拟环境创建失败: {e}")
            return False
    else:
        print(f"[信息] 使用现有虚拟环境")
    
    return True

def install_dependencies():
    """安装依赖"""
    print("[4/6] 安装依赖包...")
    
    backend_dir = Path.cwd() / "backend"
    venv_dir = backend_dir / "venv"
    
    # 根据系统确定激活脚本
    if platform.system() == "Windows":
        pip_path = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"
    
    if not pip_path.exists():
        print(f"[警告] 未找到pip，跳过依赖安装")
        return True
    
    # 检查requirements.txt
    requirements_file = backend_dir / "requirements.txt"
    
    try:
        if requirements_file.exists():
            print(f"[信息] 从requirements.txt安装依赖")
            subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], 
                          check=True, capture_output=True, text=True)
        else:
            print(f"[信息] 安装核心依赖")
            core_packages = [
                "numpy==1.26.4",
                "librosa==0.10.1", 
                "soundfile==0.12.1",
                "scipy==1.11.4",
                "flask==3.0.0",
                "flask-cors==4.0.0"
            ]
            subprocess.run([str(pip_path), "install"] + core_packages,
                          check=True, capture_output=True, text=True)
        
        print("[通过] 依赖安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[错误] 依赖安装失败: {e}")
        print(f"输出: {e.stdout}")
        print(f"错误: {e.stderr}")
        return False

def check_ports():
    """检查端口占用"""
    print("[5/6] 检查端口...")
    
    ports = [5000, 8080]
    for port in ports:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"[警告] 端口 {port} 已被占用")
                # 尝试终止占用进程
                try:
                    if platform.system() == "Windows":
                        subprocess.run(f"netstat -ano | findstr :{port}", shell=True)
                    else:
                        subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", 
                                      shell=True, stderr=subprocess.DEVNULL)
                    print(f"[信息] 已尝试释放端口 {port}")
                except:
                    pass
            else:
                print(f"[通过] 端口 {port} 可用")
                
        except Exception as e:
            print(f"[信息] 端口检查跳过: {e}")
    
    return True

def start_servers():
    """启动服务器"""
    print("[6/6] 启动服务器...")
    
    print("\n" + "=" * 60)
    print("服务器启动配置：")
    print("=" * 60)
    print("后端服务器: http://localhost:5000")
    print("前端界面: http://localhost:8080")
    print("健康检查: http://localhost:5000/api/health")
    print("调试信息: http://localhost:5000/api/debug_info")
    print("=" * 60)
    print("\n按 Ctrl+C 停止所有服务器")
    print("=" * 60 + "\n")
    
    backend_dir = Path.cwd() / "backend"
    
    # 根据系统确定Python路径
    if platform.system() == "Windows":
        python_path = backend_dir / "venv" / "Scripts" / "python.exe"
    else:
        python_path = backend_dir / "venv" / "bin" / "python"
    
    # 如果虚拟环境的Python不存在，使用系统Python
    if not python_path.exists():
        python_path = Path(sys.executable)
    
    server_script = backend_dir / "server.py"
    
    # 启动后端服务器
    print(f"[信息] 启动后端服务器...")
    print(f"命令: {python_path} {server_script}")
    
    try:
        # 在单独的进程中启动服务器
        process = subprocess.Popen(
            [str(python_path), str(server_script)],
            cwd=str(backend_dir),
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        
        # 等待几秒让服务器启动
        import time
        time.sleep(3)
        
        # 尝试打开浏览器
        try:
            print("[信息] 尝试打开浏览器...")
            webbrowser.open("http://localhost:8080", new=2)
            webbrowser.open("http://localhost:5000/api/health", new=0)
        except:
            print("[信息] 请手动打开: http://localhost:8080")
        
        print("\n[信息] 服务器正在运行...")
        print("[信息] 请保持此窗口开启")
        
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n[信息] 正在停止服务器...")
        if 'process' in locals():
            process.terminate()
        print("[信息] 服务器已停止")
    except Exception as e:
        print(f"[错误] 服务器启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print_header()
    
    # 检查步骤
    checks = [
        check_python_version,
        check_project_structure,
        setup_virtual_environment,
        install_dependencies,
        check_ports
    ]
    
    for i, check_func in enumerate(checks, 1):
        if not check_func():
            print(f"\n[错误] 检查步骤 {i} 失败，请解决问题后重试")
            if platform.system() == "Windows":
                input("按Enter键退出...")
            sys.exit(1)
    
    # 启动服务器
    start_servers()
    
    if platform.system() == "Windows":
        input("\n按Enter键退出...")

if __name__ == "__main__":
    main()