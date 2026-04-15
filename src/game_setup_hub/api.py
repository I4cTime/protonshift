"""FastAPI backend exposing ProtonShift logic over localhost HTTP."""

from __future__ import annotations

import argparse
import asyncio
import socket
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .env_vars import ENV_PRESETS, read_gaming_env, write_gaming_env
from .gpu import get_current_power_profile, get_gpu_info, get_power_profiles, set_power_profile
from .heroic import HeroicGame, discover_heroic_games
from .heroic_config import (
    get_heroic_game_config,
    list_heroic_wine_versions,
    set_heroic_launch_options,
    set_heroic_toggles,
    set_heroic_wine_version,
)
from .lutris import LutrisGame, discover_lutris_games
from .presets import LAUNCH_PRESETS
from .profiles_storage import (
    ApplicationProfile,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)
from .controllers import get_controllers, get_sdl_mapping
from .display import get_monitors, get_session_type, set_resolution
from .fixes import add_user_fix, get_fixes
from .gamescope import GamescopeOptions, build_gamescope_cmd, is_gamescope_available
from .mangohud import (
    MANGOHUD_PARAMS,
    MANGOHUD_PRESETS,
    get_per_game_config_path,
    is_mangohud_available,
    list_per_game_configs,
    read_mangohud_config,
    write_mangohud_config,
)
from .prefix import delete_prefix as _delete_prefix, get_prefix_info
from .saves import (
    backup_saves as _backup_saves,
    find_save_paths,
    list_backups,
    restore_backup as _restore_backup,
)
from .shader_cache import (
    clear_shader_cache as _clear_shader_cache,
    get_shader_cache_info,
    get_total_shader_cache_size,
)
from .protontricks import COMMON_VERBS, is_protontricks_available, run_protontricks
from .steam import (
    SteamGame,
    discover_games,
    get_available_proton_tools,
    get_localconfig_path,
    is_steam_running,
)
from .vdf_config import get_compat_tool, get_launch_options, set_compat_tool, set_launch_options

# ---------------------------------------------------------------------------
# Pydantic response models (JSON-safe mirrors of existing dataclasses)
# ---------------------------------------------------------------------------


class SteamGameResponse(BaseModel):
    app_id: str
    name: str
    install_dir: str
    last_played: int
    library_path: str
    compatdata_path: str | None
    has_compatdata: bool
    install_path: str | None
    source: str = "steam"


class HeroicGameResponse(BaseModel):
    app_id: str
    name: str
    store: str
    install_path: str | None
    prefix_path: str | None
    source: str = "heroic"


class LutrisGameResponse(BaseModel):
    app_id: str
    name: str
    install_path: str | None
    prefix_path: str | None
    source: str = "lutris"


class GPUInfoResponse(BaseModel):
    name: str
    driver: str
    vram_mb: int | None
    temperature: float | None


class SystemInfoResponse(BaseModel):
    gpus: list[GPUInfoResponse]
    power_profiles: list[str]
    current_power_profile: str | None


class LaunchPresetResponse(BaseModel):
    name: str
    value: str
    description: str
    install_command: str
    install_url: str
    is_installed: bool


class ProfileResponse(BaseModel):
    name: str
    launch_options: str
    compat_tool: str
    env_vars: dict[str, str]
    power_profile: str


class ProfileCreateRequest(BaseModel):
    name: str
    launch_options: str = ""
    compat_tool: str = ""
    env_vars: dict[str, str] = {}
    power_profile: str = ""


class LaunchOptionsRequest(BaseModel):
    options: str


class CompatToolRequest(BaseModel):
    tool_name: str


class EnvVarsRequest(BaseModel):
    vars: dict[str, str]


class PowerProfileRequest(BaseModel):
    profile: str


class ProtontricksRequest(BaseModel):
    verb: str | None = None


class PrefixInfoResponse(BaseModel):
    path: str
    exists: bool
    size_bytes: int = 0
    size_human: str = ""
    created: str = ""
    dxvk_version: str = ""
    vkd3d_version: str = ""


