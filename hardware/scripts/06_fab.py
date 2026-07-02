"""Generate JLCPCB fabrication outputs into fab/.

- Gerbers + Excellon drill (JLCPCB layer set) via kicad-cli (kcli.sh)
- BOM CSV (Comment,Designator,Footprint,LCSC) grouped from board.json
- CPL CSV (Designator,Mid X,Mid Y,Layer,Rotation) from the board.
  Rotations are KiCad-native: JLC's zero-angle conventions differ per
  package, so the human-review checklist requires checking the JLC
  assembly preview for the polarity-critical parts.
- board renders (top/bottom) for the README.

Run under KiCad python AFTER routing + DRC.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, HW, load_bridge, to_local

FAB = HW.parent / "fab"
KCLI = HW / "scripts" / "kcli.sh"


def gerbers():
    out = FAB / "gerbers"
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(KCLI), "pcb", "export", "gerbers",
                    "--layers",
                    "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,B.Silkscreen,"
                    "F.Mask,B.Mask,Edge.Cuts",
                    "--subtract-soldermask",
                    "-o", str(out) + "/", str(BOARD_PATH)], check=True)
    subprocess.run([str(KCLI), "pcb", "export", "drill",
                    "--format", "excellon", "--drill-origin", "absolute",
                    "--excellon-units", "mm",
                    "--generate-map", "--map-format", "gerberx2",
                    "-o", str(out) + "/", str(BOARD_PATH)], check=True)
    print("gerbers ->", out)


def bom():
    bridge = load_bridge()
    groups = {}
    for p in bridge["parts"]:
        key = (p["value"], p["footprint"].split(":")[-1], p["lcsc"])
        groups.setdefault(key, []).append(p["ref"])
    with open(FAB / "bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (val, fp, lcsc), refs in sorted(groups.items(),
                                            key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), fp, lcsc])
    print("bom.csv:", len(groups), "line items")


def cpl():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    rows = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith(("H", "FID")):
            continue
        x, y = to_local(fp.GetPosition())
        rows.append([ref, fp.GetValue(),
                     str(fp.GetFPID().GetLibItemName()),
                     f"{x:.3f}", f"{-y:.3f}",   # JLC: +y up
                     "top" if fp.GetLayer() == pcbnew.F_Cu else "bottom",
                     f"{fp.GetOrientationDegrees():.1f}"])
    with open(FAB / "cpl.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y",
                    "Layer", "Rotation"])
        w.writerows(sorted(rows))
    print("cpl.csv:", len(rows), "placements")


def renders():
    out = FAB / "renders"
    out.mkdir(parents=True, exist_ok=True)
    for side in ("top", "bottom"):
        subprocess.run([str(KCLI), "pcb", "render", "--side", side,
                        "--background", "opaque", "-w", "1600", "-h", "1100",
                        "-o", str(out / f"board_{side}.png"),
                        str(BOARD_PATH)], check=True)
    print("renders ->", out)


if __name__ == "__main__":
    FAB.mkdir(exist_ok=True)
    gerbers()
    bom()
    cpl()
    renders()
