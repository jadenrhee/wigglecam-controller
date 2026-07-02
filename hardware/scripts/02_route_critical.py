"""Pre-route the sensitive nets before the autorouter sees the board.

Scripted here (docs/plan.md phase 3), never left to Freerouting:
- RP2040 exposed pad: 3x3 GND thermal-via array (guide: >=9 vias);
- QSPI bundle as nested lanes, crossing-free by construction: the
  three far-side flash pins take the three leftmost U2 pins around the
  flash's left edge (deepest lane pairs with the westmost drop, so no
  vertical ever pierces another lane); near-side pins approach from
  the right at successively shallower lanes; SCLK's 27R is inline;
- crystal XIN/XOUT, short, over the In1 GND plane;
- USB differential pair: connector A/B mirror pads let us exit DP and
  DM on matching west/east sides regardless of connector orientation,
  so the pair runs straight north with the 27.4R inline;
- power entry and LED returns in heavy copper; VLED as In2 island;
- zones: In1 solid GND, In2 3V3 fill + VLED island.

All endpoints are looked up by PAD NET, never by assumed geometry —
pad-1-north assumptions already caused one round of shorts.

Decoupling stubs and 3V3 fanout vias run post-autoroute (04), where
they can be placed collision-aware. Idempotent (clears its nets).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH, BOARD_H, BOARD_W, FromMM, mm, to_local

# VLED In2 island: west entry lobe + 1 mm conduit finger + reservoir
# pocket + east lobe + right strip + left column. Drawn tightly so
# the flash / QSPI / C11 areas keep a true 3V3 plane beneath them.
VLED_ISLAND = [
    (6, 1.5), (15, 1.5), (15, 12.2), (41, 12.2), (41, 1.5),
    (74.5, 1.5), (74.5, 38), (69, 38), (69, 10), (50, 10),
    (50, 19.5), (41, 19.5), (41, 13.2), (15, 13.2), (15, 13),
    (11, 13), (11, 24), (6, 24),
]

W_QSPI = 0.15
W_USB = 0.36
W_SIG = 0.2
W_PWR = 0.8
W_FLASH = 1.5


def get(board, ref):
    # NOT FindFootprintByReference: its SWIG wrapper intermittently
    # returns a dead object on boards with zones; iteration is stable
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    raise KeyError(ref)


def pad_of(fp, num):
    for p in fp.Pads():
        if p.GetNumber() == str(num):
            return p
    raise KeyError(f"{fp.GetReference()}:{num}")


def pad_by_net(fp, netname):
    hits = [p for p in fp.Pads() if p.GetNetname() == netname]
    assert hits, f"{fp.GetReference()} has no pad on {netname}"
    return hits[0]


def fp_by_netpair(board, prefix, *netnames):
    want = set(netnames)
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith(prefix):
            continue
        nets = {p.GetNetname() for p in fp.Pads()}
        if nets == want:
            return fp
    raise KeyError(f"no {prefix}* with nets {want}")


def ppos(fp, num):
    return to_local(pad_of(fp, num).GetPosition())


def npos(fp, netname):
    return to_local(pad_by_net(fp, netname).GetPosition())


def add_track(board, netname, pts, width, layer=None):
    ni = board.FindNet(netname)
    assert ni, netname
    layer = layer if layer is not None else pcbnew.F_Cu
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(mm(*a))
        t.SetEnd(mm(*b))
        t.SetWidth(FromMM(width))
        t.SetLayer(layer)
        t.SetNet(ni)
        board.Add(t)


_via_spots = set()


def add_via(board, netname, xy, size=0.6, drill=0.3):
    key = (round(xy[0], 2), round(xy[1], 2))
    if key in _via_spots:
        return          # coincident duplicate (e.g. stacked A1/B12
    _via_spots.add(key)  # connector pads) — one via serves both
    ni = board.FindNet(netname)
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(mm(*xy))
    v.SetWidth(FromMM(size))
    v.SetDrill(FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(ni)
    board.Add(v)


OWNED_NETS = None


def clear_owned(board):
    # board.Delete (remove + destroy), NOT board.Remove: removing
    # hundreds of tracks without destroying them leaks PCB_TRACK
    # wrappers and corrupts the SWIG type table mid-process
    for t in list(board.GetTracks()):
        if t.GetNetname() in OWNED_NETS:
            board.Delete(t)
    for z in list(board.Zones()):
        board.Delete(z)


# ---------------------------------------------------------------- blocks --
def ep_vias(board):
    u2 = get(board, "U2")
    cx, cy = to_local(u2.GetPosition())
    for ix in (-1, 0, 1):
        for iy in (-1, 0, 1):
            add_via(board, "GND", (cx + ix * 1.0, cy + iy * 1.0))
    # TESTEN (pad 19, bottom row, GND) ties straight north into the
    # exposed pad — the stub finder can't reach it in QFN density
    t = ppos(u2, "19")
    add_track(board, "GND", [t, (t[0], cy + 1.55)], 0.25)


def qspi(board):
    u2, u3 = get(board, "U2"), get(board, "U3")
    r2 = fp_by_netpair(board, "R", "QSPI_SCLK", "QSPI_SCLK_FL")
    r3 = fp_by_netpair(board, "R", "QSPI_SS", "+3V3")
    ux, uy = to_local(u2.GetPosition())
    fx, fy = to_local(u3.GetPosition())
    assert abs(ux - 30.0) < 0.01 and abs(uy - 21.0) < 0.01, (ux, uy)
    assert abs(fx - 20.7) < 0.01 and abs(fy - 12.2) < 0.01, (fx, fy)

    def route(net, u2pad, u3pad, lane_y, drop_x):
        a = ppos(u2, u2pad)
        b = ppos(u3, u3pad)
        add_track(board, net,
                  [a, (a[0], lane_y), (drop_x, lane_y), (drop_x, b[1]), b],
                  W_QSPI)

    # far-side flash pins: deepest lane takes the westmost drop, so no
    # vertical crosses another's lane, and pad-entry rows nest north.
    # Lanes sit south of the flash pads (bottom pad edge ~13.9).
    route("QSPI_SS",  "56", "1", 15.5, 14.9)
    route("QSPI_SD1", "55", "2", 15.1, 15.5)
    route("QSPI_SD2", "54", "3", 14.7, 16.05)
    # near-side pins from the right, above the far lanes
    route("QSPI_SD0", "53", "5", 14.3, 25.7)
    # SCLK: lane at y13.4 (shallowest full lane — its escape x29.0 is
    # east of every other lane's end), into the series R lying flat at
    # the flash end (east pad = SCLK via fixup), then a short hop from
    # the west pad into flash pin 6.
    a = ppos(u2, "52")
    r2_in = to_local(pad_by_net(r2, "QSPI_SCLK").GetPosition())
    r2_out = to_local(pad_by_net(r2, "QSPI_SCLK_FL").GetPosition())
    assert r2_in[0] > r2_out[0], "R2 SCLK pad must be east"
    add_track(board, "QSPI_SCLK",
              [a, (a[0], 13.9), (r2_in[0], 13.9), r2_in], W_QSPI)
    b = ppos(u3, "6")
    add_track(board, "QSPI_SCLK_FL",
              [r2_out, (r2_out[0], b[1]), b], W_QSPI)
    # SD3 over the top of the near-side verticals; its drop sits at
    # x28.35, clear of the SCLK resistor's east pad (extends to 28.05)
    a = ppos(u2, "51")
    b = ppos(u3, "7")
    add_track(board, "QSPI_SD3",
              [a, (a[0], 13.3), (28.5, 13.3), (28.5, b[1]), b], W_QSPI)
    # CS pullup ties into the SS drop with a short same-net hop
    r3p = to_local(pad_by_net(r3, "QSPI_SS").GetPosition())
    add_track(board, "QSPI_SS", [r3p, (14.9, r3p[1])], W_QSPI)


def crystal(board):
    """The 3225 crystal's active pads are DIAGONAL (XIN south-east,
    XOUT_XTAL north-west, at Y1 rot90 with these nets). XIN comes down
    the crystal's east flank; XOUT_XTAL sweeps south around the body
    and enters the north-west pad from the west. Geometry asserted."""
    u2, y1 = get(board, "U2"), get(board, "Y1")
    r1 = fp_by_netpair(board, "R", "XOUT", "XOUT_XTAL")
    xin_mcu, xout_mcu = ppos(u2, "20"), ppos(u2, "21")
    p_xin = npos(y1, "XIN")
    p_xtl = npos(y1, "XOUT_XTAL")
    r1_a = to_local(pad_by_net(r1, "XOUT").GetPosition())
    r1_b = to_local(pad_by_net(r1, "XOUT_XTAL").GetPosition())
    assert p_xin[0] > p_xtl[0] and p_xin[1] > p_xtl[1], \
        "crystal pad diagonal changed — re-derive crystal()"

    # XOUT: short hop east into the series R (whichever pad is XOUT)
    add_track(board, "XOUT", [xout_mcu, (xout_mcu[0], r1_a[1]),
                              r1_a], W_SIG)
    # XIN down the east flank
    bypass_x = p_xin[0] + 1.1
    add_track(board, "XIN", [xin_mcu, (xin_mcu[0], 25.2),
                             (bypass_x, 25.2), (bypass_x, p_xin[1]),
                             p_xin], W_SIG)
    # XOUT_XTAL: south sweep around the crystal, west entry
    wx = p_xtl[0] - 1.25
    add_track(board, "XOUT_XTAL",
              [r1_b, (r1_b[0], 31.6), (wx, 31.6), (wx, p_xtl[1]),
               p_xtl], W_SIG)
    # load caps: tie each cap's signal pad to its crystal pad. If the
    # cap sits south of the XOUT_XTAL sweep (y31.6), a direct tie
    # would cross it — detour under on B.Cu instead, tapping the XIN
    # bypass vertical from below.
    for capnet, target in (("XIN", p_xin), ("XOUT_XTAL", p_xtl)):
        for fp in board.GetFootprints():
            if not fp.GetReference().startswith("C"):
                continue
            for p in fp.Pads():
                if p.GetNetname() != capnet:
                    continue
                cp = to_local(p.GetPosition())
                if capnet == "XIN" and cp[1] > 31.0:
                    add_via(board, "XIN", cp, size=0.5, drill=0.25)
                    add_track(board, "XIN",
                              [cp, (cp[0], 29.2), (bypass_x, 29.2)],
                              W_SIG, pcbnew.B_Cu)
                    add_via(board, "XIN", (bypass_x, 29.2), size=0.5,
                            drill=0.25)
                else:
                    add_track(board, capnet, [cp, target], W_SIG)


def usb(board):
    """Pair runs straight north; the connector's mirrored A/B pads let
    DP exit on the west and DM on the east for either orientation."""
    u2, u4, j2 = get(board, "U2"), get(board, "U4"), get(board, "J2")
    r_dp = fp_by_netpair(board, "R", "USB_DP_ESD", "USB_DP")
    r_dm = fp_by_netpair(board, "R", "USB_DM_ESD", "USB_DM")

    dp_pads = sorted((to_local(p.GetPosition()) for p in j2.Pads()
                      if p.GetNetname() == "USB_DP_CONN"))
    dm_pads = sorted((to_local(p.GetPosition()) for p in j2.Pads()
                      if p.GetNetname() == "USB_DM_CONN"))
    assert len(dp_pads) == 2 and len(dm_pads) == 2
    row_y = dp_pads[0][1]
    p1, p3 = npos(u4, "USB_DP_CONN"), npos(u4, "USB_DM_CONN")
    assert p1[0] < p3[0], "U4 line-side pins must be west(DP)/east(DM)"
    # The 16-pin connector interleaves the pairs (…B7 A6 A7 B6…) at
    # 0.5 mm pitch, so an F.Cu jumper for one pair always blocks the
    # other's exit. Instead: each net's "main" pad (the one nearer its
    # U4 pin x) exits straight north; the mirror pad runs north too
    # and crosses over on B.Cu between two vias placed above the pad
    # field, the inner via tapping the main exit column directly.
    def pair(pads, target_x, jumper_y):
        main = min(pads, key=lambda p: abs(p[0] - target_x))
        other = pads[0] if main is pads[1] else pads[1]
        return main, other, jumper_y

    # Mirror-pad jumpers: the four pads' stubs fan SOUTH-OUTWARD
    # (under the shell, between the two NPTH posts) to spread-out via
    # taps at two staggered depths; each pair then bridges on B.Cu.
    # The north side stays completely clean for the pair exits.
    dp_main, dp_other, _ = pair(dp_pads, p1[0], 0)
    dm_main, dm_other, _ = pair(dm_pads, p3[0], 0)
    all4 = sorted([("USB_DP_CONN", dp_main), ("USB_DP_CONN", dp_other),
                   ("USB_DM_CONN", dm_main), ("USB_DM_CONN", dm_other)],
                  key=lambda kv: kv[1][0])
    spread = [-0.9, -0.2, 0.4, 1.6]
    taps = {}
    for (net, pad), dx in zip(all4, spread):
        depth = 2.45 if net == "USB_DP_CONN" else 1.75
        kink = 0.75 if net == "USB_DP_CONN" else 1.15
        tap = (pad[0] + dx, row_y + depth)
        # straight down past the pad field first (pads end +0.73), THEN
        # diagonal — kink depths staggered per net so adjacent-column
        # kink corners keep >=0.3 mm between the two nets
        add_track(board, net, [pad, (pad[0], row_y + kink), tap], 0.3)
        add_via(board, net, tap, size=0.5, drill=0.25)
        taps.setdefault(net, []).append(tap)
    for net, tps in taps.items():
        add_track(board, net, [tps[0], tps[1]], 0.3, pcbnew.B_Cu)

    # main exits north (0.3 mm through the 0.5 mm-pitch field, then
    # full pair width after the fan), into the ESD pins
    for net, main, px in (("USB_DP_CONN", dp_main, p1[0]),
                          ("USB_DM_CONN", dm_main, p3[0])):
        # keep 0.3 mm through the fan (columns only 0.5 mm apart);
        # full pair width resumes once the pair is at 1.9 mm spacing
        add_track(board, net, [main, (main[0], row_y - 3.0),
                               (px, row_y - 3.9), (px, row_y - 4.0)], 0.3)
        tgt = p1 if net == "USB_DP_CONN" else p3
        add_track(board, net, [(px, row_y - 4.0), tgt], W_USB)

    # ESD out -> inline R -> U2. DP (west pin 47) takes the SOUTH lane
    # y16.15; DM (east pin 46) the NORTH lane y15.55 — DM's lane may
    # cross DP's resistor column only at y15.55, above DP's vertical
    # (which starts at 16.15). At the MCU end DM must cross DP's lane:
    # it does so on B.Cu between two 0.5 mm vias, then necks into its
    # pad. Necks are 0.25 mm for the last stretch into the 0.4 mm QFN
    # pitch (USB-FS tolerant; noted in the verification report).
    for esd_net, mcu_net, rfp, u2pad, lane_y in (
            ("USB_DP_ESD", "USB_DP", r_dp, "47", 16.15),
            ("USB_DM_ESD", "USB_DM", r_dm, "46", 15.55)):
        po = npos(u4, esd_net)
        ra = to_local(pad_by_net(rfp, esd_net).GetPosition())
        rb = to_local(pad_by_net(rfp, mcu_net).GetPosition())
        add_track(board, esd_net, [po, (ra[0], po[1] - 0.8), ra], W_USB)
        mcu = ppos(u2, u2pad)
        if mcu_net == "USB_DP":
            add_track(board, mcu_net,
                      [rb, (rb[0], lane_y), (mcu[0], lane_y)], W_USB)
            add_track(board, mcu_net, [(mcu[0], lane_y), mcu], 0.25)
        else:
            # DM must cross DP's lane once: do it mid-corridor at
            # x=34 on B.Cu, where both vias clear the DP lane and the
            # QFN pad row by >=0.17 mm; then approach pad 46 from the
            # south-east at y16.75 (below DP's lane) and neck in.
            add_track(board, mcu_net,
                      [rb, (rb[0], lane_y), (34.0, lane_y)], W_USB)
            add_via(board, mcu_net, (34.0, lane_y), size=0.5, drill=0.25)
            add_track(board, mcu_net,
                      [(34.0, lane_y), (34.0, 16.75)], 0.3, pcbnew.B_Cu)
            add_via(board, mcu_net, (34.0, 16.75), size=0.5, drill=0.25)
            add_track(board, mcu_net,
                      [(34.0, 16.75), (mcu[0], 16.75)], 0.25)
            add_track(board, mcu_net, [(mcu[0], 16.75), mcu], 0.25)


def power_entry(board):
    """J8 5V pins exit SOUTH into the band between the header's THT
    field and the flash pads (y=7.9), run west to the fuse (RAW pad
    forced north by the placement fixup), then a short south-side hop
    into the FET drain. Every pad resolved by net. The 5V path only
    sees the 2 A flash pulse for 150 ms — comfortably inside 0.8 mm
    copper transient capability (steady draw is <0.5 A)."""
    j8, q1 = get(board, "J8"), get(board, "Q1")
    f1 = get(board, "F1")
    p2, p4 = ppos(j8, "2"), ppos(j8, "4")
    fin = npos(f1, "PI5V_RAW")       # north pad (fixed up in placement)
    fout = npos(f1, "PI5V_FUSED")    # south pad
    assert fin[1] < fout[1], "F1 orientation fixup missing"
    # 0.5 mm lane in the 0.9 mm band between the header's THT pads
    # (edge y8.39) and the flash pads (edge y9.27). Carries ~0.5 A
    # steady; the 2.3 A flash pulse is a 150 ms transient — far below
    # IPC-2221 transient capability for 0.5 mm (see power budget).
    lane = 8.84
    w = 0.5
    add_track(board, "PI5V_RAW", [p4, (p4[0], lane), (p2[0], lane)], w)
    # west of the header: the fuse pads are 3.4 mm WIDE after the -90
    # rotation (they span x4.8..8.2), so the lane stops at x9.0 and
    # the drop runs down that column, entering the RAW pad from the
    # east at its own row.
    bx = fout[0] + 2.6      # east of the 3.4 mm-wide rotated fuse pads
    add_track(board, "PI5V_RAW",
              [p2, (p2[0], lane), (bx, lane), (bx, fin[1]), fin], w)
    qd = npos(q1, "PI5V_FUSED")      # FET drain (west-facing at rot180)
    # straight south out of the fuse pad, then east into the drain —
    # stays south of the RAW lane the whole way
    add_track(board, "PI5V_FUSED",
              [fout, (fout[0], qd[1]), qd], W_PWR)


def _obstacles(board, skip_nets):
    """(x0,y0,x1,y1) boxes of every pad not on skip_nets, plus every
    existing track segment, for collision-aware stub placement."""
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


def vled_drops(board):
    """Wide stub + twin vias from every VLED pad into the In2 island,
    direction chosen collision-aware against all other copper."""
    boxes = _obstacles(board, {"VLED"})
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "VLED":
                continue
            x, y = to_local(p.GetPosition())
            placedone = False
            for dx, dy in ((1.3, 0), (-1.3, 0), (0, 1.3), (0, -1.3),
                           (1.8, 0), (-1.8, 0)):
                if x + dx > BOARD_W - 2.0 or x + dx < 2.0:
                    continue
                vx, vy = x + dx, y + dy
                v2 = (vx + (0.9 if dy == 0 else 0),
                      vy + (0.9 if dx == 0 else 0))
                span = (min(x, vx, v2[0]) - 0.6, min(y, vy, v2[1]) - 0.6,
                        max(x, vx, v2[0]) + 0.6, max(y, vy, v2[1]) + 0.6)
                if _clear(boxes, *span):
                    add_track(board, "VLED", [(x, y), (vx, vy)], 1.2)
                    add_via(board, "VLED", (vx, vy), size=0.8, drill=0.4)
                    add_via(board, "VLED", v2, size=0.8, drill=0.4)
                    boxes.append(span)
                    placedone = True
                    break
            if not placedone:
                # fallback: single via, smaller keep-out, 8 directions
                for dx, dy in ((1.15, 0), (-1.15, 0), (0, 1.15),
                               (0, -1.15), (0.9, 0.9), (0.9, -0.9),
                               (-0.9, 0.9), (-0.9, -0.9)):
                    vx, vy = x + dx, y + dy
                    if not 2.0 < vx < BOARD_W - 2.0:
                        continue
                    span = (min(x, vx) - 0.55, min(y, vy) - 0.55,
                            max(x, vx) + 0.55, max(y, vy) + 0.55)
                    if _clear(boxes, *span):
                        add_track(board, "VLED", [(x, y), (vx, vy)], 0.9)
                        add_via(board, "VLED", (vx, vy), size=0.8,
                                drill=0.4)
                        boxes.append(span)
                        placedone = True
                        break
            if not placedone:
                # last resort: via-in-pad (fine for hand assembly;
                # flagged for the review checklist)
                add_via(board, "VLED", (x, y), size=0.5, drill=0.25)
                print(f"NEEDS-REVIEW: via-in-pad VLED tap at "
                      f"{fp.GetReference()} ({x:.1f},{y:.1f})")


def vbat(board):
    """Battery pass-through carries up to 5 A: JST -> 10 mΩ shunt ->
    JST in 1.5 mm copper (IPC-2221 external, 10 °C: ~3 A/mm → 1.5 mm
    ≈ 4.5 A steady; the 5 A case is transient camera peaks — noted in
    the verification report). INA219 sense taps ride the same nets."""
    j5, j6, r19 = get(board, "J5"), get(board, "J6"), get(board, "R19")
    jin = npos(j5, "VBAT_IN")
    jout = npos(j6, "VBAT_OUT")
    rin = to_local(pad_by_net(r19, "VBAT_IN").GetPosition())
    rout = to_local(pad_by_net(r19, "VBAT_OUT").GetPosition())
    add_track(board, "VBAT_IN", [jin, (rin[0], jin[1]), rin], 1.5)
    # L down the shunt's east column, then west along the JST pin's own
    # row (the connector's other pin sits 2.5 mm off-row, so this
    # cannot cross it); the column is corridor-reserved in placement
    add_track(board, "VBAT_OUT",
              [rout, (rout[0], jout[1]), jout], 1.5)


def led_returns(board):
    """JST return pin -> FET drain via a western bypass (x=jst-3.4)
    that clears the sense resistor's east pad; FET source -> sense R
    east pad (orientation fixed up in placement); sense GND pad gets
    vias placed SOUTH, clear of the return path."""
    for jref, qref, snet in (("J3", "Q2", "SENSE1"), ("J4", "Q3", "SENSE2")):
        j, q = get(board, jref), get(board, qref)
        r = fp_by_netpair(board, "R", snet, "GND")
        jp = ppos(j, "2")
        qd = ppos(q, "3")
        bx = jp[0] - 3.4
        add_track(board, pad_of(j, "2").GetNetname(),
                  [jp, (bx, jp[1]), (bx, qd[1]), qd], 1.0)
        qs = npos(q, snet)
        rs = to_local(pad_by_net(r, snet).GetPosition())
        rg = to_local(pad_by_net(r, "GND").GetPosition())
        add_track(board, snet, [qs, (qs[0], rs[1]), rs], 1.0)
        add_track(board, "GND", [rg, (rg[0], rg[1] + 1.6),
                                 (rg[0] + 0.9, rg[1] + 1.6)], 1.2)
        add_via(board, "GND", (rg[0], rg[1] + 1.6), size=0.8, drill=0.4)
        add_via(board, "GND", (rg[0] + 0.9, rg[1] + 1.6), size=0.8,
                drill=0.4)


def qfn_power_fanout(board):
    """U2's power pins that the corridors cut off from their caps get
    dedicated fanouts (0.25 mm) to 3V3 plane vias, using the free ring
    between the QFN pad row and the exposed pad — the standard escape
    when the periphery is congested. Coordinates assume U2 at (30,21).
    - pins 43 (ADC_AVDD) + 44 (VREG_VIN): east link at y16.9 (between
      the pad tips and the USB DM lane) to a via at (33.05, 17.05);
      pin 42 (IOVDD) joins via its own column;
    - pins 48 (USB_VDD) + 49 (IOVDD): interior link at y18.6 to a via
      at (28.0, 18.6);
    - pins 22 + 33 (IOVDD): interior link at y23.4 to (32.4, 23.4)."""
    u2 = get(board, "U2")
    p = {n: ppos(u2, n) for n in ("43", "44", "48", "49",
                                  "22", "33")}
    w = 0.25
    # north-east interior cluster (pins 43 ADC_AVDD + 44 VREG_VIN):
    # via sits on pin 43's own column (the channel between the EP and
    # the right-hand pad column is only 0.4 mm — unusable)
    for n in ("43", "44"):
        add_track(board, "+3V3", [p[n], (p[n][0], 18.6)], w)
    add_track(board, "+3V3", [(p["44"][0], 18.6), (p["43"][0], 18.6),
                              (p["43"][0], 18.9)], w)
    add_via(board, "+3V3", (p["43"][0], 18.9), size=0.5, drill=0.25)
    # north-west interior cluster (pins 48 USB_VDD + 49 IOVDD)
    for n in ("48", "49"):
        add_track(board, "+3V3", [p[n], (p[n][0], 18.6)], w)
    add_track(board, "+3V3", [(p["49"][0], 18.6), (28.0, 18.6)], w)
    add_via(board, "+3V3", (28.0, 18.6), size=0.5, drill=0.25)
    # pin 22 (IOVDD, bottom row): interior via in the south channel,
    # east of the TESTEN tie column
    add_track(board, "+3V3", [p["22"], (p["22"][0], 23.4),
                              (30.85, 23.35)], w)
    add_via(board, "+3V3", (30.9, 23.3), size=0.5, drill=0.25)
    # pin 33 connects through its explicitly-seeded east-side cap
    # (see 01_make_board's pin-33 seed override)


def pi_and_vreg_links(board):
    """Two legs the autorouter repeatedly fails in the congested NW:
    - PI_SDA: U2.4 -> B.Cu (through the x=21.0 corridor between the
      header barrels) -> J8.3;
    - VREG_1V1 pin 23 -> its west-side cap, under the crystal-hop wall
      on B.Cu."""
    u2, j8 = get(board, "U2"), get(board, "J8")
    p4 = ppos(u2, "4")
    j3p = ppos(j8, "3")
    add_track(board, "PI_SDA", [p4, (25.6, p4[1])], 0.25)
    add_via(board, "PI_SDA", (25.6, p4[1]), size=0.5, drill=0.25)
    add_track(board, "PI_SDA",
              [(25.6, p4[1]), (21.0, p4[1]), (21.0, 4.5),
               (j3p[0], 4.5), j3p], 0.25, pcbnew.B_Cu)

    p23 = ppos(u2, "23")
    cap = None
    best = 1e9
    for fp in board.GetFootprints():
        if fp.GetReference()[0] != "C":
            continue
        for p in fp.Pads():
            if p.GetNetname() == "VREG_1V1":
                c = to_local(p.GetPosition())
                d = (c[0]-p23[0])**2 + (c[1]-p23[1])**2
                if d < best:
                    best, cap = d, c
    assert cap, "no VREG cap found"
    add_track(board, "VREG_1V1", [p23, (p23[0], 25.6)], 0.25)
    add_via(board, "VREG_1V1", (p23[0], 25.6), size=0.5, drill=0.25)
    add_track(board, "VREG_1V1",
              [(p23[0], 25.6), (p23[0], 26.2), (24.9, 26.2),
               (24.9, cap[1])], 0.25, pcbnew.B_Cu)
    add_via(board, "VREG_1V1", (24.9, cap[1]), size=0.5, drill=0.25)
    add_track(board, "VREG_1V1", [(24.9, cap[1]), cap], 0.25)


def ic_power_hops(board):
    """Each IC power pin gets a direct short track to its adjacent
    decoupling cap's pad (same net): the caps carry the plane vias, so
    this closes pin -> cap -> via -> plane. Without it the pins dangle
    (+3V3 is excluded from autorouting)."""
    cpads = []
    for fp in board.GetFootprints():
        if fp.GetReference()[0] == "C":
            for p in fp.Pads():
                if p.GetNetname() == "+3V3":
                    cpads.append(to_local(p.GetPosition()))
    n = 0
    for fp in board.GetFootprints():
        if fp.GetReference()[0] not in "UY":
            continue
        for p in fp.Pads():
            if p.GetNetname() != "+3V3":
                continue
            x, y = to_local(p.GetPosition())
            best = min(cpads, key=lambda c: (c[0]-x)**2 + (c[1]-y)**2)
            # only truly adjacent caps (placement orients each cap's
            # 3V3 pad toward its pin). Exit PERPENDICULAR from the pad
            # row first so the diagonal never clips a neighboring pin.
            if (best[0]-x)**2 + (best[1]-y)**2 < 7.85:
                cx, cy = to_local(fp.GetPosition())
                if abs(x - cx) >= abs(y - cy):     # side-column pin
                    esc = (x + (1.0 if x > cx else -1.0), y)
                else:                              # row pin
                    esc = (x, y + (1.0 if y > cy else -1.0))
                add_track(board, "+3V3", [(x, y), esc, best], 0.25)
                n += 1
            else:
                print(f"  NEEDS-REVIEW: {fp.GetReference()} 3V3 pin at "
                      f"({x:.1f},{y:.1f}) has no cap within 2.8 mm")
    print(f"ic power hops: {n}")


def plane_stubs(board):
    """Every SMD pad on +3V3 / GND gets a stub + via to its plane
    BEFORE autorouting: the board is empty so spots are plentiful, and
    Freerouting then treats these vias as obstacles and never needs to
    route the plane nets at all (the professional plane-fanout flow)."""
    boxes_for = {net: _obstacles(board, {net}) for net in ("+3V3", "GND")}
    existing = {}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            existing.setdefault(t.GetNetname(), []).append(
                to_local(t.GetPosition()))
    stats = {}
    for fp in board.GetFootprints():
        if fp.GetReference() == "U2":
            continue   # EP vias + TESTEN tie + oriented cap hops serve
            # the QFN; a via ring here would choke autorouter escapes
        for p in fp.Pads():
            net = p.GetNetname()
            if net not in ("+3V3", "GND"):
                continue
            boxes = boxes_for[net]
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue   # THT pads reach the planes directly
            x, y = to_local(p.GetPosition())
            # only skip if a same-net via sits ON this pad (vias just
            # 0.8 mm away usually belong to a NEIGHBORING pad's stub
            # and have no copper path to this pad's island)
            if any((vx - x) ** 2 + (vy - y) ** 2 < 0.09
                   for vx, vy in existing.get(net, [])):
                continue
            done = False
            for dx, dy in ((1.1, 0), (-1.1, 0), (0, 1.1), (0, -1.1),
                           (0.95, 0.95), (-0.95, 0.95), (0.95, -0.95),
                           (-0.95, -0.95), (1.6, 0), (-1.6, 0),
                           (0, 1.6), (0, -1.6)):
                vx, vy = x + dx, y + dy
                if not (1.2 < vx < BOARD_W - 1.2 and
                        1.2 < vy < BOARD_H - 1.2):
                    continue
                span = (min(x, vx) - 0.48, min(y, vy) - 0.48,
                        max(x, vx) + 0.48, max(y, vy) + 0.48)
                if _clear(boxes, *span):
                    add_track(board, net, [(x, y), (vx, vy)], 0.3)
                    add_via(board, net, (vx, vy), size=0.5, drill=0.25)
                    existing.setdefault(net, []).append((vx, vy))
                    # the new stub blocks BOTH nets' later spots
                    for bl in boxes_for.values():
                        bl.append(span)
                    stats[net] = stats.get(net, 0) + 1
                    done = True
                    break
            if not done:
                add_via(board, net, (x, y), size=0.5, drill=0.25)
                print(f"  NEEDS-REVIEW: via-in-pad {net} tap at "
                      f"{fp.GetReference()} ({x:.1f},{y:.1f})")
    print("plane stubs:", stats)

    # +3V3 pads inside the VLED island's top band (east half) cannot
    # tap In2 locally — feed them south into the 3V3 region between
    # the reservoir pocket (ends x50) and the right strip (starts x69)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "+3V3":
                continue
            x, y = to_local(p.GetPosition())
            if y < 10.5 and 50.5 < x < 68.5:
                add_track(board, "+3V3", [(x, y), (x, 11.7)], 0.3)
                add_via(board, "+3V3", (x, 11.7), size=0.5, drill=0.25)


def zones(board):
    def zone(net, layer, poly, priority):
        ni = board.FindNet(net)
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(ni)
        z.SetAssignedPriority(priority)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetMinThickness(FromMM(0.2))
        z.SetLocalClearance(FromMM(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(mm(x, y).x, mm(x, y).y)
        board.Add(z)

    full = [(0.5, 0.5), (BOARD_W - 0.5, 0.5),
            (BOARD_W - 0.5, BOARD_H - 0.5), (0.5, BOARD_H - 0.5)]
    zone("GND", pcbnew.In1_Cu, full, 0)
    zone("+3V3", pcbnew.In2_Cu, full, 0)
    zone("VLED", pcbnew.In2_Cu, VLED_ISLAND, 1)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def main():
    global OWNED_NETS
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    OWNED_NETS = {"GND", "+3V3", "VLED", "PI5V_RAW", "PI5V_FUSED",
                  "XIN", "XOUT", "XOUT_XTAL",
                  "QSPI_SS", "QSPI_SCLK", "QSPI_SCLK_FL", "QSPI_SD0",
                  "QSPI_SD1", "QSPI_SD2", "QSPI_SD3",
                  "USB_DP_CONN", "USB_DM_CONN", "USB_DP_ESD",
                  "USB_DM_ESD", "USB_DP", "USB_DM", "SENSE1", "SENSE2"}
    for ref, pads in (("Q2", ("3",)), ("Q3", ("3",))):
        fp = get(board, ref)
        for pnum in pads:
            OWNED_NETS.add(pad_of(fp, pnum).GetNetname())

    OWNED_NETS.update({"VBAT_IN", "VBAT_OUT"})
    clear_owned(board)
    ep_vias(board)
    qspi(board)
    crystal(board)
    usb(board)
    power_entry(board)
    vbat(board)
    vled_drops(board)
    led_returns(board)
    qfn_power_fanout(board)
    ic_power_hops(board)
    pi_and_vreg_links(board)
    plane_stubs(board)
    zones(board)
    board.Save(str(BOARD_PATH))
    print(f"critical routing done: {sum(1 for _ in board.GetTracks())} "
          "tracks/vias")


if __name__ == "__main__":
    main()
