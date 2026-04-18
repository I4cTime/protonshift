"""ProtonShift FastAPI backend.

Public surface: ``app`` (the FastAPI instance) and ``cli`` (the entry point
the ``protonshift-api`` console script and Electron call into).

For backwards compatibility with tests and code that monkeypatched the old
flat ``api.py`` module, a few shared globals are re-exposed via the package
namespace. New code should reach into :mod:`game_setup_hub.api._state`
directly instead.
"""

from __future__ import annotations

from typing import Any

from ..steam import is_steam_running
from . import _state
from ._app import app, cli

__all__ = ["app", "cli", "is_steam_running"]


def __getattr__(name: str) -> Any:
    """Back-compat: forward legacy ``api._API_TOKEN`` etc. to ``_state``."""
    mapping = {
        "_API_TOKEN": "API_TOKEN",
        "_config_path": "config_path",
        "_steam_root": "steam_root",
        "_steam_discovered": "steam_discovered",
        "_vdf_lock": "vdf_lock",
        "_env_lock": "env_lock",
        "_profiles_lock": "profiles_lock",
        "_mangohud_lock": "mangohud_lock",
        "_heroic_lock": "heroic_lock",
    }
    target = mapping.get(name)
    if target is not None:
        return getattr(_state, target)
    raise AttributeError(f"module 'game_setup_hub.api' has no attribute {name!r}")


