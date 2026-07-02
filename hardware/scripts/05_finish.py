"""Final-mile closer: read the DRC report's unconnected pairs and draw
short, collision-checked tracks to close them — the scripted analog of
hand-finishing the last airwires. Pairs it can't close safely are
printed as NEEDS-REVIEW for the human checklist.

Usage: 05_finish.py <drc.json>   (then re-run DRC to verify)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local


def _obstacles(board, skip_net):
    boxes = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == skip_net:
                continue
            x, y = to_local(p.GetPosition())
            hx = pcbnew.ToMM(p.GetSize().x) / 2
            hy = pcbnew.ToMM(p.GetSize().y) / 2
            boxes.append((x - hx, y - hy, x + hx, y + hy))
    for t in board.GetTracks():
        if t.GetNetname() == skip_net:
            continue
        a, b = to_local(t.GetStart()), to_local(t.GetEnd())
        w = pcbnew.ToMM(t.GetWidth()) / 2
        boxes.append((min(a[0], b[0]) - w, min(a[1], b[1]) - w,
                      max(a[0], b[0]) + w, max(a[1], b[1]) + w))
    return boxes


def _clear_seg(boxes, a, b, hw=0.28):
    x0, y0 = min(a[0], b[0]) - hw, min(a[1], b[1]) - hw
    x1, y1 = max(a[0], b[0]) + hw, max(a[1], b[1]) + hw
    for bx0, by0, bx1, by1 in boxes:
        if not (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1):
            return False
    return True


def main():
    drc = json.loads(Path(sys.argv[1]).read_text())
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    fixed = skipped = 0
    cache = {}
    for u in drc.get("unconnected_items", []):
        items = u["items"]
        if len(items) != 2:
            continue
        m = re.search(r"\[([^\]]+)\]", items[0]["description"])
        if not m:
            continue
        net = m.group(1)
        if net.startswith(("Zone", "<")) or "Zone" in items[0]["description"]:
            continue
        if "Zone" in items[1]["description"]:
            continue
        pts = []
        for it in items:
            pos = it.get("pos")
            if not pos:
                break
            pts.append((pos["x"] - 100.0, pos["y"] - 100.0))
        if len(pts) != 2:
            continue
        a, b = pts
        # plane nets: a via at the pad IS the connection — but only if
        # the via hole clears all other copper there
        if net in ("+3V3", "GND", "VLED"):
            if net not in cache:
                cache[net] = _obstacles(board, net)
            done = False
            for it, pt in zip(items, pts):
                if "Pad" not in it["description"]:
                    continue
                span = (pt[0] - 0.45, pt[1] - 0.45,
                        pt[0] + 0.45, pt[1] + 0.45)
                if not _clear_seg(cache[net], (pt[0], pt[1]),
                                  (pt[0], pt[1]), hw=0.45):
                    continue
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(mm(*pt))
                v.SetWidth(FromMM(0.5))
                v.SetDrill(FromMM(0.25))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(board.FindNet(net))
                board.Add(v)
                cache[net].append(span)
                print(f"via-in-pad {net} at ({pt[0]:.1f},{pt[1]:.1f})"
                      " (NEEDS-REVIEW)")
                fixed += 1
                done = True
                break
            if done:
                continue
        d = ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5
        if d > 4.0 or d < 0.01:
            skipped += 1
            print(f"NEEDS-REVIEW: {net} gap {d:.1f} mm at "
                  f"({a[0]:.1f},{a[1]:.1f}) — too long to auto-close")
            continue
        if net not in cache:
            cache[net] = _obstacles(board, net)
        boxes = cache[net]
        ni = board.FindNet(net)
        if ni is None:
            continue
        # try straight, then two L-shapes
        for path in ([a, b],
                     [a, (a[0], b[1]), b],
                     [a, (b[0], a[1]), b]):
            ok = all(_clear_seg(boxes, p, q)
                     for p, q in zip(path, path[1:]))
            if ok:
                for p, q in zip(path, path[1:]):
                    if p == q:
                        continue
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(mm(*p))
                    t.SetEnd(mm(*q))
                    t.SetWidth(FromMM(0.25))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(ni)
                    board.Add(t)
                fixed += 1
                break
        else:
            skipped += 1
            print(f"NEEDS-REVIEW: {net} gap at ({a[0]:.1f},{a[1]:.1f})"
                  f"->({b[0]:.1f},{b[1]:.1f}) — no clear path")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(str(BOARD_PATH))
    print(f"closed {fixed}, needs-review {skipped}")


if __name__ == "__main__":
    main()
