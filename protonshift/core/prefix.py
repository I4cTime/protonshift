"""Wine/Proton prefix inspection and management.

Ported from the original ProtonShift core (was gated behind a FastAPI route);
same logic, no web layer. Reads the DXVK/VKD3D version straight out of the PE
resource of the installed DLLs, sizes the prefix, and can delete it — with the
same defensive ``validate_user_path`` guard so a bug can never ``rmtree`` a
system path.
"""

from __future__ import annotations

import shutil
import struct
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .fsutil import dir_size as _dir_size
from .paths import PathValidationError, validate_user_path


@dataclass
class PrefixInfo:
    path: str
    exists: bool
    size_bytes: int = 0
    created: str = ""
    dxvk_version: str = ""
    vkd3d_version: str = ""


def _read_pe_file_version(dll_path: Path) -> str:
    """Read the VS_FIXEDFILEINFO version from a PE file. "" if not found."""
    try:
        data = dll_path.read_bytes()
    except OSError:
        return ""
    magic = b"\xbd\x04\xef\xfe"  # VS_FIXEDFILEINFO signature
    idx = data.find(magic)
    if idx == -1:
        return ""
    try:
        ms = struct.unpack_from("<I", data, idx + 4)[0]
        ls = struct.unpack_from("<I", data, idx + 8)[0]
        major = (ms >> 16) & 0xFFFF
        minor = ms & 0xFFFF
        build = (ls >> 16) & 0xFFFF
        if major == 0 and minor == 0 and build == 0:
            return ""
        return f"{major}.{minor}.{build}" if build > 0 else f"{major}.{minor}"
    except (struct.error, IndexError):
        return ""


def _system32(prefix: Path) -> Path:
    sys32 = prefix / "pfx" / "drive_c" / "windows" / "system32"
    if not sys32.exists():
        sys32 = prefix / "drive_c" / "windows" / "system32"
    return sys32


def _detect_dxvk_version(prefix: Path) -> str:
    sys32 = _system32(prefix)
    for dll_name in ("d3d11.dll", "dxgi.dll"):
        dll = sys32 / dll_name
        if dll.exists():
            ver = _read_pe_file_version(dll)
            if ver:
                return ver
    return ""


def _detect_vkd3d_version(prefix: Path) -> str:
    dll = _system32(prefix) / "d3d12.dll"
    return _read_pe_file_version(dll) if dll.exists() else ""


def get_prefix_info(path: str) -> PrefixInfo:
    """Inspect a Wine/Proton prefix directory (size, created, DXVK/VKD3D)."""
    try:
        prefix = validate_user_path(path, allow_missing=True)
    except PathValidationError:
        return PrefixInfo(path=path, exists=False)
    if not prefix.exists():
        return PrefixInfo(path=path, exists=False)

    created = ""
    try:
        created = datetime.fromtimestamp(prefix.stat().st_ctime, tz=UTC).isoformat()
    except OSError:
        pass

    return PrefixInfo(
        path=path,
        exists=True,
        size_bytes=_dir_size(prefix),
        created=created,
        dxvk_version=_detect_dxvk_version(prefix),
        vkd3d_version=_detect_vkd3d_version(prefix),
    )


def delete_prefix(path: str) -> bool:
    """Delete a prefix directory. Fail-closed: path must resolve under a
    user-writable root, else refuse. Returns True on success."""
    try:
        prefix = validate_user_path(path, allow_missing=False)
    except PathValidationError:
        return False
    if not prefix.exists() or not prefix.is_dir():
        return False
    try:
        shutil.rmtree(prefix)
        return True
    except OSError:
        return False
