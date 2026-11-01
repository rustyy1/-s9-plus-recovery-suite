"""Screen mirroring page for Galaxy S9+ Recovery Console.

Provides controls for launching and monitoring scrcpy sessions.
Shows clear status about why mirroring may not be available.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, QTimer

from core.device_info import DeviceInfo, DeviceState, BootState
from ui.widgets import StatusBanner, SectionHeader, InfoLabel, StatusCard
from ui.theme import COLORS, FONTS


class MirrorPage(QWidget):
    """Screen mirroring control page."""

    def __init__(self, adb_manager, scrcpy_manager, log_callback, parent=None):
        super().__init__(parent)
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager
        self._log = log_callback
        self._device_info = None
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_scrcpy_status)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

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

        # ── Requirements ───────────────────────────────────────
        layout.addWidget(SectionHeader("📋 Requirements"))

        req_frame = QFrame()
        req_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        req_layout = QVBoxLayout(req_frame)
        req_layout.setSpacing(8)

        self._req_adb = QLabel("○ ADB: Checking...")
        self._req_scrcpy = QLabel("○ scrcpy: Checking...")
        self._req_device = QLabel("○ Device: Checking...")
        self._req_auth = QLabel("○ Authorization: Checking...")
        self._req_boot = QLabel("○ Boot State: Checking...")

        for lbl in [self._req_adb, self._req_scrcpy, self._req_device, self._req_auth, self._req_boot]:
            lbl.setStyleSheet(f"background: transparent; font-size: {FONTS['size_base']};")
            req_layout.addWidget(lbl)

        layout.addWidget(req_frame)

        # ── Mirror Controls ────────────────────────────────────
        layout.addWidget(SectionHeader("🖥️ Mirror Controls"))

        controls_frame = QFrame()
        controls_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(12)

        # Options
        opts = QHBoxLayout()
        self._stay_awake_cb = QCheckBox("Keep device awake")
        self._stay_awake_cb.setChecked(True)
        opts.addWidget(self._stay_awake_cb)

        self._screen_off_cb = QCheckBox("Turn device screen off")
        self._screen_off_cb.setChecked(False)
        opts.addWidget(self._screen_off_cb)
        opts.addStretch()
        controls_layout.addLayout(opts)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._start_btn = QPushButton("▶  Start Mirroring")
        self._start_btn.setProperty("class", "success")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setMinimumWidth(200)
        self._start_btn.clicked.connect(self._start_mirror)
        self._start_btn.setEnabled(False)
        btn_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■  Stop Mirroring")
        self._stop_btn.setProperty("class", "danger")
        self._stop_btn.setFixedHeight(44)
        self._stop_btn.setMinimumWidth(200)
        self._stop_btn.clicked.connect(self._stop_mirror)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)

        btn_layout.addStretch()
        controls_layout.addLayout(btn_layout)

        # Status
        self._mirror_status = QLabel("Mirroring is not active")
        self._mirror_status.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            padding: 8px 0;
        """)
        controls_layout.addWidget(self._mirror_status)

        layout.addWidget(controls_frame)

        # ── Troubleshooting ────────────────────────────────────
        layout.addWidget(SectionHeader("🔍 If Mirroring Is Unavailable"))

        trouble_frame = QFrame()
        trouble_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        trouble_layout = QVBoxLayout(trouble_frame)

        trouble_text = InfoLabel("""
<p><b>scrcpy requires USB debugging to be enabled AND authorized on the device.</b></p>
<p>If USB debugging is not enabled and your screen is not usable, you cannot enable it
through software alone. However, the Galaxy S9+ supports <b>USB-C video output</b>:</p>
<ol>
<li>Connect a <b>USB-C to HDMI multiport hub</b> (with power delivery) to the phone.</li>
<li>Connect an <b>HDMI cable</b> to an external monitor or TV.</li>
<li>Connect a <b>USB mouse and keyboard</b> to the hub.</li>
<li>Your phone's screen will appear on the external display.</li>
<li>Use the mouse to <b>unlock the phone</b> (enter PIN/password).</li>
<li>Navigate to <b>Settings → Developer Options</b> and enable USB Debugging.</li>
<li>Reconnect the phone directly to your PC via USB.</li>
<li>Accept the RSA key prompt on the external display.</li>
<li>You can now use scrcpy to mirror the screen.</li>
</ol>
<p><b>Important:</b> A Windows application cannot create a video signal over a standard USB data cable.
USB-C to HDMI requires DisplayPort Alternate Mode, which is a separate hardware function.</p>
<p>See the <b>External Display & DeX</b> tab for detailed instructions and recommended hardware.</p>
        """)
        trouble_layout.addWidget(trouble_text)
        layout.addWidget(trouble_frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def update_device_info(self, info: DeviceInfo):
        """Update requirements status and button states based on device info."""
        self._device_info = info

        # Check requirements
        adb_ok = self._adb.is_available
        scrcpy_ok = info.scrcpy_available
        device_ok = info.is_any_connection()
        auth_ok = info.is_authorized()
        boot_ok = info.boot_state == BootState.BOOTED
        all_ok = adb_ok and scrcpy_ok and device_ok and auth_ok and boot_ok

        def set_req(label, ok, text):
            icon = "✓" if ok else "✗"
            color = COLORS["success"] if ok else COLORS["error"]
            label.setText(f"{icon} {text}")
            label.setStyleSheet(f"background: transparent; color: {color}; font-size: {FONTS['size_base']};")

        set_req(self._req_adb, adb_ok, f"ADB: {'Installed' if adb_ok else 'Not Found'}")
        set_req(self._req_scrcpy, scrcpy_ok, f"scrcpy: {'Installed' if scrcpy_ok else 'Not Found'}")
        set_req(self._req_device, device_ok, f"Device: {info.state.value}")
        set_req(self._req_auth, auth_ok, f"Authorization: {'Authorized' if auth_ok else 'Not Authorized'}")
        set_req(self._req_boot, boot_ok, f"Boot State: {info.boot_state.value}")

        # Update banner
        if all_ok:
            self._banner.set_status("good", "All requirements met — ready to mirror")
        elif not adb_ok:
            self._banner.set_status("error", "ADB is not installed or not found on PATH")
        elif not scrcpy_ok:
            self._banner.set_status("error", "scrcpy is not installed or not found on PATH")
        elif not device_ok:
            self._banner.set_status("error", "No device detected — check USB connection")
        elif not auth_ok:
            self._banner.set_status("warn", "Device detected but not authorized — see troubleshooting below")
        elif not boot_ok:
            self._banner.set_status("warn", "Device is not fully booted — wait for boot to complete")

        # Enable/disable buttons
        is_running = self._scrcpy.is_running
        self._start_btn.setEnabled(all_ok and not is_running)
        self._stop_btn.setEnabled(is_running)

        if is_running:
            self._mirror_status.setText("🟢 Mirroring is active")
            self._mirror_status.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['success']};
                font-size: {FONTS['size_base']};
                font-weight: 600;
                padding: 8px 0;
            """)

    def _start_mirror(self):
        """Launch scrcpy."""
        if not self._device_info:
            self._log("No device info available — run a scan first")
            return

        serial = self._device_info.serial or None
        stay_awake = self._stay_awake_cb.isChecked()
        screen_off = self._screen_off_cb.isChecked()

        self._log("Starting scrcpy mirror session...")
        success, msg = self._scrcpy.start_mirror(
            serial=serial,
            stay_awake=stay_awake,
            turn_screen_off=screen_off,
        )

        if success:
            self._log(f"Mirror started: {msg}")
            self._mirror_status.setText("🟢 Mirroring is active")
            self._mirror_status.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['success']};
                font-size: {FONTS['size_base']};
                font-weight: 600;
                padding: 8px 0;
            """)
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._status_timer.start(2000)
        else:
            self._log(f"Mirror failed: {msg}")
            self._mirror_status.setText(f"✗ {msg}")
            self._mirror_status.setStyleSheet(f"""
                background: transparent;
                color: {COLORS['error']};
                font-size: {FONTS['size_base']};
                padding: 8px 0;
            """)
            self._banner.set_status("error", f"Mirroring failed: {msg}")

    def _stop_mirror(self):
        """Stop scrcpy."""
        self._log("Stopping scrcpy mirror session...")
        success, msg = self._scrcpy.stop_mirror()
        self._log(msg)
        self._status_timer.stop()
        self._mirror_status.setText("Mirroring stopped")
        self._mirror_status.setStyleSheet(f"""
            background: transparent;
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            padding: 8px 0;
        """)
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def _check_scrcpy_status(self):
        """Periodically check if scrcpy is still running."""
        if not self._scrcpy.is_running:
            exit_info = self._scrcpy.get_exit_info()
            if exit_info:
                self._log(f"scrcpy exited: {exit_info}")
                self._mirror_status.setText(f"Mirroring ended: {exit_info}")
                self._mirror_status.setStyleSheet(f"""
                    background: transparent;
                    color: {COLORS['warning']};
                    font-size: {FONTS['size_base']};
                    padding: 8px 0;
                """)
            self._status_timer.stop()
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
