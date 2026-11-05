"""Unit tests for the label-event matching logic."""
from drowsiness.eye import BLINK, EyeEvent
from drowsiness.eye_evaluation import match_events, read_labels, write_labels


def event(start_s, duration_s=0.2):
    return EyeEvent(BLINK, start_s * 1000, duration_s * 1000)


def test_perfect_match():
    assert match_events([5.1, 8.0], [event(5.0), event(7.9)]) == (2, 0, 0)


def test_missed_label():
    assert match_events([5.1, 8.0, 12.0], [event(5.0), event(7.9)]) == (2, 1, 0)


def test_false_alarm():
    assert match_events([5.1], [event(5.0), event(9.0)]) == (1, 0, 1)


def test_no_match_outside_tolerance():
    assert match_events([5.0], [event(6.0)]) == (0, 1, 1)


def test_match_within_tolerance():
    assert match_events([5.4], [event(5.0)], tolerance_s=0.25) == (1, 0, 0)   # event 5.0-5.2, +0.25 -> 5.45


def test_one_event_does_not_match_two_labels():
    assert match_events([5.0, 5.1], [event(5.0)]) == (1, 1, 0)


def test_empty_inputs():
    assert match_events([], []) == (0, 0, 0)
    assert match_events([3.0], []) == (0, 1, 0)
    assert match_events([], [event(3.0)]) == (0, 0, 1)


def test_label_file_round_trip(tmp_path):
    path = tmp_path / "labels" / "video.json"
    write_labels(path, "videos/sample video.avi", [8.5, 2.25, 5.0])
    video, times = read_labels(path)
    assert video == "videos/sample video.avi"
    assert times == [2.25, 5.0, 8.5]
