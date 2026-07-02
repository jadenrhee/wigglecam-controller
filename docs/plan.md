# Execution plan — RP2040 Camera Controller board

End-to-end automated design flow: schematic-as-code → scripted
placement → constrained routing → DRC to zero → fab outputs →
firmware → programmatic verification report. Each phase lands as its
own commit. Nothing in a later phase starts until the earlier phase's
check passes.

## Phase 0 — toolchain

Machine currently has none of the EDA stack. Install:

- KiCad 9 (`brew install --cask kicad`) — provides `kicad-cli` and the
  bundled Python with the `pcbnew` API (scripts must run under
  KiCad's Python, not system Python — known macOS friction, planned for)
- SKiDL (`pip install skidl`) + KiCad symbol/footprint libs on the
  search path
- Freerouting jar (needs Java 17+; verify `java -version`, else
  `brew install openjdk`)
- Pico SDK + `cmake` + `gcc-arm-embedded` for firmware

## Phase 1 — schematic as code (SKiDL)

One Python module per block: `mcu.py` (RP2040 + crystal + QSPI flash +
decoupling per the official *Hardware design with RP2040* guide, cited
inline), `power.py` (USB-C, reverse-polarity P-FET, AP2112K),
`flashdrv.py` (dual constant-current sink), `monitor.py` (INA219 +
shunt), `controls.py` (shutter conditioning, EC11, WS2812B),
`piheader.py`. Every part carries symbol + footprint + LCSC number
(see `hardware/partlist.md` — all stock-verified). Output: KiCad
netlist + **SKiDL ERC passing** (unconnected pins, drive conflicts).

## Phase 2 — board init + placement (pcbnew API)

- 4-layer stackup **JLC04161H-7628**: L1 signal / L2 GND / L3 3V3+5V
  islands / L4 signal. Outline ~65 × 42 mm — final envelope vs
  enclosure = TODO(measure).
- Net classes: `DEFAULT` 0.2/0.15 mm; `QSPI` 0.15 mm; `USB_DIFF`
  90 Ω differential geometry **computed for this stackup** with
  JLCPCB's impedance calculator (~0.36 mm / 0.15 mm gap expected —
  see Deviations); `PWR` 0.5 mm; `FLASH_HI` ≥1 mm + pours (IPC-2221
  sizing shown in the verification report).
- Scripted placement: RP2040 cluster tight (crystal + load caps
  against XIN/XOUT, away from QSPI; flash <20 mm; every VDD pin's
  100 nF adjacent); USB-C, JST, encoder, header on edges; flash
  driver + reservoir caps in their own corner over solid ground.

## Phase 3 — routing (constrained first, autoroute second)

Hand-constrained via pcbnew scripting **before** the autorouter runs:
QSPI (length-matched, CLK longest, series-R pads near flash), crystal
(short, ground-guarded), USB D± (diff pair, length-matched, ESD in
path), flash high-current path (pours). Then Freerouting headless
(`.dsn` → `.ses`) for the low-speed remainder — treated as a draft:
scripted cleanup removes redundant vias, widens power, adds GND
stitching, then re-pours planes. Freerouting's known over-via/detour
habits get an explicit pass, and anything I can't clean to standard is
marked NEEDS REVIEW rather than shipped quietly.

## Phase 4 — DRC to zero

`kicad-cli pcb drc` with JLCPCB 4-layer capability rules encoded as
custom design rules (min track 0.09 mm — we use ≥0.15; min via drill
0.3 mm / annular per JLC; hole-to-copper etc.). Iterate until zero
errors, zero unconnected.

## Phase 5 — fab outputs

`kicad-cli` Gerbers (JLC layer naming) + Excellon drill, BOM CSV and
CPL (with the known JLC rotation-offset corrections applied for
QFN/USB-C — flagged for visual check anyway), board renders (top /
bottom / 3D) for the README, schematic PDF.

## Phase 6 — firmware (Pico SDK, C)

I2C slave @ 0x17 to the Pi (register map in `docs/protocol.md`):
WHO_AM_I, TRIGGER_CAPTURE (fires camera-sync pulse on GPIO17-line),
FLASH_FIRE(duration ms, capped 150 ms in firmware AND hardware-safe
via the boot pulldown), FLASH_CURRENT (PWM ref), READ_BATTERY
(cached from INA219 on the internal I2C bus), READ_ENCODER_DELTA,
BUTTON_EVENTS, SET_LED. Interrupt-driven EC11 quadrature decode,
debounced shutter, watchdog. Builds clean with cmake + make.

## Phase 7 — verification report (the deliverable that matters)

`hardware/scripts/verify_layout.py` runs under KiCad Python, parses
the finished `.kicad_pcb`, and **measures** every claim: QSPI net
lengths/widths + flash distance, crystal cap proximity, per-power-pin
decoupling distance, EP via count, USB pair geometry + skew, flash
path copper vs IPC-2221 (calc shown: I = k·ΔT^0.44·A^0.725), DRC
output parse, BOM-vs-stock table. Output is
`docs/verification-report.md` with PASS/FAIL + measured value + source
per rule. Plus `docs/design-rationale.md` and
`docs/human-review-checklist.md` (exactly which nets were
hand-constrained vs autorouted, and every NEEDS REVIEW item).

## Known deviations & risks (stated up front)

1. **USB diff width:** the oft-quoted "0.8 mm / 0.15 mm" for 90 Ω
   applies to 2-layer 1.6 mm boards. On JLC04161H-7628 (L1→L2
   dielectric ≈ 0.21 mm) 90 Ω differential needs ≈ 0.36 mm width — the
   spec's intent (controlled 90 Ω) is honored over its literal number;
   both cited in the report. USB-FS at 12 Mbps is tolerant regardless.
2. **AO3400A pulse heating:** ~1.3 W in a SOT-23 for 150 ms. Transient
   thermal calc is a hard verification gate; fallback part chosen if
   it fails (larger package or third branch at lower current).
3. **Freerouting quality** on the QFN fanout region: if cleanup can't
   reach professional standard there, those nets are re-routed by
   script or flagged NEEDS REVIEW explicitly.
4. **WS2812B 5050 vs JLC assembly:** LCSC stocks it; JLC assembly has
   rejected the 5050 variant before. Hand-solder fallback (trivial).
5. **INA219 in the battery path** is invasive to the camera's battery
   wiring; the board provides pass-through connectors and a
   solder-jumper bypass so it's optional.
6. **CPL rotations** for QFN-56/USB-C are a classic JLC gotcha —
   corrected from the known offsets table and listed in the human
   review checklist for visual confirmation.
