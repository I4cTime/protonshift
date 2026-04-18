"""Pydantic request and response models for the API surface."""

from __future__ import annotations

from pydantic import BaseModel


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
    bus_type: str = ""
    version: str = ""


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
