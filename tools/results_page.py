"""Builds a results page (HTML) from yawdd_detection_rate.csv to open in a browser during a demo.

Usage: python tools/results_page.py [csv_path] [html_path]
Default: yawdd_detection_rate.csv -> results.html (in the project folder)
"""
import csv
import html
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "yawdd_detection_rate.csv"
html_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "results.html"

TARGET_RATE, TARGET_FPS = 90.0, 15.0
GROUP_NAMES = {"no_glasses": "No glasses", "glasses": "Glasses", "sunglasses": "Sunglasses", "unknown": "Unknown"}

with open(csv_path, encoding="utf-8-sig") as f:
    rows = [
        {
            "video": r["video"],
            "frames": int(r["frames"]),
            "found": int(r["face_frames"]),
            "rate": float(r["face_rate_percent"]),
            "fps": float(r["fps"]),
            "glasses": r["glasses"],
        }
        for r in csv.DictReader(f)
    ]
if not rows:
    raise SystemExit(f"CSV is empty: {csv_path}")


def summarize(group):
    frames = sum(r["frames"] for r in group)
    found = sum(r["found"] for r in group)
    seconds = sum(r["frames"] / r["fps"] for r in group if r["fps"])
    return {
        "videos": len(group),
        "rate": 100.0 * found / frames,
        "above": sum(1 for r in group if r["rate"] >= TARGET_RATE),
        "fps": frames / seconds if seconds else 0.0,
    }


def num(x, digits=1):
    return f"{x:.{digits}f}"


overall = summarize(rows)
groups = defaultdict(list)
for r in rows:
    groups[r["glasses"]].append(r)

cameras = defaultdict(list)
for r in rows:
    cameras["Dash (dashboard)" if r["video"].lower().startswith("dash") else "Mirror (under mirror)"].append(r)

lowest = sorted(rows, key=lambda r: r["rate"])[:10]
rate_class = "ok" if overall["rate"] >= TARGET_RATE else "bad"
fps_class = "ok" if overall["fps"] >= TARGET_FPS else "bad"


def table_row(name, s):
    return (f"<tr><td>{html.escape(name)}</td><td class='n'>{s['videos']}</td><td class='n'>{num(s['rate'])}%</td>"
            f"<td class='n'>{s['above']}/{s['videos']}</td><td class='n'>{num(s['fps'])}</td></tr>")


group_rows = "".join(table_row(GROUP_NAMES.get(k, k), summarize(groups[k])) for k in GROUP_NAMES if k in groups)
camera_rows = "".join(table_row(k, summarize(v)) for k, v in cameras.items())
lowest_rows = "".join(
    f"<tr><td>{html.escape(r['video'])}</td><td>{GROUP_NAMES.get(r['glasses'], r['glasses'])}</td>"
    f"<td class='n {'bad' if r['rate'] < TARGET_RATE else ''}'>{num(r['rate'])}%</td></tr>"
    for r in lowest
)
all_rows = "".join(
    f"<tr><td>{html.escape(r['video'])}</td><td>{GROUP_NAMES.get(r['glasses'], r['glasses'])}</td>"
    f"<td class='n'>{r['frames']}</td><td class='n {'bad' if r['rate'] < TARGET_RATE else ''}'>{num(r['rate'])}%</td>"
    f"<td class='n'>{num(r['fps'])}</td></tr>"
    for r in sorted(rows, key=lambda r: r["video"])
)

page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Measurement Results - YawDD</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; background: #f4f6f9; color: #1a1d21; }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 24px 20px 60px; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; }}
  h2 {{ font-size: 19px; margin: 30px 0 10px; color: #1f4f8a; }}
  .sub {{ color: #5b6573; margin: 0 0 18px; }}
  .cards {{ display: flex; gap: 14px; flex-wrap: wrap; }}
  .card {{ flex: 1 1 200px; background: #fff; border: 1px solid #d5dbe2; border-radius: 10px; padding: 14px 16px; }}
  .card .l {{ font-size: 13px; color: #5b6573; }}
  .card .v {{ font-size: 34px; font-weight: 700; margin: 2px 0; }}
  .card .t {{ font-size: 13px; }}
  .ok {{ color: #1c7c3a; }} .bad {{ color: #b3261e; font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; border: 1px solid #d5dbe2; font-size: 14px; }}
  th, td {{ padding: 6px 10px; border-bottom: 1px solid #e6eaef; text-align: left; }}
  th {{ background: #e8eef6; }}
  td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
  details {{ margin-top: 26px; }} summary {{ cursor: pointer; font-size: 17px; color: #1f4f8a; font-weight: 600; }}
  .note {{ background: #fff8e1; border: 1px solid #f0d98a; border-radius: 8px; padding: 10px 14px; margin-top: 22px; font-size: 14px; }}
</style></head><body><main>
<h1>Face Detection Measurement Results</h1>
<p class="sub">YawDD dataset · {overall['videos']} videos · MediaPipe Face Landmarker (478 landmarks) on every frame</p>

<div class="cards">
  <div class="card"><div class="l">Face detection rate</div><div class="v {rate_class}">{num(overall['rate'])}%</div>
    <div class="t">Target: at least {num(TARGET_RATE, 0)}% {'&#10004;' if rate_class == 'ok' else '&#10008;'}</div></div>
  <div class="card"><div class="l">Processing speed</div><div class="v {fps_class}">{num(overall['fps'], 0)} fps</div>
    <div class="t">Target: at least {num(TARGET_FPS, 0)} fps {'&#10004;' if fps_class == 'ok' else '&#10008;'}</div></div>
  <div class="card"><div class="l">Videos at {num(TARGET_RATE, 0)}% or above</div><div class="v">{overall['above']}/{overall['videos']}</div>
    <div class="t">{overall['videos'] - overall['above']} videos below the target</div></div>
</div>

<h2>By glasses type</h2>
<table><tr><th>Group</th><th class="n">Videos</th><th class="n">Face detection rate</th><th class="n">{num(TARGET_RATE, 0)}%+ videos</th><th class="n">fps</th></tr>{group_rows}</table>

<h2>By camera position</h2>
<table><tr><th>Camera</th><th class="n">Videos</th><th class="n">Face detection rate</th><th class="n">{num(TARGET_RATE, 0)}%+ videos</th><th class="n">fps</th></tr>{camera_rows}</table>

<h2>10 videos with the lowest rate</h2>
<table><tr><th>Video</th><th>Glasses</th><th class="n">Face detection rate</th></tr>{lowest_rows}</table>

<div class="note"><b>Note:</b> The face detection rate is the percentage of frames in which a face was <i>found</i>.
It is not the positional accuracy of the landmarks; that is measured in the later work packages (blinks, yawns).</div>

<details><summary>All videos ({overall['videos']})</summary>
<table><tr><th>Video</th><th>Glasses</th><th class="n">Frames</th><th class="n">Face rate</th><th class="n">fps</th></tr>{all_rows}</table></details>
</main></body></html>"""

html_path.write_text(page, encoding="utf-8")
print(f"Written: {html_path} | {overall['videos']} videos | overall rate {num(overall['rate'])}% | {num(overall['fps'], 0)} fps")
