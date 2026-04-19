#!/bin/bash
set -e

echo ""
echo " ScreenSage — Setup"
echo " =================="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+ and try again."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Installing dependencies..."
venv/bin/pip install --quiet -r assistant/requirements.txt

echo ""
echo " Setup complete."
echo " Run './run.sh' to start ScreenSage."
echo " API keys will be asked for on first launch."
echo ""
