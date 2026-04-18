"""Gamescope launch command builder."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from game_setup_hub.tool_check import is_tool_available


@dataclass
class GamescopeOptions:
    output_width: int = 0
    output_height: int = 0
    game_width: int = 0
    game_height: int = 0
    fps_limit: int = 0
    fsr: bool = False
    fsr_sharpness: int = 5
    integer_scale: bool = False
    hdr: bool = False
    nested: bool = True
    borderless: bool = True
    fullscreen: bool = True
    extra_args: str = ""


def is_gamescope_available() -> bool:
    """Check if gamescope is installed."""
    return is_tool_available("gamescope")


def build_gamescope_argv(opts: GamescopeOptions) -> list[str]:
    """Build a gamescope argv list from options.

    `extra_args` is parsed via :func:`shlex.split` so quoted segments and
    escapes are preserved correctly. The trailing ``--`` separator is always
    appended so the caller can append the wrapped command directly.
    """
    parts: list[str] = ["gamescope"]

    if opts.output_width > 0 and opts.output_height > 0:
        parts.extend(["-w", str(opts.output_width), "-h", str(opts.output_height)])

    if opts.game_width > 0 and opts.game_height > 0:
        parts.extend(["-W", str(opts.game_width), "-H", str(opts.game_height)])

    if opts.fps_limit > 0:
        parts.extend(["-r", str(opts.fps_limit)])

    if opts.fsr:
        parts.extend(["--fsr-sharpness", str(max(0, min(20, opts.fsr_sharpness)))])

    if opts.integer_scale:
        parts.append("--integer-scale")

    if opts.hdr:
        parts.append("--hdr-enabled")

    if opts.fullscreen:
        parts.append("-f")

    if opts.borderless:
        parts.append("-b")

    if opts.extra_args.strip():
        try:
            parts.extend(shlex.split(opts.extra_args))
        except ValueError:
            # unbalanced quotes — fall back to whitespace split so the user
            # at least sees something instead of silent loss
            parts.extend(opts.extra_args.split())

    parts.append("--")
    return parts


def build_gamescope_cmd(opts: GamescopeOptions) -> str:
    """Build a shell-safe gamescope command string from options.

    Returned value is suitable for copy/paste into a launch options field.
    Use :func:`build_gamescope_argv` when actually exec-ing the command.
    """
    return shlex.join(build_gamescope_argv(opts))
