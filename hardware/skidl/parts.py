"""Part templates for the Camera Controller board.

Every part is defined from scratch with an explicit pin map transcribed
from its datasheet (cited per part) instead of relying on symbol-library
lookups — a scripted flow must not depend on library naming that can
drift. Footprint strings reference the official KiCad 9 footprint
libraries; their existence on disk is asserted by the layout script
before placement, and anything missing is generated into a local
wigglecam.pretty library.

LCSC numbers were stock-verified 2026-07-02 (hardware/partlist.md).
"""

from skidl import Part, Pin, SKIDL, TEMPLATE, NETLIST

IN = Pin.types.INPUT
OUT = Pin.types.OUTPUT
BI = Pin.types.BIDIR
PAS = Pin.types.PASSIVE
PWRIN = Pin.types.PWRIN
PWROUT = Pin.types.PWROUT
NOCON = Pin.types.NOCONNECT


def _p(name, ref_prefix, footprint, pins, lcsc="", value="", template=True):
    """Templates for fixed parts (instantiate by calling them); the
    R()/C()/connector factory functions below build live instances."""
    part = Part(tool=SKIDL, name=name, ref_prefix=ref_prefix,
                dest=TEMPLATE if template else NETLIST,
                footprint=footprint, pins=pins)
    part.fields["LCSC"] = lcsc
    if value:
        part.value = value
    return part


# --------------------------------------------------------------------------
# RP2040, QFN-56.  Pin map: RP2040 datasheet §1.4.2 "Pin locations"
# (https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf).
# Support circuitry follows "Hardware design with RP2040", Minimal
# Design Example (https://datasheets.raspberrypi.com/rp2040/
# hardware-design-with-rp2040.pdf).
# --------------------------------------------------------------------------
RP2040 = _p(
    "RP2040", "U",
    "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm",
    lcsc="C2040", value="RP2040",
    pins=[
        Pin(num="1", name="IOVDD", func=PWRIN),
        *[Pin(num=str(n), name=f"GPIO{n-2}", func=BI) for n in range(2, 10)],
        Pin(num="10", name="IOVDD", func=PWRIN),
        *[Pin(num=str(n), name=f"GPIO{n-3}", func=BI) for n in range(11, 19)],
        Pin(num="19", name="TESTEN", func=IN),
        Pin(num="20", name="XIN", func=IN),
        Pin(num="21", name="XOUT", func=OUT),
        Pin(num="22", name="IOVDD", func=PWRIN),
        Pin(num="23", name="DVDD", func=PWRIN),
        Pin(num="24", name="SWCLK", func=IN),
        Pin(num="25", name="SWDIO", func=BI),
        Pin(num="26", name="RUN", func=IN),
        *[Pin(num=str(n), name=f"GPIO{n-11}", func=BI) for n in range(27, 33)],
        Pin(num="33", name="IOVDD", func=PWRIN),
        *[Pin(num=str(n), name=f"GPIO{n-12}", func=BI) for n in range(34, 38)],
        *[Pin(num=str(n), name=f"GPIO{n-12}_ADC{n-38}", func=BI)
          for n in range(38, 42)],
        Pin(num="42", name="IOVDD", func=PWRIN),
        Pin(num="43", name="ADC_AVDD", func=PWRIN),
        Pin(num="44", name="VREG_VIN", func=PWRIN),
        Pin(num="45", name="VREG_VOUT", func=PWROUT),
        Pin(num="46", name="USB_DM", func=BI),
        Pin(num="47", name="USB_DP", func=BI),
        Pin(num="48", name="USB_VDD", func=PWRIN),
        Pin(num="49", name="IOVDD", func=PWRIN),
        Pin(num="50", name="DVDD", func=PWRIN),
        Pin(num="51", name="QSPI_SD3", func=BI),
        Pin(num="52", name="QSPI_SCLK", func=OUT),
        Pin(num="53", name="QSPI_SD0", func=BI),
        Pin(num="54", name="QSPI_SD2", func=BI),
        Pin(num="55", name="QSPI_SD1", func=BI),
        Pin(num="56", name="QSPI_SS_N", func=OUT),
        Pin(num="57", name="GND", func=PWRIN),   # exposed pad
    ],
)

