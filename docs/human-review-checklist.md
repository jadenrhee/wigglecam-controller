# Human review checklist — before ordering

The DRC is clean and the verification report measures the critical
rules, but automated routing was used for the low-speed nets and a
scripted finishing pass closed the last airwires. A person should
spot-check the following in the KiCad GUI (open
`hardware/kicad/wigglecam.kicad_pcb`), roughly in priority order:

## Hand-constrained (scripted, deterministic — verify once)
- [ ] **QSPI fanout** (U2 top edge → U3): nested lanes, no crossings,
      27 Ω inline in SCLK near the flash. Verified by measurement in
      the report; eyeball for aesthetics only.
- [ ] **USB differential pair** (J2 → U4 → R6/R7 → U2): mirror-pad
      jumpers south of the connector field cross on B.Cu; one
      deliberate B.Cu crossover near x=34 where DM crosses DP's lane;
      0.25/0.3 mm necks at the QFN and connector. All fine at USB-FS.
- [ ] **Flash current loop**: VLED In2 island → JST → LED → FET →
      0.5 Ω → GND vias. Confirm the island outline hugs the loads
      (View → In2.Cu) and the two 470 µF polymers sit on it.
- [ ] **Power entry**: J8 5 V pins → PTC → P-FET drain; the 0.5 mm
      lane threads between the header barrels and the flash pads
      (steady current is <0.5 A; the 2 A flash pulse is a 150 ms
      transient — see power notes in the verification report).
- [ ] **Battery path**: J5 → 10 mΩ shunt → J6 in 1.5 mm copper;
      INA219 taps ride the same nets (not a true Kelvin connection —
      acceptable for ±few-% telemetry, noted here deliberately).

## Autorouted + scripted finishing (higher scrutiny)
- [ ] **ENC_A** crosses the board via a scripted maze route (B.Cu,
      down the encoder margin) plus small closes near C32 (one
      via-in-pad). Trace it end-to-end visually (Highlight Net).
- [ ] **VLED island continuity**: the In2 finger was widened to
      1.6 mm and patched; run DRC in the GUI and confirm zero
      unconnected, then eyeball In2.Cu for the finger path.
- [ ] **Via-in-pad taps** flagged in the layout logs (a handful of
      0603 pads and C32): fine for hand assembly; for JLC reflow
      either accept minor wicking or request them unfilled/plugged.
- [ ] **VREG_1V1 pin-23 leg** runs on B.Cu beneath the crystal
      pocket; DRC-clean, but confirm it doesn't bother you EMI-wise
      (12 MHz crystal, 1.1 V core rail).
- [ ] **Decoupling for U2 pins 43/44** is ~8 mm away (corridor
      congestion); both pins have 2 mm plane vias. ADC is unused in
      this design. Accept or hand-nudge.

## Assembly / ordering specifics
- [ ] **CPL rotations are KiCad-native**: JLCPCB's zero-angle
      conventions differ per package. In the JLC assembly preview,
      verify polarity/orientation of: **Q1** (reverse-protection FET —
      board is placed at rot 180 deliberately), U1, U4, U5, U6,
      D1/D2 (SS34 cathode bands), D5, C27/C28 polarity, U2 pin-1.
- [ ] **TS-1187A buttons** are wired on diagonal pads (works for both
      internal pairing conventions) — beep the actual switches before
      soldering anyway (one beep: legs are a pole pair).
- [ ] **EC11 encoder** is through-hole with the shaft at ~(62.5, 11)
      board-local — check against the enclosure's front-panel hole
      before ordering the enclosure print (TODO(measure)).
- [ ] **RP2040 QFN-56 (0.4 mm pitch)** is the only hard hand-solder
      part; if hand-building, use flux + drag soldering or hot air,
      and buy 2–3 spares.
- [ ] **Stock re-check**: BOM quantities/stock were verified
      2026-07-02, generic passives matched to concrete LCSC numbers
      2026-07-03 (see hardware/partlist.md); LCSC stock moves —
      re-confirm live in the JLC BOM tool at upload.
- [x] ~~The 470 µF 6.3 V polymer (EIA-7343) needs a concrete LCSC
      pick at order time~~ **Resolved 2026-07-03:** C27/C28 =
      Panasonic 6TPE470MI POSCAP, 470 µF 6.3 V, 18 mΩ (LCSC
      **C402828**) — meets the ≤100 mΩ ESR the reservoir sizing
      assumes. 6.3 V rating on a ~4.9 V rail is ~78 % — inside normal
      polymer derating practice, but do not repurpose this rail
      above 5.1 V.

## Known deviation from the reference design (accepted, not fixed)

- **BOOTSEL button has no 1 kΩ series resistor.** The RP2040
  reference design puts ~1 kΩ between the flash-CS net and the
  BOOTSEL button so that pressing the button while the RP2040 is
  actively driving QSPI_SS doesn't short a driven output to ground.
  On this board SW1 connects QSPI_SS straight to GND. Consequences:
  BOOTSEL entry works normally (hold BOOTSEL, tap RUN), but avoid
  pressing BOOTSEL while the board is running — during the boot-ROM
  flash probe the pad briefly drives into the short (tens of mA,
  µs–ms scale; survivable but out-of-spec stress). Fixing it means
  inserting an 0603 into SW1's ground leg and re-running the DRC +
  verification pipeline — do this in a future board revision, or
  before ordering if the runtime-press scenario bothers you.
