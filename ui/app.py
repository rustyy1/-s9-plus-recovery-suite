"""Main application window for Galaxy S9+ Recovery Console.

Assembles all pages into a tabbed interface with a persistent
diagnostic log panel at the bottom.
"""

import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QSplitter, QApplication,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon

from core.adb_manager import AdbManager
from core.scrcpy_manager import ScrcpyManager
from ui.theme import get_stylesheet, COLORS, FONTS
from ui.widgets import DiagnosticLog
from ui.dashboard_page import DashboardPage
from ui.mirror_page import MirrorPage
from ui.storage_page import StoragePage
from ui.dex_guide_page import DexGuidePage
from ui.troubleshoot_page import TroubleshootPage


class MainWindow(QMainWindow):
    """Main application window with tabbed pages and log panel."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Galaxy S9+ Recovery Console")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Apply theme
        self.setStyleSheet(get_stylesheet())

        # Initialize managers
        self._log_widget = DiagnosticLog()
        self._adb = AdbManager(log_callback=self._log_widget.append)
        self._scrcpy = ScrcpyManager(log_callback=self._log_widget.append)

        self._setup_ui()
        self._initialize()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Title Bar ──────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)

        # App icon and title
        app_title = QLabel("📱  Galaxy S9+ Recovery Console")
        app_title.setStyleSheet(f"""
            font-size: {FONTS['size_xl']};
            font-weight: 700;
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        title_layout.addWidget(app_title)
        title_layout.addStretch()

        # Version label
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(f"""
            color: {COLORS['text_tertiary']};
            font-size: {FONTS['size_sm']};
            background: transparent;
        """)
        title_layout.addWidget(version_label)

        main_layout.addWidget(title_bar)

        # ── Splitter (pages + log) ─────────────────────────────
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {COLORS['border']};
                height: 2px;
            }}
        """)

        # ── Tab Widget ─────────────────────────────────────────
        self._tabs = QTabWidget()

        # Dashboard
        self._dashboard = DashboardPage(
            self._adb, self._scrcpy, self._log_widget.append
        )
        self._tabs.addTab(self._dashboard, "📊  Dashboard")

        # Mirror
        self._mirror = MirrorPage(
            self._adb, self._scrcpy, self._log_widget.append
        )
        self._tabs.addTab(self._mirror, "🖥️  Mirror")

        # Storage
        self._storage = StoragePage(self._log_widget.append)
        self._tabs.addTab(self._storage, "💾  Storage")

        # DeX Guide
        self._dex_guide = DexGuidePage(self._log_widget.append)
        self._tabs.addTab(self._dex_guide, "🔌  External Display & DeX")

        # Troubleshooting
        self._troubleshoot = TroubleshootPage(
            self._adb, self._scrcpy, self._log_widget.append
        )
        self._tabs.addTab(self._troubleshoot, "🔧  Troubleshooting")

        splitter.addWidget(self._tabs)

        # ── Log Panel ──────────────────────────────────────────
        log_container = QWidget()
        log_container.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            border-top: 1px solid {COLORS['border']};
        """)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(12, 8, 12, 8)
        log_layout.addWidget(self._log_widget)

        splitter.addWidget(log_container)
        splitter.setSizes([600, 200])

        main_layout.addWidget(splitter)

        # ── Connect signals ────────────────────────────────────
        self._dashboard.device_updated.connect(self._on_device_updated)

    def _initialize(self):
        """Perform initial setup on application launch."""
        self._log_widget.append("Galaxy S9+ Recovery Console starting...")
        self._log_widget.append("—" * 50)

        # Find tools (delay to let UI render first)
        QTimer.singleShot(500, self._find_tools)

    def _find_tools(self):
        """Locate ADB and scrcpy on the system."""
        self._log_widget.append("Searching for ADB...")
        self._adb.find_adb()

        self._log_widget.append("Searching for scrcpy...")
        self._scrcpy.find_scrcpy()

        self._log_widget.append("—" * 50)
        self._log_widget.append("Ready. Click 'Refresh' on the Dashboard to scan for devices.")

        # Auto-refresh dashboard
        QTimer.singleShot(1000, self._dashboard.refresh)

    def _on_device_updated(self, info):
        """Propagate device info updates to all pages."""
        self._mirror.update_device_info(info)
        self._storage.update_device_info(info)


def run_app():
    """Entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
