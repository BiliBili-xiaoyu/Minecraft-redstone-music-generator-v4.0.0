#!/bin/bash

echo "============================================"
echo "Minecraft红石音乐投影生成器 - macOS启动脚本"
echo "============================================"
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.11或更高版本"
    echo "可以使用Homebrew安装: brew install python@3.11"
    exit 1
fi

echo "[1/4] 检查Python版本..."
python3 --version

echo "[2/4] 检查项目结构..."
if [ ! -d "backend" ]; then
    echo "[错误] 未找到backend目录"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "[警告] 未找到frontend目录，将使用backend作为工作目录"
    cd backend
else
    echo "[信息] 项目结构完整"
fi

# 进入backend目录
cd backend

echo "[3/4] 检查依赖安装..."
if [ ! -d "venv" ]; then
    echo "[信息] 创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败"
        exit 1
    fi
fi

echo "[信息] 激活虚拟环境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[警告] 虚拟环境激活失败，尝试直接运行"
fi

echo "[信息] 安装依赖包..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "[信息] 安装核心依赖..."
    pip install numpy librosa soundfile scipy flask flask-cors
fi

echo "[4/4] 启动服务器..."
echo
echo "============================================"
echo "服务器启动信息："
echo "后端地址：http://localhost:5000"
echo "前端地址：http://localhost:8080" 
echo "健康检查：http://localhost:5000/api/health"
echo "按 Ctrl+C 停止服务器"
echo "============================================"
echo

# 启动Flask服务器
python3 server.py