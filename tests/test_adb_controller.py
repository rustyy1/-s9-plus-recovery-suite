"""Tests for ADB Remote Controller coordinate mapping and authorization gating."""

import unittest
from unittest.mock import MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.adb_controller import AdbController
from core.device_info import DeviceInfo, DeviceState


class TestAdbController(unittest.TestCase):
    """Test coordinate transformation and safety checks."""

    def setUp(self):
        self.mock_adb = MagicMock()
        self.mock_adb.is_available = True
        self.ctrl = AdbController(self.mock_adb)
        # S9+ default 1080x2220
        self.ctrl._phone_width = 1080
        self.ctrl._phone_height = 2220

    def test_coordinate_transformation_corners(self):
        # Top-left corner
        x, y = self.ctrl.transform_normalized_to_device(0.0, 0.0)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

        # Bottom-right corner
        x, y = self.ctrl.transform_normalized_to_device(1.0, 1.0)
        self.assertEqual(x, 1079)
        self.assertEqual(y, 2219)

        # Center
        x, y = self.ctrl.transform_normalized_to_device(0.5, 0.5)
        self.assertAlmostEqual(x, 539, delta=2)
        self.assertAlmostEqual(y, 1109, delta=2)

    def test_coordinate_transformation_clamping(self):
        # Out-of-bounds negative
        x, y = self.ctrl.transform_normalized_to_device(-0.5, -0.2)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

        # Out-of-bounds positive
        x, y = self.ctrl.transform_normalized_to_device(1.5, 2.0)
        self.assertEqual(x, 1079)
        self.assertEqual(y, 2219)

    def test_rejection_when_unauthorized(self):
        # Device is unauthorized
        dev = DeviceInfo(serial="22858E1E40047ECE", state=DeviceState.UNAUTHORIZED)
        self.mock_adb.get_devices.return_value = [dev]

        ok, msg = self.ctrl.send_tap(0.5, 0.5)
        self.assertFalse(ok)
        self.assertIn("rejected", msg.lower())
        self.assertIn("unauthorized", msg.lower())

    def test_rejection_when_no_devices(self):
        self.mock_adb.get_devices.return_value = []
        ok, msg = self.ctrl.send_tap(0.5, 0.5)
        self.assertFalse(ok)
        self.assertIn("rejected", msg.lower())

    def test_tap_sent_when_authorized(self):
        dev = DeviceInfo(serial="22858E1E40047ECE", state=DeviceState.CONNECTED)
        self.mock_adb.get_devices.return_value = [dev]

        ok, msg = self.ctrl.send_tap(0.5, 0.5)
        self.assertTrue(ok)
        self.assertIn("Tapped", msg)

    def test_keyevent_sent_when_authorized(self):
        dev = DeviceInfo(serial="22858E1E40047ECE", state=DeviceState.CONNECTED)
        self.mock_adb.get_devices.return_value = [dev]

        ok, msg = self.ctrl.send_key(3)  # Home button
        self.assertTrue(ok)
        self.assertIn("3", msg)


if __name__ == "__main__":
    unittest.main()
