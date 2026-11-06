"""Compares two labeling rounds of the same videos (current labels versus the oldest archived ones).

It shows how consistent the manual labels are. Two rounds by the same person that disagree a lot mean that the
"ground truth" itself is uncertain, which limits what any detector can score.

Usage:
    python tools/compare_labels.py                 # blink labels
    python tools/compare_labels.py --kind yawn     # yawn labels
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import read_labels  # noqa: E402
from drowsiness.paths import ROOT  # noqa: E402

KINDS = {
    "blink": {"folder": ROOT / "labels", "key": "blink_times_s", "tolerance": 0.25},
    "yawn": {"folder": ROOT / "labels" / "yawn", "key": "yawn_times_s", "tolerance": 1.0},
}


def match_times(first, second, tolerance):
    """One-to-one matching of two lists of times; returns the number of matched pairs."""
    used, matched = set(), 0
    for t in sorted(first):
        for i, u in enumerate(sorted(second)):
            if i not in used and abs(t - u) <= tolerance:
                used.add(i)
                matched += 1
                break
    return matched


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--kind", choices=KINDS, default="blink")
    ap.add_argument("--tolerance", type=float, default=None, help="matching tolerance in s")
    args = ap.parse_args()
    kind = KINDS[args.kind]
    tolerance = args.tolerance if args.tolerance is not None else kind["tolerance"]

    print(f"{'video':<34}{'round 1':>8}{'round 2':>8}{'both':>6}{'only 1':>7}{'only 2':>7}")
    total = [0, 0, 0]
    for current in sorted(kind["folder"].glob("*.json")):
        archived = sorted((kind["folder"] / "previous").glob(f"{current.stem}-*.json"))
        if not archived:
            continue
        video, new = read_labels(current, kind["key"])
        _, old = read_labels(archived[0], kind["key"])      # the oldest archive = the first round
        both = match_times(old, new, tolerance)
        print(f"{Path(video).name[:33]:<34}{len(old):>8}{len(new):>8}{both:>6}{len(old) - both:>7}{len(new) - both:>7}")
        total[0] += both; total[1] += len(old) - both; total[2] += len(new) - both
    both, only1, only2 = total
    if both + only1 + only2 == 0:
        print("\nNo videos with two labeling rounds yet (label again with --fresh first).")
        return
    agreement = 100.0 * both / (both + only1 + only2)
    print(f"\nAgreement between the two rounds: {agreement:.1f}% "
          f"({both} matched, {only1} only in round 1, {only2} only in round 2; tolerance {tolerance:g} s)")


if __name__ == "__main__":
    main()
