#!/usr/bin/env bash
# Vendor Python runtime dependencies into ./python-vendor/ using the
# bundled CPython interpreter from ./python-runtime/.
#
# Vendoring with the SAME interpreter we ship guarantees that native
# extensions (.so files, currently only pydantic_core) match the runtime's
# ABI. That removes the ABI-fallback dance _vendor_compat.py used to do
# and lets the AppImage run without any python3 host packages.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/python-vendor"
REQ="${ROOT}/python-runtime-requirements.txt"
RUNTIME="${ROOT}/python-runtime"
PY="${RUNTIME}/bin/python3"

if [[ ! -x "${PY}" ]]; then
  echo "Bundled python not found at ${PY}." >&2
  echo "Run scripts/fetch-python.sh first (or 'pnpm run vendor-python')." >&2
  exit 1
fi

rm -rf "${TARGET}"
mkdir -p "${TARGET}"

"${PY}" -m pip install \
  -r "${REQ}" \
  -t "${TARGET}" \
  --upgrade \
  --no-cache-dir \
  --disable-pip-version-check

# Trim packaging metadata bloat — keep the bits pip/import need.
find "${TARGET}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${TARGET}" -type d -name "*.dist-info" -exec sh -c '
  for d; do
    find "$d" -maxdepth 1 -type f \
      ! -name METADATA ! -name top_level.txt ! -name RECORD -delete 2>/dev/null
  done
' _ {} + 2>/dev/null || true

# pip stays in the on-disk runtime so re-running vendor is idempotent.
# It is excluded from the shipped bundle by electron-builder's `extraResources`
# filter, which trims pip + dev cruft from the AppImage payload.
PY_VER="$("${PY}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
SO_COUNT="$(find "${TARGET}" -name '*.so' | wc -l)"
SIZE="$(du -sh "${TARGET}" | cut -f1)"
echo "Vendored Python deps into ${TARGET} (Python ${PY_VER}, ${SO_COUNT} native ext, ${SIZE})"