class ControllerResponse(BaseModel):
    id: str
    name: str
    device_path: str
    controller_type: str
    vendor_id: str = ""
    product_id: str = ""


class MonitorResponse(BaseModel):
    name: str
    connected: bool
    resolution: str
    refresh_rate: str
    primary: bool
    position: str


class SetResolutionRequest(BaseModel):
    monitor: str
    width: int
    height: int
    refresh: float = 0


class SaveLocationResponse(BaseModel):
    path: str
    exists: bool
    size_bytes: int = 0
    size_human: str = ""
    label: str = ""


class BackupInfoResponse(BaseModel):
    path: str
    filename: str
    size_bytes: int
    size_human: str
    created: str


class BackupRequest(BaseModel):
    paths: list[str]


class RestoreRequest(BaseModel):
    backup_path: str
    target_dir: str


class MangoHudConfigRequest(BaseModel):
    config: dict[str, str]


class GameFixResponse(BaseModel):
    title: str
    description: str
    fix_type: str
    key: str
    value: str
    source: str


class GameFixCreateRequest(BaseModel):
    title: str
    description: str = ""
    fix_type: str = "env"
    key: str = ""
    value: str = ""


class GamescopeBuildRequest(BaseModel):
    output_width: int = 0
    output_height: int = 0
    game_width: int = 0
    game_height: int = 0
    fps_limit: int = 0
    fsr: bool = False
    fsr_sharpness: int = 5
    integer_scale: bool = False
    hdr: bool = False
    nested: bool = True
    borderless: bool = True
    fullscreen: bool = True
    extra_args: str = ""


class ShaderCacheResponse(BaseModel):
    app_id: str
    path: str
    exists: bool
    size_bytes: int = 0
    size_human: str = ""


class OpenPathRequest(BaseModel):
    path: str


class OpenUriRequest(BaseModel):
    uri: str


class HeroicWineVersionResponse(BaseModel):
    name: str
    bin: str
    wine_type: str


class HeroicGameConfigResponse(BaseModel):
    app_id: str
    exists: bool
    wine_prefix: str = ""
    wine_version: HeroicWineVersionResponse = HeroicWineVersionResponse(name="", bin="", wine_type="")
    other_options: str = ""
    enable_esync: bool = False
    enable_fsync: bool = False
    auto_install_dxvk: bool = True
    auto_install_vkd3d: bool = False
    show_fps: bool = False
    show_mangohud: bool = False
    use_game_mode: bool = False
    nvidia_prime: bool = False
    saves_path: str = ""
    target_exe: str = ""


class HeroicLaunchOptionsRequest(BaseModel):
    options: str


class HeroicWineVersionRequest(BaseModel):
    name: str
    bin: str
    wine_type: str


class HeroicTogglesRequest(BaseModel):
    enable_esync: bool | None = None
    enable_fsync: bool | None = None
    auto_install_dxvk: bool | None = None
    auto_install_vkd3d: bool | None = None
    show_mangohud: bool | None = None
    use_game_mode: bool | None = None
    nvidia_prime: bool | None = None


class StatusResponse(BaseModel):
    success: bool
    message: str = ""


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="ProtonShift API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Locks for serializing writes to shared resources
_vdf_lock = asyncio.Lock()
_env_lock = asyncio.Lock()
_profiles_lock = asyncio.Lock()
_mangohud_lock = asyncio.Lock()
_heroic_lock = asyncio.Lock()

# Cached steam root + localconfig path (discovered once)
_steam_root: Path | None = None
_config_path: Path | None = None
_steam_discovered = False


def _ensure_steam() -> None:
    global _steam_root, _config_path, _steam_discovered
    if _steam_discovered:
        return
    _steam_root, _ = discover_games()
    if _steam_root:
        _config_path = get_localconfig_path(_steam_root)
    _steam_discovered = True


