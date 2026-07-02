"""Redo the last two closes collision-aware:
- VLED finger repair as three short B.Cu patches, each endpoint on
  verified In2 fill and each segment/via checked against all copper;
- ENC_A tap of C32 with a scanned via spot + checked link."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, FromMM, mm, to_local


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
    # remove yesterday's blind span + diag
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA":
            p = to_local(t.GetPosition())
            if t.GetNetname() == "VLED" and abs(p[1] - 12.7) < 0.05 \
                    and (abs(p[0] - 22.0) < 0.05 or abs(p[0] - 44.0) < 0.05):
                b.Delete(t)
                n += 1
            elif t.GetNetname() == "ENC_A" and abs(p[0] - 16.5) < 0.05 \
                    and abs(p[1] - 19.65) < 0.05:
                b.Delete(t)
                n += 1
        elif t.GetClass() == "PCB_TRACK":
            a, c = to_local(t.GetStart()), to_local(t.GetEnd())
            if t.GetNetname() == "VLED" and t.GetLayer() == pcbnew.B_Cu \
                    and abs(a[1] - 12.7) < 0.05 and abs(c[1] - 12.7) < 0.05 \
                    and abs(abs(a[0] - c[0]) - 22.0) < 0.1:
                b.Delete(t)
                n += 1
            elif t.GetNetname() == "ENC_A" and (
                    (round(a[0], 1), round(a[1], 2)) == (16.5, 19.65)
                    or (round(c[0], 1), round(c[1], 2)) == (16.5, 19.65)):
                b.Delete(t)
                n += 1
    print(f"removed {n} blind items")

    def all_copper(skip_net):
        segs, discs = [], []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == skip_net:
                    continue
                x, y = to_local(p.GetPosition())
                hx = pcbnew.ToMM(p.GetSize().x) / 2
                hy = pcbnew.ToMM(p.GetSize().y) / 2
                discs.append((x, y, (hx * hx + hy * hy) ** 0.5,
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

    def track_ok(segs, discs, a, c, layer, hw=0.25):
        for (p, q, w, lay) in segs:
            if lay != layer:
                continue
            for i in range(15):
                t = i / 14
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if seg_dist(pt, p, q) < hw + w + 0.16:
                    return False
        for (dx_, dy_, r, thru) in discs:
            if not thru and layer != pcbnew.F_Cu:
                continue
            m = 0.30 if thru else 0.16
            for i in range(15):
                t = i / 14
                pt = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
                if (pt[0] - dx_) ** 2 + (pt[1] - dy_) ** 2 < \
                        (hw + r + m) ** 2:
                    return False
        return True

    def via_ok(segs, discs, x, y):
        for (p, q, w, lay) in segs:
            if seg_dist((x, y), p, q) < 0.25 + w + 0.16:
                return False
        for (dx_, dy_, r, thru) in discs:
            m = 0.30 if thru else 0.16
            if (x - dx_) ** 2 + (y - dy_) ** 2 < (0.25 + r + m) ** 2:
                return False
        return True

    def trk(net, a, c, layer, w=0.5):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*c))
        t.SetWidth(FromMM(w))
        t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)

    def via(net, xy):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(mm(*xy))
        v.SetWidth(FromMM(0.5))
        v.SetDrill(FromMM(0.25))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(b.FindNet(net))
        b.Add(v)

    # VLED patches over the three finger cuts
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    z = next(zz for zz in b.Zones() if zz.GetNetname() == "VLED")
    poly = z.GetFilledPolysList(pcbnew.In2_Cu)
    vsegs, vdiscs = all_copper("VLED")
    for x0, x1 in ((29.5, 34.5), (35.5, 40.3), (39.5, 44.5)):
        done = False
        for y in (12.7, 12.4, 13.0, 12.1, 13.3):
            for xa in (x0, x0 + 0.5, x0 - 0.5):
                for xb in (x1, x1 - 0.5, x1 + 0.5):
                    if not (poly.Contains(mm(xa, y)) and
                            poly.Contains(mm(xb, y))):
                        continue
                    if via_ok(vsegs, vdiscs, xa, y) and \
                            via_ok(vsegs, vdiscs, xb, y) and \
                            track_ok(vsegs, vdiscs, (xa, y), (xb, y),
                                     pcbnew.B_Cu):
                        via("VLED", (xa, y))
                        via("VLED", (xb, y))
                        trk("VLED", (xa, y), (xb, y), pcbnew.B_Cu)
                        vdiscs += [(xa, y, 0.25, True),
                                   (xb, y, 0.25, True)]
                        vsegs.append(((xa, y), (xb, y), 0.25,
                                      pcbnew.B_Cu))
                        print(f"VLED patch ({xa},{y})->({xb},{y})")
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            print(f"NEEDS-REVIEW: VLED cut near x={x0}-{x1} unpatched")

    # ENC_A tap of C32: via on the maze column + checked link
    esegs, ediscs = all_copper("ENC_A")
    done = False
    for vy in (19.65, 19.2, 18.75, 20.1, 23.4, 23.85):
        if not via_ok(esegs, ediscs, 16.5, vy):
            continue
        if track_ok(esegs, ediscs, (16.5, vy), (15.1, 21.01),
                    pcbnew.F_Cu, hw=0.125):
            via("ENC_A", (16.5, vy))
            trk("ENC_A", (16.5, vy), (15.1, 21.01), pcbnew.F_Cu, w=0.25)
            print(f"ENC_A C32 tap via (16.5,{vy})")
            done = True
            break
    if not done:
        print("NEEDS-REVIEW: ENC_A C32 tap")

    filler.Fill(b.Zones())
    b.Save(str(BOARD_PATH))
    print("done")


if __name__ == "__main__":
    main()
