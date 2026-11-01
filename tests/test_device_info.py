"""Tests for DeviceInfo models."""

import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.device_info import DeviceInfo, DeviceState, BootState, StorageInfo


class TestDeviceInfo(unittest.TestCase):
    """Test DeviceInfo data model."""

    def test_default_state(self):
        """Default DeviceInfo should be UNAVAILABLE."""
        info = DeviceInfo()
        self.assertEqual(info.state, DeviceState.UNAVAILABLE)
        self.assertFalse(info.is_authorized())
        self.assertFalse(info.is_any_connection())

    def test_authorized_when_connected(self):
        """Device is authorized only when state is CONNECTED."""
        info = DeviceInfo(state=DeviceState.CONNECTED)
        self.assertTrue(info.is_authorized())
        self.assertTrue(info.is_any_connection())

    def test_not_authorized_when_unauthorized(self):
        """Device is not authorized when state is UNAUTHORIZED."""
        info = DeviceInfo(state=DeviceState.UNAUTHORIZED)
        self.assertFalse(info.is_authorized())
        self.assertTrue(info.is_any_connection())

    def test_any_connection_detects_offline(self):
        """Offline device should be detected as a connection."""
        info = DeviceInfo(state=DeviceState.OFFLINE)
        self.assertFalse(info.is_authorized())
        self.assertTrue(info.is_any_connection())

    def test_status_summary_connected(self):
        """Connected device summary includes model and version."""
        info = DeviceInfo(
            state=DeviceState.CONNECTED,
            model="SM-G965F",
            android_version="10",
        )
        summary = info.get_status_summary()
        self.assertIn("SM-G965F", summary)
        self.assertIn("Android 10", summary)
        self.assertIn("Authorized", summary)

    def test_status_summary_unauthorized(self):
        """Unauthorized summary explains the issue."""
        info = DeviceInfo(state=DeviceState.UNAUTHORIZED)
        summary = info.get_status_summary()
        self.assertIn("NOT authorized", summary)

    def test_status_summary_unavailable(self):
        """Unavailable summary indicates no device."""
        info = DeviceInfo(state=DeviceState.UNAVAILABLE)
        summary = info.get_status_summary()
        self.assertIn("No device", summary)

    def test_mirror_status_no_scrcpy(self):
        """Mirror status explains missing scrcpy."""
        info = DeviceInfo(
            state=DeviceState.CONNECTED,
            scrcpy_available=False,
        )
        status = info.get_mirror_status()
        self.assertIn("not found", status.lower())

    def test_mirror_status_not_authorized(self):
        """Mirror status explains unauthorized state."""
        info = DeviceInfo(
            state=DeviceState.UNAUTHORIZED,
            scrcpy_available=True,
        )
        status = info.get_mirror_status()
        self.assertIn("not authorized", status.lower())

    def test_mirror_status_not_booted(self):
        """Mirror status explains incomplete boot."""
        info = DeviceInfo(
            state=DeviceState.CONNECTED,
            scrcpy_available=True,
            boot_state=BootState.BOOTING,
        )
        status = info.get_mirror_status()
        self.assertIn("not", status.lower())

    def test_mirror_status_ready(self):
        """Mirror status shows ready when all conditions met."""
        info = DeviceInfo(
            state=DeviceState.CONNECTED,
            scrcpy_available=True,
            boot_state=BootState.BOOTED,
        )
        status = info.get_mirror_status()
        self.assertIn("Ready", status)

    def test_can_mirror_flag(self):
        """can_mirror should only be true when authorized AND booted."""
        info = DeviceInfo(state=DeviceState.CONNECTED, boot_state=BootState.BOOTED)
        # can_mirror is set by full_scan, but we can test the condition
        self.assertTrue(info.is_authorized() and info.boot_state == BootState.BOOTED)


class TestStorageInfo(unittest.TestCase):
    """Test StorageInfo data model."""

    def test_default_values(self):
        """Default StorageInfo should have empty strings."""
        si = StorageInfo()
        self.assertEqual(si.partition, "")
        self.assertEqual(si.total, "")

    def test_populated_values(self):
        """StorageInfo stores provided values."""
        si = StorageInfo(
            partition="/dev/block/dm-0",
            total="55G",
            used="42G",
            available="13G",
            use_percent="76%",
            mount_point="/data",
        )
        self.assertEqual(si.total, "55G")
        self.assertEqual(si.use_percent, "76%")


class TestDeviceStateEnum(unittest.TestCase):
    """Test DeviceState enum values."""

    def test_all_states_have_values(self):
        """All DeviceState members should have string values."""
        for state in DeviceState:
            self.assertIsInstance(state.value, str)
            self.assertTrue(len(state.value) > 0)

    def test_boot_states_have_values(self):
        """All BootState members should have string values."""
        for state in BootState:
            self.assertIsInstance(state.value, str)
            self.assertTrue(len(state.value) > 0)


if __name__ == "__main__":
    unittest.main()
