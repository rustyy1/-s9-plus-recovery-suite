"""Tests for genuine UVC video capture, format handling, stream lifecycle, and decoupling from ADB."""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
from core.uvc_capture import FpsTracker, VideoFormatInfo, CaptureDeviceInfo, UvcCaptureManager
from core.adb_controller import AdbController
from core.device_info import DeviceInfo, DeviceState

# Offscreen app for QtMultimedia tests
app = QApplication.instance()
if not app:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication([])


class TestFpsTracker(unittest.TestCase):
    """Test frame rate calculation."""

    def test_initial_fps_zero(self):
        tracker = FpsTracker()
        self.assertEqual(tracker.current_fps, 0.0)

    def test_record_frames(self):
        tracker = FpsTracker()
        for _ in range(30):
            tracker.record_frame()
        self.assertIsInstance(tracker.current_fps, float)

    def test_reset(self):
        tracker = FpsTracker()
        for _ in range(10):
            tracker.record_frame()
        tracker.reset()
        self.assertEqual(tracker.current_fps, 0.0)


class TestUvcCaptureManagerDecoupled(unittest.TestCase):
    """Test capture device enumeration, start, failure, disconnect, and ADB decoupling."""

    def setUp(self):
        self.mgr = UvcCaptureManager()

    @patch("PySide6.QtMultimedia.QMediaDevices.videoInputs")
    def test_genuine_capture_device_detected(self, mock_inputs):
        """Scenario: Genuine video capture card detected."""
        mock_dev = MagicMock()
        mock_dev.id.return_value = b"cam_link_4k"
        mock_dev.description.return_value = "Cam Link 4K"
        mock_dev.isDefault.return_value = True

        mock_fmt = MagicMock()
        mock_res = MagicMock()
        mock_res.width.return_value = 1920
        mock_res.height.return_value = 1080
        mock_fmt.resolution.return_value = mock_res
        mock_fmt.minFrameRate.return_value = 30.0
        mock_fmt.maxFrameRate.return_value = 60.0
        mock_fmt.pixelFormat.return_value = "NV12"
        mock_dev.videoFormats.return_value = [mock_fmt]

        mock_inputs.return_value = [mock_dev]

        devices = self.mgr.get_available_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].description, "Cam Link 4K")
        self.assertEqual(devices[0].device_id, "cam_link_4k")
        self.assertEqual(devices[0].formats[0].width, 1920)
        self.assertEqual(devices[0].formats[0].height, 1080)

    @patch("PySide6.QtMultimedia.QMediaDevices.videoInputs")
    def test_capture_stream_fails_nonexistent_device(self, mock_inputs):
        """Scenario: Capture stream fails when device not found."""
        mock_inputs.return_value = []
        ok, msg = self.mgr.start_capture("non_existent_id")
        self.assertFalse(ok)
        self.assertIn("not found", msg.lower())

    def test_capture_device_disconnect_handling(self):
        """Scenario: Capture device disconnect event triggers signal."""
        received = []
        self.mgr.devices_changed.connect(lambda: received.append(True))
        self.mgr._on_video_inputs_changed()
        self.assertEqual(len(received), 1)

    @patch("PySide6.QtMultimedia.QMediaDevices.videoInputs")
    def test_video_active_while_adb_unavailable(self, mock_inputs):
        """Scenario: Video subsystem works while ADB is unavailable/unauthorized."""
        mock_dev = MagicMock()
        mock_dev.id.return_value = b"usb_video_capture"
        mock_dev.description.return_value = "USB Video Capture"
        mock_dev.isDefault.return_value = True
        mock_dev.videoFormats.return_value = []
        mock_inputs.return_value = [mock_dev]

        # Setup mock ADB controller with unauthorized device
        mock_adb = MagicMock()
        mock_adb.is_available = True
        dev = DeviceInfo(serial="22858E1E40047ECE", state=DeviceState.UNAUTHORIZED)
        mock_adb.get_devices.return_value = [dev]
        ctrl = AdbController(mock_adb)

        # 1. Video device is available and enumerate-able
        devices = self.mgr.get_available_devices()
        self.assertEqual(len(devices), 1)

        # 2. ADB authorization check fails
        auth_ok, reason = ctrl.check_authorization()
        self.assertFalse(auth_ok)
        self.assertIn("unauthorized", reason.lower())

        # 3. Touch input is properly rejected because ADB is unauthorized
        tap_ok, tap_msg = ctrl.send_tap(0.5, 0.5)
        self.assertFalse(tap_ok)
        self.assertIn("rejected", tap_msg.lower())


if __name__ == "__main__":
    unittest.main()
