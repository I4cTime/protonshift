"""Load and validate the fix pack, the rule file behind Diagnose.

``docs/fix-pack.md`` is the contract. Steam hands a game's launch options to a
shell, so a rule that could carry free text into them would run a command the
next time the game starts. Every check here keeps a pack, bundled or not, down
to the narrow shapes the contract allows: anything unknown, mistyped or out of
range is a rejection, never a default or a coercion. A bad rule is dropped and
reported; the rest of the pack still loads.

The user's own version 1 fixes (``fixes.py``) are turned into rules here too,
so Diagnose sees one list. They are the user's text on the user's machine and
are held to looser value limits, as the contract's "User fixes" section says.

Pure Python, stdlib only - exercised in tests/test_fix_pack.py and
tests/test_core_safety.py.
"""

from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import fixes as _fixes

PACK_FORMAT = "protonshift-fix-pack"
PACK_VERSION = 2
SEVERITIES = ("blocking", "likely", "advice")

_BUNDLED_PATH = Path(__file__).parent / "data" / "fix_pack.json"
_MAX_PACK_BYTES = 2 * 1024 * 1024
_MAX_ACTIONS = 6
_MAX_LOG_PATTERN = 300
_MIN_LITERAL_RUN = 8
_MAX_OPEN_REPEATS = 2
_MAX_LINE = 2000
_MAX_USER_SNIPPET = 500

# Always used with fullmatch: ``$`` would also accept a trailing newline, and
# ``\d`` accepts digits from any script.
_ID_RE = re.compile(r"[a-z0-9-]{3,64}")
_REVISION_RE = re.compile(r"[0-9]{4}\.(0[1-9]|1[0-2])\.[0-9]+")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_APP_ID_RE = re.compile(r"[0-9]+")
_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ENV_VALUE_RE = re.compile(r"[A-Za-z0-9_.,:=/+@%-]{0,200}")
_GAME_ARG_RE = re.compile(r"[-+][A-Za-z0-9_.=:-]{1,60}")
_WORD_RE = re.compile(r"[A-Za-z0-9_.-]{1,40}")

# These decide what code a process loads or runs.
_FORBIDDEN_VARS = frozenset({
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "PATH",
    "PYTHONPATH",
    "STEAM_COMPAT_LAUNCHER_SERVICE",
    "WINEDLLPATH",
})
_FORBIDDEN_PREFIX = "STEAM_COMPAT_"
# ``user_rules`` hands out ``user-<n>``; a pack rule with that id could be
# mistaken for (or shadow) one of the user's own.
_USER_ID_PREFIX = "user-"

_PACK_KEYS = frozenset({"format", "version", "revision", "rules"})
_RULE_KEYS = ("id", "title", "cause", "severity", "match", "actions", "source", "verified")
_MATCH_KEYS = frozenset({"app_ids", "log", "log_also", "when"})
_WHEN_CHOICES = {
    "gpu_vendor": ("nvidia", "amd", "intel"),
    "session": ("wayland", "x11"),
    "proton_family": ("valve", "ge", "cachyos", "other"),
}
_WHEN_INTS = ("proton_major_min", "proton_major_max")
_WHEN_KEYS = frozenset({*_WHEN_CHOICES, *_WHEN_INTS, "launch_has", "env_set", "env_unset"})
# Every field listed for a type is required; any other field is a rejection.
_ACTION_FIELDS: dict[str, tuple[str, ...]] = {
    "env": ("key", "value"),
    "unset_env": ("key",),
    "game_arg": ("value",),
    "remove_word": ("value",),
    "default_proton": (),
    "manual": ("text",),
}


class PackError(ValueError):
    """A pack or rule that does not meet the contract. The message is a short reason."""


@dataclass(frozen=True)
class Action:
    type: str  # env | unset_env | game_arg | remove_word | default_proton | manual | user_snippet
    key: str = ""
    value: str = ""
    text: str = ""


@dataclass(frozen=True)
class When:
    gpu_vendor: tuple[str, ...] = ()
    session: tuple[str, ...] = ()
    proton_family: tuple[str, ...] = ()
    proton_major_min: int | None = None
    proton_major_max: int | None = None
    launch_has: tuple[str, ...] = ()
    env_set: tuple[str, ...] = ()
    env_unset: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    cause: str
    severity: str
    app_ids: tuple[str, ...]
    log: tuple[re.Pattern[str], ...]
    log_also: tuple[re.Pattern[str], ...]
    when: When
    actions: tuple[Action, ...]
    source: str
    verified: str
    origin: str = "pack"  # "pack" or "user"


