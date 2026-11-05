"""Yawn detection with the MAR (Mouth Aspect Ratio).

MAR = ||p13 - p14|| / ||p78 - p308||
(inner upper lip / inner lower lip, divided by the distance between the inner mouth corners)
It is close to 0 for a closed mouth and grows when the mouth opens wide. A yawn is a wide-open mouth
that stays open for at least about one second; speaking opens the mouth too, but only briefly.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from .landmarks import MOUTH


def compute_mar(p):
    """MAR from the 4 mouth points [upper lip, lower lip, left corner, right corner] as (4, 2) pixel coordinates."""
    p = np.asarray(p, dtype=np.float64)
    width = np.linalg.norm(p[2] - p[3])
    if width == 0:
        return 0.0
    return float(np.linalg.norm(p[0] - p[1]) / width)


def mouth_mar(points_px):
    """MAR from the (478, 2) pixel landmarks."""
    return compute_mar(points_px[MOUTH])


@dataclass
class YawnEvent:
    start_ms: float
    duration_ms: float   # set to the minimum duration when reported, updated to the full length when the mouth closes


class YawnTracker:
    """Takes the MAR frame by frame and counts yawns.

    Durations come from frame timestamps (ms), so they are correct for video and camera alike.

    mar_threshold: MAR above this value counts as "mouth open". Defaults come from measurements on the 307 YawDD
                    Mirror videos (see README): 0.4 / 0.5 / 1 s / 0.2 s.
    peak_threshold: To be a yawn the opening must also reach this MAR at least once (a wide opening). It keeps
                    ordinary speech, which stays open at a moderate MAR, from counting. Never below mar_threshold.
    min_duration_s: The mouth must stay open this long to count as a yawn; the event is reported at the
                    moment this time is reached (while the mouth is still open).
    gap_tolerance_s: Short dips below the threshold (noise, tongue/teeth shadows) shorter than this do not
                    end the open state.
    face_loss_tolerance_s: Face lost for a shorter time while the mouth was open (e.g. a hand covering the
                    mouth) does not end the open state; the lost time still counts as open time.
    """

    def __init__(self, mar_threshold=0.4, min_duration_s=1.0, gap_tolerance_s=0.2, face_loss_tolerance_s=0.5,
                 peak_threshold=0.5):
        self.mar_threshold = mar_threshold
        self.peak_threshold = max(peak_threshold, mar_threshold)
        self.min_duration_s = min_duration_s
        self.gap_tolerance_s = gap_tolerance_s
        self.face_loss_tolerance_s = face_loss_tolerance_s
        self.reset()

    def reset(self):
        """Resets counters and state (e.g. when switching to another driver)."""
        self.last_mar = None
        self.yawn_count = 0
        self.events = []
        self._open_start_ms = None
        self._last_open_ms = None     # last time the mouth was seen open
        self._last_seen_ms = None     # last time a face was seen
        self._reported = False
        self._peak = 0.0
        self._yawn_times = deque()

    @property
    def is_open(self):
        return self._open_start_ms is not None

    def open_duration_s(self, timestamp_ms):
        """How long the mouth has been wide open right now (s); 0 if it is closed."""
        if self._open_start_ms is None:
            return 0.0
        return (timestamp_ms - self._open_start_ms) / 1000.0

    def recent_yawns(self, timestamp_ms, window_s=300.0):
        """Number of yawns in the last `window_s` seconds (default 5 minutes)."""
        while self._yawn_times and timestamp_ms - self._yawn_times[0] > window_s * 1000:
            self._yawn_times.popleft()
        return len(self._yawn_times)

    def update(self, timestamp_ms, mar):
        """Processes one frame. mar: MAR of that frame, or None if there is no face. Returns the new events."""
        self.last_mar = mar
        if mar is None:
            if self._open_start_ms is not None and self._last_seen_ms is not None \
                    and (timestamp_ms - self._last_seen_ms) / 1000.0 > self.face_loss_tolerance_s:
                self._close(self._last_open_ms)
            return []   # nothing is reported while the face is missing

        self._last_seen_ms = timestamp_ms
        if mar > self.mar_threshold:
            if self._open_start_ms is None:
                self._open_start_ms = timestamp_ms
                self._reported = False
                self._peak = 0.0
            self._peak = max(self._peak, mar)
            self._last_open_ms = timestamp_ms
        elif self._open_start_ms is not None \
                and (timestamp_ms - self._last_open_ms) / 1000.0 > self.gap_tolerance_s:
            self._close(self._last_open_ms)
        return self._maybe_report(timestamp_ms)

    def finish(self):
        """Call when the video ends so that a yawn still in progress gets its final duration."""
        if self._open_start_ms is not None:
            self._close(self._last_open_ms)

    def _maybe_report(self, timestamp_ms):
        if self._open_start_ms is None or self._reported:
            return []
        if (timestamp_ms - self._open_start_ms) / 1000.0 + 0.001 < self.min_duration_s                 or self._peak < self.peak_threshold:
            return []
        self._reported = True
        self.yawn_count += 1
        self._yawn_times.append(timestamp_ms)
        event = YawnEvent(self._open_start_ms, self.min_duration_s * 1000)
        self.events.append(event)
        return [event]

    def _close(self, end_ms):
        if self._reported and self.events:
            self.events[-1].duration_ms = max(self.events[-1].duration_ms, end_ms - self._open_start_ms)
        self._open_start_ms = None
        self._last_open_ms = None
        self._reported = False
