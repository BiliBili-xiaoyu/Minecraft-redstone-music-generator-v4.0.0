@echo off
title Minecraft红石音乐生成器 - 启动器
color 0A
echo.
echo ========================================
echo   Minecraft红石音乐投影生成器 v2.0
echo ========================================
echo 正在启动前后端服务...
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python或未添加到PATH环境变量
    echo 请确保已安装Python 3.8+并配置好环境变量
    pause
    exit /b 1
)

REM 切换到脚本所在目录（项目根目录）
cd /d "%~dp0"

echo [1/3] 检查项目结构...
if not exist "backend\server.py" (
    echo [错误] 未找到backend/server.py文件
    pause
    exit /b 1
)

if not exist "frontend\index.html" (
    echo [警告] 未找到frontend/index.html，前端可能无法正常访问
)

echo [2/3] 创建必要的目录...
if not exist "backend\uploads" mkdir "backend\uploads"
if not exist "backend\projections" mkdir "backend\projections"
if not exist "frontend\logs" mkdir "frontend\logs" 2>nul

echo [3/3] 启动服务...
echo.

REM 启动后端服务器（新窗口）
start "Minecraft红石音乐 - 后端服务器" cmd /k "cd /d "%~dp0backend" && echo [后端] 正在启动Flask服务器... && python server.py"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端服务器（新窗口）
start "Minecraft红石音乐 - 前端服务器" cmd /k "cd /d "%~dp0frontend" && echo [前端] 正在启动HTTP服务器... && python -m http.server 8080"

echo.
echo ========================================
echo   服务启动完成！
echo ========================================
echo 后端API: http://localhost:5000
echo 前端界面: http://localhost:8080
echo 健康检查: http://localhost:5000/api/health
echo 请前往:http://localhost:8080或手动打开:“frontend/index.html”文件
echo.
echo 按任意键打开前端界面...
pause >nul

REM 自动打开浏览器
start http://localhost:8080

echo.
echo [提示] 要停止所有服务，请关闭打开的两个命令行窗口
echo 按任意键退出启动器...
pause >nul