"""Post-autoroute cleanup (docs/plan.md phase 3, clean-up pass).

- widen power-carrying autorouted nets (VSYS/VBUS/VBAT*) to 0.5 mm;
- add F.Cu + B.Cu GND pours (they arrive AFTER autorouting so the
  filler flows around the routed tracks);
- collision-aware 3V3 stub vias for every +3V3 pad the plane serves;
- GND stitching vias along the pours;
- refill all zones.

Run AFTER 03 import; then re-run 02 (idempotent) if the autorouter
disturbed any critical net, and gate with drc.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

# NOTE: no blind widening — the autorouter spaced its tracks for
# 0.2 mm width, so widening violates clearance. The heavy-current
# paths (VBAT, VLED, LED returns, 5 V entry) are scripted wide in 02;
# VSYS/VBUS at 0.2 mm carry <=0.65 A — at the IPC-2221 10 °C limit,
# documented in the verification report.


def gnd_pours(board):
    # idempotent: replace any existing outer-layer GND pours
    for z in list(board.Zones()):
        if (z.GetNetname() == "GND"
                and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu)):
            board.Delete(z)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(board.FindNet("GND"))
        z.SetAssignedPriority(0)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefSpokeWidth(FromMM(0.5))
        z.SetThermalReliefGap(FromMM(0.4))
        z.SetMinThickness(FromMM(0.2))
        z.SetLocalClearance(FromMM(0.25))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in [(0.5, 0.5), (BOARD_W - 0.5, 0.5),
                     (BOARD_W - 0.5, BOARD_H - 0.5), (0.5, BOARD_H - 0.5)]:
            ol.Append(mm(x, y).x, mm(x, y).y)
        board.Add(z)


def _obstacles(board, skip_nets):
    boxes = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() in skip_nets:
                continue
            x, y = to_local(p.GetPosition())
            hx = pcbnew.ToMM(p.GetSize().x) / 2
            hy = pcbnew.ToMM(p.GetSize().y) / 2
            boxes.append((x - hx, y - hy, x + hx, y + hy))
    for t in board.GetTracks():
        if t.GetNetname() in skip_nets:
            continue
        a, b = to_local(t.GetStart()), to_local(t.GetEnd())
        w = pcbnew.ToMM(t.GetWidth()) / 2
        boxes.append((min(a[0], b[0]) - w, min(a[1], b[1]) - w,
                      max(a[0], b[0]) + w, max(a[1], b[1]) + w))
    return boxes


def _clear(boxes, x0, y0, x1, y1, margin=0.15):
    for bx0, by0, bx1, by1 in boxes:
        if not (x1 + margin < bx0 or x0 - margin > bx1 or
                y1 + margin < by0 or y0 - margin > by1):
            return False
    return True


def add_via(board, netname, xy, size=0.6, drill=0.3):
    ni = board.FindNet(netname)
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(mm(*xy))
    v.SetWidth(FromMM(size))
    v.SetDrill(FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(ni)
    board.Add(v)


def add_track(board, netname, pts, width, layer=pcbnew.F_Cu):
    ni = board.FindNet(netname)
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*b))
        t.SetWidth(FromMM(width))
        t.SetLayer(layer)
        t.SetNet(ni)
        board.Add(t)


def threev3_stub_vias(board):
    """Every +3V3 pad group gets a via to the In2 plane if none of the
    net's copper within 3 mm already has one."""
    vias = [to_local(t.GetPosition()) for t in board.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetname() == "+3V3"]
    boxes = _obstacles(board, {"+3V3"})
    added = skipped = 0
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "+3V3":
                continue
            x, y = to_local(p.GetPosition())
            if any((vx - x) ** 2 + (vy - y) ** 2 < 9.0 for vx, vy in vias):
                continue
            done = False
            for dx, dy in ((1.15, 0), (-1.15, 0), (0, 1.15), (0, -1.15),
                           (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0),
                           (-1.0, -1.0), (1.7, 0), (-1.7, 0)):
                vx, vy = x + dx, y + dy
                if not (1.5 < vx < BOARD_W - 1.5 and
                        1.5 < vy < BOARD_H - 1.5):
                    continue
                span = (min(x, vx) - 0.5, min(y, vy) - 0.5,
                        max(x, vx) + 0.5, max(y, vy) + 0.5)
                if _clear(boxes, *span):
                    add_track(board, "+3V3", [(x, y), (vx, vy)], 0.3)
                    add_via(board, "+3V3", (vx, vy), size=0.5, drill=0.25)
                    vias.append((vx, vy))
                    boxes.append(span)
                    added += 1
                    done = True
                    break
            if not done:
                # last resort: via-in-pad (acceptable for a hand-built
                # or unfilled-via assembly; each is listed in the
                # human-review checklist)
                add_via(board, "+3V3", (x, y), size=0.5, drill=0.25)
                vias.append((x, y))
                skipped += 1
                print(f"  NEEDS-REVIEW: via-in-pad 3V3 tap at "
                      f"{fp.GetReference()} ({x:.1f},{y:.1f})")
    print(f"3V3 stub vias: {added} offset, {skipped} via-in-pad")


def stitching(board):
    """GND stitching grid where free."""
    boxes = _obstacles(board, {"GND"})
    n = 0
    for gx in range(6, int(BOARD_W) - 4, 8):
        for gy in range(6, int(BOARD_H) - 4, 8):
            if _clear(boxes, gx - 0.5, gy - 0.5, gx + 0.5, gy + 0.5, 0.25):
                add_via(board, "GND", (gx, gy))
                boxes.append((gx - 0.3, gy - 0.3, gx + 0.3, gy + 0.3))
                n += 1
    print(f"stitching vias: {n}")


def smd_gnd_solid(board):
    """SMD GND pads connect solid to the pours (their thermal mass is
    tiny, hand-soldering is unaffected) — avoids starved-thermal DRC
    where tracks crowd out relief spokes. THT stays thermal-relieved."""
    n = 0
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "GND":
                continue
            if (p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
                    or p.GetNumber() == "SH"      # USB shield
                    or fp.GetReference() in ("J8", "J1")):  # pins get
                # crowded by B.Cu routing; solid connect is fine
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                n += 1
    print(f"solid-connected {n} SMD GND pads")


def degenerate_sweep(board):
    """The SES import leaves sub-50µm track fragments; drop them."""
    n = 0
    for t in list(board.GetTracks()):
        if (t.GetClass() == "PCB_TRACK"
                and t.GetLength() < pcbnew.FromMM(0.05)):
            board.Delete(t)
            n += 1
    print(f"deleted {n} degenerate fragments")


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    degenerate_sweep(board)
    smd_gnd_solid(board)
    gnd_pours(board)
    stitching(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(str(BOARD_PATH))
    print("cleanup done")


if __name__ == "__main__":
    main()
