"""Game discovery + Steam/Heroic/Lutris listing + per-game Steam config."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...heroic import discover_heroic_games
from ...lutris import discover_lutris_games
from ...steam import discover_games, get_available_proton_tools, is_steam_running
from ...vdf_config import (
    get_compat_tool,
    get_launch_options,
    set_compat_tool,
    set_launch_options,
)
from .. import _state
from .._helpers import (
    heroic_game_to_response,
    lutris_game_to_response,
    steam_game_to_response,
)
from .._models import (
    CompatToolRequest,
    LaunchOptionsRequest,
    StatusResponse,
)

router = APIRouter()


@router.get("/games")
async def list_games() -> dict[str, Any]:
    _state.ensure_steam()
    _, steam_games = discover_games()
    heroic_games = discover_heroic_games()
    lutris_games = discover_lutris_games()
    return {
        "steam": [steam_game_to_response(g) for g in steam_games],
        "heroic": [heroic_game_to_response(g) for g in heroic_games],
        "lutris": [lutris_game_to_response(g) for g in lutris_games],
        "steam_running": is_steam_running(),
    }


@router.get("/games/{app_id}/launch-options")
async def get_game_launch_options(app_id: str) -> dict[str, str]:
    _state.ensure_steam()
    if not _state.config_path:
        return {"options": ""}
    try:
        opts = get_launch_options(_state.config_path, app_id)
    except (OSError, KeyError, ValueError) as exc:
        _state.log.warning("get_launch_options(%s) failed: %s", app_id, exc)
        opts = ""
    return {"options": opts}


@router.put("/games/{app_id}/launch-options")
async def update_launch_options(app_id: str, body: LaunchOptionsRequest) -> StatusResponse:
    _state.ensure_steam()
    if not _state.config_path:
        raise HTTPException(status_code=404, detail="Steam localconfig.vdf not found")
    if is_steam_running():
        # Steam holds localconfig.vdf in memory and rewrites on shutdown,
        # so any edit while it is running gets clobbered.
        raise HTTPException(
            status_code=409,
            detail="Steam is running. Quit Steam fully before editing launch options.",
        )
    async with _state.vdf_lock:
        ok = set_launch_options(_state.config_path, app_id, body.options)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write localconfig.vdf")
    return StatusResponse(success=True)


@router.get("/games/{app_id}/compat-tool")
async def get_game_compat_tool(app_id: str) -> dict[str, str]:
    _state.ensure_steam()
    if not _state.config_path:
        return {"tool": ""}
    try:
        tool = get_compat_tool(_state.config_path, app_id)
    except (OSError, KeyError, ValueError) as exc:
        _state.log.warning("get_compat_tool(%s) failed: %s", app_id, exc)
        tool = ""
    return {"tool": tool}


@router.put("/games/{app_id}/compat-tool")
async def update_compat_tool(app_id: str, body: CompatToolRequest) -> StatusResponse:
    _state.ensure_steam()
    if not _state.config_path:
        raise HTTPException(status_code=404, detail="Steam localconfig.vdf not found")
    if is_steam_running():
        raise HTTPException(
            status_code=409,
            detail="Steam is running. Quit Steam fully before changing the compat tool.",
        )
    async with _state.vdf_lock:
        ok = set_compat_tool(_state.config_path, app_id, body.tool_name)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write localconfig.vdf")
    return StatusResponse(success=True)


@router.get("/games/{app_id}/proton-tools")
async def list_proton_tools(app_id: str) -> dict[str, Any]:
    _state.ensure_steam()
    tools = get_available_proton_tools(_state.steam_root)
    current = ""
    if _state.config_path:
        try:
            current = get_compat_tool(_state.config_path, app_id)
        except (OSError, KeyError, ValueError) as exc:
            _state.log.warning("get_compat_tool(%s) failed in proton-tools: %s", app_id, exc)
    return {"tools": tools, "current": current}


@router.get("/steam/status")
async def steam_status() -> dict[str, Any]:
    _state.ensure_steam()
    return {
        "running": is_steam_running(),
        "root": str(_state.steam_root) if _state.steam_root else None,
        "config_path": str(_state.config_path) if _state.config_path else None,
    }
