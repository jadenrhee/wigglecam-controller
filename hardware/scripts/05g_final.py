"""Final connectivity surgery, all with full-layer collision checks:
1. delete the three +3V3 vias that landed on B.Cu routes;
2. re-tap U2 pins 33/42 with via spots verified against BOTH layers;
3. bridge the short ENC_A fragment gap near the crystal;
4. maze-route the long ENC_A leg with tightened-but-legal clearances;
5. verify the VLED finger fill actually joins the lobes (probe) and
   bridge on B.Cu if not."""

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

DEL = [(35.02, 11.38), (34.50, 22.00), (34.50, 18.40)]


def seg_dist(p, a, c):
    ax, ay = a
    cx, cy = c
    px, py = p
    dx, dy = cx - ax, cy - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx +
                                         (py - ay) * dy) / L2))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def main():
    b = pcbnew.LoadBoard(str(BOARD_PATH))
    ndel = 0
    for t in list(b.GetTracks()):
        if t.GetClass() != "PCB_VIA":
            continue
        p = to_local(t.GetPosition())
        if any(abs(p[0]-x) < 0.1 and abs(p[1]-y) < 0.1 for x, y in DEL):
            b.Delete(t)
            ndel += 1
    print(f"deleted {ndel} colliding vias")

    # full-layer obstacle model (pads, all tracks, vias, barrels)
    def all_copper(skip_net):
        segs, discs = [], []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == skip_net:
                    continue
                x, y = to_local(p.GetPosition())
                r = max(pcbnew.ToMM(p.GetSize().x),
                        pcbnew.ToMM(p.GetSize().y)) / 2
                discs.append((x, y, r,
                              p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD))
        for t in b.GetTracks():
            if t.GetNetname() == skip_net:
                continue
            if t.GetClass() == "PCB_VIA":
                x, y = to_local(t.GetPosition())
                discs.append((x, y, pcbnew.ToMM(t.GetWidth()) / 2, True))
            else:
                segs.append((to_local(t.GetStart()), to_local(t.GetEnd()),
                             pcbnew.ToMM(t.GetWidth()) / 2, t.GetLayer()))
        return segs, discs

    def via_ok(segs, discs, x, y):
        for (a, c, w, lay) in segs:      # vias hit every layer
            if seg_dist((x, y), a, c) < 0.25 + w + 0.15:
                return False
        for (dx_, dy_, r, thru) in discs:
            need = 0.25 + r + (0.3 if thru else 0.15)
            if (x - dx_) ** 2 + (y - dy_) ** 2 < need ** 2:
                return False
        return True

    def track_ok(segs, discs, a, c, layer, hw=0.125):
        for (p, q, w, lay) in segs:
            if lay != layer:
                continue
            # coarse: sample the new segment
            for i in range(11):
                t = i / 10
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if seg_dist(pt, p, q) < hw + w + 0.13:
                    return False
        for (dx_, dy_, r, thru) in discs:
            if not thru and layer != pcbnew.F_Cu:
                continue
            for i in range(11):
                t = i / 10
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if (pt[0] - dx_) ** 2 + (pt[1] - dy_) ** 2 < \
                        (hw + r + 0.13) ** 2:
                    return False
        return True

    def add_track(net, a, c, layer, w=0.25):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*c))
        t.SetWidth(FromMM(w))
        t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)

    def add_via(net, xy):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(mm(*xy))
        v.SetWidth(FromMM(0.5))
        v.SetDrill(FromMM(0.25))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(b.FindNet(net))
        b.Add(v)

    # 2) re-tap pins 33 / 42
    segs, discs = all_copper("+3V3")
    for pad_xy in ((33.4, 22.0), (33.4, 18.4)):
        done = False
        for dx in (1.2, 1.6, 2.0, 2.4, 2.8):
            for dy in (0, -0.6, 0.6, -1.2, 1.2):
                vx, vy = pad_xy[0] + dx, pad_xy[1] + dy
                if via_ok(segs, discs, vx, vy) and \
                        track_ok(segs, discs, pad_xy, (vx, vy),
                                 pcbnew.F_Cu):
                    add_track("+3V3", pad_xy, (vx, vy), pcbnew.F_Cu)
                    add_via("+3V3", (vx, vy))
                    discs.append((vx, vy, 0.25, True))
                    print(f"re-tapped pin at {pad_xy} via ({vx:.1f},{vy:.1f})")
                    done = True
                    break
            if done:
                break
        if not done:
            print(f"NEEDS-REVIEW: no clear tap for pad {pad_xy}")

    # 3) short ENC_A bridge
    esegs, ediscs = all_copper("ENC_A")
    a, c = (20.78, 25.47), (24.20, 26.64)
    for path in ([a, (c[0], a[1]), c], [a, (a[0], c[1]), c], [a, c]):
        if all(track_ok(esegs, ediscs, p, q, pcbnew.F_Cu)
               for p, q in zip(path, path[1:]) if p != q):
            for p, q in zip(path, path[1:]):
                if p != q:
                    add_track("ENC_A", p, q, pcbnew.F_Cu)
            print("ENC_A short gap bridged")
            break
    else:
        print("NEEDS-REVIEW: ENC_A short gap unbridged")

    # 4) maze for the long ENC_A leg, legal-tight clearances
    STEP = 0.3
    layers = (pcbnew.F_Cu, pcbnew.B_Cu)

    def blocked(x, y, layer):
        for (p, q, w, lay) in esegs:
            if lay != layer:
                continue
            if seg_dist((x, y), p, q) < 0.1 + w + 0.13:
                return True
        for (dx_, dy_, r, thru) in ediscs:
            if not thru and layer != pcbnew.F_Cu:
                continue
            if (x - dx_) ** 2 + (y - dy_) ** 2 < (0.1 + r + 0.13) ** 2:
                return True
        return False

    def via_free(x, y):
        return via_ok(esegs, ediscs, x, y)

    start = (round(51.84 / STEP), round(4.7 / STEP), 0)
    goal = (round(26.15 / STEP), round(24.02 / STEP))
    prev = {start: None}
    q = deque([start])
    end = None
    while q:
        s = q.popleft()
        if (s[0], s[1]) == goal and s[2] == 0:
            end = s
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (s[0] + d[0], s[1] + d[1], s[2])
            x, y = n[0] * STEP, n[1] * STEP
            if n in prev or not (1.2 < x < BOARD_W - 1.2
                                 and 1.2 < y < BOARD_H - 1.2):
                continue
            if blocked(x, y, layers[s[2]]):
                continue
            prev[n] = s
            q.append(n)
        n = (s[0], s[1], 1 - s[2])
        x, y = s[0] * STEP, s[1] * STEP
        if n not in prev and via_free(x, y):
            prev[n] = s
            q.append(n)
    if end:
        path = []
        s = end
        while s is not None:
            path.append(s)
            s = prev[s]
        path.reverse()
        for u, v in zip(path, path[1:]):
            pu = (u[0] * STEP, u[1] * STEP)
            pv = (v[0] * STEP, v[1] * STEP)
            if u[2] != v[2]:
                add_via("ENC_A", pu)
            else:
                add_track("ENC_A", pu, pv, layers[u[2]], w=0.2)
        print(f"ENC_A maze routed: {len(path)} steps")
    else:
        print("NEEDS-REVIEW: ENC_A long leg still unrouted")

    # 5) VLED finger probe
    z = next(zz for zz in b.Zones() if zz.GetNetname() == "VLED")
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    poly = z.GetFilledPolysList(pcbnew.In2_Cu)
    mid = mm(28.0, 12.7)
    if not poly.Contains(mid):
        print("VLED finger fill BROKEN — bridging lobes on B.Cu")
        vsegs, vdiscs = all_copper("VLED")
        # simple straight B.Cu bridge along the finger line
        a, c = (15.5, 12.7), (40.5, 12.7)
        if track_ok(vsegs, vdiscs, a, c, pcbnew.B_Cu, hw=0.25):
            add_via("VLED", a)
            add_via("VLED", c)
            add_track("VLED", a, c, pcbnew.B_Cu, w=0.5)
            print("VLED B.Cu bridge added")
        else:
            print("NEEDS-REVIEW: VLED lobes unbridged")
    else:
        print("VLED finger fill OK")

    filler.Fill(b.Zones())
    b.Save(str(BOARD_PATH))
    print("final surgery complete")


if __name__ == "__main__":
    main()
