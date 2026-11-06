"""Flow of the controlled long eye closure test (work package 2: planned closures longer than 1.5 s).

The test gives "close your eyes" commands at random intervals. A trial counts as caught if the eye tracker
reports a long closure between the command and one second after the end of the command.

The command must be clearly longer than the 1.5 s closure limit: a person needs about half a second to
react and tends to open the eyes a little early, so a 2.5 s command leaves hardly more than 1.5 s of real
closure and one flicker of the EAR is enough to miss it. The default is therefore 3.5 s.
"""
import random
from dataclasses import dataclass


@dataclass
class TrialResult:
    trial: int
    command_start_s: float
    caught: bool
    lowest_ear: float | None
    frames_without_face: int
    longest_closed_s: float
    threshold: float


class ClosureTrials:
    """State machine: calibration -> wait -> close -> evaluate -> (next trial) -> done."""

    def __init__(self, trials=10, duration_s=3.5, wait_s=(4.0, 7.0), result_delay_s=1.0, rnd=None):
        self.trials = trials
        self.duration_s = duration_s
        self.wait_s = wait_s
        self.result_delay_s = result_delay_s
        self.rnd = rnd or random.Random()
        self.state = "calibration"
        self.trial_no = 0
        self.results = []
        self.false_alarms = 0
        self.message = ""
        self._next_command_s = None
        self._command_start_s = None
        self._evaluate_start_s = None
        self._done_s = None
        self._reset_trial()

    def _reset_trial(self):
        self._caught = False
        self._lowest_ear = None
        self._no_face = 0
        self._longest_closed = 0.0

    @property
    def finished(self):
        return self.state == "done"

    def update(self, t, calibrated, remaining_calibration_s, ear, long_closure, closed_s, threshold):
        """Processes one frame. Returns "start" (command begins), "end" (command ends), "result" or None."""
        cue = None
        if self.state in ("close", "evaluate"):
            if ear is None:
                self._no_face += 1
            else:
                self._lowest_ear = ear if self._lowest_ear is None else min(self._lowest_ear, ear)
            self._longest_closed = max(self._longest_closed, closed_s)

        if self.state == "calibration":
            self.message = f"CALIBRATION: look at the camera, eyes OPEN ({remaining_calibration_s:.0f} s)"
            if calibrated:
                self.state, self.trial_no = "wait", 1
                self._next_command_s = t + self.rnd.uniform(*self.wait_s)
        elif self.state == "wait":
            left = self._next_command_s - t
            self.message = f"Trial {self.trial_no}/{self.trials}: GET READY, eyes OPEN" + \
                           (f" ({left:.0f})" if left < 3 else "")
            if long_closure:
                self.false_alarms += 1   # long closure seen without a command
            if t >= self._next_command_s:
                self.state, self._command_start_s = "close", t
                self._reset_trial()
                cue = "start"
        elif self.state == "close":
            remaining = self.duration_s - (t - self._command_start_s)
            self.message = f"Trial {self.trial_no}/{self.trials}: CLOSE YOUR EYES AND KEEP THEM CLOSED ({max(remaining, 0):.1f} s)"
            self._caught = self._caught or long_closure
            if remaining <= 0:
                self.state, self._evaluate_start_s = "evaluate", t
                cue = "end"
        elif self.state == "evaluate":
            # Command over; wait a moment for the eyes to open and the last event to arrive
            self.message = "OPEN YOUR EYES (computing result)"
            self._caught = self._caught or long_closure
            if t - self._evaluate_start_s >= self.result_delay_s:
                self.results.append(TrialResult(self.trial_no, round(self._command_start_s, 2), self._caught,
                                                self._lowest_ear, self._no_face, round(self._longest_closed, 2),
                                                threshold))
                self.message = f"Trial {self.trial_no}: {'CAUGHT' if self._caught else 'MISSED'}"
                cue = "result"
                if self.trial_no >= self.trials:
                    self.state, self._done_s = "done", t
                else:
                    self.trial_no += 1
                    self.state = "wait"
                    self._next_command_s = t + self.rnd.uniform(*self.wait_s)
        elif self.state == "done":
            self.message = "Test finished"
        return cue

    def done_for(self, t, seconds=4.0):
        """True once the test has been finished for `seconds` (time to read the last result)."""
        return self.state == "done" and t - self._done_s > seconds
