#!/usr/bin/env bash
# Run inside Arch / EndeavourOS / CachyOS *as root*.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_mount-build-share.sh
. "${SCRIPT_DIR}/_mount-build-share.sh"

# `gamescope` / `steam` hard-depend on `vulkan-driver` and `lib32-vulkan-driver`
# (mesa stopped satisfying those years ago). Under `--noconfirm` pacman silently
# picks option 1, and on CachyOS that is `mesa-git` from the cachyos-v3 repo —
# which then conflicts with the stable `mesa` already on disk and the whole
# transaction aborts.
#
# Pinning a concrete `vulkan-swrast` provider sidesteps both the prompt and the
# conflict. swrast is software-only, but every smoke-test VM in this harness
# runs without GPU passthrough anyway, and real-hardware users can layer
# `vulkan-radeon` / `vulkan-intel` / `nvidia-utils` themselves later.
pacman -Sy --noconfirm --needed \
  mesa \
  lib32-mesa \
  vulkan-swrast \
  lib32-vulkan-swrast \
  steam \
  mangohud \
  gamescope \
  gamemode \
  flatpak \
  cifs-utils \
  fuse2

# protontricks is in AUR on plain Arch; CachyOS ships it in repos. Skip if
# unavailable — the app will detect and grey out the panel.
pacman -S --noconfirm --needed protontricks 2>/dev/null || \
  echo "(protontricks not in repos — install from AUR if you need it)"

flatpak remote-add --if-not-exists flathub \
  https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.heroicgameslauncher.hgl net.lutris.Lutris

mount_protonshift_build

echo ""
echo "Provisioning done."
echo "Run: /mnt/protonshift-build/ProtonShift-*.AppImage"
