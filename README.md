# BlinkGuard

A macOS menu-bar app that tracks your blink rate using your webcam and locks your screen if you're not blinking enough — protecting your eyes during long screen sessions.

---

## How it works

BlinkGuard runs silently in the background and uses your Mac's camera + [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) to detect every blink in real time.

- Every **60 seconds**, it checks if you blinked at least **20 times**
- If you did — great, the cycle resets
- If you didn't — your **entire screen locks** with a white overlay
- To unlock: **blink 3 times rapidly** (within 3 seconds)

---

## Features

- Real-time blink detection via webcam (no internet required)
- HUD overlay in the top-right corner showing blink count + time remaining
- HUD color changes: green (20+), amber (10–19), red (<10)
- Full-screen lock across **all connected monitors**
- Unlock by blinking 3 times fast — no keyboard, no mouse needed
- Packaged as a native `.app` — no terminal needed after build

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.9+
- Webcam

---

## Build

```bash
cd ~/Desktop/blink
bash build.sh
```

The script will automatically:
1. Install dependencies (`opencv-python`, `mediapipe`, `pyinstaller`, `pyobjc`)
2. Download the MediaPipe face landmark model (~30 MB)
3. Bundle everything into `dist/BlinkGuard.app`
4. Inject the camera usage permission into `Info.plist`

---

## Install

1. Open `dist/` in Finder
2. Drag `BlinkGuard.app` into `/Applications`
3. Launch it — macOS will prompt for **camera permission**, click Allow

---

## Project Structure

```
blink/
├── main.py              # GUI — HUD widget + fullscreen lock overlays (tkinter)
├── blink_detector.py    # Camera thread — MediaPipe blink detection logic
├── build.sh             # PyInstaller build script
└── face_landmarker.task # MediaPipe face landmark model (downloaded by build.sh)
```

---

## Configuration

You can tweak these constants at the top of `blink_detector.py`:

| Constant | Default | Description |
|---|---|---|
| `BLINK_THRESHOLD` | `0.45` | Blendshape score above which eye is considered closed |
| `BLINK_CONSEC` | `2` | Consecutive frames eye must stay closed to register a blink |
| `RAPID_WINDOW` | `3.0` s | Time window to detect rapid blinks for unlock |
| `RAPID_COUNT` | `3` | Number of rapid blinks needed to unlock |
| `MINUTE_DURATION` | `60` s | Check interval |
| `MIN_BLINKS` | `20` | Minimum blinks required per interval to avoid lock |

---

## Why blink more?

The average person blinks **15–20 times per minute** normally, but this drops to as low as **5–7 times per minute** when staring at a screen. Reduced blinking causes dry eyes, eye strain, and fatigue. BlinkGuard keeps you on track.
