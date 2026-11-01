"""Device information models for Galaxy S9+ Recovery Console."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceState(Enum):
    """Possible device connection states."""
    CONNECTED = "Connected"
    UNAUTHORIZED = "Unauthorized"
    OFFLINE = "Offline"
    UNAVAILABLE = "Unavailable"
    UNKNOWN = "Unknown"
    BOOTLOADER = "Bootloader"
    RECOVERY = "Recovery"
    SIDELOAD = "Sideload"
    DOWNLOAD_MODE = "Download Mode"


class BootState(Enum):
    """Device boot states."""
    BOOTED = "Fully Booted"
    BOOTING = "Booting"
    UNKNOWN = "Unknown"
    NOT_AVAILABLE = "Not Available"


@dataclass
class StorageInfo:
    """Storage partition information."""
    partition: str = ""
    total: str = ""
    used: str = ""
    available: str = ""
    use_percent: str = ""
    mount_point: str = ""


@dataclass
class DeviceInfo:
    """Complete device information gathered from ADB."""
    # Connection
    state: DeviceState = DeviceState.UNAVAILABLE
    serial: str = ""
    transport_id: str = ""
    usb_port: str = ""

    # Identity
    model: str = ""
    device_name: str = ""
    product: str = ""
    manufacturer: str = ""
    brand: str = ""
    build_fingerprint: str = ""

    # Software
    android_version: str = ""
    sdk_version: str = ""
    security_patch: str = ""
    build_number: str = ""
    one_ui_version: str = ""

    # Boot
    boot_state: BootState = BootState.UNKNOWN
    uptime: str = ""

    # Display
    screen_size: str = ""
    screen_density: str = ""

    # Storage
    data_storage: Optional[StorageInfo] = None
    sdcard_storage: Optional[StorageInfo] = None
    sdcard_mounted: Optional[bool] = None
    storage_info_list: list = field(default_factory=list)

    # ADB
    adb_version: str = ""
    adb_path: str = ""
    usb_debugging_enabled: Optional[bool] = None

    # Capabilities
    can_mirror: bool = False
    scrcpy_available: bool = False
    scrcpy_path: str = ""

    def is_authorized(self) -> bool:
        """Check if device has an authorized ADB connection."""
        return self.state == DeviceState.CONNECTED

    def is_any_connection(self) -> bool:
        """Check if device is detected at all (even unauthorized)."""
        return self.state not in (DeviceState.UNAVAILABLE, DeviceState.UNKNOWN)

    def get_status_summary(self) -> str:
        """Return a human-readable status summary."""
        if self.state == DeviceState.CONNECTED:
            model_str = self.model or "Unknown device"
            ver_str = f" (Android {self.android_version})" if self.android_version else ""
            return f"✓ {model_str}{ver_str} — Authorized"
        elif self.state == DeviceState.UNAUTHORIZED:
            return "⚠ Device detected but NOT authorized — approve USB debugging on the phone"
        elif self.state == DeviceState.OFFLINE:
            return "⚠ Device detected but OFFLINE — check connection"
        elif self.state == DeviceState.BOOTLOADER:
            return "⚠ Device is in BOOTLOADER mode — limited diagnostics available"
        elif self.state == DeviceState.RECOVERY:
            return "⚠ Device is in RECOVERY mode — limited diagnostics available"
        elif self.state == DeviceState.SIDELOAD:
            return "⚠ Device is in SIDELOAD mode"
        elif self.state == DeviceState.DOWNLOAD_MODE:
            return "⚠ Device appears to be in DOWNLOAD (Odin) mode — ADB unavailable"
        else:
            return "✗ No device detected"

    def get_mirror_status(self) -> str:
        """Return a description of mirroring availability."""
        if not self.scrcpy_available:
            return "scrcpy not found — install from https://github.com/Genymobile/scrcpy/releases"
        if not self.is_authorized():
            return (
                "Cannot mirror: ADB is not authorized. "
                "USB debugging must be enabled and your PC must be approved on the device."
            )
        if self.boot_state != BootState.BOOTED:
            return "Cannot mirror: Device does not appear to be fully booted."
        return "Ready — click 'Start Mirroring' to launch scrcpy"
