"""UVC Video Capture Manager for S9+ HDMI Viewer & Controller.

Pure hardware-backed capture manager:
- Enumerates genuine Windows video capture devices via Windows Media Foundation
- Queries real supported resolutions and frame rates
- Manages QCamera and QMediaCaptureSession
- Measures real-time incoming FPS
- Handles device disconnect, reconnect, and capture errors
- NEVER renders simulated frames, fake phone screens, or placeholder graphics
"""

import time
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QSize, Qt
from PySide6.QtMultimedia import (
    QMediaDevices, QCamera, QCameraDevice, QCameraFormat, QMediaCaptureSession,
)
from PySide6.QtMultimediaWidgets import QVideoWidget


@dataclass
class VideoFormatInfo:
    """Represents a supported video format."""
    width: int
    height: int
    min_fps: float
    max_fps: float
    pixel_format: str

    def __str__(self) -> str:
        fps_str = f"{int(self.max_fps)} fps" if self.max_fps > 0 else ""
        return f"{self.width}x{self.height} {fps_str}".strip()


@dataclass
class CaptureDeviceInfo:
    """Represents an enumerated genuine physical capture device."""
    device_id: str
    description: str
    is_default: bool
    formats: List[VideoFormatInfo]


class FpsTracker(QObject):
    """Calculates smoothed real-time frame rates from incoming frames."""
    fps_updated = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame_count = 0
        self._last_time = time.time()
        self._current_fps = 0.0

    def record_frame(self):
        """Record the arrival of a real video frame."""
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._last_time
        if elapsed >= 1.0:
            self._current_fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_time = now
            self.fps_updated.emit(self._current_fps)

    def reset(self):
        self._frame_count = 0
        self._last_time = time.time()
        self._current_fps = 0.0
        self.fps_updated.emit(0.0)

    @property
    def current_fps(self) -> float:
        return self._current_fps


class UvcCaptureManager(QObject):
    """Manages genuine physical UVC video capture devices using Windows Media Foundation."""

    devices_changed = Signal()
    status_changed = Signal(str, str)  # status_type, message
    frame_rate_updated = Signal(float)  # live fps
    resolution_changed = Signal(int, int)  # current width, height

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera: Optional[QCamera] = None
        self._capture_session: Optional[QMediaCaptureSession] = None
        self._video_widget: Optional[QVideoWidget] = None
        self._fps_tracker = FpsTracker(self)
        self._fps_tracker.fps_updated.connect(self.frame_rate_updated)

        self._current_device_id: Optional[str] = None
        self._current_format: Optional[VideoFormatInfo] = None

        # Listen for real hardware plug/unplug events
        self._media_devices = QMediaDevices(self)
        self._media_devices.videoInputsChanged.connect(self._on_video_inputs_changed)

    # ── Device Enumeration ─────────────────────────────────────────

    def get_available_devices(self) -> List[CaptureDeviceInfo]:
        """Enumerate only genuine connected video capture devices via Windows Media Foundation."""
        devices: List[CaptureDeviceInfo] = []
        raw_devices = QMediaDevices.videoInputs()

        for dev in raw_devices:
            dev_id = bytes(dev.id()).decode("utf-8", errors="replace")
            desc = dev.description()
            is_def = dev.isDefault()

            formats: List[VideoFormatInfo] = []
            for fmt in dev.videoFormats():
                res = fmt.resolution()
                formats.append(VideoFormatInfo(
                    width=res.width(),
                    height=res.height(),
                    min_fps=fmt.minFrameRate(),
                    max_fps=fmt.maxFrameRate(),
                    pixel_format=str(fmt.pixelFormat()),
                ))

            unique_formats = []
            seen = set()
            for f in sorted(formats, key=lambda x: (x.width * x.height, x.max_fps), reverse=True):
                key = (f.width, f.height)
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(f)

            devices.append(CaptureDeviceInfo(
                device_id=dev_id,
                description=desc,
                is_default=is_def,
                formats=unique_formats,
            ))

        return devices

    def _on_video_inputs_changed(self):
        """Called when a USB video capture device is physically plugged in or unplugged."""
        self.status_changed.emit("info", "USB video devices changed (hardware event)")
        self.devices_changed.emit()

    # ── Capture Session Management ────────────────────────────────

    def attach_video_widget(self, video_widget: QVideoWidget):
        """Attach the QVideoWidget display."""
        self._video_widget = video_widget
        sink = self._video_widget.videoSink()
        if sink:
            sink.videoFrameChanged.connect(self._on_video_frame_arrived)

    def _on_video_frame_arrived(self, frame):
        """Real frame arrival hook for FPS tracking."""
        self._fps_tracker.record_frame()

    def start_capture(self, device_id: str, preferred_format: Optional[VideoFormatInfo] = None) -> Tuple[bool, str]:
        """Start capturing from a real, physical UVC capture card."""
        self.stop_capture()

        raw_devices = QMediaDevices.videoInputs()
        target_dev: Optional[QCameraDevice] = None
        for dev in raw_devices:
            if bytes(dev.id()).decode("utf-8", errors="replace") == device_id:
                target_dev = dev
                break

        if not target_dev:
            err_msg = f"Capture device '{device_id}' not found or disconnected."
            self.status_changed.emit("error", err_msg)
            return False, err_msg

        try:
            self._camera = QCamera(target_dev, self)
            self._camera.errorOccurred.connect(self._on_camera_error)

            if preferred_format:
                for fmt in target_dev.videoFormats():
                    res = fmt.resolution()
                    if res.width() == preferred_format.width and res.height() == preferred_format.height:
                        self._camera.setCameraFormat(fmt)
                        self._current_format = preferred_format
                        break

            self._capture_session = QMediaCaptureSession(self)
            self._capture_session.setCamera(self._camera)

            if self._video_widget:
                self._capture_session.setVideoOutput(self._video_widget)

            self._camera.start()
            self._current_device_id = device_id
            self._fps_tracker.reset()

            msg = f"Capture active: {target_dev.description()}"
            self.status_changed.emit("good", msg)
            return True, msg

        except Exception as e:
            err_msg = f"Failed to initialize video capture: {e}"
            self.status_changed.emit("error", err_msg)
            return False, err_msg

    def stop_capture(self):
        """Stop any active physical capture session."""
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera.deleteLater()
            self._camera = None

        if self._capture_session:
            self._capture_session.deleteLater()
            self._capture_session = None

        self._current_device_id = None
        self._fps_tracker.reset()
        self.status_changed.emit("info", "Capture stopped")

    def _on_camera_error(self, error, error_string: str):
        """Handle hardware camera error."""
        msg = f"Capture device hardware error ({error}): {error_string}"
        self.status_changed.emit("error", msg)

    @property
    def is_active(self) -> bool:
        return self._camera is not None and self._camera.isActive()

    @property
    def current_device_id(self) -> Optional[str]:
        return self._current_device_id
