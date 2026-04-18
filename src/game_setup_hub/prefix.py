"""Wine/Proton prefix inspection and management."""

from __future__ import annotations

import shutil
import struct
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from .fsutil import dir_size as _dir_size


@dataclass
class PrefixInfo:
    path: str
    exists: bool
    size_bytes: int = 0
    created: str = ""
    dxvk_version: str = ""
    vkd3d_version: str = ""


def _read_pe_file_version(dll_path: Path) -> str:
    """
    Read the VS_FIXEDFILEINFO version from a PE file's resource section.
    Returns a version string like "2.4" or "" if not found.
    """
    try:
        data = dll_path.read_bytes()
    except OSError:
        return ""

    # Search for VS_FIXEDFILEINFO magic: 0xFEEF04BD
    magic = b"\xbd\x04\xef\xfe"
    idx = data.find(magic)
    if idx == -1:
        return ""

    # VS_FIXEDFILEINFO starts 4 bytes before the magic value
    # The structure has dwFileVersionMS and dwFileVersionLS at offsets 8 and 12
    try:
        ms = struct.unpack_from("<I", data, idx + 4)[0]
        ls = struct.unpack_from("<I", data, idx + 8)[0]
        major = (ms >> 16) & 0xFFFF
        minor = ms & 0xFFFF
        build = (ls >> 16) & 0xFFFF
        if major == 0 and minor == 0 and build == 0:
            return ""
        if build > 0:
            return f"{major}.{minor}.{build}"
        return f"{major}.{minor}"
    except (struct.error, IndexError):
        return ""


def _detect_dxvk_version(prefix: Path) -> str:
    """Detect DXVK version from d3d11.dll or dxgi.dll inside the prefix."""
    sys32 = prefix / "pfx" / "drive_c" / "windows" / "system32"
    if not sys32.exists():
        sys32 = prefix / "drive_c" / "windows" / "system32"
    for dll_name in ("d3d11.dll", "dxgi.dll"):
        dll = sys32 / dll_name
        if dll.exists():
            ver = _read_pe_file_version(dll)
            if ver:
                return ver
    return ""


def _detect_vkd3d_version(prefix: Path) -> str:
    """Detect VKD3D-Proton version from d3d12.dll inside the prefix."""
    sys32 = prefix / "pfx" / "drive_c" / "windows" / "system32"
    if not sys32.exists():
        sys32 = prefix / "drive_c" / "windows" / "system32"
    dll = sys32 / "d3d12.dll"
    if dll.exists():
        return _read_pe_file_version(dll)
    return ""


def get_prefix_info(path: str) -> PrefixInfo:
    """Get information about a Wine/Proton prefix directory."""
    prefix = Path(path)
    if not prefix.exists():
        return PrefixInfo(path=path, exists=False)

    size_bytes = _dir_size(prefix)

    created = ""
    try:
        stat = prefix.stat()
        from datetime import datetime
        created = datetime.fromtimestamp(stat.st_ctime, tz=UTC).isoformat()
    except OSError:
        pass

    dxvk = _detect_dxvk_version(prefix)
    vkd3d = _detect_vkd3d_version(prefix)

    return PrefixInfo(
        path=path,
        exists=True,
        size_bytes=size_bytes,
        created=created,
        dxvk_version=dxvk,
        vkd3d_version=vkd3d,
    )


def delete_prefix(path: str) -> bool:
    """Delete a Wine/Proton prefix directory. Returns True on success."""
    prefix = Path(path)
    if not prefix.exists():
        return False
    try:
        shutil.rmtree(prefix)
        return True
    except OSError:
        return False
