@echo off
echo.
echo  ScreenSage — Setup
echo  =================

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ and try again.
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

echo Installing dependencies...
venv\Scripts\pip install --quiet -r assistant\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

echo.
echo  Setup complete.
echo  Run 'run.bat' to start ScreenSage.
echo  API keys will be asked for on first launch.
echo.
