"""Main Window for S9+ HDMI Viewer & Controller.

Pure Hardware Bridge & Diagnostics:
- Windows Media Foundation genuine video capture (no fake/simulated streams)
- Real USB device & interface descriptor verification via Windows PnP
- Strict decoupling: Video capture works completely independently of ADB
- Explicit, verifiable status strips:
  1. USB Device Connection (Real PnP verification)
  2. Phone USB Video Endpoint (Verifies UVC Class 0x0E presence)
  3. Physical Video Capture Source (WMF UVC devices)
  4. Real Video Stream Status (Resolution & FPS)
  5. Touch Control Status (Unavailable without ADB; explains physical mouse alternative)
  6. ADB Status (Strictly optional diagnostics, never a gatekeeper)
- Hardware chain documentation and DeX mode switching controls
"""

import sys
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QComboBox, QLabel, QFrame, QSplitter,
    QScrollArea, QInputDialog, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from core.uvc_capture import UvcCaptureManager, CaptureDeviceInfo, VideoFormatInfo
from core.usb_detector import UsbHardwareDetector, PhoneUsbInspectionResult
from core.adb_manager import AdbManager
from core.adb_controller import AdbController
from core.dex_mode_manager import DexModeManager
from ui.video_display_widget import VideoDisplayWidget
from ui.theme import COLORS, FONTS
from ui.widgets import SectionHeader, InfoLabel, StatusBanner, DiagnosticLog


