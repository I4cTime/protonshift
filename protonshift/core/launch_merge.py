"""Merge a snippet into a Steam launch-options line without breaking it.

Steam launch options are one shell-ish line. Anything before ``%command%`` is
a prefix (environment assignments, wrapper commands such as ``gamemoderun`` or
``gamescope ... --``); anything after it is passed to the game as arguments.
A line WITHOUT ``%command%`` is all arguments, so naively appending
``gamemoderun`` to an empty line hands the game a stray argument instead of
wrapping it. :func:`merge_launch_snippet` places each kind of snippet where it
belongs and always leaves exactly one ``%command%``.

The edit helpers below (:func:`set_env`, :func:`unset_env`, :func:`remove_word`,
:func:`add_game_arg`, :func:`single_command`, :func:`add_command`) are what a
Diagnose fix applies. They share these rules:

- A helper with nothing to do returns the line exactly as it was given, so a
  fix that changes nothing is seen as no change at all.
- Otherwise the result has exactly one ``%command%``, or is the empty string
  when nothing is left before or after it (never a bare ``%command%``).
- A line without ``%command%`` is read the way Steam reads it: every word is a
  game argument and nothing comes before the game. So :func:`unset_env`,
  :func:`remove_word` and :func:`single_command` find nothing to do on it,
  :func:`set_env` and :func:`add_game_arg` add ``%command%`` in front of the
  existing words (which stay game arguments), and :func:`add_command` is the
  one helper that moves words in front of the game.
- Words are split by :func:`split_words`, which keeps ``KEY='a b'`` together
  as one word. A line with an unbalanced quote falls back to plain whitespace
  splitting, as ``_tokens`` does, so no text is lost.
- Applying a helper twice gives the same line as applying it once.

Pure Python - exercised in tests/test_launch_merge.py.
"""

from __future__ import annotations

import re
import shlex

COMMAND = "%command%"

_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Programs that take over the launch and end their own arguments with ``--``.
_WRAPPERS = ("gamescope", "scb", "scopebuddy")
# What a word right after a removed command looks like when it is that
# command's own option or number (``mangohud --dlsym``, ``strangle 60``).
_OPTION_RE = re.compile(r"-\S*|[0-9][0-9.:]*")

# Wrapper commands people put in launch options -> the name to show.
KNOWN_COMMANDS: dict[str, str] = {
    "gamemoderun": "GameMode",
    "mangohud": "MangoHud",
    "gamescope": "gamescope",
    "scb": "ScopeBuddy",
    "scopebuddy": "ScopeBuddy",
    "obs-gamecapture": "OBS game capture",
    "prime-run": "prime-run",
    "strangle": "libstrangle",
}


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


# --------------------------------------------------------------------------- #
# edit helpers
# --------------------------------------------------------------------------- #

def split_words(text: str) -> list[str]:
    """Split on whitespace like a shell would, keeping quotes and escapes inside their word.

    Unlike ``_tokens`` (``shlex`` in non-POSIX mode), a quote in the middle of
    a word does not end it, so ``KEY='a b'`` is one word. With an unbalanced
    quote the line is split on whitespace alone rather than losing text.
    """
    words: list[str] = []
    current: list[str] = []
    in_word = False
    quote = ""
    escaped = False
    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if quote:
            current.append(ch)
            if ch == quote:
                quote = ""
            elif ch == "\\" and quote == '"':
                escaped = True
            continue
        if ch.isspace():
            if in_word:
                words.append("".join(current))
                current = []
                in_word = False
            continue
        current.append(ch)
        in_word = True
        if ch in "'\"":
            quote = ch
        elif ch == "\\":
            escaped = True
    if quote:
        return text.split()
    if in_word:
        words.append("".join(current))
    return words


def split_line(text: str) -> tuple[list[str], list[str], int]:
    """``(prefix, game_args, command_count)`` of a launch-options line.

    The prefix is what comes before the first ``%command%``; with no
    ``%command%`` it is empty and every word is a game argument, which is how
    Steam reads such a line. Later ``%command%`` words are left out of both.
    """
    words = split_words(text.strip())
    before, after, _ = _split_command(words)
    return before, after, words.count(COMMAND)


def _join(before: list[str], after: list[str]) -> str:
    if not before and not after:
        return ""
    return " ".join([*before, COMMAND, *after])


def _basename(word: str) -> str:
    return word.rsplit("/", 1)[-1]


def _is_env(word: str) -> bool:
    return _ENV_RE.match(word) is not None


def _env_key(word: str) -> str:
    return word.split("=", 1)[0]


