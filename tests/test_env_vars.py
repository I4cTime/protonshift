"""Round-trip tests for the environment.d writer."""

from __future__ import annotations

from pathlib import Path

from game_setup_hub.env_vars import (
    GAMING_CONF,
    read_gaming_env,
    write_conf,
    write_gaming_env,
)


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "70-test.conf"
    payload = {"FOO": "bar", "WITH_SPACES": "hello world", "EMPTY": ""}
    assert write_conf(target, payload, header="generated") is True
    text = target.read_text(encoding="utf-8")
    assert "FOO=\"bar\"" in text
    assert "WITH_SPACES=\"hello world\"" in text
    assert text.startswith("# generated")


def test_write_conf_quotes_special_chars(tmp_path: Path) -> None:
    target = tmp_path / "special.conf"
    write_conf(target, {"SHELL_INJ": 'val with "quotes" and \\backslash'})
    text = target.read_text(encoding="utf-8")
    assert 'SHELL_INJ="val with \\"quotes\\" and \\\\backslash"' in text


def test_write_conf_skips_invalid_keys(tmp_path: Path) -> None:
    target = tmp_path / "bad.conf"
    write_conf(target, {"GOOD": "1", "BAD-KEY": "2", "1NUMERIC": "3"})
    text = target.read_text(encoding="utf-8")
    assert "GOOD=\"1\"" in text
    assert "BAD-KEY" not in text
    assert "1NUMERIC" not in text


def test_gaming_env_roundtrip() -> None:
    original = {"PROTON_LOG": "1", "DXVK_HUD": "fps"}
    assert write_gaming_env(original) is True
    assert read_gaming_env() == original

    target = Path.home() / ".config" / "environment.d" / GAMING_CONF
    assert target.exists()


def test_gaming_env_overwrite_replaces_atomically() -> None:
    write_gaming_env({"A": "1"})
    write_gaming_env({"B": "2"})
    assert read_gaming_env() == {"B": "2"}
