"""External display and Samsung DeX guide page for Galaxy S9+ Recovery Console.

Provides interactive status detection and instructions for:
1. Samsung DeX for Windows (USB cable connection to PC)
2. Hardware Samsung DeX (USB-C to HDMI adapter / TV)
"""

import os
import subprocess
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from ui.widgets import SectionHeader, InfoLabel, StepWidget, StatusBanner
from ui.theme import COLORS, FONTS


class DexGuidePage(QWidget):
    """External display and DeX management and troubleshooting guide."""

    def __init__(self, log_callback, parent=None):
        super().__init__(parent)
        self._log = log_callback
        self._dex_path: Optional[str] = self._find_samsung_dex()
        self._setup_ui()

    def _find_samsung_dex(self) -> Optional[str]:
        """Locate the official Samsung DeX for PC executable."""
        candidates = [
            r"C:\Program Files (x86)\Samsung\Samsung DeX\SamsungDeX.exe",
            r"C:\Program Files\Samsung\Samsung DeX\SamsungDeX.exe",
        ]
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Samsung", "Samsung DeX", "SamsungDeX.exe"))

        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    def _is_dex_running(self) -> bool:
        """Check if SamsungDeX.exe process is currently active."""
        try:
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq SamsungDeX.exe"],
                text=True, stderr=subprocess.DEVNULL, timeout=3
            )
            return "SamsungDeX.exe" in output
        except Exception:
            return False

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

        # ── Header Banner ──────────────────────────────────────
        banner = StatusBanner()
        banner.set_status(
            "info",
            "This guide assists in viewing and controlling your Galaxy S9+ through "
            "Samsung DeX (PC app or direct HDMI output) when the phone screen is black."
        )
        layout.addWidget(banner)

        # ── Section 1: Samsung DeX on PC (USB Cable) ───────────
        layout.addWidget(SectionHeader("🖥️ Samsung DeX for Windows (USB Cable)"))

        dex_pc_card = QFrame()
        dex_pc_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        dex_pc_layout = QVBoxLayout(dex_pc_card)
        dex_pc_layout.setSpacing(12)

        # Status row
        status_row = QHBoxLayout()
        self._dex_status_label = QLabel()
        self._update_dex_status_label()
        status_row.addWidget(self._dex_status_label, 1)

        # Actions
        launch_btn = QPushButton("🚀 Open Samsung DeX")
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        launch_btn.clicked.connect(self._launch_samsung_dex)
        status_row.addWidget(launch_btn)

        refresh_btn = QPushButton("🔄 Check Status")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        refresh_btn.clicked.connect(self._refresh_dex_status)
        status_row.addWidget(refresh_btn)

        dex_pc_layout.addLayout(status_row)

        # Explanatory Info on the Black Screen Catch
        dex_pc_layout.addWidget(InfoLabel(f"""
<p><b>How DeX for PC Works & The Black-Screen Catch:</b></p>
<p>Samsung DeX for Windows connects to your S9+ over a standard USB cable to display a desktop environment. However, when the phone's screen is completely black, two security safeguards can block it:</p>
<ol>
<li><b>Direct Boot Lock Screen:</b> If the phone was rebooted or powered off, Android starts in encrypted Direct Boot mode. The USB port is restricted until you enter your lock screen PIN/password.</li>
<li><b>"Start Samsung DeX" Dialog:</b> When connected via USB, the phone vibrates and asks on-screen: <em>"Start Samsung DeX on your computer? [Start now]"</em>. Because the screen is black, you cannot see or tap this button.</li>
</ol>
<p><b>How to Bypass the Catch:</b></p>
<ul>
<li><b>Solution 1 (Scrcpy / Mirror Tab):</b> Once ADB is authorized, open our <b>Mirror</b> tab and start mirroring. You will see the phone screen on your PC and can click "Start now" with your mouse.</li>
<li><b>Solution 2 (OTG Keyboard):</b> Connect a USB keyboard to the phone via USB-C OTG, press <code>Enter</code>, type your PIN, and hit <code>Enter</code> to unlock the phone before connecting to PC.</li>
<li><b>Solution 3 (Hardware HDMI DeX):</b> Direct USB-C to HDMI bypasses the PC prompt entirely (see below).</li>
</ul>
        """))
        layout.addWidget(dex_pc_card)

        # ── Section 2: Hardware DeX (USB-C to HDMI) ───────────
        layout.addWidget(SectionHeader("📺 Hardware Samsung DeX / DisplayPort (Guaranteed)"))

        hdmi_frame = QFrame()
        hdmi_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        hdmi_layout = QVBoxLayout(hdmi_frame)
        hdmi_layout.addWidget(InfoLabel(f"""
<p><b>Why Hardware HDMI DeX is the Most Reliable Recovery Method:</b></p>
<p>The Galaxy S9+ (SM-G965F) has a hardware <b>DisplayPort Alternate Mode</b> chip in its USB-C port. When you connect it to a TV or monitor via a USB-C to HDMI hub, the phone immediately transmits video <b>without requiring USB debugging, ADB, developer options, or computer authorization</b>.</p>
<p>If Samsung DeX for PC cannot connect because of the on-screen prompt, connecting to a TV/monitor allows you to see the screen instantly and navigate using a USB mouse.</p>
        """))
        layout.addWidget(hdmi_frame)

        # ── Step-by-Step Connection ────────────────────────────
        layout.addWidget(SectionHeader("📋 Step-by-Step Setup for HDMI DeX"))

        steps = [
            ("Connect hub to power (Critical)",
             "Plug your USB-C fast charger into the hub's Power Delivery (PD) port. "
             "The S9+ often will not output video through multi-port hubs without external power."),
            ("Connect HDMI cable to TV or Monitor",
             "Plug the HDMI cable from the hub into your TV/monitor and set the input source to HDMI."),
            ("Plug in a wired USB Mouse",
             "Connect a standard USB wired mouse into one of the hub's USB-A ports. "
             "You will use this as your cursor on the external screen."),
            ("Connect hub to Galaxy S9+",
             "Plug the hub's USB-C connector firmly into the S9+. "
             "The phone should vibrate or chime indicating charging and external display connection."),
            ("Unlock the phone on screen",
             "Within 5–15 seconds, the Samsung DeX desktop or phone lockscreen appears on the monitor. "
             "Click and drag with the mouse to swipe up, then click your PIN numbers to unlock."),
            ("Enable USB Debugging (Permanent Fix)",
             "Once in DeX or phone settings: go to Settings → About Phone → Software information → "
             "click 'Build number' 7 times. Then go to Settings → Developer options → enable 'USB debugging'. "
             "From now on, PC mirroring will work without needing the HDMI hub!"),
        ]

        for i, (title, desc) in enumerate(steps, 1):
            layout.addWidget(StepWidget(i, title, desc))

        # ── Hardware Checklist ─────────────────────────────────
        layout.addWidget(SectionHeader("🛒 Hardware Checklist"))

        needs_frame = QFrame()
        needs_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        needs_layout = QVBoxLayout(needs_frame)
        needs_layout.addWidget(InfoLabel("""
<ul>
<li><b>USB-C Multiport Hub with HDMI & PD:</b> Must support DisplayPort Alt Mode (e.g., Anker, UGREEN, Samsung DeX Pad/Station).</li>
<li><b>Standard HDMI Cable & Monitor/TV.</b></li>
<li><b>Wired USB Mouse:</b> Bluetooth mice will not work because pairing requires the phone screen.</li>
<li><b>Phone Charger plugged into Hub:</b> Essential for clean signal generation.</li>
</ul>
        """))
        layout.addWidget(needs_frame)

        # ── Troubleshooting ────────────────────────────────────
        layout.addWidget(SectionHeader("🔧 Common Troubleshooting"))

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
        trouble_layout.addWidget(InfoLabel("""
<p><b>PC does not recognize phone over USB cable:</b></p>
<ul>
<li><b>Battery is drained:</b> When a screen dies, the phone often remains running until the battery hits 0%. Plug into a wall charger for 20 minutes before connecting to PC.</li>
<li><b>Phone is turned off:</b> Press and hold the Power button for 8–10 seconds until you feel a vibration. Wait 45 seconds for boot.</li>
<li><b>Charge-only cable:</b> Many cheap USB cables lack data wires (D+/D-). Test with a known data cable.</li>
<li><b>Use Rear Motherboard USB Ports:</b> Front-panel PC ports frequently drop USB connection with high-power phones.</li>
</ul>

<p><b>External HDMI monitor shows 'No Signal':</b></p>
<ul>
<li>Ensure the USB-C charger is connected to the hub's PD port.</li>
<li>Clean the phone's USB-C port with a wooden toothpick; lint frequently prevents video pin contact while allowing charging.</li>
<li>Try unplugging and replugging the USB-C connector into the phone.</li>
</ul>
        """))
        layout.addWidget(trouble_frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _update_dex_status_label(self):
        """Update label indicating whether Samsung DeX is installed and running."""
        is_running = self._is_dex_running()
        if self._dex_path:
            status_text = f"Installed ({self._dex_path})"
            if is_running:
                badge = f"<span style='color: {COLORS['success']}'>● Active & Running</span>"
            else:
                badge = f"<span style='color: {COLORS['accent']}'>● Installed (Ready to Launch)</span>"
        else:
            badge = f"<span style='color: {COLORS['warning']}'>● Not Found in Standard Paths</span>"
            status_text = "Samsung DeX for Windows is not installed."

        self._dex_status_label.setText(f"""
            <div style="font-size: {FONTS['size_md']}; font-weight: 600; color: {COLORS['text_primary']};">
                Samsung DeX Status: {badge}
            </div>
            <div style="font-size: {FONTS['size_sm']}; color: {COLORS['text_secondary']}; margin-top: 2px;">
                {status_text}
            </div>
        """)

    def _refresh_dex_status(self):
        self._dex_path = self._find_samsung_dex()
        self._update_dex_status_label()
        self._log("Refreshed Samsung DeX detection status.")

    def _launch_samsung_dex(self):
        """Launch or bring Samsung DeX to foreground."""
        if not self._dex_path:
            self._dex_path = self._find_samsung_dex()

        if not self._dex_path:
            QMessageBox.warning(
                self,
                "Samsung DeX Not Found",
                "Samsung DeX for Windows was not found on this computer.\n"
                "Please install it or use the HDMI hub recovery method."
            )
            return

        try:
            subprocess.Popen([self._dex_path], shell=False)
            self._log(f"Launched Samsung DeX: {self._dex_path}")
            self._update_dex_status_label()
        except Exception as e:
            self._log(f"Failed to launch Samsung DeX: {e}")
            QMessageBox.critical(self, "Launch Error", f"Could not launch Samsung DeX:\n{e}")