@dataclass
class Pack:
    revision: str
    rules: list[Rule]
    rejected: list[tuple[str, str]]  # (rule id, or "#<index>" when it has no usable id, reason)


# --------------------------------------------------------------------------- #
# small field checks
# --------------------------------------------------------------------------- #

def _check_keys(raw: dict[Any, Any], allowed: Iterable[str], where: str) -> None:
    allowed = frozenset(allowed)
    for key in raw:
        if key not in allowed:
            raise PackError(f"{where}: unknown field {key!r}")


def _has_control(text: str) -> bool:
    return any(unicodedata.category(ch) == "Cc" for ch in text)


def _text(value: object, where: str, max_len: int) -> str:
    if not isinstance(value, str):
        raise PackError(f"{where}: must be a string")
    if not value.strip():
        raise PackError(f"{where}: must not be empty")
    if len(value) > max_len:
        raise PackError(f"{where}: longer than {max_len} characters")
    if _has_control(value):
        raise PackError(f"{where}: contains a control character")
    return value


def _str_list(value: object, where: str) -> list[str]:
    # An empty list is refused: ``launch_has: []`` would hold vacuously and
    # let a rule pass the "not every game" check while matching every game.
    if not isinstance(value, list):
        raise PackError(f"{where}: must be a list")
    if not value:
        raise PackError(f"{where}: must not be empty")
    for item in value:
        if not isinstance(item, str):
            raise PackError(f"{where}: every entry must be a string")
    return value


def _env_key(value: object, where: str) -> str:
    if not isinstance(value, str) or not _KEY_RE.fullmatch(value):
        raise PackError(f"{where}: not a valid variable name")
    if value in _FORBIDDEN_VARS or value.startswith(_FORBIDDEN_PREFIX):
        raise PackError(f"{where}: {value} may not be changed by a rule")
    return value


def _source(value: object) -> str:
    if not isinstance(value, str):
        raise PackError("source: must be a string")
    if not value.startswith("https://"):
        raise PackError("source: must start with https://")
    if len(value) > 300:
        raise PackError("source: longer than 300 characters")
    if any(ch.isspace() for ch in value) or _has_control(value):
        raise PackError("source: must not contain whitespace")
    try:
        host = urlsplit(value).hostname
    except ValueError:
        host = None
    if not host:
        raise PackError("source: not a URL with a host")
    return value


