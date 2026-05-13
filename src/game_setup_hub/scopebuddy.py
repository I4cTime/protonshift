"""ScopeBuddy config paths, parsing, auto-detect capabilities, and presets."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from game_setup_hub.fsutil import atomic_write_text
from game_setup_hub.paths import sanitize_filename
from game_setup_hub.tool_check import find_scopebuddy, find_tool, is_tool_available

SCOPEBUDDY_CONFIG_DIR = Path.home() / ".config" / "scopebuddy"
SCOPEBUDDY_GLOBAL_CONF = SCOPEBUDDY_CONFIG_DIR / "scb.conf"
SCOPEBUDDY_APPID_DIR = SCOPEBUDDY_CONFIG_DIR / "AppID"
SCOPEBUDDY_ENVVARS_DIR = SCOPEBUDDY_CONFIG_DIR / "envvars"

SCB_KNOWN_KEYS: tuple[str, ...] = (
    "SCB_GAMESCOPE_ARGS",
    "SCB_AUTO_RES",
    "SCB_AUTO_HDR",
    "SCB_AUTO_VRR",
    "SCB_AUTO_REFRESH",
    "SCB_AUTO_FRAME_LIMIT",
    "SCB_NOSCOPE",
    "SCB_NESTEDFIX",
    "SCB_APPENDMODE",
    "SCB_DEBUG",
)

SCOPEBUDDY_PRESETS: dict[str, dict[str, str]] = {
    "4K HDR VRR": {
        "SCB_GAMESCOPE_ARGS": "-W 3840 -H 2160 -w 3840 -h 2160 -f -b",
        "SCB_AUTO_RES": "1",
        "SCB_AUTO_HDR": "1",
        "SCB_AUTO_VRR": "1",
    },
    "1080p capped 60": {
        "SCB_GAMESCOPE_ARGS": "-W 1920 -H 1080 -w 1920 -h 1080 -f -b -r 60",
        "SCB_AUTO_RES": "0",
    },
    "Mangoapp default": {
        "SCB_GAMESCOPE_ARGS": "--mangoapp -f -b",
        "SCB_AUTO_RES": "1",
    },
}


def _strip_inline_comment_unquoted(value: str) -> str:
    """Remove ``# ...`` only when ``#`` is not inside simple quotes."""
    in_single = in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return value[:i].rstrip()
    return value.rstrip()


def parse_scb_conf(path: Path) -> dict[str, str]:
    """Parse a bash-style ``scb.conf`` into key/value pairs.

    Lines like ``export KEY=val``, ``KEY="quoted"``, toggles ``KEY=1``.
    """
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = rest.strip()
        val = _strip_inline_comment_unquoted(val)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            inner = val[1:-1]
            out[key] = inner
        else:
            try:
                toks = shlex.split(val, posix=True)
                out[key] = " ".join(toks) if len(toks) > 1 else (toks[0] if toks else "")
            except ValueError:
                out[key] = val
    return out


def write_scb_conf(path: Path, cfg: dict[str, str]) -> bool:
    """Write ``cfg`` as bash ``KEY=value`` lines (quoted with :func:`shlex.quote`)."""
    lines: list[str] = []
    for key, value in cfg.items():
        key = key.strip()
        if not key:
            continue
        if value == "":
            lines.append(f"{key}=")
        else:
            lines.append(f"{key}={shlex.quote(value)}")
    body = "\n".join(lines) + ("\n" if lines else "")
    try:
        atomic_write_text(path, body)
        return True
    except OSError:
        return False


def read_scopebuddy_version(binary_path: str) -> str:
    """Best-effort version from the ScopeBuddy script (``SCB_VER=``)."""
    try:
        p = Path(binary_path)
        if not p.is_file():
            return ""
        head = p.read_text(encoding="utf-8", errors="ignore")[:12_000]
        m = re.search(r"SCB_VER=[\"']?([0-9.]+)[\"']?", head)
        if m:
            return m.group(1)
    except OSError:
        pass
    return ""


def scopebuddy_available_info() -> dict[str, str | bool]:
    """Return availability, invoke name, path, version, and config dir."""
    found = find_scopebuddy()
    if not found:
        return {
            "available": False,
            "binary": "",
            "path": "",
            "version": "",
            "config_dir": str(SCOPEBUDDY_CONFIG_DIR),
        }
    invoke, path = found
    return {
        "available": True,
        "binary": invoke,
        "path": path,
        "version": read_scopebuddy_version(path),
        "config_dir": str(SCOPEBUDDY_CONFIG_DIR),
    }


