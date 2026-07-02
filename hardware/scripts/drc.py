"""DRC via the pcbnew API (kicad-cli hangs headless on this machine).

Applies JLCPCB 4-layer capability limits to the board design settings,
runs the full DRC engine, and prints a violation summary. Exit code 1
if any error-severity violation or unconnected item remains.

JLCPCB 4-layer standard capabilities (jlcpcb.com/capabilities, checked
2026-07): min trace/space 0.09 mm (we enforce 0.127 conservative),
min via drill 0.15 mm laser / 0.3 mm mechanical (we use 0.3), min
annular ring 0.05 mm (we use 0.15), board-edge clearance 0.3 mm.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, FromMM

REPORT = Path(__file__).parent / "drc_report.txt"


def apply_rules(board):
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = FromMM(0.127)
    ds.m_ViasMinSize = FromMM(0.4)
    ds.m_MinThroughDrill = FromMM(0.25)
    ds.m_ViasMinAnnularWidth = FromMM(0.1)
    ds.m_MinClearance = FromMM(0.127)
    ds.m_CopperEdgeClearance = FromMM(0.3)
    ds.m_HoleClearance = FromMM(0.254)


def run(board_path=None, save_rules=True):
    board = pcbnew.LoadBoard(str(board_path or BOARD_PATH))
    apply_rules(board)
    if save_rules:
        board.Save(board.GetFileName())
    pcbnew.WriteDRCReport(board, str(REPORT), pcbnew.EDA_UNITS_MM, True)
    text = REPORT.read_text()

    m_v = re.search(r"\*\* Found (\d+) DRC violations \*\*", text)
    m_u = re.search(r"\*\* Found (\d+) unconnected pads \*\*", text)
    nv = int(m_v.group(1)) if m_v else -1
    nu = int(m_u.group(1)) if m_u else -1

    # violation type histogram
    types = {}
    for line in text.splitlines():
        m = re.match(r"\[(\w+)\]: (.*)", line)
        if m:
            types[m.group(1)] = types.get(m.group(1), 0) + 1
    print(f"violations={nv} unconnected={nu}")
    for t, n in sorted(types.items(), key=lambda kv: -kv[1]):
        print(f"  {t}: {n}")
    return nv, nu, text


if __name__ == "__main__":
    nv, nu, _ = run()
    sys.exit(0 if nv == 0 and nu == 0 else 1)
