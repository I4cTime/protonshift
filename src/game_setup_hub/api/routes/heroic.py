"""Heroic Games Launcher integration endpoints."""

from __future__ import annotations

import subprocess

from fastapi import APIRouter, HTTPException

from ...heroic_config import (
    get_heroic_game_config,
    list_heroic_wine_versions,
    set_heroic_launch_options,
    set_heroic_toggles,
    set_heroic_wine_version,
)
from .. import _state
from .._models import (
    HeroicGameConfigResponse,
    HeroicLaunchOptionsRequest,
    HeroicTogglesRequest,
    HeroicWineVersionRequest,
    HeroicWineVersionResponse,
    StatusResponse,
)

router = APIRouter(prefix="/heroic")


@router.get("/games/{app_id}/config")
async def heroic_game_config(app_id: str) -> HeroicGameConfigResponse:
    cfg = get_heroic_game_config(app_id)
    return HeroicGameConfigResponse(
        app_id=cfg.app_id,
        exists=cfg.exists,
        wine_prefix=cfg.wine_prefix,
        wine_version=HeroicWineVersionResponse(
            name=cfg.wine_version.name,
            bin=cfg.wine_version.bin,
            wine_type=cfg.wine_version.wine_type,
        ),
        other_options=cfg.other_options,
        enable_esync=cfg.enable_esync,
        enable_fsync=cfg.enable_fsync,
        auto_install_dxvk=cfg.auto_install_dxvk,
        auto_install_vkd3d=cfg.auto_install_vkd3d,
        show_fps=cfg.show_fps,
        show_mangohud=cfg.show_mangohud,
        use_game_mode=cfg.use_game_mode,
        nvidia_prime=cfg.nvidia_prime,
        saves_path=cfg.saves_path,
        target_exe=cfg.target_exe,
    )


@router.put("/games/{app_id}/launch-options")
async def update_heroic_launch_options(
    app_id: str, body: HeroicLaunchOptionsRequest
) -> StatusResponse:
    async with _state.heroic_lock:
        ok = set_heroic_launch_options(app_id, body.options)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write Heroic launch options")
    return StatusResponse(success=True)


@router.put("/games/{app_id}/wine-version")
async def update_heroic_wine_version(
    app_id: str, body: HeroicWineVersionRequest
) -> StatusResponse:
    async with _state.heroic_lock:
        ok = set_heroic_wine_version(app_id, body.name, body.bin, body.wine_type)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write Heroic wine version")
    return StatusResponse(success=True)


@router.put("/games/{app_id}/toggles")
async def update_heroic_toggles(app_id: str, body: HeroicTogglesRequest) -> StatusResponse:
    async with _state.heroic_lock:
        ok = set_heroic_toggles(
            app_id,
            enable_esync=body.enable_esync,
            enable_fsync=body.enable_fsync,
            auto_install_dxvk=body.auto_install_dxvk,
            auto_install_vkd3d=body.auto_install_vkd3d,
            show_mangohud=body.show_mangohud,
            use_game_mode=body.use_game_mode,
            nvidia_prime=body.nvidia_prime,
        )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write Heroic toggles")
    return StatusResponse(success=True)


@router.get("/wine-versions")
async def heroic_wine_versions() -> list[HeroicWineVersionResponse]:
    versions = list_heroic_wine_versions()
    return [
        HeroicWineVersionResponse(name=v.name, bin=v.bin, wine_type=v.wine_type)
        for v in versions
    ]


@router.post("/games/{app_id}/launch")
async def launch_heroic_game(app_id: str) -> StatusResponse:
    """Launch a game via heroic:// URI protocol."""
    uri = f"heroic://launch/{app_id}"
    try:
        subprocess.Popen(["xdg-open", uri], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", uri], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    return StatusResponse(success=True, message=f"Launching via {uri}")
