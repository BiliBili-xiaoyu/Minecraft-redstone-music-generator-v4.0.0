@echo off
title Minecraft红石音乐 - 前端服务器
color 0D

echo.
echo ========================================
echo   前端服务器启动器
echo ========================================

echo 检查端口8080是否可用...
netstat -ano | findstr :8080 >nul
if not errorlevel 1 (
    echo [警告] 端口8080已被占用！
    echo 请关闭占用8080端口的程序或使用其他端口
    set /p PORT=请输入新的端口号（默认: 8081）: 
    if "%PORT%"=="" set PORT=8081
) else (
    set PORT=8080
)

echo.
echo 启动HTTP服务器在端口 %PORT%...
echo 前端地址: http://localhost:%PORT%
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

python -m http.server %PORT%