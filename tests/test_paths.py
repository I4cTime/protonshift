"""Sanitization tests — these are the wall between the API and the filesystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from game_setup_hub.paths import (
    PathValidationError,
    safe_join,
    sanitize_filename,
    validate_user_path,
    validate_within,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("simple.json", "simple.json"),
        ("My Game (2024)", "My Game _2024_"),
        ("../escape", "_escape"),
        ("../../etc/passwd", "_.._etc_passwd"),
        ("...hidden", "hidden"),
        ("", "untitled"),
        ("a" * 500, "a" * 200),
    ],
)
def test_sanitize_filename(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_safe_join_blocks_traversal(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError):
        safe_join(tmp_path, "..", "etc")


def test_safe_join_blocks_absolute(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError):
        safe_join(tmp_path, "/etc/passwd")


def test_safe_join_blocks_null_byte(tmp_path: Path) -> None:
    with pytest.raises(PathValidationError):
        safe_join(tmp_path, "a\x00b")


def test_safe_join_allows_subdir(tmp_path: Path) -> None:
    result = safe_join(tmp_path, "sub", "file.txt")
    assert result == (tmp_path / "sub" / "file.txt").resolve()


def test_validate_within_rejects_outside(tmp_path: Path) -> None:
    other = tmp_path.parent / "outside"
    with pytest.raises(PathValidationError):
        validate_within(tmp_path, other)


def test_validate_user_path_accepts_home(tmp_path: Path) -> None:
    # `isolated_home` fixture pins HOME to tmp_path/home.
    home = Path.home()
    target = home / "stuff"
    target.mkdir()
    assert validate_user_path(target) == target.resolve()


def test_validate_user_path_rejects_etc() -> None:
    with pytest.raises(PathValidationError):
        validate_user_path("/etc/passwd")


def test_validate_user_path_requires_existence_by_default() -> None:
    home = Path.home()
    with pytest.raises(PathValidationError):
        validate_user_path(home / "does-not-exist")


def test_validate_user_path_allow_missing() -> None:
    home = Path.home()
    candidate = home / "future"
    assert validate_user_path(candidate, allow_missing=True) == candidate.resolve()
