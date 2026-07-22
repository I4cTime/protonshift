#!/usr/bin/env bash
# Dev launcher. Creates a local venv on first run, installs deps, launches.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi
# re-sync on every launch so new deps in pyproject.toml are picked up
# (near-instant when already up to date)
"$VENV/bin/pip" install --quiet -e .

exec "$VENV/bin/python" -m protonshift "$@"
