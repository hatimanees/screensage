#!/bin/bash
if [ ! -d venv ]; then
    echo "Run './setup.sh' first to create the virtual environment."
    exit 1
fi
venv/bin/python assistant/main.py
