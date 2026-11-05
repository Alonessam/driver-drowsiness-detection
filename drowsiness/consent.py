"""Image sharing permission of a video (yawdd_sharing_permission.csv, built from YawDD Table1/Table2)."""
import csv
from pathlib import Path

_CSV = Path(__file__).resolve().parents[1] / "yawdd_sharing_permission.csv"
_permissions = None


def _load():
    global _permissions
    if _permissions is None:
        _permissions, conflicting = {}, set()
        if _CSV.exists():
            with open(_CSV, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    name = Path(row["video"].replace("\\", "/")).name.lower()
                    if name in _permissions and _permissions[name] != row["image_sharing_permission"]:
                        conflicting.add(name)
                    _permissions[name] = row["image_sharing_permission"]
            for name in conflicting:  # same file name with different permissions is treated as unknown
                _permissions.pop(name)
    return _permissions


def image_sharing_permission(video_path):
    """Returns 'yes', 'no' or 'unknown'.

    Videos outside YawDD (e.g. UTA-RLDD) and videos missing from the list are 'unknown'.
    """
    if "yawdd" not in str(video_path).lower():
        return "unknown"
    return _load().get(Path(str(video_path).replace("\\", "/")).name.lower(), "unknown")
