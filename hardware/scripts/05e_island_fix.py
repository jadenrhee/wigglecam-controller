"""Apply the two-lobe VLED island to the LIVE board, remove the taps
that the old island invalidated or that landed on routed copper, and
re-tap the affected pads collision-aware against ALL current copper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module
VLED_ISLAND = import_module("02_route_critical").VLED_ISLAND \
    if False else [
    (6, 1.5), (15, 1.5), (15, 12.2), (41, 12.2), (41, 1.5),
    (74.5, 1.5), (74.5, 38), (69, 38), (69, 10), (50, 10),
    (50, 19.5), (41, 19.5), (41, 13.2), (15, 13.2), (15, 13),
    (11, 13), (11, 24), (6, 24),
]

DELETE_VIAS = [(35.02, 12.48), (24.1, 17.1), (32.2, 21.8), (42.4, 10.2)]
DELETE_TRACKS = [((35.02, 11.38), (35.02, 12.48)),
                 ((24.1, 18.3), (24.1, 17.1))]
RETAP = ["C6"]   # re-tap these parts' +3V3 pads collision-aware


def main():
    b = pcbnew.LoadBoard(str(BOARD_PATH))

    # 1) replace the VLED zone outline
    for z in list(b.Zones()):
        if z.GetNetname() == "VLED":
            b.Delete(z)
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.In2_Cu)
    z.SetNet(b.FindNet("VLED"))
    z.SetAssignedPriority(1)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetMinThickness(FromMM(0.2))
    z.SetLocalClearance(FromMM(0.2))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in VLED_ISLAND:
        ol.Append(mm(x, y).x, mm(x, y).y)
    b.Add(z)

    # 2) deletions
    ndel = 0
    for t in list(b.GetTracks()):
        p = to_local(t.GetPosition()) if t.GetClass() == "PCB_VIA" else None
        if p and any(abs(p[0]-x) < 0.05 and abs(p[1]-y) < 0.05
                     for x, y in DELETE_VIAS):
            b.Delete(t)
            ndel += 1
        elif t.GetClass() == "PCB_TRACK":
            a, c = to_local(t.GetStart()), to_local(t.GetEnd())
            for (x0, y0), (x1, y1) in DELETE_TRACKS:
                if ((abs(a[0]-x0) < 0.05 and abs(a[1]-y0) < 0.05 and
                     abs(c[0]-x1) < 0.05 and abs(c[1]-y1) < 0.05) or
                    (abs(c[0]-x0) < 0.05 and abs(c[1]-y0) < 0.05 and
                     abs(a[0]-x1) < 0.05 and abs(a[1]-y1) < 0.05)):
                    b.Delete(t)
                    ndel += 1
    print(f"deleted {ndel} items")

    # 3) re-add a via at (35.02, 11.38) — now over true 3V3 plane
    def via(net, xy):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(mm(*xy))
        v.SetWidth(FromMM(0.5))
        v.SetDrill(FromMM(0.25))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(b.FindNet(net))
        b.Add(v)

    via("+3V3", (35.02, 11.38))

    # 4) collision-aware re-tap for C6's +3V3 pad
    boxes = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == "+3V3":
                continue
            x, y = to_local(p.GetPosition())
            hx = pcbnew.ToMM(p.GetSize().x) / 2
            hy = pcbnew.ToMM(p.GetSize().y) / 2
            boxes.append((x-hx, y-hy, x+hx, y+hy))
    for t in b.GetTracks():
        if t.GetNetname() == "+3V3":
            continue
        a, c = to_local(t.GetStart()), to_local(t.GetEnd())
        w = pcbnew.ToMM(t.GetWidth()) / 2
        boxes.append((min(a[0], c[0])-w, min(a[1], c[1])-w,
                      max(a[0], c[0])+w, max(a[1], c[1])+w))

    def clear(x0, y0, x1, y1, m=0.15):
        return all(x1+m < bx0 or x0-m > bx1 or y1+m < by0 or y0-m > by1
                   for bx0, by0, bx1, by1 in boxes)

    for ref in RETAP:
        fp = next(f for f in b.GetFootprints() if f.GetReference() == ref)
        for p in fp.Pads():
            if p.GetNetname() != "+3V3":
                continue
            x, y = to_local(p.GetPosition())
            done = False
            for dx, dy in ((0, -1.1), (0, 1.1), (1.1, 0), (-1.1, 0),
                           (0.9, -0.9), (-0.9, -0.9), (0.9, 0.9),
                           (-0.9, 0.9), (0, -1.6), (0, 1.6)):
                vx, vy = x+dx, y+dy
                if not clear(min(x, vx)-0.45, min(y, vy)-0.45,
                             max(x, vx)+0.45, max(y, vy)+0.45):
                    continue
                ni = b.FindNet("+3V3")
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(mm(x, y))
                t.SetEnd(mm(vx, vy))
                t.SetWidth(FromMM(0.25))
                t.SetLayer(pcbnew.F_Cu)
                t.SetNet(ni)
                b.Add(t)
                via("+3V3", (vx, vy))
                print(f"re-tapped {ref} at ({vx:.1f},{vy:.1f})")
                done = True
                break
            if not done:
                print(f"NEEDS-REVIEW: {ref} +3V3 pad has no clear tap")

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.Save(str(BOARD_PATH))
    print("island fix applied")


if __name__ == "__main__":
    main()
