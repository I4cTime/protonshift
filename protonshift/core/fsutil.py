"""Shared filesystem helpers — directory sizing, human-readable sizes, atomic writes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def dir_size(path: Path, *, follow_symlinks: bool = False) -> int:
    """Recursively compute directory size in bytes.

    Symlinks are skipped by default to avoid infinite loops and double-counting.
    Errors on individual files are silently ignored — a partial size is more
    useful than an exception in UI-facing code.
    """
    total = 0
    try:
        for entry in path.rglob("*"):
            if not follow_symlinks and entry.is_symlink():
                continue
            if entry.is_file():
                try:
                    total += entry.stat().st_size if follow_symlinks else entry.lstat().st_size
                except OSError:
                    continue
    except OSError:
        return total
    return total


def human_size(size_bytes: float) -> str:
    """Format a byte count as a 1-decimal-place human-readable string."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def atomic_write_text(
    path: Path,
    data: str,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """Atomically replace ``path`` with ``data`` via a tempfile in the same dir.

    Crash-safety: writes to ``<name>.<pid>.tmp`` in the same directory, fsyncs,
    then ``os.replace``\\s onto the target. The same-directory requirement is
    what makes ``rename`` atomic on POSIX. Parent directories are created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # Some filesystems (tmpfs, network mounts) don't support fsync;
                # the write is still durable enough for our config files.
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomic binary equivalent of :func:`atomic_write_text`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
