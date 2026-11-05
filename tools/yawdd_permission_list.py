"""(Extra tool; requires PyMuPDF: pip install pymupdf)
Extracts the image sharing permission of every video from the YawDD Table1/Table2 PDFs.

Permission is evaluated per participant and conservatively: if ALL of a participant's rows in the table
are "Yes" the permission is 'yes', if all are "No" it is 'no', and if they are mixed it counts as 'no'
(and is flagged 'mixed').

Usage: python -I tools/yawdd_permission_list.py "<YawDD folder>" <output.csv>
"""
import csv
import os
import re
import sys
from collections import Counter, defaultdict

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
root, output = sys.argv[1], sys.argv[2]


def yes_no(text):
    t = (text or "").strip().lower()
    return "yes" if t == "yes" else "no" if t == "no" else None


def read_tables(pdf_path, header_word_count=3):
    """(gender, participant no) -> set of permission values."""
    result = defaultdict(set)
    doc = fitz.open(pdf_path)
    gender = "Male"
    for page in doc:
        for table in page.find_tables().tables:
            rows = table.extract()
            if rows and "Female" in (rows[0][0] or ""):
                gender = "Female"
            elif rows and "Male" in (rows[0][0] or ""):
                gender = "Male"
            elif "Female" in page.get_text().split()[:header_word_count]:
                gender = "Female"
            for r in rows:
                if r and (r[0] or "").strip().isdigit() and yes_no(r[-1]):
                    result[(gender, int(r[0]))].add(yes_no(r[-1]))
    return result


mirror_permissions = read_tables(os.path.join(root, "Table1.pdf"))
dash_permissions = read_tables(os.path.join(root, "Table2.pdf"))
mixed = [(k, sorted(v)) for k, v in {**{("M",) + k: v for k, v in mirror_permissions.items()},
                                     **{("D",) + k: v for k, v in dash_permissions.items()}}.items() if len(v) > 1]
print(f"Table1 (mirror) participants: {len(mirror_permissions)} | Table2 (dash) participants: "
      f"{len(dash_permissions)} | participants with mixed permissions: {len(mixed)} {mixed[:6]}")


def decide(permissions):
    if permissions == {"yes"}:
        return "yes", ""
    if permissions == {"no"}:
        return "no", ""
    if permissions:
        return "no", "mixed"
    return "?", ""


rows, unresolved = [], []
for folder, _, files in os.walk(root):
    for name in sorted(files):
        if not name.lower().endswith(".avi"):
            continue
        rel = os.path.relpath(os.path.join(folder, name), root)
        m = re.match(r"(\d+)-(Male|Female)(NoGlasses|SunGlasses|Glasses)(\w*)\s*(?:-(.+?))?(?:\.avi)+$", name, re.I)
        if not m:
            unresolved.append(rel); continue
        number, gender = int(m[1]), m[2].capitalize()
        g = m[3].lower()
        glasses = "NoGlasses" if g == "noglasses" else "SunGlasses" if g == "sunglasses" else "Glasses"
        action = m[5] or ""
        camera = "Mirror" if action else "Dash"
        permission, note = decide((mirror_permissions if camera == "Mirror" else dash_permissions).get((gender, number), set()))
        rows.append((rel, camera, number, gender, action or "Normal-Talking-Yawning", glasses, permission, note))

rows.sort()
with open(output, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["video", "camera", "participant", "gender", "action", "glasses", "image_sharing_permission", "note"])
    w.writerows(rows)

print(f"Matched videos: {len(rows)} | unresolved names: {len(unresolved)} {unresolved[:3]}")
print("Permission distribution:", dict(Counter(r[6] for r in rows)))
print("\nVideos with permission 'yes' (camera x glasses type):")
for k, v in sorted(Counter((r[1], r[5]) for r in rows if r[6] == "yes").items()):
    print(f"  {k[0]:<7} {k[1]:<11} {v}")
print("\nExamples of Yawning videos with permission 'yes' (by glasses type):")
for g in ("NoGlasses", "Glasses", "SunGlasses"):
    examples = [r[0] for r in rows if r[6] == "yes" and r[5] == g and r[4].lower() == "yawning"][:2]
    for e in examples:
        print(f"  {g:<10} {e}")
print("\nCSV:", output)
