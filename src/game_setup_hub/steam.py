"""Steam path discovery and game listing. Cross-distro: Pop, Ubuntu, Flatpak."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import vdf


def is_steam_running() -> bool:
    """Check if Steam client is running. Edit localconfig.vdf with Steam closed."""
    try:
        r = subprocess.run(["pgrep", "-x", "steam"], capture_output=True, timeout=2)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


STEAM_ROOTS = [
    Path.home() / ".steam" / "root",
    Path.home() / ".steam" / "steam",
    Path.home() / ".steam" / "debian-installation",
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
]


@dataclass
class SteamGame:
    app_id: str
    name: str
    install_dir: str
    last_played: int
    library_path: Path
    compatdata_path: Path | None

    @property
    def has_compatdata(self) -> bool:
        return self.compatdata_path is not None and self.compatdata_path.exists()

    @property
    def install_path(self) -> Path | None:
        """Full path to game installation (steamapps/common/installdir)."""
        if not self.install_dir:
            return None
        p = self.library_path / "steamapps" / "common" / self.install_dir
        return p if p.exists() else None


def _resolve_steam_root() -> Path | None:
    """Resolve the actual Steam installation root."""
    for candidate in STEAM_ROOTS:
        if not candidate.exists():
            continue
        # Follow symlink
        resolved = candidate.resolve() if candidate.is_symlink() else candidate
        # Check for steamapps
        steamapps = resolved / "steamapps"
        if steamapps.exists():
            return resolved
        # Flatpak layout may differ
        if "com.valvesoftware.Steam" in str(candidate):
            return resolved
    return None


def _find_libraryfolders(steam_root: Path) -> list[Path]:
    """Get all library paths from libraryfolders.vdf."""
    paths = []
    for loc in [
        steam_root / "steamapps" / "libraryfolders.vdf",
        steam_root / "config" / "libraryfolders.vdf",
    ]:
        if not loc.exists():
            continue
        try:
            with open(loc, encoding="utf-8", errors="replace") as f:
                data = vdf.load(f)
            folders = data.get("libraryfolders", data)
            if isinstance(folders, dict):
                for _key, folder in folders.items():
                    if isinstance(folder, dict) and "path" in folder:
                        p = Path(folder["path"])
                        if p.exists():
                            paths.append(p)
        except (SyntaxError, ValueError, OSError):
            pass
        break  # Use first found
    if not paths and steam_root.exists():
        paths.append(steam_root)
    return paths


def _parse_acf(path: Path) -> dict | None:
    """Parse appmanifest_*.acf file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return vdf.load(f)
    except (SyntaxError, ValueError, OSError):
        return None


def discover_games() -> tuple[Path | None, list[SteamGame]]:
    """
    Discover Steam root and all installed games.
    Returns (steam_root, games).
    """
    steam_root = _resolve_steam_root()
    if not steam_root:
        return None, []

    libraries = _find_libraryfolders(steam_root)
    games: list[SteamGame] = []
    seen_appids: set[str] = set()

    # Exclude Steamworks Common Redistributable and similar non-games
    TOOL_APPIDS = {"228980"}

    for lib in libraries:
        steamapps = lib / "steamapps"
        if not steamapps.exists():
            continue
        for acf in steamapps.glob("appmanifest_*.acf"):
            app_id = acf.stem.replace("appmanifest_", "")
            if app_id in TOOL_APPIDS or app_id in seen_appids:
                continue
            seen_appids.add(app_id)
            data = _parse_acf(acf)
            if not data:
                continue
            state = data.get("AppState", data)
            if not isinstance(state, dict):
                continue
            name = state.get("name", f"App {app_id}")
            install_dir = state.get("installdir", "")
            try:
                last_played = int(state.get("LastPlayed", 0))
            except (ValueError, TypeError):
                last_played = 0
            compatdata = steamapps / "compatdata" / app_id
            games.append(
                SteamGame(
                    app_id=app_id,
                    name=name,
                    install_dir=install_dir,
                    last_played=last_played,
                    library_path=lib,
                    compatdata_path=compatdata if compatdata.exists() else None,
                )
            )

    games.sort(key=lambda g: (-g.last_played, g.name.lower()))
    return steam_root, games


def get_userdata_dir(steam_root: Path) -> Path | None:
    """Get userdata directory. Uses first non-zero SteamID3 folder."""
    userdata = steam_root / "userdata"
    if not userdata.exists():
        return None
    for d in userdata.iterdir():
        if d.is_dir() and d.name.isdigit() and d.name != "0":
            return d
    return None


def get_localconfig_path(steam_root: Path) -> Path | None:
    """Get path to localconfig.vdf."""
    userdata = get_userdata_dir(steam_root)
    if not userdata:
        return None
    return userdata / "config" / "localconfig.vdf"


def get_compattools_dir(steam_root: Path | None) -> Path | None:
    """Get compatibility tools directory (Proton-GE, etc.)."""
    bases = [Path.home() / ".steam" / "root", Path.home() / ".steam" / "debian-installation"]
    if steam_root:
        bases.insert(0, steam_root)
    for base in bases:
        compat = base / "compatibilitytools.d"
        if compat.exists():
            return compat
    return None


# Built-in Steam Proton tool IDs (approximate — Steam may use different keys)
BUILTIN_PROTON = ["proton_experimental", "proton_9_0", "proton_8_0", "proton_7_0", "proton_6_3", ""]


def get_available_proton_tools(steam_root: Path | None) -> list[str]:
    """List Proton/GE tools: built-in first, then compatibilitytools.d."""
    tools: list[str] = ["", "proton_experimental", "proton_9_0", "proton_8_0", "proton_7_0"]
    compat_dir = get_compattools_dir(steam_root)
    if compat_dir and compat_dir.exists():
        for item in sorted(compat_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if (item / "proton").exists() or (item / "compatibilitytool.vdf").exists():
                    tools.append(item.name)
    return tools
