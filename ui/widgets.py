"""Reusable UI widgets for Galaxy S9+ Recovery Console."""

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QTextEdit, QPushButton, QSizePolicy, QProgressBar,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

from ui.theme import COLORS, FONTS


class StatusCard(QFrame):
    """A card widget displaying a label-value pair with status coloring."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet(f"""
            StatusCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_sm']};
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        layout.addWidget(self._title_label)

        self._value_label = QLabel("—")
        self._value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONTS['size_md']};
            font-weight: 600;
            background: transparent;
        """)
        self._value_label.setWordWrap(True)
        layout.addWidget(self._value_label)

    def set_value(self, value: str, status: str = "neutral"):
        """Set the value and apply status coloring.

        Args:
            value: Display text.
            status: 'good', 'warn', 'error', or 'neutral'.
        """
        self._value_label.setText(value)
        color_map = {
            "good": COLORS["success"],
            "warn": COLORS["warning"],
            "error": COLORS["error"],
            "neutral": COLORS["text_primary"],
            "info": COLORS["info"],
        }
        color = color_map.get(status, COLORS["text_primary"])
        self._value_label.setStyleSheet(f"""
            color: {color};
            font-size: {FONTS['size_md']};
            font-weight: 600;
            background: transparent;
        """)


class StatusBanner(QFrame):
    """A full-width status banner with icon and message."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)

        self._icon_label = QLabel("●")
        self._icon_label.setFixedWidth(20)
        layout.addWidget(self._icon_label)

        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)
        self._message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._message_label)

        self.set_status("info", "Initializing...")

    def set_status(self, level: str, message: str):
        """Update the banner.

        Args:
            level: 'good', 'warn', 'error', 'info'
            message: Status text
        """
        color_map = {
            "good": (COLORS["success"], COLORS["success_bg"]),
            "warn": (COLORS["warning"], COLORS["warning_bg"]),
            "error": (COLORS["error"], COLORS["error_bg"]),
            "info": (COLORS["info"], COLORS["info_bg"]),
        }
        fg, bg = color_map.get(level, (COLORS["info"], COLORS["info_bg"]))

        self.setStyleSheet(f"""
            StatusBanner {{
                background-color: {bg};
                border: 1px solid {fg}40;
                border-radius: 8px;
            }}
        """)
        self._icon_label.setStyleSheet(f"color: {fg}; font-size: 14px; background: transparent;")
        self._message_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONTS['size_base']};
            font-weight: 500;
            background: transparent;
        """)
        self._message_label.setText(message)

        icon_map = {"good": "✓", "warn": "⚠", "error": "✗", "info": "ℹ"}
        self._icon_label.setText(icon_map.get(level, "●"))


class DiagnosticLog(QWidget):
    """A scrolling diagnostic log widget with copy support."""

    log_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header bar
        header = QHBoxLayout()
        title = QLabel("📋 Diagnostic Log")
        title.setStyleSheet(f"""
            font-size: {FONTS['size_md']};
            font-weight: 600;
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        header.addWidget(title)
        header.addStretch()

        self._copy_btn = QPushButton("Copy Log")
        self._copy_btn.setFixedWidth(90)
        self._copy_btn.clicked.connect(self._copy_log)
        header.addWidget(self._copy_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(70)
        self._clear_btn.clicked.connect(self._clear_log)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Log text area
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(120)
        self._log_text.setMaximumHeight(200)
        self._log_text.setPlaceholderText("Diagnostic output will appear here...")
        layout.addWidget(self._log_text)

    def append(self, message: str):
        """Append a timestamped message to the log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self._log_text.append(formatted)
        # Auto-scroll to bottom
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._log_text.setTextCursor(cursor)
        self.log_updated.emit(message)

    def get_text(self) -> str:
        """Get the full log text."""
        return self._log_text.toPlainText()

    def _copy_log(self):
        """Copy log contents to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.get_text())
        self.append("Log copied to clipboard")

    def _clear_log(self):
        """Clear the log."""
        self._log_text.clear()


class SectionHeader(QLabel):
    """A styled section header label."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            font-size: {FONTS['size_lg']};
            font-weight: 700;
            color: {COLORS['text_primary']};
            padding: 8px 0 4px 0;
            background: transparent;
        """)


class InfoLabel(QLabel):
    """A styled label for informational/guide text."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            line-height: 1.5;
            padding: 4px 0;
            background: transparent;
        """)


class StepWidget(QFrame):
    """A numbered step in a guide or troubleshooting workflow."""

    def __init__(self, number: int, title: str, description: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StepWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Step number circle
        num_label = QLabel(str(number))
        num_label.setFixedSize(32, 32)
        num_label.setAlignment(Qt.AlignCenter)
        num_label.setStyleSheet(f"""
            background-color: {COLORS['accent']};
            color: white;
            font-size: {FONTS['size_md']};
            font-weight: 700;
            border-radius: 16px;
        """)
        layout.addWidget(num_label, 0, Qt.AlignTop)

        # Text content
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

        layout.addLayout(text_layout, 1)


class StorageBar(QFrame):
    """A visual storage usage bar with labels."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StorageBar {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        self._title = QLabel(title)
        self._title.setStyleSheet(f"""
            font-weight: 600;
            font-size: {FONTS['size_base']};
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        title_row.addWidget(self._title)

        self._percent_label = QLabel("")
        self._percent_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_sm']};
            background: transparent;
        """)
        title_row.addWidget(self._percent_label, 0, Qt.AlignRight)
        layout.addLayout(title_row)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        layout.addWidget(self._bar)

        # Detail row
        self._detail = QLabel("")
        self._detail.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_sm']};
            background: transparent;
        """)
        layout.addWidget(self._detail)

    def set_data(self, total: str, used: str, available: str, percent_str: str):
        """Update the storage bar with new data."""
        # Parse percent
        try:
            pct = int(percent_str.replace("%", ""))
        except (ValueError, AttributeError):
            pct = 0

        self._bar.setValue(pct)
        self._percent_label.setText(f"{pct}% used")
        self._detail.setText(f"{used} used of {total}  •  {available} available")

        # Color the bar based on usage
        if pct >= 90:
            bar_color = COLORS["error"]
        elif pct >= 70:
            bar_color = COLORS["warning"]
        else:
            bar_color = COLORS["accent"]

        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)
