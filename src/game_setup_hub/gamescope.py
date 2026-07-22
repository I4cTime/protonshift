"""Gamescope launch command builder."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from game_setup_hub.tool_check import find_scopebuddy, is_tool_available


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
    wrap_with_scopebuddy: bool = False
    scb_auto_res: bool = False
    scb_auto_hdr: bool = False
    scb_auto_vrr: bool = False
    scb_auto_refresh: bool = False
    scb_auto_frame_limit: bool = False
    scb_noscope: bool = False


def is_gamescope_available() -> bool:
    """Check if gamescope is installed."""
    return is_tool_available("gamescope")


def build_scopebuddy_wrap_cmd(opts: GamescopeOptions) -> str:
    """Shell prefix: ``SCB_AUTO_*=1 … scb --`` for Steam-style launch options."""
    bits: list[str] = []
    if opts.scb_auto_res:
        bits.append("SCB_AUTO_RES=1")
    if opts.scb_auto_hdr:
        bits.append("SCB_AUTO_HDR=1")
    if opts.scb_auto_vrr:
        bits.append("SCB_AUTO_VRR=1")
    if opts.scb_auto_refresh:
        bits.append("SCB_AUTO_REFRESH=1")
    if opts.scb_auto_frame_limit:
        bits.append("SCB_AUTO_FRAME_LIMIT=1")
    if opts.scb_noscope:
        bits.append("SCB_NOSCOPE=1")
    found = find_scopebuddy()
    invoke = found[0] if found else "scb"
    bits.append(invoke)
    bits.append("--")
    return " ".join(bits)


def build_gamescope_argv(opts: GamescopeOptions) -> list[str]:
    """Build a gamescope argv list from options.

    When ``wrap_with_scopebuddy`` is true, returns a token list suitable for
    display only (prepend env assignments are not a single POSIX argv).

    `extra_args` is parsed via :func:`shlex.split` so quoted segments and
    escapes are preserved correctly. The trailing ``--`` separator is always
    appended so the caller can append the wrapped command directly.
    """
    if opts.wrap_with_scopebuddy:
        try:
            return shlex.split(build_scopebuddy_wrap_cmd(opts), posix=True)
        except ValueError:
            return ["scb", "--"]

    parts: list[str] = ["gamescope"]

    # gamescope semantics: -W/-H is the OUTPUT (display/window) size,
    # -w/-h is the GAME (internal render) size. Mapping these the other way
    # round makes gamescope present a small output surface centred on a larger
    # display, which looks like pillar/letterboxing even with -f.
    if opts.output_width > 0 and opts.output_height > 0:
        parts.extend(["-W", str(opts.output_width), "-H", str(opts.output_height)])

    if opts.game_width > 0 and opts.game_height > 0:
        parts.extend(["-w", str(opts.game_width), "-h", str(opts.game_height)])

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
    """Build a shell-safe prefix for launch options.

    Either a raw ``gamescope … --`` line or ``SCB_*=1 … scb --`` when wrapping
    with ScopeBuddy. Suitable for copy/paste into Steam launch options.
    """
    if opts.wrap_with_scopebuddy:
        return build_scopebuddy_wrap_cmd(opts)
    return shlex.join(build_gamescope_argv(opts))
