"""ScopeBuddy availability, auto-detect capabilities, global and per-app config."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from ...scopebuddy import (
    SCOPEBUDDY_GLOBAL_CONF,
    SCOPEBUDDY_PRESETS,
    delete_envvars,
    delete_per_app_config,
    detect_auto_capabilities,
    list_envvars,
    list_per_app_overrides,
    read_envvars,
    read_global_config,
    read_per_app_config,
    rescan_tools,
    scopebuddy_available_info,
    write_envvars,
    write_global_config,
    write_per_app_config,
)
from .. import _state
from .._models import (
    ScopeBuddyConfigRequest,
    ScopeBuddyEnvVarsRequest,
    ScopeBuddyPerAppRequest,
    StatusResponse,
)

router = APIRouter(prefix="/scopebuddy")


def _decode_key(key: str) -> str:
    return unquote(key, errors="replace").strip()


@router.get("/available")
async def scopebuddy_available() -> dict[str, Any]:
    return scopebuddy_available_info()


@router.get("/auto-capabilities")
async def scopebuddy_auto_caps() -> dict[str, bool]:
    return detect_auto_capabilities()


@router.get("/config")
async def get_scopebuddy_global_config() -> dict[str, Any]:
    return {
        "path": str(SCOPEBUDDY_GLOBAL_CONF),
        "exists": SCOPEBUDDY_GLOBAL_CONF.is_file(),
        "config": read_global_config(),
    }


@router.put("/config")
async def put_scopebuddy_global_config(body: ScopeBuddyConfigRequest) -> StatusResponse:
    async with _state.scopebuddy_lock:
        ok = write_global_config(body.config)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write ScopeBuddy global config")
    return StatusResponse(success=True)


@router.get("/presets")
async def get_scopebuddy_presets() -> dict[str, dict[str, str]]:
    return SCOPEBUDDY_PRESETS


@router.get("/per-app")
async def list_scopebuddy_per_app() -> list[dict[str, str]]:
    return list_per_app_overrides()


@router.get("/per-app/{key}")
async def get_scopebuddy_per_app(key: str) -> dict[str, Any]:
    app_key = _decode_key(key)
    if not app_key:
        raise HTTPException(status_code=400, detail="Empty app key")
    path, exists, cfg = read_per_app_config(app_key)
    return {"key": app_key, "path": str(path), "exists": exists, "config": cfg}


@router.put("/per-app/{key}")
async def put_scopebuddy_per_app(key: str, body: ScopeBuddyPerAppRequest) -> StatusResponse:
    app_key = _decode_key(key)
    if not app_key:
        raise HTTPException(status_code=400, detail="Empty app key")
    async with _state.scopebuddy_lock:
        ok = write_per_app_config(app_key, body.config)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write per-app ScopeBuddy config")
    return StatusResponse(success=True)


@router.delete("/per-app/{key}")
async def delete_scopebuddy_per_app(key: str) -> StatusResponse:
    app_key = _decode_key(key)
    if not app_key:
        raise HTTPException(status_code=400, detail="Empty app key")
    async with _state.scopebuddy_lock:
        ok = delete_per_app_config(app_key)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete per-app ScopeBuddy config")
    return StatusResponse(success=True, message="Override removed")


@router.post("/rescan")
async def scopebuddy_rescan() -> dict[str, Any]:
    """Re-detect ``scb`` / ``scopebuddy`` after the user installs it without restarting."""
    async with _state.scopebuddy_lock:
        return rescan_tools()


@router.get("/envvars")
async def list_scopebuddy_envvars() -> list[dict[str, str]]:
    return list_envvars()


@router.get("/envvars/{name}")
async def get_scopebuddy_envvars(name: str) -> dict[str, Any]:
    decoded = _decode_key(name)
    if not decoded:
        raise HTTPException(status_code=400, detail="Empty env profile name")
    path, exists, cfg = read_envvars(decoded)
    return {"name": decoded, "path": str(path), "exists": exists, "config": cfg}


@router.put("/envvars/{name}")
async def put_scopebuddy_envvars(name: str, body: ScopeBuddyEnvVarsRequest) -> StatusResponse:
    decoded = _decode_key(name)
    if not decoded:
        raise HTTPException(status_code=400, detail="Empty env profile name")
    async with _state.scopebuddy_lock:
        ok = write_envvars(decoded, body.config)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write envvars file")
    return StatusResponse(success=True)


@router.delete("/envvars/{name}")
async def delete_scopebuddy_envvars(name: str) -> StatusResponse:
    decoded = _decode_key(name)
    if not decoded:
        raise HTTPException(status_code=400, detail="Empty env profile name")
    async with _state.scopebuddy_lock:
        ok = delete_envvars(decoded)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete envvars file")
    return StatusResponse(success=True, message="Envvars file removed")
