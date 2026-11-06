"""Manual event labeling tool: blinks (work package 2) or yawns (work package 3).

Usage:
    python tools/label_events.py <video> [--kind blink|yawn] [--speed 0.25] [--output labels/name.json] [--fresh]

Blinks: the video plays in slow motion (0.25x); press B at every blink.
Yawns : the video plays at real speed; press B once while the mouth is wide open in every yawn
        (at the middle of the yawn).
If you miss one, pause with the space bar and step frame by frame with A / D.

Keys:
    space = pause / play      b = mark event          u = undo last mark
    a / d = (while paused) 1 frame back / forward     + / - = playback speed
    s     = save              q or ESC = save and quit
"""
import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drowsiness.eye_evaluation import archive_labels, read_labels, write_labels  # noqa: E402
from drowsiness.paths import ROOT, storable_video  # noqa: E402

KINDS = {
    "blink": {"key": "blink_times_s", "folder": "labels", "speed": 0.25, "min_gap": 0.3, "noun": "blink"},
    "yawn": {"key": "yawn_times_s", "folder": "labels/yawn", "speed": 1.0, "min_gap": 2.0, "noun": "yawn"},
}


def put_text(frame, text, y, color=(255, 255, 255)):
    cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--kind", choices=KINDS, default="blink")
    ap.add_argument("--speed", type=float, default=None,
                    help="playback speed (1 = real time; default 0.25 for blinks, 1 for yawns)")
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--fresh", action="store_true",
                    help="start again from scratch; the old label file is kept in a 'previous' folder")
    ap.add_argument("--zoom", type=float, default=1.5, help="enlarge small videos by this factor (default 1.5)")
    args = ap.parse_args()

    kind = KINDS[args.kind]
    window = f"{kind['noun'].capitalize()} labeling"
    output = args.output or ROOT / kind["folder"] / f"{args.video.stem}.json"
    marks = []
    if args.fresh and output.exists():
        print(f"Old labels kept in: {archive_labels(output)}")
    if output.exists():  # continue a previous session
        _, marks = read_labels(output, kind["key"])
        print(f"Previous labels loaded: {len(marks)} {kind['noun']}s ({output.name})")

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    speed = args.speed if args.speed is not None else kind["speed"]
    paused = False
    frame_no, frame = 0, None
    message, message_left = "", 0

    def save():
        write_labels(output, storable_video(args.video), marks, kind["key"])

    def read_frame(no):
        cap.set(cv2.CAP_PROP_POS_FRAMES, no)
        ok, f = cap.read()
        return f if ok else None

    ok, frame = cap.read()
    if not ok:
        raise SystemExit("Could not read the video.")
    while True:
        t = frame_no / fps
        view = frame.copy()
        if args.zoom != 1.0 and view.shape[1] < 900:
            view = cv2.resize(view, None, fx=args.zoom, fy=args.zoom, interpolation=cv2.INTER_LINEAR)
        put_text(view, f"Time: {t:5.2f} / {total / fps:5.2f} s   Speed: {speed:.2f}x   {'PAUSED' if paused else 'playing'}", 22)
        put_text(view, f"Marked {kind['noun']}s: {len(marks)}", 46, (80, 220, 80))
        put_text(view, f"b: {kind['noun']} | u: undo | space: pause | a/d: frame | +/-: speed | q: save+quit", view.shape[0] - 12)
        if message_left > 0:
            put_text(view, message, 72, (60, 60, 240))
            message_left -= 1
        # timeline at the bottom: marks
        width = view.shape[1]
        cv2.line(view, (0, view.shape[0] - 34), (width, view.shape[0] - 34), (90, 90, 90), 2)
        for mark in marks:
            x = int(mark * fps / max(total, 1) * width)
            cv2.line(view, (x, view.shape[0] - 42), (x, view.shape[0] - 26), (80, 220, 80), 2)
        x = int(frame_no / max(total, 1) * width)
        cv2.line(view, (x, view.shape[0] - 46), (x, view.shape[0] - 22), (255, 255, 255), 2)
        cv2.imshow(window, view)

        wait = 30 if paused else max(1, int(1000 / (fps * speed)))
        key = cv2.waitKey(wait) & 0xFF
        if key in (ord("q"), 27) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            break
        if key == ord(" "):
            paused = not paused
        elif key == ord("b"):
            if marks and abs(t - marks[-1]) < kind["min_gap"]:
                message, message_left = f"Too close: this {kind['noun']} is already marked", 15
            else:
                marks.append(t)
                message, message_left = f"Marked: {t:.2f} s", 10
        elif key == ord("u") and marks:
            message, message_left = f"Undone: {marks.pop():.2f} s", 15
        elif key in (ord("+"), ord("=")):
            speed = min(2.0, speed * 1.5)
        elif key in (ord("-"), ord("_")):
            speed = max(0.05, speed / 1.5)
        elif key == ord("s"):
            save()
            message, message_left = "Saved", 15
        elif key == ord("a") and paused:
            frame_no = max(0, frame_no - 1)
            frame = read_frame(frame_no) if frame_no >= 0 else frame
        elif key == ord("d") and paused:
            new = read_frame(frame_no + 1)
            if new is not None:
                frame, frame_no = new, frame_no + 1
        if not paused:
            ok, new = cap.read()
            if ok:
                frame, frame_no = new, frame_no + 1
            else:
                paused = True  # video ended: review and quit with q
                message, message_left = "Video ended. Press q to save and quit", 200
    cap.release()
    cv2.destroyAllWindows()
    save()
    print(f"Saved: {output} ({len(marks)} {kind['noun']}s)")


if __name__ == "__main__":
    main()
