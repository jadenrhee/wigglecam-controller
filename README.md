# WiggleCam Camera Controller

A 4-layer RP2040 co-processor board for a 4-lens wigglegram camera.
It sits between a Raspberry Pi 5 (which does all capture and image
processing) and the camera's physical controls, handling the
real-time/analog work: constant-current LED flash driving, shutter
debounce, rotary-encoder decoding, battery monitoring (INA219), and a
camera-sync trigger line — exposed to the Pi over I2C (primary) and
UART (fallback) through a header that seats directly on Pi 5 GPIO
pins 1–12.

Designed end to end using modern automated design tooling: schematic
as code (SKiDL), scripted placement and constrained routing
(KiCad/pcbnew + Freerouting), DRC-gated fabrication outputs for
JLCPCB, and a programmatic verification report that measures the
finished layout against published design guidance (RP2040 hardware
design guide, IPC-2221, JLCPCB capabilities).

**Status: phase 0 — part list under review.** See
[docs/plan.md](docs/plan.md) for the full execution plan and
[hardware/partlist.md](hardware/partlist.md) for the LCSC
stock-verified part list.

## Repository layout

| Path | Contents |
|------|----------|
| `hardware/` | SKiDL schematic source, KiCad project, netlist, layout-verification scripts |
| `fab/` | Gerbers, drill, BOM, CPL, board renders |
| `firmware/` | RP2040 firmware (Pico SDK, C): I2C-slave command set for the Pi |
| `docs/` | plan, design rationale, verification report, human review checklist, protocol |
