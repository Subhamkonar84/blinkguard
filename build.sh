#!/usr/bin/env bash
# build.sh — produces dist/BlinkGuard.app (double-clickable on Mac)
set -e

echo "=== BlinkGuard — build script ==="

PYTHON=$(which python3)
echo "Python: $PYTHON  ($($PYTHON --version))"

# ── 1. Install / upgrade build tools ──────────────────────────────────
echo ""
echo "[1/5] Installing build dependencies..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install opencv-python mediapipe pyinstaller pyobjc-framework-Cocoa

# ── 2. Locate mediapipe package so PyInstaller can bundle its data ─────
echo ""
echo "[2/5] Locating MediaPipe data files..."
MEDIAPIPE_DIR=$($PYTHON -c "import mediapipe, os; print(os.path.dirname(mediapipe.__file__))")
echo "      MediaPipe: $MEDIAPIPE_DIR"

CV2_DIR=$($PYTHON -c "import cv2, os; print(os.path.dirname(cv2.__file__))")
echo "      OpenCV:    $CV2_DIR"

# ── 3. Clean previous build ───────────────────────────────────────────
echo ""
echo "[3/5] Cleaning previous build..."
rm -rf build dist BlinkGuard.spec

# ── 3.5. Download face landmark model if needed ───────────────────────
MODEL="face_landmarker.task"
if [ ! -f "$MODEL" ]; then
    echo ""
    echo "[3.5/5] Downloading face landmark model (~30 MB)..."
    curl -L -o "$MODEL" "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
else
    echo ""
    echo "[3.5/5] Face landmark model already present."
fi

# ── 4. Run PyInstaller ────────────────────────────────────────────────
echo ""
echo "[4/5] Building BlinkGuard.app with PyInstaller..."
pyinstaller \
    --windowed \
    --name "BlinkGuard" \
    --add-data "$MEDIAPIPE_DIR:mediapipe" \
    --add-data "$CV2_DIR:cv2" \
    --add-data "face_landmarker.task:." \
    --collect-all mediapipe \
    --collect-all cv2 \
    --hidden-import mediapipe \
    --hidden-import cv2 \
    --hidden-import tkinter \
    --hidden-import AppKit \
    --hidden-import Foundation \
    --noconfirm \
    main.py

# ── 5. Inject camera-usage permission into Info.plist ─────────────────
echo ""
echo "[5/5] Adding NSCameraUsageDescription to Info.plist..."
PLIST="dist/BlinkGuard.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c \
    "Add :NSCameraUsageDescription string 'BlinkGuard uses the camera to track your blink rate and remind you to blink regularly.'" \
    "$PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c \
    "Set :NSCameraUsageDescription 'BlinkGuard uses the camera to track your blink rate and remind you to blink regularly.'" \
    "$PLIST"

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo " Build complete!"
echo " App location: $(pwd)/dist/BlinkGuard.app"
echo ""
echo " To install: drag dist/BlinkGuard.app into /Applications"
echo " First run:  macOS may ask for camera permission — allow it."
echo "============================================"
