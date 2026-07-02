"""Create wigglecam.kicad_pcb: 4-layer board, outline, nets, placement.

Placement strategy (docs/plan.md phase 2):
- fixed anchors for ICs/connectors/mechanical parts;
- decoupling caps assigned to specific power pins by net signature and
  placed adjacent to those pads (positions computed from the real pad
  coordinates after the IC is placed);
- remaining passives anchored to the nearest fixed-part pad on their
  most specific net, spiral-searched into free space.

Run with KiCad's bundled python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/\
Versions/Current/bin/python3 01_make_board.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import (BOARD_PATH, BOARD_H, BOARD_W, FromMM, Grid,
                          load_bridge, load_footprint, mm, occupy,
                          pad_pos, place_free, save, to_local)

# ------------------------------------------------------------- anchors ----
# ref: (x, y, rotation_deg)  — local mm, origin top-left, +y down.
ANCHORS = {
    "U2": (30, 21, 0),        # RP2040: QSPI pins 51-56 exit the top edge
    "U3": (20.7, 12.2, 0),    # flash up-left, ~10 mm from U2
    "Y1": (24.5, 29, 90),     # crystal below U2 pins 20/21 (bottom row)
    "U1": (17.5, 32, 0),      # LDO
    "U4": (38, 35, 90),       # USB ESD between connector and MCU
    "J2": (38, 47.7, 0),      # USB-C, mouth out the bottom edge
    "J8": (19.65, 4.4, 90),   # Pi 2x6 socket: pin1 at origin, pins
                              # extend EAST — this centers it ~26
    "J1": (48, 46, 90),       # SWD 1x3
    "F1": (8.5, 7, 90),       # power entry, top-left (clear of H1)
    "Q1": (12.5, 11, 180),    # reverse-polarity FET; rot180 puts the
                              # drain (SOT-23 center pin) toward F1
    "D2": (9.5, 20.5, 90),    # VLED->VSYS OR-diode on the island's
                              # west column, clear of the Q1/R3 pocket
    "D1": (44, 37, 90),       # VBUS OR-diode near USB
    "U5": (52, 24, 0),        # flash driver block, right side
    "Q2": (60, 20, 0),
    "Q3": (60, 32, 0),
    "J3": (73.6, 22, 270),    # LED JSTs on the right edge
    "J4": (73.6, 36, 270),
    "U6": (11, 36, 0),        # battery monitor, bottom-left
    "R19": (11.5, 32, 0),     # 10 mΩ shunt
    "J5": (2.9, 34.5, 90),    # VBAT in/out on the left edge
    "J6": (2.9, 44, 90),
    "J7": (2.9, 25, 90),      # shutter JST, left edge
    "SW3": (55, 8.5, 0),      # encoder, top-right (clear of H2 hole)
    "SW1": (23.5, 44.2, 0),   # BOOTSEL — stacked with RUN, west of
    "SW2": (23.5, 36.2, 0),   # the USB corridor (no side-by-side room)
    "D4": (59, 46, 0),        # WS2812B (clear of SWD pins ending x53.1)
    "D5": (47, 28, 0),        # 1N4148WS
    "D6": (66, 45, 0),        # debug LED
    "D3": (8.2, 26, 90),      # shutter TVS east of J7
}

# Anchors resolved by NET (refs shift when the schematic is edited;
# nets are stable). net pair -> (x, y, rot)
NET_ANCHORS = [
    ({"XOUT", "XOUT_XTAL"}, (31.6, 27, 90)),      # crystal series R
    ({"QSPI_SCLK", "QSPI_SCLK_FL"}, (27.0, 12.6, 0)),   # SCLK 27R at
    #                                 the flash end of the lane
    ({"QSPI_SS", "+3V3"}, (13.4, 13.6, 0)),       # CS pullup
    ({"USB_DP_ESD", "USB_DP"}, (37.05, 20, 90)),  # DP 27.4R inline
    ({"USB_DM_ESD", "USB_DM"}, (38.95, 20, 90)),  # DM 27.4R inline
    ({"SENSE1", "GND"}, (60, 24, 0)),             # branch A 0.5R sense
    ({"SENSE2", "GND"}, (60, 36, 0)),             # branch B 0.5R sense
]

# routing corridors reserved before passives are auto-placed:
# (x0, y0, x1, y1) regions the placer must keep clear
CORRIDORS = [
    (35.4, 16.5, 40.2, 45.0),   # USB differential pair, U2 → ESD → J2
    (15.2, 12.8, 32.0, 16.4),   # QSPI lanes, U2 top edge → flash
    (15.2, 8.0, 17.8, 12.8),    # QSPI far-side verticals, left of flash
    (25.6, 9.4, 30.2, 12.8),    # QSPI near-side verticals + SCLK/SD3
    (6.0, 7.9, 34.0, 9.4),      # power entry lane below the J8 field
                                # (J8's own occupy covers the THT area)
    (28.6, 24.8, 33.2, 29.4),   # crystal routing pocket (XIN/XOUT/R1)
    (21.6, 27.4, 23.2, 32.2),   # crystal XOUT_XTAL west approach
    (30.8, 15.2, 40.2, 17.2),   # USB pair lanes into U2 pads 46/47
    (53.8, 3.5, 72.3, 18.5),    # EC11 body+pads (origin at A/B/C pads,
                                # S1/S2 +14.5 mm east, body centered
                                # +7.5,+2.5); the knob turns 20 mm above
                                # the board so only body+pads block.
                                # SW3 skips bbox-occupy (bogus bbox)
    (30.4, 29.4, 32.8, 32.4),   # crystal XOUT_XTAL south sweep (east)
    (22.2, 30.9, 30.6, 32.3),   # crystal XOUT_XTAL south sweep (west)
    (65.8, 18.5, 72.5, 40.0),   # LED-return bypass strip, right edge
    (56.9, 24.9, 59.4, 26.3),   # sense-R GND via pocket, branch A
    (56.9, 36.9, 59.4, 38.3),   # sense-R GND via pocket, branch B
    (13.4, 31.0, 15.4, 46.4),   # VBAT_OUT heavy trace column
    (2.0, 41.6, 15.4, 46.4),    # VBAT_OUT row to J6 (either pin row)
    (2.0, 32.8, 9.6, 34.7),     # VBAT_IN heavy trace row
]

# power-pin cap assignment: (owner ref, pad) consuming 100nF {+3V3,GND}
CAP_100N_3V3_TARGETS = [
    ("U2", "1"), ("U2", "10"), ("U2", "22"), ("U2", "33"),
    ("U2", "42"), ("U2", "49"),      # six IOVDD
    ("U2", "48"),                    # USB_VDD
    ("U2", "43"),                    # ADC_AVDD
    ("U3", "8"),                     # flash VCC
    ("U6", "4"),                     # INA219 VS
]


def netsig(part):
    return frozenset(part["pads"].values())


def main():
    bridge = load_bridge()
    board = pcbnew.NewBoard(str(BOARD_PATH))
    board.SetCopperLayerCount(4)

    # default netclass: KiCad's 0.5 mm default clearance is far above
    # JLC capability and flags every fine-pitch part; use our reals.
    try:
        dnc = board.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
        dnc.SetClearance(FromMM(0.15))
        dnc.SetTrackWidth(FromMM(0.2))
        dnc.SetViaDiameter(FromMM(0.6))
        dnc.SetViaDrill(FromMM(0.3))
    except AttributeError as e:
        raise RuntimeError(f"netclass API drift, fix here: {e}")

    # board-level minimums = JLCPCB 4-layer capabilities (conservative)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = FromMM(0.127)
    ds.m_ViasMinSize = FromMM(0.4)
    ds.m_MinThroughDrill = FromMM(0.25)
    ds.m_ViasMinAnnularWidth = FromMM(0.1)
    ds.m_MinClearance = FromMM(0.127)
    ds.m_CopperEdgeClearance = FromMM(0.3)
    ds.m_HoleClearance = FromMM(0.254)

    # --- board outline: plain 65 x 42 rectangle on Edge.Cuts
    corners = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm(*corners[i]))
        seg.SetEnd(mm(*corners[(i + 1) % 4]))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(FromMM(0.1))
        board.Add(seg)

    # --- nets
    nets = {}
    for name in bridge["nets"]:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # --- footprints
    fps = {}
    for part in bridge["parts"]:
        fp = load_footprint(part["footprint"])
        fp.SetReference(part["ref"])
        fp.SetValue(part["value"])
        fp.SetPosition(mm(-20, -20))  # parked; placed below
        board.Add(fp)
        padnames = {p.GetNumber() for p in fp.Pads()}
        for padnum, netname in part["pads"].items():
            if padnum not in padnames:
                raise RuntimeError(
                    f"{part['ref']} ({part['footprint']}): netlist pad "
                    f"{padnum} not in footprint pads {sorted(padnames)}")
            for pad in fp.Pads():
                if pad.GetNumber() == padnum:
                    pad.SetNet(nets[netname])
        fps[part["ref"]] = fp

    grid = Grid()

    # --- fixed anchors (refs + net-resolved)
    anchors = dict(ANCHORS)
    for netpair, place in NET_ANCHORS:
        matches = [p["ref"] for p in bridge["parts"]
                   if p["ref"][0] == "R" and set(p["pads"].values()) == netpair]
        assert len(matches) == 1, (netpair, matches)
        anchors[matches[0]] = place
    for ref, (x, y, rot) in anchors.items():
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(mm(x, y))
        if ref != "SW3":   # bogus origin-centered bbox; corridor covers it
            occupy(grid, fp)

    # orientation fixups: some routes need a specific pad on a specific
    # side; flip the part rather than guessing footprint pad order.
    def fixup(fp, net, side):
        pads = {}
        for p in fp.Pads():
            pads.setdefault(p.GetNetname(), to_local(p.GetPosition()))
        other = next(n for n in pads if n != net)
        axis = 1 if side in ("north", "south") else 0
        want_less = side in ("north", "west")
        if (pads[net][axis] > pads[other][axis]) == want_less:
            fp.SetOrientationDegrees(fp.GetOrientationDegrees() + 180)

    fixup(fps["F1"], "PI5V_RAW", "north")
    fixup(fps["D2"], "VLED", "north")
    fixup(fps["J3"], "VLED", "north")
    fixup(fps["J4"], "VLED", "north")

    def ref_by_netpair(netpair):
        return next(p["ref"] for p in bridge["parts"]
                    if p["ref"][0] == "R"
                    and set(p["pads"].values()) == netpair)

    fixup(fps[ref_by_netpair({"SENSE1", "GND"})], "SENSE1", "east")
    fixup(fps[ref_by_netpair({"SENSE2", "GND"})], "SENSE2", "east")
    fixup(fps[ref_by_netpair({"QSPI_SS", "+3V3"})], "QSPI_SS", "east")
    fixup(fps[ref_by_netpair({"XOUT", "XOUT_XTAL"})], "XOUT_XTAL", "south")
    fixup(fps[ref_by_netpair({"QSPI_SCLK", "QSPI_SCLK_FL"})],
          "QSPI_SCLK", "east")

    # reserve routing corridors before any passive is auto-placed
    for x0, y0, x1, y1 in CORRIDORS:
        grid.occupy_bbox(x0, y0, x1, y1)

    # mechanical parts go in BEFORE the auto-placer so passives avoid
    # them (fiducial keep-outs, hole courtyards)
    for i, (x, y) in enumerate([(3, 3), (39.5, 2.5), (11, 47), (73, 47)]):
        fp = load_footprint("MountingHole:MountingHole_2.7mm_M2.5")
        fp.SetReference(f"H{i+1}")
        fp.SetPosition(mm(x, y))
        board.Add(fp)
        occupy(grid, fp)
    for i, (x, y) in enumerate([(2.5, 12), (68, 47.8), (74, 8)]):
        fp = load_footprint("Fiducial:Fiducial_1mm_Mask2mm")
        fp.SetReference(f"FID{i+1}")
        fp.SetPosition(mm(x, y))
        board.Add(fp)
        occupy(grid, fp)

    byref = {p["ref"]: p for p in bridge["parts"]}
    placed = set(anchors)

    # VLED reservoirs claim their channel spots FIRST — the decoupling
    # spiral otherwise fills the only zone big enough for them
    res_refs = [p["ref"] for p in bridge["parts"]
                if p["name"] == "C" and p["value"] == "470uF"]
    for ref, tgt in zip(res_refs, [(46, 8), (45.5, 17)]):
        place_free(grid, fps[ref], *tgt)
        placed.add(ref)

    # --- decoupling caps by net signature
    caps_100n_33 = [p["ref"] for p in bridge["parts"]
                    if p["name"] == "C" and p["value"] == "100nF"
                    and netsig(p) == frozenset({"+3V3", "GND"})]
    assert len(caps_100n_33) == len(CAP_100N_3V3_TARGETS), \
        (caps_100n_33, CAP_100N_3V3_TARGETS)
    def orient_cap_toward(capref, net, px, py):
        """Rotate a 2-pin cap so its `net` pad faces the target pad —
        the pin->cap hop then runs straight and short."""
        fp = fps[capref]
        pads = {p.GetNetname(): to_local(p.GetPosition())
                for p in fp.Pads()}
        other = next(n for n in pads if n != net)
        d_net = (pads[net][0]-px)**2 + (pads[net][1]-py)**2
        d_oth = (pads[other][0]-px)**2 + (pads[other][1]-py)**2
        if d_net > d_oth:
            fp.SetOrientationDegrees(fp.GetOrientationDegrees() + 180)

    for ref, (owner, padnum) in zip(caps_100n_33, CAP_100N_3V3_TARGETS):
        px, py = pad_pos(fps[owner], padnum)
        # push outward from the owner's center so the cap sits just
        # outside the package body, next to its pin
        cx, cy = to_local(fps[owner].GetPosition())
        dx, dy = px - cx, py - cy
        norm = max((dx * dx + dy * dy) ** 0.5, 0.1)
        tx, ty = px + dx / norm * 1.9, py + dy / norm * 1.9
        if owner == "U2" and padnum in ("33", "42"):
            # these pins' outward spots are inside the USB corridor;
            # the free strip east of the pad column fits their caps
            tx, ty = 34.35, py
            fps[ref].SetOrientationDegrees(90)
        place_free(grid, fps[ref], tx, ty)
        orient_cap_toward(ref, "+3V3", px, py)
        placed.add(ref)

    # DVDD (VREG_1V1) caps → pins 23 and 50; 1 µF pair → pins 44/45
    special = [
        (lambda p: p["value"] == "100nF" and
            netsig(p) == frozenset({"VREG_1V1", "GND"}),
         [("U2", "23"), ("U2", "50")]),
        (lambda p: p["value"] == "1uF" and
            netsig(p) == frozenset({"VREG_1V1", "GND"}), [("U2", "45")]),
        (lambda p: p["value"] == "1uF" and
            netsig(p) == frozenset({"+3V3", "GND"}), [("U2", "44")]),
        # crystal load caps: pad anchor for orientation + explicit
        # seed clear of the XOUT_XTAL sweep corridors
        (lambda p: p["value"] == "15pF",
         [("Y1", "1", 27.7, 30.4), ("Y1", "3", 22.3, 26.4)]),
        (lambda p: p["value"] == "22uF" and
            netsig(p) == frozenset({"VSYS", "GND"}),
         [(12, 28.8), (15.5, 28.8)]),
    ]
    for sel, targets in special:
        refs = [p["ref"] for p in bridge["parts"]
                if p["name"] == "C" and sel(p) and p["ref"] not in placed]
        assert len(refs) == len(targets), (refs, targets)
        for ref, tgt in zip(refs, targets):
            anchor_pad = None
            if isinstance(tgt[0], str) and len(tgt) == 4:
                anchor_pad = pad_pos(fps[tgt[0]], tgt[1])
                tx, ty = tgt[2], tgt[3]
                if tgt[:2] == ("Y1", "1"):
                    # rotated, it fits the narrow pocket east of Y1
                    fps[ref].SetOrientationDegrees(90)
            elif isinstance(tgt[0], str):
                anchor_pad = pad_pos(fps[tgt[0]], tgt[1])
                tx, ty = anchor_pad
                cx, cy = to_local(fps[tgt[0]].GetPosition())
                dx, dy = tx - cx, ty - cy
                n = max((dx * dx + dy * dy) ** 0.5, 0.1)
                tx, ty = tx + dx / n * 1.9, ty + dy / n * 1.9
            else:
                tx, ty = tgt
            place_free(grid, fps[ref], tx, ty)
            if anchor_pad is not None:
                # face the cap's signal pad (its non-GND net) toward
                # the pad it decouples/loads, so the tie runs straight
                signet = next((n for n in byref[ref]["pads"].values()
                               if n != "GND"), None)
                if signet:
                    orient_cap_toward(ref, signet, *anchor_pad)
            placed.add(ref)

    # --- everything else: anchor to the most specific net's fixed pad
    netpads = {}
    for p in bridge["parts"]:
        for padnum, net in p["pads"].items():
            netpads.setdefault(net, []).append((p["ref"], padnum))
    POWERISH = {"GND", "+3V3", "VSYS", "VLED", "VBUS", "PI5V_RAW"}

    remaining = [p for p in bridge["parts"] if p["ref"] not in placed]
    # place parts on fewer-pad (more specific) nets first
    def specificity(p):
        return min(len(netpads[n]) for n in p["pads"].values()
                   if n not in POWERISH) if any(
            n not in POWERISH for n in p["pads"].values()) else 99
    remaining.sort(key=specificity)

    for p in remaining:
        target = None
        for net in sorted(p["pads"].values(),
                          key=lambda n: (n in POWERISH, len(netpads[n]))):
            for ref, padnum in netpads[net]:
                if ref in placed and ref != p["ref"]:
                    target = pad_pos(fps[ref], padnum)
                    break
            if target:
                break
        if target is None:
            target = (BOARD_W / 2, BOARD_H / 2)
        place_free(grid, fps[p["ref"]], *target)
        placed.add(p["ref"])

    save(board)
    print(f"placed {len(placed)} parts")


if __name__ == "__main__":
    main()
