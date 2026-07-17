# Design rationale — block by block

Datasheets: [RP2040](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) ·
[Hardware design with RP2040](https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf) ·
[W25Q128JV](https://www.winbond.com/resource-files/w25q128jv%20revf%2003272018%20plus.pdf) ·
[AP2112](https://www.diodes.com/assets/Datasheets/AP2112.pdf) ·
[USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) ·
[INA219](https://www.ti.com/lit/ds/symlink/ina219.pdf) ·
[AO3400A](http://aosmd.com/pdfs/datasheet/AO3400A.pdf) /
[AO3401A](http://aosmd.com/pdfs/datasheet/AO3401A.pdf) ·
[LM358](https://www.ti.com/lit/ds/symlink/lm358.pdf)

## MCU core
Bare RP2040 with the support circuit taken directly from the official
guide's Minimal Design Example: 12 MHz ABM8-272-T3 (CL = 10 pF → two
15 pF C0G load caps, 1 kΩ series on XOUT limits drive), W25Q128JVSIQ
QSPI flash 9 mm away with a 27 Ω series option in SCLK, 100 nF at
every IOVDD/USB_VDD/ADC_AVDD, two 100 nF + 1 µF on the internal
1.1 V regulator, BOOTSEL (QSPI_SS to GND) and RUN buttons wired on
diagonal tact-switch pads so either internal pairing convention works.

## Power input
Pi 5 V enters through a 3 A PTC and an AO3401A P-FET oriented
drain-to-input (body diode conducts at first power, channel then
enhances; reversed input blocks). The post-FET node **is** the flash
rail (VLED) and feeds the logic rail through one of two SS34 OR-diodes
— the other comes from USB VBUS, so a bench USB port can never be
asked for the 2 A flash pulse. AP2112K-3.3 (600 mA) supplies logic
with 3× margin.

## Flash driver
Two independent op-amp constant-current sinks (½ LM358 + AO3400A +
0.5 Ω sense each): I = VREF / 0.5 Ω, VREF = 0–0.5 V from an RC-filtered
RP2040 PWM through a 5.6k/1k divider, with a 100 kΩ pulldown that
holds the reference at zero through reset — the flash cannot fire
until firmware commands it. An AL8860 buck was rejected because from
a 5 V rail it cannot drive a series LED string (Vf 6–9 V) — one
driver+inductor per LED, all JLC extended parts. Worst-case sink
dissipation ≈1.4 W for ≤150 ms (firmware-capped, plus 800 ms
cooldown): within the SOT-23 single-pulse transient envelope with
margin (AO3400A Zth curve). Reservoir: 2× 470 µF low-ESR polymer on
the VLED island.

## Battery monitor
INA219 high-side on a JST-in/JST-out pass-through with a 10 mΩ 2 W
shunt (5 A → 50 mV, inside the ±320 mV PGA range). It lives on a
separate internal I2C bus (RP2040 master) so its traffic never
touches the Pi-facing bus; firmware caches readings.

## Controls & status
Shutter and encoder lines get 10 k pullups + 1 k series + 100 nF RC
(hardware debounce first stage) and the shutter — which leaves the
enclosure — gets a PESD5V0S1BA TVS at the connector. WS2812B runs its
VDD through a 1N4148W drop (~4.3 V) so 3.3 V logic meets the 0.7·VDD
input threshold. One green LED on GPIO25 keeps the Pico debugging
convention.

## Pi interface
2×6 socket matching Pi 5 GPIO pins 1–12 exactly: I2C (slave 0x17),
UART, camera-sync out (→ Pi GPIO17), event/ATTN line (→ Pi GPIO18),
5 V in, grounds. 330 Ω series resistors on the push-pull lines as
contention insurance; the I2C lines connect directly because the Pi 5
carries 1.8 kΩ hardware pullups.

## Board & layout strategy
76×50 mm 4-layer (JLC04161H-7628): L1 signal, L2 solid GND, L3 3V3
plane + a tightly-drawn VLED island (west entry lobe → 1.6 mm conduit
finger → reservoir pocket → right strip to the LED connectors), L4
signal. The sensitive geometry was routed first and by hand — QSPI
nested-lane fanout, crystal, the USB pair with its mirror-pad B.Cu
jumpers, power entry, battery path, LED returns, plane fanouts — with
explicit crossing-free geometry; the low-speed GPIO were then worked
in around it, kept off the inner planes. Everything gates through
`kicad-cli drc --refill-zones` at JLCPCB capability limits — the
final board reports **0 violations, 0 unconnected** (see
docs/verification-report.md).
