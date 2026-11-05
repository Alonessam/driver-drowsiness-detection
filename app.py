"""Live demo: shows face landmarks from a camera or a video file.

Usage:
    python app.py                           # default camera
    python app.py --pick                    # choose a video with a file dialog
    python app.py --source video.avi        # video file
    python app.py --source video.avi --privacy

Videos whose image sharing permission is not "yes" (permission "no", or unknown such as UTA-RLDD)
automatically start in privacy mode.

Eye tracking: the first 3 seconds are calibration (look at the camera, eyes open); after that blinks and
long eye closures are counted, and the EAR and a graph of the last 10 seconds are shown on screen.

Keys: g = toggle privacy mode, r = recalibrate, q or ESC = quit
"""
import argparse
import time
from collections import deque
from pathlib import Path

import cv2

from drowsiness.consent import image_sharing_permission
from drowsiness.drawing import draw, draw_ear_graph, fit_to_screen, put_info, put_warning
from drowsiness.eye import EyeTracker, mean_ear
from drowsiness.landmarks import FaceLandmarkDetector, to_pixels
from drowsiness.paths import YAWDD_DIR
from drowsiness.source import VideoSource

WINDOW = "Driver Drowsiness Detection"


def parse_source(value):
    return int(value) if value.isdigit() else value


def pick_video():
    """Opens a file dialog; returns the chosen path (None if cancelled)."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # keep the dialog from hiding behind other windows
    root.update()
    print("Opening file dialog... If you cannot see it, check the taskbar.", flush=True)
    path = filedialog.askopenfilename(
        parent=root,
        title="Select video",
        initialdir=str(YAWDD_DIR if YAWDD_DIR.exists() else Path.home()),
        filetypes=[("Video files", "*.avi *.mp4 *.mov *.mkv"), ("All files", "*.*")],
    )
    root.destroy()
    return path or None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--source", default="0", help="camera index or video path (default: 0)")
    ap.add_argument("--pick", action="store_true", help="choose a video with a file dialog")
    ap.add_argument("--privacy", action="store_true", help="start with privacy mode on")
    args = ap.parse_args()

    if args.pick:
        source_path = pick_video()
        if not source_path:
            return
    else:
        source_path = parse_source(args.source)

    # For videos, privacy mode starts on unless the image sharing permission is "yes"
    permission = image_sharing_permission(source_path) if isinstance(source_path, str) else None
    privacy = args.privacy or (permission is not None and permission != "yes")
    fps = 0.0
    first_frame = True
    eyes = EyeTracker()
    history = deque(maxlen=3000)  # (time_s, ear) pairs for the graph
    with VideoSource(source_path) as source, FaceLandmarkDetector() as detector:
        for _, timestamp_ms, frame in source.frames():
            t0 = time.perf_counter()
            landmarks = detector.detect(frame, timestamp_ms)
            ear = None
            if landmarks is not None:
                height, width = frame.shape[:2]
                ear = mean_ear(to_pixels(landmarks, width, height))
            eyes.update(timestamp_ms, ear)
            history.append((timestamp_ms / 1000.0, ear))
            output = fit_to_screen(draw(frame, landmarks, privacy))
            elapsed = time.perf_counter() - t0
            fps = 0.9 * fps + 0.1 / elapsed if fps else 1.0 / elapsed
            lines = [
                f"Face: {'found' if landmarks is not None else 'NONE'}",
                f"Privacy mode: {'ON' if privacy else 'off'} (g)",
                f"Processing speed: {fps:.0f} fps",
            ]
            if not eyes.is_calibrated:
                lines.append(f"CALIBRATION: look at the camera, eyes open ({eyes.remaining_s:.0f} s)")
            else:
                lines.append(f"EAR: {'-' if ear is None else f'{ear:.2f}'}  (threshold {eyes.threshold:.2f})")
                lines.append(f"Eyes: {'CLOSED' if eyes.is_closed else 'open'}"
                             f"{f'  ({eyes.closed_duration_s(timestamp_ms):.1f} s)' if eyes.is_closed else ''}")
                lines.append(f"Blinks: {eyes.blink_count}   Slow blinks: {eyes.long_blink_count}"
                             f"   Long closures: {eyes.long_closure_count}")
            if permission is not None:
                lines.append(f"Image sharing permission: {permission}")
            lines.append("g: privacy | r: recalibrate | q/ESC/X: quit")
            put_info(output, lines)
            draw_ear_graph(output, history, eyes.threshold)
            if eyes.closed_duration_s(timestamp_ms) >= eyes.long_closure_s:
                put_warning(output, "LONG EYE CLOSURE!")
            cv2.imshow(WINDOW, output)
            if first_frame:  # bring the window to the front (the q key goes to the focused window)
                cv2.setWindowProperty(WINDOW, cv2.WND_PROP_TOPMOST, 1)
                first_frame = False
            # Play video files at real speed
            wait = 1 if source.is_camera else max(1, int(1000 / source.fps - elapsed * 1000))
            key = cv2.waitKey(wait) & 0xFF
            if key in (ord("q"), 27):
                break
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:  # closed with the X button
                break
            if key == ord("g"):
                privacy = not privacy
            if key == ord("r"):
                eyes.reset_calibration()
                history.clear()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
