"""Evaluates yawn detection (work package 3).

(a) Recall: detected yawns versus manually labeled yawns in the test videos (target: at least 85 %).
    Labels are created with  python tools/label_events.py <video> --kind yawn  (stored in labels/yawn/).
(b) False yawns: yawns detected in videos where the driver only talks (target: at most 1 per video).

Usage:
    python tools/evaluate_yawns.py                    # both parts
    python tools/evaluate_yawns.py --skip-talking     # only the labeled test videos
    python tools/evaluate_yawns.py --skip-labels      # only the talking videos
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import match_events, read_labels  # noqa: E402
from drowsiness.mouth_evaluation import video_yawn_events  # noqa: E402
from drowsiness.paths import ROOT, YAWDD_DIR, resolve_video  # noqa: E402

TARGET_RECALL = 85.0
MAX_FALSE_PER_VIDEO = 1


def evaluate_labels(files, tolerance):
    rows, totals = [], [0, 0, 0]
    print(f"{'video':<40}{'labels':>7}{'TP':>5}{'FN':>5}{'FP':>5}{'recall':>12}")
    for file in files:
        video, labels = read_labels(file, "yawn_times_s")
        _, events = video_yawn_events(resolve_video(video))
        tp, fn, fp = match_events(labels, events, tolerance)
        recall = 100.0 * tp / len(labels) if labels else float("nan")
        print(f"{Path(video).name[:39]:<40}{len(labels):>7}{tp:>5}{fn:>5}{fp:>5}{recall:>11.1f}%")
        rows.append([Path(video).name, len(labels), tp, fn, fp, round(recall, 1)])
        totals[0] += tp; totals[1] += fn; totals[2] += fp
    tp, fn, fp = totals
    recall = 100.0 * tp / (tp + fn) if tp + fn else float("nan")
    print(f"\nTOTAL: labels {tp + fn} | detected {tp} | missed {fn} | extra detections {fp}")
    print(f"Recall (share of labeled yawns detected): {recall:.1f}%   (target >= {TARGET_RECALL:.0f}%: "
          f"{'MET' if recall >= TARGET_RECALL else 'NOT MET'})")
    return rows


def evaluate_talking(folder, limit):
    # "Talking&Yawning" videos contain real yawns, so only pure talking videos are used
    videos = sorted(p for p in folder.rglob("*-Talking.avi"))
    if limit:
        videos = videos[:limit]
    rows = []
    print(f"\nFalse yawns in {len(videos)} talking videos (folder: {folder})")
    for i, video in enumerate(videos, 1):
        _, events = video_yawn_events(video)
        rows.append([video.name, len(events)])
        print(f"[{i}/{len(videos)}] {video.name}: {len(events)} yawn(s) detected", flush=True)
    counts = [r[1] for r in rows]
    if counts:
        over = sum(1 for c in counts if c > MAX_FALSE_PER_VIDEO)
        print(f"\nTalking videos: {len(counts)} | mean {sum(counts) / len(counts):.2f} false yawns per video | "
              f"max {max(counts)} | videos above {MAX_FALSE_PER_VIDEO}: {over} "
              f"(target: at most {MAX_FALSE_PER_VIDEO} per video: {'MET' if over == 0 else 'NOT MET'})")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--tolerance", type=float, default=0.5, help="label matching tolerance (s, default 0.5)")
    ap.add_argument("--talking-dir", type=Path, default=YAWDD_DIR / "Mirror")
    ap.add_argument("--limit", type=int, default=0, help="at most this many talking videos (0 = all)")
    ap.add_argument("--skip-labels", action="store_true")
    ap.add_argument("--skip-talking", action="store_true")
    ap.add_argument("--output", type=Path, default=ROOT / "yawn_evaluation.csv")
    args = ap.parse_args()

    label_rows, talking_rows = [], []
    if not args.skip_labels:
        files = sorted((ROOT / "labels" / "yawn").glob("*.json"))
        if files:
            label_rows = evaluate_labels(files, args.tolerance)
        else:
            print("No yawn label files yet (labels/yawn/*.json). Label the test videos first:\n"
                  "  python tools/test_videos.py label --kind yawn")
    if not args.skip_talking:
        talking_rows = evaluate_talking(args.talking_dir, args.limit)

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["part", "video", "labels", "TP", "FN", "extra", "recall_percent_or_false_yawns"])
        for r in label_rows:
            w.writerow(["labeled", r[0], r[1], r[2], r[3], r[4], r[5]])
        for r in talking_rows:
            w.writerow(["talking", r[0], "", "", "", "", r[1]])
    print(f"CSV: {args.output}")


if __name__ == "__main__":
    main()
