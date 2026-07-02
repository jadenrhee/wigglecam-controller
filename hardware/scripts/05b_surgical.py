"""Surgical closes for the final connectivity gaps — the scripted
equivalent of the last half-dozen hand-routed airwires. Coordinates
were measured from the live board (see git history); each is verified
by the DRC gate afterwards.

Applied once to the routed board; not part of the regenerative
pipeline (01→04). If the board is regenerated from scratch, re-run
the pipeline and re-apply / adapt.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, FromMM, mm


def track(board, net, pts, w=0.25, layer=pcbnew.F_Cu):
    ni = board.FindNet(net)
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*b))
        t.SetWidth(FromMM(w))
        t.SetLayer(layer)
        t.SetNet(ni)
        board.Add(t)


def via(board, net, xy):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(mm(*xy))
    v.SetWidth(FromMM(0.5))
    v.SetDrill(FromMM(0.25))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(board.FindNet(net))
    board.Add(v)


def main():
    b = pcbnew.LoadBoard(str(BOARD_PATH))
    # flash VCC island -> 3V3 plane
    track(b, "+3V3", [(24.3, 10.3), (25.5, 9.6)])
    via(b, "+3V3", (25.5, 9.6))
    # C6 (U2 pin-1 decoupler) island -> plane
    track(b, "+3V3", [(24.1, 18.3), (24.1, 17.1)])
    via(b, "+3V3", (24.1, 17.1))
    # U2 pin 33 -> plane, east of the pad column
    track(b, "+3V3", [(33.4, 22.0), (34.5, 22.0)])
    via(b, "+3V3", (34.5, 22.0))
    # U2 pin 42 -> plane, same pattern
    track(b, "+3V3", [(33.4, 18.4), (34.5, 18.4)])
    via(b, "+3V3", (34.5, 18.4))
    # C11 -> plane, west stub
    track(b, "+3V3", [(35.2, 13.6), (34.0, 13.6)])
    via(b, "+3V3", (34.0, 13.6))
    # ENC_A: R25 output -> B.Cu run down the encoder margin and across
    # -> up into the RC/GPIO cluster west of the crystal
    track(b, "ENC_A", [(51.8, 4.7), (51.8, 5.8)])
    via(b, "ENC_A", (51.8, 5.8))
    track(b, "ENC_A", [(51.8, 5.8), (51.8, 26.0), (25.4, 26.0)],
          layer=pcbnew.B_Cu)
    via(b, "ENC_A", (25.4, 26.0))
    track(b, "ENC_A", [(25.4, 26.0), (26.1, 25.0)])

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.Save(str(BOARD_PATH))
    print("surgical closes applied")


if __name__ == "__main__":
    main()
