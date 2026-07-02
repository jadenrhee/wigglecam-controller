"""Camera Controller — full circuit connectivity.

Block-by-block wiring with design math inline. Sources:
- "Hardware design with RP2040" (Raspberry Pi, RP-008279-DS) — MCU
  support circuit, crystal values, USB series Rs, decoupling counts.
- RP2040 datasheet §1.4.2 — pin map (transcribed in parts.py).
- TI INA219 datasheet — monitor wiring, address straps.
- ST USBLC6-2 datasheet — flow-through ESD routing.
- Sedra/Smith op-amp current-sink topology for the flash driver.
"""

from skidl import Net, POWER
# NC (the no-connect net) is injected into builtins by skidl on import.

import parts as P

# ---------------------------------------------------------------- nets ----
GND = Net("GND"); GND.drive = POWER
VBUS = Net("VBUS")            # USB-C 5 V (bench power)
PI5V_RAW = Net("PI5V_RAW")    # 5 V from Pi header, pre-protection
VSYS = Net("VSYS")            # diode-OR of VBUS/VLED → logic supply
VSYS.drive = POWER            # driven through the OR diodes (skidl
                              # doesn't propagate drive through parts)
V33 = Net("+3V3")
VLED = Net("VLED")            # 5 V from Pi, post fuse + reverse-FET;
                              # doubles as the flash rail — tapped here, so a
                              # laptop USB port can never source the 2 A
                              # flash pulse (VBUS is diode-isolated)
VBAT_IN = Net("VBAT_IN")      # battery pass-through, shunt high side
VBAT_OUT = Net("VBAT_OUT")    # battery pass-through, shunt low side

for n in (VBUS, PI5V_RAW):
    n.drive = POWER


def power_input():
    """USB-C + Pi 5 V inputs → VSYS; reverse-polarity protected.

    Pi path: PI5V_RAW → F1 (PTC 3 A hold) → Q1 AO3401A (drain=input,
    source=load, gate=GND: body diode conducts at first power, channel
    then enhances with Vgs=-5 V; on reversed input both diode and
    channel block) → VLED → D2 → VSYS.
    USB path: VBUS → D1 → VSYS. The two SS34s diode-OR the rails; VLED
    cannot back-feed the USB port nor VBUS the Pi.
    AO3401A: 30 V/-4 A, Rds(on)≈60 mΩ @ Vgs=-4.5 V → 2.3 A flash-pulse
    peak drops ~0.14 V, dissipates ~0.3 W for 150 ms. Within rating.
    """
    f1 = P.PTC_3A()
    q1 = P.AO3401A()
    d1, d2 = P.SS34(), P.SS34()

    fused = Net("PI5V_FUSED")
    f1[1] += PI5V_RAW; f1[2] += fused
    q1["D"] += fused
    q1["S"] += VLED
    q1["G"] += GND     # gate hard to GND: textbook P-FET reverse guard

    d2["A"] += VLED; d2["K"] += VSYS
    d1["A"] += VBUS; d1["K"] += VSYS

    # input bulk: 2×22 µF X5R 0805 on VSYS + 10 µF on VLED
    for _ in range(2):
        c = P.C("22uF", "0805"); c[1] += VSYS; c[2] += GND
    c = P.C("10uF", "0805"); c[1] += VLED; c[2] += GND


def regulator_3v3():
    """AP2112K-3.3: 600 mA LDO. Load ≈ RP2040 (~50 mA typ, <200 mA
    peak) + INA219 (1 mA) + WS2812 (<20 mA) → <40 % of rating.
    Datasheet-recommended 1 µF/10 µF in/out ceramics + EN tied to VIN."""
    u = P.AP2112K()
    u["VIN"] += VSYS
    u["EN"] += VSYS
    u["GND"] += GND
    u["VOUT"] += V33
    cin = P.C("1uF"); cin[1] += VSYS; cin[2] += GND
    cout = P.C("10uF", "0805"); cout[1] += V33; cout[2] += GND