def _steam_game_to_response(g: SteamGame) -> SteamGameResponse:
    return SteamGameResponse(
        app_id=g.app_id,
        name=g.name,
        install_dir=g.install_dir,
        last_played=g.last_played,
        library_path=str(g.library_path),
        compatdata_path=str(g.compatdata_path) if g.compatdata_path else None,
        has_compatdata=g.has_compatdata,
        install_path=str(g.install_path) if g.install_path else None,
    )


def _heroic_game_to_response(g: HeroicGame) -> HeroicGameResponse:
    return HeroicGameResponse(
        app_id=g.app_id,
        name=g.name,
        store=g.store,
        install_path=str(g.install_path) if g.install_path else None,
        prefix_path=str(g.prefix_path) if g.prefix_path else None,
    )


def _lutris_game_to_response(g: LutrisGame) -> LutrisGameResponse:
    return LutrisGameResponse(
        app_id=g.app_id,
        name=g.name,
        install_path=str(g.install_path) if g.install_path else None,
        prefix_path=str(g.prefix_path) if g.prefix_path else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/games")
async def list_games() -> dict[str, Any]:
    _ensure_steam()
    _, steam_games = discover_games()
    heroic_games = discover_heroic_games()
    lutris_games = discover_lutris_games()
    return {
        "steam": [_steam_game_to_response(g) for g in steam_games],
        "heroic": [_heroic_game_to_response(g) for g in heroic_games],
        "lutris": [_lutris_game_to_response(g) for g in lutris_games],
        "steam_running": is_steam_running(),
    }


@app.get("/games/{app_id}/launch-options")
async def get_game_launch_options(app_id: str) -> dict[str, str]:
    _ensure_steam()
    if not _config_path:
        return {"options": ""}
    try:
        opts = get_launch_options(_config_path, app_id)
    except Exception:
        opts = ""
    return {"options": opts}


@app.put("/games/{app_id}/launch-options")
async def update_launch_options(app_id: str, body: LaunchOptionsRequest) -> StatusResponse:
    _ensure_steam()
    if not _config_path:
        raise HTTPException(status_code=404, detail="Steam localconfig.vdf not found")
    async with _vdf_lock:
        ok = set_launch_options(_config_path, app_id, body.options)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write localconfig.vdf")
    return StatusResponse(success=True)


@app.get("/games/{app_id}/compat-tool")
async def get_game_compat_tool(app_id: str) -> dict[str, str]:
    _ensure_steam()
    if not _config_path:
        return {"tool": ""}
    try:
        tool = get_compat_tool(_config_path, app_id)
    except Exception:
        tool = ""
    return {"tool": tool}


@app.put("/games/{app_id}/compat-tool")
async def update_compat_tool(app_id: str, body: CompatToolRequest) -> StatusResponse:
    _ensure_steam()
    if not _config_path:
        raise HTTPException(status_code=404, detail="Steam localconfig.vdf not found")
    async with _vdf_lock:
        ok = set_compat_tool(_config_path, app_id, body.tool_name)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write localconfig.vdf")
    return StatusResponse(success=True)


@app.get("/games/{app_id}/proton-tools")
async def list_proton_tools(app_id: str) -> dict[str, Any]:
    _ensure_steam()
    tools = get_available_proton_tools(_steam_root)
    current = ""
    if _config_path:
        try:
            current = get_compat_tool(_config_path, app_id)
        except Exception:
            pass
    return {"tools": tools, "current": current}


@app.post("/games/{app_id}/protontricks")
async def trigger_protontricks(app_id: str, body: ProtontricksRequest) -> StatusResponse:
    if not is_protontricks_available():
        raise HTTPException(status_code=404, detail="Protontricks not installed")
    ok, msg = run_protontricks(app_id, body.verb)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return StatusResponse(success=True, message=msg)


@app.get("/protontricks/verbs")
async def list_protontricks_verbs() -> dict[str, Any]:
    return {
        "available": is_protontricks_available(),
        "verbs": [{"id": v[0], "label": v[1]} for v in COMMON_VERBS],
    }


@app.get("/presets")
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


@app.get("/env-presets")
async def list_env_presets() -> dict[str, dict[str, str]]:
    return ENV_PRESETS


@app.get("/env-vars")
async def get_env_vars() -> dict[str, str]:
    try:
        return read_gaming_env()
    except Exception:
        return {}


@app.put("/env-vars")
async def update_env_vars(body: EnvVarsRequest) -> StatusResponse:
    async with _env_lock:
        ok = write_gaming_env(body.vars)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write env config")
    return StatusResponse(success=True)


@app.get("/system")
async def system_info() -> SystemInfoResponse:
    try:
        gpus = get_gpu_info()
    except Exception:
        gpus = []
    try:
        profiles = get_power_profiles()
    except Exception:
        profiles = []
    try:
        current = get_current_power_profile()
    except Exception:
        current = None
    return SystemInfoResponse(
        gpus=[GPUInfoResponse(name=g.name, driver=g.driver, vram_mb=g.vram_mb, temperature=g.temperature) for g in gpus],
        power_profiles=profiles,
        current_power_profile=current,
    )


@app.put("/system/power-profile")
async def update_power_profile(body: PowerProfileRequest) -> StatusResponse:
    ok, msg = set_power_profile(body.profile)
    return StatusResponse(success=ok, message=msg)


@app.get("/profiles")
async def list_all_profiles() -> list[str]:
    return list_profiles()


@app.get("/profiles/{name}")
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


@app.post("/profiles")
async def create_profile(body: ProfileCreateRequest) -> StatusResponse:
    profile = ApplicationProfile(
        name=body.name,
        launch_options=body.launch_options,
        compat_tool=body.compat_tool,
        env_vars=body.env_vars,
        power_profile=body.power_profile,
    )
    async with _profiles_lock:
        ok = save_profile(profile)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save profile")
    return StatusResponse(success=True)


@app.delete("/profiles/{name}")
async def remove_profile(name: str) -> StatusResponse:
    async with _profiles_lock:
        ok = delete_profile(name)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found or could not be deleted")
    return StatusResponse(success=ok)


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} PB"


