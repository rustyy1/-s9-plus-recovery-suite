"""Storage diagnostics page for Galaxy S9+ Recovery Console.

Shows detailed partition usage, user storage, and SD card status
when an authorized ADB connection exists.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QLabel, QGridLayout,
)
from PySide6.QtCore import Qt

from core.device_info import DeviceInfo, DeviceState
from ui.widgets import (
    StatusBanner, SectionHeader, InfoLabel,
    StatusCard, StorageBar,
)
from ui.theme import COLORS, FONTS


class StoragePage(QWidget):
    """Storage diagnostics and information page."""

    def __init__(self, log_callback, parent=None):
        super().__init__(parent)
        self._log = log_callback
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
        layout.addWidget(self._banner)

        # ── Main Storage Bars ──────────────────────────────────
        layout.addWidget(SectionHeader("💾 Partition Usage"))

        self._data_bar = StorageBar("Data Partition (/data)")
        layout.addWidget(self._data_bar)

        self._sdcard_bar = StorageBar("SD Card")
        layout.addWidget(self._sdcard_bar)

        # ── Device Info ────────────────────────────────────────
        layout.addWidget(SectionHeader("🏷️ Device Identification"))

        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        info_grid = QGridLayout(info_frame)
        info_grid.setSpacing(8)

        self._info_cards = {}
        fields = [
            ("Model", 0, 0), ("Android Version", 0, 1),
            ("Build Fingerprint", 1, 0, 1, 2),
            ("Manufacturer", 2, 0), ("Brand", 2, 1),
        ]
        for item in fields:
            name = item[0]
            card = StatusCard(name)
            self._info_cards[name] = card
            if len(item) == 5:
                info_grid.addWidget(card, item[1], item[2], item[3], item[4])
            else:
                info_grid.addWidget(card, item[1], item[2])

        layout.addWidget(info_frame)

        # ── All Partitions Table ───────────────────────────────
        layout.addWidget(SectionHeader("📊 All Partitions"))

        self._partitions_frame = QFrame()
        self._partitions_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        self._partitions_layout = QVBoxLayout(self._partitions_frame)
        self._partitions_layout.setSpacing(4)

        self._no_partitions_label = QLabel("No partition data available — connect and authorize a device.")
        self._no_partitions_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            background: transparent;
            padding: 8px;
        """)
        self._partitions_layout.addWidget(self._no_partitions_label)

        layout.addWidget(self._partitions_frame)

        # ── Explanation ────────────────────────────────────────
        layout.addWidget(SectionHeader("ℹ️ Understanding Storage"))

        explain_frame = QFrame()
        explain_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        explain_layout = QVBoxLayout(explain_frame)
        explain_layout.addWidget(InfoLabel("""
<p><b>Total Physical Flash vs. Data Partition vs. User Storage:</b></p>
<ul>
<li><b>Total physical flash</b> — The raw NAND/UFS chip capacity (e.g., 64 GB or 128 GB).
Part of this is reserved for the system, boot, recovery, and cache partitions and is not
shown as user-accessible space.</li>
<li><b>/data partition</b> — The partition where Android stores user data, installed apps,
and app data. This is smaller than the total flash because the operating system,
firmware, and recovery images occupy separate partitions.</li>
<li><b>Available user storage</b> — The free space remaining within the /data partition.
This is what you see in Android Settings → Storage.</li>
</ul>
<p><b>SD Card:</b> If a microSD card is inserted, it appears as a separate mount point.
The Galaxy S9+ supports microSD cards up to 512 GB.</p>
<p><b>Note:</b> This tool does not extract any private files. Storage information is
gathered using standard <code>df -h</code> and <code>mount</code> commands, which only
report partition sizes and mount status.</p>
        """))
        layout.addWidget(explain_frame)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def update_device_info(self, info: DeviceInfo):
        """Update storage display with new device info."""
        if not info.is_authorized():
            self._banner.set_status("warn", "Storage diagnostics require an authorized ADB connection")
            return

        self._banner.set_status("good", "Storage information loaded")

        # Data partition bar
        if info.data_storage:
            self._data_bar.set_data(
                info.data_storage.total,
                info.data_storage.used,
                info.data_storage.available,
                info.data_storage.use_percent,
            )
        else:
            self._data_bar.set_data("—", "—", "—", "0%")

        # SD card bar
        if info.sdcard_mounted and info.sdcard_storage:
            self._sdcard_bar.set_data(
                info.sdcard_storage.total,
                info.sdcard_storage.used,
                info.sdcard_storage.available,
                info.sdcard_storage.use_percent,
            )
        elif info.sdcard_mounted:
            self._sdcard_bar.set_data("Mounted", "—", "—", "0%")
        else:
            self._sdcard_bar.set_data("Not Detected", "—", "—", "0%")

        # Info cards
        card_data = {
            "Model": info.model,
            "Android Version": f"{info.android_version} (SDK {info.sdk_version})" if info.android_version else "",
            "Build Fingerprint": info.build_fingerprint,
            "Manufacturer": info.manufacturer,
            "Brand": info.brand,
        }
        for name, value in card_data.items():
            if name in self._info_cards:
                self._info_cards[name].set_value(value or "—", "neutral")

        # All partitions
        self._update_partitions_table(info.storage_info_list)

    def _update_partitions_table(self, partitions):
        """Rebuild the partitions table."""
        # Clear existing
        while self._partitions_layout.count():
            child = self._partitions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not partitions:
            label = QLabel("No partition data available")
            label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
            self._partitions_layout.addWidget(label)
            return

        # Header
        header = QHBoxLayout()
        headers = ["Mount Point", "Total", "Used", "Available", "Usage"]
        widths = [250, 80, 80, 80, 60]
        for text, w in zip(headers, widths):
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: {FONTS['size_sm']};
                font-weight: 600;
                background: transparent;
            """)
            header.addWidget(lbl)
        header.addStretch()

        header_widget = QWidget()
        header_widget.setLayout(header)
        self._partitions_layout.addWidget(header_widget)

        # Rows
        for p in partitions:
            row = QHBoxLayout()
            values = [p.mount_point, p.total, p.used, p.available, p.use_percent]
            for text, w in zip(values, widths):
                lbl = QLabel(str(text))
                lbl.setFixedWidth(w)
                lbl.setStyleSheet(f"""
                    color: {COLORS['text_primary']};
                    font-family: {FONTS['mono']};
                    font-size: {FONTS['size_sm']};
                    background: transparent;
                """)
                row.addWidget(lbl)
            row.addStretch()

            row_widget = QWidget()
            row_widget.setLayout(row)
            self._partitions_layout.addWidget(row_widget)
