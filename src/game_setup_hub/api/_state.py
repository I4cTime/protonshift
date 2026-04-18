"""Shared mutable state for the FastAPI app and routers.

Every router imports this module and reads/writes attributes on it so the
locks and cached Steam discovery are shared across the package. Modules
should NOT do ``from ._state import API_TOKEN`` because that copies the
value at import time; use ``_state.API_TOKEN`` instead.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

log = logging.getLogger("protonshift.api")

# Auth token. The Electron main process generates this and passes it through
# ``PROTONSHIFT_API_TOKEN``. Standalone CLI users get a freshly-printed token
# at startup. Empty disables auth (back-compat for ``protonshift-api``
# invocations without setting the env var — only safe on a single-user desktop).
API_TOKEN: str = os.environ.get("PROTONSHIFT_API_TOKEN", "")

# Endpoints exempt from auth. ``/health`` lets Electron poll for readiness
# before the token has propagated; ``/docs`` etc. are FastAPI's own.
AUTH_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})

# Locks for serializing writes to shared resources.
vdf_lock = asyncio.Lock()
env_lock = asyncio.Lock()
profiles_lock = asyncio.Lock()
mangohud_lock = asyncio.Lock()
heroic_lock = asyncio.Lock()

# Cached Steam discovery (resolved once per process).
steam_root: Path | None = None
config_path: Path | None = None
steam_discovered = False


def ensure_steam() -> None:
    """Discover the Steam root + ``localconfig.vdf`` path lazily, once."""
    global steam_root, config_path, steam_discovered
    if steam_discovered:
        return
    from ..steam import discover_games, get_localconfig_path

    steam_root, _ = discover_games()
    if steam_root:
        config_path = get_localconfig_path(steam_root)
    steam_discovered = True
