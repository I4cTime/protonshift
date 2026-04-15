"""Game-specific fixes database — built-in and user-contributed."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"
_USER_FIXES_DIR = Path.home() / ".config" / "protonshift" / "fixes"


@dataclass
class GameFix:
    title: str
    description: str
    fix_type: str  # "env" or "launch_arg"
    key: str  # env var key (empty for launch_arg)
    value: str
    source: str  # "builtin" or "user"


def _load_builtin_fixes() -> dict[str, list[dict[str, Any]]]:
    path = _DATA_DIR / "known_fixes.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_user_fixes(app_id: str) -> list[dict[str, Any]]:
    path = _USER_FIXES_DIR / f"{app_id}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _dict_to_fix(d: dict[str, Any], source: str) -> GameFix:
    return GameFix(
        title=d.get("title", ""),
        description=d.get("description", ""),
        fix_type=d.get("type", "env"),
        key=d.get("key", ""),
        value=d.get("value", ""),
        source=source,
    )


def get_fixes(app_id: str) -> list[GameFix]:
    """Get all applicable fixes for a game (built-in + user + common)."""
    builtin = _load_builtin_fixes()

    fixes: list[GameFix] = []

    for entry in builtin.get(app_id, []):
        fixes.append(_dict_to_fix(entry, "builtin"))

    for entry in builtin.get("_common", []):
        fixes.append(_dict_to_fix(entry, "builtin"))

    for entry in _load_user_fixes(app_id):
        fixes.append(_dict_to_fix(entry, "user"))

    return fixes


def add_user_fix(
    app_id: str,
    title: str,
    description: str,
    fix_type: str,
    key: str,
    value: str,
) -> bool:
    """Add a user-contributed fix for a game. Returns True on success."""
    _USER_FIXES_DIR.mkdir(parents=True, exist_ok=True)
    path = _USER_FIXES_DIR / f"{app_id}.json"

    existing = _load_user_fixes(app_id)
    existing.append({
        "title": title,
        "description": description,
        "type": fix_type,
        "key": key,
        "value": value,
    })

    try:
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
