"""Unit tests for the EAR computation and the eye tracker (with synthetic EAR sequences)."""
import numpy as np
import pytest

from drowsiness.eye import BLINK, LONG_BLINK, LONG_CLOSURE, EyeTracker, compute_ear

FPS = 30
OPEN, CLOSED = 0.30, 0.10


def simulate(tracker, segments, t0_s=0.0):
    """segments: [(duration_s, ear), ...]  (ear=None: no face). Returns (end time in s, events)."""
    t, events = t0_s, []
    for duration, ear in segments:
        for _ in range(round(duration * FPS)):
            events += tracker.update(t * 1000, ear)
            t += 1 / FPS
    return t, events


@pytest.fixture
def tracker():
    """A tracker whose calibration is finished (threshold ~0.216)."""
    t = EyeTracker()
    simulate(t, [(3.5, OPEN)])
    assert t.is_calibrated
    return t


def eye_points(vertical):
    """An eye with horizontal extent 10 and vertical opening `vertical` (in the order p1..p6)."""
    y = vertical / 2
    return [(0, 0), (3, y), (7, y), (10, 0), (7, -y), (3, -y)]


def test_ear_open_and_closed_eye():
    assert compute_ear(eye_points(4)) == pytest.approx(0.4)   # (4 + 4) / (2 * 10)
    assert compute_ear(eye_points(0)) == pytest.approx(0.0)


def test_ear_zero_width_does_not_divide_by_zero():
    assert compute_ear([(1, 1)] * 6) == 0.0


def test_calibration_threshold_uses_the_median():
    t = EyeTracker()
    assert not t.is_calibrated
    simulate(t, [(3.5, OPEN)])
    assert t.is_calibrated
    assert t.normal_ear == pytest.approx(0.30)
    assert t.threshold == pytest.approx(0.30 * 0.72)


def test_blinks_during_calibration_do_not_distort_the_threshold():
    t = EyeTracker()
    simulate(t, [(1.0, OPEN), (0.2, CLOSED), (1.0, OPEN), (0.2, CLOSED), (1.5, OPEN)])
    assert t.normal_ear == pytest.approx(0.30)   # median, not affected by blinks


def test_threshold_limits():
    low, high = EyeTracker(), EyeTracker()
    simulate(low, [(3.5, 0.08)])
    simulate(high, [(3.5, 0.50)])
    assert low.threshold == pytest.approx(0.10)    # lower limit
    assert high.threshold == pytest.approx(0.28)   # upper limit


def test_no_events_during_calibration():
    t = EyeTracker()
    _, events = simulate(t, [(1.0, OPEN), (0.2, CLOSED), (1.0, OPEN)])
    assert events == [] and not t.is_calibrated
    assert t.remaining_s < 3.0


def test_blink_is_counted(tracker):
    _, events = simulate(tracker, [(1.0, OPEN), (0.2, CLOSED), (1.0, OPEN)], t0_s=3.5)
    assert tracker.blink_count == 1
    assert [e.kind for e in events] == [BLINK]
    assert events[0].duration_ms == pytest.approx(200, abs=40)


def test_multiple_blinks(tracker):
    segments = [(0.5, OPEN), (0.15, CLOSED)] * 5 + [(0.5, OPEN)]
    simulate(tracker, segments, t0_s=3.5)
    assert tracker.blink_count == 5


def test_very_short_dip_is_noise(tracker):
    simulate(tracker, [(1.0, OPEN), (1 / FPS, CLOSED), (1.0, OPEN)], t0_s=3.5)  # a single frame
    assert tracker.blink_count == 0 and tracker.long_blink_count == 0


def test_slow_blink_becomes_long_blink(tracker):
    _, events = simulate(tracker, [(1.0, OPEN), (0.8, CLOSED), (1.0, OPEN)], t0_s=3.5)
    assert tracker.long_blink_count == 1
    assert tracker.blink_count == 0 and tracker.long_closure_count == 0
    assert [e.kind for e in events] == [LONG_BLINK]


def test_long_closure_is_reported_while_eyes_are_still_closed(tracker):
    # The event must arrive when 1.5 s are up, without the eyes opening
    t, events = simulate(tracker, [(1.0, OPEN), (1.8, CLOSED)], t0_s=3.5)
    assert [e.kind for e in events] == [LONG_CLOSURE]
    assert events[0].duration_ms == pytest.approx(1500, abs=40)
    assert tracker.is_closed


def test_long_closure_counted_once_and_not_as_blink(tracker):
    _, events = simulate(tracker, [(1.0, OPEN), (3.0, CLOSED), (1.0, OPEN)], t0_s=3.5)
    assert [e.kind for e in events] == [LONG_CLOSURE]
    assert tracker.long_closure_count == 1
    assert tracker.blink_count == 0 and tracker.long_blink_count == 0


def test_consecutive_long_closures_are_counted_separately(tracker):
    segments = [(1.0, OPEN), (2.0, CLOSED), (1.0, OPEN), (2.0, CLOSED), (1.0, OPEN)]
    simulate(tracker, segments, t0_s=3.5)
    assert tracker.long_closure_count == 2


def test_face_loss_does_not_count_a_half_closure(tracker):
    simulate(tracker, [(1.0, OPEN), (0.2, CLOSED), (0.5, None), (1.0, OPEN)], t0_s=3.5)
    assert tracker.blink_count == 0
    assert not tracker.is_closed


def test_no_events_without_a_face(tracker):
    _, events = simulate(tracker, [(2.0, None)], t0_s=3.5)
    assert events == []


def test_closed_duration(tracker):
    t, _ = simulate(tracker, [(1.0, OPEN), (0.6, CLOSED)], t0_s=3.5)
    assert tracker.is_closed
    assert tracker.closed_duration_s((t - 1 / FPS) * 1000) == pytest.approx(0.6, abs=0.1)
    simulate(tracker, [(0.5, OPEN)], t0_s=t)
    assert tracker.closed_duration_s(t * 1000) == 0.0


def test_recalibration_resets_counters(tracker):
    simulate(tracker, [(1.0, OPEN), (0.2, CLOSED), (1.0, OPEN)], t0_s=3.5)
    assert tracker.blink_count == 1
    tracker.reset_calibration()
    assert not tracker.is_calibrated and tracker.blink_count == 0 and tracker.events == []


def test_blink_rate_per_minute(tracker):
    segments = [(0.9, OPEN), (0.1, CLOSED)] * 30 + [(0.5, OPEN)]   # 30 blinks in 30 s
    t, _ = simulate(tracker, segments, t0_s=3.5)
    assert tracker.blink_count == 30
    assert tracker.blink_rate_per_min(t * 1000) == pytest.approx(60, rel=0.15)


def test_blink_rate_is_none_early(tracker):
    assert tracker.blink_rate_per_min(3600) is None


def test_ear_works_with_numpy_array():
    p = np.array(eye_points(4), dtype=np.float32)
    assert compute_ear(p) == pytest.approx(0.4)
