"""Drawing face landmarks on screen in normal and privacy mode."""
import cv2
import mediapipe as mp
import numpy as np

from .landmarks import LEFT_EYE, MOUTH, RIGHT_EYE, to_pixels

_CONNECTIONS = mp.tasks.vision.FaceLandmarksConnections


def _lines(connections):
    return np.array([(c.start, c.end) for c in connections], dtype=np.int32)


_MESH = _lines(_CONNECTIONS.FACE_LANDMARKS_TESSELATION)
_CONTOUR = _lines(_CONNECTIONS.FACE_LANDMARKS_CONTOURS)

# BGR colors
GRAY = (90, 80, 70)
WHITE = (235, 235, 235)
GREEN = (80, 220, 80)
RED = (60, 60, 240)


def _draw_lines(canvas, points_px, lines, color, thickness=1):
    segments = points_px[lines].astype(np.int32)  # (N, 2, 2)
    cv2.polylines(canvas, segments, False, color, thickness, cv2.LINE_AA)


def _mark_eyes_and_mouth(canvas, points_px):
    for idx in RIGHT_EYE + LEFT_EYE:
        cv2.circle(canvas, tuple(points_px[idx].astype(int)), 2, GREEN, -1, cv2.LINE_AA)
    for idx in MOUTH:
        cv2.circle(canvas, tuple(points_px[idx].astype(int)), 2, RED, -1, cv2.LINE_AA)


def draw(frame, landmarks, privacy=False):
    """Returns a new frame with the drawing.

    privacy=False: face contour and eye/mouth points are drawn over the real image.
    privacy=True : the image is discarded; only the face mesh and points are drawn on a black canvas.
    """
    height, width = frame.shape[:2]
    canvas = np.zeros_like(frame) if privacy else frame.copy()
    if landmarks is None:
        return canvas
    px = to_pixels(landmarks, width, height)
    if privacy:
        _draw_lines(canvas, px, _MESH, GRAY)
    _draw_lines(canvas, px, _CONTOUR, WHITE)
    _mark_eyes_and_mouth(canvas, px)
    return canvas


def fit_to_screen(frame, max_width=1280, max_height=720):
    """Shrinks large (e.g. portrait phone) videos to fit the window, keeping the aspect ratio."""
    height, width = frame.shape[:2]
    scale = min(max_width / width, max_height / height, 1.0)
    if scale == 1.0:
        return frame
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def put_info(canvas, lines):
    """Writes info lines in the top-left corner (OpenCV fonts do not support non-ASCII characters)."""
    for i, line in enumerate(lines):
        y = 24 + 24 * i
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)


def draw_ear_graph(canvas, history, threshold, window_s=10.0, width=260, height=90, ear_max=0.45):
    """Draws the EAR graph of the last `window_s` seconds in the bottom-left corner (red dashed line: threshold).

    history: (time_s, ear) pairs; ear is None for frames without a face (the line is broken there).
    """
    draw_graph(canvas, history, threshold, "EAR (last 10 s)", ear_max, 10, window_s, width, height)


def draw_mar_graph(canvas, history, threshold, window_s=10.0, width=260, height=90, mar_max=1.2):
    """Draws the MAR graph of the last `window_s` seconds next to the EAR graph (red dashed line: threshold)."""
    draw_graph(canvas, history, threshold, "MAR (last 10 s)", mar_max, 10 + width + 10, window_s, width, height)


def draw_graph(canvas, history, threshold, title, value_max, x0, window_s=10.0, width=260, height=90):
    """Draws a (time_s, value) graph in the bottom-left area, starting at horizontal position x0."""
    canvas_height = canvas.shape[0]
    y0 = canvas_height - height - 10
    cv2.rectangle(canvas, (x0, y0), (x0 + width, y0 + height), (30, 30, 30), -1)
    cv2.rectangle(canvas, (x0, y0), (x0 + width, y0 + height), (120, 120, 120), 1)
    cv2.putText(canvas, title, (x0 + 5, y0 + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    if not history:
        return
    t_last = history[-1][0]
    t_first = t_last - window_s

    def point(t, e):
        x = x0 + int((t - t_first) / window_s * width)
        y = y0 + height - int(min(max(e, 0.0), value_max) / value_max * height)
        return x, y

    if threshold is not None:
        y_threshold = point(t_first, threshold)[1]
        for x in range(x0, x0 + width, 8):  # dashed line
            cv2.line(canvas, (x, y_threshold), (min(x + 4, x0 + width), y_threshold), RED, 1)
    segment = []
    for t, e in history:
        if t < t_first:
            continue
        if e is None:
            if len(segment) > 1:
                cv2.polylines(canvas, [np.array(segment, np.int32)], False, GREEN, 1, cv2.LINE_AA)
            segment = []
        else:
            segment.append(point(t, e))
    if len(segment) > 1:
        cv2.polylines(canvas, [np.array(segment, np.int32)], False, GREEN, 1, cv2.LINE_AA)


def put_warning(canvas, text, row=0):
    """Draws a red warning banner at the top center of the image (row 1 is drawn below row 0)."""
    height, width = canvas.shape[:2]
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    top = 8 + row * (h + 28)
    x0 = max(0, (width - w) // 2 - 12)
    cv2.rectangle(canvas, (x0, top), (min(width, x0 + w + 24), top + h + 20), (30, 30, 200), -1)
    cv2.putText(canvas, text, (x0 + 12, top + h + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
