"""Steam path discovery and game listing. Cross-distro: Pop, Ubuntu, Flatpak."""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import vdf

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


def get_steam_root() -> Path | None:
    """Public accessor for the resolved Steam installation root."""
    return _resolve_steam_root()


def _find_libraryfolders(steam_root: Path) -> list[Path]:
    """Get all library paths from libraryfolders.vdf."""
    paths: list[Path] = []
    for loc in [
        steam_root / "steamapps" / "libraryfolders.vdf",
        steam_root / "config" / "libraryfolders.vdf",
    ]:
        if not loc.exists():
            continue
        try:
            with open(loc, encoding="utf-8", errors="replace") as f:
                data = vdf.load(f)
        except (SyntaxError, ValueError, OSError):
            continue
        folders = data.get("libraryfolders", data)
        if isinstance(folders, dict):
            for folder in folders.values():
                if isinstance(folder, dict) and "path" in folder:
                    p = Path(folder["path"])
                    if p.exists():
                        paths.append(p)
        if paths:
            break  # Stop at the first manifest that yielded usable paths
    if not paths and steam_root.exists():
        paths.append(steam_root)
    return paths


# Steam installs its own runtimes as ordinary apps with an appmanifest. They
# are not games: nothing to launch, no prefix, no launch options.
_TOOL_NAME_RE = re.compile(
    r"^(Proton( |-)(\d|Experimental|Hotfix|EasyAntiCheat|BattlEye|Next)"
    r"|Steam Linux Runtime"
    r"|Steamworks Common Redistributables)",
    re.IGNORECASE,
)


def is_steam_tool(name: str) -> bool:
    """True for Proton builds, Steam Linux Runtimes and redistributables."""
    return bool(_TOOL_NAME_RE.match(name.strip()))


def _parse_acf(path: Path) -> dict | None:
    """Parse appmanifest_*.acf file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return vdf.load(f)
    except (SyntaxError, ValueError, OSError):
        return None


# Library walks add up: every API request to /games, /games/{app_id}/*,
# /open-path etc. used to re-stat hundreds of acf files. A 5s TTL keeps the
# UI snappy without going stale long enough to confuse users who just
# installed something.
_DISCOVERY_TTL_SECONDS = 5.0
_discovery_lock = threading.Lock()
_discovery_cache: tuple[float, Path | None, list[SteamGame]] | None = None


def invalidate_discovery_cache() -> None:
    """Drop the cached game list (call after install/uninstall events)."""
    global _discovery_cache
    with _discovery_lock:
        _discovery_cache = None


def discover_games() -> tuple[Path | None, list[SteamGame]]:
    """Discover Steam root and all installed games. Cached briefly per process.

    Returns ``(steam_root, games)``. Disk walks are skipped if a fresh enough
    result is already cached.
    """
    global _discovery_cache
    now = time.monotonic()
    with _discovery_lock:
        cached = _discovery_cache
        if cached and (now - cached[0]) < _DISCOVERY_TTL_SECONDS:
            return cached[1], cached[2]

    steam_root = _resolve_steam_root()
    if not steam_root:
        with _discovery_lock:
            _discovery_cache = (now, None, [])
        return None, []

    libraries = _find_libraryfolders(steam_root)
    games: list[SteamGame] = []
    seen_appids: set[str] = set()

    # Steamworks Common Redistributables: a tool with no telling name pattern
    TOOL_APPIDS = {"228980"}

    for lib in libraries:
        steamapps = lib / "steamapps"
        if not steamapps.exists():
            continue
        for acf in steamapps.glob("appmanifest_*.acf"):
            app_id = acf.stem.replace("appmanifest_", "")
            # Steam app ids are decimal digits only; a crafted filename like
            # ``appmanifest_...acf`` would otherwise inject ``..`` as an id
            # and create a phantom entry that downstream path joins trip on.
            if not app_id.isdigit():
                continue
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
            if is_steam_tool(str(name)):
                continue
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
    with _discovery_lock:
        _discovery_cache = (now, steam_root, games)
    return steam_root, games


def get_userdata_dir(steam_root: Path) -> Path | None:
    """Get userdata directory for the most recently active account.

    Multi-account machines have several SteamID3 folders; iteration order of
    ``iterdir`` is filesystem-dependent, so instead of "first hit" we pick the
    account whose ``config/localconfig.vdf`` was modified most recently (Steam
    touches it constantly for the logged-in user). Falls back to the highest
    numeric id when no localconfig exists at all.
    """
    userdata = steam_root / "userdata"
    if not userdata.exists():
        return None
    candidates = [
        d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit() and d.name != "0"
    ]
    if not candidates:
        return None

    def _localconfig_mtime(d: Path) -> float | None:
        try:
            return (d / "config" / "localconfig.vdf").stat().st_mtime
        except OSError:
            return None

    timed = [(m, d) for d in candidates if (m := _localconfig_mtime(d)) is not None]
    if timed:
        return max(timed, key=lambda t: t[0])[1]
    return max(candidates, key=lambda d: int(d.name))


def get_localconfig_path(steam_root: Path) -> Path | None:
    """Get path to localconfig.vdf."""
    userdata = get_userdata_dir(steam_root)
    if not userdata:
        return None
    return userdata / "config" / "localconfig.vdf"


def get_compattools_dir(steam_root: Path | None) -> Path | None:
    """The user's compatibility tools directory (Proton-GE, etc.) - writable."""
    bases = [Path.home() / ".steam" / "root", Path.home() / ".steam" / "debian-installation"]
    if steam_root:
        bases.insert(0, steam_root)
    for base in bases:
        compat = base / "compatibilitytools.d"
        if compat.exists():
            return compat
    return None


