# WiggleCam Camera Controller

A 4-layer RP2040 co-processor board for a 4-lens wigglegram camera.
It sits between a Raspberry Pi 5 — which does all capture and image
processing — and the camera's physical hardware, handling the
real-time and analog work: constant-current LED flash driving with
hardware-enforced safety limits, shutter debounce, rotary-encoder
decoding, battery telemetry (INA219), and a camera-sync trigger line.
All of it is exposed to the Pi over I2C (slave `0x17`, primary) and
UART (fallback) through a 2×6 header that maps 1:1 onto Pi 5 GPIO
pins 1–12.

![Board, top](fab/renders/board_top.png)
![Board, bottom](fab/renders/board_bottom.png)

Signal routing — front copper in red, back copper in blue, with the
GND and power planes on the inner layers hidden for readability:

![Routing view](fab/renders/layout.svg)

## Status

| Stage | Result |
|-------|--------|
| Schematic | ERC clean — 0 errors, 0 warnings |
| Layout | 76×50 mm 4-layer (Sig / GND / 3V3+VLED / Sig), fully routed |
| DRC (JLCPCB 4-layer rules, zones refilled) | **0 violations, 0 unconnected** |
| Verification | 24 measured checks against published design guidance: no FAILs, deviations analyzed — [report](docs/verification-report.md) |
| Firmware (Pico SDK, C) | builds clean → `camctrl.uf2` |
| Fab outputs | Gerbers + drill + BOM + CPL in [fab/](fab/); every SMT line carries a verified LCSC number |

## Repository layout

| Path | Contents |
|------|----------|
| [hardware/skidl/](hardware/skidl/) | schematic as code — one module per block, datasheet pin maps inline |
| [hardware/scripts/](hardware/scripts/) | layout, fab-output, and verification scripts (pcbnew API) |
| [hardware/kicad/](hardware/kicad/) | the routed board (`wigglecam.kicad_pcb`) + custom footprints |
| [hardware/partlist.md](hardware/partlist.md) | LCSC stock-verified part list, with the reasoning per part |
| [hardware/drc-final.json](hardware/drc-final.json) | machine-readable final DRC result |
| [fab/](fab/) | Gerbers (JLCPCB layer set), Excellon drill, `bom.csv`, `cpl.csv`, renders |
| [firmware/](firmware/) | Pico-SDK C firmware: I2C register file, flash safety logic, INA219, EC11, WS2812 |
| [docs/](docs/) | [verification report](docs/verification-report.md) · [design rationale](docs/design-rationale.md) · [Pi protocol](docs/protocol.md) |

## Enclosure

[enclosure/](enclosure/) holds a two-shell 3D-printable control pod
(screen + this PCB + Pi 5) whose PCB-facing features are generated
from the routed board file, with print-ordering instructions for
JLC3DP/Craftcloud — see [enclosure/README.md](enclosure/README.md).

![pod](enclosure/renders/pod_assembly.png)