def mcu_core():
    """RP2040 + crystal + QSPI flash + decoupling, per the official
    hardware design guide's Minimal Design Example."""
    u = P.RP2040()
    fl = P.W25Q128()
    y = P.XTAL_12M()

    # --- power ---
    for pin in u["IOVDD"]:
        pin += V33
    u["USB_VDD"] += V33
    u["ADC_AVDD"] += V33
    u["VREG_VIN"] += V33
    vreg_out = Net("VREG_1V1")
    u["VREG_VOUT"] += vreg_out
    for pin in u["DVDD"]:
        pin += vreg_out
    u["GND"] += GND
    u["TESTEN"] += GND

    # decoupling per guide: 100 nF at each IOVDD (6), USB_VDD,
    # ADC_AVDD; 100 nF ×2 at DVDD; 1 µF at VREG in and out.
    for _ in range(8):
        c = P.C("100nF"); c[1] += V33; c[2] += GND
    for _ in range(2):
        c = P.C("100nF"); c[1] += vreg_out; c[2] += GND
    c = P.C("1uF"); c[1] += V33; c[2] += GND          # VREG_VIN
    c = P.C("1uF"); c[1] += vreg_out; c[2] += GND     # VREG_VOUT
    c = P.C("10uF", "0805"); c[1] += V33; c[2] += GND # bulk

    # --- crystal: guide fig. "Crystal" — 12 MHz CL=10 pF ABM8-272-T3,
    # 15 pF load caps (2×15 pF series → 7.5 pF + ~2.5 pF stray ≈ CL),
    # 1 kΩ series on XOUT to limit drive level.
    xin, xout, xtal_b = Net("XIN"), Net("XOUT"), Net("XOUT_XTAL")
    u["XIN"] += xin
    u["XOUT"] += xout
    r = P.R("1k")
    r[1] += xout; r[2] += xtal_b
    y["X1"] += xin
    y["X2"] += xtal_b
    c1 = P.C("15pF"); c1[1] += xin; c1[2] += GND
    c2 = P.C("15pF"); c2[1] += xtal_b; c2[2] += GND
    for gpin in y["GND"]:
        gpin += GND

    # --- QSPI flash ---
    qspi = {
        "CS": Net("QSPI_SS"),
        "D0": Net("QSPI_SD0"), "D1": Net("QSPI_SD1"),
        "D2": Net("QSPI_SD2"), "D3": Net("QSPI_SD3"),
    }
    u["QSPI_SS_N"] += qspi["CS"]
    u["QSPI_SD0"] += qspi["D0"]
    u["QSPI_SD1"] += qspi["D1"]
    u["QSPI_SD2"] += qspi["D2"]
    u["QSPI_SD3"] += qspi["D3"]
    # 27 Ω series in SCLK at the RP2040 end (source termination on the
    # one unidirectional, always-toggling QSPI line).
    clk_mcu, clk_fl = Net("QSPI_SCLK"), Net("QSPI_SCLK_FL")
    u["QSPI_SCLK"] += clk_mcu
    r_clk = P.R("27R")
    r_clk[1] += clk_mcu; r_clk[2] += clk_fl
    fl["CLK"] += clk_fl
    fl["CS_N"] += qspi["CS"]
    fl["DI_IO0"] += qspi["D0"]
    fl["DO_IO1"] += qspi["D1"]
    fl["WP_IO2"] += qspi["D2"]
    fl["HOLD_IO3"] += qspi["D3"]
    fl["VCC"] += V33
    fl["GND"] += GND
    c = P.C("100nF"); c[1] += V33; c[2] += GND  # at flash VCC
    r_cs = P.R("10k"); r_cs[1] += qspi["CS"]; r_cs[2] += V33

    # BOOTSEL: button pulls QSPI_SS low at reset (guide §2.4).
    # TS-1187A pads 1/2 and 3/4 are the same contact internally —
    # wiring both matches the part and gives routing two entries.
    bootsel = P.TACT()
    bootsel[1] += qspi["CS"]; bootsel[2] += qspi["CS"]
    bootsel[3] += GND; bootsel[4] += GND

    # RUN: 10 k pullup + button to GND + 100 nF debounce
    run = Net("RUN")
    u["RUN"] += run
    r_run = P.R("10k"); r_run[1] += run; r_run[2] += V33
    c_run = P.C("100nF"); c_run[1] += run; c_run[2] += GND
    btn_run = P.TACT()
    btn_run[1] += run; btn_run[2] += run
    btn_run[3] += GND; btn_run[4] += GND

    # spare GPIOs — deliberately unused (ERC-visible intent)
    for g in (8, 9, 14, 15, 17, 18, 19, 20, 21, 23, 24, 26, 27, 28, 29):
        u[f"GPIO{g}" if g < 26 else f"GPIO{g}_ADC{g-26}"] += NC

    # SWD header
    j = P.SWD_HDR()
    j["SWCLK"] += u["SWCLK"]
    j["SWDIO"] += u["SWDIO"]
    j["GND"] += GND

    return u


