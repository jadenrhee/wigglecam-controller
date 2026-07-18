# Part list — verified against LCSC stock, 2026-07-02

Every named part below was individually confirmed present and in stock
at LCSC on the date above (links in each row). Prices are the LCSC
from-price at qty 1; re-check stock at order time — it moves.
"JLC class" (basic vs extended, affects assembly setup fees) should be
confirmed in the JLCPCB BOM tool at order time; known classes noted.

**2026-07-03 update:** refdes corrected to match the routed board
(`fab/bom.csv` is the authoritative refdes source), generic-passive
picks added (each number verified against its LCSC product page for
value + package), and the 470 µF reservoir got its concrete pick.

## MCU core

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U2 | [RP2040](https://www.lcsc.com/product-detail/C2040.html) | QFN-56 7×7 | **C2040** | 0.70 | in stock; support circuit per the official *Hardware design with RP2040* guide |
| U3 | [W25Q128JVSIQ](https://www.lcsc.com/product-detail/NOR-FLASH_Winbond-Elec-W25Q128JVSIQ_C97521.html) 16 MB QSPI | SOIC-8 | **C97521** | 0.47 | in stock; the flash used on the Pico |
| Y1 | [ABM8-272-T3](https://www.lcsc.com/product-detail/C20625731.html) 12 MHz, CL = 10 pF | 3225 | **C20625731** | 0.15 | in stock; the exact crystal from the RP2040 guide's minimal example → 15 pF load caps + 1 kΩ series R on XOUT, straight from the guide |
| SW1, SW2 | [TS-1187A-B-A-B](https://www.lcsc.com/product-detail/C318884.html) BOOTSEL + RUN | SMD 5.1 mm | **C318884** | 0.01 | in stock, JLC **basic**. Known deviation: no 1 kΩ in series with the BOOTSEL button (reference design has one) |
| J1 | SWD header 1×3, 2.54 mm | THT | generic | — | hand-solder; any vendor |

## Power

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U1 | [AP2112K-3.3TRG1](https://www.lcsc.com/product-detail/C51118.html) 600 mA LDO | SOT-23-5 | **C51118** | 0.09 | in stock (131 k units) |
| Q1 | [AO3401A](https://www.lcsc.com/product-detail/C15127.html) P-ch, reverse-polarity protection | SOT-23 | **C15127** | 0.05 | in stock, JLC **basic**; polarity-critical in the JLC preview |
| D1, D2 | [SS34](https://www.lcsc.com/product-detail/C8678.html) 3 A Schottky, VBUS/VLED diode-OR | SMA | **C8678** | 0.03 | cathode bands polarity-critical in the JLC preview |
| F1 | [BSMD1812-300-16V](https://www.lcsc.com/product-detail/C883162.html) PTC, 3 A hold | 1812 | **C883162** | — | Pi-5V input fuse |

## USB-C

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| J2 | [TYPE-C-31-M-12](https://www.lcsc.com/product-detail/USB-Type-C_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.html) 16-pin | SMD+THT shell | **C165948** | 0.10 | in stock; the de-facto hobby USB-C jack, hand-solderable |
| U4 | [USBLC6-2SC6](https://www.lcsc.com/product-detail/C7519.html) ESD array | SOT-23-6 | **C7519** | 0.08 | in stock; in D± path before the MCU |
| R7, R8 | 27 Ω 1 % D± series | 0603 | **C25190** | — | guide-nominal 27 Ω (Pico's 27.4 Ω is the E96 neighbour — equivalent at USB-FS); JLC **basic** |

## Flash driver (constant-current, discrete — see decision note below)

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| U5 | [LM358DR2G](https://www.lcsc.com/product-detail/General-Purpose-Amplifiers_ON-Semiconductor-LM358DR2G_C7950.html) dual op-amp | SOIC-8 | **C7950** | 0.03 | in stock, JLC **basic**; one half per LED branch |
| Q2, Q3 | [AO3400A](https://www.lcsc.com/product-detail/MOSFET_AOS_AO3400A_AO3400A_C20917.html) N-ch sink FETs | SOT-23 | **C20917** | 0.05 | in stock, JLC **basic**; 150 ms pulse-thermal disposition in the verification report |
| R13, R16 | [RTT25R500FTE](https://www.lcsc.com/product-detail/C105149.html) 0.5 Ω 1 % 1 W sense | 2512 | **C105149** | 0.02 | 1 A per branch → 0.5 V sense; 0.5 W only during the ≤150 ms pulse |
| C27, C28 | [6TPE470MI](https://www.lcsc.com/product-detail/Tantalum-Capacitors_PANASONIC_C402828.html) 470 µF 6.3 V 18 mΩ POSCAP | EIA-7343 | **C402828** | — | the low-ESR polymer reservoir the sizing math assumes; 6.3 V on a ~4.9 V rail ≈ 78 % — inside polymer derating practice |
| J3, J4 | [B2B-XH-A(LF)(SN)](https://www.lcsc.com/product-detail/C158012.html) JST-XH 2-pin, LED branches out | THT | **C158012** | — | genuine JST; LEDs (2× XP-G3 stars) live off-board at the flash window; hand-solder |

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
| R19 | [GX2512-2W-10mR-1%](https://jlcpcb.com/partdetail/Milliohm-GX2512_2W_10mR_1/C500718) shunt | 2512 2 W | **C500718** | — | in stock; 5 A → 50 mV drop, 0.25 W — inside INA219 ±320 mV range |
| J5, J6 | [B2B-XH-A(LF)(SN)](https://www.lcsc.com/product-detail/C158012.html) JST-XH battery pass-through (in/out) | THT | **C158012** | — | battery lead routes through the shunt; can be left unpopulated with a solder-jumper bypass; hand-solder |

## Controls & status

| Ref | Part | Package | LCSC | ~$ | Notes |
|-----|------|---------|------|----|-------|
| J7, D3 | Shutter via [B2B-XH-A](https://www.lcsc.com/product-detail/C158012.html) JST-XH (panel button off-board) + RC debounce + [PESD5V0S1BA,115](https://www.lcsc.com/product-detail/C19224.html) TVS | THT / SOD-323 | **C158012** / **C19224** | — | TVS in stock (328 k units), Nexperia original |
| SW3 | [EC11E18244AU](https://www.lcsc.com/product-detail/C202365.html) rotary encoder w/ push | THT | **C202365** | — | in stock, genuine ALPS; shaft length vs enclosure = TODO(measure); hand-solder |
| D4 | [WS2812B-B/T](https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_Worldsemi-WS2812B-B-T_C2761795.html) status RGB | 5050 | **C2761795** | 0.05 | in stock at LCSC; reports exist of JLC assembly rejecting the 5050 variant — hand-solder fallback (easy). VDD fed through a 1N4148 drop (~4.3 V) so 3.3 V data meets the 0.7·VDD input threshold |
| D5 | [1N4148W](https://www.lcsc.com/product-detail/C81598.html) WS2812 VDD drop | SOD-123 | **C81598** | — | |
| D6 | [Green LED](https://www.lcsc.com/product-detail/C72043.html) debug, GPIO25 | 0603 | **C72043** | — | |
| J8 | 2×6 female socket, 2.54 mm — Pi interface | THT | generic | — | maps 1:1 onto Pi 5 GPIO pins 1–12, see below; hand-solder; any vendor |

## Generic passives — JLC picks (value + package verified 2026-07-03)

All 0603/0805 lines are JLC-basic-class commodity parts; refdes
groupings match `fab/bom.csv`.

| Value | Refs | Package | LCSC | Part |
|-------|------|---------|------|------|
| 100 nF X7R 50 V | C6–C15, C21–C23, C30–C34 (×18) | 0603 | **C14663** | YAGEO CC0603KRX7R9BB104 |
| 1 µF X5R | C4, C16, C17, C24 | 0603 | **C15849** | Samsung CL10A105KB8NNNC |
| 15 pF C0G 50 V (crystal load) | C19, C20 | 0603 | **C1644** | Samsung CL10C150JB8NNNC |
| 1 nF X7R (comp) | C25, C26 | 0603 | **C1588** | Samsung CL10B102KB8NNNC |
| 10 µF X5R 25 V | C3, C5, C18, C29, C35 | 0805 | **C15850** | Samsung CL21A106KAYNNNE |
| 22 µF X5R 25 V (VSYS bulk) | C1, C2 | 0805 | **C45783** | Samsung CL21A226MAQNNNE |
| 27 Ω 1 % | R2, R7, R8 | 0603 | **C25190** | UNI-ROYAL |
| 100 Ω 1 % | R14, R17 | 0603 | **C22775** | UNI-ROYAL 0603WAF1000T5E |
| 330 Ω 1 % | R32–R35 | 0603 | **C23138** | UNI-ROYAL 0603WAF3300T5E |
| 470 Ω 1 % | R30 | 0603 | **C23179** | UNI-ROYAL 0603WAF4700T5E |
| 1 kΩ 1 % | R1, R10, R12, R23, R25, R27, R29, R31 | 0603 | **C21190** | UNI-ROYAL 0603WAF1001T5E |
| 4.7 kΩ 1 % | R20, R21 | 0603 | **C23162** | UNI-ROYAL 0603WAF4701T5E |
| 5.1 kΩ 1 % | R5, R6 | 0603 | **C23186** | UNI-ROYAL 0603WAF5101T5E |
| 5.6 kΩ 1 % | R11 | 0603 | **C23189** | UNI-ROYAL 0603WAF5601T5E |
| 10 kΩ 1 % | R3, R4, R22, R24, R26, R28 | 0603 | **C25804** | UNI-ROYAL 0603WAF1002T5E |
| 100 kΩ 1 % | R9, R15, R18 | 0603 | **C25803** | UNI-ROYAL 0603WAF1003T5E |

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
