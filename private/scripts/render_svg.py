"""Export layer-composite SVGs via the plot API (render fallback)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from kicad_common import BOARD_PATH

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp")


def plot(board, layers, name):
    pc = pcbnew.PLOT_CONTROLLER(board)
    po = pc.GetPlotOptions()
    po.SetOutputDirectory(str(OUT))
    po.SetPlotFrameRef(False)
    po.SetSvgPrecision(4)
    pc.OpenPlotfile(name, pcbnew.PLOT_FORMAT_SVG, name)
    for i, layer in enumerate(layers):
        pc.SetLayer(layer)
        pc.PlotLayer()
    pc.ClosePlot()


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    plot(board, [pcbnew.F_Cu], "F_Cu")
    plot(board, [pcbnew.B_Cu], "B_Cu")
    plot(board, [pcbnew.In1_Cu], "In1_Cu")
    plot(board, [pcbnew.In2_Cu], "In2_Cu")
    plot(board, [pcbnew.F_SilkS], "F_Silk")
    plot(board, [pcbnew.Edge_Cuts], "Edge")
    print("SVGs in", OUT)


if __name__ == "__main__":
    main()
