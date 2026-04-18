"""Gamescope cmd builder."""

from __future__ import annotations

import shlex

from game_setup_hub.gamescope import (
    GamescopeOptions,
    build_gamescope_argv,
    build_gamescope_cmd,
)


def test_argv_starts_with_gamescope_and_ends_with_separator() -> None:
    argv = build_gamescope_argv(GamescopeOptions())
    assert argv[0] == "gamescope"
    assert argv[-1] == "--"


def test_resolution_args_emitted() -> None:
    opts = GamescopeOptions(output_width=1920, output_height=1080, game_width=1280, game_height=720)
    argv = build_gamescope_argv(opts)
    assert "-w" in argv and "1920" in argv
    assert "-h" in argv and "1080" in argv
    assert "-W" in argv and "1280" in argv
    assert "-H" in argv and "720" in argv


def test_extra_args_are_shell_split() -> None:
    opts = GamescopeOptions(extra_args='--prefer-vk-device "1234:5678"')
    argv = build_gamescope_argv(opts)
    assert "--prefer-vk-device" in argv
    assert "1234:5678" in argv


def test_cmd_string_is_quoted() -> None:
    opts = GamescopeOptions(extra_args="--mango 'hello world'")
    cmd = build_gamescope_cmd(opts)
    parts = shlex.split(cmd)
    assert parts[0] == "gamescope"
    assert "hello world" in parts


def test_fsr_sharpness_clamped() -> None:
    opts = GamescopeOptions(fsr=True, fsr_sharpness=999)
    argv = build_gamescope_argv(opts)
    sharpness_idx = argv.index("--fsr-sharpness")
    assert argv[sharpness_idx + 1] == "20"
