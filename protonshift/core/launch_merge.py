"""Merge a snippet into a Steam launch-options line without breaking it.

Steam launch options are one shell-ish line. Anything before ``%command%`` is
a prefix (environment assignments, wrapper commands such as ``gamemoderun`` or
``gamescope ... --``); anything after it is passed to the game as arguments.
A line WITHOUT ``%command%`` is all arguments, so naively appending
``gamemoderun`` to an empty line hands the game a stray argument instead of
wrapping it. :func:`merge_launch_snippet` places each kind of snippet where it
belongs and always leaves exactly one ``%command%``.

Pure Python - exercised in tests/test_launch_merge.py.
"""

from __future__ import annotations

import re
import shlex

COMMAND = "%command%"

_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Programs that take over the launch and end their own arguments with ``--``.
_WRAPPERS = ("gamescope", "scb", "scopebuddy")


def _tokens(text: str) -> list[str]:
    """Split on whitespace, keeping quoted segments (and their quotes) intact."""
    try:
        return shlex.split(text, posix=False)
    except ValueError:  # unbalanced quote: fall back rather than lose the text
        return text.split()


def _split_command(tokens: list[str]) -> tuple[list[str], list[str], bool]:
    """``(before, after, had_command)`` around the first ``%command%``."""
    if COMMAND in tokens:
        i = tokens.index(COMMAND)
        return tokens[:i], [t for t in tokens[i + 1:] if t != COMMAND], True
    return [], tokens, False


def _is_wrapper(tokens: list[str]) -> bool:
    """True for ``[ENV=.. ...] gamescope|scb ... --``."""
    words = [t for t in tokens if not _ENV_RE.match(t)]
    return bool(words) and words[0].rsplit("/", 1)[-1] in _WRAPPERS and tokens[-1] == "--"


def _strip_wrapper(prefix: list[str]) -> list[str]:
    """Remove an existing gamescope/ScopeBuddy wrapper (and its SCB_ env) from a prefix."""
    start = next((i for i, t in enumerate(prefix) if t.rsplit("/", 1)[-1] in _WRAPPERS), None)
    if start is None:
        return prefix
    end = next((i for i in range(start, len(prefix)) if prefix[i] == "--"), None)
    if end is None:
        return prefix
    head = [t for t in prefix[:start] if not t.startswith("SCB_")]
    return head + prefix[end + 1:]


def merge_launch_snippet(text: str, snippet: str) -> str:
    """Return ``text`` with ``snippet`` merged in.

    - Environment assignments (``KEY=value``) go to the front of the prefix.
    - A wrapper (``gamescope ... --``, ``SCB_..=1 scb --``) replaces any
      wrapper already there and sits after the environment assignments.
    - Other prefix commands (``gamemoderun``) go right before ``%command%``.
    - Whatever the snippet has after its own ``%command%`` is appended to the
      game's arguments.

    Tokens already present are not added twice, so merging the same snippet
    again returns the line unchanged.
    """
    add_before, add_after, snippet_had_command = _split_command(_tokens(snippet.strip()))
    if not snippet_had_command:
        # No %command% in the snippet: the whole thing is a prefix.
        add_before, add_after = add_after, []
    if not add_before and not add_after:
        return text

    before, after, _ = _split_command(_tokens(text.strip()))

    if _is_wrapper(add_before):
        before = _strip_wrapper(before)
        env = [t for t in before if _ENV_RE.match(t)]
        rest = [t for t in before if not _ENV_RE.match(t)]
        before = env + add_before + rest
    else:
        new_env = [t for t in add_before if _ENV_RE.match(t) and t not in before]
        new_cmd = [t for t in add_before if not _ENV_RE.match(t) and t not in before]
        # keep an existing wrapper's own env + words together: env goes first,
        # plain commands go last (right before %command%, inside any wrapper)
        before = new_env + before + new_cmd

    after = after + [t for t in add_after if t not in after]
    return " ".join([*before, COMMAND, *after])
