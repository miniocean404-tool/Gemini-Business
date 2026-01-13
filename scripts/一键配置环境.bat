@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Gemini Business Auto Register - Setup
echo ========================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/4] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo [OK] venv created
) else (
    echo [OK] venv exists
)

echo.
echo [3/4] Activating environment...
call venv\Scripts\activate

echo.
echo [4/4] Installing dependencies...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

echo.
echo ========================================
echo  Setup complete!
echo  Run: python auto_register_browser.py
echo ========================================
pause
