"""Tests for merging snippets into a Steam launch-options line, and the edit helpers."""

from __future__ import annotations

import pytest

from protonshift.core.launch_merge import (
    add_command,
    add_game_arg,
    env_word,
    prefix_commands,
    prefix_env,
    remove_word,
    set_env,
    single_command,
    split_line,
    split_words,
    unset_env,
)
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
        # a quoted assignment stays one word and stays in front of a new wrapper
        ("KEY='a b;c' gamemoderun %command%", "gamescope -f --",
         "KEY='a b;c' gamescope -f -- gamemoderun %command%"),
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


# --- edit helpers ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("KEY='a b' %command%", ["KEY='a b'", "%command%"]),
        ("KEY='a b;c' gamemoderun %command%", ["KEY='a b;c'", "gamemoderun", "%command%"]),
        ('FOO="a b" gamemoderun %command%', ['FOO="a b"', "gamemoderun", "%command%"]),
        ('A="x \\" y" %command%', ['A="x \\" y"', "%command%"]),
        ("A=a\\ b %command%", ["A=a\\ b", "%command%"]),
        ("  gamemoderun   %command%  -novid ", ["gamemoderun", "%command%", "-novid"]),
        # unbalanced quote: plain whitespace split, nothing lost
        ("FOO='a b %command%", ["FOO='a", "b", "%command%"]),
        ("", []),
    ],
)
def test_split_words(text: str, expected: list[str]) -> None:
    assert split_words(text) == expected


def test_split_line_reads_a_line_without_command_as_arguments() -> None:
    assert split_line("gamemoderun -novid") == ([], ["gamemoderun", "-novid"], 0)
    assert split_line("A=1 %command% -x %command% -y") == (["A=1"], ["-x", "-y"], 2)


@pytest.mark.parametrize(
    ("text", "key", "value", "expected"),
    [
        ("", "PROTON_LOG", "1", "PROTON_LOG=1 %command%"),
        ("gamemoderun %command%", "PROTON_LOG", "1", "PROTON_LOG=1 gamemoderun %command%"),
        # replaced where it stands
        ("A=1 PROTON_LOG=0 gamemoderun %command% -novid", "PROTON_LOG", "1",
         "A=1 PROTON_LOG=1 gamemoderun %command% -novid"),
        # a later duplicate would win in the shell, so it goes
        ("X=1 gamemoderun X=2 %command%", "X", "3", "X=3 gamemoderun %command%"),
        # a quoted value is one word and is replaced whole
        ("DXVK_HUD='fps, gpuload' %command%", "DXVK_HUD", "fps", "DXVK_HUD=fps %command%"),
        # no %command%: the words stay game arguments
        ("-novid -fullscreen", "A", "1", "A=1 %command% -novid -fullscreen"),
        ("gamemoderun", "A", "1", "A=1 %command% gamemoderun"),
        # already set: the line comes back exactly as given
        ("A=1  %command%", "A", "1", "A=1  %command%"),
        # gamescope's options are not touched
        ("gamescope -f -- %command%", "A", "1", "A=1 gamescope -f -- %command%"),
        # a value outside the pack's characters (a user's own) is single-quoted ...
        ("gamemoderun %command%", "WINEDLLOVERRIDES", "d3d9=n;dinput8=n,b",
         "WINEDLLOVERRIDES='d3d9=n;dinput8=n,b' gamemoderun %command%"),
        ("%command%", "A", "a b", "A='a b' %command%"),
        # ... and replaces an existing quoted assignment of the key as one word
        ("A='x y' B=1 %command%", "A", "a b;c", "A='a b;c' B=1 %command%"),
        ('A="x y" %command%', "A", "1", "A=1 %command%"),
    ],
)
def test_set_env(text: str, key: str, value: str, expected: str) -> None:
    assert set_env(text, key, value) == expected
    assert set_env(expected, key, value) == expected


@pytest.mark.parametrize("value", ["it's", "a\nb", "a\rb", "a\x00b", "%command%", "x%command%y"])
def test_env_word_refuses_what_quoting_cannot_make_safe(value: str) -> None:
    with pytest.raises(ValueError):
        env_word("A", value)
    with pytest.raises(ValueError):
        set_env("%command%", "A", value)


def test_env_word_quotes_only_when_needed() -> None:
    assert env_word("A", "fps,frametime") == "A=fps,frametime"
    assert env_word("A", "") == "A="
    assert env_word("A", "a b") == "A='a b'"
    assert env_word("A", "$HOME") == "A='$HOME'"


