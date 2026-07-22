#!/usr/bin/env bash
# Regenerate the vendored (offline) Python dependency modules for the Flathub build.
#
# PySide6 is NOT vendored here — it comes from io.qt.PySide.BaseApp (see the
# Flathub manifest). Only pure-Python runtime deps outside the BaseApp need
# vendoring; today that is just `vdf`.
#
# Requires network + a Python with `requirements-parser`, and the freedesktop
# SDK installed so wheels resolve against the runtime's Python (3.12):
#   flatpak install -y flathub org.freedesktop.Sdk//24.08
#
# Usage:  ./gen-vendor.sh
set -euo pipefail
cd "$(dirname "$0")"

# Pinned to a specific flatpak-builder-tools commit and verified by sha256 —
# never execute a script curl'd from a mutable ref. To bump: pick a new commit,
# fetch the file, update GEN_SHA256 with `sha256sum` of the download.
GEN_COMMIT="dda10aa5949811589747e6e485da6ae2e86b5d2b"
GEN_SHA256="5e26c4ddd560f4867aa2a90bf53c747fbb476d575ae4a2d8f32c229e317aa4c6"
GEN_URL="https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/${GEN_COMMIT}/pip/flatpak-pip-generator.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "› fetching flatpak-pip-generator @ ${GEN_COMMIT}"
curl -sSL -o "$TMP/fpg.py" "$GEN_URL"

echo "› verifying sha256"
echo "${GEN_SHA256}  $TMP/fpg.py" | sha256sum --check --quiet || {
  echo "!! flatpak-pip-generator.py checksum mismatch — refusing to execute" >&2
  exit 1
}

echo "› ensuring requirements-parser is available"
python3 -c "import requirements" 2>/dev/null || pip3 install --user --quiet requirements-parser

echo "› generating python3-vdf.yaml (resolved inside org.freedesktop.Sdk//24.08)"
python3 "$TMP/fpg.py" \
  --runtime=org.freedesktop.Sdk//24.08 \
  --yaml -o python3-vdf \
  vdf

echo "✓ wrote $(pwd)/python3-vdf.yaml"
echo "  If you add a new pure-Python dependency, list it above and re-run."
