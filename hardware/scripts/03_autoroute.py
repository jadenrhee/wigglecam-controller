"""Export DSN for Freerouting / import the SES it produces.

Usage (KiCad python):
  03_autoroute.py export   -> writes wigglecam.dsn
  03_autoroute.py import   -> reads wigglecam.ses back into the board

The Freerouting jar itself is driven from the shell between the two
steps (see docs/plan.md phase 3): its output is treated as a draft —
04_cleanup re-asserts critical geometry and the DRC gate decides.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH

DSN = BOARD_PATH.with_suffix(".dsn")
SES = BOARD_PATH.with_suffix(".ses")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "export"
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    if mode == "export":
        ok = pcbnew.ExportSpecctraDSN(board, str(DSN))
        print("DSN export:", ok, DSN)
    else:
        ok = pcbnew.ImportSpecctraSES(board, str(SES))
        board.Save(str(BOARD_PATH))
        print("SES import:", ok)


if __name__ == "__main__":
    main()