def usb(u):
    """USB-C device port: CC pulldowns advertise UFP (USB spec §4.5.1.2
    — 5.1 kΩ Rd), USBLC6 in the data path ahead of the MCU, 27.4 Ω
    series Rs at the RP2040 pins per the design guide."""
    j = P.USBC()
    esd = P.USBLC6()

    for pin in j["VBUS"]:
        pin += VBUS
    for pin in j["GND"]:
        pin += GND
    j["SHIELD"] += GND
    rcc1 = P.R("5.1k"); rcc1[1] += j["CC1"]; rcc1[2] += GND
    rcc2 = P.R("5.1k"); rcc2[1] += j["CC2"]; rcc2[2] += GND
    j["SBU1"] += NC
    j["SBU2"] += NC

    # connector → ESD (flow-through) → series R → MCU
    dp_conn, dm_conn = Net("USB_DP_CONN"), Net("USB_DM_CONN")
    j["DP1"] += dp_conn; j["DP2"] += dp_conn
    j["DM1"] += dm_conn; j["DM2"] += dm_conn
    esd["IO1"] += dm_conn
    esd["IO2"] += dp_conn
    esd["VBUS"] += VBUS
    esd["GND"] += GND
    r_dp = P.R("27.4R"); esd["IO2B"] & r_dp & u["USB_DP"]
    r_dm = P.R("27.4R"); esd["IO1B"] & r_dm & u["USB_DM"]




def flash_driver(u):
    """Two-branch op-amp constant-current sink, 1.00 A per branch.

    Per branch: LM358 half drives AO3400A gate; source-sense 0.5 Ω 1 %
    closes the loop: I = VREF/0.5 Ω. VREF from GPIO16 PWM → RC (1 k /
    1 µF, fc≈160 Hz) → 5.6 k/1 k divider → 0–0.5 V for 0–100 % duty.
    100 k pulldown holds VREF at 0 V through boot (RP2040 GPIO defaults
    to hi-Z; pulldown wins → flash cannot fire before firmware).
    Dissipation at 1 A: FET (4.9−3.0−0.5) V ≈ 1.4 W and sense 0.5 W,
    150 ms pulse — pulse-thermal check is a verification-report gate.
    Reservoir 2×470 µF on VLED sources the pulse leading edge.
    """
    op = P.LM358()
    op["V+"] += VSYS       # always powered → defined gate drive
    op["V-"] += GND
    c = P.C("100nF"); c[1] += VSYS; c[2] += GND

    pwm = Net("FLASH_PWM")
    u["GPIO16"] += pwm
    r_pd = P.R("100k"); r_pd[1] += pwm; r_pd[2] += GND
    vref_raw, vref = Net("VREF_RAW"), Net("VREF")
    r_f = P.R("1k"); pwm & r_f & vref_raw
    c_f = P.C("1uF"); c_f[1] += vref_raw; c_f[2] += GND
    r_d1 = P.R("5.6k"); vref_raw & r_d1 & vref
    r_d2 = P.R("1k"); r_d2[1] += vref; r_d2[2] += GND

    for half, (o, inn, inp) in enumerate(
            (("OUT1", "IN1-", "IN1+"), ("OUT2", "IN2-", "IN2+"))):
        q = P.AO3400A()
        r_s = P.R("0.5R 1%", "2512")
        r_gate = P.R("100R")
        r_gpd = P.R("100k")
        c_comp = P.C("1nF")
        jst = P.JST_XH2(f"LED{half+1}")

        op[inp] += vref
        sense = Net(f"SENSE{half+1}")
        op[inn] += sense
        op[o] & r_gate & q["G"]
        r_gpd[1] += q["G"]; r_gpd[2] += GND
        c_comp[1] += op[o]; c_comp[2] += sense
        q["S"] += sense
        r_s[1] += sense; r_s[2] += GND
        jst[1] += VLED               # LED anode feed
        jst[2] += q["D"]             # LED cathode return → sink

    for _ in range(2):
        c = P.C("470uF", "elec"); c[1] += VLED; c[2] += GND
    c = P.C("10uF", "0805"); c[1] += VLED; c[2] += GND


def battery_monitor(u):
    """INA219 high-side on a battery pass-through (JST in → 10 mΩ 2 W
    shunt → JST out). 5 A worst case → 50 mV (PGA ±320 mV range),
    0.25 W in a 2 W part. Address A0=A1=GND → 0x40. Lives on the
    board-internal I2C0 bus (RP2040 master) — isolated from the
    Pi-facing bus."""
    ina = P.INA219()
    sh = P.SHUNT()
    j_in = P.JST_XH2("VBAT_IN")
    j_out = P.JST_XH2("VBAT_OUT")

    j_in[1] += VBAT_IN; j_in[2] += GND
    j_out[1] += VBAT_OUT; j_out[2] += GND
    sh[1] += VBAT_IN; sh[2] += VBAT_OUT
    ina["IN+"] += VBAT_IN
    ina["IN-"] += VBAT_OUT
    ina["VS"] += V33
    ina["GND"] += GND
    ina["A0"] += GND
    ina["A1"] += GND
    c = P.C("100nF"); c[1] += V33; c[2] += GND

    sda0, scl0 = Net("I2C0_SDA"), Net("I2C0_SCL")
    u["GPIO4"] += sda0; ina["SDA"] += sda0
    u["GPIO5"] += scl0; ina["SCL"] += scl0
    for n in (sda0, scl0):
        r = P.R("4.7k"); r[1] += n; r[2] += V33


