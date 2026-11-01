"""Automated tests for USB Hardware Detector, USB interface descriptors, and signal path diagnostics."""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.usb_detector import UsbHardwareDetector, PhoneUsbInspectionResult


class TestUsbHardwareDetector(unittest.TestCase):
    """Test USB PnP device tree and descriptor parsing with mocked Windows responses."""

    def setUp(self):
        self.detector = UsbHardwareDetector()

    @patch("subprocess.run")
    def test_no_device_connected(self, mock_run):
        """Scenario 1: No device connected."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "[]"
        mock_run.return_value = mock_proc

        result = self.detector.inspect_connected_phone()
        self.assertFalse(result.is_physically_connected)
        self.assertIn("No Samsung USB device", result.hardware_diagnosis)

    @patch("subprocess.run")
    def test_s9_connected_without_video_interface(self, mock_run):
        """Scenario 2: S9+ connected but exposes MTP, Modem, ADB only (NO video interface)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_data = [
            {
                "Name": "SAMSUNG Mobile USB Composite Device",
                "DeviceID": "USB\\VID_04E8&PID_6860\\22858E1E40047ECE",
                "Service": "dg_ssudbus",
                "Present": True
            },
            {
                "Name": "Galaxy S9+",
                "DeviceID": "USB\\VID_04E8&PID_6860&MS_COMP_MTP&SAMSUNG_ANDROID\\7&2E9FFE24&0&0000",
                "Service": "WUDFWpdMtp",
                "Present": True
            },
            {
                "Name": "SAMSUNG Mobile USB Modem #3",
                "DeviceID": "USB\\VID_04E8&PID_6860&MODEM\\7&2E9FFE24&0&0001",
                "Service": "Modem",
                "Present": True
            },
            {
                "Name": "SAMSUNG Android ADB Interface",
                "DeviceID": "USB\\VID_04E8&PID_6860&ADB\\7&2E9FFE24&0&0004",
                "Service": "WINUSB",
                "Present": True
            }
        ]
        mock_proc.stdout = json.dumps(mock_data)
        mock_run.return_value = mock_proc

        result = self.detector.inspect_connected_phone()
        self.assertTrue(result.is_physically_connected)
        self.assertEqual(result.serial_number, "22858E1E40047ECE")
        self.assertTrue(result.has_mtp_interface)
        self.assertTrue(result.has_modem_interface)
        self.assertTrue(result.has_adb_interface)
        # CRITICAL TEST: Phone does NOT have UVC video interface
        self.assertFalse(result.has_uvc_video_interface)
        self.assertFalse(result.pc_port_supports_dp_sink)
        self.assertIn("does NOT expose a USB Video Class (UVC) endpoint", result.hardware_diagnosis)

    @patch("subprocess.run")
    def test_device_with_uvc_interface_hypothetical(self, mock_run):
        """Scenario: Connected device with standard UVC class 0x0E interface."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_data = [
            {
                "Name": "USB Video Device",
                "DeviceID": "USB\\VID_04E8&PID_6860&MI_00\\7&Class_0e",
                "Service": "usbvideo",
                "Present": True
            }
        ]
        mock_proc.stdout = json.dumps(mock_data)
        mock_run.return_value = mock_proc

        result = self.detector.inspect_connected_phone()
        self.assertTrue(result.is_physically_connected)
        self.assertTrue(result.has_uvc_video_interface)
        self.assertIn("Direct USB video endpoint detected", result.hardware_diagnosis)


if __name__ == "__main__":
    unittest.main()
