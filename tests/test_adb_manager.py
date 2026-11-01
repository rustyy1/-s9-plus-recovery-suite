"""Tests for ADB Manager — device detection, command execution, and timeout handling.

Uses mocked subprocess calls to test without requiring a physical device.
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import subprocess
import os
import sys

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.adb_manager import AdbManager
from core.device_info import DeviceState, BootState, StorageInfo


class TestAdbManagerFindAdb(unittest.TestCase):
    """Test ADB executable discovery."""

    @patch("shutil.which")
    def test_find_adb_on_path(self, mock_which):
        """ADB found on PATH."""
        mock_which.return_value = "C:\\platform-tools\\adb.exe"
        mgr = AdbManager()

        with patch.object(mgr, "_get_adb_version", return_value="Android Debug Bridge version 1.0.41"):
            with patch("os.path.isfile", return_value=True):
                found, path = mgr.find_adb()

        self.assertTrue(found)
        self.assertIn("adb", path.lower())

    @patch("shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_adb_not_found(self, mock_isfile, mock_which):
        """ADB not found anywhere."""
        mgr = AdbManager()
        found, msg = mgr.find_adb()

        self.assertFalse(found)
        self.assertIn("not found", msg.lower())
        self.assertFalse(mgr.is_available)


class TestAdbManagerDeviceDetection(unittest.TestCase):
    """Test device detection and state parsing."""

    def setUp(self):
        self.mgr = AdbManager()
        self.mgr._adb_path = "C:\\platform-tools\\adb.exe"

    @patch("subprocess.run")
    def test_detect_authorized_device(self, mock_run):
        """Parse a connected, authorized device."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "ABCDEF123456    device usb:1-3 product:star2ltexx model:SM_G965F device:star2lte transport_id:1\n"
            ),
            stderr=""
        )

        devices = self.mgr.detect_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["serial"], "ABCDEF123456")
        self.assertEqual(devices[0]["state"], "device")
        self.assertEqual(devices[0].get("model"), "SM_G965F")

    @patch("subprocess.run")
    def test_detect_unauthorized_device(self, mock_run):
        """Parse an unauthorized device."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "ABCDEF123456    unauthorized usb:1-3 transport_id:1\n"
            ),
            stderr=""
        )

        devices = self.mgr.detect_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["state"], "unauthorized")

    @patch("subprocess.run")
    def test_detect_no_devices(self, mock_run):
        """No devices connected."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n\n",
            stderr=""
        )

        devices = self.mgr.detect_devices()
        self.assertEqual(len(devices), 0)

    @patch("subprocess.run")
    def test_detect_offline_device(self, mock_run):
        """Parse an offline device."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "ABCDEF123456    offline\n"
            ),
            stderr=""
        )

        devices = self.mgr.detect_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["state"], "offline")

    @patch("subprocess.run")
    def test_detect_multiple_devices(self, mock_run):
        """Parse multiple connected devices."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "DEVICE_A    device transport_id:1\n"
                "DEVICE_B    unauthorized transport_id:2\n"
            ),
            stderr=""
        )

        devices = self.mgr.detect_devices()
        self.assertEqual(len(devices), 2)


