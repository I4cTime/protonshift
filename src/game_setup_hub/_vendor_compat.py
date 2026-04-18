"""Ensure vendored native extensions are compatible with the running Python.

When the app is packaged (AppImage/deb/rpm), Python dependencies are vendored
into a directory added to PYTHONPATH.  Native extensions (.so) are ABI-locked
to the Python version used at build time.  If the user runs a different Python
minor version, those .so files won't load.

This module detects the mismatch early and removes incompatible vendored
packages from sys.path so Python falls back to system site-packages.
"""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path

_NATIVE_PACKAGES = [
    "pydantic_core",
    "uvloop",
    "httptools",
    "watchfiles",
    "yaml",  # PyYAML
]

_SOABI = sysconfig.get_config_var("SOABI") or ""


def _has_compatible_so(pkg_dir: Path) -> bool:
    """Check if a vendored package dir has .so files matching this Python."""
    so_files = list(pkg_dir.glob("*.so"))
    if not so_files:
        return True  # pure-Python package, always compatible
    return any(_SOABI in f.name for f in so_files)


def fixup_vendor_path() -> None:
    """Remove vendored native-extension dirs that are ABI-incompatible."""
    vendor_dirs = [
        p for p in sys.path
        if "vendor" in p and Path(p).is_dir()
    ]
    if not vendor_dirs:
        return

    for vendor_dir in vendor_dirs:
        vp = Path(vendor_dir)
        for pkg_name in _NATIVE_PACKAGES:
            pkg_dir = vp / pkg_name
            if pkg_dir.is_dir() and not _has_compatible_so(pkg_dir):
                _remove_vendored_package(vp, pkg_name)


def _remove_vendored_package(vendor_dir: Path, pkg_name: str) -> None:
    """Remove a single incompatible package from the vendor dir at runtime."""
    import shutil

    pkg_dir = vendor_dir / pkg_name
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir, ignore_errors=True)

    for dist_info in vendor_dir.glob(f"{pkg_name}-*.dist-info"):
        shutil.rmtree(dist_info, ignore_errors=True)

    # Clear any cached import state
    if pkg_name in sys.modules:
        del sys.modules[pkg_name]


fixup_vendor_path()
