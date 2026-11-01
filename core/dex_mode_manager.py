"""Samsung DeX vs Screen Mirroring Mode Manager for Galaxy S9+.

Handles:
- Detecting if the S9+ has entered Samsung DeX on the external HDMI display
- Providing safe, supported options to switch to phone screen mirroring mode
- Guidance for physical mouse / keyboard shortcuts on the HDMI display
- Safe non-destructive ADB commands to request exiting DeX mode
"""

from typing import Optional, Tuple
from core.adb_manager import AdbManager


class DexModeManager:
    """Manages Samsung DeX vs Screen Mirroring behavior on external HDMI displays."""

    def __init__(self, adb_manager: Optional[AdbManager] = None):
        self._adb = adb_manager

    def check_dex_active_adb(self, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Check if Samsung Desktop Mode is currently active via ADB dumpsys."""
        if not self._adb or not self._adb.is_available:
            return False, "ADB not available to check DeX status."

        try:
            res = self._adb.run_shell(["dumpsys", "desktopmode"], serial=serial, timeout=4)
            if res and res.returncode == 0:
                stdout_lower = res.stdout.lower()
                if "state: enabled" in stdout_lower or "desktop mode: true" in stdout_lower or "currenstate: enabled" in stdout_lower:
                    return True, "Samsung DeX is currently active on the external display."
                return False, "Screen mirroring is active (DeX desktop not engaged)."
        except Exception as e:
            return False, f"Could not query desktop mode: {e}"

        return False, "Desktop mode status unknown."

    def request_switch_to_mirroring_adb(self, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Send safe Samsung broadcast to exit desktop mode and switch to mirroring."""
        if not self._adb or not self._adb.is_available:
            return False, "ADB is not available or authorized to send broadcast."

        try:
            # Samsung official desktopmode exit broadcast
            cmd = ["am", "broadcast", "-a", "com.samsung.android.desktopmode.action.STOP_DESKTOP_MODE"]
            res = self._adb.run_shell(cmd, serial=serial, timeout=5)
            if res and res.returncode == 0:
                return True, "Sent STOP_DESKTOP_MODE broadcast to S9+."
            else:
                return False, f"Broadcast failed: {res.stderr if res else 'timeout'}"
        except Exception as e:
            return False, f"Error sending switch broadcast: {e}"

    @staticmethod
    def get_hardware_switching_guide() -> str:
        """Step-by-step instructions to switch to mirroring using a physical mouse on the HDMI screen."""
        return """
<b>How to Switch from DeX to Phone Screen Mirroring (Without ADB):</b>
<ol>
<li><b>Bottom-Right System Bar:</b> Look at the bottom-right corner of the HDMI screen (where the clock and battery are shown).</li>
<li><b>Open Quick Settings:</b> Click the chevron or notifications icon in the taskbar.</li>
<li><b>Click Samsung DeX:</b> Find the 'Samsung DeX' item in the notifications or quick panel.</li>
<li><b>Select 'Switch to screen mirroring':</b> The external screen will immediately switch from the desktop interface to a 1:1 mirror of your phone's screen.</li>
<li><b>Hardware Keyboard Shortcut:</b> If you have a physical keyboard plugged into your USB-C hub, press <code>Windows Key + W</code> to toggle DeX and Screen Mirroring.</li>
</ol>
"""
