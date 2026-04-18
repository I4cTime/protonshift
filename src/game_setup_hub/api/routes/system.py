"""System info: GPU, power profile, env vars, presets, controllers, displays."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...controllers import get_controllers, get_sdl_mapping
from ...display import get_monitors, get_session_type, set_resolution
from ...env_vars import ENV_PRESETS, read_gaming_env, write_gaming_env
from ...gpu import (
    get_current_power_profile,
    get_gpu_info,
    get_power_profiles,
    set_power_profile,
)
from ...presets import LAUNCH_PRESETS
from .. import _state
from .._models import (
    ControllerResponse,
    EnvVarsRequest,
    GPUInfoResponse,
    LaunchPresetResponse,
    MonitorResponse,
    PowerProfileRequest,
    SetResolutionRequest,
    StatusResponse,
    SystemInfoResponse,
)

router = APIRouter()


@router.get("/system")
async def system_info() -> SystemInfoResponse:
    try:
        gpus = get_gpu_info()
    except OSError as exc:
        _state.log.warning("get_gpu_info failed: %s", exc)
        gpus = []
    try:
        profiles = get_power_profiles()
    except OSError as exc:
        _state.log.warning("get_power_profiles failed: %s", exc)
        profiles = []
    try:
        current = get_current_power_profile()
    except OSError as exc:
        _state.log.warning("get_current_power_profile failed: %s", exc)
        current = None
    return SystemInfoResponse(
        gpus=[
            GPUInfoResponse(name=g.name, driver=g.driver, vram_mb=g.vram_mb, temperature=g.temperature)
            for g in gpus
        ],
        power_profiles=profiles,
        current_power_profile=current,
    )


@router.put("/system/power-profile")
async def update_power_profile(body: PowerProfileRequest) -> StatusResponse:
    ok, msg = set_power_profile(body.profile)
    return StatusResponse(success=ok, message=msg)


@router.get("/env-vars")
async def get_env_vars() -> dict[str, str]:
    try:
        return read_gaming_env()
    except OSError as exc:
        _state.log.warning("read_gaming_env failed: %s", exc)
        return {}


@router.put("/env-vars")
async def update_env_vars(body: EnvVarsRequest) -> StatusResponse:
    async with _state.env_lock:
        ok = write_gaming_env(body.vars)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write env config")
    return StatusResponse(success=True)


@router.get("/env-presets")
async def list_env_presets() -> dict[str, dict[str, str]]:
    return ENV_PRESETS


@router.get("/presets")
async def list_presets() -> list[LaunchPresetResponse]:
    return [
        LaunchPresetResponse(
            name=p.name,
            value=p.value,
            description=p.description,
            install_command=p.install_command,
            install_url=p.install_url,
            is_installed=p.is_installed(),
        )
        for p in LAUNCH_PRESETS
    ]


@router.get("/controllers")
async def list_controllers() -> list[ControllerResponse]:
    ctrls = get_controllers()
    return [
        ControllerResponse(
            id=c.id,
            name=c.name,
            device_path=c.device_path,
            controller_type=c.controller_type,
            vendor_id=c.vendor_id,
            product_id=c.product_id,
            bus_type=c.bus_type,
            version=c.version,
        )
        for c in ctrls
    ]


@router.get("/controllers/{controller_id}/sdl-mapping")
async def controller_sdl_mapping(controller_id: str) -> dict[str, str]:
    ctrls = get_controllers()
    ctrl = next((c for c in ctrls if c.id == controller_id), None)
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controller not found")
    return {"mapping": get_sdl_mapping(ctrl)}


@router.get("/display/monitors")
async def list_monitors() -> dict[str, Any]:
    session = get_session_type()
    monitors = get_monitors()
    return {
        "session_type": session,
        "monitors": [
            MonitorResponse(
                name=m.name,
                connected=m.connected,
                resolution=m.resolution,
                refresh_rate=m.refresh_rate,
                primary=m.primary,
                position=m.position,
            )
            for m in monitors
        ],
    }


@router.put("/display/resolution")
async def update_resolution(body: SetResolutionRequest) -> StatusResponse:
    ok = set_resolution(body.monitor, body.width, body.height, body.refresh)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to set resolution")
    return StatusResponse(success=True, message=f"Set {body.monitor} to {body.width}x{body.height}")