# W25Q128JVSIQ, SOIC-8 208 mil. Pin map: Winbond W25Q128JV datasheet §3.1.
W25Q128 = _p(
    "W25Q128JVSIQ", "U",
    "Package_SO:SOIC-8_5.23x5.23mm_P1.27mm",
    lcsc="C97521", value="W25Q128JVSIQ",
    pins=[
        Pin(num="1", name="CS_N", func=IN),
        Pin(num="2", name="DO_IO1", func=BI),
        Pin(num="3", name="WP_IO2", func=BI),
        Pin(num="4", name="GND", func=PWRIN),
        Pin(num="5", name="DI_IO0", func=BI),
        Pin(num="6", name="CLK", func=IN),
        Pin(num="7", name="HOLD_IO3", func=BI),
        Pin(num="8", name="VCC", func=PWRIN),
    ],
)

# ABM8-272-T3 12 MHz, CL=10 pF. 3225 4-pad: pins 1/3 crystal, 2/4 GND.
XTAL_12M = _p(
    "ABM8-272-T3", "Y",
    "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    lcsc="C20625731", value="12MHz",
    pins=[
        Pin(num="1", name="X1", func=PAS),
        Pin(num="2", name="GND", func=PWRIN),
        Pin(num="3", name="X2", func=PAS),
        Pin(num="4", name="GND", func=PWRIN),
    ],
)

# AP2112K-3.3, SOT-23-5. Pin map: Diodes Inc AP2112 datasheet.
AP2112K = _p(
    "AP2112K-3.3", "U",
    "Package_TO_SOT_SMD:SOT-23-5",
    lcsc="C51118", value="AP2112K-3.3",
    pins=[
        Pin(num="1", name="VIN", func=PWRIN),
        Pin(num="2", name="GND", func=PWRIN),
        Pin(num="3", name="EN", func=IN),
        Pin(num="4", name="NC", func=NOCON),
        Pin(num="5", name="VOUT", func=PWROUT),
    ],
)

# USBLC6-2SC6, SOT-23-6. Pin map: ST USBLC6-2 datasheet (flow-through:
# line enters pin 1/3, exits pin 6/4).
USBLC6 = _p(
    "USBLC6-2SC6", "U",
    "Package_TO_SOT_SMD:SOT-23-6",
    lcsc="C7519", value="USBLC6-2SC6",
    pins=[
        Pin(num="1", name="IO1", func=PAS),
        Pin(num="2", name="GND", func=PWRIN),
        Pin(num="3", name="IO2", func=PAS),
        Pin(num="4", name="IO2B", func=PAS),
        Pin(num="5", name="VBUS", func=PWRIN),
        Pin(num="6", name="IO1B", func=PAS),
    ],
)

# USB-C receptacle, HRO TYPE-C-31-M-12 (16 pin, USB 2.0). Pad names
# match KiCad's USB_C_Receptacle_HRO_TYPE-C-31-M-12 footprint; the
# layout script asserts the actual pad set and fails loudly on drift.
USBC = _p(
    "TYPE-C-31-M-12", "J",
    "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    lcsc="C165948", value="USB-C",
    pins=[
        Pin(num="A1", name="GND", func=PWRIN),
        Pin(num="A4", name="VBUS", func=PWRIN),
        Pin(num="A5", name="CC1", func=BI),
        Pin(num="A6", name="DP1", func=BI),
        Pin(num="A7", name="DM1", func=BI),
        Pin(num="A8", name="SBU1", func=NOCON),
        Pin(num="B1", name="GND", func=PWRIN),
        Pin(num="B4", name="VBUS", func=PWRIN),
        Pin(num="B5", name="CC2", func=BI),
        Pin(num="B6", name="DP2", func=BI),
        Pin(num="B7", name="DM2", func=BI),
        Pin(num="B8", name="SBU2", func=NOCON),
        Pin(num="S1", name="SHIELD", func=PAS),
    ],
)

