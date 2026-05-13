#!/usr/bin/env bash
# Boot a Quickemu guest described by vm-test/quickemu/<name>.extras.conf.
#
# Usage:
#   ./run-vm.sh <name>          # download ISO via quickget if needed, merge custom Quickemu knobs, boot
#   ./run-vm.sh <name> --status # print VM info only
#   ./run-vm.sh list            # list available guests
#
# quickget refuses to regenerate <distro>-<release>.conf if that path already
# exists WITHOUT an iso/img line — a common trap when committing a stray
# handcrafted .conf. We only ship *.extras.conf fragments; merged .conf lives
# in quickemu/*.conf (typically gitignored) with proper iso=/img= pointers.
#
# Host build artefacts are exposed via:
#     quickemu --public-dir "$(repo)/build/"
# Guests mount smb://10.0.2.4/qemu (see docs/guest-build-share-appimage.md + provision/).

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_DIR="${HERE}/quickemu"
ARTIFACT_DIR="$(cd "${HERE}/.." && pwd)/build"

list_configs() {
  ls -1 "${CONF_DIR}"/*.extras.conf 2>/dev/null | sed 's|.*/||; s/\.extras\.conf$//' | sort -u
}

# Merge ASSIGNMENT lines from extras into MAIN_CONF — fragment keys shadow
# any existing keys picked up by quickemu/quickget upstream.
quickemu_merge_overrides() {
  local main_conf="$1" extras="$2"
  [[ -f "${extras}" ]] || return 0
  local stripped tmp_assign
  tmp_assign="$(mktemp)"
  stripped="$(mktemp)"
  grep -E '^[a-zA-Z_][a-zA-Z0-9_]*=' "${extras}" \
    | grep -Ev '^(CONF_BASENAME|QG_DISTRO|QG_RELEASE|QG_EDITION)=' > "${tmp_assign}" || true
  cp "${main_conf}" "${stripped}"

  # GNU grep exits 1 when it would print nothing (`set -e` would abort). Use awk.
  local k=""
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ "$line" =~ ^([a-zA-Z_][a-zA-Z0-9_]*)= ]] || continue
    k="${BASH_REMATCH[1]}"
    awk -v p="${k}=" 'substr($0, 1, length(p)) != p { print }' "${stripped}" > "${stripped}.new"
    mv "${stripped}.new" "${stripped}"
  done < "${tmp_assign}"

  {
    cat "${stripped}"
    cat "${tmp_assign}"
  } > "${main_conf}"

  rm -f "${stripped}" "${tmp_assign}"
}

conf_has_boot_media() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  grep -qE '^iso="|^fixed_iso="|^img="' "$f"
}

