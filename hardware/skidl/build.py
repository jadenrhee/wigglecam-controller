"""Build the Camera Controller netlist: ERC + KiCad netlist + JSON bridge.

Run:  python3 build.py
Outputs (in hardware/):
  netlist.net   — KiCad-format netlist (committed deliverable)
  board.json    — {parts: [{ref, name, value, footprint, lcsc,
                   pads: {padnum: netname}}], nets: [...]}
                  consumed by the pcbnew layout scripts, so the
                  layout stage has zero dependence on netlist parsing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from skidl import ERC, generate_netlist

import circuit as ckt
from builtins import default_circuit  # injected by skidl on import

HW = Path(__file__).resolve().parent.parent


def main():
    ckt.power_input()
    ckt.regulator_3v3()
    u = ckt.mcu_core()
    ckt.usb(u)
    ckt.flash_driver(u)
    ckt.battery_monitor(u)
    ckt.controls(u)
    ckt.pi_header(u)

    ERC()
    generate_netlist(file_=str(HW / "netlist.net"))

    parts = []
    for part in default_circuit.parts:
        pads = {}
        for pin in part.pins:
            if pin.net is not None and pin.net.name != "NC":
                pads[str(pin.num)] = pin.net.name
        parts.append({
            "ref": part.ref,
            "name": part.name,
            "value": str(part.value),
            "footprint": part.footprint,
            "lcsc": part.fields.get("LCSC", ""),
            "pads": pads,
        })
    nets = sorted({n.name for n in default_circuit.nets
                   if n.name not in ("NC",)})
    (HW / "board.json").write_text(
        json.dumps({"parts": parts, "nets": nets}, indent=1))
    print(f"parts={len(parts)} nets={len(nets)}")
    print("WROTE", HW / "netlist.net", HW / "board.json")


if __name__ == "__main__":
    main()
