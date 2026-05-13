#!/usr/bin/env bash
# Run inside an Ubuntu / Debian guest *as root* (sudo bash this).
# Installs the game-related deps Protonshift exercises. Python and
# pydantic are intentionally NOT installed — the AppImage bundles them.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_mount-build-share.sh
. "${SCRIPT_DIR}/_mount-build-share.sh"

export DEBIAN_FRONTEND=noninteractive

# steam-installer pins matching steam-libs / steam-libs-i386 versions; without
# i386, apt reports steam-libs-i386 as "not installable".
if ! dpkg --print-foreign-architectures | grep -qx 'i386'; then
  dpkg --add-architecture i386
fi

apt-get update -qq

# Needed before HTTPS Launchpad repos.
apt-get install -y --no-install-recommends \
  ca-certificates \
  gnupg \
  software-properties-common

# Steam .deb lives in multiverse on Ubuntu; minimal/cloud images often omit it.
add-apt-repository -y universe 2>/dev/null || true
add-apt-repository -y multiverse 2>/dev/null || true
apt-get update -qq

# flatpak Depends: fuse3. The transitional "fuse" .deb (FUSE 2 userspace) conflicts
# (fuse3 Breaks: fuse) on every arch — including fuse:i386 on multiarch guests.
# apt sometimes satisfies virtual "Depends: fuse" via fuse:i386 anyway; pinning the
# concrete package "fuse" forces resolution through fuse3 (Provides: fuse).
install -d -m0755 /etc/apt/preferences.d
cat >/etc/apt/preferences.d/99-protonshift-fuse.pref <<'EOF'
# Satisfy Depends: fuse via fuse3 only (never the fuse/FUSE2 metapackage).
Package: fuse
Pin: release *
Pin-Priority: -1
EOF

DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends fuse3
DEBIAN_FRONTEND=noninteractive apt-get remove -y fuse 'fuse:i386' 2>/dev/null || true

. /etc/os-release
CODENAME="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
VID="${VERSION_ID:-}"

gamescope_has_candidate() {
  local cand=""
  cand="$(apt-cache policy gamescope 2>/dev/null | sed -n 's/^[[:space:]]*Candidate:[[:space:]]*\(.*\)$/\1/p' | head -1)"
  [[ -n "${cand}" && "${cand}" != "(none)" ]]
}

# gamescope has no Debian/Ubuntu mirror entry on Noble (24.04); use Marco
# Trevisán's gamescope PPA for that release (and Pop!_OS / Ubuntu clones that
# still report noble + VERSION_ID 24.04). Jammy: prefer universe package.
if ! gamescope_has_candidate; then
  if [[ "${CODENAME}" == noble || "${VID}" == "24.04" ]]; then
    echo "Adding ppa:3v1n0/gamescope for Ubuntu Noble / 24.04-family (gamescope not in stock repos)…"
    add-apt-repository -y ppa:3v1n0/gamescope
    apt-get update -qq
  elif [[ "${CODENAME}" == jammy ]]; then
    add-apt-repository -y universe
    apt-get update -qq
  else
    echo "Note: no gamescope path for codename=${CODENAME}, VERSION_ID=${VID}; skipping PPA/game repository tweak." >&2
  fi
fi

# AppImage needs FUSE2 userspace libs. Prefer libfuse2t64 (Noble+) else
# libfuse2-2 (Jammy/Debian bookworm). Omit transitional "fuse" — clashes with fuse3.
FUSE2_AIMG=()
if apt-cache show libfuse2t64 &>/dev/null; then FUSE2_AIMG=(libfuse2t64)
elif apt-cache show libfuse2-2 &>/dev/null; then FUSE2_AIMG=(libfuse2-2)
fi

apt-get install -y --no-install-recommends \
  steam-installer \
  mangohud \
  gamemode \
  protontricks \
  flatpak \
  cifs-utils \
  curl \
  "${FUSE2_AIMG[@]}"

if ! apt-get install -y --no-install-recommends gamescope; then
  if gamescope_has_candidate; then
    echo "Note: apt could not install gamescope despite a Candidate (dependency/conflict?). Continuing." >&2
  else
    echo "Note: gamescope has no Candidate (PPA unreachable or unsupported arch?). ProtonShift will grey out Gamescope." >&2
  fi
fi

flatpak remote-add --if-not-exists flathub \
  https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub com.heroicgameslauncher.hgl net.lutris.Lutris

mount_protonshift_build

echo ""
echo "Provisioning done. Launch ProtonShift (Electron needs the sandbox tweak on many setups):"
echo "  VM / Ubuntu /tmp nosuid:"
echo "    /mnt/protonshift-build/ProtonShift-*.AppImage --no-sandbox"
echo "  Or TMPDIR under HOME (often allows setuid sandbox):"
echo "    mkdir -p \"\${HOME}/.cache/protonshift-appimage-tmp\""
echo "    TMPDIR=\"\${HOME}/.cache/protonshift-appimage-tmp\" /mnt/protonshift-build/ProtonShift-*.AppImage"
echo "  Do not run AppImage as root unless you pass --no-sandbox (electron blocks root by default)."
