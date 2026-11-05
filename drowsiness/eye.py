"""Blink and long eye closure detection (EAR: Eye Aspect Ratio).

EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)  (Soukupova and Cech, 2016)
It is about 0.25-0.30 for an open eye and close to zero when the eye is closed.
"""
from dataclasses import dataclass
from statistics import median

import numpy as np

from .landmarks import LEFT_EYE, RIGHT_EYE

TOLERANCE_S = 0.001  # keeps durations on a boundary from falling on the wrong side due to float rounding
BLINK = "blink"
LONG_BLINK = "long_blink"
LONG_CLOSURE = "long_closure"


def compute_ear(p):
    """EAR of a single eye. p: (6, 2) pixel coordinates in the order p1..p6."""
    p = np.asarray(p, dtype=np.float64)
    vertical1 = np.linalg.norm(p[1] - p[5])
    vertical2 = np.linalg.norm(p[2] - p[4])
    horizontal = np.linalg.norm(p[0] - p[3])
    if horizontal == 0:
        return 0.0
    return float((vertical1 + vertical2) / (2.0 * horizontal))


def mean_ear(points_px):
    """Mean EAR of both eyes (reduces noise). points_px: (478, 2) pixel coordinates."""
    right = compute_ear(points_px[RIGHT_EYE])
    left = compute_ear(points_px[LEFT_EYE])
    return (right + left) / 2.0


@dataclass
class EyeEvent:
    kind: str           # BLINK, LONG_BLINK or LONG_CLOSURE
    start_ms: float
    duration_ms: float


class EyeTracker:
    """Takes the EAR frame by frame; calibrates and counts blinks and long closures.

    Durations are computed from frame timestamps (ms), so they are correct for both video and camera.

    calibration_s: Time at the start in which the normal EAR is measured. The median is used so that
                   blinks do not affect it; threshold = median x threshold_ratio.
    blink_min_s / blink_max_s: Closures in this range count as a "blink"; shorter ones are treated
                   as noise and ignored.
    long_closure_s: If the eyes stay closed longer than this, a "long eye closure (microsleep)" event is
                   emitted (while the eyes are still closed, at the moment the time is reached).
    Closures longer than a blink but shorter than a long closure count as a "long blink" (slow blink).
    """

    def __init__(self, calibration_s=3.0, threshold_ratio=0.72, threshold_min=0.10, threshold_max=0.28,
                 blink_min_s=0.10, blink_max_s=0.40, long_closure_s=1.5, min_samples=10):
        self.calibration_s = calibration_s
        self.threshold_ratio = threshold_ratio
        self.threshold_min, self.threshold_max = threshold_min, threshold_max
        self.blink_min_s, self.blink_max_s = blink_min_s, blink_max_s
        self.long_closure_s = long_closure_s
        self.min_samples = min_samples
        self.reset_calibration()

    def reset_calibration(self):
        """Resets the calibration and counters (e.g. when switching to another driver)."""
        self.threshold = None
        self.normal_ear = None
        self.remaining_s = self.calibration_s
        self.last_ear = None
        self.blink_count = 0
        self.long_blink_count = 0
        self.long_closure_count = 0
        self.events = []
        self._samples = []
        self._calibration_start_ms = None
        self._closed_start_ms = None
        self._long_reported = False
        self.monitoring_start_ms = None

    @property
    def is_calibrated(self):
        return self.threshold is not None

    @property
    def is_closed(self):
        return self._closed_start_ms is not None

    def closed_duration_s(self, timestamp_ms):
        """How long the eyes have been closed right now (s); 0 if they are open."""
        if self._closed_start_ms is None:
            return 0.0
        return (timestamp_ms - self._closed_start_ms) / 1000.0

    def blink_rate_per_min(self, timestamp_ms):
        """Average blinks per minute since calibration (None if there is not enough time yet)."""
        if self.monitoring_start_ms is None:
            return None
        minutes = (timestamp_ms - self.monitoring_start_ms) / 60000.0
        return self.blink_count / minutes if minutes >= 0.25 else None

    def update(self, timestamp_ms, ear):
        """Processes one frame. ear: EAR of that frame, or None if there is no face. Returns the new events."""
        self.last_ear = ear
        if ear is None:
            # Face lost: a half-finished closure is unreliable, drop it without counting
            self._closed_start_ms = None
            self._long_reported = False
            return []
        if not self.is_calibrated:
            self._calibration_step(timestamp_ms, ear)
            return []

        new_events = []
        if ear < self.threshold:  # eyes closed
            if self._closed_start_ms is None:
                self._closed_start_ms = timestamp_ms
                self._long_reported = False
            elapsed = (timestamp_ms - self._closed_start_ms) / 1000.0
            if elapsed + TOLERANCE_S >= self.long_closure_s and not self._long_reported:
                self._long_reported = True
                self.long_closure_count += 1
                new_events.append(EyeEvent(LONG_CLOSURE, self._closed_start_ms, elapsed * 1000))
        elif self._closed_start_ms is not None:  # eyes just opened
            duration = (timestamp_ms - self._closed_start_ms) / 1000.0
            if not self._long_reported:  # a long closure was already reported, do not count it again
                if self.blink_min_s - TOLERANCE_S <= duration <= self.blink_max_s + TOLERANCE_S:
                    self.blink_count += 1
                    new_events.append(EyeEvent(BLINK, self._closed_start_ms, duration * 1000))
                elif self.blink_max_s < duration < self.long_closure_s - TOLERANCE_S:
                    self.long_blink_count += 1
                    new_events.append(EyeEvent(LONG_BLINK, self._closed_start_ms, duration * 1000))
            self._closed_start_ms = None
            self._long_reported = False
        self.events.extend(new_events)
        return new_events

    def _calibration_step(self, timestamp_ms, ear):
        if self._calibration_start_ms is None:
            self._calibration_start_ms = timestamp_ms
        self._samples.append(ear)
        elapsed = (timestamp_ms - self._calibration_start_ms) / 1000.0
        self.remaining_s = max(0.0, self.calibration_s - elapsed)
        if elapsed >= self.calibration_s and len(self._samples) >= self.min_samples:
            self.normal_ear = float(median(self._samples))
            self.threshold = float(np.clip(self.normal_ear * self.threshold_ratio,
                                           self.threshold_min, self.threshold_max))
            self.monitoring_start_ms = timestamp_ms
