"""Face landmark detection with the MediaPipe Face Landmarker."""
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from .paths import MODEL_PATH

# Eye landmarks in the order p1..p6 used by the EAR formula: corner, upper, upper, corner, lower, lower
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
# Inner upper lip (13), inner lower lip (14), inner mouth corners (78, 308)
MOUTH = [13, 14, 78, 308]


class FaceLandmarkDetector:
    """Finds 478 landmarks for a single face in video frames."""

    def __init__(self, model_path=MODEL_PATH):
        vision = mp.tasks.vision
        options = vision.FaceLandmarkerOptions(
            # The model is passed as a buffer so that non-ASCII characters in the path do not matter.
            base_options=mp.tasks.BaseOptions(model_asset_buffer=Path(model_path).read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def detect(self, bgr_frame, timestamp_ms):
        """Returns a (478, 3) array of normalized (x, y, z) landmarks in the 0-1 range for the frame.

        Returns None if no face is found. timestamp_ms must increase with every call.
        """
        timestamp_ms = max(int(timestamp_ms), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        rgb = np.ascontiguousarray(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.face_landmarks:
            return None
        return np.array([(n.x, n.y, n.z) for n in result.face_landmarks[0]], dtype=np.float32)

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def to_pixels(landmarks, width, height):
    """Converts normalized (x, y) coordinates to pixel coordinates: (478, 2) float."""
    return landmarks[:, :2] * np.array([width, height], dtype=np.float32)
