"""Gamescope cmd builder."""

from __future__ import annotations

import shlex

from game_setup_hub.gamescope import (
    GamescopeOptions,
    build_gamescope_argv,
    build_gamescope_cmd,
    build_scopebuddy_wrap_cmd,
)


def test_argv_starts_with_gamescope_and_ends_with_separator() -> None:
    argv = build_gamescope_argv(GamescopeOptions())
    assert argv[0] == "gamescope"
    assert argv[-1] == "--"


def test_resolution_args_emitted() -> None:
    opts = GamescopeOptions(output_width=1920, output_height=1080, game_width=1280, game_height=720)
    argv = build_gamescope_argv(opts)
    # Output (display) resolution maps to -W/-H; game (render) res maps to -w/-h.
    assert argv[argv.index("-W") + 1] == "1920"
    assert argv[argv.index("-H") + 1] == "1080"
    assert argv[argv.index("-w") + 1] == "1280"
    assert argv[argv.index("-h") + 1] == "720"


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


def test_scopebuddy_wrap_cmd_env_order() -> None:
    opts = GamescopeOptions(
        wrap_with_scopebuddy=True,
        scb_auto_res=True,
        scb_auto_hdr=True,
        scb_noscope=True,
    )
    cmd = build_scopebuddy_wrap_cmd(opts)
    assert "SCB_AUTO_RES=1" in cmd
    assert "SCB_AUTO_HDR=1" in cmd
    assert "SCB_NOSCOPE=1" in cmd
    assert cmd.endswith(" scb --") or cmd.endswith(" scopebuddy --")
    parts = shlex.split(cmd)
    assert parts[-1] == "--"
    assert parts[-2] in ("scb", "scopebuddy")


def test_wrap_mode_argv_is_tokenized() -> None:
    opts = GamescopeOptions(wrap_with_scopebuddy=True, scb_auto_vrr=True)
    argv = build_gamescope_argv(opts)
    assert "SCB_AUTO_VRR=1" in argv
    assert argv[-1] == "--"
