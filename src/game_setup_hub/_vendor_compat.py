"""Make vendored native extensions tolerate Python minor-version drift.

When the app is packaged (AppImage / .deb / .rpm) Python dependencies are
vendored into a directory that gets prepended to ``sys.path``. Native
extensions (``.so``) are ABI-locked to the Python build that produced them
(``cp312-…``). If the user is running a different Python minor version,
those ``.so`` files cannot load and importing the package raises
``ImportError`` — even when a perfectly good system copy exists further
down ``sys.path``.

The previous strategy was to ``shutil.rmtree`` the offending vendor dirs.
That is silently a no-op on read-only squashfs (i.e. inside an AppImage),
which is exactly the deployment we needed it to work in.

This module instead resolves the conflict by mutating ``sys.path`` —
which lives in process memory and works regardless of filesystem
permissions:

1. Detect whether any vendored native package has an ABI-incompatible
   ``.so`` for the running interpreter.
2. If so, prepend the standard system + user site-packages directories
   so the system copy of those packages wins import resolution. The
   vendor dir stays for everything else (``vdf``, ``fastapi``, …).

This file is imported as the very first line of :mod:`game_setup_hub.api._app`,
before any third-party package is touched, so the path tweak takes effect
before pydantic/FastAPI try to load ``pydantic_core``.
"""

from __future__ import annotations

import logging
import site
import sys
import sysconfig
from pathlib import Path

log = logging.getLogger("protonshift.vendor_compat")

# Native extensions actually present in our vendor set. Anything not in this
# list is either pure-Python or not a declared dependency.
_NATIVE_PACKAGES: tuple[str, ...] = (
    "pydantic_core",
)

_SOABI = sysconfig.get_config_var("SOABI") or ""


def _has_compatible_so(pkg_dir: Path) -> bool:
    """True if ``pkg_dir`` is pure Python or has a ``.so`` for our SOABI."""
    so_files = list(pkg_dir.glob("*.so"))
    if not so_files:
        return True
    return any(_SOABI in f.name for f in so_files)


def _vendor_dirs() -> list[Path]:
    """Return the vendor directories currently on ``sys.path``."""
    out: list[Path] = []
    for entry in sys.path:
        if not entry:
            continue
        p = Path(entry)
        if "vendor" in p.parts and p.is_dir():
            out.append(p)
    return out


def _has_incompatible_native_pkg(vendor_dirs: list[Path]) -> bool:
    for vd in vendor_dirs:
        for pkg in _NATIVE_PACKAGES:
            pkg_dir = vd / pkg
            if pkg_dir.is_dir() and not _has_compatible_so(pkg_dir):
                log.warning(
                    "Vendored %s has no .so matching %r; will prefer system site-packages.",
                    pkg, _SOABI,
                )
                return True
    return False


def _system_site_dirs() -> list[str]:
    """Best-effort list of system + user site-packages."""
    seen: set[str] = set()
    out: list[str] = []
    candidates: list[str] = []
    try:
        candidates.extend(site.getsitepackages())
    except (AttributeError, OSError):
        pass
    user = ""
    try:
        user = site.getusersitepackages()
    except (AttributeError, OSError):
        pass
    if user:
        candidates.append(user)
    for c in candidates:
        if c and c not in seen and Path(c).is_dir():
            seen.add(c)
            out.append(c)
    return out


def fixup_vendor_path() -> None:
    """Reorder ``sys.path`` when vendored native extensions don't match.

    On match, this is a no-op. On mismatch, the system + user site-packages
    directories are inserted at the front of ``sys.path`` so the system copy
    of any conflicting native package is found before the broken vendored
    one. The filesystem is never touched.
    """
    vendor_dirs = _vendor_dirs()
    if not vendor_dirs:
        return
    if not _has_incompatible_native_pkg(vendor_dirs):
        return

    inserted: list[str] = []
    for sp in _system_site_dirs():
        if sp not in sys.path:
            sys.path.insert(0, sp)
            inserted.append(sp)

    if inserted:
        log.warning(
            "Inserted system site-packages at the head of sys.path for ABI fallback: %s",
            inserted,
        )
    else:
        log.warning(
            "ABI mismatch detected for vendored native extensions but no system "
            "site-packages were available. Imports of %s may fail. Install the "
            "package system-wide (e.g. `python3-pydantic`) or run with the "
            "interpreter the AppImage was built against.",
            ", ".join(_NATIVE_PACKAGES),
        )


fixup_vendor_path()
