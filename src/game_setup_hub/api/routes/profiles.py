"""Application profile CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...profiles_storage import (
    ApplicationProfile,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)
from .. import _state
from .._models import ProfileCreateRequest, ProfileResponse, StatusResponse

router = APIRouter(prefix="/profiles")


@router.get("")
async def list_all_profiles() -> list[str]:
    return list_profiles()


@router.get("/{name}")
async def get_profile(name: str) -> ProfileResponse:
    p = load_profile(name)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(
        name=p.name,
        launch_options=p.launch_options,
        compat_tool=p.compat_tool,
        env_vars=p.env_vars,
        power_profile=p.power_profile,
    )


@router.post("")
async def create_profile(body: ProfileCreateRequest) -> StatusResponse:
    profile = ApplicationProfile(
        name=body.name,
        launch_options=body.launch_options,
        compat_tool=body.compat_tool,
        env_vars=body.env_vars,
        power_profile=body.power_profile,
    )
    async with _state.profiles_lock:
        ok = save_profile(profile)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save profile")
    return StatusResponse(success=True)


@router.delete("/{name}")
async def remove_profile(name: str) -> StatusResponse:
    async with _state.profiles_lock:
        ok = delete_profile(name)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found or could not be deleted")
    return StatusResponse(success=ok)
