#!/usr/bin/env bash
# install.sh — installs all Python dependencies and downloads the face landmark model
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== BlinkGuard — installing dependencies ==="

PYTHON=$(which python3)
echo "Python: $PYTHON  ($($PYTHON --version))"

$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install opencv-python mediapipe

echo ""
echo "Downloading face landmark model..."
MODEL_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL_PATH="$SCRIPT_DIR/face_landmarker.task"

if [ -f "$MODEL_PATH" ]; then
    echo "  Model already exists at $MODEL_PATH — skipping download."
else
    curl -L -o "$MODEL_PATH" "$MODEL_URL"
    echo "  Saved to $MODEL_PATH"
fi

echo ""
echo "Done. Run the app with:"
echo "  python3 main.py"
echo ""
echo "Or build a double-clickable .app with:"
echo "  ./build.sh"
