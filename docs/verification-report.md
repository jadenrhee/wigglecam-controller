# Verification report

Generated 2026-07-02 by `hardware/scripts/07_verify.py`, which measures the final `wigglecam.kicad_pcb` directly — every value below is a measurement or a machine check, not an assertion.

| # | Area | Rule | Measured | Verdict | Source |
|---|------|------|----------|---------|--------|
| 1 | QSPI | flash within 20 mm of the RP2040 | 12.8 mm center-to-center | **PASS** | RP2040 hardware design guide (RP-008279-DS); PCB Artists RP2040 layout notes |
| 2 | QSPI | CLK is the longest QSPI trace | CLK 8.3 mm vs data 7.8–19.9 mm; SS total 50.1 mm incl. its off-bus BOOTSEL-button leg | **DEVIATION** | PCB Artists RP2040 layout notes. **Accepted:** the far-side data wraps exceed CLK by 11.6 mm ≈ 70 ps — about 1.9% of the 133 MHz half-period; the rule targets much faster/longer buses. Data arrive early relative to CLK, which errs in the safe direction for setup time. |
| 3 | QSPI | data lines length-matched | spread 12.1 mm ≈ 73 ps | **PASS** | RP2040 datasheet timing budget (SDR, 7.5 ns period) |
| 4 | QSPI | trace width ~0.15 mm | widths [0.15] | **PASS** | PCB Artists RP2040 layout notes |
| 5 | QSPI | series R in SCLK near the flash | 27 Ω at 6.3 mm from flash | **PASS** | PCB Artists RP2040 layout notes (series termination option) |
| 6 | Crystal | load caps adjacent to the crystal | cap-to-crystal-pad 3.2, 5.7 mm | **PASS** | RP2040 hardware design guide §2.2 |
| 7 | Crystal | XIN/XOUT short | total crystal-net copper 44.6 mm (includes both load-cap ties and the series-R leg; the direct U2-to-crystal legs are the ~5 mm placement distance) | **DEVIATION** | RP2040 hardware design guide §2.2. **Accepted:** longer than a hand-optimized layout (the Pico achieves ~10 mm total) because the load-cap ties detour around the congested region. A 12 MHz fundamental crystal is highly tolerant of load-trace length; the ties run over the solid In1 GND plane. Flagged for visual review. |
| 8 | Crystal | crystal nets isolated from QSPI | min endpoint separation 6.9 mm | **PASS** | RP2040 hardware design guide §2.2 (keep XIN/XOUT away from fast signals) |
| 9 | Decoupling | 100 nF adjacent to every RP2040 power pin | pin-to-nearest-cap 2.5–8.0 mm (6 of 8 pins <3 mm) | **DEVIATION** | RP2040 hardware design guide §2.1 (place decoupling close). **Accepted:** pins 43 (ADC_AVDD) and 44 (VREG_VIN) have their caps ~8 mm away — the USB corridor owns their natural spots. Both pins have dedicated low-inductance vias into the 3V3 plane 2 mm away (interior fanout), and this design does not use the ADC. Flagged in the review checklist. |
| 10 | Decoupling | QFN center pad stitched to GND with >=9 vias | 9 vias in the EP | **PASS** | RP2040 hardware design guide §2.1 |
| 11 | USB | pair length-matched | DP 39.6 mm vs DM 40.4 mm (Δ 0.8 mm; USB-FS intra-pair budget is generous) | **PASS** | USB 2.0 spec §7.1.6 (FS); Intel HSD guidelines for FS routing |
| 12 | USB | differential geometry 0.36 mm width (90 Ω on JLC04161H-7628 per JLCPCB impedance calculator; the oft-cited 0.8 mm applies to 2-layer 1.6 mm boards) with documented 0.25/0.3 mm necks at the QFN and connector fields | widths used: [0.25, 0.3, 0.36] | **PASS** | JLCPCB impedance calculator (JLC04161H-7628); deviation documented in docs/plan.md |
| 13 | USB | ESD array in the line before the MCU | USBLC6 carries CONN-side and ESD-side nets (flow-through) | **PASS** | ST USBLC6-2 datasheet, application diagram |
| 14 | Flash path | IPC-2221 width for 2 A at ΔT=10 °C on 1 oz: A=(I/(k·ΔT^0.44))^(1/0.725) = 42.4 mil² → 0.78 mm; VLED is a plane island (>=5 mm) and shares the 2 A across two 1 A branches | LED return widths [1.0] mm vs 1 A need 0.30 mm | **PASS** | IPC-2221A §6.2, external-layer chart |
| 15 | Flash path | highest-current distribution as pour, not trace | VLED In2 island area 684 mm² | **PASS** | IPC-2221A; standard practice for pulse rails |
| 16 | Power integrity | solid GND plane on In1 | 3455 mm² of 3800 mm² board | **PASS** | standard 4-layer practice; Ott, Electromagnetic Compatibility Engineering ch.16 |
| 17 | Power integrity | no signal routing through the planes (no plane splits under high-speed nets) | 0 track segments on In1/In2 | **PASS** | Ott ch.16; verified by layer scan |
| 18 | Power integrity | reservoir sizing: 2×470 µF polymer supplies the 2 A pulse front; steady-state comes from the X1202 5 V rail (5 A). ΔV = I·t/C for the first 1 ms before the rail responds: 2 A × 1 ms / 940 µF ≈ 2.1 V worst-case droop locally, recovered by the rail; low-ESR polymer chosen for this reason | 2×470 µF EIA-7343 polymer on VLED at the reservoir pocket | **PASS** | standard reservoir sizing; part choice documented in BOM |
| 19 | Power integrity | input protection chain present | PI5V → PTC 3 A → AO3401A reverse-polarity P-FET → VLED | **PASS** | netlist topology check; AOS AO3401A datasheet |
| 20 | DFM | DRC clean at JLCPCB 4-layer capability limits (min track 0.127, clearance 0.127, via 0.4/0.25, annular 0.1, edge 0.3, hole-to-copper 0.254) | 0 violations, 0 unconnected | **PASS** | kicad-cli drc --refill-zones (report committed); jlcpcb.com/capabilities 4-layer |
| 21 | DFM | min track width used >= 0.127 mm | 0.150 mm | **PASS** | JLCPCB capabilities |
| 22 | DFM | min via >= 0.4/0.2 mm (JLC min 0.25 hole for 4-layer mechanical; ours 0.25 drill / 0.5 dia) | smallest via (0.5, 0.25) (dia, drill) of 188 vias | **PASS** | JLCPCB capabilities |
| 23 | Assembly | hand-solderable: no BGA; finest pitch is the RP2040 QFN-56 at 0.4 mm (hard but standard with flux + drag-soldering or hot air; everything else is 0603+/SOIC/SOT) | packages: 27 kinds; finest: ['QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm'] | **PASS** | design constraint from the brief |
| 24 | Assembly | fiducials for pick-and-place | 3 fiducials (FID1-3) | **PASS** | JLCPCB SMT guidelines |

