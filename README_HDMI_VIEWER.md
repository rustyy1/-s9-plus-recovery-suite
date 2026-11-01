# S9+ HDMI Viewer & Controller

A dedicated Windows desktop utility for viewing and controlling a **Samsung Galaxy S9+ (SM-G965F, Exynos 9810)** with an unusable built-in display via **USB UVC HDMI Capture** and optional **ADB Input Control**.

---

## 1. Physical Hardware Connection & Why It Is Required

### The Physical Hardware Chain
```
[ Galaxy S9+ (SM-G965F) ]
            │ (USB-C DisplayPort Alternate Mode)
            ▼
[ USB-C Multiport Hub with HDMI ] ◄── [ Wall Fast Charger plugged into Hub PD Port ]
            │ (Standard HDMI Cable)
            ▼
[ USB UVC HDMI Video Capture Card ] (e.g., Cam Link, USB 3.0/2.0 HDMI Capture Dongle)
            │ (USB Male Type-A / Type-C)
            ▼
[ Windows PC USB Port ] ────────────► [ S9+ HDMI Viewer & Controller Window ]
```

### Why a Standard USB Cable Cannot Ingest HDMI Video
- **Host vs. Sink Architecture:** Windows PC USB ports are **USB Hosts** designed to receive data packets (MTP, ADB), not uncompressed video signals.
- **DisplayPort Alt Mode:** The Galaxy S9+'s USB-C port outputs video via DisplayPort Alt Mode pins. A standard USB-C to USB-A cable does not connect or convert these video pins.
- **The Capture Card Role:** The **USB UVC HDMI Capture Card** acts as the hardware bridge. It digitizes the HDMI output from the phone and presents it to Windows as a standard **UVC (USB Video Class)** webcam device via Windows Media Foundation or DirectShow.

---

## 2. Touch Control vs. Video Capture (Strict Separation)

> [!IMPORTANT]
> **HDMI Video is strictly unidirectional (Phone → PC).**
> Viewing the video stream on your PC screen **does NOT** mean mouse clicks on the window will control the phone.

The application enforces a strict separation:

### When ADB is NOT Authorized:
- **Status Indicator:** `🔴 Touch Control: DISABLED (No Authorized ADB)`
- Clicking on the video preview displays an on-screen warning and does not transmit any events.
- **Recommended Alternative:** Plug a **standard wired USB mouse** into one of the USB-A ports on your **USB-C multiport hub**. A hardware mouse cursor will appear directly on the HDMI video output, allowing you to unlock the phone and interact with it with **zero ADB and zero developer options**.

### When ADB IS Authorized:
- **Status Indicator:** `🟢 Touch Control: ACTIVE (ADB Authorized)`
- Clicks on the video window are mapped to the phone's native display coordinates (`input tap X Y`).
- Swipe and drag gestures are mapped to `input swipe`.
- Quick action buttons (Power, Unlock/Swipe Up, Back, Home, Recents, Volume) are enabled.
- Option to launch **scrcpy Control-Only Mode** (`scrcpy --no-video --no-audio`) for low-latency hardware keyboard/mouse forwarding.

---

## 3. Samsung DeX vs. Mirrored-Phone Mode

When an external HDMI display is connected to a Galaxy S9+ running One UI (Android 10), Samsung frequently defaults to launching **Samsung DeX desktop** instead of mirroring the phone screen.

If you want to view the **actual phone screen** (portrait lockscreen, phone apps) rather than the DeX desktop:

### Method 1: Using a Physical Mouse on the External Screen
1. Move the mouse to the **bottom-right corner** of the HDMI screen.
2. Click the **Quick Settings / Notification** panel.
3. Click the **Samsung DeX** notification.
4. Select **"Switch to screen mirroring"**. The display will immediately switch to mirroring the phone's actual screen.

### Method 2: Hardware Keyboard Shortcut
If a keyboard is plugged into the USB-C hub, press `Windows Key + W` to toggle between DeX mode and Screen Mirroring.

### Method 3: Safe ADB Request
In the application's **DeX vs Mirror** tab, click **"Request Switch to Mirroring via ADB"**. This sends the official Samsung broadcast:
```bash
am broadcast -a com.samsung.android.desktopmode.action.STOP_DESKTOP_MODE
```
This command is safe, non-destructive, and does not alter system integrity.

---

## 4. Software Requirements & Setup

### Prerequisites
1. **Python 3.10+**: Make sure Python is installed and added to PATH.
2. **PySide6**:
   ```bash
   pip install -r requirements.txt
   ```
3. *(Optional)* **scrcpy / ADB**: Already auto-discovered if located on your Desktop or PATH.

---

## 5. Running the Application

### Via Windows Batch Launcher
Double-click `launch_hdmi_viewer.bat` or run:
```cmd
launch_hdmi_viewer.bat
```

### Directly via Python
```powershell
python main_hdmi_viewer.py
```

---

## 6. Hardware Verification & Automated Testing

The application strictly connects to genuine physical capture hardware. All simulated/synthetic frame generators have been removed.

To verify the hardware pipeline and USB detection:
```powershell
python -m pytest tests/ -v
```
This runs 58 automated unit tests verifying:
- USB PnP device tree queries and interface descriptor parsing
- Verification of UVC absence on standard Samsung USB composite mode
- Genuine capture device enumeration, streaming, failure, and disconnection handling
- Decoupling of video streaming from ADB authorization state

---

## 7. Building a Standalone Windows Binary

To compile into a standalone `.exe`:
```powershell
python build_hdmi_viewer.py
```
The output directory will be located at `dist/S9HdmiViewer/`.

---

## 8. Safety & Data Preservation Guarantee

- **Zero firmware flashing**: Odin, Heimdall, and raw download mode commands are never used.
- **Zero partition modifications**: No recovery or boot partition altering.
- **Zero FRP bypasses**: Standard Android device security is respected.
- All user data, photos, accounts, and application storage remain untouched.
