"""Steam shader cache inspection and management."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .fsutil import dir_size as _dir_size


@dataclass
class ShaderCacheInfo:
    app_id: str
    path: str
    exists: bool
    size_bytes: int = 0


def _shader_cache_dir(steam_root: Path, app_id: str) -> Path:
    return steam_root / "steamapps" / "shadercache" / app_id


def get_shader_cache_info(steam_root: Path, app_id: str) -> ShaderCacheInfo:
    """Get shader cache info for a single game."""
    cache_dir = _shader_cache_dir(steam_root, app_id)
    if not cache_dir.exists():
        return ShaderCacheInfo(app_id=app_id, path=str(cache_dir), exists=False)
    return ShaderCacheInfo(
        app_id=app_id,
        path=str(cache_dir),
        exists=True,
        size_bytes=_dir_size(cache_dir),
    )


def clear_shader_cache(steam_root: Path, app_id: str) -> bool:
    """Delete the shader cache directory for a game. Returns True on success."""
    cache_dir = _shader_cache_dir(steam_root, app_id)
    if not cache_dir.exists():
        return True
    try:
        shutil.rmtree(cache_dir)
        return True
    except OSError:
        return False


def get_total_shader_cache_size(steam_root: Path) -> int:
    """Get the total size of all shader caches in bytes."""
    cache_root = steam_root / "steamapps" / "shadercache"
    if not cache_root.exists():
        return 0
    return _dir_size(cache_root)
