"""Optional ADB Remote Control Module for S9+ HDMI Viewer & Controller.

CRITICAL DESIGN PRINCIPLE:
Video capture (HDMI via UVC) and Touch Control (ADB over USB) are strictly separated.
Mouse clicks on the video stream NEVER send input unless USB debugging is
explicitly enabled, connected, and authorized via ADB.

When ADB is not authorized, touch control is marked as DISABLED, and the user
is instructed to connect a physical USB mouse directly to the phone's USB-C hub.
"""

import threading
from typing import Optional, Tuple, Callable
import logging

from core.adb_manager import AdbManager
from core.device_info import DeviceInfo, DeviceState

logger = logging.getLogger("hdmi_viewer.adb_controller")


class AdbController:
    """Manages optional remote input control over authorized ADB connection."""

    def __init__(self, adb_manager: AdbManager, log_callback: Optional[Callable[[str], None]] = None):
        self._adb = adb_manager
        self._log = log_callback or (lambda msg: None)
        self._phone_width: int = 1080
        self._phone_height: int = 2220  # S9+ default FHD+ (18.5:9)
        self._scrcpy_process = None

    def refresh_screen_size(self, serial: Optional[str] = None):
        """Query physical screen resolution via adb wm size."""
        if not self._adb.is_available:
            return
        w, h = self._adb.get_screen_size(serial)
        if w > 0 and h > 0:
            self._phone_width = w
            self._phone_height = h
            self._log(f"Detected phone resolution: {w}x{h}")

    @property
    def is_adb_ready(self) -> bool:
        """Check if ADB is present on system."""
        return self._adb.is_available

    def check_authorization(self) -> Tuple[bool, str]:
        """Check if an authorized device is connected via ADB.

        Returns:
            (authorized: bool, message: str)
        """
        if not self._adb.is_available:
            return False, "ADB not installed or not found on system."

        devices = self._adb.get_devices()
        if not devices:
            return False, "No device detected over USB data. Touch control is unavailable."

        for dev in devices:
            if dev.state == DeviceState.CONNECTED:
                return True, f"ADB authorized on device {dev.serial}."
            elif dev.state == DeviceState.UNAUTHORIZED:
                return False, "Device is UNAUTHORIZED. Confirm the RSA debugging prompt on the phone."
            elif dev.state == DeviceState.OFFLINE:
                return False, "Device is OFFLINE. Reconnect the USB data cable."

        return False, "Device state not ready for input control."

    # ── Coordinate Transformation ──────────────────────────────────

    def transform_normalized_to_device(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Convert normalized (0.0 - 1.0) video canvas coordinates to device screen pixels.

        Clamps coordinates to [0, phone_dimension - 1].
        """
        clamped_x = max(0.0, min(1.0, norm_x))
        clamped_y = max(0.0, min(1.0, norm_y))
        dev_x = int(clamped_x * (self._phone_width - 1))
        dev_y = int(clamped_y * (self._phone_height - 1))
        return dev_x, dev_y

    # ── Input Commands (Asynchronous) ──────────────────────────────

    def send_tap(self, norm_x: float, norm_y: float, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Send a touch tap event if ADB is authorized."""
        auth_ok, reason = self.check_authorization()
        if not auth_ok:
            return False, f"Touch input rejected: {reason}"

        dev_x, dev_y = self.transform_normalized_to_device(norm_x, norm_y)

        def _do_tap():
            try:
                self._adb.run_shell(["input", "tap", str(dev_x), str(dev_y)], serial=serial, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send tap: {e}")

        threading.Thread(target=_do_tap, daemon=True).start()
        return True, f"Tapped at ({dev_x}, {dev_y})"

    def send_swipe(self, n_x1: float, n_y1: float, n_x2: float, n_y2: float,
                   duration_ms: int = 300, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Send a swipe/drag gesture."""
        auth_ok, reason = self.check_authorization()
        if not auth_ok:
            return False, f"Swipe rejected: {reason}"

        x1, y1 = self.transform_normalized_to_device(n_x1, n_y1)
        x2, y2 = self.transform_normalized_to_device(n_x2, n_y2)

        def _do_swipe():
            try:
                self._adb.run_shell(
                    ["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                    serial=serial, timeout=8
                )
            except Exception as e:
                logger.error(f"Failed to send swipe: {e}")

        threading.Thread(target=_do_swipe, daemon=True).start()
        return True, f"Swiped ({x1},{y1}) -> ({x2},{y2})"

    def send_key(self, keycode: int, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Send an Android keycode (Back=4, Home=3, Power=26, Recents=187, etc.)."""
        auth_ok, reason = self.check_authorization()
        if not auth_ok:
            return False, f"Keyevent rejected: {reason}"

        def _do_key():
            try:
                self._adb.run_shell(["input", "keyevent", str(keycode)], serial=serial, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send keycode: {e}")

        threading.Thread(target=_do_key, daemon=True).start()
        return True, f"Sent keyevent {keycode}"

    def send_text(self, text: str, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Send typed text to active text input."""
        auth_ok, reason = self.check_authorization()
        if not auth_ok:
            return False, f"Text input rejected: {reason}"

        # Replace spaces with %s for adb input text
        safe_text = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')

        def _do_text():
            try:
                self._adb.run_shell(["input", "text", safe_text], serial=serial, timeout=8)
            except Exception as e:
                logger.error(f"Failed to send text: {e}")

        threading.Thread(target=_do_text, daemon=True).start()
        return True, "Text sent"

    # ── scrcpy Control-Only Mode ───────────────────────────────────

    def start_scrcpy_control_only(self, scrcpy_path: str, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Launch scrcpy in control-only mode (--no-video --no-audio).

        This forwards keyboard and mouse events directly from PC hardware
        to the phone without opening a duplicate video stream.
        """
        import subprocess

        auth_ok, reason = self.check_authorization()
        if not auth_ok:
            return False, f"Cannot launch scrcpy control: {reason}"

        if self._scrcpy_process and self._scrcpy_process.poll() is None:
            return True, "scrcpy control session is already running"

        cmd = [scrcpy_path, "--no-video", "--no-audio"]
        if serial:
            cmd.extend(["--serial", serial])

        try:
            self._scrcpy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._log("Started scrcpy in control-only mode (hardware keyboard/mouse forwarding).")
            return True, "scrcpy control active"
        except Exception as e:
            return False, f"Failed to launch scrcpy: {e}"

    def stop_scrcpy_control_only(self):
        """Stop control-only scrcpy session."""
        if self._scrcpy_process:
            try:
                self._scrcpy_process.terminate()
            except Exception:
                pass
            self._scrcpy_process = None
