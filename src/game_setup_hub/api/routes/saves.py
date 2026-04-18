"""Game save discovery, backup, restore."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...fsutil import human_size
from ...paths import PathValidationError, validate_user_path
from ...saves import backup_saves, find_save_paths, list_backups, restore_backup
from ...steam import discover_games
from .. import _state
from .._models import (
    BackupInfoResponse,
    BackupRequest,
    RestoreRequest,
    SaveLocationResponse,
    StatusResponse,
)

router = APIRouter()


@router.get("/games/{app_id}/saves")
async def game_saves(app_id: str, prefix_path: str | None = None) -> list[SaveLocationResponse]:
    prefix = prefix_path
    if not prefix:
        _state.ensure_steam()
        _, steam_games = discover_games()
        game = next((g for g in steam_games if g.app_id == app_id), None)
        prefix = str(game.compatdata_path) if game and game.compatdata_path else None
    locations = find_save_paths(app_id, prefix)
    return [
        SaveLocationResponse(
            path=loc.path,
            exists=loc.exists,
            size_bytes=loc.size_bytes,
            size_human=human_size(loc.size_bytes),
            label=loc.label,
        )
        for loc in locations
    ]


@router.post("/games/{app_id}/saves/backup")
async def backup_game_saves(app_id: str, body: BackupRequest) -> dict[str, Any]:
    result = backup_saves(app_id, body.paths)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create backup")
    return {"path": result}


@router.get("/games/{app_id}/saves/backups")
async def list_game_backups(app_id: str) -> list[BackupInfoResponse]:
    backups = list_backups(app_id)
    return [
        BackupInfoResponse(
            path=b.path,
            filename=b.filename,
            size_bytes=b.size_bytes,
            size_human=human_size(b.size_bytes),
            created=b.created,
        )
        for b in backups
    ]


@router.post("/games/{app_id}/saves/restore")
async def restore_game_saves(app_id: str, body: RestoreRequest) -> StatusResponse:
    try:
        target = validate_user_path(body.target_dir, allow_missing=True)
    except PathValidationError as exc:
        raise HTTPException(status_code=400, detail=f"target_dir rejected: {exc}") from exc
    ok = restore_backup(body.backup_path, str(target))
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to restore backup")
    return StatusResponse(success=True, message="Backup restored")
