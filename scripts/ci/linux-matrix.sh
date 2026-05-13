#!/usr/bin/env bash
# Run Python lint + tests inside Linux distro containers (Podman or Docker).
# Use for a quick "does the backend behave on Debian vs musl vs Ubuntu" check.
#
# Usage:
#   ./scripts/ci/linux-matrix.sh                    # all targets
#   LINUX_MATRIX_IMAGE=python:3.12-alpine ./scripts/ci/linux-matrix.sh
#
# Override engine: CONTAINER_ENGINE=docker ./scripts/ci/linux-matrix.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="${CONTAINER_ENGINE:-}"
if [[ -z "$ENGINE" ]]; then
  if command -v podman >/dev/null 2>&1; then
    ENGINE=podman
  elif command -v docker >/dev/null 2>&1; then
    ENGINE=docker
  else
    echo "Install podman or docker, or set CONTAINER_ENGINE." >&2
    exit 1
  fi
fi

# label|image (official python images ship pip; same install path everywhere)
declare -a OFFICIAL_PYTHON=(
  "debian-12-glibc|python:3.12-slim-bookworm"
  "alpine-musl|python:3.12-alpine"
)

run_in_python_image() {
  local label=$1 image=$2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ ${label} (${image})"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  $ENGINE run --pull=missing --rm \
    -v "${ROOT}:/work:ro" \
    "${image}" \
    sh -euc '
      if command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq && apt-get install -y -qq libatomic1
      fi
      rm -rf /tmp/psrc
      cp -a /work /tmp/psrc
      cd /tmp/psrc
      pip install --root-user-action ignore -q -U pip
      pip install --root-user-action ignore -q -e ".[dev]"
      ruff check src/
      if [ -f /etc/alpine-release ]; then
        echo "Note: skipping pyright on Alpine (Pyright prebuilt Node is glibc-only)."
      else
        pyright
      fi
      pytest -q
    '
}

run_in_ubuntu2404() {
  local image="ubuntu:24.04"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "▶ ubuntu-24.04 (${image})"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  $ENGINE run --pull=missing --rm \
    -e DEBIAN_FRONTEND=noninteractive \
    -v "${ROOT}:/work:ro" \
    "${image}" \
    bash -euo pipefail -c '
      apt-get update -qq
      apt-get install -y -qq python3.12 python3.12-venv ca-certificates libatomic1
      python3.12 -m venv /tmp/venv
      /tmp/venv/bin/pip install --root-user-action ignore -q -U pip
      rm -rf /tmp/psrc
      cp -a /work /tmp/psrc
      cd /tmp/psrc
      /tmp/venv/bin/pip install --root-user-action ignore -q -e ".[dev]"
      export PATH="/tmp/venv/bin:${PATH}"
      ruff check src/
      pyright
      pytest -q
    '
}

if [[ -n "${LINUX_MATRIX_IMAGE:-}" ]]; then
  case "${LINUX_MATRIX_IMAGE}" in
    ubuntu:24.04)
      run_in_ubuntu2404
      ;;
    *)
      run_in_python_image "custom" "${LINUX_MATRIX_IMAGE}"
      ;;
  esac
  exit 0
fi

for entry in "${OFFICIAL_PYTHON[@]}"; do
  label="${entry%%|*}"
  image="${entry#*|}"
  run_in_python_image "${label}" "${image}"
done

run_in_ubuntu2404

echo "All matrix targets passed."
