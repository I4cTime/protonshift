"""Heroic Games Launcher discovery. Epic (Legendary) and GOG."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


HEROIC_ROOTS = [
    Path.home() / ".config" / "heroic",
    Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic",
]


@dataclass
class HeroicGame:
    app_id: str
    name: str
    store: str  # "epic" | "gog"
    install_path: Path | None
    prefix_path: Path | None

    @property
    def compatdata_path(self) -> Path | None:
        """Wine prefix, analogous to Steam compatdata."""
        return self.prefix_path


def _resolve_heroic_root() -> Path | None:
    for root in HEROIC_ROOTS:
        if root.exists():
            return root
    return None


def _discover_epic_games(heroic_root: Path) -> list[HeroicGame]:
    """Discover Epic (Legendary) installed games."""
    installed = heroic_root / "legendaryConfig" / "legendary" / "installed.json"
    if not installed.exists():
        return []
    games: list[HeroicGame] = []
    try:
        with open(installed, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    games_config = heroic_root / "GamesConfig"
    for app_id, info in data.items():
        if not isinstance(info, dict) or app_id == "__timestamp":
            continue
        name = info.get("title", info.get("app_name", app_id))
        install_path = info.get("install_path")
        install = Path(install_path) if install_path else None
        prefix_path = None
        if games_config.exists():
            cfg_file = games_config / f"{app_id}.json"
            if cfg_file.exists():
                try:
                    with open(cfg_file, encoding="utf-8") as cf:
                        cfg = json.load(cf)
                    if isinstance(cfg, dict) and app_id in cfg:
                        wine_prefix = cfg[app_id].get("winePrefix")
                        if wine_prefix:
                            prefix_path = Path(wine_prefix)
                except (json.JSONDecodeError, OSError, KeyError):
                    pass
        games.append(
            HeroicGame(
                app_id=app_id,
                name=str(name),
                store="epic",
                install_path=install,
                prefix_path=prefix_path,
            )
        )
    return games


def _build_gog_title_map(heroic_root: Path) -> dict[str, str]:
    """Build app_name → title map from gog_library.json."""
    lib_path = heroic_root / "store_cache" / "gog_library.json"
    if not lib_path.exists():
        return {}
    try:
        with open(lib_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    titles: dict[str, str] = {}
    games_list = data.get("games") if isinstance(data, dict) else None
    if isinstance(games_list, list):
        for entry in games_list:
            if not isinstance(entry, dict):
                continue
            app = entry.get("app_name")
            title = entry.get("title")
            if app and title:
                titles[str(app)] = str(title)
    return titles


def _discover_gog_games(heroic_root: Path) -> list[HeroicGame]:
    """Discover GOG installed games from gog_store/installed.json."""
    games_config = heroic_root / "GamesConfig"

    gog_installed_path = heroic_root / "gog_store" / "installed.json"
    if not gog_installed_path.exists():
        return []

    try:
        with open(gog_installed_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []

    entries = data.get("installed")
    if not isinstance(entries, list):
        return []

    title_map = _build_gog_title_map(heroic_root)

    games: list[HeroicGame] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("is_dlc") or (
            isinstance(entry.get("install"), dict)
            and entry["install"].get("is_dlc")
        ):
            continue
        app_id = entry.get("appName") or entry.get("app_name")
        if not app_id:
            continue
        app_id = str(app_id)

        name = title_map.get(app_id) or entry.get("folder_name") or app_id

        raw_path = entry.get("install_path")
        install_path = Path(raw_path) if raw_path else None

        prefix_path = None
        if games_config.exists():
            cfg_file = games_config / f"{app_id}.json"
            if cfg_file.exists():
                try:
                    with open(cfg_file, encoding="utf-8") as f:
                        cfg = json.load(f)
                    if isinstance(cfg, dict) and app_id in cfg:
                        wine_prefix = cfg[app_id].get("winePrefix")
                        if wine_prefix:
                            prefix_path = Path(wine_prefix)
                except (json.JSONDecodeError, OSError, KeyError):
                    pass

        games.append(
            HeroicGame(
                app_id=app_id,
                name=name,
                store="gog",
                install_path=install_path,
                prefix_path=prefix_path,
            )
        )
    return games


def discover_heroic_games() -> list[HeroicGame]:
    """Discover all Heroic installed games (Epic + GOG)."""
    root = _resolve_heroic_root()
    if not root:
        return []
    games = _discover_epic_games(root) + _discover_gog_games(root)
    games.sort(key=lambda g: g.name.lower())
    return games
