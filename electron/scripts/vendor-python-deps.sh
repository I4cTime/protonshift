#!/usr/bin/env bash
# Vendor Python runtime dependencies for AppImage/deb/rpm packaging.
#
# Native extensions (.so) are version-locked to the build Python.
# The Electron main process appends system site-packages as a fallback
# so users on a different Python minor version still get native deps
# from their system packages.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/python-vendor"
REQ="${ROOT}/python-runtime-requirements.txt"

rm -rf "${TARGET}"
python3 -m pip install \
  -r "${REQ}" \
  -t "${TARGET}" \
  --upgrade \
  --no-cache-dir

# Remove unnecessary bloat from vendor dir
find "${TARGET}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${TARGET}" -type d -name "*.dist-info" -exec sh -c '
  for d; do
    # Keep METADATA and top_level.txt, delete the rest
    find "$d" -maxdepth 1 -type f ! -name METADATA ! -name top_level.txt ! -name RECORD -delete 2>/dev/null
  done
' _ {} + 2>/dev/null || true

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
SO_COUNT="$(find "${TARGET}" -name '*.so' | wc -l)"
echo "Vendored Python deps into ${TARGET} (Python ${PY_VER}, ${SO_COUNT} native extensions)"
