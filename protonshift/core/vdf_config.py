"""Read/write Steam localconfig.vdf LaunchOptions — fail-closed.

The old backend swallowed a parse failure into ``{}`` and then rebuilt a minimal
tree over the top, so a corrupt or mid-write ``localconfig.vdf`` (Steam holds it
open while running) got overwritten with a stub — destroying every launch option
and per-app setting (review #20, critical). Here a parse failure on an existing
file makes the write **refuse**, never overwrite.

Scope: LaunchOptions only. CompatToolMapping is intentionally left out — the old
code read/wrote it in the wrong file (review #H1); porting it needs the
config.vdf/InstallConfigStore fix, done separately.
"""

from __future__ import annotations

import io
from pathlib import Path

import vdf

from .fsutil import atomic_write_text


class VdfParseError(Exception):
    """Raised when an existing VDF file cannot be parsed."""


def _get_apps_node(data: dict) -> dict | None:
    """Navigate to UserLocalConfigStore.Software.Valve.Steam.apps."""
    try:
        steam = data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]
        return steam.get("apps") or steam.get("Apps")
    except (KeyError, TypeError):
        return None


def _load_vdf_strict(path: Path) -> dict:
    """Load a VDF file, raising ``VdfParseError`` if it exists but won't parse.

    A *missing* file is not an error (returns ``{}``) — that's a legitimate
    first-write. A present-but-unparseable file raises, so callers can refuse to
    clobber it.
    """
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = vdf.load(f)
    except (SyntaxError, ValueError, OSError) as exc:
        raise VdfParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise VdfParseError("unexpected top-level VDF structure")
    return data


def _dump_vdf_atomic(path: Path, data: dict) -> bool:
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


def read_launch_options(config_path: Path, app_id: str) -> tuple[bool, str]:
    """Return ``(ok, options)``. ``ok`` is False if the file couldn't be parsed.

    Distinguishing a read failure from "no options set" lets the UI avoid the
    trap of showing an empty field for a config it merely failed to read.
    """
    try:
        data = _load_vdf_strict(config_path)
    except VdfParseError:
        return False, ""
    apps = _get_apps_node(data)
    if not apps:
        return True, ""
    app = apps.get(app_id)
    if not isinstance(app, dict):
        return True, ""
    return True, app.get("LaunchOptions", "")


def set_launch_options(config_path: Path, app_id: str, options: str) -> bool:
    """Set LaunchOptions for a game. Returns False (writing nothing) if the
    existing file can't be parsed — never overwrites an unreadable config."""
    try:
        data = _load_vdf_strict(config_path)
    except VdfParseError:
        # #20 fix: the file exists but is unparseable — abort rather than
        # rebuild a stub over the user's entire localconfig.
        return False

    store = data.setdefault("UserLocalConfigStore", {})
    software = store.setdefault("Software", {})
    valve = software.setdefault("Valve", {})
    steam = valve.setdefault("Steam", {})

    # Steam files in the wild carry either casing; some carry *both*. The old
    # ``setdefault("apps", steam.pop("Apps", {}))`` popped and silently
    # discarded the entire "Apps" subtree whenever "apps" also existed, so the
    # next save dropped those per-app entries. Merge instead — existing
    # lowercase "apps" keys win on collision.
    legacy = steam.pop("Apps", None)
    apps = steam.get("apps")
    if not isinstance(apps, dict):
        apps = {}
        steam["apps"] = apps
    if isinstance(legacy, dict):
        for k, v in legacy.items():
            apps.setdefault(k, v)

    if app_id not in apps or not isinstance(apps[app_id], dict):
        apps[app_id] = {}
    apps[app_id]["LaunchOptions"] = options

    return _dump_vdf_atomic(config_path, data)