@app.get("/controllers")
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
        )
        for c in ctrls
    ]


@app.get("/controllers/{controller_id}/sdl-mapping")
async def controller_sdl_mapping(controller_id: str) -> dict[str, str]:
    ctrls = get_controllers()
    ctrl = next((c for c in ctrls if c.id == controller_id), None)
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controller not found")
    mapping = get_sdl_mapping(ctrl)
    return {"mapping": mapping}


@app.get("/display/monitors")
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


@app.put("/display/resolution")
async def update_resolution(body: SetResolutionRequest) -> StatusResponse:
    ok = set_resolution(body.monitor, body.width, body.height, body.refresh)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to set resolution")
    return StatusResponse(success=True, message=f"Set {body.monitor} to {body.width}x{body.height}")


@app.get("/games/{app_id}/saves")
async def game_saves(app_id: str, prefix_path: str | None = None) -> list[SaveLocationResponse]:
    prefix = prefix_path
    if not prefix:
        _ensure_steam()
        _, steam_games = discover_games()
        game = next((g for g in steam_games if g.app_id == app_id), None)
        prefix = str(game.compatdata_path) if game and game.compatdata_path else None
    locations = find_save_paths(app_id, prefix)
    return [
        SaveLocationResponse(
            path=loc.path,
            exists=loc.exists,
            size_bytes=loc.size_bytes,
            size_human=_human_size(loc.size_bytes),
            label=loc.label,
        )
        for loc in locations
    ]


@app.post("/games/{app_id}/saves/backup")
async def backup_game_saves(app_id: str, body: BackupRequest) -> dict[str, Any]:
    result = _backup_saves(app_id, body.paths)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create backup")
    return {"path": result}


@app.get("/games/{app_id}/saves/backups")
async def list_game_backups(app_id: str) -> list[BackupInfoResponse]:
    backups = list_backups(app_id)
    return [
        BackupInfoResponse(
            path=b.path,
            filename=b.filename,
            size_bytes=b.size_bytes,
            size_human=_human_size(b.size_bytes),
            created=b.created,
        )
        for b in backups
    ]


