"""MangoHud configuration endpoints (global + per-game)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...mangohud import (
    MANGOHUD_PARAMS,
    MANGOHUD_PRESETS,
    get_per_game_config_path,
    is_mangohud_available,
    list_per_game_configs,
    read_mangohud_config,
    write_mangohud_config,
)
from .. import _state
from .._models import MangoHudConfigRequest, StatusResponse

router = APIRouter(prefix="/mangohud")


@router.get("/available")
async def mangohud_available() -> dict[str, bool]:
    return {"available": is_mangohud_available()}


@router.get("/config")
async def get_mangohud_config() -> dict[str, Any]:
    return {
        "config": read_mangohud_config(),
        "params": MANGOHUD_PARAMS,
    }


@router.put("/config")
async def update_mangohud_config(body: MangoHudConfigRequest) -> StatusResponse:
    async with _state.mangohud_lock:
        ok = write_mangohud_config(body.config)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write MangoHud config")
    return StatusResponse(success=True)


@router.get("/presets")
async def get_mangohud_presets() -> dict[str, dict[str, str]]:
    return MANGOHUD_PRESETS


@router.get("/per-game")
async def list_mangohud_per_game() -> list[dict[str, str]]:
    """List all existing per-game MangoHud config files."""
    return list_per_game_configs()


@router.get("/per-game/{game_name}")
async def get_mangohud_per_game_config(game_name: str) -> dict[str, Any]:
    """Read a per-game MangoHud config."""
    conf_path = get_per_game_config_path(game_name)
    return {
        "path": str(conf_path),
        "exists": conf_path.exists(),
        "config": read_mangohud_config(conf_path) if conf_path.exists() else {},
        "params": MANGOHUD_PARAMS,
    }


@router.put("/per-game/{game_name}")
async def update_mangohud_per_game_config(
    game_name: str, body: MangoHudConfigRequest
) -> StatusResponse:
    """Write a per-game MangoHud config."""
    conf_path = get_per_game_config_path(game_name)
    async with _state.mangohud_lock:
        ok = write_mangohud_config(body.config, conf_path)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write per-game MangoHud config")
    return StatusResponse(success=True)
