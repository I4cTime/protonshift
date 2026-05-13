#!/usr/bin/env bash
# Bazzite is rpm-ostree, so most game tooling is preinstalled (Steam,
# MangoHud, Gamescope, GameMode). Just install Heroic + Lutris via Flatpak
# and copy the AppImage in via SCP — `cifs-utils` would require an
# rpm-ostree install + reboot, which is overkill for a smoke test.
set -euo pipefail

flatpak remote-add --if-not-exists --user flathub \
  https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y --user flathub com.heroicgameslauncher.hgl net.lutris.Lutris

mkdir -p /var/home/"${SUDO_USER:-$USER}"/protonshift-build
cat <<EOF

Bazzite ships Steam / MangoHud / Gamescope / GameMode by default.

To pull the AppImage in from the host, on the *host* run:
  HOST_PORT=\$(awk -F= '/^ssh_port/{print \$2}' vm-test/quickemu/bazzite-*/.ports)
  scp -P "\$HOST_PORT" build/ProtonShift-*.AppImage \\
    ${SUDO_USER:-$USER}@localhost:~/protonshift-build/

Then in the guest:
  chmod +x ~/protonshift-build/ProtonShift-*.AppImage
  ~/protonshift-build/ProtonShift-*.AppImage
EOF
