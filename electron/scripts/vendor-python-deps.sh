#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/python-vendor"
REQ="${ROOT}/python-runtime-requirements.txt"
rm -rf "${TARGET}"
python3 -m pip install -r "${REQ}" -t "${TARGET}" --upgrade
echo "Vendored Python deps into ${TARGET}"
