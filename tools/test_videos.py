"""Walks through the work package 2 test videos for labeling and shows the label status.

Usage:
    python tools/test_videos.py label          # opens unlabeled videos one by one (labeled ones are skipped)
    python tools/test_videos.py label --all    # also reopens labeled ones (continues the previous marks)
    python tools/test_videos.py status         # which video has how many blinks labeled
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import read_labels  # noqa: E402
from drowsiness.paths import ROOT, resolve_video  # noqa: E402

LIST = ROOT / "labels" / "test_videos.txt"
LABELER = ROOT / "tools" / "label_blinks.py"


def videos():
    return [resolve_video(s.strip()) for s in LIST.read_text(encoding="utf-8").splitlines() if s.strip()]


def label_path(video):
    return ROOT / "labels" / f"{video.stem}.json"


def print_status():
    done = 0
    for i, v in enumerate(videos(), 1):
        path = label_path(v)
        if path.exists():
            _, times = read_labels(path)
            done += 1
            print(f"{i}. [x] {v.name}: {len(times)} blinks marked")
        else:
            print(f"{i}. [ ] {v.name}: not labeled yet")
    print(f"\nLabeled videos: {done}/{len(videos())}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["label", "status"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--speed", default="0.25")
    args = ap.parse_args()

    if args.command == "status":
        print_status()
        return
    for i, v in enumerate(videos(), 1):
        if label_path(v).exists() and not args.all:
            print(f"{i}. {v.name}: already labeled, skipped")
            continue
        print(f"\n{i}/{len(videos())}  {v.name}")
        print("Press B at every blink. Press Q when done to save and open the next video.")
        subprocess.run([sys.executable, str(LABELER), str(v), "--speed", args.speed], check=False)
    print("\nDone.")
    print_status()


if __name__ == "__main__":
    main()
