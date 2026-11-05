"""Running the yawn tracker on videos (success criterion of work package 3)."""
from .landmarks import FaceLandmarkDetector, to_pixels
from .mouth import YawnTracker, mouth_mar
from .source import VideoSource


def video_yawn_events(video_path, max_s=None, tracker=None):
    """Processes a video from start to end; returns (tracker, events)."""
    tracker = tracker or YawnTracker()
    with VideoSource(str(video_path)) as source, FaceLandmarkDetector() as detector:
        for _, timestamp_ms, frame in source.frames():
            if max_s and timestamp_ms / 1000.0 > max_s:
                break
            landmarks = detector.detect(frame, timestamp_ms)
            mar = None
            if landmarks is not None:
                height, width = frame.shape[:2]
                mar = mouth_mar(to_pixels(landmarks, width, height))
            tracker.update(timestamp_ms, mar)
    tracker.finish()
    return tracker, tracker.events
