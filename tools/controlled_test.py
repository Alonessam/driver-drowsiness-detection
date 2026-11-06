"""Controlled long eye closure test (work package 2: at least 90% of planned closures longer than 1.5 s are caught).

The camera runs live; the program gives "CLOSE YOUR EYES" commands at random intervals. Close your eyes when
you hear the high beep and KEEP THEM CLOSED until the low beep (default 3.5 s, so that you are closed for
clearly more than 1.5 s even after your reaction time). For every trial it records whether the system caught the
long eye closure. NO IMAGE IS SAVED; only numbers (EAR values and the result table) are written.

Usage:
    python tools/controlled_test.py [--trials 10] [--duration 3.5] [--show-video]

It runs in privacy mode by default (your face is not shown on screen, only the face mesh).
Keys: q or ESC = finish early
"""
import argparse
import csv
import random
import sys
import threading
from datetime import datetime
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.controlled import ClosureTrials  # noqa: E402
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
    ap.add_argument("--duration", type=float, default=3.5, help="length of the command, s (default 3.5)")
    ap.add_argument("--wait", type=float, nargs=2, default=(4.0, 7.0), metavar=("MIN", "MAX"))
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--show-video", action="store_true", help="show the real image instead of privacy mode")
    ap.add_argument("--output", type=Path, default=ROOT / "controlled_test_results.csv")
    ap.add_argument("--trace", type=Path, default=ROOT / "controlled_test_trace.csv",
                    help="numeric EAR trace of the last run (no images), for diagnosing misses")
    args = ap.parse_args()

    eyes = EyeTracker()
    flow = ClosureTrials(args.trials, args.duration, tuple(args.wait), rnd=random.Random())
    history = []
    trace = []   # (time_s, ear, state, closed_s)

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
            closed_s = eyes.closed_duration_s(timestamp_ms)
            cue = flow.update(t, eyes.is_calibrated, eyes.remaining_s, ear,
                              any(e.kind == LONG_CLOSURE for e in events), closed_s, eyes.threshold)
            trace.append((round(t, 3), "" if ear is None else round(ear, 4), flow.state, round(closed_s, 2)))
            if cue == "start":
                beep(880, 300)
            elif cue == "end":
                beep(1320, 300)
            elif cue == "result":
                r = flow.results[-1]
                print(f"Trial {r.trial}: {'caught' if r.caught else 'MISSED'} | lowest EAR "
                      f"{'-' if r.lowest_ear is None else f'{r.lowest_ear:.2f}'} (threshold {r.threshold:.2f}) | "
                      f"frames without face {r.frames_without_face} | longest closed {r.longest_closed_s:.1f} s",
                      flush=True)
            if flow.done_for(t):
                break

            output = fit_to_screen(draw(frame, landmarks, privacy=not args.show_video))
            caught_now = sum(1 for r in flow.results if r.caught)
            lines = [flow.message,
                     f"EAR: {'-' if ear is None else f'{ear:.2f}'}  (threshold {eyes.threshold:.2f})" if eyes.is_calibrated else "",
                     f"Caught: {caught_now}/{len(flow.results)}"]
            put_info(output, [line for line in lines if line])
            draw_ear_graph(output, history[-400:], eyes.threshold)
            if flow.state == "close":
                put_warning(output, "EYES CLOSED - KEEP THEM CLOSED")
            cv2.imshow(WINDOW, output)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    cv2.destroyAllWindows()

    with open(args.trace, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "ear", "state", "closed_s"])
        w.writerows(trace)

    results = flow.results
    if not results:
        print("No trial was completed.")
        return
    caught_count = sum(1 for r in results if r.caught)
    rate = 100.0 * caught_count / len(results)
    print(f"\nControlled test: {caught_count}/{len(results)} long eye closures caught = {rate:.0f}% "
          f"(target >= {TARGET:.0f}%: {'MET' if rate >= TARGET else 'NOT MET'})")
    print(f"False long-closure alarms outside commands: {flow.false_alarms}")
    is_new = not args.output.exists()
    with open(args.output, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["date", "trial", "command_duration_s", "caught", "lowest_ear", "threshold",
                        "frames_without_face", "longest_closed_s"])
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for r in results:
            w.writerow([stamp, r.trial, args.duration, "yes" if r.caught else "no",
                        "" if r.lowest_ear is None else round(r.lowest_ear, 3), round(r.threshold, 3),
                        r.frames_without_face, r.longest_closed_s])
    print(f"Results appended: {args.output}\nEAR trace (numbers only): {args.trace}\nNo image was saved.")


if __name__ == "__main__":
    main()