class HdmiViewerWindow(QMainWindow):
    """Main window for S9+ HDMI Viewer & Controller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("S9+ HDMI Viewer & Controller")
        self.resize(1280, 850)
        self.setMinimumSize(960, 640)

        # Core engines
        self._uvc = UvcCaptureManager(self)
        self._usb_detector = UsbHardwareDetector()
        self._adb_mgr = AdbManager(self._on_log_message)
        self._adb_ctrl = AdbController(self._adb_mgr, self._on_log_message)
        self._dex_mgr = DexModeManager(self._adb_mgr)

        self._available_devices: List[CaptureDeviceInfo] = []
        self._is_adb_authorized: bool = False
        self._phone_usb_status: PhoneUsbInspectionResult = PhoneUsbInspectionResult()

        self._setup_ui()
        self._connect_signals()

        # Initial scans
        QTimer.singleShot(150, self._inspect_usb_hardware)
        QTimer.singleShot(300, self._refresh_device_list)
        QTimer.singleShot(600, self._check_adb_status_quiet)

        # Polling timer for USB hardware and ADB diagnostics (every 4s)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._poll_timer.start(4000)

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(f"background-color: {COLORS['bg_main']};")

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # ── 1. Top Header & Toolbar ────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 12px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(12)

        # Title
        title_label = QLabel("S9+ HDMI Viewer & Controller")
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONTS['size_md']};
            font-weight: 700;
        """)
        header_layout.addWidget(title_label)
        header_layout.addSpacing(16)

        # Capture Device Selector
        header_layout.addWidget(QLabel("Video Capture Source:"))
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(260)
        self._device_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        self._device_combo.currentIndexChanged.connect(self._on_device_selection_changed)
        header_layout.addWidget(self._device_combo)

        # Resolution Selector
        header_layout.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox()
        self._format_combo.setMinimumWidth(160)
        self._format_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        header_layout.addWidget(self._format_combo)

        # Connect / Disconnect Buttons
        self._connect_btn = QPushButton("▶ Connect Video")
        self._connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                font-weight: 600;
                padding: 6px 14px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_muted']};
            }}
        """)
        self._connect_btn.clicked.connect(self._start_selected_capture)
        header_layout.addWidget(self._connect_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self._stop_btn.clicked.connect(self._stop_capture)
        header_layout.addWidget(self._stop_btn)

        refresh_dev_btn = QPushButton("🔄 Rescan Hardware")
        refresh_dev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                padding: 6px 10px;
                border-radius: 6px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        refresh_dev_btn.clicked.connect(self._rescan_all_hardware)
        header_layout.addWidget(refresh_dev_btn)

        header_layout.addStretch()

        # Telemetry Badges
        self._fps_badge = QLabel("FPS: 0.0")
        self._fps_badge.setStyleSheet(f"""
            background-color: {COLORS['bg_input']};
            color: {COLORS['text_primary']};
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid {COLORS['border']};
        """)
        header_layout.addWidget(self._fps_badge)

        root_layout.addWidget(header_frame)

        # ── 2. Multi-Tier Status Strip (Completely Decoupled) ────
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        status_grid = QGridLayout(status_frame)
        status_grid.setContentsMargins(4, 2, 4, 2)
        status_grid.setHorizontalSpacing(18)
        status_grid.setVerticalSpacing(4)

        # Row 0: Hardware layer
        self._usb_status_badge = QLabel("🔌 USB PnP: Scanning...")
        self._usb_status_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: 600;")
        status_grid.addWidget(self._usb_status_badge, 0, 0)

        self._phone_video_badge = QLabel("⚡ Direct USB Video Endpoint: None (UVC Absent)")
        self._phone_video_badge.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")
        status_grid.addWidget(self._phone_video_badge, 0, 1)

        self._pc_sink_badge = QLabel("💻 PC USB Port: Host-Only (No DP Alt Mode Sink)")
        self._pc_sink_badge.setStyleSheet(f"color: {COLORS['text_secondary']};")
        status_grid.addWidget(self._pc_sink_badge, 0, 2)

        # Row 1: Stream and Control layer
        self._video_status_badge = QLabel("📹 Video Feed: Disconnected")
        self._video_status_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: 600;")
        status_grid.addWidget(self._video_status_badge, 1, 0)

        self._touch_status_badge = QLabel("🔴 Touch Control: Unavailable (No Authorized ADB)")
        self._touch_status_badge.setStyleSheet(f"color: {COLORS['error']}; font-weight: 600;")
        status_grid.addWidget(self._touch_status_badge, 1, 1)

        self._adb_diag_badge = QLabel("⚙️ ADB Diagnostics: Checking...")
        self._adb_diag_badge.setStyleSheet(f"color: {COLORS['text_muted']};")
        status_grid.addWidget(self._adb_diag_badge, 1, 2)

        root_layout.addWidget(status_frame)

        # ── 3. Main Splitter (Left: Video Display | Right: Diagnostics)
        main_splitter = QSplitter(Qt.Horizontal)

        # Video Display Container
        self._video_display = VideoDisplayWidget(self)
        self._uvc.attach_video_widget(self._video_display.uvc_video_widget)
        self._video_display.touch_tapped.connect(self._on_video_touch_tap)
        self._video_display.touch_swiped.connect(self._on_video_touch_swipe)
        main_splitter.addWidget(self._video_display)

        # Right-side Tabs
        right_panel = QTabWidget()
        right_panel.setMinimumWidth(390)

        # Tab 1: Hardware Diagnostics & Limitations
        hardware_diag_tab = self._create_hardware_diag_tab()
        right_panel.addTab(hardware_diag_tab, "🔍 USB & Signal Path")

        # Tab 2: Control & Alternative Input
        control_tab = self._create_control_tab()
        right_panel.addTab(control_tab, "🎮 Remote Control")

        # Tab 3: DeX vs Mirroring
        dex_tab = self._create_dex_tab()
        right_panel.addTab(dex_tab, "🔄 DeX vs Mirror")

        # Tab 4: Logs
        log_tab = self._create_log_tab()
        right_panel.addTab(log_tab, "📜 Diagnostics")

        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([840, 440])

        root_layout.addWidget(main_splitter, 1)

    def _create_hardware_diag_tab(self) -> QWidget:
        """Create tab with genuine USB descriptor and signal path inspection."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader("🔍 USB Descriptor & Hardware Signal Inspection"))

        self._hardware_summary_card = QFrame()
        self._hardware_summary_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        h_layout = QVBoxLayout(self._hardware_summary_card)
        self._hardware_summary_label = InfoLabel("Inspecting USB hardware...")
        h_layout.addWidget(self._hardware_summary_label)
        layout.addWidget(self._hardware_summary_card)

        # Detailed Technical Explanation
        tech_frame = QFrame()
        tech_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        tech_layout = QVBoxLayout(tech_frame)
        tech_layout.addWidget(InfoLabel(f"""
<p><b>Physical Signal Path Analysis (Standard Cable vs. Video Stream):</b></p>
<pre style="color: #00d2ff; font-family: Consolas, monospace; font-size: 11px;">
[ Galaxy S9+ SM-G965F ]
          │  (USB-C DisplayPort Alt Mode Differential PHY)
          ▼
[ USB-C Multiport Hub / Adapter ] ◄── [ Wall Fast Charger ]
          │  (Standard HDMI Video Signal)
          ▼
[ USB UVC HDMI Video Capture Card ] (e.g. Cam Link, UVC Capture Dongle)
          │  (Standard USB Video Class Webcam Stream)
          ▼
[ Windows PC USB Port ] ──► (Viewable directly in this window without ADB)
</pre>
<p><b>Why a Standard USB Cable Cannot Ingest DisplayPort Video on PC:</b></p>
<ul>
<li><b>GPU Signaling:</b> The Galaxy S9+'s GPU outputs uncompressed video via VESA DisplayPort Alternate Mode on its USB-C high-speed pins. This is native DisplayPort video, not USB protocol packets.</li>
<li><b>Host vs. Sink:</b> PC USB ports are <b>USB Hosts (xHCI)</b> designed to receive data packets (MTP/ADB). Motherboards and GPU Type-C ports do not possess DisplayPort Sink receiver circuitry.</li>
<li><b>Missing Capability:</b> Windows software cannot convert raw DisplayPort signaling into a USB stream without physical capture silicon.</li>
</ul>
        """))
        layout.addWidget(tech_frame)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_control_tab(self) -> QWidget:
        """Create tab with remote touch and navigation buttons."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader("🎮 Input Control & Alternatives"))

        self._control_banner = StatusBanner()
        self._control_banner.set_status("warn", "Touch input unavailable: ADB is unauthorized.")
        layout.addWidget(self._control_banner)

        # Physical mouse alternative notice
        alt_frame = QFrame()
        alt_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        alt_layout = QVBoxLayout(alt_frame)
        alt_layout.addWidget(QLabel("<b>Recommended No-ADB Alternative (Hardware OTG Mouse):</b>"))
        alt_layout.addWidget(InfoLabel(
            "If you plug a standard wired USB mouse into the USB-A port of your phone's USB-C hub, "
            "a native hardware mouse cursor appears directly on the phone's HDMI video output. "
            "This provides full navigation and lock screen unlock with <b>zero ADB and zero authorization</b>."
        ))
        layout.addWidget(alt_frame)

        # ADB Control Buttons Grid (Enabled ONLY if ADB is genuinely authorized)
        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        grid = QGridLayout(btn_frame)
        grid.setSpacing(8)

        def make_btn(text: str, handler):
            btn = QPushButton(text)
            btn.setEnabled(False)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_input']};
                    color: {COLORS['text_primary']};
                    padding: 8px 12px;
                    border-radius: 6px;
                    border: 1px solid {COLORS['border']};
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['border']};
                }}
                QPushButton:disabled {{
                    color: {COLORS['text_muted']};
                    border-color: transparent;
                }}
            """)
            btn.clicked.connect(handler)
            return btn

        self._btn_power = make_btn("⚡ Power", lambda: self._adb_ctrl.send_key(26))
        self._btn_unlock = make_btn("🔓 Unlock", lambda: self._adb_ctrl.send_swipe(0.5, 0.8, 0.5, 0.2, 300))
        self._btn_back = make_btn("◀ Back", lambda: self._adb_ctrl.send_key(4))
        self._btn_home = make_btn("⚪ Home", lambda: self._adb_ctrl.send_key(3))
        self._btn_recents = make_btn("▢ Recents", lambda: self._adb_ctrl.send_key(187))
        self._btn_type = make_btn("⌨ Type Text", self._prompt_type_text)

        grid.addWidget(self._btn_power, 0, 0)
        grid.addWidget(self._btn_unlock, 0, 1)
        grid.addWidget(self._btn_back, 1, 0)
        grid.addWidget(self._btn_home, 1, 1)
        grid.addWidget(self._btn_recents, 2, 0)
        grid.addWidget(self._btn_type, 2, 1)

        layout.addWidget(btn_frame)
        layout.addStretch()
        return tab

    def _create_dex_tab(self) -> QWidget:
        """Create tab explaining DeX vs Screen Mirroring mode."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader("🔄 Samsung DeX vs. Mirrored-Phone Mode"))

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        flayout = QVBoxLayout(frame)
        flayout.addWidget(InfoLabel(f"""
