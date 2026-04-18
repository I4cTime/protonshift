"""Read/write Steam localconfig.vdf for LaunchOptions and CompatToolMapping."""

from __future__ import annotations

import io
from pathlib import Path

import vdf

from .fsutil import atomic_write_text


def _get_apps_node(data: dict) -> dict | None:
    """Navigate to UserLocalConfigStore.Software.Valve.Steam.apps (lowercase)."""
    try:
        store = data["UserLocalConfigStore"]
        software = store["Software"]
        valve = software["Valve"]
        steam = valve["Steam"]
        return steam.get("apps") or steam.get("Apps")
    except KeyError:
        return None


def _load_vdf(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = vdf.load(f)
        return data if isinstance(data, dict) else {}
    except (SyntaxError, ValueError, OSError):
        return {}


def _dump_vdf_atomic(path: Path, data: dict) -> bool:
    """Serialise ``data`` and atomically replace ``path``.

    Atomicity matters here because partial writes to ``localconfig.vdf`` can
    nuke every launch option / compat tool mapping for the user. Steam itself
    holds the file open while running, so a torn write is more than a theory.
    """
    buf = io.StringIO()
    try:
        vdf.dump(data, buf, pretty=True)
    except (TypeError, ValueError):
        return False
    try:
        atomic_write_text(path, buf.getvalue())
    except OSError:
        return False
    return True


def get_launch_options(config_path: Path, app_id: str) -> str:
    """Get LaunchOptions for a game. Returns empty string if not set."""
    data = _load_vdf(config_path)
    apps = _get_apps_node(data)
    if not apps:
        return ""
    app = apps.get(app_id)
    if not isinstance(app, dict):
        return ""
    return app.get("LaunchOptions", "")


def get_compat_tool(config_path: Path, app_id: str) -> str:
    """Get CompatToolMapping for a game. Returns empty if not set."""
    data = _load_vdf(config_path)
    try:
        store = data["UserLocalConfigStore"]
        software = store["Software"]
        valve = software["Valve"]
        steam = valve["Steam"]
        mapping = steam.get("CompatToolMapping") or steam.get("compat_tool_mapping")
        if isinstance(mapping, dict):
            entry = mapping.get(app_id, "")
            if isinstance(entry, dict):
                return entry.get("name", "")
            return entry or ""
    except (KeyError, TypeError):
        pass
    return ""


def set_compat_tool(config_path: Path, app_id: str, tool_name: str) -> bool:
    """Set CompatToolMapping for a game. Use empty string to clear."""
    data = _load_vdf(config_path) if config_path.exists() else {}

    store = data.setdefault("UserLocalConfigStore", {})
    software = store.setdefault("Software", {})
    valve = software.setdefault("Valve", {})
    steam = valve.setdefault("Steam", {})
    mapping = steam.setdefault("CompatToolMapping", steam.get("compat_tool_mapping", {}))
    if not isinstance(mapping, dict):
        mapping = {}
        steam["CompatToolMapping"] = mapping

    if tool_name:
        mapping[app_id] = tool_name
    elif app_id in mapping:
        del mapping[app_id]

    return _dump_vdf_atomic(config_path, data)


def set_launch_options(config_path: Path, app_id: str, options: str) -> bool:
    """Set LaunchOptions for a game. Creates nodes if needed."""
    data = _load_vdf(config_path) if config_path.exists() else {}

    store = data.setdefault("UserLocalConfigStore", {})
    software = store.setdefault("Software", {})
    valve = software.setdefault("Valve", {})
    steam = valve.setdefault("Steam", {})
    apps = steam.setdefault("apps", {})

    if app_id not in apps or not isinstance(apps[app_id], dict):
        apps[app_id] = {}
    apps[app_id]["LaunchOptions"] = options

    return _dump_vdf_atomic(config_path, data)