def _dashdash(prefix: list[str], start: int) -> int | None:
    return next((i for i in range(start + 1, len(prefix)) if prefix[i] == "--"), None)


def prefix_env(prefix: list[str]) -> list[str]:
    """The environment assignments (``KEY=value``) in a prefix, in order."""
    return [w for w in prefix if _is_env(w)]


def prefix_commands(prefix: list[str]) -> list[str]:
    """The command words in a prefix: not assignments, not a wrapper's own options before its ``--``."""
    out: list[str] = []
    i = 0
    while i < len(prefix):
        word = prefix[i]
        if _is_env(word):
            i += 1
            continue
        out.append(word)
        end = _dashdash(prefix, i) if _basename(word) in _WRAPPERS else None
        i = end + 1 if end is not None else i + 1
    return out


def _check_key(key: str) -> None:
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        raise ValueError(f"not a valid variable name: {key!r}")


def set_env(text: str, key: str, value: str) -> str:
    """Set ``KEY=value`` before ``%command%``.

    An existing assignment of the same key is replaced where it stands (a later
    duplicate is dropped, since the shell would let it win); otherwise the
    assignment goes to the front of the prefix.
    """
    _check_key(key)
    before, after, count = split_line(text)
    new = f"{key}={value}"
    out: list[str] = []
    placed = False
    for word in before:
        if _is_env(word) and _env_key(word) == key:
            if not placed:
                out.append(new)
                placed = True
            continue
        out.append(word)
    if not placed:
        out.insert(0, new)
    if count and out == before:
        return text
    return _join(out, after)


def unset_env(text: str, key: str) -> str:
    """Remove every assignment of ``KEY`` from before ``%command%``."""
    _check_key(key)
    before, after, count = split_line(text)
    out = [w for w in before if not (_is_env(w) and _env_key(w) == key)]
    if not count or out == before:
        return text
    return _join(out, after)


def remove_word(text: str, word: str) -> str:
    """Remove the command ``word`` (compared by basename) from before ``%command%``.

    A wrapper that carries its own options up to ``--`` (gamescope, scb,
    scopebuddy) goes together with those options and the ``--``. Without a
    ``--`` there is no telling where its options end, so every word after it
    up to ``%command%`` goes too: a leftover option would otherwise become the
    command Steam runs. Any other command takes the option-like words right
    after it (``mangohud --dlsym``, ``strangle 60``) with it, for the same
    reason. Environment assignments and game arguments are never removed.
    """
    before, after, count = split_line(text)
    if not count:
        return text
    out: list[str] = []
    changed = False
    i = 0
    while i < len(before):
        current = before[i]
        if _is_env(current):
            out.append(current)
            i += 1
            continue
        name = _basename(current)
        if name in _WRAPPERS:
            end = _dashdash(before, i)
            if name == word:
                changed = True
                if end is None:
                    out.extend(w for w in before[i + 1:] if _is_env(w))
                    break
                i = end + 1
                continue
            stop = end + 1 if end is not None else i + 1
            out.extend(before[i:stop])
            i = stop
            continue
        if name == word:
            changed = True
            i += 1
            while i < len(before) and _OPTION_RE.fullmatch(before[i]):
                i += 1
            continue
        out.append(current)
        i += 1
    if not changed:
        return text
    return _join(out, after)


def add_game_arg(text: str, arg: str) -> str:
    """Add ``arg`` after ``%command%`` unless the game already gets it."""
    before, after, _count = split_line(text)
    if arg in after:
        return text
    return _join(before, [*after, arg])


def single_command(text: str) -> str:
    """Keep the first ``%command%`` and drop the others."""
    before, after, count = split_line(text)
    if count <= 1:
        return text
    return _join(before, after)


def add_command(text: str) -> str:
    """Insert ``%command%`` after the leading assignments and known wrapper commands.

    For a line with no ``%command%`` such as ``PROTON_LOG=1 gamemoderun -novid``:
    the leading run (``PROTON_LOG=1 gamemoderun``) becomes the prefix and the
    rest stays game arguments. A wrapper in the run keeps its options up to its
    ``--``. A line that already has ``%command%``, or that does not start with
    such words, is returned as it was.
    """
    words = split_words(text.strip())
    if COMMAND in words:
        return text
    i = 0
    while i < len(words):
        word = words[i]
        if _is_env(word):
            i += 1
            continue
        name = _basename(word)
        if name not in KNOWN_COMMANDS:
            break
        end = _dashdash(words, i) if name in _WRAPPERS else None
        i = end + 1 if end is not None else i + 1
    if i == 0:
        return text
    return _join(words[:i], words[i:])
