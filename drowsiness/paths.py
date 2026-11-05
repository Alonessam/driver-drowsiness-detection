"""Project paths.

The YawDD dataset is looked up in this order: the YAWDD_DIR environment variable, `data/YawDD` inside the
project, a sibling folder named `YawDD dataset` next to the project folder.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "face_landmarker.task"


def _find_yawdd():
    if os.environ.get("YAWDD_DIR"):
        return Path(os.environ["YAWDD_DIR"])
    for candidate in (ROOT / "data" / "YawDD", ROOT.parent / "YawDD dataset"):
        if candidate.exists():
            return candidate
    return ROOT / "data" / "YawDD"


YAWDD_DIR = _find_yawdd()


def resolve_video(video):
    """Relative video paths (as stored in label files) are resolved against the YawDD folder."""
    path = Path(video)
    return path if path.is_absolute() else YAWDD_DIR / path


def storable_video(video):
    """Path as stored in label files: relative to the YawDD folder when the video is inside it
    (so that no machine-specific absolute path is saved), otherwise unchanged."""
    path = Path(video).resolve()
    try:
        return path.relative_to(YAWDD_DIR.resolve()).as_posix()
    except ValueError:
        return str(video)
