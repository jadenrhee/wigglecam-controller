#!/bin/zsh
# kicad-cli wrapper. On macOS, kicad-cli's library-table scan touches
# ~/Documents, which TCC blocks forever for headless processes — point
# both homes at a writable scratch dir instead.
export KICAD_CONFIG_HOME="${TMPDIR:-/tmp}/kicad-headless-cfg"
export KICAD_DOCUMENTS_HOME="${TMPDIR:-/tmp}/kicad-headless-docs"
mkdir -p "$KICAD_CONFIG_HOME" "$KICAD_DOCUMENTS_HOME"
exec /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli "$@"
