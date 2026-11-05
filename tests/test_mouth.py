"""Unit tests for the MAR computation and the yawn tracker (with synthetic MAR sequences)."""
import numpy as np
import pytest

from drowsiness.mouth import YawnTracker, compute_mar

FPS = 30
CLOSED, WIDE, TALK = 0.05, 0.9, 0.7


def simulate(tracker, segments, t0_s=0.0):
    """segments: [(duration_s, mar), ...]  (mar=None: no face). Returns (end time in s, events)."""
    t, events = t0_s, []
    for duration, mar in segments:
        for _ in range(round(duration * FPS)):
            events += tracker.update(t * 1000, mar)
            t += 1 / FPS
    return t, events


def mouth_points(opening, width=10.0):
    """[upper lip, lower lip, left corner, right corner] for a mouth that is `opening` high and `width` wide."""
    return [(5, 0), (5, opening), (0, opening / 2), (width, opening / 2)]


def test_mar_closed_and_open_mouth():
    assert compute_mar(mouth_points(0)) == pytest.approx(0.0)
    assert compute_mar(mouth_points(8)) == pytest.approx(0.8)    # 8 / 10


def test_mar_zero_width_does_not_divide_by_zero():
    assert compute_mar([(1, 1)] * 4) == 0.0


def test_mar_works_with_numpy_array():
    assert compute_mar(np.array(mouth_points(6), dtype=np.float32)) == pytest.approx(0.6)


def test_wide_open_mouth_for_two_seconds_is_a_yawn():
    t = YawnTracker()
    _, events = simulate(t, [(1.0, CLOSED), (2.0, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 1 and len(events) == 1
    assert events[0].start_ms == pytest.approx(1000, abs=40)
    assert t.events[0].duration_ms == pytest.approx(2000, abs=100)   # updated when the mouth closed


def test_yawn_is_reported_while_the_mouth_is_still_open():
    t = YawnTracker()
    _, events = simulate(t, [(1.0, CLOSED), (1.5, WIDE)])
    assert len(events) == 1 and t.is_open
    assert t.open_duration_s(2400) == pytest.approx(1.4, abs=0.1)


def test_open_shorter_than_minimum_is_not_a_yawn():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.6, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 0 and not t.is_open


def test_exactly_the_minimum_duration_counts():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (1.0 + 1 / FPS, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 1


def test_speech_like_short_openings_are_ignored():
    t = YawnTracker()
    segments = [(0.4, TALK), (0.3, CLOSED)] * 8
    simulate(t, segments)
    assert t.yawn_count == 0


def test_moderate_opening_below_threshold_is_ignored():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (3.0, 0.45), (1.0, CLOSED)])
    assert t.yawn_count == 0


def test_opening_must_reach_the_peak_threshold():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (1.5, 0.45), (1.0, CLOSED)])    # open (>0.4) for long enough, but never wide (<0.5)
    assert t.yawn_count == 0
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.6, 0.45), (0.8, 0.6), (1.0, CLOSED)])    # starts moderate, then opens wide
    assert t.yawn_count == 1


def test_a_long_yawn_is_counted_once():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (5.0, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 1


def test_two_separate_yawns():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (1.5, WIDE), (2.0, CLOSED), (1.5, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 2


def test_short_dip_inside_a_yawn_does_not_split_it():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.8, WIDE), (0.1, CLOSED), (0.8, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 1


def test_long_pause_between_two_openings_splits_them():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.8, WIDE), (0.5, CLOSED), (0.8, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 0     # neither opening lasted a full second


def test_short_face_loss_during_a_yawn_keeps_it_open():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.6, WIDE), (0.3, None), (0.8, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 1


def test_long_face_loss_ends_the_open_state():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (0.6, WIDE), (1.5, None), (0.6, WIDE), (1.0, CLOSED)])
    assert t.yawn_count == 0


def test_no_events_without_a_face():
    t = YawnTracker()
    _, events = simulate(t, [(3.0, None)])
    assert events == [] and not t.is_open


def test_recent_yawns_window():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (1.5, WIDE), (1.0, CLOSED)])
    assert t.recent_yawns(5000) == 1
    assert t.recent_yawns(5000 + 301_000) == 0      # older than 5 minutes


def test_reset_clears_everything():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (2.0, WIDE)])
    t.reset()
    assert t.yawn_count == 0 and t.events == [] and not t.is_open and t.last_mar is None


def test_finish_sets_the_final_duration_of_a_yawn_in_progress():
    t = YawnTracker()
    simulate(t, [(1.0, CLOSED), (3.0, WIDE)])
    t.finish()
    assert t.events[0].duration_ms == pytest.approx(3000, abs=100)
