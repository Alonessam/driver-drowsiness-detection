"""Controlled long eye closure test (work package 2: at least 90% of planned closures longer than 1.5 s are caught).

The camera runs live; the program gives "CLOSE YOUR EYES" commands at random intervals. Keep your eyes
closed for the duration of the command (default 2.5 s) and open them on the "OPEN" command. For every trial
it records whether the system caught the long eye closure. NO IMAGE IS SAVED; only the result table is written.

Usage:
    python tools/controlled_test.py [--trials 10] [--duration 2.5] [--show-video]

It runs in privacy mode by default (your face is not shown on screen, only the face mesh).
Keys: q or ESC = finish early
"""
import argparse
import csv
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.drawing import draw, draw_ear_graph, fit_to_screen, put_info, put_warning  # noqa: E402
from drowsiness.eye import LONG_CLOSURE, EyeTracker, mean_ear  # noqa: E402
from drowsiness.landmarks import FaceLandmarkDetector, to_pixels  # noqa: E402
from drowsiness.paths import ROOT  # noqa: E402
from drowsiness.source import VideoSource  # noqa: E402

WINDOW = "Controlled eye closure test"
TARGET = 90.0


def beep(frequency=880, duration_ms=150):
    try:
        import winsound
        threading.Thread(target=winsound.Beep, args=(frequency, duration_ms), daemon=True).start()
    except ImportError:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--trials", type=int, default=10, help="number of trials (default 10)")
    ap.add_argument("--duration", type=float, default=2.5, help="how long to keep the eyes closed, s (default 2.5)")
    ap.add_argument("--wait", type=float, nargs=2, default=(4.0, 7.0), metavar=("MIN", "MAX"))
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--show-video", action="store_true", help="show the real image instead of privacy mode")
    ap.add_argument("--output", type=Path, default=ROOT / "controlled_test_results.csv")
    args = ap.parse_args()

    rnd = random.Random()
    eyes = EyeTracker()
    history = []
    results = []  # (trial no, command time, caught)
    state = "calibration"   # calibration -> wait -> close -> (next trial) -> done
    trial_no, next_command_s, command_start_s = 0, None, None
    caught = False
    false_alarms = 0
    message = ""
    end_s = None

    with VideoSource(args.camera) as source, FaceLandmarkDetector() as detector:
        for _, timestamp_ms, frame in source.frames():
            t = timestamp_ms / 1000.0
            landmarks = detector.detect(frame, timestamp_ms)
            ear = None
            if landmarks is not None:
                height, width = frame.shape[:2]
                ear = mean_ear(to_pixels(landmarks, width, height))
            events = eyes.update(timestamp_ms, ear)
            history.append((t, ear))
            long_closure = any(e.kind == LONG_CLOSURE for e in events)

            if state == "calibration":
                message = f"CALIBRATION: look at the camera, eyes OPEN ({eyes.remaining_s:.0f} s)"
                if eyes.is_calibrated:
                    state, trial_no = "wait", 1
                    next_command_s = t + rnd.uniform(*args.wait)
            elif state == "wait":
                message = f"Trial {trial_no}/{args.trials}: GET READY, eyes OPEN"
                if long_closure:
                    false_alarms += 1   # long closure seen without a command
                if t >= next_command_s:
                    state, command_start_s, caught = "close", t, False
                    beep(880, 250)
            elif state == "close":
                remaining = args.duration - (t - command_start_s)
                message = f"Trial {trial_no}/{args.trials}: CLOSE YOUR EYES! ({max(remaining, 0):.1f} s)"
                caught = caught or long_closure
                if remaining <= 0:
                    beep(1320, 250)
                    state = "evaluate"
                    evaluate_start_s = t
            elif state == "evaluate":
                # Command over; wait a moment for the eyes to open and the last event to arrive
                message = "OPEN! (computing result)"
                caught = caught or long_closure
                if t - evaluate_start_s >= 1.0:
                    results.append((trial_no, round(command_start_s, 2), caught))
                    message = f"Trial {trial_no}: {'CAUGHT' if caught else 'MISSED'}"
                    if trial_no >= args.trials:
                        state, end_s = "done", t
                    else:
                        trial_no += 1
                        state = "wait"
                        next_command_s = t + rnd.uniform(*args.wait)
            if state == "done" and t - end_s > 4.0:
                break

            output = fit_to_screen(draw(frame, landmarks, privacy=not args.show_video))
            lines = [message,
                     f"EAR: {'-' if ear is None else f'{ear:.2f}'}  (threshold {eyes.threshold:.2f})" if eyes.is_calibrated else "",
                     f"Caught: {sum(1 for r in results if r[2])}/{len(results)}"]
            put_info(output, [line for line in lines if line])
            draw_ear_graph(output, history[-400:], eyes.threshold)
            if state == "close":
                put_warning(output, "CLOSE YOUR EYES!")
            cv2.imshow(WINDOW, output)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    cv2.destroyAllWindows()

    if not results:
        print("No trial was completed.")
        return
    caught_count = sum(1 for r in results if r[2])
    rate = 100.0 * caught_count / len(results)
    print(f"\nControlled test: {caught_count}/{len(results)} long eye closures caught = {rate:.0f}% "
          f"(target >= {TARGET:.0f}%: {'MET' if rate >= TARGET else 'NOT MET'})")
    print(f"False long-closure alarms outside commands: {false_alarms}")
    is_new = not args.output.exists()
    with open(args.output, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["date", "trial", "command_duration_s", "caught"])
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for no, _, c in results:
            w.writerow([stamp, no, args.duration, "yes" if c else "no"])
    print(f"Results appended: {args.output} (no image was saved)")


if __name__ == "__main__":
    main()
