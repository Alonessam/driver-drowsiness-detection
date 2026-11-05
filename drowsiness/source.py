"""Reading frames from a video file or a camera."""
import time

import cv2


class VideoSource:
    """source: camera index (0, 1, ...) or path to a video file."""

    def __init__(self, source):
        self.is_camera = isinstance(source, int)
        self._cap = cv2.VideoCapture(source)
        if self.is_camera and not self._cap.isOpened():
            self._cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)  # fallback backend on Windows
        if not self._cap.isOpened():
            raise OSError(f"Could not open source: {source}")
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps and fps > 1 else 30.0
        self.total_frames = None if self.is_camera else int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def frames(self):
        """Yields (frame_no, timestamp_ms, bgr_frame)."""
        start = time.monotonic()
        frame_no = 0
        while True:
            ok, frame = self._cap.read()
            if not ok:
                return
            if self.is_camera:
                timestamp_ms = (time.monotonic() - start) * 1000
            else:
                timestamp_ms = frame_no * 1000.0 / self.fps
            yield frame_no, timestamp_ms, frame
            frame_no += 1

    def close(self):
        self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
