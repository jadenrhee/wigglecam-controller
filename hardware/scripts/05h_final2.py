"""Round 2 of final surgery with corrected clearance modeling:
- pad discs use rect-corner (hypot) radii;
- NPTH/through items get the 0.254 hole-clearance rule + slack;
- track-track margin 0.16 (> netclass 0.15).
Redoes the ENC_A maze (deleting the previous attempt), re-taps the
two east-side caps, closes the ENC_A short gap (F.Cu or B.Cu hop),
and re-verifies the VLED west lobe."""

import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

TRK_M = 0.16
HOLE_M = 0.30


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

    # 1) remove the previous maze attempt (0.2 mm ENC_A tracks + vias)
    n = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() != "ENC_A":
            continue
        if t.GetClass() == "PCB_VIA":
            b.Delete(t)
            n += 1
        elif abs(pcbnew.ToMM(t.GetWidth()) - 0.2) < 0.01:
            b.Delete(t)
            n += 1
    print(f"removed {n} previous maze items")

    def all_copper(skip_net):
        segs, discs = [], []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == skip_net:
                    continue
                x, y = to_local(p.GetPosition())
                hx = pcbnew.ToMM(p.GetSize().x) / 2
                hy = pcbnew.ToMM(p.GetSize().y) / 2
                r = (hx * hx + hy * hy) ** 0.5
                discs.append((x, y, r,
                              p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD))
        for t in b.GetTracks():
            if t.GetNetname() == skip_net:
                continue
            if t.GetClass() == "PCB_VIA":
                x, y = to_local(t.GetPosition())
                discs.append((x, y, pcbnew.ToMM(t.GetWidth()) / 2, True))
            else:
                segs.append((to_local(t.GetStart()),
                             to_local(t.GetEnd()),
                             pcbnew.ToMM(t.GetWidth()) / 2, t.GetLayer()))
        return segs, discs

    def track_ok(segs, discs, a, c, layer, hw):
        for (p, q, w, lay) in segs:
            if lay != layer:
                continue
            for i in range(13):
                t = i / 12
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if seg_dist(pt, p, q) < hw + w + TRK_M:
                    return False
        for (dx_, dy_, r, thru) in discs:
            if not thru and layer != pcbnew.F_Cu:
                continue
            m = HOLE_M if thru else TRK_M
            for i in range(13):
                t = i / 12
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if (pt[0] - dx_) ** 2 + (pt[1] - dy_) ** 2 < \
                        (hw + r + m) ** 2:
                    return False
        return True

    def via_ok(segs, discs, x, y):
        for (p, q, w, lay) in segs:
            if seg_dist((x, y), p, q) < 0.25 + w + TRK_M:
                return False
        for (dx_, dy_, r, thru) in discs:
            m = HOLE_M if thru else TRK_M
            if (x - dx_) ** 2 + (y - dy_) ** 2 < (0.25 + r + m) ** 2:
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

    # 2) re-tap the two east-side caps (their pads at x=34.35)
    segs3, discs3 = all_copper("+3V3")
    for pad_xy in ((34.35, 21.15), (34.35, 22.85),
                   (34.35, 17.55), (34.35, 19.25), (35.2, 13.6)):
        # try candidates around each possible cap-pad location
        done = False
        for dx in (0.9, 1.3, 1.7, -0.9, -1.3):
            for dy in (0, -0.7, 0.7, -1.4, 1.4):
                vx, vy = pad_xy[0] + dx, pad_xy[1] + dy
                if via_ok(segs3, discs3, vx, vy) and \
                        track_ok(segs3, discs3, pad_xy, (vx, vy),
                                 pcbnew.F_Cu, 0.125):
                    add_track("+3V3", pad_xy, (vx, vy), pcbnew.F_Cu)
                    add_via("+3V3", (vx, vy))
                    discs3.append((vx, vy, 0.25, True))
                    print(f"tap ({pad_xy[0]:.1f},{pad_xy[1]:.1f}) via "
                          f"({vx:.1f},{vy:.1f})")
                    done = True
                    break
            if done:
                break
        if not done:
            print(f"no tap for ({pad_xy[0]:.1f},{pad_xy[1]:.1f})")

    # 3) ENC_A short gap: F.Cu Ls, then B.Cu via-hop
    esegs, ediscs = all_copper("ENC_A")
    a, c = (20.78, 25.47), (24.20, 26.64)
    closed = False
    for path in ([a, (c[0], a[1]), c], [a, (a[0], c[1]), c], [a, c]):
        if all(track_ok(esegs, ediscs, p, q, pcbnew.F_Cu, 0.125)
               for p, q in zip(path, path[1:]) if p != q):
            for p, q in zip(path, path[1:]):
                if p != q:
                    add_track("ENC_A", p, q, pcbnew.F_Cu)
            closed = True
            print("ENC_A short gap: F.Cu bridge")
            break
    if not closed and via_ok(esegs, ediscs, *a) and \
            via_ok(esegs, ediscs, *c) and \
            track_ok(esegs, ediscs, a, c, pcbnew.B_Cu, 0.125):
        add_via("ENC_A", a)
        add_via("ENC_A", c)
        add_track("ENC_A", a, c, pcbnew.B_Cu)
        closed = True
        print("ENC_A short gap: B.Cu hop")
    if not closed:
        print("NEEDS-REVIEW: ENC_A short gap")

    # 4) maze for the long leg with the corrected model
    esegs, ediscs = all_copper("ENC_A")
    STEP = 0.3
    layers = (pcbnew.F_Cu, pcbnew.B_Cu)

    def blocked(x, y, layer):
        for (p, q, w, lay) in esegs:
            if lay != layer:
                continue
            if seg_dist((x, y), p, q) < 0.1 + w + TRK_M:
                return True
        for (dx_, dy_, r, thru) in ediscs:
            if not thru and layer != pcbnew.F_Cu:
                continue
            m = HOLE_M if thru else TRK_M
            if (x - dx_) ** 2 + (y - dy_) ** 2 < (0.1 + r + m) ** 2:
                return True
        return False

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
            nn = (s[0] + d[0], s[1] + d[1], s[2])
            x, y = nn[0] * STEP, nn[1] * STEP
            if nn in prev or not (1.4 < x < BOARD_W - 1.4
                                  and 1.4 < y < BOARD_H - 1.4):
                continue
            if blocked(x, y, layers[s[2]]):
                continue
            prev[nn] = s
            q.append(nn)
        nn = (s[0], s[1], 1 - s[2])
        x, y = s[0] * STEP, s[1] * STEP
        if nn not in prev and via_ok(esegs, ediscs, x, y):
            prev[nn] = s
            q.append(nn)
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
        print("NEEDS-REVIEW: ENC_A long leg unrouted")

    # 5) VLED west lobe verification
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    z = next(zz for zz in b.Zones() if zz.GetNetname() == "VLED")
    poly = z.GetFilledPolysList(pcbnew.In2_Cu)
    probe = mm(13.44, 10.05)
    if not poly.Contains(probe):
        print("NEEDS-REVIEW: Q1.S via not inside VLED fill")
    else:
        print("VLED west lobe OK at Q1.S via")

    b.Save(str(BOARD_PATH))
    print("surgery round 2 complete")


if __name__ == "__main__":
    main()
