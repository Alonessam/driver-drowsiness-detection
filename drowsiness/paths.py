"""Project paths. The YawDD dataset location can be overridden with the YAWDD_DIR environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "face_landmarker.task"
YAWDD_DIR = Path(os.environ.get("YAWDD_DIR", ROOT / "data" / "YawDD"))


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