if [[ $# -lt 1 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  echo "Usage: $0 <name>|list [--status]"
  echo ""
  echo "Available VMs:"
  list_configs | sed 's/^/  /'
  exit 0
fi

if [[ "$1" == "list" ]]; then
  list_configs
  exit 0
fi

NAME="$1"
shift || true
EXTRAS="${CONF_DIR}/${NAME}.extras.conf"
if [[ ! -f "${EXTRAS}" ]]; then
  echo "Unknown VM '${NAME}'. Known names:" >&2
  list_configs | sed 's/^/  /' >&2
  exit 1
fi

for tool in quickemu quickget; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "Required tool '${tool}' not on PATH. Install Quickemu first." >&2
    echo "See vm-test/README.md for distro-specific install commands." >&2
    exit 1
  fi
done

mkdir -p "${ARTIFACT_DIR}"
cd "${CONF_DIR}"

unset QG_DISTRO QG_RELEASE QG_EDITION CONF_BASENAME
# shellcheck disable=SC1090
source "${EXTRAS}"

if [[ -z "${QG_DISTRO:-}" ]] || [[ -z "${QG_RELEASE:-}" ]]; then
  echo "extras file must define QG_DISTRO and QG_RELEASE: ${EXTRAS}" >&2
  exit 1
fi

BASE="${CONF_BASENAME:-$NAME}"
MAIN_CONF="${CONF_DIR}/${BASE}.conf"

if [[ -f "${MAIN_CONF}" ]] && ! conf_has_boot_media "${MAIN_CONF}"; then
  echo "Stale ${BASE}.conf (no iso/img/image). Removing so quickget can regenerate iso=…" >&2
  mv -f "${MAIN_CONF}" "${MAIN_CONF}.bak.$(date +%s)" 2>/dev/null \
    || rm -f "${MAIN_CONF}"
fi

# quickget ALWAYS exits successfully after fetching *and refuses to regenerate
# an existing *.conf*. If the iso line is gone we nuked MAIN_CONF above; if the
# per-ISO directory is empty/unusable, let quickget refill it.
needs_fetch=false
if [[ ! -f "${MAIN_CONF}" ]]; then
  needs_fetch=true
elif ! conf_has_boot_media "${MAIN_CONF}"; then
  rm -f "${MAIN_CONF}"
  needs_fetch=true
fi

if [[ "${needs_fetch}" == true ]]; then
  echo "Fetching ${QG_DISTRO} ${QG_RELEASE}${QG_EDITION:+ (${QG_EDITION})} via quickget…"
  if [[ -n "${QG_EDITION:-}" ]]; then
    quickget "${QG_DISTRO}" "${QG_RELEASE}" "${QG_EDITION}"
  else
    quickget "${QG_DISTRO}" "${QG_RELEASE}"
  fi
fi

if [[ ! -f "${MAIN_CONF}" ]]; then
  echo "ERROR: expected Quickemu conf at ${MAIN_CONF}" >&2
  echo "(quickget emits <VM_PATH>.conf — tweak CONF_BASENAME in ${EXTRAS}?)" >&2
  exit 1
fi
if ! conf_has_boot_media "${MAIN_CONF}"; then
  echo "ERROR: ${MAIN_CONF} still has no iso/fixed_iso/img assignment." >&2
  exit 1
fi

quickemu_merge_overrides "${MAIN_CONF}" "${EXTRAS}"

PROV_STAGE="${ARTIFACT_DIR}/_provision"
mkdir -p "${PROV_STAGE}"
cp "${HERE}/provision/"*.sh "${PROV_STAGE}/"
chmod +x "${PROV_STAGE}/"*.sh

# Stage vm-test docs into the SMB share so guests can `cat`/`less` them at
# /mnt/protonshift-build/_docs/<file>.md without bouncing back to the host.
DOCS_STAGE="${ARTIFACT_DIR}/_docs"
rm -rf "${DOCS_STAGE}"
mkdir -p "${DOCS_STAGE}"
cp "${HERE}/docs/"*.md          "${DOCS_STAGE}/"
cp "${HERE}/smoke-checklist.md" "${DOCS_STAGE}/"
cp "${HERE}/README.md"          "${DOCS_STAGE}/README.md"

QUICKEMU_ARGS=(--vm "${BASE}.conf" --public-dir "${ARTIFACT_DIR}")

if [[ "${1:-}" == "--status" ]]; then
  QUICKEMU_ARGS+=(--status-quo)
fi

if ! command -v smbd >/dev/null 2>&1; then
  cat >&2 <<EOF
Warning: 'smbd' is not installed on the host. Quickemu won't be able to
expose ${ARTIFACT_DIR} to the guest as smb://10.0.2.4/qemu, so
/mnt/protonshift-build will not auto-mount inside the VM.

Install Samba (one-time):
  sudo apt install --no-install-recommends samba   # Pop!_OS / Ubuntu / Debian
  sudo dnf install samba                           # Fedora / Bazzite

Or copy artifacts via the auto-forwarded SSH port (.ports beside the VM).
EOF
fi

echo "Booting ${NAME}"
echo "  Quickemu conf:       ${BASE}.conf"
echo "  Host artefacts dir:  ${ARTIFACT_DIR}"
echo "  Guest mount target:  smb://10.0.2.4/qemu → /mnt/protonshift-build"
echo "  Guest provision:     /mnt/protonshift-build/_provision/<distro>.sh"
echo "  Guest docs (paste):  /mnt/protonshift-build/_docs/<this-distro>.md"
exec quickemu "${QUICKEMU_ARGS[@]}"
