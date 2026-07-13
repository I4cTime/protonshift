"""Configuration profiles: a named snapshot of launch options, compat tool,
gaming env vars, and power profile that can be re-applied later.

Ported from the original ProtonShift core. Storage only — capturing and
applying the live values is the controller's job (it reads/writes the other
domain modules).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .fsutil import atomic_write_text
from .paths import sanitize_filename

PROFILES_DIR = Path.home() / ".config" / "protonshift" / "profiles"


@dataclass
class ApplicationProfile:
    name: str
    launch_options: str
    compat_tool: str
    env_vars: dict[str, str]
    power_profile: str


def ensure_profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def list_profiles() -> list[str]:
    ensure_profiles_dir()
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json") if p.is_file())


def _profile_path(name: str) -> Path:
    return ensure_profiles_dir() / f"{sanitize_filename(name, fallback='profile')}.json"


def save_profile(profile: ApplicationProfile) -> bool:
    try:
        atomic_write_text(_profile_path(profile.name), json.dumps(asdict(profile), indent=2))
        return True
    except OSError:
        return False


def load_profile(name: str) -> ApplicationProfile | None:
    path = _profile_path(name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ApplicationProfile(
            name=data.get("name", name),
            launch_options=data.get("launch_options", ""),
            compat_tool=data.get("compat_tool", ""),
            env_vars=dict(data.get("env_vars", {})),
            power_profile=data.get("power_profile", ""),
        )
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def delete_profile(name: str) -> bool:
    path = _profile_path(name)
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError:
            pass
    return False
