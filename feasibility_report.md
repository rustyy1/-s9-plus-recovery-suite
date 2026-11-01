# Feasibility Report: Galaxy S9+ Black-Screen Recovery

## Device: Samsung Galaxy S9+ (SM-G965F, Exynos 9810)
## Problem: Built-in OLED display is completely unusable

---

## Executive Summary

The Galaxy S9+ with a dead display can be recovered and controlled using two
complementary approaches, depending on whether USB debugging was previously enabled:

| Approach | Works Without USB Debugging? | Works Without Screen? | Cost |
|----------|------------------------------|----------------------|------|
| **USB-C to HDMI + mouse** | ✅ Yes | ✅ Yes | $15–$40 |
| **ADB + scrcpy mirroring** | ❌ No (requires USB debugging) | ✅ Yes (once enabled) | Free |
| **Samsung DeX for PC** | N/A | N/A | ❌ Discontinued |
| **Samsung Smart Switch** | Partially (needs unlocked phone) | Partially | Free |
| **Phone Link (Link to Windows)** | Needs Bluetooth pairing | Needs screen | Free |
| **Custom USB video driver** | N/A | N/A | ❌ Not feasible |

**Recommended path**: Use a USB-C to HDMI hub first to see the phone screen on an
external monitor, enable USB debugging with a mouse, then use scrcpy for permanent
remote access from your PC.

---

## Detailed Analysis

### 1. ADB + scrcpy Screen Mirroring

**How it works**: scrcpy connects to the phone via ADB (USB data), captures the
phone's framebuffer, and streams it as a compressed video to your PC. It also
forwards mouse/keyboard input back to the phone.

**Requirements**:
- USB debugging must be **enabled** in Developer Options on the phone
- Your PC must be **authorized** (the phone shows an RSA key prompt that must be accepted)
- The phone must be **fully booted** into Android

**Verdict**: ✅ **Best long-term solution** — but only works if USB debugging was
already enabled, OR if you can enable it using an external display first.

**Limitation**: There is no way to enable USB debugging purely through software
from the PC side. The setting must be toggled on the phone, and the RSA authorization
prompt must be accepted on the phone's screen (or an external display showing the phone).

---

### 2. USB-C to HDMI (DisplayPort Alternate Mode)

**How it works**: The Galaxy S9+'s USB-C port supports **DisplayPort Alternate Mode**.
With a compatible USB-C to HDMI adapter or hub, the phone outputs a real video signal
to an external monitor — the same way a laptop connects to a projector.

**Requirements**:
- A USB-C multiport hub with HDMI output (must support DP Alt Mode)
- An HDMI cable and external monitor/TV
- A USB wired mouse (connected to the hub)
- **External power** via the hub's USB-C PD port (critical — many hubs won't output
  video without it)

**Verdict**: ✅ **Best first step** — Works without any software configuration, USB
debugging, or ADB. This is a hardware-level video output that works as long as:
1. The phone powers on
2. The USB-C port is functional
3. The adapter supports DP Alt Mode

**Key details**:
- The phone boots and outputs video automatically
- You must unlock the phone using the USB mouse (type PIN/password)
- Samsung DeX may activate, providing a desktop-like interface
- Once unlocked, you can navigate to Settings and enable USB debugging
- Common failure cause: lint in the USB-C port blocking high-speed pins

**Cost**: $15–$40 for a compatible USB-C hub.

---

### 3. Samsung DeX

**Samsung DeX on an external display**: ✅ Still works on the Galaxy S9+. When
you connect a compatible USB-C hub with HDMI, DeX activates automatically and
provides a desktop-like interface with taskbar, resizable windows, and mouse support.

**Samsung DeX for PC (Windows app)**: ❌ **Discontinued by Samsung**. The Windows
application that allowed DeX to run inside a window on your PC has been retired.
Samsung directs users to Microsoft Phone Link as a replacement, but Phone Link
does not provide full DeX functionality and requires Bluetooth pairing (which
needs the phone screen).

**Verdict**: DeX on an external monitor is excellent for initial recovery. DeX for
PC is no longer an option.

---

### 4. USB-C HDMI Output to External Monitor

This is the same as approach #2. The Galaxy S9+ uses DisplayPort Alternate Mode
over its USB-C port. There is no separate "HDMI output" — it's all through USB-C
with the right adapter.

**Critical distinction**: This is a **hardware video signal**, not a software
protocol. A Windows PC connected via a regular USB data cable cannot receive this
video signal. The USB-C to HDMI adapter must connect to a **monitor or TV with
HDMI input**, not to the PC's USB port.