def _verified(value: object) -> str:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise PackError("verified: must be a date as YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise PackError("verified: not a real calendar date") from None
    return value


# --------------------------------------------------------------------------- #
# log expressions
# --------------------------------------------------------------------------- #

def _regex_tree(pattern: str) -> list[tuple[Any, ...]] | None:
    """A neutral tree of ``pattern``, or None when it cannot be checked.

    The one use of ``re._parser``, the stdlib's private regex parser
    (importable on Python 3.11 and 3.12, the versions CI runs). Being private
    it can change, so its tree is translated here into a small shape the checks
    below own, and any surprise - the module missing, an opcode or layout this
    code does not know - returns None, which the caller turns into a rejection
    rather than a crash or a silent pass.

    Node kinds: ``("lit",)`` one literal character, ``("char",)`` one
    character that is not a literal, ``("zero",)`` a zero-width anchor,
    ``("alt", [seq, ...])``, ``("rep", min, seq, max)`` (max None when
    open-ended) and ``("look", seq)``.
    Groups are spliced into their parent: an unquantified group matches its
    contents exactly once (the parser already does this for ``(?:...)``).
    Back-references and conditionals are not translated, so they are refused.
    """
    try:
        from re import _constants as c
        from re import _parser

        class_items = (c.LITERAL, c.RANGE, c.CATEGORY, c.NEGATE)
        repeats = (c.MAX_REPEAT, c.MIN_REPEAT, c.POSSESSIVE_REPEAT)

        def convert(sub: Any) -> list[tuple[Any, ...]]:
            out: list[tuple[Any, ...]] = []
            for op, av in sub:
                if op == c.LITERAL:
                    out.append(("lit",))
                elif op in (c.NOT_LITERAL, c.ANY):
                    out.append(("char",))
                elif op == c.IN:
                    if any(item_op not in class_items for item_op, _ in av):
                        raise ValueError("unknown class item")
                    out.append(("char",))
                elif op == c.AT:
                    out.append(("zero",))
                elif op == c.SUBPATTERN:
                    _group, add_flags, del_flags, body = av
                    if add_flags or del_flags:
                        raise ValueError("scoped flags")
                    out.extend(convert(body))
                elif op == c.ATOMIC_GROUP:
                    out.extend(convert(av))
                elif op == c.BRANCH:
                    out.append(("alt", [convert(branch) for branch in av[1]]))
                elif op in repeats:
                    low, high, body = av
                    top = None if high == c.MAXREPEAT else int(high)
                    out.append(("rep", int(low), convert(body), top))
                elif op in (c.ASSERT, c.ASSERT_NOT):
                    out.append(("look", convert(av[1])))
                else:
                    raise ValueError("unknown opcode")
            return out

        return convert(_parser.parse(pattern))
    except Exception:  # noqa: BLE001 - any surprise from a private module means "cannot check"
        return None


def _children(node: tuple[Any, ...]) -> list[list[tuple[Any, ...]]]:
    if node[0] == "alt":
        return node[1]
    if node[0] == "rep":
        return [node[2]]
    if node[0] == "look":
        return [node[1]]
    return []


def _contains_repeat(seq: list[tuple[Any, ...]]) -> bool:
    return any(n[0] == "rep" or any(_contains_repeat(s) for s in _children(n)) for n in seq)


def _has_nested_repeat(seq: list[tuple[Any, ...]]) -> bool:
    # An outer quantifier that can match at most once (``?``, ``{0,1}``) does
    # not repeat its group, so it cannot multiply the ways the inner repeat
    # splits a line; any quantifier inside a real repeat counts, ``?`` too,
    # since ``(a?)+`` style patterns backtrack as badly as ``(a+)+``.
    return any(
        (n[0] == "rep" and (n[3] is None or n[3] > 1) and _contains_repeat(n[2]))
        or any(_has_nested_repeat(s) for s in _children(n))
        for n in seq
    )


def _open_repeats(seq: list[tuple[Any, ...]]) -> int:
    # Summed over alternation branches too: simpler than finding the worst
    # branch, and never lower than it.
    return sum(
        (n[0] == "rep" and n[3] is None) + sum(_open_repeats(s) for s in _children(n)) for n in seq
    )


def _literal_run(seq: list[tuple[Any, ...]]) -> int:
    """The longest run of literal characters that every match must contain."""
    best = run = 0
    for node in seq:
        if node[0] == "lit":
            run += 1
            best = max(best, run)
            continue
        run = 0
        if node[0] == "alt":
            # Only text that every branch has is guaranteed.
            best = max(best, min(_literal_run(branch) for branch in node[1]))
        elif node[0] == "rep" and node[1] >= 1:
            best = max(best, _literal_run(node[2]))
    return best


def _compile_log(pattern: object, where: str) -> re.Pattern[str]:
    if not isinstance(pattern, str):
        raise PackError(f"{where}: every entry must be a string")
    if len(pattern) > _MAX_LOG_PATTERN:
        raise PackError(f"{where}: expression longer than {_MAX_LOG_PATTERN} characters")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise PackError(f"{where}: expression does not compile ({exc.msg})") from None
    except (RecursionError, OverflowError, ValueError):
        raise PackError(f"{where}: expression does not compile") from None
    # The contract says matching is case sensitive; inline flags would change
    # what a rule means without it being visible in the plain syntax.
    if compiled.flags & ~re.UNICODE:
        raise PackError(f"{where}: expression must not set flags")
    tree = _regex_tree(pattern)
    if tree is None:
        raise PackError(f"{where}: expression uses a construct that cannot be checked")
    if _has_nested_repeat(tree):
        raise PackError(f"{where}: expression repeats a group that contains a repeat")
    if _open_repeats(tree) > _MAX_OPEN_REPEATS:
        raise PackError(f"{where}: expression has more than {_MAX_OPEN_REPEATS} open-ended repeats")
    if _literal_run(tree) < _MIN_LITERAL_RUN:
        raise PackError(f"{where}: expression needs {_MIN_LITERAL_RUN} literal characters in a row")
    return compiled


def _compile_log_list(raw: object, where: str) -> tuple[re.Pattern[str], ...]:
    if not isinstance(raw, list) or not raw:
        raise PackError(f"{where}: must be a non-empty list")
    return tuple(_compile_log(p, where) for p in raw)


def match_log(rule: Rule, lines: Iterable[str]) -> str | None:
    """The first line a ``log`` expression is found in, stripped, or None.

    With ``log_also``, that line counts only if every ``log_also`` expression
    is also found in some line (the same line included). One pass, so a
    one-shot iterable over a long log tail is fine; it stops as soon as the
    answer is known.
    """
    if not rule.log:
        return None
    evidence: str | None = None
    missing = list(rule.log_also)
    for line in lines:
        text = line.rstrip("\r\n")[:_MAX_LINE]
        if evidence is None and any(pattern.search(text) for pattern in rule.log):
            evidence = text.strip()
        if missing:
            missing = [pattern for pattern in missing if not pattern.search(text)]
        if evidence is not None and not missing:
            return evidence
    return None


# --------------------------------------------------------------------------- #
# rules
# --------------------------------------------------------------------------- #

def _parse_when(raw: object) -> When:
    if not isinstance(raw, dict):
        raise PackError("when: must be an object")
    _check_keys(raw, _WHEN_KEYS, "when")
    if not raw:
        raise PackError("when: has no conditions")
    fields: dict[str, Any] = {}
    for name, choices in _WHEN_CHOICES.items():
        if name in raw:
            items = _str_list(raw[name], f"when.{name}")
            for item in items:
                if item not in choices:
                    raise PackError(f"when.{name}: {item!r} is not one of {', '.join(choices)}")
            fields[name] = tuple(items)
    for name in _WHEN_INTS:
        if name in raw:
            value = raw[name]
            if type(value) is not int or value < 0:  # bool is an int subclass; refuse it
                raise PackError(f"when.{name}: must be a whole number")
            fields[name] = value
    low, high = fields.get("proton_major_min"), fields.get("proton_major_max")
    if low is not None and high is not None and low > high:
        raise PackError("when: proton_major_min is above proton_major_max")
    if "launch_has" in raw:
        words = _str_list(raw["launch_has"], "when.launch_has")
        for word in words:
            if not _WORD_RE.fullmatch(word):
                raise PackError(f"when.launch_has: {word!r} is not a command name")
        fields["launch_has"] = tuple(words)
    for name in ("env_set", "env_unset"):
        if name in raw:
            names = _str_list(raw[name], f"when.{name}")
            for var in names:
                if not _KEY_RE.fullmatch(var):
                    raise PackError(f"when.{name}: {var!r} is not a valid variable name")
            fields[name] = tuple(names)
    return When(**fields)


def _parse_action(raw: object, where: str) -> Action:
    if not isinstance(raw, dict):
        raise PackError(f"{where}: must be an object")
    kind = raw.get("type")
    if kind == "user_snippet":
        raise PackError(f"{where}: user_snippet is not a pack action")
    if not isinstance(kind, str) or kind not in _ACTION_FIELDS:
        raise PackError(f"{where}: unknown action type {kind!r}")
    needed = _ACTION_FIELDS[kind]
    _check_keys(raw, ("type", *needed), where)
    for name in needed:
        if name not in raw:
            raise PackError(f"{where}: {kind} needs {name}")
    if kind == "env":
        key = _env_key(raw["key"], f"{where}.key")
        value = raw["value"]
        if not isinstance(value, str) or not _ENV_VALUE_RE.fullmatch(value):
            raise PackError(f"{where}.value: not allowed for env (letters, digits and _.,:=/+@%- only)")
        # Steam substitutes %command% wherever it appears, so a value holding
        # it would splice the game's command line into the assignment.
        if "%command%" in value:
            raise PackError(f"{where}.value: must not contain %command%")
        return Action("env", key=key, value=value)
    if kind == "unset_env":
        return Action("unset_env", key=_env_key(raw["key"], f"{where}.key"))
    if kind == "game_arg":
        value = raw["value"]
        if not isinstance(value, str) or not _GAME_ARG_RE.fullmatch(value):
            raise PackError(f"{where}.value: not a single game switch such as -vulkan")
        return Action("game_arg", value=value)
    if kind == "remove_word":
        value = raw["value"]
        if not isinstance(value, str) or not _WORD_RE.fullmatch(value):
            raise PackError(f"{where}.value: not a command name")
        return Action("remove_word", value=value)
    if kind == "manual":
        return Action("manual", text=_text(raw["text"], f"{where}.text", 300))
    return Action("default_proton")


def _parse_actions(raw: object) -> tuple[Action, ...]:
    if not isinstance(raw, list):
        raise PackError("actions: must be a list")
    if len(raw) > _MAX_ACTIONS:
        raise PackError(f"actions: more than {_MAX_ACTIONS}")
    actions = tuple(_parse_action(item, f"actions[{i}]") for i, item in enumerate(raw))
    # Actions are applied and undone together; two that touch the same
    # variable (or repeat each other) leave the result order-dependent.
    keys = [a.key for a in actions if a.type in ("env", "unset_env")]
    if len(keys) != len(set(keys)):
        raise PackError("actions: two actions change the same variable")
    if len(actions) != len(set(actions)):
        raise PackError("actions: the same action is listed twice")
    return actions


def parse_rule(raw: object) -> Rule:
    """Validate one rule from a pack. Raises :class:`PackError` with the first problem found."""
    if not isinstance(raw, dict):
        raise PackError("rule: must be an object")
    _check_keys(raw, _RULE_KEYS, "rule")
    for name in _RULE_KEYS:
        if name not in raw:
            raise PackError(f"rule: missing {name}")

    rule_id = raw["id"]
    if not isinstance(rule_id, str) or not _ID_RE.fullmatch(rule_id):
        raise PackError("id: 3 to 64 lowercase letters, digits and hyphens")
    if rule_id.startswith(_USER_ID_PREFIX):
        raise PackError(f"id: the {_USER_ID_PREFIX} prefix is kept for the user's own fixes")
    title = _text(raw["title"], "title", 100)
    cause = _text(raw["cause"], "cause", 400)
    severity = raw["severity"]
    if severity not in SEVERITIES:
        raise PackError(f"severity: must be one of {', '.join(SEVERITIES)}")

    match = raw["match"]
    if not isinstance(match, dict):
        raise PackError("match: must be an object")
    _check_keys(match, _MATCH_KEYS, "match")
    app_ids: tuple[str, ...] = ()
    if "app_ids" in match:
        ids = _str_list(match["app_ids"], "match.app_ids")
        for app_id in ids:
            if not _APP_ID_RE.fullmatch(app_id):
                raise PackError(f"match.app_ids: {app_id!r} is not a Steam App ID")
        app_ids = tuple(ids)
    log = _compile_log_list(match["log"], "match.log") if "log" in match else ()
    if "log_also" in match and "log" not in match:
        raise PackError("match.log_also: only allowed together with log")
    log_also = _compile_log_list(match["log_also"], "match.log_also") if "log_also" in match else ()
    when = _parse_when(match["when"]) if "when" in match else When()
    if not (app_ids or log or when.launch_has or when.env_set):
        raise PackError("match: needs app_ids, log, or a when with launch_has or env_set")
    if app_ids and not log and severity != "advice":
        raise PackError("severity: a rule with app_ids and no log must be advice")

    return Rule(
        id=rule_id,
        title=title,
        cause=cause,
        severity=severity,
        app_ids=app_ids,
        log=log,
        log_also=log_also,
        when=when,
        actions=_parse_actions(raw["actions"]),
        source=_source(raw["source"]),
        verified=_verified(raw["verified"]),
    )


# --------------------------------------------------------------------------- #
# packs
# --------------------------------------------------------------------------- #

def _usable_id(raw: object) -> str | None:
    if isinstance(raw, dict):
        rule_id = raw.get("id")
        if isinstance(rule_id, str) and _ID_RE.fullmatch(rule_id):
            return rule_id
    return None


def parse_pack(data: object) -> Pack:
    """Validate a decoded pack.

    Raises :class:`PackError` when ``data`` is not a pack at all or is a
    version this app does not understand; a rule that fails is reported in
    ``rejected`` and the others still load.
    """
    if not isinstance(data, dict) or data.get("format") != PACK_FORMAT:
        raise PackError(f"not a fix pack (format is not {PACK_FORMAT})")
    version = data.get("version")
    if type(version) is not int:
        raise PackError("version must be a whole number")
    if version > PACK_VERSION:
        raise PackError(f"pack version {version} is newer than this app understands")
    if version != PACK_VERSION:
        raise PackError(f"pack version {version} is not supported")
    _check_keys(data, _PACK_KEYS, "pack")
    revision = data.get("revision")
    if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
        raise PackError("revision must look like YYYY.MM.N")
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        raise PackError("rules must be a list")

    rules: list[Rule] = []
    rejected: list[tuple[str, str]] = []
    # Every id seen so far, accepted or not: a later rule never takes the
    # place of an earlier one, whatever happened to the earlier one.
    seen: set[str] = set()
    for index, raw in enumerate(raw_rules):
        rule_id = _usable_id(raw)
        label = rule_id or f"#{index}"
        if rule_id is not None and rule_id in seen:
            rejected.append((label, "duplicate id"))
            continue
        if rule_id is not None:
            seen.add(rule_id)
        try:
            rules.append(parse_rule(raw))
        except PackError as exc:
            rejected.append((label, str(exc)))
    return Pack(revision, rules, rejected)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    # json keeps the last of two equal keys silently; in a rule that would
    # let one reading of the file differ from another.
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PackError(f"duplicate key {key!r}")
        out[key] = value
    return out


def load_pack(path: Path) -> Pack:
    """Read, decode and validate the pack at ``path``. Raises :class:`PackError`."""
    try:
        with open(path, "rb") as fh:
            if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                raise PackError("pack is not a regular file")
            raw = fh.read(_MAX_PACK_BYTES + 1)
    except OSError as exc:
        raise PackError(f"cannot read the pack ({exc.strerror or exc})") from None
    if len(raw) > _MAX_PACK_BYTES:
        raise PackError("pack file is larger than 2 MB")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except PackError:
        raise
    except UnicodeDecodeError:
        raise PackError("pack is not UTF-8 text") from None
    except (ValueError, RecursionError):
        raise PackError("pack is not valid JSON") from None
    return parse_pack(data)


def load_bundled_pack() -> Pack:
    """The pack shipped with the app. Never raises; a failure is one ``("pack", reason)`` entry."""
    try:
        return load_pack(_BUNDLED_PATH)
    except PackError as exc:
        return Pack("", [], [("pack", str(exc))])
    except Exception:  # noqa: BLE001 - Diagnose must still open with an empty pack
        return Pack("", [], [("pack", "the bundled pack could not be loaded")])


# --------------------------------------------------------------------------- #
# the user's own fixes
# --------------------------------------------------------------------------- #

def _user_action(entry: dict[Any, Any]) -> Action | None:
    value = entry.get("value", "")
    # A line break or NUL would end the launch-options line or the string
    # carrying it; nothing else about the user's own value is limited.
    if not isinstance(value, str) or any(ch in value for ch in "\n\r\0"):
        return None
    kind = entry.get("type")
    if kind == "env":
        key = entry.get("key", "")
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            return None
        return Action("env", key=key, value=value)
    if kind == "launch_arg":
        snippet = value.strip()
        if not snippet or len(snippet) > _MAX_USER_SNIPPET:
            return None
        return Action("user_snippet", value=snippet)
    return None


def user_rules(app_id: str) -> list[Rule]:
    """The user's version 1 fixes for ``app_id`` as advice rules; unusable entries are skipped."""
    rules: list[Rule] = []
    for position, entry in enumerate(_fixes._load_user_fixes(app_id), start=1):
        if not isinstance(entry, dict):
            continue
        title = entry.get("title", "")
        description = entry.get("description", "")
        if not isinstance(title, str) or not isinstance(description, str):
            continue
        action = _user_action(entry)
        if action is None:
            continue
        rules.append(Rule(
            id=f"{_USER_ID_PREFIX}{position}",
            title=title.strip()[:100] or "Your own fix",
            cause=description.strip()[:400],
            severity="advice",
            app_ids=(app_id,),
            log=(),
            log_also=(),
            when=When(),
            actions=(action,),
            source="",
            verified="",
            origin="user",
        ))
    return rules
