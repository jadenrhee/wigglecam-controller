"""Export DSN for Freerouting / import the SES it produces.

Usage (KiCad python):
  03_autoroute.py export   -> writes wigglecam.dsn
  03_autoroute.py import   -> reads wigglecam.ses back into the board

The Freerouting jar itself is driven from the shell between the two
steps (see docs/plan.md phase 3): its output is treated as a draft —
04_cleanup re-asserts critical geometry and the DRC gate decides.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH

DSN = BOARD_PATH.with_suffix(".dsn")
SES = BOARD_PATH.with_suffix(".ses")


def _drop(txt, netname):
    """Replace the net's pin list with an empty one: the net stays
    defined (the wiring section references it for existing copper)
    but Freerouting has nothing to route."""
    out = txt
    for key, quoted in ((f'(net "{netname}"', True),
                        (f"(net {netname}\n", False),
                        (f"(net {netname} ", False)):
        start = 0
        while True:
            i = out.find(key, start)
            if i < 0:
                break
            depth = 0
            j = i
            while True:
                if out[j] == "(":
                    depth += 1
                elif out[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            name = f'"{netname}"' if quoted else netname
            stub = f"(net {name}\n      (pins))"
            out = out[:i] + stub + out[j + 1:]
            start = i + len(stub)
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "export"
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    if mode == "export-only":
        # strip EVERY net except the listed ones: targeted repair pass
        # where all existing copper acts as fixed obstacles
        keep = set(sys.argv[2].split(","))
        ok = pcbnew.ExportSpecctraDSN(board, str(DSN))
        text = DSN.read_text()
        allnets = {board.GetNetInfo().GetNetItem(i).GetNetname()
                   for i in range(1, board.GetNetInfo().GetNetCount())}
        netsec = text.find("(network")
        head, tail = text[:netsec], text[netsec:]
        for n in sorted(allnets - keep - {""}):
            tail = _drop(tail, n)
        DSN.write_text(head + tail)
        print(f"DSN repair export: kept {sorted(keep)}")
        return
    if mode == "export":
        # shrink the outline 0.35 mm for the DSN only, so Freerouting
        # honors the copper-to-edge clearance it otherwise ignores
        # (the board file itself is NOT saved with this change)
        from kicad_common import BOARD_H, BOARD_W, mm, to_local
        for d in board.GetDrawings():
            if d.GetLayer() != pcbnew.Edge_Cuts:
                continue
            for getter, setter in ((d.GetStart, d.SetStart),
                                   (d.GetEnd, d.SetEnd)):
                x, y = to_local(getter())
                x = 0.35 if x < 0.1 else (BOARD_W - 0.35
                                          if x > BOARD_W - 0.1 else x)
                y = 0.35 if y < 0.1 else (BOARD_H - 0.35
                                          if y > BOARD_H - 0.1 else y)
                setter(mm(x, y))
        ok = pcbnew.ExportSpecctraDSN(board, str(DSN))
        text = DSN.read_text()
        # 1) mark the inner plane layers as 'power' so Freerouting
        #    never routes signals through the GND / 3V3 planes
        for inner in ("In1.Cu", "In2.Cu"):
            text = text.replace(f"(layer {inner}\n      (type signal)",
                                f"(layer {inner}\n      (type power)")
        assert "(type power)" in text, "DSN layer-type patch failed"
        # 2) remove every net 02 already completed (planes included):
        #    Freerouting can't see plane/via connectivity and would
        #    add dangling duplicate wires for them
        # Strip only nets that are TRULY complete after 02:
        # - GND: In1 plane + stubs on every SMD pad + pours later
        # - VLED: In2 island + stubs on every pad
        # - point-to-point nets whose EVERY pad the script wired.
        # Nets with additional legs stay routable (QSPI_SS's BOOTSEL,
        # SENSEx's op-amp input + comp cap, VBAT's INA219 taps, +3V3
        # pads over the VLED island half where In2 isn't 3V3).
        done_nets = {"GND", "+3V3", "VLED", "PI5V_RAW", "PI5V_FUSED",
                     "PI_SDA", "XIN", "XOUT", "XOUT_XTAL",
                     "QSPI_SCLK", "QSPI_SCLK_FL", "QSPI_SD0",
                     "QSPI_SD1", "QSPI_SD2", "QSPI_SD3",
                     "USB_DP_CONN", "USB_DM_CONN", "USB_DP_ESD",
                     "USB_DM_ESD", "USB_DP", "USB_DM"}
        for fp in board.GetFootprints():
            if fp.GetReference() in ("Q2", "Q3"):
                for p in fp.Pads():
                    if p.GetNumber() == "3":
                        done_nets.add(p.GetNetname())   # LED returns

        # only inside the (network ...) section do (net ...) blocks
        # carry pin lists; class lists reference plain names, harmless
        netsec = text.find("(network")
        head, tail = text[:netsec], text[netsec:]
        for n in sorted(done_nets):
            tail = _drop(tail, n)
        text = head + tail
        DSN.write_text(text)
        print("DSN export:", ok, f"({len(done_nets)} completed nets "
              "removed)", DSN)
    else:
        ok = pcbnew.ImportSpecctraSES(board, str(SES))
        board.Save(str(BOARD_PATH))
        print("SES import:", ok)


if __name__ == "__main__":
    main()
