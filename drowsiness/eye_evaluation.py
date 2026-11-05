"""Comparing blink detection with manual labels (success criterion of work package 2)."""
import json
from pathlib import Path

from .eye import BLINK, LONG_BLINK, EyeTracker, mean_ear
from .landmarks import FaceLandmarkDetector, to_pixels
from .source import VideoSource

BLINK_KINDS = (BLINK, LONG_BLINK)  # a slow blink is also a blink


def match_events(label_times_s, events, tolerance_s=0.25):
    """Matches manually marked blink times one-to-one with detected events.

    A label matches if its time falls in the event's [start - tolerance, end + tolerance] range;
    every label and every event is used at most once.
    Returns: (true positives TP, missed FN, false alarms FP)
    """
    events = sorted(events, key=lambda e: e.start_ms)
    used = set()
    tp = 0
    for t in sorted(label_times_s):
        for i, event in enumerate(events):
            if i in used:
                continue
            low = event.start_ms / 1000.0 - tolerance_s
            high = (event.start_ms + event.duration_ms) / 1000.0 + tolerance_s
            if low <= t <= high:
                used.add(i)
                tp += 1
                break
    return tp, len(label_times_s) - tp, len(events) - tp


def read_labels(json_path):
    """Reads (video path, blink times in s) from a label file."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["video"], sorted(float(t) for t in data["blink_times_s"])


def write_labels(json_path, video_path, times_s):
    """Saves manually marked blink times together with the video they belong to."""
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    data = {"video": str(video_path).replace("\\", "/"), "blink_times_s": [round(t, 3) for t in sorted(times_s)]}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def video_eye_events(video_path, max_s=None, tracker=None):
    """Processes a video from start to end; returns (tracker, events)."""
    tracker = tracker or EyeTracker()
    with VideoSource(str(video_path)) as source, FaceLandmarkDetector() as detector:
        for _, timestamp_ms, frame in source.frames():
            if max_s and timestamp_ms / 1000.0 > max_s:
                break
            landmarks = detector.detect(frame, timestamp_ms)
            ear = None
            if landmarks is not None:
                height, width = frame.shape[:2]
                ear = mean_ear(to_pixels(landmarks, width, height))
            tracker.update(timestamp_ms, ear)
    return tracker, tracker.events


def calibration_end_s(tracker):
    """Time (s) at which calibration ended; blinks before it cannot be counted."""
    return (tracker.monitoring_start_ms or 0) / 1000.0
