@echo off
chcp 65001 >nul
cd /d "%~dp0\.."

set port=17890
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%port%"') do (
    powershell -Command "Write-Host '发现占用端口 %port% 的进程 PID: %%a，正在终止...' -ForegroundColor Cyan"
    taskkill /F /PID %%a >nul 2>&1
)

call .venv\Scripts\activate
python auto_register_browser.py
pause
