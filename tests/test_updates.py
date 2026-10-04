"""Tests for the manual update check's pure logic (`core/updates.py`).

No network: only version parsing/comparison and the release-URL allow-list.
"""

from __future__ import annotations

import pytest

from protonshift.core.updates import RELEASES_PAGE, is_newer, parse_version, release_url


@pytest.mark.parametrize(
    ("text", "expected"),
    [("v1.2.0", (1, 2, 0)), ("1.2", (1, 2)), (" v10.0.1 ", (10, 0, 1)), ("1.3.0-beta.1", (1, 3, 0)),
     ("latest", None), ("", None), (None, None)],
)
def test_parse_version(text: object, expected: tuple[int, ...] | None) -> None:
    assert parse_version(text) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("latest", "current", "expected"),
    [("1.2.1", "1.2.0", True), ("v1.3.0", "1.2.9", True), ("1.10.0", "1.9.0", True),
     ("1.2.0", "1.2.0", False), ("1.2", "1.2.0", False), ("1.1.9", "1.2.0", False),
     ("garbage", "1.2.0", False), ("1.2.1", "garbage", False)],
)
def test_is_newer(latest: str, current: str, expected: bool) -> None:
    assert is_newer(latest, current) is expected


def test_release_url_only_trusts_our_releases() -> None:
    ours = RELEASES_PAGE + "/tag/v1.2.0"
    assert release_url(ours) == ours
    assert release_url("https://evil.example/releases/tag/v9") == RELEASES_PAGE
    assert release_url("https://github.com/I4cTime/protonshift/releases-evil/x") == RELEASES_PAGE
    assert release_url(None) == RELEASES_PAGE
