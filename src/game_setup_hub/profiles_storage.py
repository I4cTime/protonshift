"""Save/load application profiles: launch opts, env, Proton, power preset."""

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
    """Return sorted list of profile names (without .json)."""
    ensure_profiles_dir()
    names = []
    for p in PROFILES_DIR.glob("*.json"):
        if p.is_file():
            names.append(p.stem)
    return sorted(names)


def _profile_path(name: str) -> Path:
    return ensure_profiles_dir() / f"{sanitize_filename(name, fallback='profile')}.json"


def save_profile(profile: ApplicationProfile) -> bool:
    path = _profile_path(profile.name)
    try:
        atomic_write_text(path, json.dumps(asdict(profile), indent=2))
        return True
    except OSError:
        return False


def load_profile(name: str) -> ApplicationProfile | None:
    path = _profile_path(name)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
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
