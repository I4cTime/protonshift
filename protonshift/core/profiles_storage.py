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


# --- export / import ---------------------------------------------------------
#
# Profiles travel as a single JSON "bundle" so one file can carry a whole
# library setup between machines. The bundle is versioned and strictly
# validated on import: unknown/invalid entries are skipped, never partially
# applied, and env var keys go through the same validator the editor uses.

BUNDLE_FORMAT = "protonshift-profiles"
BUNDLE_VERSION = 1
MAX_BUNDLE_BYTES = 4 * 1024 * 1024  # profiles are tiny; refuse anything absurd


@dataclass
class ImportResult:
    imported: list[str]
    skipped_existing: list[str]
    invalid: int

    @property
    def summary(self) -> str:
        parts = [f"Imported {len(self.imported)}"]
        if self.skipped_existing:
            parts.append(f"skipped {len(self.skipped_existing)} existing")
        if self.invalid:
            parts.append(f"ignored {self.invalid} invalid")
        return ", ".join(parts) + "."


class BundleError(ValueError):
    """Raised when a file is not a ProtonShift profile bundle."""


def export_profiles(names: list[str], dest: Path) -> int:
    """Write ``names`` (existing profiles) to ``dest`` as a bundle.

    Returns the number of profiles written. Missing/unreadable profiles are
    skipped. Raises ``OSError`` if the destination can't be written.
    """
    from datetime import UTC, datetime

    profiles = [p for p in (load_profile(n) for n in names) if p is not None]
    bundle = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "profiles": [asdict(p) for p in profiles],
    }
    atomic_write_text(dest, json.dumps(bundle, indent=2) + "\n")
    return len(profiles)


def _coerce_profile(raw: object) -> ApplicationProfile | None:
    """Validate one bundle entry; ``None`` if it isn't a usable profile."""
    from .env_vars import _valid_key

    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()[:200]
    launch = raw.get("launch_options", "")
    compat = raw.get("compat_tool", "")
    power = raw.get("power_profile", "")
    env = raw.get("env_vars", {})
    if not all(isinstance(v, str) for v in (launch, compat, power)):
        return None
    if not isinstance(env, dict):
        return None
    if any("\n" in v or "\r" in v for v in (launch, compat, power)):
        return None
    clean_env: dict[str, str] = {}
    for k, v in env.items():
        if not isinstance(k, str) or not isinstance(v, str) or not _valid_key(k):
            return None
        if "\n" in v or "\r" in v or "\x00" in v:
            return None
        clean_env[k] = v
    return ApplicationProfile(
        name=name,
        launch_options=launch,
        compat_tool=compat,
        env_vars=clean_env,
        power_profile=power,
    )


def read_bundle(src: Path) -> list[ApplicationProfile]:
    """Parse ``src``; returns the valid profiles it holds (invalid ones dropped).

    Raises :class:`BundleError` when the file isn't a bundle at all.
    """
    try:
        if src.stat().st_size > MAX_BUNDLE_BYTES:
            raise BundleError("File is too large to be a profile bundle.")
        data = json.loads(src.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BundleError(f"Couldn't read file: {exc.strerror or exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleError("Not a JSON file.") from exc
    if not isinstance(data, dict) or data.get("format") != BUNDLE_FORMAT:
        raise BundleError("Not a ProtonShift profile bundle.")
    if not isinstance(data.get("version"), int) or data["version"] > BUNDLE_VERSION:
        raise BundleError("Bundle was made by a newer ProtonShift — update to import it.")
    entries = data.get("profiles")
    if not isinstance(entries, list):
        raise BundleError("Bundle has no profiles.")
    return [p for p in (_coerce_profile(e) for e in entries) if p is not None]


def import_profiles(src: Path, *, overwrite: bool = False) -> ImportResult:
    """Import every valid profile from the bundle at ``src``.

    Existing profiles (same sanitized filename) are skipped unless
    ``overwrite`` is set. Raises :class:`BundleError` for non-bundle input.
    """
    try:
        raw_count = len(json.loads(src.read_text(encoding="utf-8")).get("profiles", []))
    except Exception:  # noqa: BLE001 - read_bundle reports the real problem below
        raw_count = 0
    profiles = read_bundle(src)
    existing = set(list_profiles())
    result = ImportResult(imported=[], skipped_existing=[], invalid=max(0, raw_count - len(profiles)))
    for prof in profiles:
        stem = _profile_path(prof.name).stem
        if stem in existing and not overwrite:
            result.skipped_existing.append(prof.name)
            continue
        if save_profile(prof):
            result.imported.append(prof.name)
            existing.add(stem)
        else:
            result.invalid += 1
    return result
