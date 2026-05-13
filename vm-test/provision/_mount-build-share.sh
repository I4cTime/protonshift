#!/usr/bin/env bash
# Source this from a per-distro provision script (after installing
# `cifs-utils` or its equivalent). Mounts the host's build/ directory at
# /mnt/protonshift-build using the Samba share Quickemu's `--public-dir`
# advertises at smb://10.0.2.4/qemu.

mount_protonshift_build() {
  local target="${1:-/mnt/protonshift-build}"
  mkdir -p "${target}"

  if mountpoint -q "${target}"; then
    return 0
  fi

  local user_for_id="${SUDO_USER:-${USER:-root}}"
  local guest_uid guest_gid
  guest_uid="$(id -u "${user_for_id}")"
  guest_gid="$(id -g "${user_for_id}")"

  if mount -t cifs //10.0.2.4/qemu "${target}" \
      -o "guest,vers=3.0,ro,uid=${guest_uid},gid=${guest_gid},forceuid,forcegid" 2>/dev/null; then
    echo "Mounted //10.0.2.4/qemu → ${target}"
    if ! grep -q '//10.0.2.4/qemu' /etc/fstab 2>/dev/null; then
      printf '//10.0.2.4/qemu  %s  cifs  guest,vers=3.0,ro,uid=%s,gid=%s,forceuid,forcegid,nofail,_netdev  0  0\n' \
        "${target}" "${guest_uid}" "${guest_gid}" >> /etc/fstab
    fi
    cat <<EOF
Inside the VM you can now:
  ls   ${target}                       # AppImage / .deb / .rpm + _provision/ + _docs/
  less ${target}/_docs/README.md       # vm-test overview
  less ${target}/_docs/<this-distro>.md  # this distro's runbook
EOF
    return 0
  fi

  cat <<EOF
Note: could not mount //10.0.2.4/qemu at ${target}.
  - Make sure 'smbd' is installed and running on the *host*.
  - Make sure you booted this VM via vm-test/run-vm.sh (it adds --public-dir).
  - You can still copy artifacts in via the auto-forwarded SSH port; see
    .ports in the per-VM directory on the host.
EOF
  return 1
}
