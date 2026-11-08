# 🚛 AI Visual Hand-Tracking Steering Wheel

A real-time computer vision driving controller that turns any standard webcam or **smartphone camera** into an authentic virtual steering wheel for **American Truck Simulator (ATS)**, **Euro Truck Simulator 2 (ETS2)**, and other PC racing games.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)
![Input](https://img.shields.io/badge/Controller-Virtual_Xbox_360_%2B_DirectInput-green.svg)
![Docs](https://img.shields.io/badge/Manual-Word_.docx_Included-1B365D.svg)

---

## 🌟 Highlights

- **Smooth 1:1 Proportional Analog Steering**: Emulates an authentic **Xbox 360 Controller** (`vgamepad`), allowing smooth lane keeping, realistic cornering, and delicate maneuvers without jerky keyboard turning.
- **Enterprise 900° Multi-Turn Tracking**: Rotate your hands continuously, cross your arms, and drive hand-over-hand without losing tracking or snapping angles.
- **📢 Real Truck Horn System**: Press the center of the virtual steering wheel hub with your hand to HONK the truck's horn (Maps to ATS `H` / Air Horn `N`).
- **💡 Left & Right Turn Blinkers**: Flick your index finger outward to the left (`[`) or right (`]`) to activate turn signal blinkers on your truck.
- **Adaptive One Euro Filter (1€ Filter)**: Delivers jitter-free steering on straight highways with zero-latency response on sharp turns.
- **Analog Pinch Pedals**: Pinch your right hand (Thumb + Index) for progressive Throttle (Gas), pinch your left hand for Brake & Reverse.
- **Picture-in-Picture Mini HUD (`[O]` key)**: Float a compact Always-on-Top camera HUD over your game in Borderless Window mode.
- **Interactive Standalone Highway Simulator**: Test drive immediately with `play_demo.bat` even if American Truck Simulator is not yet installed on your machine!
- **Illustrated Word User Manual Included**: Complete beginner-friendly manual at [`ATS_Visual_Driving_User_Manual.docx`](./ATS_Visual_Driving_User_Manual.docx).

---

## 🎮 Driving & Gesture Controls

| Control | Physical Gesture | In-Game Binding | On-Screen HUD Visual |
| :--- | :--- | :--- | :--- |
| **Steering Wheel** | Hold hands up at 9-and-3 o'clock; tilt left/right. | Xbox Left Joystick X | Rotating neon steering wheel & angle badge |
| **Enterprise 900° Rotation** | Rotate hands hand-over-hand (supports 360°–900°). | Extended analog steering | Continuous wheel tracking, angle readout |
| **Gas / Accelerator** | **Right Hand**: Pinch thumb & index finger together. | Right Trigger (RT) | Green analog bar: `GAS 0% -> 100%` |
| **Brake / Reverse** | **Left Hand**: Pinch thumb & index finger together. | Left Trigger (LT) | Red analog bar: `BRAKE 0% -> 100%` |
| **Honk Horn** | Push either hand forward toward the virtual wheel center. | Key `[H]` (Air Horn `[N]`) | Bright Amber `HORN ACTIVE` alert |
| **Left Turn Blinker** | Flick Left Thumb or Index finger outward. | Key `[` | Green dashboard flasher `<<` with sound |
| **Right Turn Blinker** | Flick Right Thumb or Index finger outward. | Key `]` | Green dashboard flasher `>>` with sound |

---

## 📱 No Webcam on your Laptop? Use Your Phone!

If using a laptop with no built-in webcam, any smartphone can be used as a 60 FPS ultra-low latency camera:

### Option A: DroidCam or Iriun Webcam (Recommended — 60 FPS & Zero Lag)
1. Install **DroidCam** or **Iriun Webcam** from Google Play Store (Android) or Apple App Store (iOS).
2. Install the free client on the laptop:
   - [Iriun Webcam Client](https://iriun.com/) or [DroidCam PC Client](https://www.dev47apps.com/)
3. Connect the phone via **USB Cable** (recommended for zero latency) or local **Wi-Fi**.
4. Double-click `run.bat` — the software detects your phone camera automatically!

### Option B: Wireless IP Webcam (Direct Wi-Fi Stream)
1. Install **IP Webcam** (free on Android).
2. Open the app, scroll to the bottom, and tap **Start Server**.
3. Note the IP address shown on the phone screen (e.g. `http://192.168.1.15:8080`).
4. In `config.py`, set:
   ```python
   PHONE_STREAM_URL = "http://192.168.1.15:8080/video"
   ```
5. Double-click `run.bat` — it streams directly from the phone wirelessly!

---

## 🚀 Quick Start

### 1. Drive in American Truck Simulator
Double-click:
```bash
run.bat
```

### 2. Play the Built-in Highway Demo (No ATS Needed!)
Double-click:
```bash
play_demo.bat
```

### 3. One-Time Xbox Gamepad Driver Setup (If Needed)
If ATS doesn't detect the virtual controller, double-click:
```bash
install_gamepad_driver.bat
```

---

## ⌨️ In-App Hotkeys

- **`[O]`**: Toggle Always-on-Top Mini Picture-in-Picture (PiP) HUD mode.
- **`[R]`**: Recalibrate steering wheel center (resets current hand position to $0^\circ$).
- **`[M]`**: Switch tracking engine mode (Standard 180° $\leftrightarrow$ Enterprise 900° Continuous Rotation).
- **`[P]`**: Pause / Resume inputs.
- **`[Q]` / `[ESC]`**: Exit cleanly.

---

## 📖 User Manual
A complete, non-technical, illustrated user manual with AI diagrams is included in the root directory:
👉 **[`ATS_Visual_Driving_User_Manual.docx`](./ATS_Visual_Driving_User_Manual.docx)**

---

## 🛠️ Requirements & Manual Installation (For Developers)

If running from source rather than the portable package:

```bash
git clone https://github.com/mRcOol7/hand-tracking-driving-simulator.git
cd hand-tracking-driving-simulator
pip install -r requirements.txt
python main.py
```