def test_a_quoted_assignment_is_one_assignment_everywhere() -> None:
    line = "KEY='a b;c gamemoderun' mangohud %command%"
    prefix = split_line(line)[0]
    assert prefix_env(prefix) == ["KEY='a b;c gamemoderun'"]
    assert prefix_commands(prefix) == ["mangohud"]
    assert unset_env(line, "KEY") == "mangohud %command%"
    # gamemoderun inside the value is not a command to remove
    assert remove_word(line, "gamemoderun") == line


def test_set_env_refuses_a_bad_key() -> None:
    with pytest.raises(ValueError):
        set_env("%command%", "A B", "1")
    with pytest.raises(ValueError):
        unset_env("%command%", "")


@pytest.mark.parametrize(
    ("text", "key", "expected"),
    [
        ("MANGOHUD=1 %command%", "MANGOHUD", ""),
        ("MANGOHUD=1 gamemoderun %command% -novid", "MANGOHUD", "gamemoderun %command% -novid"),
        ("A=1 MANGOHUD=1 MANGOHUD=0 %command%", "MANGOHUD", "A=1 %command%"),
        ("FOO='a b' MANGOHUD=1 %command%", "MANGOHUD", "FOO='a b' %command%"),
        # nothing to remove
        ("A=1 %command%", "MANGOHUD", "A=1 %command%"),
        # after %command% it is a game argument, never an assignment
        ("%command% MANGOHUD=1", "MANGOHUD", "%command% MANGOHUD=1"),
        # no %command%: nothing is before the game
        ("MANGOHUD=1", "MANGOHUD", "MANGOHUD=1"),
        # MY_MANGOHUD is another variable
        ("MY_MANGOHUD=1 %command%", "MANGOHUD", "MY_MANGOHUD=1 %command%"),
    ],
)
def test_unset_env(text: str, key: str, expected: str) -> None:
    assert unset_env(text, key) == expected
    assert unset_env(expected, key) == expected


@pytest.mark.parametrize(
    ("text", "word", "expected"),
    [
        ("gamemoderun %command%", "gamemoderun", ""),
        ("MANGOHUD=1 gamemoderun mangohud %command% -novid", "gamemoderun",
         "MANGOHUD=1 mangohud %command% -novid"),
        ("/usr/bin/gamemoderun %command%", "gamemoderun", ""),
        # a wrapper goes with its options and its --
        ("gamescope -W 1920 -H 1080 -f -- gamemoderun %command%", "gamescope", "gamemoderun %command%"),
        ("SCB_AUTO_RES=1 scb -- %command% -dx11", "scb", "SCB_AUTO_RES=1 %command% -dx11"),
        # without -- nobody can tell where its options end, so they all go
        ("A=1 gamescope -f -W 1920 gamemoderun B=2 %command%", "gamescope", "A=1 B=2 %command%"),
        # option-like words right after a plain command are its own
        ("mangohud --dlsym gamemoderun %command%", "mangohud", "gamemoderun %command%"),
        ("strangle 60 %command%", "strangle", ""),
        # a word inside gamescope's options is not a command
        ("gamescope -o gamemoderun -- %command%", "gamemoderun", "gamescope -o gamemoderun -- %command%"),
        # but one after its -- is
        ("gamescope -f -- gamemoderun %command%", "gamemoderun", "gamescope -f -- %command%"),
        # never an assignment, never a game argument
        ("gamemoderun=1 %command% gamemoderun", "gamemoderun", "gamemoderun=1 %command% gamemoderun"),
        # no %command%: nothing to remove
        ("gamemoderun", "gamemoderun", "gamemoderun"),
        ("prime-run %command%", "gamemoderun", "prime-run %command%"),
    ],
)
def test_remove_word(text: str, word: str, expected: str) -> None:
    assert remove_word(text, word) == expected
    assert remove_word(expected, word) == expected


