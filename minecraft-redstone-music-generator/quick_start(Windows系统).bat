@echo off
echo 快速启动Minecraft红石音乐生成器...
echo.

REM 检查Python脚本是否存在
if exist "start.py" (
    echo 使用Python启动脚本...
    python start.py
) else (
    echo 使用Windows启动脚本...
    call start_windows.bat
)

pause