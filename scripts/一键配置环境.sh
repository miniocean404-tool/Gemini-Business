#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo " Gemini Business Auto Register - Setup"
echo "========================================"
echo

echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python not found. Please install Python 3.10+"
    exit 1
fi
python3 --version

echo
echo "[2/4] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] venv created"
else
    echo "[OK] venv exists"
fi

echo
echo "[3/4] Activating environment..."
source venv/bin/activate

echo
echo "[4/4] Installing dependencies..."
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

echo
echo "========================================"
echo " Setup complete!"
echo " Run: python auto_register_browser.py"
echo "========================================"