def _gdctl_supports_json(gdctl: str) -> bool:
    try:
        r = subprocess.run(
            [gdctl, "show", "--format=json"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def detect_auto_capabilities() -> dict[str, bool]:
    """Which ``SCB_AUTO_*`` backends are likely usable on this session."""
    jq = is_tool_available("jq")
    kde = bool(os.environ.get("KDE_FULL_SESSION")) and bool(find_tool("kscreen-doctor")) and jq

    is_gnome_session = os.environ.get("XDG_CURRENT_DESKTOP", "").upper().find("GNOME") >= 0 or (
        (os.environ.get("DESKTOP_SESSION") or "").lower() == "gnome"
    )
    gdctl_path = find_tool("gdctl")
    gnome_gdctl = bool(
        is_gnome_session and jq and gdctl_path is not None and _gdctl_supports_json(gdctl_path)
    )

    gnome_randr = bool(find_tool("gnome-randr"))
    wlroots = bool(find_tool("wlr-randr")) and jq

    return {
        "kde": kde,
        "gnome_gdctl": gnome_gdctl,
        "gnome_randr": gnome_randr,
        "wlroots": wlroots,
        "jq": jq,
    }


def per_app_conf_path(app_key: str) -> Path:
    """Path to ``AppID/<sanitized>.conf`` for a Steam app id or Heroic/Lutris slug."""
    safe = sanitize_filename(app_key.replace(":", "_").replace("/", "_"), fallback="game")
    return SCOPEBUDDY_APPID_DIR / f"{safe}.conf"


def list_per_app_overrides() -> list[dict[str, str]]:
    """List existing per-app override files under ``AppID/``."""
    if not SCOPEBUDDY_APPID_DIR.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for p in sorted(SCOPEBUDDY_APPID_DIR.glob("*.conf")):
        stem = p.stem
        rows.append({"key": stem, "path": str(p)})
    return rows


def read_global_config() -> dict[str, str]:
    return parse_scb_conf(SCOPEBUDDY_GLOBAL_CONF)


def write_global_config(cfg: dict[str, str]) -> bool:
    SCOPEBUDDY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(SCOPEBUDDY_GLOBAL_CONF, cfg)


def read_per_app_config(app_key: str) -> tuple[Path, bool, dict[str, str]]:
    path = per_app_conf_path(app_key)
    exists = path.is_file()
    return path, exists, parse_scb_conf(path) if exists else {}


def write_per_app_config(app_key: str, cfg: dict[str, str]) -> bool:
    path = per_app_conf_path(app_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(path, cfg)


def delete_per_app_config(app_key: str) -> bool:
    path = per_app_conf_path(app_key)
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def envvars_path(name: str) -> Path:
    """Path to ``envvars/<sanitized>.conf`` for a named env-var snippet."""
    safe = sanitize_filename(name.replace(":", "_").replace("/", "_"), fallback="profile")
    return SCOPEBUDDY_ENVVARS_DIR / f"{safe}.conf"


def list_envvars() -> list[dict[str, str]]:
    """List existing envvars snippet files under ``envvars/``."""
    if not SCOPEBUDDY_ENVVARS_DIR.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for p in sorted(SCOPEBUDDY_ENVVARS_DIR.glob("*.conf")):
        rows.append({"name": p.stem, "path": str(p)})
    return rows


def read_envvars(name: str) -> tuple[Path, bool, dict[str, str]]:
    path = envvars_path(name)
    exists = path.is_file()
    return path, exists, parse_scb_conf(path) if exists else {}


def write_envvars(name: str, cfg: dict[str, str]) -> bool:
    path = envvars_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(path, cfg)


def delete_envvars(name: str) -> bool:
    path = envvars_path(name)
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def rescan_tools() -> dict[str, str | bool]:
    """Force re-detection of ``scb`` / ``scopebuddy`` (clears tool_check cache)."""
    from game_setup_hub.tool_check import find_tool as _ft

    _ft.cache_clear()
    return scopebuddy_available_info()
