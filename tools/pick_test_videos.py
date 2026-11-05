"""Picks the yawn test videos with a fixed, documented rule (so the choice cannot be cherry-picked).

Rule: YawDD Mirror "Yawning" videos with image sharing permission "yes", no sunglasses, and a face found in
at least 95 % of the first 300 frames. Candidates are shuffled with a fixed seed (default 2026) and taken
in that order until there are 3 videos without glasses and 2 with glasses.

Usage: python tools/pick_test_videos.py [--seed 2026]   (writes labels/yawn_test_videos.txt)
Needs yawdd_sharing_permission.csv (build it with tools/yawdd_permission_list.py).
"""
import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.paths import ROOT, YAWDD_DIR  # noqa: E402
from measure_detection import measure_video  # noqa: E402

WANTED = {"NoGlasses": 3, "Glasses": 2}
MIN_FACE_RATE = 95.0
CHECK_FRAMES = 300


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--output", type=Path, default=ROOT / "labels" / "yawn_test_videos.txt")
    args = ap.parse_args()

    with open(ROOT / "yawdd_sharing_permission.csv", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)
                if r["camera"] == "Mirror" and r["action"].lower() == "yawning"
                and r["image_sharing_permission"] == "yes" and r["glasses"] in WANTED]
    random.Random(args.seed).shuffle(rows)

    chosen, counts = [], {k: 0 for k in WANTED}
    for r in rows:
        if counts[r["glasses"]] >= WANTED[r["glasses"]]:
            continue
        frames, found, _ = measure_video(YAWDD_DIR / r["video"], CHECK_FRAMES)
        rate = 100.0 * found / frames if frames else 0.0
        accepted = rate >= MIN_FACE_RATE and frames >= CHECK_FRAMES
        print(f"{r['video']}: face in {rate:.1f}% of {frames} frames -> {'accepted' if accepted else 'rejected'}")
        if accepted:
            chosen.append(Path(r["video"]).as_posix())
            counts[r["glasses"]] += 1
        if all(counts[k] >= WANTED[k] for k in WANTED):
            break
    args.output.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    print(f"\n{len(chosen)} videos written to {args.output}")


if __name__ == "__main__":
    main()
