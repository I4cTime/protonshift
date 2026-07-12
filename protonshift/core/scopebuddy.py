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
