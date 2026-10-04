"""Non-Steam games added to Steam ("Add a Non-Steam Game").

They live in the binary ``userdata/<id>/config/shortcuts.vdf``, not in an
appmanifest. Each has a 32-bit app id Steam generated for it; its Proton
prefix is ``steamapps/compatdata/<that id>`` and its compatibility tool is
stored in ``config.vdf`` under the same id, exactly like a store game. Launch
options, however, live inside shortcuts.vdf itself, so ProtonShift shows them
read-only rather than editing ``localconfig.vdf`` for them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import vdf

from .steam import get_userdata_dir


@dataclass
class SteamShortcut:
    app_id: str  # unsigned 32-bit id, decimal
    name: str
    exe: str
    start_dir: Path | None
    launch_options: str
    compatdata_path: Path | None

    @property
    def game_id(self) -> str:
        """The 64-bit id ``steam://rungameid/`` needs for a shortcut."""
        return str((int(self.app_id) << 32) | 0x02000000)


def _get(entry: dict, *names: str) -> object:
    """Case-insensitive field lookup (Steam has changed key casing over time)."""
    lowered = {str(k).lower(): v for k, v in entry.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _unquote(value: object) -> str:
    text = value if isinstance(value, str) else ""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text


def read_shortcuts(path: Path, steam_root: Path) -> list[SteamShortcut]:
    """Parse one shortcuts.vdf. A missing or corrupt file yields no shortcuts."""
    try:
        with open(path, "rb") as f:
            data = vdf.binary_load(f)
    except (OSError, SyntaxError, ValueError, KeyError, IndexError, UnicodeDecodeError):
        return []
    entries = _get(data, "shortcuts") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return []
    shortcuts: list[SteamShortcut] = []
    for entry in entries.values():
        if not isinstance(entry, dict):
            continue
        raw_id = _get(entry, "appid")
        name = _get(entry, "AppName")
        if not isinstance(raw_id, int) or not isinstance(name, str) or not name.strip():
            continue
        app_id = str(raw_id & 0xFFFFFFFF)  # stored signed; Steam uses it unsigned
        start = _unquote(_get(entry, "StartDir"))
        start_dir = Path(start) if start and Path(start).is_dir() else None
        compatdata = steam_root / "steamapps" / "compatdata" / app_id
        options = _get(entry, "LaunchOptions")
        shortcuts.append(
            SteamShortcut(
                app_id=app_id,
                name=name.strip(),
                exe=_unquote(_get(entry, "Exe")),
                start_dir=start_dir,
                launch_options=options if isinstance(options, str) else "",
                compatdata_path=compatdata if compatdata.exists() else None,
            )
        )
    shortcuts.sort(key=lambda s: s.name.lower())
    return shortcuts


def discover_shortcuts(steam_root: Path | None) -> list[SteamShortcut]:
    """Non-Steam shortcuts of the most recently active Steam account."""
    if not steam_root:
        return []
    userdata = get_userdata_dir(steam_root)
    if not userdata:
        return []
    return read_shortcuts(userdata / "config" / "shortcuts.vdf", steam_root)
