"""Connection troubleshooting page for Galaxy S9+ Recovery Console.

Provides a guided diagnostic workflow from basic cable checks
through to successful mirroring, with clear explanations at each step.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.device_info import DeviceInfo, DeviceState, BootState
from ui.widgets import (
    SectionHeader, InfoLabel, StepWidget, StatusBanner, StatusCard,
)
from ui.theme import COLORS, FONTS


class DiagnosticWorker(QThread):
    """Background worker for running diagnostic steps."""
    step_update = Signal(str, str, str)  # step_id, status, message
    finished = Signal()

    def __init__(self, adb_manager, scrcpy_manager):
        super().__init__()
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager

    def run(self):
        # Step A: ADB availability
        self.step_update.emit("adb", "running", "Checking ADB installation...")
        if self._adb.is_available:
            self.step_update.emit("adb", "pass", f"ADB found: {self._adb.adb_path}")
        else:
            found, msg = self._adb.find_adb()
            if found:
                self.step_update.emit("adb", "pass", f"ADB found: {msg}")
            else:
                self.step_update.emit("adb", "fail", "ADB not found — install Platform Tools")
                self.finished.emit()
                return

        # Step B: ADB server
        self.step_update.emit("server", "running", "Checking ADB server...")
        self._adb.start_adb_server()
        self.step_update.emit("server", "pass", "ADB server is running")

        # Step C: Device detection
        self.step_update.emit("detect", "running", "Scanning for USB devices...")
        devices = self._adb.detect_devices()
        if not devices:
            self.step_update.emit("detect", "fail",
                "No devices detected.\n"
                "• Check USB cable — try a different cable\n"
                "• Try a different USB port (preferably USB 2.0 on the back of PC)\n"
                "• Ensure Samsung USB drivers are installed\n"
                "• Check Device Manager for unknown devices\n"
                "• If the phone is in Download Mode, ADB will not detect it"
            )
            self.finished.emit()
            return

        dev = devices[0]
        serial = dev.get("serial", "")
        state = dev.get("state", "")
        self.step_update.emit("detect", "pass",
            f"Device found: {serial} (state: {state})")

        # Step D: Authorization check
        self.step_update.emit("auth", "running", "Checking authorization...")
        if state == "device":
            self.step_update.emit("auth", "pass", "Device is authorized ✓")
        elif state == "unauthorized":
            self.step_update.emit("auth", "fail",
                "Device is UNAUTHORIZED.\n"
                "The phone must display a 'Allow USB debugging?' prompt and you must tap 'Allow'.\n\n"
                "Since your screen is not usable, you need to:\n"
                "1. Connect the phone to an external display via USB-C to HDMI hub\n"
                "2. Use a USB mouse to tap 'Allow' on the authorization prompt\n"
                "3. See the External Display & DeX tab for instructions"
            )
            self.finished.emit()
            return
        elif state == "offline":
            self.step_update.emit("auth", "fail",
                "Device is OFFLINE.\n"
                "• The phone may be booting — wait 30 seconds and try again\n"
                "• Try unplugging and replugging the USB cable\n"
                "• Try restarting the ADB server"
            )
            self.finished.emit()
            return
        else:
            self.step_update.emit("auth", "warn",
                f"Device state: {state} — this is unusual. "
                "Try restarting ADB server and reconnecting.")
            self.finished.emit()
            return

        # Step E: Boot state
        self.step_update.emit("boot", "running", "Checking boot state...")
        boot = self._adb.get_boot_completed(serial)
        if boot == BootState.BOOTED:
            self.step_update.emit("boot", "pass", "Device is fully booted ✓")
        elif boot == BootState.BOOTING:
            self.step_update.emit("boot", "warn",
                "Device is still booting — wait for it to finish and re-run diagnostics")
            self.finished.emit()
            return
        else:
            self.step_update.emit("boot", "warn",
                "Cannot determine boot state — the device may not be fully started")

        # Step F: Model check
        self.step_update.emit("model", "running", "Querying device model...")
        model = self._adb.get_model(serial)
        android_ver = self._adb.get_android_version(serial)
        if model:
            self.step_update.emit("model", "pass",
                f"Model: {model}, Android: {android_ver}")
        else:
            self.step_update.emit("model", "warn", "Could not read device model")

        # Step G: scrcpy check
        self.step_update.emit("scrcpy", "running", "Checking scrcpy availability...")
        if self._scrcpy.is_available:
            self.step_update.emit("scrcpy", "pass",
                f"scrcpy found: {self._scrcpy.scrcpy_path}\n"
                "→ Go to the Mirror tab to start screen mirroring!")
        else:
            found, msg = self._scrcpy.find_scrcpy()
            if found:
                self.step_update.emit("scrcpy", "pass",
                    f"scrcpy found: {msg}\n"
                    "→ Go to the Mirror tab to start screen mirroring!")
            else:
                self.step_update.emit("scrcpy", "warn",
                    "scrcpy not found — mirroring will not work until scrcpy is installed.\n"
                    "Download from: https://github.com/Genymobile/scrcpy/releases\n"
                    "However, the device IS accessible via ADB for diagnostics.")

        self.finished.emit()


class TroubleshootPage(QWidget):
    """Connection troubleshooting and guided diagnostics page."""

    def __init__(self, adb_manager, scrcpy_manager, log_callback, parent=None):
        super().__init__(parent)
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager
        self._log = log_callback
        self._worker = None
        self._step_widgets = {}

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

        # ── Banner ─────────────────────────────────────────────
        self._banner = StatusBanner()
        self._banner.set_status("info", "Click 'Run Diagnostics' to check your device connection step by step")
        layout.addWidget(self._banner)

        # ── Run Button ─────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("🔍  Run Diagnostics")
        self._run_btn.setProperty("class", "primary")
        self._run_btn.setFixedHeight(40)
        self._run_btn.setMinimumWidth(200)
        self._run_btn.clicked.connect(self._run_diagnostics)
        btn_layout.addWidget(self._run_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ── Diagnostic Steps ──────────────────────────────────
        layout.addWidget(SectionHeader("📋 Diagnostic Steps"))

        steps = [
            ("adb", "A", "Check ADB Installation", "Verify that ADB (Android Debug Bridge) is installed and accessible"),
            ("server", "B", "Start ADB Server", "Ensure the ADB server daemon is running"),
            ("detect", "C", "Detect USB Devices", "Scan for devices connected via USB"),
            ("auth", "D", "Check Authorization", "Verify that the device has authorized this PC for debugging"),
            ("boot", "E", "Check Boot State", "Determine if the device has fully booted into Android"),
            ("model", "F", "Query Device Info", "Read device model and Android version"),
            ("scrcpy", "G", "Check Mirroring", "Verify scrcpy availability for screen mirroring"),
        ]

        for step_id, letter, title, desc in steps:
            widget = self._create_step_widget(letter, title, desc)
            self._step_widgets[step_id] = widget
            layout.addWidget(widget)

        # ── Recovery Modes ─────────────────────────────────────
        layout.addWidget(SectionHeader("🔧 Special Device Modes"))

        modes_frame = QFrame()
        modes_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        modes_layout = QVBoxLayout(modes_frame)
        modes_layout.addWidget(InfoLabel("""
