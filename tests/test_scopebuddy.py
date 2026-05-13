"""ScopeBuddy config parsing, envvars helpers, and rescan."""

from __future__ import annotations

from pathlib import Path

import game_setup_hub.scopebuddy as scb_mod
from game_setup_hub.scopebuddy import (
    delete_envvars,
    list_envvars,
    parse_scb_conf,
    read_envvars,
    rescan_tools,
    write_envvars,
    write_scb_conf,
)


def test_parse_scb_conf_basic(tmp_path: Path) -> None:
    p = tmp_path / "scb.conf"
    p.write_text(
        'export SCB_GAMESCOPE_ARGS="-f -b"\n'
        "SCB_AUTO_RES=1\n"
        "# comment\n"
        "SCB_NOSCOPE=1\n",
        encoding="utf-8",
    )
    cfg = parse_scb_conf(p)
    assert cfg["SCB_GAMESCOPE_ARGS"] == "-f -b"
    assert cfg["SCB_AUTO_RES"] == "1"
    assert cfg["SCB_NOSCOPE"] == "1"


def test_write_scb_conf_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "out.conf"
    ok = write_scb_conf(
        p,
        {"SCB_GAMESCOPE_ARGS": "--mangoapp -f", "SCB_AUTO_RES": "1"},
    )
    assert ok is True
    cfg = parse_scb_conf(p)
    assert cfg["SCB_GAMESCOPE_ARGS"] == "--mangoapp -f"
    assert cfg["SCB_AUTO_RES"] == "1"


def test_envvars_roundtrip(tmp_path, monkeypatch) -> None:
    """``write_envvars`` should land under ``envvars/`` and round-trip."""
    monkeypatch.setattr(scb_mod, "SCOPEBUDDY_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(scb_mod, "SCOPEBUDDY_ENVVARS_DIR", tmp_path / "envvars")

    assert list_envvars() == []

    ok = write_envvars(
        "nvidia-wayland",
        {"VK_DRIVER_FILES": "/usr/share/vulkan/icd.d/nvidia.json", "DXVK_HUD": "fps"},
    )
    assert ok is True

    rows = list_envvars()
    assert any(r["name"] == "nvidia-wayland" for r in rows)

    path, exists, cfg = read_envvars("nvidia-wayland")
    assert exists is True
    assert path.parent == tmp_path / "envvars"
    assert cfg["VK_DRIVER_FILES"].endswith("nvidia.json")
    assert cfg["DXVK_HUD"] == "fps"

    assert delete_envvars("nvidia-wayland") is True
    assert list_envvars() == []


def test_envvars_sanitizes_names(tmp_path, monkeypatch) -> None:
    """Slashes and weird chars in names should not escape ``envvars/``."""
    monkeypatch.setattr(scb_mod, "SCOPEBUDDY_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(scb_mod, "SCOPEBUDDY_ENVVARS_DIR", tmp_path / "envvars")

    assert write_envvars("../escape/attempt:two", {"FOO": "bar"}) is True
    files = list((tmp_path / "envvars").glob("*.conf"))
    assert len(files) == 1
    assert files[0].parent == tmp_path / "envvars"


def test_rescan_tools_clears_cache_and_returns_info() -> None:
    """``rescan_tools`` must drop the lru_cache and return availability info."""
    from game_setup_hub.tool_check import find_tool

    sentinel = "__protonshift_rescan_sentinel__"
    find_tool.cache_clear()
    find_tool(sentinel)
    assert any(sentinel in str(k) for k in find_tool.cache_info()._asdict().values()) or (
        find_tool.cache_info().currsize >= 1
    )

    result = rescan_tools()

    find_tool(sentinel)
    assert find_tool.cache_info().misses >= 1, (
        "after rescan the sentinel lookup must miss the cache again"
    )
    info_at_end = find_tool.cache_info()
    assert info_at_end.hits == 0, (
        "no hits should be recorded post-rescan for distinct probe keys"
    )
    assert {"available", "binary", "path", "version", "config_dir"} <= set(result.keys())
