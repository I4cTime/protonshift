"""Steam shader cache inspection and management.

Ported from the original ProtonShift core. Shader caches live under
``<steam_root>/steamapps/shadercache/<app_id>`` and can grow large; this lets
the UI show and clear them per game plus a grand total.

``app_id`` ultimately comes from ``appmanifest_*.acf`` filenames on disk, which
an attacker (or a stray file) can shape — e.g. ``appmanifest_...acf`` yields an
app_id of ``..`` which would make ``clear_shader_cache`` rmtree ``steamapps``
itself. Steam app ids are always decimal digits, so anything else is rejected,
and the resolved path is additionally verified to stay under ``shadercache/``.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .fsutil import dir_size as _dir_size
from .paths import PathValidationError, validate_within

# Steam app ids are decimal digits only. Anything else (``..``, absolute paths,
# empty string) is untrusted filename residue and must never reach the fs.
_APP_ID_RE = re.compile(r"^[0-9]+$")


@dataclass
class ShaderCacheInfo:
    app_id: str
    path: str
    exists: bool
    size_bytes: int = 0


def _shader_cache_dir(steam_root: Path, app_id: str) -> Path | None:
    """Resolved cache dir for ``app_id``, or ``None`` if the id is unsafe.

    Rejects non-numeric ids, then verifies the joined path resolves under
    ``steamapps/shadercache`` (defence in depth against symlink tricks).
    """
    if not _APP_ID_RE.fullmatch(app_id):
        return None
    base = steam_root / "steamapps" / "shadercache"
    try:
        return validate_within(base, base / app_id)
    except PathValidationError:
        return None


def get_shader_cache_info(steam_root: Path, app_id: str) -> ShaderCacheInfo:
    cache_dir = _shader_cache_dir(steam_root, app_id)
    if cache_dir is None or not cache_dir.exists():
        return ShaderCacheInfo(
            app_id=app_id,
            path=str(cache_dir) if cache_dir is not None else "",
            exists=False,
        )
    return ShaderCacheInfo(
        app_id=app_id, path=str(cache_dir), exists=True, size_bytes=_dir_size(cache_dir)
    )


def clear_shader_cache(steam_root: Path, app_id: str) -> bool:
    """Delete the shader cache dir for a game. True if gone (incl. never existed).

    An invalid ``app_id`` returns False — nothing is deleted.
    """
    cache_dir = _shader_cache_dir(steam_root, app_id)
    if cache_dir is None:
        return False
    if not cache_dir.exists():
        return True
    try:
        shutil.rmtree(cache_dir)
        return True
    except OSError:
        return False


def get_total_shader_cache_size(steam_root: Path) -> int:
    cache_root = steam_root / "steamapps" / "shadercache"
    return _dir_size(cache_root) if cache_root.exists() else 0
