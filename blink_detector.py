import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
import time
import queue
import os
import sys

BLINK_THRESHOLD   = 0.45  # blendshape score above this = eye closed
BLINK_CONSEC      = 2     # consecutive frames eye must be closed to register
RAPID_WINDOW      = 3.0   # seconds
RAPID_COUNT       = 3
MINUTE_DURATION   = 60
MIN_BLINKS        = 15


def _model_path() -> str:
    """Finds face_landmarker.task whether running as script or bundled .app."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'face_landmarker.task')


class BlinkDetector:
    def __init__(self, msg_queue: queue.Queue):
        self.q            = msg_queue
        self.running      = False

        self.blink_count  = 0
        self.minute_start = time.time()

        self.closed_frames = 0

        self.rapid_blinks: list[float] = []
        self.locked = False

    # ------------------------------------------------------------------
    def run(self):
        self.running = True

        model = _model_path()
        if not os.path.exists(model):
            self.q.put({'type': 'error',
                        'msg': f'Model not found at:\n{model}\n\nRun install.sh first.'})
            return

        base_opts = mp_tasks.BaseOptions(model_asset_path=model)
        options   = mp_vision.FaceLandmarkerOptions(
            base_options=base_opts,
            running_mode=mp_vision.RunningMode.VIDEO,
            output_face_blendshapes=True,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        with mp_vision.FaceLandmarker.create_from_options(options) as landmarker:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms    = int(time.time() * 1000)
                result   = landmarker.detect_for_video(mp_img, ts_ms)

                # --- Blink score from blend shapes ---
                blink_score = 0.0
                if result.face_blendshapes:
                    shapes = {s.category_name: s.score
                              for s in result.face_blendshapes[0]}
                    left  = shapes.get('eyeBlinkLeft',  0.0)
                    right = shapes.get('eyeBlinkRight', 0.0)
                    blink_score = (left + right) / 2.0

                # --- State machine: closed → open edge = blink ---
                if blink_score > BLINK_THRESHOLD:
                    self.closed_frames += 1
                else:
                    if self.closed_frames >= BLINK_CONSEC:
                        self._on_blink()
                    self.closed_frames = 0

                # --- Minute boundary ---
                elapsed   = time.time() - self.minute_start
                remaining = max(0, MINUTE_DURATION - int(elapsed))
                now       = time.time()
                rapid     = len([t for t in self.rapid_blinks
                                 if now - t <= RAPID_WINDOW])

                self.q.put({
                    'type':      'update',
                    'count':     self.blink_count,
                    'remaining': remaining,
                    'rapid':     rapid,
                })

                if elapsed >= MINUTE_DURATION:
                    if not self.locked and self.blink_count < MIN_BLINKS:
                        self.locked = True
                        self.q.put({'type': 'lock'})
                    self.blink_count  = 0
                    self.minute_start = time.time()

        cap.release()

    # ------------------------------------------------------------------
    def _on_blink(self):
        now = time.time()
        self.blink_count += 1
        self.rapid_blinks.append(now)
        self.rapid_blinks = [t for t in self.rapid_blinks
                             if now - t <= RAPID_WINDOW]

        if self.locked and len(self.rapid_blinks) >= RAPID_COUNT:
            self.locked       = False
            self.rapid_blinks = []
            self.q.put({'type': 'unlock'})

    # ------------------------------------------------------------------
    def stop(self):
        self.running = False
