"""Misc one-shot utilities: protontricks, gamescope, fixes, shader cache, prefix, open-path/uri."""

from __future__ import annotations

import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

from ...fixes import add_user_fix, get_fixes
from ...fsutil import human_size
from ...gamescope import (
    GamescopeOptions,
    build_gamescope_argv,
    build_gamescope_cmd,
    is_gamescope_available,
)
from ...paths import PathValidationError, validate_user_path
from ...prefix import delete_prefix, get_prefix_info
from ...protontricks import COMMON_VERBS, is_protontricks_available, run_protontricks
from ...shader_cache import (
    clear_shader_cache,
    get_shader_cache_info,
    get_total_shader_cache_size,
)
from ...steam import discover_games
from .. import _state
from .._models import (
    GameFixCreateRequest,
    GameFixResponse,
    GamescopeBuildRequest,
    OpenPathRequest,
    OpenUriRequest,
    PrefixInfoResponse,
    ProtontricksRequest,
    ShaderCacheResponse,
    StatusResponse,
)

router = APIRouter()


# --- protontricks ----------------------------------------------------------


@router.post("/games/{app_id}/protontricks")
async def trigger_protontricks(app_id: str, body: ProtontricksRequest) -> StatusResponse:
    if not is_protontricks_available():
        raise HTTPException(status_code=404, detail="Protontricks not installed")
    ok, msg = run_protontricks(app_id, body.verb)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return StatusResponse(success=True, message=msg)


@router.get("/protontricks/verbs")
async def list_protontricks_verbs() -> dict[str, Any]:
    return {
        "available": is_protontricks_available(),
        "verbs": [{"id": v[0], "label": v[1]} for v in COMMON_VERBS],
    }


# --- gamescope -------------------------------------------------------------


@router.get("/gamescope/available")
async def gamescope_available() -> dict[str, bool]:
    return {"available": is_gamescope_available()}


@router.post("/gamescope/build-cmd")
async def gamescope_build(body: GamescopeBuildRequest) -> dict[str, Any]:
    opts = GamescopeOptions(
        output_width=body.output_width,
        output_height=body.output_height,
        game_width=body.game_width,
        game_height=body.game_height,
        fps_limit=body.fps_limit,
        fsr=body.fsr,
        fsr_sharpness=body.fsr_sharpness,
        integer_scale=body.integer_scale,
        hdr=body.hdr,
        nested=body.nested,
        borderless=body.borderless,
        fullscreen=body.fullscreen,
        extra_args=body.extra_args,
    )
    return {
        "command": build_gamescope_cmd(opts),
        "argv": build_gamescope_argv(opts),
    }


# --- fixes ------------------------------------------------------------------


@router.get("/games/{app_id}/fixes")
async def list_game_fixes(app_id: str) -> list[GameFixResponse]:
    fixes = get_fixes(app_id)
    return [
        GameFixResponse(
            title=f.title,
            description=f.description,
            fix_type=f.fix_type,
            key=f.key,
            value=f.value,
            source=f.source,
        )
        for f in fixes
    ]


@router.post("/games/{app_id}/fixes")
async def create_game_fix(app_id: str, body: GameFixCreateRequest) -> StatusResponse:
    ok = add_user_fix(
        app_id=app_id,
        title=body.title,
        description=body.description,
        fix_type=body.fix_type,
        key=body.key,
        value=body.value,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save fix")
    return StatusResponse(success=True)


# --- shader cache -----------------------------------------------------------


@router.get("/games/{app_id}/shader-cache")
async def game_shader_cache(app_id: str) -> ShaderCacheResponse:
    _state.ensure_steam()
    if not _state.steam_root:
        return ShaderCacheResponse(app_id=app_id, path="", exists=False)
    info = get_shader_cache_info(_state.steam_root, app_id)
    return ShaderCacheResponse(
        app_id=app_id,
        path=info.path,
        exists=info.exists,
        size_bytes=info.size_bytes,
        size_human=human_size(info.size_bytes),
    )


@router.delete("/games/{app_id}/shader-cache")
async def clear_game_shader_cache(app_id: str) -> StatusResponse:
    _state.ensure_steam()
    if not _state.steam_root:
        raise HTTPException(status_code=404, detail="Steam root not found")
    ok = clear_shader_cache(_state.steam_root, app_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to clear shader cache")
    return StatusResponse(success=True, message="Shader cache cleared")


@router.get("/shader-cache/total")
async def total_shader_cache() -> dict[str, Any]:
    _state.ensure_steam()
    if not _state.steam_root:
        return {"size_bytes": 0, "size_human": "0.0 B"}
    total = get_total_shader_cache_size(_state.steam_root)
    return {"size_bytes": total, "size_human": human_size(total)}


# --- prefix -----------------------------------------------------------------


@router.get("/games/{app_id}/prefix-info")
async def game_prefix_info(app_id: str, prefix_path: str | None = None) -> PrefixInfoResponse:
    ppath = prefix_path
    if not ppath:
        _state.ensure_steam()
        _, steam_games = discover_games()
        game = next((g for g in steam_games if g.app_id == app_id), None)
        ppath = str(game.compatdata_path) if game and game.compatdata_path else None
    if not ppath:
        return PrefixInfoResponse(path="", exists=False)
    info = get_prefix_info(ppath)
    return PrefixInfoResponse(
        path=info.path,
        exists=info.exists,
        size_bytes=info.size_bytes,
        size_human=human_size(info.size_bytes),
        created=info.created,
        dxvk_version=info.dxvk_version,
        vkd3d_version=info.vkd3d_version,
    )


@router.delete("/games/{app_id}/prefix")
async def delete_game_prefix(app_id: str, prefix_path: str | None = None) -> StatusResponse:
    ppath = prefix_path
    if not ppath:
        _state.ensure_steam()
        _, steam_games = discover_games()
        game = next((g for g in steam_games if g.app_id == app_id), None)
        if not game or not game.compatdata_path:
            raise HTTPException(status_code=404, detail="No prefix found for this game")
        ppath = str(game.compatdata_path)
    try:
        # Reject any prefix path that doesn't live under a user-writable root.
        # Without this check, an attacker who can reach 127.0.0.1 could send
        # ``prefix_path=/etc`` and delete the system config tree.
        validate_user_path(ppath)
    except PathValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ok = delete_prefix(ppath)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete prefix")
    return StatusResponse(
        success=True,
        message="Prefix deleted. The launcher will recreate it on next launch.",
    )


# --- open-path / open-uri ---------------------------------------------------


@router.post("/open-path")
async def open_path(body: OpenPathRequest) -> StatusResponse:
    """Open a file or folder in the system file manager.

    Restricted to user-writable roots (``$HOME``, mounts, ``/tmp``) to keep
    the localhost API from being a generic system-wide xdg-open proxy.
    """
    try:
        target = validate_user_path(body.path)
    except PathValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        subprocess.Popen(["xdg-open", str(target)], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", str(target)], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    return StatusResponse(success=True)


@router.post("/open-uri")
async def open_uri(body: OpenUriRequest) -> StatusResponse:
    """Open a URI (e.g. ``steam://rungameid/...``) with the system handler."""
    try:
        subprocess.Popen(["xdg-open", body.uri], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", body.uri], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    return StatusResponse(success=True)
