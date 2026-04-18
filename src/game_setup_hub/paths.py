"""Path validation helpers — keep API inputs from escaping their sandbox.

Centralised so :mod:`api` (and any future caller) sanitizes the same way and
``..``/absolute/symlink-escape attacks fail at one boundary instead of being
re-implemented per endpoint.
"""

from __future__ import annotations

import re
from pathlib import Path


class PathValidationError(ValueError):
    """Raised when an untrusted path or filename is rejected."""


_FILENAME_BLOCKED = re.compile(r"[^A-Za-z0-9._\- ]")
_LEADING_DOTS = re.compile(r"^\.+")


def sanitize_filename(name: str, *, fallback: str = "untitled") -> str:
    """Reduce ``name`` to a safe single-segment filename.

    - Strips path separators and any non-alphanumeric/whitespace/.-_ chars.
    - Collapses leading ``.`` so we never silently create dotfiles.
    - Trims to 200 chars to stay under common filesystem limits.
    - Returns ``fallback`` if the result is empty.
    """
    if not name:
        return fallback
    cleaned = _FILENAME_BLOCKED.sub("_", name)
    cleaned = _LEADING_DOTS.sub("", cleaned).strip().rstrip(".")
    cleaned = cleaned[:200]
    return cleaned or fallback


def safe_join(base: Path, *parts: str) -> Path:
    """Join ``parts`` onto ``base`` and verify the result stays under ``base``.

    ``base`` must already exist (or at least its parent must); the joined
    components may not yet exist. Symlinks are not followed by ``resolve``
    when targets are missing, which is fine — we only need the lexical
    parent check to reject ``..`` escape and absolute overrides.

    Raises :class:`PathValidationError` on escape, absolute overrides, or
    null-byte injection.
    """
    base_resolved = base.resolve(strict=False)
    for part in parts:
        if "\x00" in part:
            raise PathValidationError("Null byte in path component")
        if Path(part).is_absolute():
            raise PathValidationError(f"Absolute path component not allowed: {part!r}")

    candidate = (base_resolved.joinpath(*parts)).resolve(strict=False)
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise PathValidationError(
            f"Path {candidate} escapes base {base_resolved}"
        ) from exc
    return candidate


def validate_within(base: Path, candidate: Path) -> Path:
    """Verify ``candidate`` resolves under ``base``. Returns the resolved path."""
    base_resolved = base.resolve(strict=False)
    candidate_resolved = candidate.resolve(strict=False)
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise PathValidationError(
            f"Path {candidate_resolved} is not under {base_resolved}"
        ) from exc
    return candidate_resolved


# Roots a localhost API caller may interact with. Anything outside these is
# rejected — keeps a malicious or buggy client from poking at /etc, /usr, etc.
_USER_PATH_ROOTS: tuple[Path, ...] = (
    Path.home(),
    Path("/run/media"),
    Path("/media"),
    Path("/mnt"),
    Path("/tmp"),  # noqa: S108 — explicit allow, the API never *creates* in /tmp
)


def validate_user_path(path: str | Path, *, allow_missing: bool = False) -> Path:
    """Return a resolved :class:`Path` if it lives under a user-writable root.

    Used at API boundaries. Rejects null bytes, ``..`` escape, and anything
    outside :data:`_USER_PATH_ROOTS`. Set ``allow_missing=False`` (default) to
    require the target to exist — typical for "open this folder" actions.
    """
    raw = str(path)
    if "\x00" in raw:
        raise PathValidationError("Null byte in path")
    p = Path(raw).expanduser().resolve(strict=False)
    if not allow_missing and not p.exists():
        raise PathValidationError(f"Path does not exist: {p}")
    for root in _USER_PATH_ROOTS:
        try:
            p.relative_to(root.resolve(strict=False))
            return p
        except ValueError:
            continue
    raise PathValidationError(f"Path {p} is outside permitted roots")
