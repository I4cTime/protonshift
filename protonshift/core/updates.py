"""Manual update check against the project's GitHub releases.

Nothing here runs on its own: the About card calls :func:`check_for_update`
only when the user presses "Check for updates". The request carries no
identifying data beyond the app's User-Agent. Pure Python - no PySide6 import.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .. import __version__

RELEASES_API = "https://api.github.com/repos/I4cTime/protonshift/releases/latest"
RELEASES_PAGE = "https://github.com/I4cTime/protonshift/releases"
USER_AGENT = f"ProtonShift/{__version__}"

_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)*)")


class UpdateError(RuntimeError):
    """Raised when the update check fails (network, bad response)."""


@dataclass(frozen=True)
class UpdateCheck:
    current: str
    latest: str
    newer: bool
    url: str


def parse_version(text: str) -> tuple[int, ...] | None:
    """``"v1.2.0"`` / ``"1.2"`` -> ``(1, 2, 0)`` / ``(1, 2)``; None if not a version."""
    if not isinstance(text, str):
        return None
    match = _VERSION_RE.match(text.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` is a strictly higher version than ``current``.

    Compares numerically, padding the shorter one with zeros (1.2 == 1.2.0).
    An unparseable version on either side is never "newer".
    """
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def release_url(candidate: object) -> str:
    """The release page to open: GitHub's own link if it is one of ours.

    The URL comes from a network response, so anything that isn't under this
    project's releases falls back to the fixed releases page.
    """
    if isinstance(candidate, str) and candidate.startswith(RELEASES_PAGE + "/"):
        return candidate
    return RELEASES_PAGE


def check_for_update(current: str = __version__, timeout: float = 10) -> UpdateCheck:
    """Ask GitHub for the newest release. Raises :class:`UpdateError`."""
    request = urllib.request.Request(
        RELEASES_API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise UpdateError(f"GitHub answered with an error ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError("Couldn't reach GitHub. Check your connection and try again.") from exc
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise UpdateError("Unexpected response from GitHub.") from exc
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if parse_version(tag) is None:
        raise UpdateError("Unexpected response from GitHub.")
    latest = tag.strip().lstrip("v")
    return UpdateCheck(
        current=current,
        latest=latest,
        newer=is_newer(latest, current),
        url=release_url(data.get("html_url")),
    )