class TestAdbManagerCommands(unittest.TestCase):
    """Test ADB command execution with mocked subprocess."""

    def setUp(self):
        self.mgr = AdbManager()
        self.mgr._adb_path = "C:\\platform-tools\\adb.exe"

    @patch("subprocess.run")
    def test_get_model(self, mock_run):
        """Successfully read device model."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="SM-G965F\n",
            stderr=""
        )
        model = self.mgr.get_model()
        self.assertEqual(model, "SM-G965F")

    @patch("subprocess.run")
    def test_get_android_version(self, mock_run):
        """Successfully read Android version."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="10\n",
            stderr=""
        )
        version = self.mgr.get_android_version()
        self.assertEqual(version, "10")

    @patch("subprocess.run")
    def test_get_boot_completed(self, mock_run):
        """Boot completed returns BOOTED."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1\n",
            stderr=""
        )
        state = self.mgr.get_boot_completed()
        self.assertEqual(state, BootState.BOOTED)

    @patch("subprocess.run")
    def test_get_boot_not_completed(self, mock_run):
        """Boot not completed returns BOOTING."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0\n",
            stderr=""
        )
        state = self.mgr.get_boot_completed()
        self.assertEqual(state, BootState.BOOTING)

    @patch("subprocess.run")
    def test_command_timeout(self, mock_run):
        """Command timeout is handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
        result = self.mgr._run_adb(["devices"], timeout=10)
        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_adb_not_found_runtime(self, mock_run):
        """FileNotFoundError is handled gracefully."""
        mock_run.side_effect = FileNotFoundError()
        result = self.mgr._run_adb(["devices"])
        self.assertIsNone(result)
        self.assertIsNone(self.mgr._adb_path)

    @patch("subprocess.run")
    def test_get_screen_size(self, mock_run):
        """Parse screen size from wm size output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Physical size: 1440x2960\n",
            stderr=""
        )
        size = self.mgr.get_screen_size()
        self.assertEqual(size, "1440x2960")

    @patch("subprocess.run")
    def test_get_screen_density(self, mock_run):
        """Parse screen density from wm density output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Physical density: 560\n",
            stderr=""
        )
        density = self.mgr.get_screen_density()
        self.assertEqual(density, "560 dpi")


class TestAdbManagerStorage(unittest.TestCase):
    """Test storage information parsing."""

    def setUp(self):
        self.mgr = AdbManager()
        self.mgr._adb_path = "C:\\platform-tools\\adb.exe"

    @patch("subprocess.run")
    def test_get_data_storage(self, mock_run):
        """Parse /data partition info."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Filesystem      Size  Used  Avail Use% Mounted on\n"
                "/dev/block/dm-0  55G   42G    13G  76% /data\n"
            ),
            stderr=""
        )
        storage = self.mgr.get_data_storage()
        self.assertIsNotNone(storage)
        self.assertEqual(storage.total, "55G")
        self.assertEqual(storage.used, "42G")
        self.assertEqual(storage.available, "13G")
        self.assertEqual(storage.use_percent, "76%")
        self.assertEqual(storage.mount_point, "/data")

    @patch("subprocess.run")
    def test_get_storage_info_multiple(self, mock_run):
        """Parse multiple partition entries."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Filesystem      Size  Used  Avail Use% Mounted on\n"
                "/dev/block/dm-0  55G   42G    13G  76% /data\n"
                "/dev/block/sda17 3.3G  2.8G  508M  85% /system\n"
                "tmpfs            1.8G   0     1.8G   0% /dev\n"
            ),
            stderr=""
        )
        partitions = self.mgr.get_storage_info()
        self.assertEqual(len(partitions), 3)


class TestAdbManagerFullScan(unittest.TestCase):
    """Test the full device scan workflow."""

    def setUp(self):
        self.mgr = AdbManager()
        self.mgr._adb_path = "C:\\platform-tools\\adb.exe"
        self.mgr._adb_version = "Android Debug Bridge version 1.0.41"

    @patch("subprocess.run")
    def test_full_scan_no_devices(self, mock_run):
        """Full scan with no devices connected."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\n\n",
            stderr=""
        )
        info = self.mgr.full_scan()
        self.assertEqual(info.state, DeviceState.UNAVAILABLE)

    @patch("subprocess.run")
    def test_full_scan_unauthorized(self, mock_run):
        """Full scan with unauthorized device — should not query properties."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "ABCDEF123456    unauthorized transport_id:1\n"
            ),
            stderr=""
        )
        info = self.mgr.full_scan()
        self.assertEqual(info.state, DeviceState.UNAUTHORIZED)
        self.assertEqual(info.serial, "ABCDEF123456")
        # Model etc should be empty since we can't query
        self.assertEqual(info.android_version, "")

    def test_full_scan_no_adb(self):
        """Full scan when ADB is not available."""
        self.mgr._adb_path = None
        with patch.object(self.mgr, "find_adb", return_value=(False, "not found")):
            info = self.mgr.full_scan()
        self.assertEqual(info.state, DeviceState.UNAVAILABLE)


class TestDeviceState(unittest.TestCase):
    """Test DeviceState mapping."""

    def setUp(self):
        self.mgr = AdbManager()
        self.mgr._adb_path = "C:\\platform-tools\\adb.exe"

    @patch("subprocess.run")
    def test_state_mapping_device(self, mock_run):
        """State 'device' maps to CONNECTED."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\nABC    device\n",
            stderr=""
        )
        state = self.mgr.get_device_state()
        self.assertEqual(state, DeviceState.CONNECTED)

    @patch("subprocess.run")
    def test_state_mapping_unauthorized(self, mock_run):
        """State 'unauthorized' maps to UNAUTHORIZED."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\nABC    unauthorized\n",
            stderr=""
        )
        state = self.mgr.get_device_state()
        self.assertEqual(state, DeviceState.UNAUTHORIZED)

    @patch("subprocess.run")
    def test_state_mapping_recovery(self, mock_run):
        """State 'recovery' maps to RECOVERY."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="List of devices attached\nABC    recovery\n",
            stderr=""
        )
        state = self.mgr.get_device_state()
        self.assertEqual(state, DeviceState.RECOVERY)


if __name__ == "__main__":
    unittest.main()
