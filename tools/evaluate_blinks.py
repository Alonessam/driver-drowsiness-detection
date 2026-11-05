"""Compares blink detection with manual labels (success criterion: at least 85% of manually counted blinks).

Usage:
    python tools/evaluate_blinks.py                       # all labels/*.json files
    python tools/evaluate_blinks.py labels/name.json ...  # specific label files

Every label file is created with tools/label_events.py and contains the video it belongs to.
Blinks made during calibration (first ~3 s) cannot be counted, so they are left out of the evaluation.
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import (BLINK_KINDS, calibration_end_s, match_events,  # noqa: E402
                                       read_labels, video_eye_events)
from drowsiness.paths import ROOT, resolve_video  # noqa: E402

TARGET = 85.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("labels", nargs="*", type=Path)
    ap.add_argument("--tolerance", type=float, default=0.25, help="matching tolerance (s, default 0.25)")
    ap.add_argument("--output", type=Path, default=ROOT / "blink_evaluation.csv")
    args = ap.parse_args()

    files = args.labels or sorted((ROOT / "labels").glob("*.json"))
    if not files:
        raise SystemExit("No label files. Label the videos first with tools/label_events.py.")

    rows = []
    totals = [0, 0, 0]
    print(f"{'video':<40}{'labels':>7}{'TP':>5}{'FN':>5}{'FP':>5}{'recall':>12}{'precision':>11}")
    for file in files:
        video, labels = read_labels(file)
        tracker, events = video_eye_events(resolve_video(video))
        blinks = [e for e in events if e.kind in BLINK_KINDS]
        calibration_end = calibration_end_s(tracker)
        valid = [t for t in labels if t >= calibration_end]
        excluded = len(labels) - len(valid)
        tp, fn, fp = match_events(valid, blinks, args.tolerance)
        recall = 100.0 * tp / len(valid) if valid else float("nan")
        precision = 100.0 * tp / (tp + fp) if tp + fp else float("nan")
        name = Path(video).name + (f" (-{excluded} in calibration)" if excluded else "")
        print(f"{name[:39]:<40}{len(valid):>7}{tp:>5}{fn:>5}{fp:>5}{recall:>11.1f}%{precision:>10.1f}%")
        rows.append([Path(video).name, len(labels), excluded, len(valid), tp, fn, fp,
                     round(recall, 1), round(precision, 1)])
        totals[0] += tp; totals[1] += fn; totals[2] += fp

    tp, fn, fp = totals
    recall = 100.0 * tp / (tp + fn) if tp + fn else float("nan")
    precision = 100.0 * tp / (tp + fp) if tp + fp else float("nan")
    print(f"\nTOTAL: labels {tp + fn} | correct {tp} | missed {fn} | false alarms {fp}")
    print(f"Recall (share of labeled blinks detected): {recall:.1f}%   (target >= {TARGET:.0f}%: "
          f"{'MET' if recall >= TARGET else 'NOT MET'})")
    print(f"Precision (share of detections that are correct): {precision:.1f}%")

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["video", "label_count", "excluded_in_calibration", "evaluated", "TP", "FN", "FP",
                    "recall_percent", "precision_percent"])
        w.writerows(rows)
    print(f"CSV: {args.output}")


if __name__ == "__main__":
    main()
