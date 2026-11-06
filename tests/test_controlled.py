"""Tests of the controlled test flow with a simulated person (reaction delay, early opening, EAR flicker)."""
import random

import pytest

from drowsiness.controlled import ClosureTrials
from drowsiness.eye import LONG_CLOSURE, EyeTracker

FPS = 30
OPEN, CLOSED = 0.30, 0.10


def run_session(person, trials=5, duration_s=3.5, seed=1, face_loss=None):
    """person(command_t, t) -> EAR at time t given the start time of the current command (None = no command).

    Runs the real EyeTracker and the trial flow on a simulated frame stream. Returns the ClosureTrials object.
    """
    tracker = EyeTracker()
    flow = ClosureTrials(trials=trials, duration_s=duration_s, wait_s=(2.0, 3.0), rnd=random.Random(seed))
    command_t = None
    t = 0.0
    while not flow.done_for(t, 0.5) and t < 600:
        ear = person(command_t, t)
        if face_loss and command_t is not None and face_loss(command_t, t):
            ear = None
        events = tracker.update(t * 1000, ear)
        long_closure = any(e.kind == LONG_CLOSURE for e in events)
        cue = flow.update(t, tracker.is_calibrated, tracker.remaining_s, ear, long_closure,
                          tracker.closed_duration_s(t * 1000), tracker.threshold)
        if cue == "start":
            command_t = t
        elif cue == "result":
            command_t = None
        t += 1 / FPS
    return flow


def obedient(reaction_s=0.7, open_early_s=0.0, duration_s=3.5):
    """Closes the eyes `reaction_s` after the command and opens them `open_early_s` before it ends."""
    def person(command_t, t):
        if command_t is None:
            return OPEN
        elapsed = t - command_t
        return CLOSED if reaction_s <= elapsed < duration_s - open_early_s else OPEN
    return person


def test_all_trials_caught_with_a_typical_person():
    flow = run_session(obedient(reaction_s=0.7, open_early_s=0.2))
    assert len(flow.results) == 5
    assert all(r.caught for r in flow.results)
    assert flow.false_alarms == 0


def test_a_slow_person_is_still_caught_with_the_default_duration():
    flow = run_session(obedient(reaction_s=1.2, open_early_s=0.3))
    assert all(r.caught for r in flow.results)


def test_the_old_2_5_second_command_was_too_tight():
    # reaction 1.0 s and opening 0.2 s early leaves only 1.3 s of closure: a miss caused by the test design
    flow = run_session(obedient(reaction_s=1.0, open_early_s=0.2, duration_s=2.5), duration_s=2.5)
    assert not any(r.caught for r in flow.results)
    flow = run_session(obedient(reaction_s=1.0, open_early_s=0.2, duration_s=3.5), duration_s=3.5)
    assert all(r.caught for r in flow.results)


def test_person_who_ignores_the_command_is_missed_and_diagnostics_show_open_eyes():
    flow = run_session(lambda command_t, t: OPEN, trials=2)
    assert [r.caught for r in flow.results] == [False, False]
    assert all(r.lowest_ear == pytest.approx(OPEN) and r.longest_closed_s == 0 for r in flow.results)


def test_diagnostics_report_face_loss():
    def lost(command_t, t):
        return command_t is not None and t - command_t > 0.5
    flow = run_session(obedient(), trials=1, face_loss=lost)
    r = flow.results[0]
    assert not r.caught
    assert r.frames_without_face > 50


def test_short_face_loss_during_the_closure_does_not_break_it():
    def lost(command_t, t):
        return command_t is not None and 1.5 <= t - command_t < 1.7   # 0.2 s
    flow = run_session(obedient(), trials=3, face_loss=lost)
    assert all(r.caught for r in flow.results)


def test_closure_before_any_command_counts_as_a_false_alarm():
    state = {"first": True}

    def person(command_t, t):
        if command_t is None and 3.5 < t < 6.0 and state["first"]:
            return CLOSED
        return OPEN if command_t is None else (CLOSED if 0.7 <= t - command_t < 3.5 else OPEN)

    flow = run_session(person, trials=1, seed=3)
    assert flow.false_alarms >= 1
