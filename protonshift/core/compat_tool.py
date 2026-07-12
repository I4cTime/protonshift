"""Per-game Proton version (CompatToolMapping) — in the *correct* file.

The old backend read/wrote ``CompatToolMapping`` in ``localconfig.vdf`` under
``UserLocalConfigStore`` — but Steam keeps it in ``<steam_root>/config/config.vdf``
under ``InstallConfigStore.Software.Valve.Steam.CompatToolMapping``. So the
feature silently no-oped: ProtonShift injected a node Steam ignores, then read
its own bogus node back and reported success (review #H1).

This module targets config.vdf, navigates nodes case-insensitively (real-world
files vary: ``Software``/``software``, ``Valve``/``valve``), and is fail-closed
like ``vdf_config``: an unparseable existing file refuses the write.
"""

from __future__ import annotations

import io
from pathlib import Path

import vdf

from .fsutil import atomic_write_text
from .vdf_config import VdfParseError, _load_vdf_strict


def get_config_vdf_path(steam_root: Path) -> Path:
    return steam_root / "config" / "config.vdf"


def _child(node: dict, name: str) -> dict | None:
    """Case-insensitive child lookup (returns the real value or None)."""
    if not isinstance(node, dict):
        return None
    for k, v in node.items():
        if k.lower() == name.lower():
            return v if isinstance(v, dict) else None
    return None


def _child_setdefault(node: dict, name: str) -> dict:
    """Case-insensitive setdefault that preserves existing key casing."""
    for k, v in node.items():
        if k.lower() == name.lower():
            if isinstance(v, dict):
                return v
            node[k] = {}
            return node[k]
    node[name] = {}
    return node[name]


def _mapping_node(data: dict, create: bool = False) -> dict | None:
    """Navigate InstallConfigStore.Software.Valve.Steam.CompatToolMapping."""
    if create:
        node = _child_setdefault(data, "InstallConfigStore")
        for name in ("Software", "Valve", "Steam"):
            node = _child_setdefault(node, name)
        return _child_setdefault(node, "CompatToolMapping")
    node = _child(data, "InstallConfigStore")
    for name in ("Software", "Valve", "Steam"):
        if node is None:
            return None
        node = _child(node, name)
    return _child(node, "CompatToolMapping") if node is not None else None


def read_compat_tool(config_path: Path, app_id: str) -> tuple[bool, str]:
    """Return ``(ok, tool_name)``. ``ok`` False when the file won't parse."""
    try:
        data = _load_vdf_strict(config_path)
    except VdfParseError:
        return False, ""
    mapping = _mapping_node(data)
    if not mapping:
        return True, ""
    entry = mapping.get(app_id, "")
    if isinstance(entry, dict):
        return True, entry.get("name", "")
    return True, entry or ""


def set_compat_tool(config_path: Path, app_id: str, tool_name: str) -> bool:
    """Set (or clear, with ``""``) the Proton tool for a game. Fail-closed.

    Entries are written in Steam's own shape:
    ``{"name": <tool>, "config": "", "priority": "250"}``.
    """
    try:
        data = _load_vdf_strict(config_path)
    except VdfParseError:
        return False  # never rebuild a stub over an unreadable config.vdf

    mapping = _mapping_node(data, create=True)
    if tool_name:
        mapping[app_id] = {"name": tool_name, "config": "", "priority": "250"}
    else:
        mapping.pop(app_id, None)

    buf = io.StringIO()
    try:
        vdf.dump(data, buf, pretty=True)
    except (TypeError, ValueError):
        return False
    try:
        atomic_write_text(config_path, buf.getvalue())
    except OSError:
        return False
    return True
