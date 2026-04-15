"""Save/load application profiles: launch opts, env, Proton, power preset."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

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


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip() or "profile"


def save_profile(profile: ApplicationProfile) -> bool:
    path = ensure_profiles_dir() / f"{_safe_filename(profile.name)}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(profile), f, indent=2)
        return True
    except OSError:
        return False


def load_profile(name: str) -> ApplicationProfile | None:
    path = PROFILES_DIR / f"{_safe_filename(name)}.json"
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
    path = PROFILES_DIR / f"{_safe_filename(name)}.json"
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError:
            pass
    return False
