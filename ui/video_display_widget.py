"""Video Display Widget for S9+ HDMI Viewer & Controller.

Displays genuine incoming video from physical UVC HDMI capture devices via QVideoWidget.
- Strict aspect-ratio preservation (KeepAspectRatio)
- Clear idle screen when no physical video source is active
- Transparent touch overlay reporting normalized coordinates only when input control is valid
- NEVER renders simulated frames or fake phone graphics
"""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtMultimediaWidgets import QVideoWidget

from ui.theme import COLORS, FONTS


class TouchOverlay(QWidget):
    """Transparent overlay on top of the video feed that captures touch coordinates.
    
    Does NOT claim control works unless ADB is verified. If unauthorized, displays
    an explicit warning that clicks do not reach the phone over standard video feed.
    """

    touch_clicked = Signal(float, float)  # norm_x, norm_y (0.0 to 1.0)
    touch_swiped = Signal(float, float, float, float)  # start_nx, start_ny, end_nx, end_ny

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self._is_adb_authorized: bool = False
        self._active_video_rect: QRectF = QRectF()
        self._press_pos: Optional[QPointF] = None
        self._ripples = []
        self._ripple_timer = QTimer(self)
        self._ripple_timer.timeout.connect(self._update_ripples)

        # Warning banner message when unauthorized click happens
        self._warning_text: str = ""
        self._warning_timer = QTimer(self)
        self._warning_timer.setSingleShot(True)
        self._warning_timer.timeout.connect(self._clear_warning)

    def set_adb_authorized(self, authorized: bool):
        self._is_adb_authorized = authorized
        self.update()

    def set_active_video_rect(self, rect: QRectF):
        self._active_video_rect = rect
        self.update()

    def _update_ripples(self):
        updated = []
        for r in self._ripples:
            r[2] += 4
            r[5] -= 15
            if r[5] > 0 and r[2] < r[3]:
                updated.append(r)
        self._ripples = updated
        if not self._ripples:
            self._ripple_timer.stop()
        self.update()

    def _add_ripple(self, x: float, y: float, color: QColor):
        self._ripples.append([x, y, 6, 36, color, 220])
        if not self._ripple_timer.isActive():
            self._ripple_timer.start(20)
        self.update()

    def _clear_warning(self):
        self._warning_text = ""
        self.update()

    def _calculate_normalized(self, pos: QPointF) -> Optional[Tuple[float, float]]:
        rect = self._active_video_rect if not self._active_video_rect.isEmpty() else QRectF(self.rect())
        if not rect.contains(pos):
            return None
        norm_x = (pos.x() - rect.left()) / rect.width()
        norm_y = (pos.y() - rect.top()) / rect.height()
        return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position()
            if self._is_adb_authorized:
                self._add_ripple(event.position().x(), event.position().y(), QColor(0, 210, 255))
            else:
                self._add_ripple(event.position().x(), event.position().y(), QColor(255, 90, 95))
                self._warning_text = (
                    "Touch control unavailable: ADB is not authorized.\n"
                    "Connect a physical USB mouse to your phone's USB-C hub to navigate without ADB."
                )
                self._warning_timer.start(4000)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos:
            release_pos = event.position()
            dist = (release_pos - self._press_pos).manhattanLength()

            if dist < 10:
                norm = self._calculate_normalized(release_pos)
                if norm and self._is_adb_authorized:
                    self.touch_clicked.emit(norm[0], norm[1])
            else:
                start_n = self._calculate_normalized(self._press_pos)
                end_n = self._calculate_normalized(release_pos)
                if start_n and end_n and self._is_adb_authorized:
                    self.touch_swiped.emit(start_n[0], start_n[1], end_n[0], end_n[1])

            self._press_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw Ripples
        for x, y, r, _, color, alpha in self._ripples:
            c = QColor(color)
            c.setAlpha(alpha)
            painter.setPen(QPen(c, 2))
            painter.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), max(0, alpha // 4))))
            painter.drawEllipse(QPointF(x, y), r, r)

        # Draw Warning Overlay if click occurred without authorization
        if self._warning_text:
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            box_w = min(self.width() - 40, 540)
            box_h = 60
            box_x = (self.width() - box_w) // 2
            box_y = self.height() - box_h - 24

            painter.setPen(QPen(QColor(255, 75, 75), 1))
            painter.setBrush(QBrush(QColor(30, 20, 25, 235)))
            painter.drawRoundedRect(box_x, box_y, box_w, box_h, 8, 8)

            painter.setPen(QColor(255, 200, 200))
            painter.drawText(QRectF(box_x + 12, box_y + 8, box_w - 24, box_h - 16),
                             Qt.AlignCenter | Qt.TextWordWrap, self._warning_text)

        painter.end()


class IdlePlaceholderWidget(QFrame):
    """Clean, honest idle state displayed when no real video capture source is active."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border: 1px dashed {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel("📹")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("No Live Video Capture Stream")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONTS['size_lg']};
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(title)

        desc = QLabel(
            "Select an available video capture device in the toolbar above and click 'Connect'.\n\n"
            "• Direct USB Cable: The Galaxy S9+ does not expose a UVC video stream over standard USB data.\n"
            "• To view S9+ display: Connect phone USB-C → HDMI Hub → USB UVC Capture Card → PC USB."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['size_base']};
            line-height: 1.5;
            max-width: 500px;
            background: transparent;
        """)
        layout.addWidget(desc)


class VideoDisplayWidget(QWidget):
    """Main container for real physical video rendering and touch overlay."""

    touch_tapped = Signal(float, float)
    touch_swiped = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']}; border-radius: 8px;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 320)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)

        # Page 0: Idle placeholder
        self._idle_widget = IdlePlaceholderWidget(self)
        self._stack.addWidget(self._idle_widget)

        # Page 1: Physical UVC Video Widget
        self._uvc_widget = QVideoWidget(self)
        self._uvc_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self._uvc_widget.setStyleSheet("background-color: #0b0e14;")
        self._stack.addWidget(self._uvc_widget)

        self._layout.addWidget(self._stack)

        # Touch Overlay on top
        self._overlay = TouchOverlay(self)
        self._overlay.touch_clicked.connect(self.touch_tapped)
        self._overlay.touch_swiped.connect(self.touch_swiped)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._update_overlay_active_rect()

    def _update_overlay_active_rect(self):
        w, h = self.width(), self.height()
        aspect = 16.0 / 9.0
        widget_aspect = w / max(1, h)

        if widget_aspect > aspect:
            content_h = h
            content_w = int(h * aspect)
            x = (w - content_w) // 2
            y = 0
        else:
            content_w = w
            content_h = int(w / aspect)
            x = 0
            y = (h - content_h) // 2

        self._overlay.set_active_video_rect(QRectF(x, y, content_w, content_h))

    @property
    def uvc_video_widget(self) -> QVideoWidget:
        return self._uvc_widget

    def show_live_stream(self):
        """Show active hardware video widget."""
        self._stack.setCurrentIndex(1)
        self._update_overlay_active_rect()

    def show_idle_state(self):
        """Show idle placeholder when no stream is active."""
        self._stack.setCurrentIndex(0)
        self._update_overlay_active_rect()

    def set_adb_authorized(self, authorized: bool):
        self._overlay.set_adb_authorized(authorized)
