# JLCPCB upload set

Three files, in this order.

| Step | File |
|---|---|
| PCB | `../wigglecam_gerbers.zip` (upload as-is, do not unzip) |
| BOM | `bom-smt.csv` |
| Placement | `cpl-smt.csv` |

PCB settings: **4 layers**, 76 x 50 mm, **1.6 mm** thickness, 1 oz outer
copper. Assembly: **top side only** (all 90 placements are top side).

## What these files are

`bom-smt.csv` / `cpl-smt.csv` hold the 90 surface-mount placements and
nothing else. The eight through-hole parts are split out into
`bom-handsolder.csv` so the upload has no rows JLC has to reject.

`../bom.csv` and `../cpl.csv` remain the complete set for the whole
board, all 98 placements.

## Hand-soldered separately

J1, J3, J4, J5, J6, J7, J8, SW3. Buy these yourself; they are not in
the JLC upload. All are 2.54 mm headers, JST-XH, or the EC11 encoder,
so none of them is difficult.

## Parts to confirm in the picker

Stock moves daily, so the last step happens in JLC's BOM tool, not
here. Note that JLC's assembly inventory is a different pool from
LCSC's retail stock: a part can be buyable at LCSC and still show a
shortfall in the BOM tool. When that happens the cheapest fix is
usually to deselect it and hand-solder one bought from LCSC.

Expect to resolve these:

- **R12** is C22765 (1.2 k 0603 1 %, JLC basic). It sets the flash
  reference: 1.2 k settles at 0.508 V, giving 1.015 A per LED branch.
  **Do not substitute 1 k** (0.434 V, 0.87 A) or 1.1 k (0.471 V,
  0.94 A).
- **D4 (WS2812B)** is often flagged "Standard Only" on Economic
  assembly. Deselect and hand-solder it if so; it is a 4-pad 5050.
- Anything showing an inventory shortfall: deselect it and hand-solder,
  or pick an equivalent. Nothing here is exotic except the parts
  called out in `../../hardware/partlist.md`.

The one part that cannot simply be dropped is **U1 (AP2112K-3.3,
SOT-23-5)**. It is the 3.3 V rail for the RP2040, flash, INA219 and
WS2812, so the board does nothing without it. If C51118 is short, use
**ME6211C33M5G-N (C82942)**: same SOT-23-5 pinout, 500 mA instead of
600 mA, which still leaves better than 2x margin on this board's
221 mA worst case. Any other substitute needs its pinout checked
against 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT first, because plenty of
SOT-23-5 regulators number those differently.
