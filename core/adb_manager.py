"""ADB command execution and device detection for Galaxy S9+ Recovery Console.

Handles all interaction with the Android Debug Bridge, including:
- Finding the ADB executable
- Detecting connected devices and their states
- Querying device properties (model, Android version, boot state, storage)
- Proper timeout handling and error reporting
"""

import subprocess
import shutil
import re
import os
import logging
from typing import Optional, Tuple, List, Callable

from core.device_info import DeviceInfo, DeviceState, BootState, StorageInfo

logger = logging.getLogger("recovery_console.adb")

# Default timeout for ADB commands (seconds)
DEFAULT_TIMEOUT = 10
SHELL_TIMEOUT = 15


class AdbManager:
    """Manages ADB interactions with connected Android devices."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._adb_path: Optional[str] = None
        self._adb_version: str = ""
        self._log = log_callback or (lambda msg: None)

    # ── ADB Discovery ──────────────────────────────────────────────

    def find_adb(self) -> Tuple[bool, str]:
        """Locate the ADB executable on the system.

        Returns:
            (found: bool, path_or_error: str)
        """
        # Check common locations
        candidates = [
            shutil.which("adb"),
            shutil.which("adb.exe"),
        ]

        # Also check alongside this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        for d in [parent_dir, script_dir]:
            candidates.append(os.path.join(d, "adb.exe"))
            candidates.append(os.path.join(d, "platform-tools", "adb.exe"))

        # Check standard install locations
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"))

        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        candidates.append(os.path.join(program_files, "platform-tools", "adb.exe"))

        for c_drive_path in ["C:\\platform-tools\\adb.exe", "C:\\adb\\adb.exe"]:
            candidates.append(c_drive_path)

        # Check Desktop folders (e.g. scrcpy or platform-tools)
        desktop_dir = os.path.dirname(parent_dir)
        if os.path.isdir(desktop_dir):
            try:
                for entry in os.listdir(desktop_dir):
                    sub = os.path.join(desktop_dir, entry)
                    if os.path.isdir(sub) and ("scrcpy" in entry.lower() or "platform" in entry.lower() or "adb" in entry.lower()):
                        candidates.append(os.path.join(sub, "adb.exe"))
            except OSError:
                pass

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                self._adb_path = candidate
                self._log(f"Found ADB at: {candidate}")
                # Get version
                ver = self._get_adb_version()
                if ver:
                    self._adb_version = ver
                    self._log(f"ADB version: {ver}")
                return True, candidate

        msg = (
            "ADB not found. Install Android SDK Platform Tools from:\n"
            "https://developer.android.com/tools/releases/platform-tools\n"
            "and add the directory to your system PATH."
        )
        self._log(f"ERROR: {msg}")
        return False, msg

    def _get_adb_version(self) -> str:
        """Get the ADB version string."""
        try:
            result = self._run_adb(["version"], timeout=5)
            if result and result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "Android Debug Bridge version" in line:
                        return line.strip()
                    if "Version" in line:
                        return line.strip()
                return result.stdout.splitlines()[0].strip() if result.stdout.strip() else ""
        except Exception as e:
            logger.debug(f"Could not get ADB version: {e}")
        return ""

    @property
    def adb_path(self) -> Optional[str]:
        return self._adb_path

    @property
    def adb_version(self) -> str:
        return self._adb_version

    @property
    def is_available(self) -> bool:
        if self._adb_path is None:
            self.find_adb()
        return self._adb_path is not None

    # ── Command Execution ──────────────────────────────────────────

    def _run_adb(
        self,
        args: List[str],
        timeout: int = DEFAULT_TIMEOUT,
        serial: Optional[str] = None,
    ) -> Optional[subprocess.CompletedProcess]:
        """Execute an ADB command with timeout and error handling.

        Args:
            args: ADB arguments (without the 'adb' prefix).
            timeout: Command timeout in seconds.
            serial: Target device serial (for multi-device scenarios).

        Returns:
            CompletedProcess or None on failure.
        """
        if not self._adb_path:
            self._log("ERROR: ADB not available")
            return None

        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)

        cmd_str = " ".join(cmd)
        logger.debug(f"Running: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode != 0 and result.stderr.strip():
                logger.debug(f"ADB stderr: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            self._log(f"TIMEOUT: Command timed out after {timeout}s: {cmd_str}")
            logger.warning(f"Command timed out: {cmd_str}")
            return None
        except FileNotFoundError:
            self._log(f"ERROR: ADB executable not found at {self._adb_path}")
            self._adb_path = None
            return None
        except OSError as e:
            self._log(f"ERROR: OS error running ADB: {e}")
            logger.error(f"OS error: {e}")
            return None

    def _shell(self, command: str, timeout: int = SHELL_TIMEOUT, serial: Optional[str] = None) -> Optional[str]:
        """Run an ADB shell command and return stdout, or None on failure."""
        result = self._run_adb(["shell", command], timeout=timeout, serial=serial)
        if result and result.returncode == 0:
            return result.stdout.strip()
        return None

    # ── Device Detection ───────────────────────────────────────────

    def detect_devices(self) -> List[dict]:
        """Detect all connected ADB devices.

        Returns:
            List of dicts with keys: serial, state, usb, product, model, device, transport_id
        """
        if not self.is_available:
            return []

        result = self._run_adb(["devices", "-l"], timeout=DEFAULT_TIMEOUT)
        if not result or result.returncode != 0:
            self._log("Could not list ADB devices")
            return []

        devices = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of") or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            state = parts[1]

            info = {"serial": serial, "state": state}

            # Parse key:value pairs from extended output
            for part in parts[2:]:
                if ":" in part:
                    key, _, value = part.partition(":")
                    info[key] = value

            devices.append(info)

        return devices

    def get_devices(self) -> List[DeviceInfo]:
        """Get structured DeviceInfo objects for all connected devices."""
        raw_list = self.detect_devices()
        results = []
        state_map = {
            "device": DeviceState.CONNECTED,
            "unauthorized": DeviceState.UNAUTHORIZED,
            "offline": DeviceState.OFFLINE,
            "bootloader": DeviceState.BOOTLOADER,
            "recovery": DeviceState.RECOVERY,
            "sideload": DeviceState.SIDELOAD,
        }
        for d in raw_list:
            s = state_map.get(d.get("state", "").lower(), DeviceState.UNKNOWN)
            results.append(DeviceInfo(serial=d.get("serial", ""), state=s))
        return results

    def get_device_state(self, serial: Optional[str] = None) -> DeviceState:
        """Get the connection state of a specific device."""
        devices = self.detect_devices()
        if not devices:
            return DeviceState.UNAVAILABLE

        target = None
        if serial:
            for d in devices:
                if d["serial"] == serial:
                    target = d
                    break
        else:
            target = devices[0]

        if not target:
            return DeviceState.UNAVAILABLE

        state_str = target.get("state", "").lower()
        state_map = {
            "device": DeviceState.CONNECTED,
            "unauthorized": DeviceState.UNAUTHORIZED,
            "offline": DeviceState.OFFLINE,
            "bootloader": DeviceState.BOOTLOADER,
            "recovery": DeviceState.RECOVERY,
            "sideload": DeviceState.SIDELOAD,
        }
        return state_map.get(state_str, DeviceState.UNKNOWN)

    # ── Property Queries ───────────────────────────────────────────

    def _getprop(self, prop: str, serial: Optional[str] = None) -> str:
        """Get an Android system property."""
        val = self._shell(f"getprop {prop}", serial=serial)
        return val if val else ""

    def get_model(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.product.model", serial)

    def get_android_version(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.build.version.release", serial)

    def get_sdk_version(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.build.version.sdk", serial)

    def get_manufacturer(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.product.manufacturer", serial)

    def get_brand(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.product.brand", serial)

    def get_device_name(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.product.device", serial)

    def get_product(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.product.name", serial)

    def get_build_fingerprint(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.build.fingerprint", serial)

    def get_build_number(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.build.display.id", serial)

    def get_security_patch(self, serial: Optional[str] = None) -> str:
        return self._getprop("ro.build.version.security_patch", serial)

    def get_boot_completed(self, serial: Optional[str] = None) -> BootState:
        """Check whether the device has finished booting."""
        val = self._getprop("sys.boot_completed", serial)
        if val == "1":
            return BootState.BOOTED
        elif val == "0":
            return BootState.BOOTING
        return BootState.UNKNOWN

    def get_screen_size(self, serial: Optional[str] = None) -> str:
        """Get the device screen resolution."""
        result = self._shell("wm size", serial=serial)
        if result:
            match = re.search(r"(\d+x\d+)", result)
            if match:
                return match.group(1)
        return ""

    def get_screen_density(self, serial: Optional[str] = None) -> str:
        """Get the device screen density."""
        result = self._shell("wm density", serial=serial)
        if result:
            match = re.search(r"(\d+)", result)
            if match:
                return match.group(1) + " dpi"
        return ""

    # ── Storage ────────────────────────────────────────────────────

    def get_storage_info(self, serial: Optional[str] = None) -> List[StorageInfo]:
        """Get storage partition information using df -h."""
        result = self._shell("df -h", timeout=SHELL_TIMEOUT, serial=serial)
        if not result:
            return []

        partitions = []
        for line in result.splitlines():
            # Skip header
            if line.startswith("Filesystem") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 6:
                info = StorageInfo(
                    partition=parts[0],
                    total=parts[1],
                    used=parts[2],
                    available=parts[3],
                    use_percent=parts[4],
                    mount_point=parts[5],
                )
                partitions.append(info)

        return partitions

    def get_data_storage(self, serial: Optional[str] = None) -> Optional[StorageInfo]:
        """Get storage info specifically for /data partition."""
        result = self._shell("df -h /data", timeout=SHELL_TIMEOUT, serial=serial)
        if not result:
            return None

        for line in result.splitlines():
            if line.startswith("Filesystem") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 6:
                return StorageInfo(
                    partition=parts[0],
                    total=parts[1],
                    used=parts[2],
                    available=parts[3],
                    use_percent=parts[4],
                    mount_point=parts[5],
                )
        return None

    def check_sdcard(self, serial: Optional[str] = None) -> Tuple[bool, Optional[StorageInfo]]:
        """Check whether an SD card is mounted."""
        # Check common SD card mount points
        for path in ["/storage/sdcard1", "/mnt/media_rw/", "/storage/"]:
            result = self._shell(f"df -h {path}", timeout=SHELL_TIMEOUT, serial=serial)
            if result:
                for line in result.splitlines():
                    if "sdcard" in line.lower() or "extsd" in line.lower() or "media_rw" in line.lower():
                        parts = line.split()
                        if len(parts) >= 6:
                            return True, StorageInfo(
                                partition=parts[0],
                                total=parts[1],
                                used=parts[2],
                                available=parts[3],
                                use_percent=parts[4],
                                mount_point=parts[5],
                            )

        # Also check mount command
        result = self._shell("mount | grep -i sdcard", serial=serial)
        if result and result.strip():
            return True, None

        return False, None

    # ── Full Device Scan ───────────────────────────────────────────

    def full_scan(self) -> DeviceInfo:
        """Perform a complete device scan and return all gathered information.

        This is the main entry point for the dashboard refresh.
        """
        info = DeviceInfo()

        # ADB availability
        if not self.is_available:
            found, path_or_err = self.find_adb()
            if not found:
                info.state = DeviceState.UNAVAILABLE
                self._log("ADB is not available. Cannot scan for devices.")
                return info

        info.adb_path = self._adb_path or ""
        info.adb_version = self._adb_version

        # Detect devices
        self._log("Scanning for devices...")
        devices = self.detect_devices()

        if not devices:
            info.state = DeviceState.UNAVAILABLE
            self._log("No ADB devices detected. Check USB connection and drivers.")
            return info

        # Use first device
        dev = devices[0]
        info.serial = dev.get("serial", "")
        info.usb_port = dev.get("usb", "")
        info.transport_id = dev.get("transport_id", "")

        state_str = dev.get("state", "").lower()
        state_map = {
            "device": DeviceState.CONNECTED,
            "unauthorized": DeviceState.UNAUTHORIZED,
            "offline": DeviceState.OFFLINE,
            "bootloader": DeviceState.BOOTLOADER,
            "recovery": DeviceState.RECOVERY,
            "sideload": DeviceState.SIDELOAD,
        }
        info.state = state_map.get(state_str, DeviceState.UNKNOWN)

        self._log(f"Device found: {info.serial} — State: {info.state.value}")

        # If not authorized, we can't query properties
        if not info.is_authorized():
            self._log(
                "Device is not authorized. Cannot query device properties.\n"
                "To authorize: enable USB debugging and approve this PC on the phone screen."
            )
            # Fill in what we can from device list
            info.model = dev.get("model", "")
            info.device_name = dev.get("device", "")
            info.product = dev.get("product", "")
            return info

        # Query all properties
        self._log("Querying device properties...")
        info.model = self.get_model(info.serial) or dev.get("model", "")
        info.device_name = self.get_device_name(info.serial) or dev.get("device", "")
        info.product = self.get_product(info.serial) or dev.get("product", "")
        info.manufacturer = self.get_manufacturer(info.serial)
        info.brand = self.get_brand(info.serial)
        info.android_version = self.get_android_version(info.serial)
        info.sdk_version = self.get_sdk_version(info.serial)
        info.build_fingerprint = self.get_build_fingerprint(info.serial)
        info.build_number = self.get_build_number(info.serial)
        info.security_patch = self.get_security_patch(info.serial)
        info.boot_state = self.get_boot_completed(info.serial)
        info.screen_size = self.get_screen_size(info.serial)
        info.screen_density = self.get_screen_density(info.serial)

        self._log(f"Model: {info.model}")
        self._log(f"Android: {info.android_version} (SDK {info.sdk_version})")
        self._log(f"Boot state: {info.boot_state.value}")
        self._log(f"Build: {info.build_number}")

        # Storage
        self._log("Checking storage...")
        info.data_storage = self.get_data_storage(info.serial)
        if info.data_storage:
            self._log(
                f"Data partition: {info.data_storage.total} total, "
                f"{info.data_storage.used} used, "
                f"{info.data_storage.available} available ({info.data_storage.use_percent})"
            )

        sdcard_found, sdcard_info = self.check_sdcard(info.serial)
        info.sdcard_mounted = sdcard_found
        info.sdcard_storage = sdcard_info
        if sdcard_found:
            self._log("SD card: Mounted")
            if sdcard_info:
                self._log(f"SD card: {sdcard_info.total} total, {sdcard_info.available} available")
        else:
            self._log("SD card: Not detected")

        info.storage_info_list = self.get_storage_info(info.serial)

        # Check mirroring capability
        info.can_mirror = info.is_authorized() and info.boot_state == BootState.BOOTED

        # Check scrcpy availability (set externally by ScrcpyManager)
        # info.scrcpy_available is set by the caller

        self._log("Scan complete.")
        return info

    def start_adb_server(self) -> bool:
        """Start the ADB server if not running."""
        self._log("Starting ADB server...")
        result = self._run_adb(["start-server"], timeout=DEFAULT_TIMEOUT)
        if result and result.returncode == 0:
            self._log("ADB server started")
            return True
        self._log("Failed to start ADB server")
        return False

    def kill_adb_server(self) -> bool:
        """Kill the ADB server."""
        self._log("Stopping ADB server...")
        result = self._run_adb(["kill-server"], timeout=DEFAULT_TIMEOUT)
        if result and result.returncode == 0:
            self._log("ADB server stopped")
            return True
        self._log("Failed to stop ADB server")
        return False
