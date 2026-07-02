"""Dual-layer BFS maze router for a single stubborn net leg (ENC_A).
States are (cell_x, cell_y, layer); moves are 4-neighbor steps on the
current layer plus layer swaps where a via fits (both layers + hole
clearance). Deterministic; validated by the DRC gate afterwards."""

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

NET = "ENC_A"
START = (51.8, 4.7)     # R25.2 pad — routing starts ON the pad
GOAL = (26.6, 23.6)     # U2 pin 14 (GPIO11) pad
STEP = 0.35
CLR_TRACK = 0.28        # halfwidth 0.125 + clearance 0.15
CLR_VIA = 0.42          # via r 0.25 + clearance 0.15 + slop


def build_obstacles(board):
    perlayer = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    barrels = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == NET:
                continue
            x, y = to_local(p.GetPosition())
            hx = pcbnew.ToMM(p.GetSize().x) / 2
            hy = pcbnew.ToMM(p.GetSize().y) / 2
            box = (x - hx, y - hy, x + hx, y + hy)
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) \
                    else pcbnew.B_Cu
                perlayer[lay].append(box)
            else:
                perlayer[pcbnew.F_Cu].append(box)
                perlayer[pcbnew.B_Cu].append(box)
                barrels.append(box)
    for t in board.GetTracks():
        if t.GetNetname() == NET:
            continue
        if t.GetClass() == "PCB_VIA":
            x, y = to_local(t.GetPosition())
            r = pcbnew.ToMM(t.GetWidth()) / 2
            box = (x - r, y - r, x + r, y + r)
            perlayer[pcbnew.F_Cu].append(box)
            perlayer[pcbnew.B_Cu].append(box)
            barrels.append(box)
        elif t.GetLayer() in perlayer:
            a, b = to_local(t.GetStart()), to_local(t.GetEnd())
            w = pcbnew.ToMM(t.GetWidth()) / 2
            perlayer[t.GetLayer()].append(
                (min(a[0], b[0]) - w, min(a[1], b[1]) - w,
                 max(a[0], b[0]) + w, max(a[1], b[1]) + w))
    return perlayer, barrels


def hit(boxes, x, y, margin):
    for x0, y0, x1, y1 in boxes:
        if x0 - margin < x < x1 + margin and y0 - margin < y < y1 + margin:
            return True
    return False


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    per, barrels = build_obstacles(board)
    layers = (pcbnew.F_Cu, pcbnew.B_Cu)

    def cell(p):
        return (round(p[0] / STEP), round(p[1] / STEP))

    start = cell(START) + (0,)   # layer index 0 = F.Cu
    goal_xy = cell(GOAL)
    prev = {start: None}
    q = deque([start])
    end_state = None
    while q:
        s = q.popleft()
        if (s[0], s[1]) == goal_xy and s[2] == 0:
            end_state = s
            break
        cx, cy = s[0] * STEP, s[1] * STEP
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (s[0] + d[0], s[1] + d[1], s[2])
            if n in prev:
                continue
            x, y = n[0] * STEP, n[1] * STEP
            if not (1.2 < x < BOARD_W - 1.2 and 1.2 < y < BOARD_H - 1.2):
                continue
            if hit(per[layers[s[2]]], x, y, CLR_TRACK):
                continue
            prev[n] = s
            q.append(n)
        # layer swap (via)
        n = (s[0], s[1], 1 - s[2])
        if n not in prev and not hit(per[layers[0]], cx, cy, CLR_VIA) \
                and not hit(per[layers[1]], cx, cy, CLR_VIA) \
                and not hit(barrels, cx, cy, 0.55):
            prev[n] = s
            q.append(n)
    if end_state is None:
        print("NEEDS-REVIEW: dual-layer maze found no path for", NET)
        return

    path = []
    s = end_state
    while s is not None:
        path.append(s)
        s = prev[s]
    path.reverse()

    ni = board.FindNet(NET)

    def track(a, b, layer):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*b))
        t.SetWidth(FromMM(0.25))
        t.SetLayer(layer)
        t.SetNet(ni)
        board.Add(t)

    def via(xy):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(mm(*xy))
        v.SetWidth(FromMM(0.5))
        v.SetDrill(FromMM(0.25))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        board.Add(v)

    print(f"maze path found: {len(path)} steps, emitting...")
    # per-step tracks (electrically identical to merged runs),
    # vias at layer changes
    for a, b in zip(path, path[1:]):
        pa = (a[0] * STEP, a[1] * STEP)
        pb = (b[0] * STEP, b[1] * STEP)
        if a[2] != b[2]:
            via(pa)
        else:
            track(pa, pb, layers[a[2]])
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(str(BOARD_PATH))
    print("maze route emitted")


if __name__ == "__main__":
    main()