<p><b>Does the Galaxy S9+ Automatically Launch DeX on HDMI?</b></p>
<p>Yes. On Samsung One UI (Android 10), connecting an external display frequently defaults to <b>Samsung DeX desktop</b> instead of mirroring the phone screen.</p>
{self._dex_mgr.get_hardware_switching_guide()}
        """))

        # Safe ADB Switch Button
        switch_adb_btn = QPushButton("🔄 Request Switch to Mirroring via ADB (Safe)")
        switch_adb_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        switch_adb_btn.clicked.connect(self._request_switch_dex)
        flayout.addWidget(switch_adb_btn)

        layout.addWidget(frame)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_log_tab(self) -> QWidget:
        """Create tab for live diagnostic messages."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self._log_widget = DiagnosticLog()
        layout.addWidget(self._log_widget)
        return tab

    # ── Signal Connections ─────────────────────────────────────────

    def _connect_signals(self):
        self._uvc.devices_changed.connect(self._refresh_device_list)
        self._uvc.frame_rate_updated.connect(self._on_fps_updated)
        self._uvc.status_changed.connect(self._on_uvc_status_changed)

    def _on_log_message(self, message: str):
        if hasattr(self, "_log_widget"):
            self._log_widget.append(message)

    # ── Hardware Diagnostics & Polling ────────────────────────────

    def _on_poll_tick(self):
        """Periodic background status update."""
        self._inspect_usb_hardware()
        self._check_adb_status_quiet()

    def _inspect_usb_hardware(self):
        """Query genuine Windows PnP and driver services for connected phone."""
        self._phone_usb_status = self._usb_detector.inspect_connected_phone()

        if self._phone_usb_status.is_physically_connected:
            self._usb_status_badge.setText(f"🔌 USB PnP: Connected ({self._phone_usb_status.device_name})")
            self._usb_status_badge.setStyleSheet(f"color: {COLORS['success']}; font-weight: 600;")
        else:
            self._usb_status_badge.setText("🔌 USB PnP: No Samsung USB Device Detected")
            self._usb_status_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: 600;")

        # Direct Video Endpoint verification
        if self._phone_usb_status.has_uvc_video_interface:
            self._phone_video_badge.setText("⚡ Phone Video Endpoint: UVC Active")
            self._phone_video_badge.setStyleSheet(f"color: {COLORS['success']}; font-weight: 600;")
        else:
            self._phone_video_badge.setText("⚡ Direct USB Video Endpoint: None (UVC Absent on Phone)")
            self._phone_video_badge.setStyleSheet(f"color: {COLORS['warning']}; font-weight: 600;")

        # Update summary text
        interfaces_str = "<br>".join([f"• Interface {iface.interface_number}: {iface.name} [Service: {iface.service}]"
                                     for iface in self._phone_usb_status.interfaces])
        if not interfaces_str:
            interfaces_str = "• No interfaces enumerated."

        self._hardware_summary_label.setText(f"""
<p><b>Connected USB Hardware Status:</b></p>
<p><b>Physical Connection:</b> {'Yes (USB VID 04E8 / PID 6860 detected)' if self._phone_usb_status.is_physically_connected else 'Disconnected'}</p>
<p><b>Serial Number:</b> {self._phone_usb_status.serial_number or 'N/A'}</p>
<p><b>Enumerated USB Interfaces on Phone:</b></p>
{interfaces_str}
<p><b>Direct USB Video (UVC Class 0x0E):</b> {'Exposed' if self._phone_usb_status.has_uvc_video_interface else '<span style="color:#d29922">NOT EXPOSED</span>'}</p>
<p><b>PC USB Controller:</b> AMD/Intel xHCI Host Controller (Host-only, no DP Sink PHY)</p>
<p><b>Diagnosis:</b> {self._phone_usb_status.hardware_diagnosis}</p>
        """)

    def _rescan_all_hardware(self):
        """Manual refresh trigger."""
        self._on_log_message("Manual hardware rescan triggered.")
        self._inspect_usb_hardware()
        self._refresh_device_list()
        self._check_adb_status_quiet()

    # ── Video Capture Controls (Decoupled from ADB) ───────────────

    def _refresh_device_list(self):
        """Query genuine UVC capture devices from Windows Media Foundation."""
        self._available_devices = self._uvc.get_available_devices()
        self._device_combo.blockSignals(True)
        self._device_combo.clear()

        if not self._available_devices:
            self._device_combo.addItem("No Capture Devices Found", None)
            self._connect_btn.setEnabled(False)
        else:
            for dev in self._available_devices:
                self._device_combo.addItem(f"📹 {dev.description}", dev.device_id)
            self._connect_btn.setEnabled(not self._uvc.is_active)

        self._device_combo.blockSignals(False)
        self._on_device_selection_changed(self._device_combo.currentIndex())

    def _on_device_selection_changed(self, index: int):
        self._format_combo.clear()
        if index < 0 or index >= self._device_combo.count():
            return

        data = self._device_combo.currentData()
        if not data:
            return

        for dev in self._available_devices:
            if dev.device_id == data:
                for fmt in dev.formats:
                    self._format_combo.addItem(str(fmt), fmt)
                break

    def _start_selected_capture(self):
        """Start capturing from currently selected genuine capture device."""
        data = self._device_combo.currentData()
        if not data:
            QMessageBox.information(
                self, "No Capture Device",
                "No physical video capture device is selected.\n\n"
                "To capture the Galaxy S9+ video feed, connect its USB-C port to an external "
                "HDMI hub, then connect the HDMI output to a USB UVC HDMI capture card plugged into this PC."
            )
            return

        preferred_fmt = self._format_combo.currentData()
        self._video_display.show_live_stream()
        ok, msg = self._uvc.start_capture(data, preferred_fmt)
        self._on_log_message(msg)

        if ok:
            self._connect_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            dev_name = self._device_combo.currentText()
            self._video_status_badge.setText(f"🟢 Video Feed: Active ({dev_name})")
            self._video_status_badge.setStyleSheet(f"color: {COLORS['success']}; font-weight: 600;")
        else:
            self._video_display.show_idle_state()
            QMessageBox.warning(self, "Capture Error", f"Could not start video capture:\n{msg}")

    def _stop_capture(self):
        """Stop active video capture."""
        self._uvc.stop_capture()
        self._video_display.show_idle_state()
        self._connect_btn.setEnabled(bool(self._available_devices))
        self._stop_btn.setEnabled(False)
        self._video_status_badge.setText("📹 Video Feed: Disconnected")
        self._video_status_badge.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: 600;")
        self._fps_badge.setText("FPS: 0.0")

    def _on_fps_updated(self, fps: float):
        self._fps_badge.setText(f"FPS: {fps:.1f}")

    def _on_uvc_status_changed(self, status_type: str, message: str):
        self._on_log_message(f"[{status_type.upper()}] {message}")

    # ── ADB Diagnostics & Input Control ───────────────────────────

    def _check_adb_status_quiet(self):
        """Check ADB state as an independent diagnostic without blocking video."""
        auth_ok, reason = self._adb_ctrl.check_authorization()
        self._is_adb_authorized = auth_ok
        self._video_display.set_adb_authorized(auth_ok)

        # Update button states
        for btn in [self._btn_power, self._btn_unlock, self._btn_back, self._btn_home,
                    self._btn_recents, self._btn_type]:
            btn.setEnabled(auth_ok)

        if auth_ok:
            self._touch_status_badge.setText("🟢 Touch Control: ACTIVE (ADB Authorized)")
            self._touch_status_badge.setStyleSheet(f"color: {COLORS['success']}; font-weight: 600;")
            self._adb_diag_badge.setText("⚙️ ADB Diagnostics: Authorized")
            self._adb_diag_badge.setStyleSheet(f"color: {COLORS['success']};")
            self._control_banner.set_status("good", "ADB connection authorized. Clicking on video sends real touch events.")
        else:
            self._touch_status_badge.setText("🔴 Touch Control: Unavailable (No Authorized ADB)")
            self._touch_status_badge.setStyleSheet(f"color: {COLORS['error']}; font-weight: 600;")
            self._adb_diag_badge.setText(f"⚙️ ADB Diagnostics: {reason}")
            self._adb_diag_badge.setStyleSheet(f"color: {COLORS['text_muted']};")
            self._control_banner.set_status(
                "warn",
                f"Touch control unavailable: {reason}\n"
                "Use a standard USB mouse connected to your phone's USB-C hub to navigate without ADB."
            )

    def _on_video_touch_tap(self, norm_x: float, norm_y: float):
        if not self._is_adb_authorized:
            self._on_log_message("Touch tap ignored: ADB is not authorized.")
            return
        ok, msg = self._adb_ctrl.send_tap(norm_x, norm_y)
        self._on_log_message(msg)

    def _on_video_touch_swipe(self, n_x1: float, n_y1: float, n_x2: float, n_y2: float):
        if not self._is_adb_authorized:
            self._on_log_message("Swipe ignored: ADB is not authorized.")
            return
        ok, msg = self._adb_ctrl.send_swipe(n_x1, n_y1, n_x2, n_y2)
        self._on_log_message(msg)

    def _prompt_type_text(self):
        text, ok = QInputDialog.getText(self, "Type Text via ADB", "Enter text to send to phone:")
        if ok and text:
            self._adb_ctrl.send_text(text)

    def _request_switch_dex(self):
        ok, msg = self._dex_mgr.request_switch_to_mirroring_adb()
        self._on_log_message(msg)
        if ok:
            QMessageBox.information(self, "DeX Switch", "Sent broadcast to request screen mirroring.")
        else:
            QMessageBox.warning(self, "DeX Switch", f"Could not switch via ADB:\n{msg}\n\nUse a physical USB mouse on the hub instead.")


def run_hdmi_viewer():
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = HdmiViewerWindow()
    window.show()
    sys.exit(app.exec())
