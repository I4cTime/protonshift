#!/usr/bin/env bash
# Fetch a portable, fully self-contained CPython runtime for bundling.
#
# Source: astral-sh/python-build-standalone — these tarballs are linked
# against glibc 2.17+, ship a complete stdlib + working pip, and run on
# essentially every modern Linux distro without touching system Python.
#
# Output: ./python-runtime/  (relative to this repo's electron/ dir)
#
# Override version pin via env vars:
#   PBS_RELEASE=20260510
#   PBS_PYTHON=3.12.13
#   PBS_SHA256=<sha256>
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/python-runtime"

# Pinned upstream — bump together. SHA from the release's SHA256SUMS.
PBS_RELEASE="${PBS_RELEASE:-20260510}"
PBS_PYTHON="${PBS_PYTHON:-3.12.13}"
PBS_SHA256="${PBS_SHA256:-d480f5d5878910ecbae212bf23bd7c25d7b209eb8cf5e98823c977384d272e88}"

ARCH="x86_64-unknown-linux-gnu"
FLAVOR="install_only_stripped"
ASSET="cpython-${PBS_PYTHON}+${PBS_RELEASE}-${ARCH}-${FLAVOR}.tar.gz"
URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${ASSET//+/%2B}"

VERSION_STAMP="${TARGET}/.protonshift-version"
WANT_STAMP="${PBS_RELEASE}-${PBS_PYTHON}-${PBS_SHA256}"

if [[ -f "${VERSION_STAMP}" ]] && [[ "$(cat "${VERSION_STAMP}")" == "${WANT_STAMP}" ]]; then
  echo "python-runtime already at ${PBS_PYTHON}+${PBS_RELEASE}; skipping fetch."
  exit 0
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT
TARBALL="${TMPDIR}/${ASSET}"

echo "Downloading ${ASSET}"
curl -fSL --retry 3 --retry-delay 2 -o "${TARBALL}" "${URL}"

echo "Verifying sha256"
echo "${PBS_SHA256}  ${TARBALL}" | sha256sum -c -

rm -rf "${TARGET}"
mkdir -p "${TARGET}"
echo "Extracting into ${TARGET}"
tar -xzf "${TARBALL}" -C "${TMPDIR}"
# Tarball top-level is "python/", flatten one level.
mv "${TMPDIR}/python/"* "${TARGET}/"

# Sanity check: the bundled interpreter must be runnable as-is.
"${TARGET}/bin/python3" -c "import sys; print('bundled python:', sys.version.split()[0])"

# Trim things we will never use at runtime. Roughly halves the bundle size.
PY_LIB="${TARGET}/lib/python$(echo "${PBS_PYTHON}" | cut -d. -f1-2)"
if [[ -d "${PY_LIB}" ]]; then
  rm -rf "${PY_LIB}/test" "${PY_LIB}/idlelib" "${PY_LIB}/tkinter" \
         "${PY_LIB}/turtledemo" "${PY_LIB}/ensurepip" 2>/dev/null || true
  find "${PY_LIB}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
fi
# Tk / Tcl: Electron renders the UI; nothing in our backend uses them.
rm -rf "${TARGET}/lib/tcl9"* "${TARGET}/lib/tk9"* "${TARGET}/lib/itcl"* \
       "${TARGET}/lib/thread"* "${TARGET}/lib/libtcl"* "${TARGET}/lib/libtk"* 2>/dev/null || true
# terminfo / man pages: not used by a daemon process.
rm -rf "${TARGET}/share/terminfo" "${TARGET}/share/man" 2>/dev/null || true
# C headers are only useful for building extensions; we ship prebuilt wheels.
rm -rf "${TARGET}/include" 2>/dev/null || true
# Drop config-only python3-config helpers; not used at runtime.
rm -f "${TARGET}/bin/python3.12-config" "${TARGET}/bin/2to3"* 2>/dev/null || true

echo "${WANT_STAMP}" > "${VERSION_STAMP}"

SIZE="$(du -sh "${TARGET}" | cut -f1)"
echo "python-runtime ready: ${PBS_PYTHON}+${PBS_RELEASE} (${SIZE})"
