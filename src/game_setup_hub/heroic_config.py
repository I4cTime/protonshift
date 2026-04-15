"""Heroic Games Launcher per-game config read/write via GamesConfig JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .heroic import HEROIC_ROOTS, _resolve_heroic_root


@dataclass
class HeroicWineVersion:
    name: str = ""
    bin: str = ""
    wine_type: str = ""  # "wine" | "proton"


@dataclass
class HeroicGameConfig:
    app_id: str
    exists: bool = False
    wine_prefix: str = ""
    wine_version: HeroicWineVersion = field(default_factory=HeroicWineVersion)
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


def _get_games_config_dir() -> Path | None:
    root = _resolve_heroic_root()
    if not root:
        return None
    return root / "GamesConfig"


def _read_config_file(app_id: str) -> dict[str, Any] | None:
    cfg_dir = _get_games_config_dir()
    if not cfg_dir or not cfg_dir.exists():
        return None
    cfg_file = cfg_dir / f"{app_id}.json"
    if not cfg_file.exists():
        return None
    try:
        with open(cfg_file, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and app_id in data:
            return data[app_id]
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _write_config_file(app_id: str, config: dict[str, Any]) -> bool:
    cfg_dir = _get_games_config_dir()
    if not cfg_dir:
        return False
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / f"{app_id}.json"

    existing: dict[str, Any] = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    if app_id in existing and isinstance(existing[app_id], dict):
        existing[app_id].update(config)
    else:
        existing[app_id] = config

    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        return True
    except OSError:
        return False


def get_heroic_game_config(app_id: str) -> HeroicGameConfig:
    raw = _read_config_file(app_id)
    if not raw:
        return HeroicGameConfig(app_id=app_id, exists=False)

    wv_raw = raw.get("wineVersion", {})
    wine_version = HeroicWineVersion(
        name=wv_raw.get("name", "") if isinstance(wv_raw, dict) else "",
        bin=wv_raw.get("bin", "") if isinstance(wv_raw, dict) else "",
        wine_type=wv_raw.get("type", "") if isinstance(wv_raw, dict) else "",
    )

    return HeroicGameConfig(
        app_id=app_id,
        exists=True,
        wine_prefix=raw.get("winePrefix", ""),
        wine_version=wine_version,
        other_options=raw.get("otherOptions", ""),
        enable_esync=bool(raw.get("enableEsync", False)),
        enable_fsync=bool(raw.get("enableFsync", False)),
        auto_install_dxvk=bool(raw.get("autoInstallDxvk", True)),
        auto_install_vkd3d=bool(raw.get("autoInstallVkd3d", False)),
        show_fps=bool(raw.get("showFps", False)),
        show_mangohud=bool(raw.get("showMangohud", False)),
        use_game_mode=bool(raw.get("useGameMode", False)),
        nvidia_prime=bool(raw.get("nvidiaPrime", False)),
        saves_path=raw.get("savesPath", ""),
        target_exe=raw.get("targetExe", ""),
    )


def set_heroic_launch_options(app_id: str, options: str) -> bool:
    return _write_config_file(app_id, {"otherOptions": options})


def set_heroic_wine_version(app_id: str, name: str, bin_path: str, wine_type: str) -> bool:
    return _write_config_file(app_id, {
        "wineVersion": {"name": name, "bin": bin_path, "type": wine_type},
    })


def set_heroic_toggles(
    app_id: str,
    enable_esync: bool | None = None,
    enable_fsync: bool | None = None,
    auto_install_dxvk: bool | None = None,
    auto_install_vkd3d: bool | None = None,
    show_mangohud: bool | None = None,
    use_game_mode: bool | None = None,
    nvidia_prime: bool | None = None,
) -> bool:
    patch: dict[str, Any] = {}
    if enable_esync is not None:
        patch["enableEsync"] = enable_esync
    if enable_fsync is not None:
        patch["enableFsync"] = enable_fsync
    if auto_install_dxvk is not None:
        patch["autoInstallDxvk"] = auto_install_dxvk
    if auto_install_vkd3d is not None:
        patch["autoInstallVkd3d"] = auto_install_vkd3d
    if show_mangohud is not None:
        patch["showMangohud"] = show_mangohud
    if use_game_mode is not None:
        patch["useGameMode"] = use_game_mode
    if nvidia_prime is not None:
        patch["nvidiaPrime"] = nvidia_prime
    if not patch:
        return True
    return _write_config_file(app_id, patch)


@dataclass
class HeroicWineVersionInfo:
    name: str
    bin: str
    wine_type: str  # "wine" | "proton"


def list_heroic_wine_versions() -> list[HeroicWineVersionInfo]:
    root = _resolve_heroic_root()
    if not root:
        return []

    versions: list[HeroicWineVersionInfo] = []

    for subdir, wtype in [("tools/wine", "wine"), ("tools/proton", "proton")]:
        tools_dir = root / subdir
        if not tools_dir.exists():
            continue
        for item in sorted(tools_dir.iterdir()):
            if not item.is_dir():
                continue
            bin_path = item / "bin" / ("wine" if wtype == "wine" else "proton")
            if not bin_path.exists() and wtype == "proton":
                bin_path = item / "proton"
            if not bin_path.exists():
                bin_path = item / "bin" / "wine"
            versions.append(HeroicWineVersionInfo(
                name=item.name,
                bin=str(bin_path),
                wine_type=wtype,
            ))

    return versions
