"""Tests for DexModeManager detection and safe switching broadcast."""

import unittest
from unittest.mock import MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.dex_mode_manager import DexModeManager


class TestDexModeManager(unittest.TestCase):
    """Test Samsung DeX mode detection and broadcast command."""

    def setUp(self):
        self.mock_adb = MagicMock()
        self.mock_adb.is_available = True
        self.mgr = DexModeManager(self.mock_adb)

    def test_check_dex_active_true(self):
        res = MagicMock()
        res.returncode = 0
        res.stdout = "mCurrentState: ENABLED\nDesktop Mode: true"
        self.mock_adb.run_shell.return_value = res

        active, msg = self.mgr.check_dex_active_adb()
        self.assertTrue(active)
        self.assertIn("active", msg.lower())

    def test_check_dex_active_false(self):
        res = MagicMock()
        res.returncode = 0
        res.stdout = "mCurrentState: DISABLED\nDesktop Mode: false"
        self.mock_adb.run_shell.return_value = res

        active, msg = self.mgr.check_dex_active_adb()
        self.assertFalse(active)

    def test_switch_broadcast_sent(self):
        res = MagicMock()
        res.returncode = 0
        self.mock_adb.run_shell.return_value = res

        ok, msg = self.mgr.request_switch_to_mirroring_adb()
        self.assertTrue(ok)
        self.assertIn("STOP_DESKTOP_MODE", msg)
        self.mock_adb.run_shell.assert_called_with(
            ["am", "broadcast", "-a", "com.samsung.android.desktopmode.action.STOP_DESKTOP_MODE"],
            serial=None, timeout=5
        )


if __name__ == "__main__":
    unittest.main()