@pytest.mark.parametrize(
    ("text", "arg", "expected"),
    [
        ("", "-vulkan", "%command% -vulkan"),
        ("gamemoderun %command%", "-vulkan", "gamemoderun %command% -vulkan"),
        ("%command% -novid", "-vulkan", "%command% -novid -vulkan"),
        ("%command% -vulkan", "-vulkan", "%command% -vulkan"),
        # no %command%: the line was game arguments and still is
        ("-novid", "-vulkan", "%command% -novid -vulkan"),
        ("-vulkan", "-vulkan", "-vulkan"),
        # in front of the game is not the game's argument
        ("gamescope -vulkan -- %command%", "-vulkan", "gamescope -vulkan -- %command% -vulkan"),
    ],
)
def test_add_game_arg(text: str, arg: str, expected: str) -> None:
    assert add_game_arg(text, arg) == expected
    assert add_game_arg(expected, arg) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("gamemoderun %command% %command%", "gamemoderun %command%"),
        ("%command% -a %command% -b", "%command% -a -b"),
        ("%command% %command%", ""),
        ("gamemoderun %command%", "gamemoderun %command%"),
        ("-novid", "-novid"),
    ],
)
def test_single_command(text: str, expected: str) -> None:
    assert single_command(text) == expected
    assert single_command(expected) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("gamemoderun", "gamemoderun %command%"),
        ("PROTON_LOG=1", "PROTON_LOG=1 %command%"),
        ("PROTON_LOG=1 gamemoderun -novid", "PROTON_LOG=1 gamemoderun %command% -novid"),
        ("PROTON_LOG=1 gamemoderun +connect", "PROTON_LOG=1 gamemoderun %command% +connect"),
        ("FOO='a b' mangohud", "FOO='a b' mangohud %command%"),
        ("gamescope -f -b -- -novid", "gamescope -f -b -- %command% -novid"),
        ("/usr/bin/gamemoderun -novid", "/usr/bin/gamemoderun %command% -novid"),
        # a command keeps its own option-like words, as remove_word reads them
        ("strangle 60", "strangle 60 %command%"),
        ("mangohud --dlsym", "mangohud --dlsym %command%"),
        ("strangle 60 +fps_max=0", "strangle 60 %command% +fps_max=0"),
        # a command that takes no options runs the next word, so the game goes right after it
        ("gamemoderun -novid", "gamemoderun %command% -novid"),
        ("prime-run -novid 60", "prime-run %command% -novid 60"),
        ("obs-gamecapture --x", "obs-gamecapture %command% --x"),
        ("gamemoderun strangle 60 -novid", "gamemoderun strangle 60 %command% -novid"),
        ("/usr/bin/mangohud --dlsym -novid", "/usr/bin/mangohud --dlsym %command% -novid"),
        ("strangle -k 60:30 -dx11", "strangle -k 60:30 %command% -dx11"),
        # a wrapper without -- owns every word after it
        ("gamescope -W 1920 -H 1080 -f", "gamescope -W 1920 -H 1080 -f -- %command%"),
        ("gamescope", "gamescope -- %command%"),
        ("SCB_AUTO_RES=1 scb", "SCB_AUTO_RES=1 scb -- %command%"),
        # with a --, the game goes right after it and the rest stays the game's
        ("gamescope -W 1920 -- -novid +x", "gamescope -W 1920 -- %command% -novid +x"),
        # env assignments first, then two commands
        ("A=1 B=2 strangle 60 mangohud --dlsym +connect",
         "A=1 B=2 strangle 60 mangohud --dlsym %command% +connect"),
        ("PROTON_LOG=1 gamemoderun gamescope -f", "PROTON_LOG=1 gamemoderun gamescope -f -- %command%"),
        ("gamescope -f -- gamemoderun +x", "gamescope -f -- gamemoderun %command% +x"),
        # a quoted argument stays one word, for the game or the wrapper
        ("FOO='a b' strangle 60 'my arg'", "FOO='a b' strangle 60 %command% 'my arg'"),
        ("gamescope --cursor 'a b.png'", "gamescope --cursor 'a b.png' -- %command%"),
        # nothing at the start that belongs before the game
        ("-novid gamemoderun", "-novid gamemoderun"),
        # already there
        ("gamemoderun %command%", "gamemoderun %command%"),
        ("", ""),
    ],
)
def test_add_command(text: str, expected: str) -> None:
    assert add_command(text) == expected
    assert add_command(expected) == expected


def test_unbalanced_quote_keeps_every_word() -> None:
    text = "FOO='a b gamemoderun %command% -novid"
    assert remove_word(text, "gamemoderun") == "FOO='a b %command% -novid"
    assert set_env(text, "A", "1") == "A=1 FOO='a b gamemoderun %command% -novid"
