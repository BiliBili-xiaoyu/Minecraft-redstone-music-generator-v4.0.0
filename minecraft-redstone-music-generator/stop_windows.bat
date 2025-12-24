@echo off
echo 正在停止Minecraft红石音乐生成器服务...
echo.

REM 查找并停止Python的http.server进程（前端）
for /f "tokens=2" %%i in ('netstat -ano ^| findstr :8080') do (
    for /f "tokens=5" %%j in ('netstat -ano ^| findstr :8080 ^| findstr %%i') do (
        taskkill /PID %%j /F >nul 2>&1
        echo [已停止] 前端服务器 (端口8080)
    )
)

REM 查找并停止Python的Flask服务器进程（后端）
for /f "tokens=2" %%i in ('netstat -ano ^| findstr :5000') do (
    for /f "tokens=5" %%j in ('netstat -ano ^| findstr :5000 ^| findstr %%i') do (
        taskkill /PID %%j /F >nul 2>&1
        echo [已停止] 后端服务器 (端口5000)
    )
)

echo.
echo 服务已停止完成！
timeout /t 3 >nul