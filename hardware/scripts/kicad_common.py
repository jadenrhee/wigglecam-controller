"""Shared helpers for the pcbnew layout scripts (KiCad 10 bundled python)."""

import json
from pathlib import Path

import pcbnew

HW = Path(__file__).resolve().parent.parent
BOARD_PATH = HW / "kicad" / "wigglecam.kicad_pcb"
SYS_FP = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
LOCAL_FP = HW / "kicad"

# Board frame: outline rectangle in absolute KiCad coords.
ORIGIN = (100.0, 100.0)          # mm, top-left of board
BOARD_W, BOARD_H = 76.0, 50.0

FromMM = pcbnew.FromMM


def mm(x, y):
    """Local board coords (origin top-left) → VECTOR2I."""
    return pcbnew.VECTOR2I(FromMM(ORIGIN[0] + x), FromMM(ORIGIN[1] + y))


def to_local(v):
    return (pcbnew.ToMM(v.x) - ORIGIN[0], pcbnew.ToMM(v.y) - ORIGIN[1])


def load_bridge():
    return json.loads((HW / "board.json").read_text())


def fp_lib_path(fpid):
    lib, name = fpid.split(":")
    if lib == "wigglecam":
        return str(LOCAL_FP / "wigglecam.pretty"), name
    p = SYS_FP / f"{lib}.pretty"
    if not p.exists():
        raise FileNotFoundError(f"footprint library not found: {p}")
    return str(p), name


def load_footprint(fpid):
    libpath, name = fp_lib_path(fpid)
    fp = pcbnew.FootprintLoad(libpath, name)
    if fp is None:
        raise FileNotFoundError(f"footprint not found: {fpid}")
    return fp


def save(board):
    board.Save(str(BOARD_PATH))
    print("saved", BOARD_PATH)


class Grid:
    """Coarse occupancy grid for collision-free placement."""
    CELL = 0.25  # mm

    def __init__(self):
        self.used = set()

    def _cells(self, x0, y0, x1, y1):
        # range() already excludes the stop index — a former +1 here
        # phantom-padded every box AND every probe by one cell, which
        # compounded into ~500 mm² of fake occupancy board-wide
        import math
        for ix in range(int(math.floor(x0 / self.CELL)),
                        int(math.ceil(x1 / self.CELL))):
            for iy in range(int(math.floor(y0 / self.CELL)),
                            int(math.ceil(y1 / self.CELL))):
                yield (ix, iy)

    def occupy_bbox(self, x0, y0, x1, y1):
        self.used.update(self._cells(x0, y0, x1, y1))

    def is_free(self, x0, y0, x1, y1):
        return not any(c in self.used for c in self._cells(x0, y0, x1, y1))


def fp_bbox_mm(fp):
    """(x0,y0,x1,y1) local-mm box: union of the reported bbox and every
    pad box. Some footprints (PinSocket, EC11) report origin-centered
    boxes that EXCLUDE their pad fields — trust pads over the report."""
    bb = fp.GetBoundingBox(False)
    x0 = pcbnew.ToMM(bb.GetX()) - ORIGIN[0]
    y0 = pcbnew.ToMM(bb.GetY()) - ORIGIN[1]
    x1 = x0 + pcbnew.ToMM(bb.GetWidth())
    y1 = y0 + pcbnew.ToMM(bb.GetHeight())
    for p in fp.Pads():
        px, py = to_local(p.GetPosition())
        hx = pcbnew.ToMM(p.GetSize().x) / 2
        hy = pcbnew.ToMM(p.GetSize().y) / 2
        r = max(hx, hy)   # pad may be rotated; use the safe radius
        x0, y0 = min(x0, px - r), min(y0, py - r)
        x1, y1 = max(x1, px + r), max(y1, py + r)
    return x0, y0, x1, y1


def fp_extent(fp, margin=0.28):
    """Half-size (w/2, h/2) in mm around the footprint POSITION —
    conservative: max distance from position to any box edge."""
    x0, y0, x1, y1 = fp_bbox_mm(fp)
    cx, cy = to_local(fp.GetPosition())
    return (max(cx - x0, x1 - cx) + margin,
            max(cy - y0, y1 - cy) + margin)


def occupy(grid, fp):
    # reserve the true pad-union box with a TIGHT margin (0.14);
    # searches use a generous one, so parts prefer 0.4+ gaps but may
    # nestle to 0.3 when space is short. Connectors get extra margin
    # (housing lips reach beyond the body bbox).
    margin = 0.55 if fp.GetReference().startswith("J") else 0.14
    x0, y0, x1, y1 = fp_bbox_mm(fp)
    grid.occupy_bbox(x0 - margin, y0 - margin, x1 + margin, y1 + margin)


def place_free(grid, fp, tx, ty, keepin=1.0):
    """Place fp as close to (tx, ty) as possible on a spiral search,
    staying inside the board with `keepin` margin. Falls back to a
    tighter part-to-part margin if the comfortable one finds nothing.
    Returns final (x,y)."""
    import math
    best = None
    for margin in (0.28, 0.16):
        hw, hh = fp_extent(fp, margin)
        ring = 0
        while best is None and ring < 130:
            if ring == 0:
                cands = [(tx, ty)]
            else:
                r = ring * 0.5
                n = max(8, ring * 6)
                cands = [(tx + r * math.cos(2 * math.pi * i / n),
                          ty + r * math.sin(2 * math.pi * i / n))
                         for i in range(n)]
            for cx, cy in cands:
                if (cx - hw < keepin or cy - hh < keepin or
                        cx + hw > BOARD_W - keepin or
                        cy + hh > BOARD_H - keepin):
                    continue
                if grid.is_free(cx - hw, cy - hh, cx + hw, cy + hh):
                    best = (cx, cy)
                    break
            ring += 1
        if best:
            break
    if best is None:
        raise RuntimeError(f"no free spot near ({tx},{ty}) for "
                           f"{fp.GetReference()}")
    fp.SetPosition(mm(*best))
    occupy(grid, fp)
    return best


def pad_pos(fp, padnum):
    for pad in fp.Pads():
        if pad.GetNumber() == str(padnum):
            return to_local(pad.GetPosition())
    raise KeyError(f"{fp.GetReference()} pad {padnum}")
