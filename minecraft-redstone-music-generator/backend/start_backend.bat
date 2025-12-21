@echo off
title Minecraft红石音乐 - 后端服务器
color 0B

echo.
echo ========================================
echo   后端服务器启动器
echo ========================================

REM 检查Python版本
python --version

echo.
echo 正在检查依赖...
pip install -r requirements.txt --quiet

echo.
echo 正在创建必要的目录...
if not exist "uploads" mkdir "uploads"
if not exist "projections" mkdir "projections"

echo.
echo 启动Flask服务器...
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

python server.py

if errorlevel 1 (
    echo.
    echo [错误] 服务器启动失败
    echo 请检查:
    echo 1. Python是否正确安装
    echo 2. 依赖是否完整 (requirements.txt)
    echo 3. server.py文件是否存在
    pause
)