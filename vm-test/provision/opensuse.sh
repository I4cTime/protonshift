#!/usr/bin/env bash
# Run inside openSUSE Tumbleweed *as root*.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_mount-build-share.sh
. "${SCRIPT_DIR}/_mount-build-share.sh"

zypper --non-interactive install --no-recommends \
  steam \
  mangohud \
  gamescope \
  gamemoded \
  protontricks \
  flatpak \
  cifs-utils \
  fuse

flatpak remote-add --if-not-exists flathub \
  https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.heroicgameslauncher.hgl net.lutris.Lutris

mount_protonshift_build

echo ""
echo "Provisioning done."
echo "Run: /mnt/protonshift-build/ProtonShift-*.AppImage"
