"""Game save detection, backup, and restore."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .fsutil import dir_size as _dir_size
from .paths import (
    PathValidationError,
    sanitize_filename,
    validate_user_path,
    validate_within,
)

_BACKUP_ROOT = Path.home() / ".config" / "protonshift" / "backups"

# Reject backups larger than 4 GB raw or with > 50k files. A genuine save set
# never approaches this; it is a tripwire for accidental backups of full
# install dirs and a soft DoS guard on disk usage.
_MAX_BACKUP_BYTES = 4 * 1024 * 1024 * 1024
_MAX_BACKUP_FILES = 50_000


@dataclass
class SaveLocation:
    path: str
    exists: bool
    size_bytes: int = 0
    label: str = ""


@dataclass
class BackupInfo:
    path: str
    filename: str
    size_bytes: int
    created: str


def find_save_paths(app_id: str, prefix_path: str | None) -> list[SaveLocation]:
    """Detect possible save locations for a game.

    ``prefix_path`` is validated through :func:`validate_user_path`; if it
    falls outside a user-writable root we skip the prefix portion rather
    than crawling arbitrary directories.
    """
    locations: list[SaveLocation] = []

    prefix: Path | None = None
    if prefix_path:
        try:
            prefix = validate_user_path(prefix_path, allow_missing=True)
        except PathValidationError:
            prefix = None
    if prefix is not None:
        # Proton saves: various common save paths inside prefix
        save_candidates = [
            (prefix / "pfx" / "drive_c" / "users" / "steamuser" / "Saved Games", "Proton Saved Games"),
            (prefix / "pfx" / "drive_c" / "users" / "steamuser" / "Documents", "Proton Documents"),
            (prefix / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Local", "Proton AppData/Local"),
            (prefix / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming", "Proton AppData/Roaming"),
            (prefix / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "LocalLow", "Proton AppData/LocalLow"),
        ]
        for path, label in save_candidates:
            if path.exists():
                size = _dir_size(path)
                if size > 0:
                    locations.append(SaveLocation(
                        path=str(path),
                        exists=True,
                        size_bytes=size,
                        label=label,
                    ))

    # Native Linux save dirs. ``app_id`` is sanitized to a single segment so a
    # malicious value like ``../../etc`` cannot escape ``userdata/``.
    safe_app_id = sanitize_filename(app_id, fallback="unknown")
    home = Path.home()
    native_candidates = [
        (home / ".local" / "share" / "Steam" / "userdata", "Steam Cloud / Userdata"),
    ]
    for path, label in native_candidates:
        app_subdir = path / safe_app_id
        if app_subdir.exists():
            size = _dir_size(app_subdir)
            if size > 0:
                locations.append(SaveLocation(
                    path=str(app_subdir),
                    exists=True,
                    size_bytes=size,
                    label=label,
                ))

    return locations


def backup_saves(app_id: str, paths: list[str]) -> str | None:
    """Backup save directories to a timestamped zip. Returns backup path or None.

    Each input path's tree is added under ``<basename>/`` inside the archive,
    so identical leaf names from different roots cannot overwrite each other.
    Aborts (and removes the partial zip) if size or file-count tripwires fire.
    """
    safe_app_id = sanitize_filename(app_id, fallback="unknown")
    backup_dir = _BACKUP_ROOT / safe_app_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / f"backup_{timestamp}.zip"

    total_bytes = 0
    total_files = 0
    used_basenames: dict[str, int] = {}

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for save_path_str in paths:
                # Validate every input path lives under a user-writable root
                # before touching the filesystem. This both stops the API
                # being abused to enumerate /etc and gives CodeQL a clean
                # sanitizer it can recognise on the data-flow path.
                try:
                    save_path = validate_user_path(save_path_str, allow_missing=True)
                except PathValidationError:
                    continue
                if not save_path.exists():
                    continue
                base_name = sanitize_filename(save_path.name, fallback="root")
                count = used_basenames.get(base_name, 0)
                used_basenames[base_name] = count + 1
                arc_root = base_name if count == 0 else f"{base_name}_{count}"
                for fpath in save_path.rglob("*"):
                    if not fpath.is_file() or fpath.is_symlink():
                        continue
                    try:
                        size = fpath.lstat().st_size
                    except OSError:
                        continue
                    total_bytes += size
                    total_files += 1
                    if total_bytes > _MAX_BACKUP_BYTES or total_files > _MAX_BACKUP_FILES:
                        raise OSError("Backup exceeded size or file-count limit")
                    rel = fpath.relative_to(save_path)
                    zf.write(fpath, f"{arc_root}/{rel.as_posix()}")
        return str(zip_path)
    except OSError:
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def list_backups(app_id: str) -> list[BackupInfo]:
    """List all backups for a game."""
    safe_app_id = sanitize_filename(app_id, fallback="unknown")
    backup_dir = _BACKUP_ROOT / safe_app_id
    if not backup_dir.exists():
        return []

    backups: list[BackupInfo] = []
    for zf in sorted(backup_dir.glob("backup_*.zip"), reverse=True):
        try:
            stat = zf.stat()
            created = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
            backups.append(BackupInfo(
                path=str(zf),
                filename=zf.name,
                size_bytes=stat.st_size,
                created=created,
            ))
        except OSError:
            pass
    return backups


def restore_backup(backup_path: str, target_dir: str) -> bool:
    """Restore a backup zip to the target directory.

    Hardened against zip-slip: each archive member is verified to land under
    ``target_dir`` before extraction. Backups must originate from
    :data:`_BACKUP_ROOT`; arbitrary zip paths are rejected. The target dir
    must live under one of the user-writable roots.
    """
    zip_path = Path(backup_path).resolve(strict=False)

    try:
        validate_within(_BACKUP_ROOT, zip_path)
    except PathValidationError:
        return False
    try:
        target = validate_user_path(target_dir, allow_missing=True)
    except PathValidationError:
        return False

    if not zip_path.exists():
        return False

    target.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # zipfile member names use forward slashes; reject absolute
                # paths and parent-traversal before extraction.
                member_name = member.filename
                if member_name.startswith("/") or "\x00" in member_name:
                    return False
                resolved = (target / member_name).resolve(strict=False)
                try:
                    validate_within(target, resolved)
                except PathValidationError:
                    return False
            zf.extractall(target)
        return True
    except (zipfile.BadZipFile, OSError):
        return False
