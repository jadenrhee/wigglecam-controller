# WiggleCam Camera Controller

The RP2040 co-processor board for a [4-lens wigglegram
camera](https://github.com/jadenrhee/wigglecam). It handles the real-time and
analog work the Pi 5 shouldn't: constant-current LED flash with hardware
safety limits, shutter debounce, encoder decoding, battery telemetry (INA219),
and the camera sync trigger. Exposed over I2C (`0x17`) with UART fallback,
on a 2×6 header that lands 1:1 on Pi 5 GPIO pins 1–12.

![Board, top](fab/renders/board_top.png)
![Board, bottom](fab/renders/board_bottom.png)

Signal routing, front copper red and back copper blue, planes hidden:

![Routing view](fab/renders/layout.svg)

| | |
|---|---|
| Board | 76 × 50 mm, 4-layer (Sig / GND / 3V3+VLED / Sig) |
| ERC | 0 errors, 0 warnings |
| DRC | 0 violations, 0 unconnected, at JLCPCB 4-layer rules |
| Verification | 24 measured checks, no FAILs — [report](docs/verification-report.md) |
| Firmware | Pico SDK, builds clean → `camctrl.uf2` |
| Fab | Gerbers, drill, BOM, CPL in [fab/](fab/); LCSC numbers verified |

## Repo layout

| Path | Contents |
|------|----------|
| [hardware/skidl/](hardware/skidl/) | schematic source of record |
| [hardware/scripts/](hardware/scripts/) | layout, fab-output, and verification tooling |
| [hardware/kicad/](hardware/kicad/) | the board (`wigglecam.kicad_pcb`) + custom footprints |
| [hardware/partlist.md](hardware/partlist.md) | part list with reasoning and LCSC numbers |
| [fab/](fab/) | Gerbers, Excellon drill, `bom.csv`, `cpl.csv`, renders |
| [firmware/](firmware/) | I2C register file, flash safety logic, INA219, EC11, WS2812 |
| [enclosure/](enclosure/) | 3D-printable control pod — screen, this PCB, Pi 5 |
| [docs/](docs/) | [Verification](docs/verification-report.md) · [Rationale](docs/design-rationale.md) · [Protocol](docs/protocol.md) |

![pod](enclosure/renders/pod_assembly.png)