<p><b>Download Mode (Odin Mode):</b></p>
<ul>
<li>Used for firmware flashing with Samsung's Odin tool.</li>
<li>ADB does <em>not</em> work in Download Mode — only Odin can communicate.</li>
<li>The phone appears in Windows Device Manager under "Modems" or as a Samsung USB CDC device.</li>
<li>To enter: Hold <b>Volume Down + Bixby</b> while plugging in USB cable.</li>
<li><b>This tool will not flash firmware or modify the device in Download Mode.</b></li>
</ul>

<p><b>Recovery Mode:</b></p>
<ul>
<li>ADB works in recovery mode with limited commands (adb sideload).</li>
<li>To enter: Hold <b>Volume Up + Bixby + Power</b> until the Samsung logo appears.</li>
<li>In recovery mode, you can perform a factory reset — but this erases all data.</li>
<li><b>This tool will never initiate a factory reset.</b></li>
</ul>

<p><b>Safe Mode:</b></p>
<ul>
<li>Boots Android with only system apps. Useful if a third-party app is causing problems.</li>
<li>To enter: Hold <b>Volume Down</b> during boot after the Samsung logo appears.</li>
<li>ADB and USB debugging work normally in Safe Mode if previously enabled.</li>
</ul>

<p><b>If ADB is unavailable and the screen is dead:</b></p>
<ul>
<li>Your best option is a <b>USB-C to HDMI adapter</b> to see the phone on an external display.</li>
<li>See the <b>External Display & DeX</b> tab for detailed instructions.</li>
</ul>
        """))
        layout.addWidget(modes_frame)

        # ── FRP Notice ─────────────────────────────────────────
        layout.addWidget(SectionHeader("🔒 Google Factory Reset Protection (FRP)"))

        frp_frame = QFrame()
        frp_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['warning_bg']};
                border: 1px solid {COLORS['warning']}40;
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        frp_layout = QVBoxLayout(frp_frame)
        frp_layout.addWidget(InfoLabel(f"""