@app.post("/games/{app_id}/saves/restore")
async def restore_game_saves(app_id: str, body: RestoreRequest) -> StatusResponse:
    ok = _restore_backup(body.backup_path, body.target_dir)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to restore backup")
    return StatusResponse(success=True, message="Backup restored")


@app.get("/mangohud/available")
async def mangohud_available() -> dict[str, bool]:
    return {"available": is_mangohud_available()}


@app.get("/mangohud/config")
async def get_mangohud_config() -> dict[str, Any]:
    return {
        "config": read_mangohud_config(),
        "params": MANGOHUD_PARAMS,
    }


@app.put("/mangohud/config")
async def update_mangohud_config(body: MangoHudConfigRequest) -> StatusResponse:
    async with _mangohud_lock:
        ok = write_mangohud_config(body.config)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write MangoHud config")
    return StatusResponse(success=True)


@app.get("/mangohud/presets")
async def get_mangohud_presets() -> dict[str, dict[str, str]]:
    return MANGOHUD_PRESETS


@app.get("/mangohud/per-game")
async def list_mangohud_per_game() -> list[dict[str, str]]:
    """List all existing per-game MangoHud config files."""
    return list_per_game_configs()


@app.get("/mangohud/per-game/{game_name}")
async def get_mangohud_per_game_config(game_name: str) -> dict[str, Any]:
    """Read a per-game MangoHud config."""
    conf_path = get_per_game_config_path(game_name)
    return {
        "path": str(conf_path),
        "exists": conf_path.exists(),
        "config": read_mangohud_config(conf_path) if conf_path.exists() else {},
        "params": MANGOHUD_PARAMS,
    }


@app.put("/mangohud/per-game/{game_name}")
async def update_mangohud_per_game_config(
    game_name: str, body: MangoHudConfigRequest
) -> StatusResponse:
    """Write a per-game MangoHud config."""
    conf_path = get_per_game_config_path(game_name)
    async with _mangohud_lock:
        ok = write_mangohud_config(body.config, conf_path)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write per-game MangoHud config")
    return StatusResponse(success=True)


@app.get("/games/{app_id}/fixes")
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


@app.post("/games/{app_id}/fixes")
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


@app.get("/gamescope/available")
async def gamescope_available() -> dict[str, bool]:
    return {"available": is_gamescope_available()}


@app.post("/gamescope/build-cmd")
async def gamescope_build(body: GamescopeBuildRequest) -> dict[str, str]:
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
    return {"command": build_gamescope_cmd(opts)}


@app.get("/games/{app_id}/shader-cache")
async def game_shader_cache(app_id: str) -> ShaderCacheResponse:
    _ensure_steam()
    if not _steam_root:
        return ShaderCacheResponse(app_id=app_id, path="", exists=False)
    info = get_shader_cache_info(_steam_root, app_id)
    return ShaderCacheResponse(
        app_id=app_id,
        path=info.path,
        exists=info.exists,
        size_bytes=info.size_bytes,
        size_human=_human_size(info.size_bytes),
    )


@app.delete("/games/{app_id}/shader-cache")
async def clear_game_shader_cache(app_id: str) -> StatusResponse:
    _ensure_steam()
    if not _steam_root:
        raise HTTPException(status_code=404, detail="Steam root not found")
    ok = _clear_shader_cache(_steam_root, app_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to clear shader cache")
    return StatusResponse(success=True, message="Shader cache cleared")


@app.get("/shader-cache/total")
async def total_shader_cache() -> dict[str, Any]:
    _ensure_steam()
    if not _steam_root:
        return {"size_bytes": 0, "size_human": "0.0 B"}
    total = get_total_shader_cache_size(_steam_root)
    return {"size_bytes": total, "size_human": _human_size(total)}


@app.get("/games/{app_id}/prefix-info")
async def game_prefix_info(app_id: str, prefix_path: str | None = None) -> PrefixInfoResponse:
    ppath = prefix_path
    if not ppath:
        _ensure_steam()
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
        size_human=_human_size(info.size_bytes),
        created=info.created,
        dxvk_version=info.dxvk_version,
        vkd3d_version=info.vkd3d_version,
    )


