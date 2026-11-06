# Driver Drowsiness Detection

A driver drowsiness detection system built with Python, OpenCV and the MediaPipe Face Landmarker.
It is a single-person project, built in work packages (WP). **Work in progress:** WP1 (face landmarks and
privacy mode), WP2 (eye blinks and long eye closures) and WP3 (yawning) are implemented; head pose, PERCLOS,
the alarm decision logic and the user interface are planned.

## Features

- 478-point face landmarks from a camera or a video file (MediaPipe Face Landmarker, Tasks API).
- **Privacy mode:** the camera image is discarded and only the face mesh is drawn on a black canvas.
  The application never writes any frame to disk.
- **Eye tracking (EAR):** 3-second calibration, blink counting, slow-blink counting and a warning for
  eye closures longer than 1.5 s. EAR value, threshold and a 10-second EAR graph are shown live.
- **Yawn tracking (MAR):** mouth aspect ratio, a yawn counter, the number of yawns in the last 5 minutes and a
  10-second MAR graph.
- **Sunglasses mode:** eye tracking is switched off (the eyes are hidden), yawn tracking keeps working.
- Tools to measure the face detection rate, label blinks and yawns by hand and evaluate both detectors.

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
.\.venv\Scripts\python.exe app.py --sunglasses                      # start with eye tracking off
```

Keys: `g` toggle privacy mode, `r` recalibrate and reset counters, `s` toggle sunglasses mode,
`q` / `ESC` / window close button quit.

**Eyes.** During calibration (first 3 s) look at the camera with open eyes. The EAR threshold is the median
EAR multiplied by 0.72 (limited to 0.10-0.28). A closure of 0.10-0.40 s is a **blink**, 0.40-1.5 s a
**slow blink**, and an eye closure that reaches **1.5 s** raises a **long eye closure** warning while the eyes
are still closed. Dips shorter than 0.10 s are treated as noise. A face lost for less than 0.3 s during a
closure does not end it; a longer loss discards it.

**Mouth.** MAR = ||p13 - p14|| / ||p78 - p308|| (inner lips over inner mouth corners). The mouth counts as open
above MAR 0.4; an opening is a **yawn** if it stays open for at least **1 s** and reaches MAR 0.5 at least once.
Dips shorter than 0.2 s do not end an opening, a face lost for less than 0.5 s neither. The yawn warning appears
while the mouth is still open.

Sunglasses hide the eyes, so eye-based measurements are not reliable with them. For YawDD files whose name
contains "SunGlasses" the app switches to sunglasses mode by itself.

`demo.bat` is a small demo menu for Windows (camera, sample videos, results page, file dialog).

## Measurements

Face detection rate and speed on a folder of videos (WP1 targets: >= 90 % and >= 15 fps):

```powershell
.\.venv\Scripts\python.exe measure_detection.py data\YawDD --output yawdd_detection_rate.csv
.\.venv\Scripts\python.exe tools\results_page.py        # HTML summary of the CSV
```

Blink detection (WP2 targets: >= 85 % of manually counted blinks, >= 90 % of planned closures longer than
1.5 s), using `eye_tests.bat` or directly:

```powershell
.\.venv\Scripts\python.exe tools\test_videos.py label    # label the videos listed in labels\test_videos.txt
.\.venv\Scripts\python.exe tools\evaluate_blinks.py      # compare detection with the labels (tolerance 0.25 s)
.\.venv\Scripts\python.exe tools\controlled_test.py      # live test: close eyes at the high beep, keep them closed until the low beep (3.5 s)
```

To label a video set again from scratch (the first labels are kept in a `previous` folder) use
`tools\test_videos.py label --fresh` (add `--kind yawn` for yawns); `tools\compare_labels.py` then shows how well
the two labeling rounds agree. `tools\test_videos.py one` (add `--kind yawn`) lets you pick a single video from the
list and either continue or redo its labels.

Yawn detection (WP3 targets: >= 85 % of manually counted yawns in 5 test videos, at most 1 false yawn per talking
video), using `yawn_tests.bat` or directly:

```powershell
.\.venv\Scripts\python.exe tools\pick_test_videos.py                       # picks the 5 test videos (fixed rule and seed)
.\.venv\Scripts\python.exe tools\test_videos.py label --kind yawn          # label them: B in the middle of each yawn
.\.venv\Scripts\python.exe tools\evaluate_yawns.py                         # recall on labels + false yawns in talking videos
```

Label files in `labels/` store video paths relative to the YawDD folder. The folder is found through the
`YAWDD_DIR` environment variable, `data\YawDD`, or a sibling folder named `YawDD dataset`.

### Results so far

| Measurement | Result | Notes |
|---|---|---|
| Face found in frame (YawDD, 349 videos) | 99.4 % | share of frames with a face, **not** landmark accuracy |
| Processing speed | about 84 fps | video reading + detection on CPU, drawing excluded |
| Blink detection (5 videos, 34 labeled blinks) | 91.2 % recall, 93.9 % precision | 3 missed, 2 false alarms |
| Controlled long-closure test | not completed yet | |
| Yawn detection, labeled recall (5 videos) | not measured yet | labeling pending |
| False yawns, 100 YawDD talking videos | mean 0.06 per video; 99 videos with at most 1, one with 3 | see below |
| False yawns, 105 YawDD normal videos | 0 | |

### How the yawn thresholds were chosen

MAR series were extracted from all 307 YawDD mirror-camera videos of the classes Yawning (102), Talking (100)
and Normal (105) and the tracker was run on them with a grid of settings. The form's starting values
(open above MAR 0.6 for 1 s) gave almost no false yawns but detected an event in only 78 % of the yawning videos;
using an open threshold of 0.4 together with a peak of 0.5 raised this to 92 % (94 of 102 videos, counted as videos with
at least one detected yawn, which is an upper bound for recall because not every yawning video is guaranteed to
contain a clear yawn) while keeping false yawns low. The one talking video with more than one false yawn
(`17-FemaleSunGlasses-Talking`, 3 detections of 1.0-1.2 s) is a sunglasses video. **Limitation:** the settings
were tuned on the same videos they are evaluated on (there is no separate hold-out set), so the false-yawn numbers
are optimistic.

Run the unit tests with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests
```

## Project structure

- `drowsiness/landmarks.py`: Face Landmarker wrapper (478 points), eye and mouth point indices
- `drowsiness/source.py`: frame reading from a camera or a video file
- `drowsiness/drawing.py`: normal and privacy-mode drawing, EAR/MAR graphs, warning banners
- `drowsiness/eye.py`: EAR computation, calibration, blink and long-closure tracker
- `drowsiness/mouth.py`: MAR computation and yawn tracker
- `drowsiness/eye_evaluation.py`, `drowsiness/mouth_evaluation.py`: matching detections with manual labels
- `drowsiness/controlled.py`: flow of the controlled long-closure test (commands, trials, diagnostics)
- `drowsiness/consent.py`: per-video image sharing permission (see below)
- `app.py`: live window, `measure_detection.py`: batch measurement
- `tools/`: labeling, label comparison, evaluation, controlled test, test video picker, results page, permission list builder
- `tests/`: unit tests (synthetic EAR and MAR sequences)

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

WP4 head pose + PERCLOS + decision logic + audible alarm, WP5 performance evaluation, WP6 user interface,
WP7 software testing, WP8 documentation.
