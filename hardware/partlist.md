# Part list — verified against LCSC stock, 2026-07-02

Every named part below was individually confirmed present and in stock
at LCSC on the date above (links in each row). Prices are the LCSC
from-price at qty 1; re-check stock at order time — it moves.
"JLC class" (basic vs extended, affects assembly setup fees) should be
confirmed in the JLCPCB BOM tool at order time; known classes noted.

## MCU core

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U1 | [RP2040](https://www.lcsc.com/product-detail/C2040.html) | QFN-56 7×7 | **C2040** | 0.70 | in stock; support circuit per the official *Hardware design with RP2040* guide |
| U2 | [W25Q128JVSIQ](https://www.lcsc.com/product-detail/NOR-FLASH_Winbond-Elec-W25Q128JVSIQ_C97521.html) 16 MB QSPI | SOIC-8 | **C97521** | 0.47 | in stock; the flash used on the Pico |
| Y1 | [ABM8-272-T3](https://www.lcsc.com/product-detail/C20625731.html) 12 MHz, CL = 10 pF | 3225 | **C20625731** | 0.15 | in stock; the exact crystal from the RP2040 guide's minimal example → 15 pF load caps + 1 kΩ series R on XOUT, straight from the guide |
| — | Load caps 15 pF C0G, decoupling 100 nF ×~10, 1 µF ×3 | 0603 | generic | — | JLC basic passives |
| SW1, SW2 | [TS-1187A-B-A-B](https://www.lcsc.com/product-detail/C318884.html) BOOTSEL + RUN | SMD 5.1 mm | **C318884** | 0.01 | in stock, JLC **basic** |

## Power

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U3 | [AP2112K-3.3TRG1](https://www.lcsc.com/product-detail/C51118.html) 600 mA LDO | SOT-23-5 | **C51118** | 0.09 | in stock (131 k units) |
| Q1 | [AO3401A](https://www.lcsc.com/product-detail/C15127.html) P-ch, reverse-polarity protection | SOT-23 | **C15127** | 0.05 | in stock, JLC **basic** |
| — | Input bulk 22 µF ×2 (0805/1206 MLCC), 10 µF out | — | generic | — | |

## USB-C

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| J1 | [TYPE-C-31-M-12](https://www.lcsc.com/product-detail/USB-Type-C_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.html) 16-pin | SMD+THT shell | **C165948** | 0.10 | in stock; the de-facto hobby USB-C jack, hand-solderable |
| U4 | [USBLC6-2SC6](https://www.lcsc.com/product-detail/C7519.html) ESD array | SOT-23-6 | **C7519** | 0.08 | in stock; in D± path before the MCU |
| — | 2× 5.1 kΩ CC pulldowns, 2× 27.4 Ω D± series | 0603 | generic | — | per RP2040 guide |

## Flash driver (constant-current, discrete — see decision note below)

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U5 | [LM358DR2G](https://www.lcsc.com/product-detail/General-Purpose-Amplifiers_ON-Semiconductor-LM358DR2G_C7950.html) dual op-amp | SOIC-8 | **C7950** | 0.03 | in stock, JLC **basic**; one half per LED branch |
| Q2, Q3 | [AO3400A](https://www.lcsc.com/product-detail/MOSFET_AOS_AO3400A_AO3400A_C20917.html) N-ch sink FETs | SOT-23 | **C20917** | 0.05 | in stock, JLC **basic**; 150 ms pulse-thermal calc is a mandatory verification item — fallback is a SOT-89/DPAK part if the math says no |
| R_sns | 0.5 Ω 1 % 1206/2010, one per branch | — | generic | — | 1 A per branch → 0.5 V sense |
| C_res | Reservoir: polymer/electrolytic bulk (≥2× 470 µF 6.3 V) | SMD | generic | — | sizing math in verification report |
| J2, J3 | JST-XH 2-pin, LED branches out | THT | generic | — | LEDs (2× XP-G3 stars) live off-board at the flash window |

**Decision — discrete sink over AL8860:** the AL8860 is a *buck* driver,
so from a 5 V rail it cannot drive a 2–3-LED series string (6–9 V);
you'd need one AL8860 + inductor per LED — all JLC extended parts. The
discrete sink (LM358 + AO3400A + sense R, all JLC basic) drives two
parallel 1 A branches from 5 V, is cheaper, and regulates true constant
current. Reference for the sinks comes from an RP2040 PWM pin through
an RC filter (adjustable flash power); a 100 kΩ pulldown on that node
holds the reference at 0 V during boot — the flash physically cannot
fire until firmware drives it.

## Battery monitor

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U6 | [INA219AIDCNR](https://www.lcsc.com/product-detail/C87469.html) | SOT-23-8 | **C87469** | 0.33 | in stock; on an internal I2C bus (RP2040 master), separate from the Pi-facing bus |
| R_sh | [GX2512-2W-10mR-1%](https://jlcpcb.com/partdetail/Milliohm-GX2512_2W_10mR_1/C500718) shunt | 2512 2 W | **C500718** | — | in stock; 5 A → 50 mV drop, 0.25 W — inside INA219 ±320 mV range |
| J4, J5 | JST-XH 2-pin battery pass-through (in/out) | THT | generic | — | battery lead routes through the shunt; can be left unpopulated with a solder-jumper bypass |

## Controls & status

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| SW3 | Shutter button via JST-XH 2-pin (panel button is off-board) + RC debounce + [PESD5V0S1BA,115](https://www.lcsc.com/product-detail/C19224.html) TVS | SOD-323 | **C19224** | — | in stock (328 k units), Nexperia original |
| ENC1 | [EC11E18244AU](https://www.lcsc.com/product-detail/C202365.html) rotary encoder w/ push | THT | **C202365** | — | in stock, genuine ALPS; shaft length vs enclosure = TODO(measure) |
| D1 | [WS2812B-B/T](https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_Worldsemi-WS2812B-B-T_C2761795.html) status RGB | 5050 | **C2761795** | 0.05 | in stock at LCSC; reports exist of JLC assembly rejecting the 5050 variant — hand-solder fallback (easy). VDD fed through a 1N4148 drop (~4.3 V) so 3.3 V data meets the 0.7·VDD input threshold |
| J6 | 2×6 female socket, 2.54 mm — Pi interface | THT | generic | — | maps 1:1 onto Pi 5 GPIO pins 1–12, see below |

## Pi interface header (2×6, matches Pi 5 pins 1–12 exactly)

| Pi pin | Signal | Board use |
|--------|--------|-----------|
| 1 | 3V3 | reference only (not a power source) |
| 2, 4 | 5V | board power in (through Q1 reverse protection) |
| 3 / 5 | GPIO2 SDA / GPIO3 SCL | I2C — RP2040 slave @ 0x17. Pi has 1.8 kΩ hardware pullups on these pins, so the board adds none (optional solder-jumper 4.7 k for standalone bench use) |
| 6, 9 | GND | |
| 7 | GPIO4 | spare |
| 8 / 10 | GPIO14 TXD / GPIO15 RXD | UART fallback link |
| 11 | GPIO17 | **camera-sync trigger** (RP2040 → Pi input) |
| 12 | GPIO18 | spare / flash-inhibit |