@app.delete("/games/{app_id}/prefix")
async def delete_game_prefix(app_id: str, prefix_path: str | None = None) -> StatusResponse:
    ppath = prefix_path
    if not ppath:
        _ensure_steam()
        _, steam_games = discover_games()
        game = next((g for g in steam_games if g.app_id == app_id), None)
        if not game or not game.compatdata_path:
            raise HTTPException(status_code=404, detail="No prefix found for this game")
        ppath = str(game.compatdata_path)
    ok = _delete_prefix(ppath)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete prefix")
    return StatusResponse(success=True, message="Prefix deleted. The launcher will recreate it on next launch.")


@app.post("/open-path")
async def open_path(body: OpenPathRequest) -> StatusResponse:
    """Open a file or folder in the system file manager."""
    import subprocess
    target = Path(body.path).expanduser()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {body.path}")
    try:
        subprocess.Popen(["xdg-open", str(target)], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", str(target)], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))
    return StatusResponse(success=True)


@app.post("/open-uri")
async def open_uri(body: OpenUriRequest) -> StatusResponse:
    """Open a URI (e.g. steam://rungameid/...) with the system handler."""
    import subprocess
    try:
        subprocess.Popen(["xdg-open", body.uri], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", body.uri], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))
    return StatusResponse(success=True)


# ---------------------------------------------------------------------------
# Heroic endpoints
# ---------------------------------------------------------------------------


@app.get("/heroic/games/{app_id}/config")
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


@app.put("/heroic/games/{app_id}/launch-options")
async def update_heroic_launch_options(
    app_id: str, body: HeroicLaunchOptionsRequest
) -> StatusResponse:
    async with _heroic_lock:
        ok = set_heroic_launch_options(app_id, body.options)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write Heroic launch options")
    return StatusResponse(success=True)


@app.put("/heroic/games/{app_id}/wine-version")
async def update_heroic_wine_version(
    app_id: str, body: HeroicWineVersionRequest
) -> StatusResponse:
    async with _heroic_lock:
        ok = set_heroic_wine_version(app_id, body.name, body.bin, body.wine_type)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write Heroic wine version")
    return StatusResponse(success=True)


@app.put("/heroic/games/{app_id}/toggles")
async def update_heroic_toggles(app_id: str, body: HeroicTogglesRequest) -> StatusResponse:
    async with _heroic_lock:
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


@app.get("/heroic/wine-versions")
async def heroic_wine_versions() -> list[HeroicWineVersionResponse]:
    versions = list_heroic_wine_versions()
    return [
        HeroicWineVersionResponse(name=v.name, bin=v.bin, wine_type=v.wine_type)
        for v in versions
    ]


@app.post("/heroic/games/{app_id}/launch")
async def launch_heroic_game(app_id: str) -> StatusResponse:
    """Launch a game via heroic:// URI protocol."""
    import subprocess
    uri = f"heroic://launch/{app_id}"
    try:
        subprocess.Popen(["xdg-open", uri], start_new_session=True)
    except FileNotFoundError:
        try:
            subprocess.Popen(["gio", "open", uri], start_new_session=True)
        except (FileNotFoundError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))
    return StatusResponse(success=True, message=f"Launching via {uri}")


@app.get("/steam/status")
async def steam_status() -> dict[str, Any]:
    _ensure_steam()
    return {
        "running": is_steam_running(),
        "root": str(_steam_root) if _steam_root else None,
        "config_path": str(_config_path) if _config_path else None,
    }


# ---------------------------------------------------------------------------
# CLI entry point — Electron spawns this process
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cli() -> None:
    parser = argparse.ArgumentParser(description="ProtonShift API server")
    parser.add_argument("--port", type=int, default=0, help="Port to listen on (0 = auto)")
    args = parser.parse_args()

    port = args.port if args.port > 0 else _find_free_port()

    # Print port to stdout so Electron main process can read it
    print(f"PORT:{port}", flush=True)

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    cli()
