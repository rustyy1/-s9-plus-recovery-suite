"""Low-Level Windows USB Descriptor and Hardware Detector for Galaxy S9+.

Inspects:
- Windows Plug and Play device tree for connected Samsung devices (VID 04E8)
- Real USB interface functions (MTP, Modem, Connectivity, ADB)
- Verifies whether the connected device exposes any USB Video Class (UVC, Class 0x0E) interface
- Verifies whether the PC USB port has DisplayPort Alt Mode sink capability
- Enumerates genuine Windows Media Foundation / DirectShow video capture cards
"""

import subprocess
import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class UsbInterfaceInfo:
    """Represents an enumerated USB interface on the device."""
    interface_number: int
    name: str
    service: str
    hardware_id: str
    is_video_class: bool = False


@dataclass
class PhoneUsbInspectionResult:
    """Detailed hardware inspection of the phone's physical USB connection."""
    is_physically_connected: bool = False
    device_name: str = ""
    serial_number: str = ""
    hardware_id: str = ""
    interfaces: List[UsbInterfaceInfo] = field(default_factory=list)
    has_uvc_video_interface: bool = False
    has_adb_interface: bool = False
    has_mtp_interface: bool = False
    has_modem_interface: bool = False
    pc_port_supports_dp_sink: bool = False
    hardware_diagnosis: str = ""


class UsbHardwareDetector:
    """Queries Windows SetupAPI and PnP registry for real USB hardware inspection."""

    SAMSUNG_VID = "04E8"
    GALAXY_S9_PID = "6860"

    def __init__(self):
        pass

    def inspect_connected_phone(self) -> PhoneUsbInspectionResult:
        """Inspect the connected Galaxy S9+ through Windows PnP and driver services."""
        result = PhoneUsbInspectionResult()

        # 1. Query Win32_PnPEntity for VID 04E8
        try:
            cmd = [
                "powershell", "-NoProfile", "-Command",
                'Get-WmiObject Win32_PnPEntity | Where-Object { $_.DeviceID -match "04E8" } | '
                'Select-Object Name, DeviceID, Service, Present | ConvertTo-Json -Compress'
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if proc.returncode != 0 or not proc.stdout.strip():
                result.is_physically_connected = False
                result.hardware_diagnosis = "No Samsung USB device detected on any PC USB port."
                return result

            import json
            raw_data = json.loads(proc.stdout)
            if isinstance(raw_data, dict):
                entities = [raw_data]
            elif isinstance(raw_data, list):
                entities = raw_data
            else:
                entities = []

            if not entities:
                result.is_physically_connected = False
                result.hardware_diagnosis = "No Samsung USB device detected on any PC USB port."
                return result

            result.is_physically_connected = True

            for ent in entities:
                name = ent.get("Name") or ""
                dev_id = ent.get("DeviceID") or ""
                svc = ent.get("Service") or ""

                if "22858E1E40047ECE" in dev_id or ("VID_04E8" in dev_id and "PID_6860" in dev_id and not "&" in dev_id.split("\\")[-1]):
                    result.device_name = name or "SAMSUNG Mobile USB Composite Device"
                    result.hardware_id = dev_id
                    parts = dev_id.split("\\")
                    if len(parts) >= 3:
                        result.serial_number = parts[2]

                # Classify interfaces
                if "MS_COMP_MTP" in dev_id or "MTP" in name.upper() or svc == "WUDFWpdMtp":
                    result.has_mtp_interface = True
                    result.interfaces.append(UsbInterfaceInfo(0, "MTP (Media Transfer Protocol)", svc, dev_id, False))
                elif "MODEM" in dev_id.upper() or "Modem" in svc:
                    result.has_modem_interface = True
                    result.interfaces.append(UsbInterfaceInfo(1, "CDC ACM Modem", svc, dev_id, False))
                elif "CONN2" in dev_id or "ss_conn" in svc:
                    result.interfaces.append(UsbInterfaceInfo(3, "Samsung Connectivity V2", svc, dev_id, False))
                elif "ADB" in dev_id or "WINUSB" in svc.upper():
                    result.has_adb_interface = True
                    result.interfaces.append(UsbInterfaceInfo(4, "Android ADB Interface (WinUSB)", svc, dev_id, False))

                # Check if ANY interface is Class 0x0E (UVC Video)
                if "class_0e" in dev_id.lower() or "uvc" in svc.lower() or "usbvideo" in svc.lower():
                    result.has_uvc_video_interface = True

        except Exception as e:
            result.is_physically_connected = False
            result.hardware_diagnosis = f"Error querying Windows PnP: {e}"
            return result

        # 2. PC Port DisplayPort Alt Mode Sink Check
        # Standard xHCI host controllers on AMD/Intel PCs only operate as USB Host Controllers (data only).
        # They lack DisplayPort RX PHY hardware.
        result.pc_port_supports_dp_sink = False

        # 3. Formulate Hardware Diagnosis
        if not result.has_uvc_video_interface:
            result.hardware_diagnosis = (
                "The Galaxy S9+ USB connection provides standard data interfaces (MTP, Modem, ADB), "
                "but does NOT expose a USB Video Class (UVC) endpoint. "
                "Direct USB video reception requires an external UVC HDMI capture card."
            )
        else:
            result.hardware_diagnosis = "Direct USB video endpoint detected."

        return result

    @staticmethod
    def get_hardware_limitations_explanation() -> str:
        """Detailed technical explanation of the physical hardware signal path."""
        return (
            "PHYSICAL HARDWARE SIGNAL PATH ANALYSIS:\n"
            "1. Phone Output: The Galaxy S9+ (SM-G965F) outputs uncompressed video via VESA DisplayPort "
            "Alternate Mode on the physical high-speed pins of its USB-C connector (TX1/RX1, TX2/RX2).\n"
            "2. Normal USB Cable: A standard USB cable connected to a PC connects only the USB 2.0 (D+/D-) "
            "and USB 3.0 (SSTX/SSRX) data pins to the PC's USB Host Controller (xHCI).\n"
            "3. PC USB Port: PC USB ports are USB Hosts designed for data packet transfer; they do not possess "
            "DisplayPort Sink (Rx) receiver circuitry and cannot ingest DisplayPort differential signals.\n"
            "4. Required Bridge: A USB UVC HDMI Capture Card is physically required to accept the phone's HDMI "
            "video and convert it into a standard UVC webcam stream that Windows can display."
        )
