"""Galaxy S9+ Recovery Console — Application Entry Point.

A diagnostic, mirroring, and recovery utility for accessing a
Samsung Galaxy S9+ (SM-G965F) with an unusable built-in display.

Usage:
    python main.py

Requirements:
    - Python 3.11+
    - PySide6
    - ADB (Android SDK Platform Tools) — on PATH or in same directory
    - scrcpy — on PATH or in same directory (for screen mirroring)
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import run_app


if __name__ == "__main__":
    run_app()
