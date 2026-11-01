# Galaxy S9+ Recovery & HDMI Control Suite 📱🖥️

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg?style=flat&logo=qt&logoColor=white)](https://wiki.qt.io/Qt_for_Python)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-58%20passed-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078D6.svg?logo=windows)](https://microsoft.com)

A comprehensive, production-ready desktop tool suite engineered specifically for **diagnosing, displaying, controlling, and recovering data from a Samsung Galaxy S9+ (SM-G965F / SM-G965U)** with a black, broken, or unresponsive internal display.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture & Two Operational Modes](#-architecture--two-operational-modes)
- [Key Features](#-key-features)
- [Hardware Setup & Video Ingestion Chain](#-hardware-setup--video-ingestion-chain)
- [Touch Control vs. Video Capture](#-touch-control-vs-video-capture)
- [Samsung DeX vs. Screen Mirroring](#-samsung-dex-vs-screen-mirroring)
- [Prerequisites](#-prerequisites)
- [Installation & Quick Start](#-installation--quick-start)
- [Project Structure](#-project-structure)
- [Running Tests](#-running-tests)
- [Building Standalone Executables](#-building-standalone-executables)
- [Troubleshooting Matrix](#-troubleshooting-matrix)
- [Contributing & License](#-license)

---

## 🌟 Overview

When a Samsung Galaxy S9+ suffers OLED panel failure (black screen, violent flickering, or dead digitizer), the phone's hardware remains fully functional. However, standard recovery workflows are hindered by:
1. **Unidirectional HDMI**: Video output over USB-C (DisplayPort Alt Mode) does not natively relay touch/mouse events from a PC.
2. **Unauthorized ADB**: Developer Options / USB Debugging cannot be easily enabled or accepted without display confirmation.
3. **Automatic DeX Activation**: Connecting an external display often forces Samsung DeX instead of phone screen mirroring.

This repository provides **two specialized desktop applications** to handle every scenario—from zero-debug hardware capture to complete ADB-backed remote control and forensic data retrieval.

---

## ⚙️ Architecture & Two Operational Modes

| Capability | **Mode 1: HDMI Viewer & Controller** (`main_hdmi_viewer.py`) | **Mode 2: Recovery Console** (`main.py`) |
| :--- | :--- | :--- |
| **Primary Use Case** | Broken screen with zero ADB authorization; low-latency HDMI capture via UVC capture card. | Authorized ADB debugging; full storage diagnostics and scrcpy screen mirroring. |
| **Display Pipeline** | Direct hardware video ingest from USB UVC capture cards (`PySide6.QtMultimedia`). | `scrcpy` video stream over USB cable or ADB Wi-Fi. |
| **Control Method** | Ingest window mouse-to-ADB coordinate mapper (`input tap`, `input swipe`) + quick action bar. | Full scrcpy keyboard & mouse virtualization. |
| **Hardware Needed** | USB-C Multiport Hub + HDMI cable + USB Capture Dongle. | Standard USB-C to USB-A/C data cable. |
| **DeX Handling** | Dedicated DeX/Mirror toggle triggers + safe broadcast dispatches. | Step-by-step external display and recovery walkthroughs. |

---

## 🚀 Key Features

### 1. S9+ HDMI Viewer & Controller (`main_hdmi_viewer.py`)
- **Direct UVC Video Stream**: Ingests real-time video up to 1080p60 from any standard UVC HDMI capture device.
- **Dynamic Camera Switching**: Auto-detects connected capture cards and video sources with resolution selection.
- **Smart ADB Coordinate Mapping**: Translates clicks and swipes on the capture window directly into touch coordinates on the S9+ (when ADB is active).
- **Virtual Quick Action Bar**: Emulates Power, Screen Wake, Swipe to Unlock, Home, Back, Recents, and Volume +/-.
- **DeX Management**: One-click broadcast dispatch to switch One UI between Samsung DeX and phone screen mirroring.
- **Control-Only scrcpy Integration**: Spawns low-latency keyboard/mouse forwarding (`scrcpy --no-video --no-audio`) while keeping the crisp HDMI feed on screen.

### 2. Galaxy S9+ Recovery Console (`main.py`)
- **Device Health Dashboard**: Real-time ADB connection status, model number, serial, battery level, Android version, and authorization check.
- **Storage Diagnostics**: Live reporting of `/data`, `/system`, internal storage usage, and MicroSD card detection.
- **Connection Diagnostics**: Step-by-step diagnostic tree for driver errors, unauthorized states, and offline devices.
- **Log Streamer**: Color-coded real-time diagnostic console with export and clipboard utilities.

---

## 🔌 Hardware Setup & Video Ingestion Chain

### The Physical Video Chain
```text
[ Samsung Galaxy S9+ (SM-G965F) ]
            │ (USB-C DisplayPort Alternate Mode)
            ▼
[ USB-C Multiport Hub (with HDMI & USB-A) ] ◄── [ Wall Fast Charger plugged into Hub PD Port ]
            │ (Standard HDMI Cable)
            ▼
[ USB UVC HDMI Capture Card ] (e.g. Cam Link, Elgato, generic USB 3.0/2.0 capture dongle)
            │ (USB 3.0 / USB-A)
            ▼
[ Windows PC USB Port ] ──────────────► [ S9+ HDMI Viewer / Controller Window ]
```

### Why a Standard USB Cable Cannot Ingest HDMI Video
- **Host vs. Sink**: Windows PC USB ports are USB Hosts designed for data transmission (MTP, ADB), not uncompressed raw video ingestion.
- **DisplayPort Alt Mode**: The Galaxy S9+'s USB-C port outputs video using dedicated DisplayPort Alt Mode pins. A standard USB-C to USB-A cable does not connect or convert these pins.
- **The Capture Card**: A UVC (USB Video Class) HDMI capture card digitizes the phone's HDMI video signal into a video stream that Windows reads like a standard webcam.

---

## 🖱️ Touch Control vs. Video Capture

> [!IMPORTANT]
> **HDMI Video is strictly unidirectional (Phone → PC).**
> Viewing video on your PC screen does not automatically forward mouse clicks to the phone unless bridged by ADB or direct hardware input.

### When ADB is **NOT** Authorized:
- **Status Indicator**: `🔴 Touch Control: DISABLED (No Authorized ADB)`
- The HDMI stream displays the phone screen cleanly.
- **Zero-ADB Control Fix**: Plug a **standard wired or wireless USB mouse** directly into an available USB-A port on the **USB-C Multiport Hub**. An on-screen mouse pointer will instantly appear on the phone display, enabling you to unlock your phone and navigate settings with **zero software setup**.

### When ADB **IS** Authorized:
- **Status Indicator**: `🟢 Touch Control: ACTIVE (ADB Authorized)`
- Clicks on the video window are mapped to the phone's screen resolution (`input tap X Y`).
- Drags and swipes are translated to smooth gestures (`input swipe X1 Y1 X2 Y2`).
- The quick action buttons and keyboard shortcuts become fully operational.

---

## 🖥️ Samsung DeX vs. Screen Mirroring

When plugged into an external HDMI source, Samsung Galaxy S9+ running One UI (Android 10) frequently launches **Samsung DeX desktop** by default.

To switch to **phone screen mirroring**:
1. **Physical Mouse Method**: Move the mouse connected to the hub to the bottom-right corner of the screen, open Notifications, select the Samsung DeX notification, and click **"Switch to screen mirroring"**.
2. **Keyboard Shortcut**: Press <kbd>Win</kbd> + <kbd>W</kbd> on a keyboard connected to the USB-C hub.
3. **Automated ADB Broadcast**: In the app's DeX tab, click **"Request Switch to Mirroring via ADB"**, which executes:
   ```bash
   adb shell am broadcast -a com.samsung.android.desktopmode.action.STOP_DESKTOP_MODE
   ```

---

## 📦 Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit).
2. **Python**: Python 3.10 or higher.
3. **Android Platform Tools (ADB)**:
   - Download [SDK Platform-Tools for Windows](https://developer.android.com/tools/releases/platform-tools).
   - Extract and add the directory to your system `PATH`, or place `adb.exe` in the application root.
4. **scrcpy** (optional, recommended for low-latency mirroring):
   - Download the latest Windows release from [scrcpy releases](https://github.com/Genymobile/scrcpy/releases).
   - Extract and add to system `PATH` or place in the app folder.
5. **Samsung Android USB Driver**:
   - Download from [Samsung Developers](https://developer.samsung.com/android-usb-driver) or via Samsung Smart Switch.

---

## 🚀 Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/s9-plus-recovery-suite.git
cd s9-plus-recovery-suite
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Desired Tool

#### Launch HDMI Viewer & Controller:
```bash
python main_hdmi_viewer.py
# or double-click:
launch_hdmi_viewer.bat
```

#### Launch Recovery Console:
```bash
python main.py
# or double-click:
launch.bat
```

#### One-Click Auto Mirror:
```bash
auto_mirror.bat
```

---

## 📁 Project Structure

```text
s9+/
├── core/                        # Core backend management services
│   ├── adb_controller.py        # Touch & swipe input coordinate translator
│   ├── adb_manager.py           # ADB process manager & device detection
│   ├── device_info.py           # Device properties, specs & partition parser
│   ├── dex_mode_manager.py      # Samsung DeX mode detection and broadcast handler
│   ├── scrcpy_manager.py        # scrcpy process launcher (full and control-only)
│   ├── usb_detector.py          # Windows USB device listener and port checker
│   └── uvc_capture.py           # PySide6 QtMultimedia UVC camera capture engine
├── ui/                          # GUI components built on PySide6 / Qt6
│   ├── app.py                   # Main window for Recovery Console
│   ├── hdmi_viewer_window.py    # Main window for HDMI Viewer & Controller
│   ├── video_display_widget.py  # Aspect-ratio preserving video renderer with touch mapper
│   ├── dashboard_page.py        # Real-time connection & health dashboard
│   ├── mirror_page.py           # scrcpy session controls & options
│   ├── storage_page.py          # Storage partitions, SD card & battery stats
│   ├── dex_guide_page.py        # Visual DeX vs mirror instruction guide
│   ├── troubleshoot_page.py     # Interactive troubleshooting assistant
│   ├── widgets.py               # Reusable styled UI widgets (cards, meters, badges)
│   └── theme.py                 # Modern dark theme palette & stylesheets
├── tests/                       # Complete automated unit test suite
│   ├── test_adb_controller.py
│   ├── test_adb_manager.py
│   ├── test_device_info.py
│   ├── test_dex_mode_manager.py
│   ├── test_usb_detector.py
│   └── test_uvc_capture.py
├── auto_mirror.bat              # Script to immediately launch scrcpy mirroring
├── build.py                     # PyInstaller build script for Recovery Console
├── build_hdmi_viewer.py         # PyInstaller build script for HDMI Viewer
├── feasibility_report.md        # Technical analysis of S9+ video & control methods
├── launch.bat                   # Convenient Windows launcher for Recovery Console
├── launch_hdmi_viewer.bat       # Convenient Windows launcher for HDMI Viewer
├── main.py                      # Recovery Console entry point
├── main_hdmi_viewer.py          # HDMI Viewer & Controller entry point
├── requirements.txt             # Project dependencies
└── README.md                    # Main suite documentation
```

---

## 🧪 Running Tests

The project includes an extensive test suite with 100% mocked hardware dependencies:

```bash
pytest -v
```

Output:
```text
tests/test_adb_controller.py ......                                      [ 10%]
tests/test_adb_manager.py .......................                        [ 50%]
tests/test_device_info.py ................                               [ 77%]
tests/test_dex_mode_manager.py ...                                       [ 82%]
tests/test_usb_detector.py ...                                           [ 87%]
tests/test_uvc_capture.py .......                                        [100%]
============================= 58 passed in 0.38s ==============================
```

---

## 🔨 Building Standalone Executables

Compile standalone Windows executables without requiring a Python environment on target machines:

### Build Recovery Console:
```bash
python build.py
```
Output: `dist/GalaxyS9RecoveryConsole/GalaxyS9RecoveryConsole.exe`

### Build HDMI Viewer & Controller:
```bash
python build_hdmi_viewer.py
```
Output: `dist/S9_HDMI_Viewer/S9_HDMI_Viewer.exe`

---

## 🔍 Troubleshooting Matrix

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **"No UVC Video Device Found"** | Capture card not plugged in or driver missing. | Plug the USB capture dongle into a USB 3.0 port. Check Windows Device Manager under "Cameras". |
| **Black screen in HDMI Viewer** | S9+ screen timed out or hub lacks power. | Plug fast charger into hub PD port. Press the Power button on the phone or in the action bar. |
| **Phone boots to DeX instead of phone mirror** | Samsung DeX auto-start behavior. | Use a USB mouse plugged into hub to switch to mirror in notifications, or click "Switch to Mirroring" in the app. |
| **"Device Unauthorized"** | ADB RSA key prompt hasn't been accepted on phone. | Use HDMI view + mouse plugged into hub to tap "Allow" on the USB Debugging prompt. |
| **Clicks on HDMI window do nothing** | ADB is not active or unauthorized. | Touch control requires authorized ADB. Without ADB, connect a USB mouse directly to the hub. |
| **"ADB not found"** | ADB binaries not in PATH or local directory. | Download Android Platform Tools and place `adb.exe` in the application directory. |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