---

### 5. Samsung Smart Switch

**How it works**: Samsung's official backup/transfer tool. Connects via USB.

**Limitation for dead screen**: Smart Switch requires the phone to be **unlocked**.
If the phone is locked and the screen is dead, Smart Switch will show a "Device is
locked" error and refuse to backup.

**Workaround**: Use the USB-C to HDMI method to unlock the phone first, then
connect to the PC for Smart Switch backup.

**Verdict**: ⚠️ Useful for backup after you've unlocked the phone, but cannot
bypass the lock screen.

---

### 6. Recovery Mode and Download Mode

**Recovery Mode** (Volume Up + Bixby + Power):
- ADB works with limited commands (`adb sideload`)
- Can perform factory reset (⚠️ **destroys all data**)
- Useful for diagnostics but not for data recovery
- This tool **will not** initiate any destructive operations

**Download Mode** (Volume Down + Bixby + USB cable):
- Used for firmware flashing with Samsung's Odin tool
- **ADB does not work** in Download Mode
- Odin communicates through Samsung USB CDC drivers
- The phone appears in Device Manager under "Modems" or as a Samsung USB device
- This tool can detect Download Mode but **will not flash firmware**

**Verdict**: These modes are for advanced recovery scenarios. For a dead screen
with data preservation as the goal, they are not the primary path.

---

## What Software CANNOT Do

| Claim | Reality |
|-------|---------|
| "Software can output video over USB data cable" | ❌ Impossible. USB data and DisplayPort Alt Mode use different electrical signals. |
| "PC can force DeX to start on the phone" | ❌ DeX is initiated by the phone when it detects a compatible display adapter. |
| "ADB can be enabled remotely from PC" | ❌ USB debugging is a phone-side setting requiring on-device interaction. |
| "Custom driver can emulate HDMI over USB" | ❌ The USB host (PC) cannot produce a DisplayPort signal to the phone. |
| "Software can unlock the phone screen" | ❌ Screen unlock requires the correct PIN/password/pattern. |
| "App can bypass FRP automatically" | ❌ FRP is a hardware-backed security feature. This tool does not bypass it. |

---

## Recommended Recovery Workflow

### Phase 1: Get Visual Access (Hardware)
1. Purchase a USB-C multiport hub with HDMI + USB-A + PD passthrough ($15–$40)
2. Connect hub → HDMI → external monitor/TV
3. Connect USB mouse to hub
4. Connect phone charger to hub's PD port
5. Plug hub into Galaxy S9+
6. Unlock the phone with the mouse on the external display

### Phase 2: Enable Remote Access (Software)
7. On the external display: Settings → About phone → Software info → tap Build number 7x
8. Settings → Developer options → enable USB debugging
9. Disconnect hub, connect phone directly to PC via USB cable
10. Accept RSA key prompt on external display (may need to briefly reconnect hub)
11. Run Galaxy S9+ Recovery Console on PC
12. Click Refresh → Start Mirroring

### Phase 3: Ongoing Access
13. scrcpy now shows the phone's live screen on your PC
14. Use PC mouse and keyboard to control the phone
15. Back up data, transfer files, or continue using the phone

---

## Hardware Requirements Summary

| What You Need | Why | Approximate Cost |
|---------------|-----|------------------|
| USB-C hub with HDMI + USB-A + PD | Video output + mouse + power | $15–$35 |
| HDMI cable | Connect hub to monitor | $5–$10 |
| External monitor/TV | Display the phone's output | (likely already owned) |
| USB wired mouse | Navigate the phone | $5–$10 |
| USB wired keyboard (optional) | Type PIN/password easily | $5–$10 |
| USB-C phone charger | Power the hub | (likely already owned) |
| USB-A to USB-C cable | Connect phone to PC for ADB | (likely already owned) |

**Total new purchase needed**: Typically $20–$40 if you already have a monitor and cables.

---

## Device State Requirements for This Application

| Feature | Requires |
|---------|----------|
| Dashboard (basic) | ADB installed, device detected (any state) |
| Dashboard (full info) | Authorized ADB connection, device fully booted |
| Screen mirroring | Authorized ADB + scrcpy installed + device fully booted |
| Storage diagnostics | Authorized ADB connection |
| External display guide | No device connection needed (informational) |
| Troubleshooting | ADB installed (runs step-by-step checks) |

---

*Report generated by Galaxy S9+ Recovery Console v1.0.0*
*This analysis is based on the Galaxy S9+ (SM-G965F, Exynos 9810) hardware capabilities*
*and official documentation as of 2024. No physical device was connected during generation.*
