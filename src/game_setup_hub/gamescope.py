"""Gamescope launch command builder."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field


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
    return shutil.which("gamescope") is not None


def build_gamescope_cmd(opts: GamescopeOptions) -> str:
    """Build a gamescope command string from options."""
    parts = ["gamescope"]

    if opts.output_width > 0 and opts.output_height > 0:
        parts.extend(["-w", str(opts.output_width), "-h", str(opts.output_height)])

    if opts.game_width > 0 and opts.game_height > 0:
        parts.extend(["-W", str(opts.game_width), "-H", str(opts.game_height)])

    if opts.fps_limit > 0:
        parts.extend(["-r", str(opts.fps_limit)])

    if opts.fsr:
        parts.append("--fsr-sharpness")
        parts.append(str(max(0, min(20, opts.fsr_sharpness))))

    if opts.integer_scale:
        parts.append("--integer-scale")

    if opts.hdr:
        parts.append("--hdr-enabled")

    if opts.fullscreen:
        parts.append("-f")

    if opts.borderless:
        parts.append("-b")

    if opts.extra_args:
        parts.append(opts.extra_args.strip())

    parts.append("--")

    return " ".join(parts)