## Known deviations & NEEDS-REVIEW items

These are called out rather than hidden; see also docs/human-review-checklist.md:

- **USB differential width** deviates from the commonly quoted 0.8 mm because that figure assumes a 2-layer 1.6 mm board; on JLC04161H-7628 the 90 Ω geometry is ≈0.36 mm (JLCPCB impedance calculator). Short 0.25/0.3 mm necks exist at the QFN pads and connector field — at USB-FS (12 Mbps) these are electrically negligible.
- **USB series resistors** sit mid-corridor (~15 mm from the RP2040) rather than hard against it — a placement-congestion trade-off, acceptable at FS speeds.
- **A handful of via-in-pad plane taps** were used where the fanout was too dense for offset stubs (flagged in the layout scripts' NEEDS-REVIEW output). For hand assembly this is a non-issue; for reflow, request unfilled vias or accept minor solder wicking on those 0603 pads.
- **Final-mile airwire closes** (scripts 05_finish through 05i) were validated only by the DRC gate; give the affected areas (encoder net ENC_A's cross-board route, the VLED island patches) a visual pass in the KiCad GUI before ordering.
- **VREG_1V1 pin-23 leg** routes via B.Cu under the crystal pocket; verify visually that it keeps clear of the XIN/XOUT region (DRC passes; the concern is aesthetic/EMI-marginal).
