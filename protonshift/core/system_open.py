"""Open files/folders in the desktop file manager and hand URIs to the system.

Replaces the old ``/open-path`` and ``/open-uri`` endpoints. Everything goes
through the host runner so it works inside a Flatpak (``flatpak-spawn --host``),
and both entry points validate their argument so a caller can't be tricked into
opening an arbitrary system path or a dangerous URI scheme.
"""

from __future__ import annotations

import subprocess

from .host import host_argv
from .paths import PathValidationError, validate_user_path

# Only these URI schemes may be handed to the opener. steam:// covers
# rungameid / gameproperties / nav; heroic:// launches Heroic titles.
_ALLOWED_SCHEMES = ("steam:", "heroic:")


def _spawn(argv: list[str]) -> tuple[bool, str]:
    try:
        subprocess.Popen(  # noqa: S603 — argv is validated / constant
            host_argv(argv),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (FileNotFoundError, OSError) as exc:
        return False, f"Couldn't open: {exc}"
    return True, ""


def open_path(path: str) -> tuple[bool, str]:
    """Open a user-owned file/folder in the file manager. ``(ok, message)``."""
    try:
        p = validate_user_path(path, allow_missing=False)
    except PathValidationError:
        return False, "Path is not accessible."
    return _spawn(["xdg-open", str(p)])


def open_uri(uri: str) -> tuple[bool, str]:
    """Hand an allow-listed URI (steam://, heroic://) to the system opener."""
    uri = uri.strip()
    if not any(uri.lower().startswith(s) for s in _ALLOWED_SCHEMES):
        return False, "Unsupported URI."
    return _spawn(["xdg-open", uri])
