#!/bin/bash
# 快速启动脚本 - Unix系统

echo "快速启动Minecraft红石音乐生成器..."
echo

# 检测系统类型
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到macOS系统"
    chmod +x start_macos.sh
    ./start_macos.sh
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到Linux系统"
    chmod +x start_linux.sh
    ./start_linux.sh
else
    echo "未知系统，尝试使用Python启动脚本"
    python3 start.py
fi