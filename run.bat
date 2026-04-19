@echo off
if not exist venv (
    echo Run 'setup.bat' first to create the virtual environment.
    exit /b 1
)
venv\Scripts\python assistant\main.py
