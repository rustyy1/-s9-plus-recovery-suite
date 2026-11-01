"""Dark theme and styling for Galaxy S9+ Recovery Console.

Defines the complete visual design system including colors, fonts,
and the Qt stylesheet for the application.
"""

# ── Color Palette ──────────────────────────────────────────────────
# Inspired by Samsung One UI dark mode with accent highlights

COLORS = {
    # Base
    "bg_primary": "#0D1117",       # Deep navy-black
    "bg_main": "#0D1117",          # Main window background
    "bg_dark": "#0B0E14",          # Dark canvas background
    "bg_secondary": "#161B22",     # Slightly lighter panel
    "bg_tertiary": "#1C2333",      # Card / elevated surface
    "bg_card": "#1A2332",          # Card background
    "bg_hover": "#222D3D",         # Hover state
    "bg_input": "#0D1117",         # Input field background

    # Borders
    "border": "#30363D",           # Subtle border
    "border_light": "#3D444D",     # Lighter border for focus
    "border_accent": "#1F6FEB",    # Accent border

    # Text
    "text_primary": "#E6EDF3",     # Primary text
    "text_secondary": "#8B949E",   # Secondary / muted text
    "text_muted": "#8B949E",       # Muted text alias
    "text_tertiary": "#6E7681",    # Tertiary / hint text
    "text_link": "#58A6FF",        # Links

    # Status colors
    "success": "#3FB950",          # Green — connected, success
    "success_bg": "#0D2818",       # Success background tint
    "warning": "#D29922",          # Amber — unauthorized, caution
    "warning_bg": "#2D1F06",       # Warning background tint
    "error": "#F85149",            # Red — error, disconnected
    "error_bg": "#2D0B0E",         # Error background tint
    "info": "#58A6FF",             # Blue — informational
    "info_bg": "#0C2D6B",          # Info background tint

    # Accent
    "accent": "#1F6FEB",           # Samsung blue
    "accent_hover": "#388BFD",     # Lighter accent hover
    "accent_pressed": "#1158C7",   # Darker accent pressed

    # Special
    "samsung_blue": "#1428A0",     # Samsung brand blue
    "galaxy_purple": "#6E40C9",    # Galaxy purple accent
    "mirror_green": "#3FB950",     # Mirror active indicator
}

# ── Font Configuration ─────────────────────────────────────────────

FONTS = {
    "family": "Segoe UI, Inter, -apple-system, sans-serif",
    "mono": "Cascadia Code, Consolas, Courier New, monospace",
    "size_xs": "11px",
    "size_sm": "12px",
    "size_base": "13px",
    "size_md": "14px",
    "size_lg": "16px",
    "size_xl": "20px",
    "size_2xl": "24px",
    "size_3xl": "28px",
}


def get_stylesheet() -> str:
    """Generate the complete application stylesheet."""
    c = COLORS
    f = FONTS

    return f"""
    /* ── Global ──────────────────────────────────────────────── */
    QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: {f['family']};
        font-size: {f['size_base']};
    }}

    /* ── Main Window ─────────────────────────────────────────── */
    QMainWindow {{
        background-color: {c['bg_primary']};
    }}

    /* ── Scroll Areas ────────────────────────────────────────── */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: {c['bg_secondary']};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['border_light']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {c['bg_secondary']};
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        min-width: 30px;
        border-radius: 4px;
    }}

    /* ── Labels ──────────────────────────────────────────────── */
    QLabel {{
        background-color: transparent;
        color: {c['text_primary']};
        padding: 0;
    }}
    QLabel[class="heading"] {{
        font-size: {f['size_xl']};
        font-weight: bold;
        color: {c['text_primary']};
    }}
    QLabel[class="subheading"] {{
        font-size: {f['size_lg']};
        font-weight: 600;
        color: {c['text_primary']};
    }}
    QLabel[class="muted"] {{
        color: {c['text_secondary']};
        font-size: {f['size_sm']};
    }}
    QLabel[class="status-good"] {{
        color: {c['success']};
        font-weight: 600;
    }}
    QLabel[class="status-warn"] {{
        color: {c['warning']};
        font-weight: 600;
    }}
    QLabel[class="status-error"] {{
        color: {c['error']};
        font-weight: 600;
    }}

    /* ── Buttons ─────────────────────────────────────────────── */
    QPushButton {{
        background-color: {c['bg_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-size: {f['size_base']};
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['border_light']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_secondary']};
    }}
    QPushButton:disabled {{
        color: {c['text_tertiary']};
        background-color: {c['bg_secondary']};
        border-color: {c['border']};
    }}
    QPushButton[class="primary"] {{
        background-color: {c['accent']};
        color: white;
        border: 1px solid {c['accent']};
        font-weight: 600;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: {c['accent_hover']};
        border-color: {c['accent_hover']};
    }}
    QPushButton[class="primary"]:pressed {{
        background-color: {c['accent_pressed']};
    }}
    QPushButton[class="success"] {{
        background-color: {c['success']};
        color: white;
        border: 1px solid {c['success']};
        font-weight: 600;
    }}
    QPushButton[class="danger"] {{
        background-color: {c['error']};
        color: white;
        border: 1px solid {c['error']};
        font-weight: 600;
    }}

    /* ── Group Boxes (Cards) ─────────────────────────────────── */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 28px;
        font-weight: 600;
        font-size: {f['size_md']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: {c['text_primary']};
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        left: 12px;
    }}

    /* ── Text Edit / Log ─────────────────────────────────────── */
    QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        font-family: {f['mono']};
        font-size: {f['size_sm']};
        selection-background-color: {c['accent']};
    }}

    /* ── Tab Widget ──────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 0 0 8px 8px;
        background-color: {c['bg_secondary']};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {c['bg_tertiary']};
        color: {c['text_secondary']};
        border: 1px solid {c['border']};
        border-bottom: none;
        border-radius: 6px 6px 0 0;
        padding: 8px 20px;
        margin-right: 2px;
        font-weight: 500;
        min-width: 100px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border-bottom: 2px solid {c['accent']};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {c['bg_hover']};
        color: {c['text_primary']};
    }}

    /* ── Progress Bar ────────────────────────────────────────── */
    QProgressBar {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 3px;
    }}

    /* ── Frames ──────────────────────────────────────────────── */
    QFrame[class="separator"] {{
        background-color: {c['border']};
        max-height: 1px;
        min-height: 1px;
    }}
    QFrame[class="card"] {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 16px;
    }}

    /* ── Tooltips ─────────────────────────────────────────────── */
    QToolTip {{
        background-color: {c['bg_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: {f['size_sm']};
    }}

    /* ── Check Boxes ─────────────────────────────────────────── */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 8px;
        background-color: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c['border']};
        border-radius: 3px;
        background-color: {c['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent']};
        border-color: {c['accent']};
    }}

    /* ── Combo Box ────────────────────────────────────────────── */
    QComboBox {{
        background-color: {c['bg_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-width: 120px;
    }}
    QComboBox:hover {{
        border-color: {c['border_light']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
    }}
    """
