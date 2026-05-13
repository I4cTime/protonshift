#!/usr/bin/env bash
# Run inside Fedora Workstation *as root*.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_mount-build-share.sh
. "${SCRIPT_DIR}/_mount-build-share.sh"

# RPMFusion gives us steam, mangohud, gamemode.
dnf install -y \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
  https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm

dnf install -y \
  steam \
  mangohud \
  gamescope \
  gamemode \
  protontricks \
  flatpak \
  cifs-utils \
  fuse fuse-libs

flatpak remote-add --if-not-exists flathub \
  https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.heroicgameslauncher.hgl net.lutris.Lutris

mount_protonshift_build

echo ""
echo "Provisioning done. Launch ProtonShift with one of:"
echo "  /mnt/protonshift-build/ProtonShift-*.AppImage"
echo "  sudo dnf install /mnt/protonshift-build/protonshift-*.rpm"
