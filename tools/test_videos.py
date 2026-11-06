"""Walks through the test videos for labeling and shows the label status.

Usage:
    python tools/test_videos.py label                  # blink test videos (work package 2), unlabeled ones one by one
    python tools/test_videos.py label --kind yawn      # yawn test videos (work package 3)
    python tools/test_videos.py label --all            # also reopens labeled ones (continues the previous marks)
    python tools/test_videos.py label --fresh          # label ALL videos again from scratch (old labels are kept)
    python tools/test_videos.py one [--kind yawn]      # pick ONE video from the list and (re)label it
    python tools/test_videos.py status [--kind yawn]   # which video has how many events labeled
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import read_labels  # noqa: E402
from drowsiness.paths import ROOT, resolve_video  # noqa: E402

LABELER = ROOT / "tools" / "label_events.py"
KINDS = {
    "blink": {"list": ROOT / "labels" / "test_videos.txt", "folder": ROOT / "labels",
              "key": "blink_times_s", "noun": "blink", "hint": "Press B at every blink."},
    "yawn": {"list": ROOT / "labels" / "yawn_test_videos.txt", "folder": ROOT / "labels" / "yawn",
             "key": "yawn_times_s", "noun": "yawn", "hint": "Press B once in the middle of every yawn."},
}


def videos(kind):
    return [resolve_video(s.strip()) for s in kind["list"].read_text(encoding="utf-8").splitlines() if s.strip()]


def label_path(kind, video):
    return kind["folder"] / f"{video.stem}.json"


def print_status(kind):
    done = 0
    for i, v in enumerate(videos(kind), 1):
        path = label_path(kind, v)
        if path.exists():
            _, times = read_labels(path, kind["key"])
            done += 1
            print(f"{i}. [x] {v.name}: {len(times)} {kind['noun']}s marked")
        else:
            print(f"{i}. [ ] {v.name}: not labeled yet")
    print(f"\nLabeled videos: {done}/{len(videos(kind))}")


def ask(prompt):
    """input() that shows the prompt on standard output.

    The batch menus redirect standard error to a log file, and input() writes its prompt there when it is
    redirected, which would hide the question from the user.
    """
    print(prompt, end="", flush=True)
    return input()


def label_one(kind_name, kind):
    """Lists the test videos, lets the user pick one and label it (continue the old marks or start again)."""
    vids = videos(kind)
    for i, v in enumerate(vids, 1):
        path = label_path(kind, v)
        info = f"{len(read_labels(path, kind['key'])[1])} {kind['noun']}s marked" if path.exists() else "not labeled yet"
        print(f"  {i}. {v.name}  ({info})")
    choice = ask(f"\nVideo number (1-{len(vids)}, Enter = cancel): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(vids):
        print("Cancelled.")
        return
    video = vids[int(choice) - 1]
    fresh = False
    if label_path(kind, video).exists():
        answer = ask("Existing labels found. [C]ontinue editing them or [R]edo from scratch "
                     "(old labels are kept)? [C/R]: ").strip().lower()
        fresh = answer.startswith("r")
    print(f"\n{video.name}\n{kind['hint']} Press Q when done to save.")
    command = [sys.executable, str(LABELER), str(video), "--kind", kind_name] + (["--fresh"] if fresh else [])
    subprocess.run(command, check=False)
    print_status(kind)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["label", "status", "one"])
    ap.add_argument("--kind", choices=KINDS, default="blink")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="label every video again from scratch; old labels are kept in 'previous'")
    args = ap.parse_args()
    kind = KINDS[args.kind]

    if args.command == "status":
        print_status(kind)
        return
    if args.command == "one":
        label_one(args.kind, kind)
        return
    for i, v in enumerate(videos(kind), 1):
        if label_path(kind, v).exists() and not args.all and not args.fresh:
            print(f"{i}. {v.name}: already labeled, skipped")
            continue
        print(f"\n{i}/{len(videos(kind))}  {v.name}")
        print(f"{kind['hint']} Press Q when done to save and open the next video.")
        command = [sys.executable, str(LABELER), str(v), "--kind", args.kind] + (["--fresh"] if args.fresh else [])
        subprocess.run(command, check=False)
    print("\nDone.")
    print_status(kind)


if __name__ == "__main__":
    main()
