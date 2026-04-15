"""Read/write Steam localconfig.vdf for LaunchOptions."""

from __future__ import annotations

from pathlib import Path

import vdf


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


def get_launch_options(config_path: Path, app_id: str) -> str:
    """Get LaunchOptions for a game. Returns empty string if not set."""
    if not config_path.exists():
        return ""
    try:
        with open(config_path, encoding="utf-8", errors="replace") as f:
            data = vdf.load(f)
    except (vdf.VDFError, OSError):
        return ""
    apps = _get_apps_node(data)
    if not apps:
        return ""
    app = apps.get(app_id)
    if not isinstance(app, dict):
        return ""
    return app.get("LaunchOptions", "")


def get_compat_tool(config_path: Path, app_id: str) -> str:
    """Get CompatToolMapping for a game. Returns empty if not set."""
    if not config_path.exists():
        return ""
    try:
        with open(config_path, encoding="utf-8", errors="replace") as f:
            data = vdf.load(f)
    except (vdf.VDFError, OSError):
        return ""
    try:
        store = data["UserLocalConfigStore"]
        software = store["Software"]
        valve = software["Valve"]
        steam = valve["Steam"]
        mapping = steam.get("CompatToolMapping") or steam.get("compat_tool_mapping")
        if isinstance(mapping, dict):
            return mapping.get(app_id, "")
    except (KeyError, TypeError):
        pass
    return ""


def set_compat_tool(config_path: Path, app_id: str, tool_name: str) -> bool:
    """Set CompatToolMapping for a game. Use empty string to clear."""
    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8", errors="replace") as f:
                data = vdf.load(f)
        except (vdf.VDFError, OSError):
            return False

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

    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8", newline="\n") as f:
            vdf.dump(data, f, pretty=True)
    except OSError:
        return False
    return True


def set_launch_options(config_path: Path, app_id: str, options: str) -> bool:
    """Set LaunchOptions for a game. Creates nodes if needed."""
    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8", errors="replace") as f:
                data = vdf.load(f)
        except (vdf.VDFError, OSError):
            return False

    # Ensure full structure exists
    store = data.setdefault("UserLocalConfigStore", {})
    software = store.setdefault("Software", {})
    valve = software.setdefault("Valve", {})
    steam = valve.setdefault("Steam", {})
    apps = steam.setdefault("apps", {})

    if app_id not in apps or not isinstance(apps[app_id], dict):
        apps[app_id] = {}
    apps[app_id]["LaunchOptions"] = options

    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8", newline="\n") as f:
            vdf.dump(data, f, pretty=True)
    except OSError:
        return False
    return True
