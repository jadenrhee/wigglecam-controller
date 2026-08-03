# WiggleCam Camera Controller

This is the second board for my [4-lens camera](https://github.com/jadenrhee/wigglecam).
The Raspberry Pi runs the camera and does the image work, but it's bad at
things that have to happen at an exact moment, and it can't drive the
flash directly. So this board handles that side of it.

An RP2040 runs the LED flash at a steady current, with the limits built
into the circuit rather than just the code. It also debounces the
shutter so one press counts once, reads the EC11 encoder, and watches
battery voltage and current through an INA219. When a shot fires, it
sends the Pi a pulse the instant the LEDs are at full current.

The Pi drives it over I2C at address 0x17, and the pulse comes back on
its own GPIO line. The header lines up 1:1 with pins 1 to 12 on the Pi.

It isn't fabricated yet. Everything below is from the design files.

![Board, top](fab/renders/board_top.png)
![Board, bottom](fab/renders/board_bottom.png)

Here's the actual routing. Front copper is red, back is blue, and I hid
the power and ground layers so you can see the traces:

![Routing view](fab/renders/layout.svg)

| | |
|---|---|
| Board | 76 x 50 mm, 4 layers |
| Schematic check | 0 errors, 0 warnings |
| Layout check | DRC clean, nothing left unconnected, against JLCPCB's published 4-layer rules |
| My own checks | 24 things I measured off the finished layout, nothing failed. [Report here](docs/verification-report.md) |
| Firmware | builds clean with the Pico SDK |
| Ordering files | Gerbers, drill, BOM, and placement files are in [fab/](fab/) |

## What's in here

| Path | What it is |
|------|----------|
| [hardware/skidl/](hardware/skidl/) | the schematic, written as code |
| [hardware/scripts/](hardware/scripts/) | scripts that build the board, spit out the ordering files, and check my work |
| [hardware/kicad/](hardware/kicad/) | the actual board file, plus footprints I had to draw myself |
| [hardware/partlist.md](hardware/partlist.md) | every part, why I picked it, and where to buy it |
| [fab/](fab/) | the files you'd hand to the board house |
| [firmware/](firmware/) | the C code that runs on the chip |
| [enclosure/](enclosure/) | 3D printable case that holds the screen, this board, and the Pi |
| [docs/](docs/) | [what I checked](docs/verification-report.md), [why I designed it this way](docs/design-rationale.md), and [how the Pi talks to it](docs/protocol.md) |

![pod](enclosure/renders/pod_assembly.png)