def controls(u):
    """Shutter (off-board button via JST): 10 k pullup, 1 k series +
    100 nF at the MCU (RC τ=1 ms hardware debounce first stage), TVS
    at the connector — the line leaves the enclosure wall, so it gets
    ESD treatment. EC11 A/B/SW get the same RC conditioning (ALPS
    application note pattern)."""
    j = P.JST_XH2("SHUTTER")
    tvs = P.TVS_5V()
    raw = Net("SHUTTER_RAW"); sig = Net("SHUTTER_N")
    j[1] += raw; j[2] += GND
    tvs[1] += raw; tvs[2] += GND
    r_pu = P.R("10k"); r_pu[1] += raw; r_pu[2] += V33
    r_s = P.R("1k"); raw & r_s & sig
    c = P.C("100nF"); c[1] += sig; c[2] += GND
    u["GPIO10"] += sig

    enc = P.EC11()
    enc["COM"] += GND
    for pad, gpio in (("A", "GPIO11"), ("B", "GPIO12"), ("SW1", "GPIO13")):
        raw_n = Net(f"ENC_{pad}_RAW"); sig_n = Net(f"ENC_{pad}")
        enc[pad] += raw_n
        r_pu = P.R("10k"); r_pu[1] += raw_n; r_pu[2] += V33
        r_s = P.R("1k"); raw_n & r_s & sig_n
        c = P.C("100nF"); c[1] += sig_n; c[2] += GND
        u[gpio] += sig_n
    enc["S2"] += GND

    # WS2812B: VDD through 1N4148 (≈4.3 V) so VIH = 0.7·VDD ≈ 3.0 V —
    # drivable from 3.3 V logic within spec (Worldsemi datasheet).
    led = P.WS2812B()
    d = P.D4148()
    vled5 = Net("WS_VDD")
    vled5.drive = POWER          # fed through the 1N4148 from VSYS
    d["A"] += VSYS; d["K"] += vled5
    led["VDD"] += vled5
    led["VSS"] += GND
    c = P.C("10uF", "0805"); c[1] += vled5; c[2] += GND
    r = P.R("470R")
    din, din_led = Net("WS_DIN"), Net("WS_DIN_R")
    u["GPIO22"] += din
    r[1] += din; r[2] += din_led
    led["DIN"] += din_led
    led["DOUT"] += NC

    # debug LED on GPIO25 (Pico convention)
    dled = P.LED_G(); r_l = P.R("1k")
    u["GPIO25"] & r_l & dled["A"]; dled["K"] += GND


def pi_header(u):
    """2×6 socket seating on Pi 5 GPIO pins 1–12. 330 Ω series on the
    push-pull lines (UART, sync) as contention insurance; I2C is
    open-drain and connects direct (Pi 5 has 1.8 kΩ pullups on
    GPIO2/3 — board adds none)."""
    j = P.PI_HDR()
    j["P1"] += NC                # Pi 3V3 — reference only, unused
    j["P2"] += PI5V_RAW
    j["P4"] += PI5V_RAW
    j["P6"] += GND
    j["P9"] += GND
    j["P7"] += NC                # Pi GPIO4 — spare, unused

    sda, scl = Net("PI_SDA"), Net("PI_SCL")
    j["P3"] += sda; u["GPIO2"] += sda   # Pi master ↔ RP2040 I2C1 slave
    j["P5"] += scl; u["GPIO3"] += scl

    def series(name, a, b):
        r = P.R("330R")
        n1, n2 = Net(name + "_HDR"), Net(name)
        a += n1; r[1] += n1; r[2] += n2; b += n2

    series("UART_RX", j["P8"], u["GPIO1"])    # Pi TXD → RP2040 RX
    series("UART_TX", j["P10"], u["GPIO0"])   # RP2040 TX → Pi RXD
    series("CAM_SYNC", j["P11"], u["GPIO6"])  # sync pulse → Pi GPIO17
    series("SPARE_IO", j["P12"], u["GPIO7"])  # ↔ Pi GPIO18
