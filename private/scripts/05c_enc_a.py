"""Replace the ENC_A cross-board link with a quieter B.Cu path:
east margin down at x=51.8 was fine, but the y=26 crossing plowed the
B.Cu midfield. New route: along y=6.8 under the top edge (clear of the
header barrel row by 0.15 mm), descending at x=27.5 into the GPIO11
cluster. Removes the previous ENC_A B.Cu attempt first."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, FromMM, mm, to_local


def main():
    b = pcbnew.LoadBoard(str(BOARD_PATH))
    ni = b.FindNet("ENC_A")
    for t in list(b.GetTracks()):
        if t.GetNetname() != "ENC_A":
            continue
        if t.GetClass() == "PCB_VIA":
            b.Delete(t)
        elif t.GetLayer() == pcbnew.B_Cu:
            b.Delete(t)
        else:
            a, c = to_local(t.GetStart()), to_local(t.GetEnd())
            # the two F.Cu link stubs from the previous attempt
            if abs(a[1] - 5.25) < 1.2 and a[0] > 50:
                b.Delete(t)
            elif (round(a[0], 1), round(a[1], 1)) == (25.4, 26.0) or \
                 (round(c[0], 1), round(c[1], 1)) == (25.4, 26.0):
                b.Delete(t)

    def track(pts, layer=pcbnew.F_Cu, w=0.25):
        for p, q in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(mm(*p))
            t.SetEnd(mm(*q))
            t.SetWidth(FromMM(w))
            t.SetLayer(layer)
            t.SetNet(ni)
            b.Add(t)

    def via(xy):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(mm(*xy))
        v.SetWidth(FromMM(0.5))
        v.SetDrill(FromMM(0.25))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        b.Add(v)

    track([(51.8, 4.7), (51.8, 5.8)])
    via((51.8, 5.8))
    track([(51.8, 5.8), (51.8, 6.8), (27.5, 6.8), (27.5, 24.4)],
          layer=pcbnew.B_Cu)
    via((27.5, 24.4))
    track([(27.5, 24.4), (26.6, 23.6)])

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.Save(str(BOARD_PATH))
    print("ENC_A rerouted")


if __name__ == "__main__":
    main()
