"""Round-trip + atomicity tests for vdf_config."""

from __future__ import annotations

from pathlib import Path

import vdf

from game_setup_hub.vdf_config import (
    get_compat_tool,
    get_launch_options,
    set_compat_tool,
    set_launch_options,
)


def _seed_localconfig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "UserLocalConfigStore": {
            "Software": {
                "Valve": {
                    "Steam": {
                        "apps": {
                            "440": {"LaunchOptions": "-novid"},
                        },
                        "CompatToolMapping": {
                            "440": {"name": "proton_8_0", "config": "", "priority": "250"},
                        },
                    }
                }
            }
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        vdf.dump(data, f, pretty=True)


def test_get_existing_launch_options(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    _seed_localconfig(cfg)
    assert get_launch_options(cfg, "440") == "-novid"


def test_get_existing_compat_tool(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    _seed_localconfig(cfg)
    assert get_compat_tool(cfg, "440") == "proton_8_0"


def test_set_launch_options_creates_nodes(tmp_path: Path) -> None:
    cfg = tmp_path / "fresh.vdf"
    assert set_launch_options(cfg, "12345", "MANGOHUD=1 %command%") is True
    assert get_launch_options(cfg, "12345") == "MANGOHUD=1 %command%"


def test_set_launch_options_preserves_other_apps(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    _seed_localconfig(cfg)
    set_launch_options(cfg, "10", "-fullscreen")
    assert get_launch_options(cfg, "10") == "-fullscreen"
    # Existing app must still be intact
    assert get_launch_options(cfg, "440") == "-novid"
    assert get_compat_tool(cfg, "440") == "proton_8_0"


def test_set_compat_tool_clears_when_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    _seed_localconfig(cfg)
    set_compat_tool(cfg, "440", "")
    assert get_compat_tool(cfg, "440") == ""


def test_writes_are_atomic_no_temp_files(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    _seed_localconfig(cfg)
    set_launch_options(cfg, "440", "-newopt")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".localconfig.vdf.")]
    assert leftovers == []
