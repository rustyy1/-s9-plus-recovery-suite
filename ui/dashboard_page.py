"""Dashboard page for Galaxy S9+ Recovery Console.

Displays device connection status, ADB info, device properties,
and boot state in a card-based layout with auto-refresh.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QScrollArea, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from core.device_info import DeviceInfo, DeviceState, BootState
from ui.widgets import StatusCard, StatusBanner, SectionHeader
from ui.theme import COLORS, FONTS


class ScanWorker(QThread):
    """Background worker for device scanning."""
    finished = Signal(object)  # DeviceInfo

    def __init__(self, adb_manager, scrcpy_manager):
        super().__init__()
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager

    def run(self):
        info = self._adb.full_scan()
        info.scrcpy_available = self._scrcpy.is_available
        info.scrcpy_path = self._scrcpy.scrcpy_path or ""
        self.finished.emit(info)


class DashboardPage(QWidget):
    """Main dashboard showing device status and diagnostics."""

    # Signal emitted when device info is updated
    device_updated = Signal(object)  # DeviceInfo

    def __init__(self, adb_manager, scrcpy_manager, log_callback, parent=None):
        super().__init__(parent)
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager
        self._log = log_callback
        self._scan_worker = None
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.refresh)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # ── Status Banner ──────────────────────────────────────
        self._banner = StatusBanner()
        layout.addWidget(self._banner)

        # ── Action Bar ─────────────────────────────────────────
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self._refresh_btn = QPushButton("🔄  Refresh")
        self._refresh_btn.setProperty("class", "primary")
        self._refresh_btn.setFixedHeight(36)
        self._refresh_btn.clicked.connect(self.refresh)
        action_bar.addWidget(self._refresh_btn)

        self._adb_restart_btn = QPushButton("⟳  Restart ADB Server")
        self._adb_restart_btn.setFixedHeight(36)
        self._adb_restart_btn.clicked.connect(self._restart_adb)
        action_bar.addWidget(self._adb_restart_btn)

        self._auto_refresh_btn = QPushButton("⏱  Auto-Refresh: OFF")
        self._auto_refresh_btn.setFixedHeight(36)
        self._auto_refresh_btn.setCheckable(True)
        self._auto_refresh_btn.clicked.connect(self._toggle_auto_refresh)
        action_bar.addWidget(self._auto_refresh_btn)

        action_bar.addStretch()
        layout.addLayout(action_bar)

        # ── ADB & Tool Status ──────────────────────────────────
        layout.addWidget(SectionHeader("🔧 Tools"))
        tools_grid = QGridLayout()
        tools_grid.setSpacing(8)

        self._adb_card = StatusCard("ADB Status")
        self._adb_ver_card = StatusCard("ADB Version")
        self._scrcpy_card = StatusCard("scrcpy Status")

        tools_grid.addWidget(self._adb_card, 0, 0)
        tools_grid.addWidget(self._adb_ver_card, 0, 1)
        tools_grid.addWidget(self._scrcpy_card, 0, 2)
        layout.addLayout(tools_grid)

        # ── Connection Status ──────────────────────────────────
        layout.addWidget(SectionHeader("📱 Device Connection"))
        conn_grid = QGridLayout()
        conn_grid.setSpacing(8)

        self._state_card = StatusCard("Connection State")
        self._serial_card = StatusCard("Serial / ID")
        self._auth_card = StatusCard("Authorization")
        self._boot_card = StatusCard("Boot State")

        conn_grid.addWidget(self._state_card, 0, 0)
        conn_grid.addWidget(self._serial_card, 0, 1)
        conn_grid.addWidget(self._auth_card, 0, 2)
        conn_grid.addWidget(self._boot_card, 0, 3)
        layout.addLayout(conn_grid)

        # ── Device Identity ────────────────────────────────────
        layout.addWidget(SectionHeader("🏷️ Device Identity"))
        id_grid = QGridLayout()
        id_grid.setSpacing(8)

        self._model_card = StatusCard("Model")
        self._android_card = StatusCard("Android Version")
        self._build_card = StatusCard("Build Number")
        self._security_card = StatusCard("Security Patch")
        self._fingerprint_card = StatusCard("Build Fingerprint")
        self._manufacturer_card = StatusCard("Manufacturer")

        id_grid.addWidget(self._model_card, 0, 0)
        id_grid.addWidget(self._android_card, 0, 1)
        id_grid.addWidget(self._build_card, 0, 2)
        id_grid.addWidget(self._security_card, 1, 0)
        id_grid.addWidget(self._fingerprint_card, 1, 1, 1, 2)
        layout.addLayout(id_grid)

        # ── Display & Mirroring ────────────────────────────────
        layout.addWidget(SectionHeader("🖥️ Display & Mirroring"))
        display_grid = QGridLayout()
        display_grid.setSpacing(8)

        self._screen_card = StatusCard("Screen Resolution")
        self._density_card = StatusCard("Screen Density")
        self._mirror_card = StatusCard("Mirror Status")

        display_grid.addWidget(self._screen_card, 0, 0)
        display_grid.addWidget(self._density_card, 0, 1)
        display_grid.addWidget(self._mirror_card, 0, 2)
        layout.addLayout(display_grid)

        # ── Quick Storage ──────────────────────────────────────
        layout.addWidget(SectionHeader("💾 Storage (Quick View)"))
        storage_grid = QGridLayout()
        storage_grid.setSpacing(8)

        self._data_storage_card = StatusCard("/data Partition")
        self._sdcard_card = StatusCard("SD Card")

        storage_grid.addWidget(self._data_storage_card, 0, 0)
        storage_grid.addWidget(self._sdcard_card, 0, 1)
        layout.addLayout(storage_grid)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def refresh(self):
        """Start a background device scan."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._log("Scan already in progress...")
            return

        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⏳  Scanning...")
        self._banner.set_status("info", "Scanning for devices...")
        self._log("Starting device scan...")

        self._scan_worker = ScanWorker(self._adb, self._scrcpy)
        self._scan_worker.finished.connect(self._on_scan_complete)
        self._scan_worker.start()

    def _on_scan_complete(self, info: DeviceInfo):
        """Handle scan completion and update all cards."""
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("🔄  Refresh")

        # Banner
        if info.state == DeviceState.CONNECTED:
            self._banner.set_status("good", info.get_status_summary())
        elif info.state == DeviceState.UNAUTHORIZED:
            self._banner.set_status("warn", info.get_status_summary())
        elif info.state in (DeviceState.OFFLINE, DeviceState.BOOTLOADER, DeviceState.RECOVERY):
            self._banner.set_status("warn", info.get_status_summary())
        else:
            self._banner.set_status("error", info.get_status_summary())

        # Tools
        if self._adb.is_available:
            self._adb_card.set_value("Installed", "good")
        else:
            self._adb_card.set_value("Not Found", "error")

        self._adb_ver_card.set_value(info.adb_version or "—", "neutral")

        if info.scrcpy_available:
            self._scrcpy_card.set_value("Installed", "good")
        else:
            self._scrcpy_card.set_value("Not Found", "warn")

        # Connection
        state_status = {
            DeviceState.CONNECTED: "good",
            DeviceState.UNAUTHORIZED: "warn",
            DeviceState.OFFLINE: "warn",
            DeviceState.BOOTLOADER: "warn",
            DeviceState.RECOVERY: "warn",
            DeviceState.UNAVAILABLE: "error",
        }
        self._state_card.set_value(info.state.value, state_status.get(info.state, "neutral"))
        self._serial_card.set_value(info.serial or "—", "neutral")

        if info.is_authorized():
            self._auth_card.set_value("Authorized ✓", "good")
        elif info.state == DeviceState.UNAUTHORIZED:
            self._auth_card.set_value("NOT Authorized", "warn")
        else:
            self._auth_card.set_value("—", "neutral")

        boot_status = {
            BootState.BOOTED: "good",
            BootState.BOOTING: "warn",
        }
        self._boot_card.set_value(
            info.boot_state.value,
            boot_status.get(info.boot_state, "neutral")
        )

        # Identity
        self._model_card.set_value(info.model or "—", "neutral")
        self._android_card.set_value(
            f"{info.android_version} (SDK {info.sdk_version})" if info.android_version else "—",
            "neutral"
        )
        self._build_card.set_value(info.build_number or "—", "neutral")
        self._security_card.set_value(info.security_patch or "—", "neutral")
        self._fingerprint_card.set_value(info.build_fingerprint or "—", "neutral")

        # Display
        self._screen_card.set_value(info.screen_size or "—", "neutral")
        self._density_card.set_value(info.screen_density or "—", "neutral")
        self._mirror_card.set_value(info.get_mirror_status(), "good" if info.can_mirror and info.scrcpy_available else "warn")

        # Storage
        if info.data_storage:
            self._data_storage_card.set_value(
                f"{info.data_storage.used} / {info.data_storage.total} ({info.data_storage.use_percent})",
                "neutral"
            )
        else:
            self._data_storage_card.set_value("—", "neutral")

        if info.sdcard_mounted:
            sd_text = "Mounted ✓"
            if info.sdcard_storage:
                sd_text += f" — {info.sdcard_storage.available} available"
            self._sdcard_card.set_value(sd_text, "good")
        elif info.sdcard_mounted is False:
            self._sdcard_card.set_value("Not detected", "neutral")
        else:
            self._sdcard_card.set_value("—", "neutral")

        # Emit update
        self.device_updated.emit(info)

    def _restart_adb(self):
        """Restart the ADB server."""
        self._log("Restarting ADB server...")
        self._adb.kill_adb_server()
        self._adb.start_adb_server()
        self._log("ADB server restarted. Refreshing...")
        QTimer.singleShot(1000, self.refresh)

    def _toggle_auto_refresh(self, checked: bool):
        """Toggle auto-refresh every 5 seconds."""
        if checked:
            self._auto_refresh_timer.start(5000)
            self._auto_refresh_btn.setText("⏱  Auto-Refresh: ON")
            self._log("Auto-refresh enabled (5s interval)")
        else:
            self._auto_refresh_timer.stop()
            self._auto_refresh_btn.setText("⏱  Auto-Refresh: OFF")
            self._log("Auto-refresh disabled")