# AO3400A N-ch / AO3401A P-ch, SOT-23: 1=G 2=S 3=D (AOS datasheets).
AO3400A = _p(
    "AO3400A", "Q", "Package_TO_SOT_SMD:SOT-23",
    lcsc="C20917", value="AO3400A",
    pins=[Pin(num="1", name="G", func=IN),
          Pin(num="2", name="S", func=PAS),
          Pin(num="3", name="D", func=PAS)],
)
AO3401A = _p(
    "AO3401A", "Q", "Package_TO_SOT_SMD:SOT-23",
    lcsc="C15127", value="AO3401A",
    pins=[Pin(num="1", name="G", func=IN),
          Pin(num="2", name="S", func=PAS),
          Pin(num="3", name="D", func=PAS)],
)

# LM358, SOIC-8. Pin map: TI/onsemi LM358 datasheet.
LM358 = _p(
    "LM358DR2G", "U", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    lcsc="C7950", value="LM358",
    pins=[
        Pin(num="1", name="OUT1", func=OUT),
        Pin(num="2", name="IN1-", func=IN),
        Pin(num="3", name="IN1+", func=IN),
        Pin(num="4", name="V-", func=PWRIN),
        Pin(num="5", name="IN2+", func=IN),
        Pin(num="6", name="IN2-", func=IN),
        Pin(num="7", name="OUT2", func=OUT),
        Pin(num="8", name="V+", func=PWRIN),
    ],
)

# INA219AIDCNR, SOT-23-8. Pin map: TI INA219 datasheet (DCN package):
# 1 IN+, 2 IN-, 3 GND, 4 VS, 5 SCL, 6 SDA, 7 A0, 8 A1.
INA219 = _p(
    "INA219AIDCNR", "U", "Package_TO_SOT_SMD:SOT-23-8",
    lcsc="C87469", value="INA219",
    pins=[
        Pin(num="1", name="IN+", func=PAS),
        Pin(num="2", name="IN-", func=PAS),
        Pin(num="3", name="GND", func=PWRIN),
        Pin(num="4", name="VS", func=PWRIN),
        Pin(num="5", name="SCL", func=BI),
        Pin(num="6", name="SDA", func=BI),
        Pin(num="7", name="A0", func=IN),
        Pin(num="8", name="A1", func=IN),
    ],
)

# WS2812B 5050: 1 VDD, 2 DOUT, 3 VSS, 4 DIN (Worldsemi datasheet).
WS2812B = _p(
    "WS2812B", "D", "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm",
    lcsc="C2761795", value="WS2812B",
    pins=[
        Pin(num="1", name="VDD", func=PWRIN),
        Pin(num="2", name="DOUT", func=OUT),
        Pin(num="3", name="VSS", func=PWRIN),
        Pin(num="4", name="DIN", func=IN),
    ],
)

# ALPS EC11E vertical, with push switch: A/C/B + S1/S2.
EC11 = _p(
    "EC11E18244AU", "SW",
    "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
    lcsc="C202365", value="EC11",
    pins=[
        Pin(num="A", name="A", func=PAS),
        Pin(num="B", name="B", func=PAS),
        Pin(num="C", name="COM", func=PAS),
        Pin(num="S1", name="SW1", func=PAS),
        Pin(num="S2", name="SW2", func=PAS),
    ],
)

# TS-1187A-B-A-B tact switch: pins 1/2 and 3/4 are internally paired
# (XKB datasheet); custom footprint generated into wigglecam.pretty.
TACT = _p(
    "TS-1187A", "SW", "wigglecam:SW_TS-1187A_5.1x5.1mm",
    lcsc="C318884", value="TACT",
    pins=[Pin(num="1", name="A", func=PAS),
          Pin(num="2", name="A2", func=PAS),
          Pin(num="3", name="B", func=PAS),
          Pin(num="4", name="B2", func=PAS)],
)

