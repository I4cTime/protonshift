"""Cover the parts of fsutil whose bugs would corrupt user config files."""

from __future__ import annotations

from pathlib import Path

import pytest

from game_setup_hub.fsutil import (
    atomic_write_bytes,
    atomic_write_text,
    dir_size,
    human_size,
)


def test_dir_size_sums_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"world!")
    assert dir_size(tmp_path) == len(b"hello") + len(b"world!")


def test_dir_size_skips_symlinks_by_default(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "a").write_bytes(b"x" * 10)
    link = tmp_path / "link"
    link.symlink_to(real)
    # 10 bytes for the file, plus the symlink itself contributes nothing
    assert dir_size(tmp_path) == 10


def test_dir_size_returns_zero_for_missing(tmp_path: Path) -> None:
    assert dir_size(tmp_path / "nope") == 0


@pytest.mark.parametrize(
    "raw,expected_unit",
    [
        (0, "B"),
        (1023, "B"),
        (1024, "KB"),
        (1024 * 1024, "MB"),
        (1024 ** 3, "GB"),
        (1024 ** 4, "TB"),
    ],
)
def test_human_size_unit_progression(raw: int, expected_unit: str) -> None:
    assert human_size(raw).endswith(expected_unit)


def test_atomic_write_text_replaces_existing(tmp_path: Path) -> None:
    target = tmp_path / "config.conf"
    target.write_text("old contents", encoding="utf-8")
    atomic_write_text(target, "new contents")
    assert target.read_text(encoding="utf-8") == "new contents"


def test_atomic_write_text_creates_parents(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "file.txt"
    atomic_write_text(target, "ok")
    assert target.read_text(encoding="utf-8") == "ok"


def test_atomic_write_text_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    atomic_write_text(target, "x")
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".file.txt.")]
    assert leftovers == []


def test_atomic_write_bytes_roundtrips(tmp_path: Path) -> None:
    target = tmp_path / "blob.bin"
    payload = b"\x00\x01\x02binary"
    atomic_write_bytes(target, payload)
    assert target.read_bytes() == payload
