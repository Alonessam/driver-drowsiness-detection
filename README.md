# Driver Drowsiness Detection

A driver drowsiness detection system built with Python, OpenCV and the MediaPipe Face Landmarker.
It is a single-person project, built in work packages (WP). **Work in progress:** WP1 (face landmarks and privacy mode) and
WP2 (eye blinks and long eye closures) are implemented; yawning, head pose, PERCLOS, the alarm
decision logic and the user interface are planned.

## Features

- 478-point face landmarks from a camera or a video file (MediaPipe Face Landmarker, Tasks API).
- **Privacy mode:** the camera image is discarded and only the face mesh is drawn on a black canvas.
  The application never writes any frame to disk.
- **Eye tracking (EAR):** 3-second calibration, blink counting, slow-blink counting and a warning for
  eye closures longer than 1.5 s. EAR value, threshold and a 10-second EAR graph are shown live.
- Tools to measure the face detection rate, label blinks by hand and evaluate blink detection.

## Setup (Python 3.12 is required; MediaPipe does not support 3.13)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Download the model (about 3.7 MB, the official Google MediaPipe model) to `models\face_landmarker.task`:

```powershell
curl -L -o models\face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

Install `opencv-contrib-python` only (do not also install `opencv-python`; the two conflict).

## Usage

```powershell
.\.venv\Scripts\python.exe app.py                                   # camera
.\.venv\Scripts\python.exe app.py --source data\YawDD\video.avi     # video file
.\.venv\Scripts\python.exe app.py --pick                            # choose a video in a file dialog
.\.venv\Scripts\python.exe app.py --privacy                         # start in privacy mode
```

Keys: `g` toggle privacy mode, `r` recalibrate, `q` / `ESC` / window close button quit.

During calibration (first 3 s) look at the camera with open eyes. The EAR threshold is the median EAR
multiplied by 0.72 (limited to 0.10-0.28). A closure of 0.10-0.40 s is a **blink**, 0.40-1.5 s a
**slow blink**, and an eye closure that reaches **1.5 s** raises a **long eye closure** warning while
the eyes are still closed. Dips shorter than 0.10 s are treated as noise. If the face is lost, a
half-finished closure is discarded.

Sunglasses hide the eyes, so eye-based measurements are not reliable with them.

`demo.bat` is a small demo menu for Windows (camera, sample videos, results page, file dialog).

## Measurements

Face detection rate and speed on a folder of videos (WP1 targets: >= 90 % and >= 15 fps):

```powershell
.\.venv\Scripts\python.exe measure_detection.py data\YawDD --output yawdd_detection_rate.csv
.\.venv\Scripts\python.exe tools\results_page.py        # HTML summary of the CSV
```

Blink detection (WP2 target: >= 85 % of manually counted blinks), using `eye_tests.bat` or directly:

```powershell
.\.venv\Scripts\python.exe tools\test_videos.py label    # label the videos listed in labels\test_videos.txt
.\.venv\Scripts\python.exe tools\evaluate_blinks.py      # compare detection with the labels (tolerance 0.25 s)
.\.venv\Scripts\python.exe tools\controlled_test.py      # live test: planned eye closures > 1.5 s (target >= 90 %)
```

Label files in `labels/` store video paths relative to the YawDD folder (`data\YawDD` by default, or the
folder in the `YAWDD_DIR` environment variable).

### Results so far

| Measurement | Result | Notes |
|---|---|---|
| Face found in frame (YawDD, 349 videos) | 99.4 % | share of frames with a face, **not** landmark accuracy |
| Processing speed | about 84 fps | video reading + detection on CPU, drawing excluded |
| Blink detection (5 videos, 34 labeled blinks) | 91.2 % recall, 93.9 % precision | 3 missed, 2 false alarms |
| Controlled long-closure test | not completed yet | |

The 5 test videos were chosen by a fixed random rule among normal-driving videos with permission to
share images and without sunglasses; they are small, so these numbers are indicative only.

Run the unit tests with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests
```

## Project structure

- `drowsiness/landmarks.py`: Face Landmarker wrapper (478 points), eye and mouth point indices
- `drowsiness/source.py`: frame reading from a camera or a video file
- `drowsiness/drawing.py`: normal and privacy-mode drawing, EAR graph, warning banner
- `drowsiness/eye.py`: EAR computation, calibration, blink and long-closure tracker
- `drowsiness/eye_evaluation.py`: matching detections with manual labels
- `drowsiness/consent.py`: per-video image sharing permission (see below)
- `app.py`: live window, `measure_detection.py`: batch measurement
- `tools/`: labeling, evaluation, controlled test, results page, permission list builder
- `tests/`: unit tests (synthetic EAR sequences)

## Data and privacy

The datasets are **not included** in this repository and must be obtained from their owners:

- **YawDD** (Yawning Detection Dataset), Abtahi et al., 2014, IEEE DataPort,
  [doi:10.21227/e1qm-hb90](https://doi.org/10.21227/e1qm-hb90). Free for non-commercial / academic use
  with attribution. Participants gave different permissions for sharing their images;
  `tools/yawdd_permission_list.py` extracts them from the dataset's `Table1.pdf` / `Table2.pdf` into
  `yawdd_sharing_permission.csv`. Videos whose permission is not "yes" automatically open in privacy mode
  and no screenshot of them should be shared.
- **UTA-RLDD** (Real-Life Drowsiness Dataset), Ghoddoosian et al., CVPR Workshops 2019. Its sharing
  permissions are unknown here, so its videos are always shown in privacy mode.

The application does not save camera frames. Note that MediaPipe's native library contains an embedded
usage-logging request to `play.googleapis.com/log` (observed to fail with HTTP 500 here); its content was
not inspected.

## Roadmap

WP3 yawning (mouth aspect ratio), WP4 head pose + PERCLOS + decision logic + audible alarm,
WP5 performance evaluation, WP6 user interface, WP7 software testing, WP8 documentation.
