"""Deterministic single-net B.Cu maze route (BFS on a 0.4 mm grid over
the true obstacle map) — used for the one leg (ENC_A) that both the
autorouter and hand lanes kept failing. Endpoints get vias; the F.Cu
tails tie into the existing net copper.
"""

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

NET = "ENC_A"
START = (51.8, 5.8)     # near R25.2 (51.8, 4.7)
GOAL = (27.5, 24.4)     # near the GPIO11 cluster (pin14 at 26.6, 23.6)
STEP = 0.4
CLR = 0.30              # track halfwidth 0.125 + clearance 0.15 + slop


def obstacles(board):
    obs = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == NET:
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                continue  # front-side SMD pads don't exist on B.Cu
            x, y = to_local(p.GetPosition())
            r = max(pcbnew.ToMM(p.GetSize().x),
                    pcbnew.ToMM(p.GetSize().y)) / 2
            obs.append((x, y, x, y, r))
    for t in board.GetTracks():
        if t.GetNetname() == NET:
            continue
        if t.GetClass() == "PCB_VIA":
            x, y = to_local(t.GetPosition())
            obs.append((x, y, x, y, pcbnew.ToMM(t.GetWidth()) / 2))
        elif t.GetLayer() == pcbnew.B_Cu:
            a, b = to_local(t.GetStart()), to_local(t.GetEnd())
            w = pcbnew.ToMM(t.GetWidth()) / 2
            obs.append((min(a[0], b[0]), min(a[1], b[1]),
                        max(a[0], b[0]), max(a[1], b[1]), w))
    return obs


def blocked(obs, x, y):
    for x0, y0, x1, y1, r in obs:
        cx = min(max(x, x0), x1)
        cy = min(max(y, y0), y1)
        if (x - cx) ** 2 + (y - cy) ** 2 < (r + CLR) ** 2:
            return True
    return False


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    obs = obstacles(board)

    def cell(p):
        return (round(p[0] / STEP), round(p[1] / STEP))

    start, goal = cell(START), cell(GOAL)
    prev = {start: None}
    q = deque([start])
    found = False
    while q:
        c = q.popleft()
        if c == goal:
            found = True
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            x, y = n[0] * STEP, n[1] * STEP
            if not (1.2 < x < BOARD_W - 1.2 and 1.2 < y < BOARD_H - 1.2):
                continue
            if n in prev or blocked(obs, x, y):
                continue
            prev[n] = c
            q.append(n)
    if not found:
        print("NEEDS-REVIEW: BFS found no B.Cu path for", NET)
        return

    path = []
    c = goal
    while c is not None:
        path.append((c[0] * STEP, c[1] * STEP))
        c = prev[c]
    path.reverse()
    # compress collinear runs
    pts = [path[0]]
    for a, b in zip(path[1:], path[2:]):
        if (a[0] - pts[-1][0]) * (b[1] - a[1]) != \
                (a[1] - pts[-1][1]) * (b[0] - a[0]):
            pts.append(a)
    pts.append(path[-1])

    ni = board.FindNet(NET)

    def track(seq, layer, w=0.25):
        for p, q2 in zip(seq, seq[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(mm(*p))
            t.SetEnd(mm(*q2))
            t.SetWidth(FromMM(w))
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

    via(pts[0])
    via(pts[-1])
    track(pts, pcbnew.B_Cu)
    track([(51.8, 4.7), pts[0]], pcbnew.F_Cu)     # R25.2 tail
    track([pts[-1], (26.6, 23.6)], pcbnew.F_Cu)   # GPIO11 tail
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(str(BOARD_PATH))
    print(f"BFS route: {len(pts)} waypoints from {pts[0]} to {pts[-1]}")


if __name__ == "__main__":
    main()
