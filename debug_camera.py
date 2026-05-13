"""Run this to see exactly what's happening with camera + mediapipe."""
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
import time
import os

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'face_landmarker.task')

print(f"Model path: {MODEL}")
print(f"Model exists: {os.path.exists(MODEL)}")

print("Creating FaceLandmarker...")
base = mp_tasks.BaseOptions(model_asset_path=MODEL)
opts = mp_vision.FaceLandmarkerOptions(
    base_options=base,
    running_mode=mp_vision.RunningMode.VIDEO,
    output_face_blendshapes=True,
    num_faces=1,
)
landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
print("FaceLandmarker ready.")

print("Opening camera...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Could not open camera!")
    exit(1)
print("Camera open. Starting 10-second capture loop — look at the camera!")
print()

start = time.time()
blink_count = 0
closed = False

while time.time() - start < 10:
    ret, frame = cap.read()
    if not ret:
        print("WARNING: Failed to read frame")
        continue

    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img    = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    ts_ms  = int(time.time() * 1000)
    result = landmarker.detect_for_video(img, ts_ms)

    if result.face_blendshapes:
        shapes = {s.category_name: s.score for s in result.face_blendshapes[0]}
        left   = shapes.get('eyeBlinkLeft',  0.0)
        right  = shapes.get('eyeBlinkRight', 0.0)
        avg    = (left + right) / 2.0

        if avg > 0.45 and not closed:
            closed = True
        elif avg <= 0.45 and closed:
            closed = False
            blink_count += 1
            print(f"  Blink #{blink_count} detected  (L={left:.2f} R={right:.2f})")
    else:
        print("  No face detected in frame")
        time.sleep(0.1)
        continue

cap.release()
landmarker.close()
print()
print(f"Done. Detected {blink_count} blinks in 10 seconds.")
if blink_count == 0:
    print("Tip: Make sure your face is well-lit and fully in frame.")
