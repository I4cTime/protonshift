#!/usr/bin/env bash
# Dev launcher. Creates a local venv on first run, installs deps, launches.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -e .
fi

exec "$VENV/bin/python" -m protonshift "$@"
