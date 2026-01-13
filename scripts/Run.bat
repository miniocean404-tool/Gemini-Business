@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate
python auto_register_browser.py
pause
