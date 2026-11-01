"""S9+ HDMI Viewer & Controller — Application Entry Point.

View and control a Samsung Galaxy S9+ (SM-G965F) via USB UVC HDMI capture,
with aspect-ratio preservation, live FPS, and optional ADB remote control.

Usage:
    python main_hdmi_viewer.py
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.hdmi_viewer_window import HdmiViewerWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set default clean font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = HdmiViewerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