# PESD5V0S1BA bidirectional TVS, SOD-323.
TVS_5V = _p(
    "PESD5V0S1BA", "D", "Diode_SMD:D_SOD-323",
    lcsc="C19224", value="PESD5V0S1BA",
    pins=[Pin(num="1", name="K", func=PAS),
          Pin(num="2", name="A", func=PAS)],
)

# SS34 3A Schottky, SMA. Commodity part; LCSC C8678 class — final
# number confirmed at BOM generation.
SS34 = _p(
    "SS34", "D", "Diode_SMD:D_SMA",
    lcsc="C8678", value="SS34",
    pins=[Pin(num="1", name="K", func=PAS),
          Pin(num="2", name="A", func=PAS)],
)

# 1N4148WS small-signal diode, SOD-323 (WS2812 VDD drop).
D4148 = _p(
    "1N4148WS", "D", "Diode_SMD:D_SOD-323",
    lcsc="C81598", value="1N4148WS",
    pins=[Pin(num="1", name="K", func=PAS),
          Pin(num="2", name="A", func=PAS)],
)

# PTC resettable fuse, 1812, 3 A hold. Commodity; number at BOM time.
PTC_3A = _p(
    "PTC_3A", "F", "Fuse:Fuse_1812_4532Metric",
    lcsc="TBC-1812-PTC-3A", value="PTC 3A",
    pins=[Pin(num="1", name="1", func=PAS),
          Pin(num="2", name="2", func=PAS)],
)

# Generic two-terminal passives ------------------------------------------
def R(value, size="0603", lcsc=""):
    fp = {"0603": "Resistor_SMD:R_0603_1608Metric",
          "1206": "Resistor_SMD:R_1206_3216Metric",
          "2512": "Resistor_SMD:R_2512_6332Metric"}[size]
    return _p("R", "R", fp, lcsc=lcsc, value=value, template=False,
              pins=[Pin(num="1", name="1", func=PAS),
                    Pin(num="2", name="2", func=PAS)])


def C(value, size="0603", lcsc=""):
    fp = {"0603": "Capacitor_SMD:C_0603_1608Metric",
          "0805": "Capacitor_SMD:C_0805_2012Metric",
          "elec": "Capacitor_SMD:CP_Elec_8x10.2"}[size]
    return _p("C", "C", fp, lcsc=lcsc, value=value, template=False,
              pins=[Pin(num="1", name="1", func=PAS),
                    Pin(num="2", name="2", func=PAS)])


# Shunt: GX2512-2W-10mR-1% (stock-verified C500718).
def SHUNT():
    return _p("R_shunt", "R", "Resistor_SMD:R_2512_6332Metric",
              lcsc="C500718", value="10mR 2W 1%", template=False,
              pins=[Pin(num="1", name="1", func=PAS),
                    Pin(num="2", name="2", func=PAS)])


# Green debug LED, 0603.
LED_G = _p(
    "LED_GREEN", "D", "LED_SMD:LED_0603_1608Metric",
    lcsc="C72043", value="GREEN",
    pins=[Pin(num="1", name="K", func=PAS),
          Pin(num="2", name="A", func=PAS)],
)

# Connectors ---------------------------------------------------------------
def JST_XH2(name):
    return _p(name, "J",
              "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
              lcsc="TBC-JST-XH-2P", value=name, template=False,
              pins=[Pin(num="1", name="1", func=PAS),
                    Pin(num="2", name="2", func=PAS)])


PI_HDR = _p(
    "PI_HEADER_2x6", "J",
    "Connector_PinSocket_2.54mm:PinSocket_2x06_P2.54mm_Vertical",
    lcsc="TBC-PinSocket-2x6", value="Pi GPIO 1-12",
    pins=[Pin(num=str(n), name=f"P{n}", func=PAS) for n in range(1, 13)],
)

SWD_HDR = _p(
    "SWD", "J",
    "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    lcsc="TBC-PinHeader-1x3", value="SWD",
    pins=[Pin(num="1", name="SWCLK", func=PAS),
          Pin(num="2", name="GND", func=PAS),
          Pin(num="3", name="SWDIO", func=PAS)],
)
