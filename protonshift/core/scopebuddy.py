"""ScopeBuddy config: paths, parsing, presets, availability.

Lifted from the old backend with two config-safety fixes:

* #M1 — ``parse_scb_conf`` now inverts ``write_scb_conf``'s ``shlex.quote`` by
  always ``shlex.split``-ing the value, instead of a naive outer-quote strip
  that returned raw bash-escaped garbage for values containing quotes.
* #M2 — ``write_scb_conf`` merges into the existing file line-by-line: comments,
  blank lines, bash logic (``if/then/export …``), and unmanaged assignments are
  preserved verbatim. Only ``SCB_*`` keys the editor manages are updated,
  inserted, or (when removed in the UI) dropped. ``scb.conf`` is a sourced bash
  script — the old rewrite-from-dict destroyed everything but plain assignments.

Scope of the first slice: the global scb.conf. Per-app / envvars helpers are
kept for later slices; the same parse/write fixes cover them.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from .fsutil import atomic_write_text
from .paths import sanitize_filename
from .tool_check import find_scopebuddy, find_tool, is_tool_available

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


def _assignment_key(line: str) -> str | None:
    """Return the variable name if ``line`` is a simple assignment, else None."""
    s = line.strip()
    if s.startswith("export "):
        s = s[7:].strip()
    if "=" not in s:
        return None
    key = s.partition("=")[0].strip()
    if key and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return key
    return None


def _format_line(key: str, value: str) -> str:
    return f"{key}=" if value == "" else f"{key}={shlex.quote(value)}"


def _block_delta(line: str) -> int:
    """Rough bash block nesting change for a line (then/do open, fi/done close).

    Not a real parser — just enough to avoid touching assignments *inside* a
    control structure, so removing a managed key can't leave an empty
    ``then``/``do`` block (invalid bash).
    """
    opens = len(re.findall(r"\b(?:then|do)\b", line))
    closes = len(re.findall(r"\b(?:fi|done)\b", line))
    return opens - closes


def parse_scb_conf(path: Path) -> dict[str, str]:
    """Parse a bash-style ``scb.conf`` into key/value pairs.

    Values are round-tripped through ``shlex`` so a ``shlex.quote``d write reads
    back identically (the #M1 fix).
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
        val = _strip_inline_comment_unquoted(rest.strip())
        try:
            out[key] = " ".join(shlex.split(val, posix=True))
        except ValueError:
            out[key] = val
    return out


def write_scb_conf(path: Path, cfg: dict[str, str]) -> bool:
    """Merge ``cfg`` into ``path``, preserving comments and bash logic (#M2)."""
    try:
        existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        return False

    written: set[str] = set()
    out: list[str] = []
    depth = 0
    for raw in existing:
        key = _assignment_key(raw)
        top_level = depth == 0
        if key is None or not top_level:
            out.append(raw)  # comment / blank / bash logic / inside-block — keep
        elif key in cfg:
            out.append(_format_line(key, cfg[key]))  # managed update
            written.add(key)
        elif key.startswith("SCB_"):
            pass  # a top-level managed key the UI removed — drop it
        else:
            out.append(raw)  # unmanaged assignment — leave alone
        depth = max(0, depth + _block_delta(raw))

    for key, value in cfg.items():
        if key.strip() and key not in written:
            out.append(_format_line(key.strip(), value))  # new key

    body = "\n".join(out)
    if body and not body.endswith("\n"):
        body += "\n"
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


def read_global_config() -> dict[str, str]:
    return parse_scb_conf(SCOPEBUDDY_GLOBAL_CONF)


def write_global_config(cfg: dict[str, str]) -> bool:
    SCOPEBUDDY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(SCOPEBUDDY_GLOBAL_CONF, cfg)


def per_app_conf_path(app_key: str) -> Path:
    """Path to ``AppID/<sanitized>.conf`` for a Steam app id or Heroic/Lutris slug."""
    safe = sanitize_filename(app_key.replace(":", "_").replace("/", "_"), fallback="game")
    return SCOPEBUDDY_APPID_DIR / f"{safe}.conf"


def list_per_app_overrides() -> list[dict[str, str]]:
    if not SCOPEBUDDY_APPID_DIR.is_dir():
        return []
    return [{"key": p.stem, "path": str(p)} for p in sorted(SCOPEBUDDY_APPID_DIR.glob("*.conf"))]


def read_per_app_config(app_key: str) -> tuple[bool, dict[str, str]]:
    """``(exists, config)`` for a per-app override. Comment/quote-safe parse."""
    path = per_app_conf_path(app_key)
    return path.is_file(), parse_scb_conf(path)


def write_per_app_config(app_key: str, cfg: dict[str, str]) -> bool:
    """Write a per-app override (creates ``AppID/`` as needed, merge-preserving)."""
    path = per_app_conf_path(app_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(path, cfg)


def delete_per_app_config(app_key: str) -> bool:
    """Remove a per-app override file."""
    try:
        per_app_conf_path(app_key).unlink(missing_ok=True)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Named envvar snippets (envvars/<name>.conf)
# --------------------------------------------------------------------------- #

def envvars_path(name: str) -> Path:
    """Path to ``envvars/<sanitized>.conf`` for a named env-var snippet."""
    safe = sanitize_filename(name.replace(":", "_").replace("/", "_"), fallback="profile")
    return SCOPEBUDDY_ENVVARS_DIR / f"{safe}.conf"


def list_envvars() -> list[dict[str, str]]:
    """List existing envvars snippet files under ``envvars/``."""
    if not SCOPEBUDDY_ENVVARS_DIR.is_dir():
        return []
    return [{"name": p.stem, "path": str(p)} for p in sorted(SCOPEBUDDY_ENVVARS_DIR.glob("*.conf"))]


def read_envvars(name: str) -> tuple[bool, dict[str, str]]:
    """``(exists, config)`` for a named snippet; comment/quote-safe parse."""
    path = envvars_path(name)
    exists = path.is_file()
    return exists, (parse_scb_conf(path) if exists else {})


def write_envvars(name: str, cfg: dict[str, str]) -> bool:
    """Write a named env-var snippet (merge-preserving)."""
    path = envvars_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_scb_conf(path, cfg)


def delete_envvars(name: str) -> bool:
    """Remove a named env-var snippet file."""
    try:
        envvars_path(name).unlink(missing_ok=True)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# SCB_AUTO_* capability detection
# --------------------------------------------------------------------------- #

def _gdctl_supports_json(gdctl_path: str) -> bool:
    """True if this gdctl understands ``--format=json`` (GNOME 47+)."""
    try:
        r = subprocess.run(  # noqa: S603 — path from find_tool, constant args
            [gdctl_path, "show", "--help"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "json" in (r.stdout + r.stderr).lower()


def detect_auto_capabilities() -> dict[str, bool]:
    """Which ``SCB_AUTO_*`` backends are likely usable on this session.

    ScopeBuddy's auto res/HDR/VRR features shell out to a display tool + ``jq``
    to read the primary monitor. This reports which backend is present so the
    UI can tell the user whether the auto toggles will actually do anything.
    """
    jq = is_tool_available("jq")
    kde = (
        bool(os.environ.get("KDE_FULL_SESSION"))
        and bool(find_tool("kscreen-doctor"))
        and jq
    )
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    is_gnome = "GNOME" in desktop or (os.environ.get("DESKTOP_SESSION") or "").lower() == "gnome"
    gdctl_path = find_tool("gdctl")
    gnome_gdctl = bool(is_gnome and jq and gdctl_path and _gdctl_supports_json(gdctl_path))
    wlroots = bool(find_tool("wlr-randr")) and jq
    return {
        "kde": kde,
        "gnome_gdctl": gnome_gdctl,
        "gnome_randr": bool(find_tool("gnome-randr")),
        "wlroots": wlroots,
        "jq": jq,
        "any": bool(kde or gnome_gdctl or wlroots),
    }
