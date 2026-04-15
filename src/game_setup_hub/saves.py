"""Game save detection, backup, and restore."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_BACKUP_ROOT = Path.home() / ".config" / "protonshift" / "backups"


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


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in path.rglob("*"):
            if not entry.is_symlink() and entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def find_save_paths(app_id: str, prefix_path: str | None) -> list[SaveLocation]:
    """Detect possible save locations for a game."""
    locations: list[SaveLocation] = []

    if prefix_path:
        prefix = Path(prefix_path)
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

    # Native Linux save dirs
    home = Path.home()
    native_candidates = [
        (home / ".local" / "share" / "Steam" / "userdata", "Steam Cloud / Userdata"),
    ]
    for path, label in native_candidates:
        app_subdir = path / app_id
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
    """Backup save directories to a timestamped zip. Returns backup path or None."""
    backup_dir = _BACKUP_ROOT / app_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / f"backup_{timestamp}.zip"

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for save_path_str in paths:
                save_path = Path(save_path_str)
                if not save_path.exists():
                    continue
                for fpath in save_path.rglob("*"):
                    if fpath.is_file():
                        arcname = str(fpath.relative_to(save_path.parent))
                        zf.write(fpath, arcname)
        return str(zip_path)
    except OSError:
        return None


def list_backups(app_id: str) -> list[BackupInfo]:
    """List all backups for a game."""
    backup_dir = _BACKUP_ROOT / app_id
    if not backup_dir.exists():
        return []

    backups: list[BackupInfo] = []
    for zf in sorted(backup_dir.glob("backup_*.zip"), reverse=True):
        try:
            stat = zf.stat()
            created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
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
    """Restore a backup zip to the target directory. Returns True on success."""
    zip_path = Path(backup_path)
    target = Path(target_dir)
    if not zip_path.exists():
        return False
    target.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target)
        return True
    except (zipfile.BadZipFile, OSError):
        return False
