"""Measures the face detection rate and processing speed on the videos in a folder (work package 1 criteria).

Usage:
    python measure_detection.py data/YawDD --output yawdd_detection_rate.csv
    python measure_detection.py data/YawDD --max-frames 300     # first 300 frames of each video

Metrics: percentage of frames with face landmarks (target >= 90%) and processing speed (target >= 15 fps).
Results are also split by glasses type (NoGlasses / Glasses / SunGlasses in the file name).
"""
import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path

from drowsiness.landmarks import FaceLandmarkDetector
from drowsiness.source import VideoSource

EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".m4v"}
GLASSES_GROUPS = ("no_glasses", "glasses", "sunglasses", "unknown")


def glasses_type(file_name):
    """Extracts the glasses type from a YawDD file name (NoGlasses, SunGlasses, Glasses)."""
    name = file_name.lower()
    if "noglasses" in name:
        return "no_glasses"
    if "sunglasses" in name:
        return "sunglasses"
    if "glasses" in name:
        return "glasses"
    return "unknown"


def measure_video(path, max_frames):
    """Returns (frame count, frames with a face, total seconds) for one video."""
    frame_count = found = 0
    with VideoSource(str(path)) as source, FaceLandmarkDetector() as detector:
        start = time.perf_counter()
        for frame_no, timestamp_ms, frame in source.frames():
            if max_frames and frame_no >= max_frames:
                break
            if detector.detect(frame, timestamp_ms) is not None:
                found += 1
            frame_count += 1
        seconds = time.perf_counter() - start
    return frame_count, found, seconds


def print_summary(title, rows):
    """rows: (video, frames, found, rate, fps, seconds, glasses)"""
    total = sum(r[1] for r in rows)
    found = sum(r[2] for r in rows)
    seconds = sum(r[5] for r in rows)
    if not total:
        return
    print(f"{title:<16}: {len(rows):>3} videos | face detection rate {100 * found / total:5.1f}% | "
          f"90%+ videos {sum(1 for r in rows if r[3] >= 90):>3}/{len(rows):<3} | "
          f"{total / seconds:6.1f} fps")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("folder", type=Path, help="folder containing the videos (including subfolders)")
    ap.add_argument("--output", type=Path, default=Path("detection_rate.csv"))
    ap.add_argument("--max-frames", type=int, default=0, help="at most this many frames per video (0 = all)")
    ap.add_argument("--no-subfolders", action="store_true", help="do not look into subfolders")
    args = ap.parse_args()

    files = args.folder.glob("*") if args.no_subfolders else args.folder.rglob("*")
    videos = sorted(p for p in files if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not videos:
        raise SystemExit(f"No videos found in folder: {args.folder}")

    rows = []
    for i, path in enumerate(videos, 1):
        try:
            n, found, seconds = measure_video(path, args.max_frames)
        except OSError as error:
            print(f"[{i}/{len(videos)}] SKIPPED {path.name}: {error}", flush=True)
            continue
        rate = 100.0 * found / n if n else 0.0
        fps = n / seconds if seconds else 0.0
        rows.append((str(path.relative_to(args.folder)), n, found, round(rate, 1), round(fps, 1),
                     seconds, glasses_type(path.name)))
        print(f"[{i}/{len(videos)}] {path.name}: {n} frames, face {rate:.1f}%, {fps:.1f} fps", flush=True)

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["video", "frames", "face_frames", "face_rate_percent", "fps", "glasses"])
        w.writerows([r[:5] + (r[6],) for r in rows])

    print("\n--- SUMMARY (targets: face detection rate >= 90%, processing speed >= 15 fps) ---")
    print_summary("ALL VIDEOS", rows)
    groups = defaultdict(list)
    for r in rows:
        groups[r[6]].append(r)
    for name in GLASSES_GROUPS:
        if name in groups:
            print_summary(name, groups[name])
    print("\n5 videos with the lowest detection rate:")
    for r in sorted(rows, key=lambda r: r[3])[:5]:
        print(f"  {r[3]:5.1f}%  {r[0]}  ({r[6]})")
    print(f"\nCSV: {args.output}")


if __name__ == "__main__":
    main()
