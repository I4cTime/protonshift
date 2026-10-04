"""Heroic Games Launcher discovery: Epic (Legendary), GOG, Amazon (Nile) and
sideloaded games."""

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
    store: str  # "epic" | "gog" | "amazon" | "sideload"
    install_path: Path | None
    prefix_path: Path | None
    platform: str = "windows"  # "windows" | "linux" | "mac" | "browser"

    @property
    def is_native(self) -> bool:
        """A Linux-native game: no Wine prefix to manage."""
        return self.platform == "linux"

    @property
    def compatdata_path(self) -> Path | None:
        """Wine prefix, analogous to Steam compatdata."""
        return self.prefix_path


def resolve_heroic_root() -> Path | None:
    """Return the first existing Heroic config root (native or Flatpak)."""
    for root in HEROIC_ROOTS:
        if root.exists():
            return root
    return None


# Backwards compatibility alias for older imports.
_resolve_heroic_root = resolve_heroic_root


def _load_json(path: Path) -> object:
    """Parsed JSON, or None when the file is missing or unreadable."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _prefix_for(heroic_root: Path, app_id: str) -> Path | None:
    """The game's Wine prefix from ``GamesConfig/<app_id>.json``, if it has one."""
    cfg = _load_json(heroic_root / "GamesConfig" / f"{app_id}.json")
    if not isinstance(cfg, dict) or not isinstance(cfg.get(app_id), dict):
        return None
    wine_prefix = cfg[app_id].get("winePrefix")
    return Path(wine_prefix) if isinstance(wine_prefix, str) and wine_prefix else None


def _platform(value: object) -> str:
    """Normalize Heroic's platform spellings ("Windows", "linux", "osx"...)."""
    text = str(value or "").lower()
    if text.startswith("lin"):
        return "linux"
    if text.startswith(("mac", "osx", "darwin")):
        return "mac"
    if text.startswith("brow"):
        return "browser"
    return "windows"


def _title_map(path: Path) -> dict[str, str]:
    """``app_name -> title`` from one of Heroic's ``store_cache/*_library.json``.

    The list sits under ``games`` (GOG) or ``library`` (Epic, Amazon).
    """
    data = _load_json(path)
    if not isinstance(data, dict):
        return {}
    titles: dict[str, str] = {}
    for key in ("games", "library"):
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("app_name") and entry.get("title"):
                titles[str(entry["app_name"])] = str(entry["title"])
    return titles


def _discover_amazon_games(heroic_root: Path) -> list[HeroicGame]:
    """Amazon Games (Nile) installs: ``nile_config/nile/installed.json``."""
    entries = _load_json(heroic_root / "nile_config" / "nile" / "installed.json")
    if not isinstance(entries, list):
        return []
    titles = _title_map(heroic_root / "store_cache" / "nile_library.json")
    games: list[HeroicGame] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        app_id = str(entry["id"])
        raw_path = entry.get("path")
        install_path = Path(raw_path) if isinstance(raw_path, str) and raw_path else None
        games.append(
            HeroicGame(
                app_id=app_id,
                name=titles.get(app_id) or (install_path.name if install_path else app_id),
                store="amazon",
                install_path=install_path,
                prefix_path=_prefix_for(heroic_root, app_id),
            )
        )
    return games


def _discover_sideloaded_games(heroic_root: Path) -> list[HeroicGame]:
    """Games added by hand ("Add Game"): ``sideload_apps/library.json``."""
    data = _load_json(heroic_root / "sideload_apps" / "library.json")
    entries = data.get("games") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    games: list[HeroicGame] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("app_name"):
            continue
        if entry.get("is_installed") is False:
            continue
        app_id = str(entry["app_name"])
        install = entry.get("install") if isinstance(entry.get("install"), dict) else {}
        platform = _platform(install.get("platform"))
        folder = entry.get("folder_name")
        executable = install.get("executable")
        if isinstance(folder, str) and folder:
            install_path = Path(folder)
        elif isinstance(executable, str) and executable:
            install_path = Path(executable).parent
        else:
            install_path = None
        games.append(
            HeroicGame(
                app_id=app_id,
                name=str(entry.get("title") or app_id),
                store="sideload",
                install_path=install_path,
                # a native Linux game runs without Wine even if a default
                # prefix path was written into its config
                prefix_path=None if platform == "linux" else _prefix_for(heroic_root, app_id),
                platform=platform,
            )
        )
    return games


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
    """Discover all Heroic installed games (Epic, GOG, Amazon, sideloaded)."""
    root = resolve_heroic_root()
    if not root:
        return []
    games: list[HeroicGame] = []
    # one unreadable store must not hide the others
    for discover in (
        _discover_epic_games,
        _discover_gog_games,
        _discover_amazon_games,
        _discover_sideloaded_games,
    ):
        try:
            games += discover(root)
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    games.sort(key=lambda g: g.name.lower())
    return games