# Steam also scans these system-wide locations (distro packages such as Arch's
# proton-ge-custom-bin install there). Read-only from the app's point of view.
SYSTEM_COMPAT_DIRS: tuple[Path, ...] = (
    Path("/usr/share/steam/compatibilitytools.d"),
    Path("/usr/local/share/steam/compatibilitytools.d"),
)


def get_system_compattools_dirs() -> list[Path]:
    """Existing system-wide ``compatibilitytools.d`` directories (``$XDG_DATA_DIRS`` too)."""
    candidates: list[Path] = list(SYSTEM_COMPAT_DIRS)
    for entry in os.environ.get("XDG_DATA_DIRS", "").split(":"):
        if entry:
            candidates.append(Path(entry) / "steam" / "compatibilitytools.d")
    found: list[Path] = []
    seen: set[Path] = set()
    for c in candidates:
        try:
            if not c.is_dir():
                continue
            key = c.resolve()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        found.append(c)
    return found


def read_tool_manifest(tool_dir: Path) -> tuple[str, str]:
    """``(internal_name, display_name)`` from a tool's ``compatibilitytool.vdf``.

    Steam keys ``CompatToolMapping`` by the *internal* name, which is the
    directory name for GE tarballs but not for distro packages (Arch installs
    ``proton-ge-custom/`` registered as ``Proton-GE``). Falls back to the
    directory name when the manifest is missing or unreadable.
    """
    fallback = (tool_dir.name, tool_dir.name)
    manifest = tool_dir / "compatibilitytool.vdf"
    try:
        with open(manifest, encoding="utf-8", errors="replace") as f:
            data = vdf.load(f)
        tools = data.get("compatibilitytools", {}).get("compat_tools", {})
        for internal, info in tools.items():
            if not isinstance(info, dict):
                continue
            display = str(info.get("display_name") or internal)
            return str(internal), display
    except (OSError, ValueError, AttributeError, SyntaxError):
        pass
    return fallback


# Built-in Steam Proton tool IDs. Source of truth is Steam itself; this list is
# best-effort for the dropdown and may lag a release. Newer Proton tools are
# discovered via `compatibilitytools.d` so users always see GE-Proton/etc.
_BUILTIN_PROTON: tuple[str, ...] = (
    "",
    "proton_experimental",
    "proton_9_0",
    "proton_8_0",
    "proton_7_0",
)


def get_available_proton_tools(steam_root: Path | None) -> list[str]:
    """List Proton/GE tools: built-in first, then compatibilitytools.d."""
    tools: list[str] = list(_BUILTIN_PROTON)
    dirs: list[Path] = []
    compat_dir = get_compattools_dir(steam_root)
    if compat_dir and compat_dir.exists():
        dirs.append(compat_dir)
    dirs.extend(get_system_compattools_dirs())
    for d in dirs:
        try:
            items = sorted(d.iterdir())
        except OSError:
            continue
        for item in items:
            if (
                item.is_dir()
                and not item.name.startswith(".")
                and ((item / "proton").exists() or (item / "compatibilitytool.vdf").exists())
            ):
                internal, _display = read_tool_manifest(item)
                if internal not in tools:
                    tools.append(internal)
    return tools