<p style="color: {COLORS['text_primary']}"><b>About Google Factory Reset Protection (FRP):</b></p>
<p style="color: {COLORS['text_primary']}">If your device has been factory-reset and FRP is active, you will need
the original Google account credentials to set up the device again.</p>
<ul style="color: {COLORS['text_primary']}">
<li>Screen mirroring and ADB access do <em>not</em> bypass FRP.</li>
<li>This tool does <em>not</em> attempt to defeat FRP or any other Android security mechanism.</li>
<li>If you are the legitimate owner and have forgotten your Google credentials,
visit <b>accounts.google.com</b> to recover your account.</li>
<li>If FRP is active, firmware recovery will still require the Google account sign-in.</li>
</ul>
        """))
        layout.addWidget(frp_frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_step_widget(self, letter: str, title: str, description: str) -> QFrame:
        """Create a diagnostic step widget with status indicator."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Step letter
        letter_label = QLabel(letter)
        letter_label.setFixedSize(32, 32)
        letter_label.setAlignment(Qt.AlignCenter)
        letter_label.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_md']};
            font-weight: 700;
            border-radius: 16px;
            border: 1px solid {COLORS['border']};
        """)
        layout.addWidget(letter_label, 0, Qt.AlignTop)

        # Content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {FONTS['size_md']};
            font-weight: 600;
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            background: transparent;
        """)
        text_layout.addWidget(desc_label)

        # Status (initially hidden)
        status_label = QLabel("")
        status_label.setWordWrap(True)
        status_label.setVisible(False)
        status_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_sm']};
            font-family: {FONTS['mono']};
            background: transparent;
            padding: 4px 0;
        """)
        text_layout.addWidget(status_label)

        layout.addLayout(text_layout, 1)

        # Store references
        frame._letter_label = letter_label
        frame._desc_label = desc_label
        frame._status_label = status_label

        return frame

    def _update_step(self, step_id: str, status: str, message: str):
        """Update a diagnostic step's visual status."""
        if step_id not in self._step_widgets:
            return

        widget = self._step_widgets[step_id]
        status_label = widget._status_label
        letter_label = widget._letter_label

        status_label.setText(message)
        status_label.setVisible(True)

        if status == "pass":
            color = COLORS["success"]
            bg = COLORS["success_bg"]
            border = COLORS["success"]
        elif status == "fail":
            color = COLORS["error"]
            bg = COLORS["error_bg"]
            border = COLORS["error"]
        elif status == "warn":
            color = COLORS["warning"]
            bg = COLORS["warning_bg"]
            border = COLORS["warning"]
        elif status == "running":
            color = COLORS["info"]
            bg = COLORS["info_bg"]
            border = COLORS["info"]
        else:
            color = COLORS["text_secondary"]
            bg = COLORS["bg_tertiary"]
            border = COLORS["border"]

        letter_label.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            font-size: {FONTS['size_md']};
            font-weight: 700;
            border-radius: 16px;
            border: 1px solid {border};
        """)
        status_label.setStyleSheet(f"""
            color: {color};
            font-size: {FONTS['size_sm']};
            font-family: {FONTS['mono']};
            background: transparent;
            padding: 4px 0;
        """)

        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {border}60;
                border-radius: 8px;
                padding: 12px;
            }}
        """)

    def _run_diagnostics(self):
        """Start the diagnostic workflow."""
        if self._worker and self._worker.isRunning():
            return

        self._run_btn.setEnabled(False)
        self._run_btn.setText("⏳  Running...")
        self._banner.set_status("info", "Running diagnostics...")
        self._log("Starting connection diagnostics...")

        # Reset all steps
        for step_id, widget in self._step_widgets.items():
            widget._status_label.setVisible(False)
            widget._letter_label.setStyleSheet(f"""
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_secondary']};
                font-size: {FONTS['size_md']};
                font-weight: 700;
                border-radius: 16px;
                border: 1px solid {COLORS['border']};
            """)
            widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)

        self._worker = DiagnosticWorker(self._adb, self._scrcpy)
        self._worker.step_update.connect(self._update_step)
        self._worker.finished.connect(self._on_diagnostics_complete)
        self._worker.start()

    def _on_diagnostics_complete(self):
        """Handle completion of diagnostic workflow."""
        self._run_btn.setEnabled(True)
        self._run_btn.setText("🔍  Run Diagnostics")

        # Determine overall status
        has_fail = False
        has_warn = False
        all_pass = True

        for step_id, widget in self._step_widgets.items():
            text = widget._status_label.text()
            if not widget._status_label.isVisible():
                all_pass = False
                continue
            # Check by letter label color
            style = widget._letter_label.styleSheet()
            if COLORS["error"] in style:
                has_fail = True
                all_pass = False
            elif COLORS["warning"] in style:
                has_warn = True
                all_pass = False

        if has_fail:
            self._banner.set_status("error", "Diagnostics found issues — see details above")
        elif has_warn:
            self._banner.set_status("warn", "Diagnostics completed with warnings — see details above")
        elif all_pass:
            self._banner.set_status("good", "All diagnostics passed! Your device is ready for mirroring.")
        else:
            self._banner.set_status("info", "Diagnostics completed")

        self._log("Diagnostics complete")
