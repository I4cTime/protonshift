"""Tests for merging snippets into a Steam launch-options line."""

from __future__ import annotations

import pytest

from protonshift.core.launch_merge import merge_launch_snippet as merge


@pytest.mark.parametrize(
    ("text", "snippet", "expected"),
    [
        # an empty line gains %command%, or the snippet would become a game argument
        ("", "gamemoderun", "gamemoderun %command%"),
        ("", "MANGOHUD=1", "MANGOHUD=1 %command%"),
        ("", "gamescope -f -b --", "gamescope -f -b -- %command%"),
        ("", "gamescope -f -- %command%", "gamescope -f -- %command%"),
        # existing game arguments (no %command%) stay arguments
        ("-novid -fullscreen", "gamemoderun", "gamemoderun %command% -novid -fullscreen"),
        # env goes first, commands go right before %command%
        ("gamemoderun %command%", "MANGOHUD=1", "MANGOHUD=1 gamemoderun %command%"),
        ("MANGOHUD=1 %command%", "gamemoderun", "MANGOHUD=1 gamemoderun %command%"),
        # a wrapper sits after env and before other commands
        ("MANGOHUD=1 gamemoderun %command% -novid", "gamescope -f --",
         "MANGOHUD=1 gamescope -f -- gamemoderun %command% -novid"),
        # a new wrapper replaces the old one instead of nesting
        ("gamescope -W 1920 -H 1080 -f -- %command%", "gamescope -f -b --", "gamescope -f -b -- %command%"),
        ("SCB_AUTO_RES=1 scb -- %command%", "gamescope -f --", "gamescope -f -- %command%"),
        ("PROTON_LOG=1 gamescope -f -- gamemoderun %command%", "SCB_AUTO_RES=1 SCB_AUTO_HDR=1 scb --",
         "PROTON_LOG=1 SCB_AUTO_RES=1 SCB_AUTO_HDR=1 scb -- gamemoderun %command%"),
        # a snippet that carries its own %command% never duplicates it
        ("gamemoderun %command%", "PROTON_LARGE_ADDRESS_AWARE=1 %command%",
         "PROTON_LARGE_ADDRESS_AWARE=1 gamemoderun %command%"),
        ("%command%", "%command% -dx11", "%command% -dx11"),
        # quoted values survive
        ('FOO="a b" %command%', "gamemoderun", 'FOO="a b" gamemoderun %command%'),
    ],
)
def test_merge(text: str, snippet: str, expected: str) -> None:
    assert merge(text, snippet) == expected


@pytest.mark.parametrize(
    ("text", "snippet"),
    [
        ("gamemoderun %command%", "gamemoderun"),
        ("MANGOHUD=1 gamemoderun %command% -novid", "MANGOHUD=1"),
        ("gamescope -f -b -- %command%", "gamescope -f -b --"),
        ("%command% -dx11", "%command% -dx11"),
        ("anything", ""),
        ("anything", "   "),
    ],
)
def test_merge_is_idempotent(text: str, snippet: str) -> None:
    assert merge(text, snippet) == text


def test_merge_twice_equals_once() -> None:
    once = merge("-novid", "gamescope -f --")
    assert merge(once, "gamescope -f --") == once
    assert once.count("%command%") == 1
