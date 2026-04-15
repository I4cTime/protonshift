#!/bin/bash
# Run ProtonShift. Ensure python3-vdf is installed: sudo apt install python3-vdf
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
exec python3 -m game_setup_hub "$@"
