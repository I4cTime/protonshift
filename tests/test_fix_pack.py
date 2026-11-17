"""Tests for protonshift.core.fix_pack - the Diagnose rule file loader.

docs/fix-pack.md is the contract these tests hold the loader to. Pure core:
no Qt, no network, no real home directory.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from protonshift.core import fix_pack
from protonshift.core import fixes as fixes_mod
from protonshift.core.fix_pack import (
    PACK_FORMAT,
    PACK_VERSION,
    Action,
    PackError,
    load_bundled_pack,
    load_pack,
    match_log,
    parse_pack,
    parse_rule,
    user_rules,
)

LOG_LINE = r"wine: could not load kernel32\.dll"


def rule(**overrides: Any) -> dict[str, Any]:
    """A minimal valid rule; keyword overrides replace top-level fields."""
    base: dict[str, Any] = {
        "id": "kernel32-missing",
        "title": "Wine could not load kernel32",
        "cause": "The prefix is broken.",
        "severity": "blocking",
        "match": {"log": [LOG_LINE]},
        "actions": [],
        "source": "https://github.com/ValveSoftware/Proton/issues/1",
        "verified": "2026-11-16",
    }
    base.update(overrides)
    return base


def with_match(**match: Any) -> dict[str, Any]:
    return rule(match=match)


def with_actions(*actions: dict[str, Any]) -> dict[str, Any]:
    return rule(actions=list(actions))


def pack(*rules: Any, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "format": PACK_FORMAT,
        "version": PACK_VERSION,
        "revision": "2026.11.1",
        "rules": list(rules),
    }
    base.update(overrides)
    return base


def rejects(raw: Any, fragment: str = "") -> str:
    with pytest.raises(PackError) as info:
        parse_rule(raw)
    assert fragment in str(info.value), str(info.value)
    return str(info.value)


# --------------------------------------------------------------------------- #
# a valid rule
# --------------------------------------------------------------------------- #

def test_minimal_rule_parses() -> None:
    r = parse_rule(rule())
    assert r.id == "kernel32-missing"
    assert r.severity == "blocking"
    assert r.app_ids == ()
    assert [p.pattern for p in r.log] == [LOG_LINE]
    assert r.log_also == ()
    assert r.actions == ()
    assert r.origin == "pack"


def test_full_rule_parses() -> None:
    r = parse_rule(rule(
        match={
            "app_ids": ["1091500", "570"],
            "log": [LOG_LINE],
            "log_also": [r"err:module:import_dll"],
            "when": {
                "gpu_vendor": ["nvidia", "amd"],
                "session": ["wayland"],
                "proton_family": ["ge"],
                "proton_major_min": 8,
                "proton_major_max": 9,
                "launch_has": ["gamemoderun"],
                "env_set": ["DXVK_HUD"],
                "env_unset": ["PROTON_LOG"],
            },
        },
        actions=[
            {"type": "env", "key": "PROTON_ENABLE_NVAPI", "value": "1"},
            {"type": "unset_env", "key": "DXVK_ASYNC"},
            {"type": "game_arg", "value": "-vulkan"},
            {"type": "remove_word", "value": "gamemoderun"},
            {"type": "default_proton"},
            {"type": "manual", "text": "Verify the game files in Steam."},
        ],
    ))
    assert r.app_ids == ("1091500", "570")
    assert r.when.gpu_vendor == ("nvidia", "amd")
    assert r.when.proton_major_min == 8 and r.when.proton_major_max == 9
    assert r.when.launch_has == ("gamemoderun",)
    assert [a.type for a in r.actions] == [
        "env", "unset_env", "game_arg", "remove_word", "default_proton", "manual",
    ]
    assert r.actions[0] == Action("env", key="PROTON_ENABLE_NVAPI", value="1")
    assert r.actions[5].text == "Verify the game files in Steam."


def test_rule_is_frozen() -> None:
    r = parse_rule(rule())
    with pytest.raises(AttributeError):
        r.title = "changed"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# top-level fields
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw", [None, [], "rule", 3])
def test_rule_must_be_an_object(raw: Any) -> None:
    rejects(raw, "must be an object")


@pytest.mark.parametrize("missing", ["id", "title", "cause", "severity", "match", "actions", "source", "verified"])
def test_every_field_is_required(missing: str) -> None:
    raw = rule()
    del raw[missing]
    rejects(raw, f"missing {missing}")


def test_unknown_rule_field_is_rejected() -> None:
    raw = rule()
    raw["serverity"] = "advice"
    rejects(raw, "unknown field 'serverity'")


@pytest.mark.parametrize(
    "bad_id",
    ["ab", "a" * 65, "Upper-case", "under_score", "spa ce", "dot.ted", "", 7, None, "kernel\n"],
)
def test_bad_ids(bad_id: Any) -> None:
    rejects(rule(id=bad_id), "id:")


@pytest.mark.parametrize("good_id", ["abc", "a" * 64, "0-9", "wrapper-gamemoderun-missing"])
def test_good_ids(good_id: str) -> None:
    assert parse_rule(rule(id=good_id)).id == good_id


def test_user_prefix_is_reserved() -> None:
    rejects(rule(id="user-1"), "user-")


@pytest.mark.parametrize("field,limit", [("title", 100), ("cause", 400)])
def test_text_limits(field: str, limit: int) -> None:
    assert getattr(parse_rule(rule(**{field: "x" * limit})), field) == "x" * limit
    rejects(rule(**{field: "x" * (limit + 1)}), f"longer than {limit}")


@pytest.mark.parametrize("field", ["title", "cause"])
@pytest.mark.parametrize("bad", ["", "   ", 5, None, ["text"], "two\nlines", "tab\there", "nul\0"])
def test_text_rejections(field: str, bad: Any) -> None:
    rejects(rule(**{field: bad}), f"{field}:")


@pytest.mark.parametrize("severity", ["blocking", "likely", "advice"])
def test_severities(severity: str) -> None:
    assert parse_rule(rule(severity=severity)).severity == severity


@pytest.mark.parametrize("bad", ["Blocking", "error", "", None, 1, ["advice"]])
def test_bad_severity(bad: Any) -> None:
    rejects(rule(severity=bad), "severity:")


@pytest.mark.parametrize(
    "good",
    [
        "https://github.com/ValveSoftware/Proton/issues/1",
        "https://gitlab.winehq.org/wine/wine/-/blob/master/dlls/ntdll/loader.c#L100",
        "https://example.org/" + "a" * (300 - len("https://example.org/")),
    ],
)
def test_good_sources(good: str) -> None:
    assert parse_rule(rule(source=good)).source == good


@pytest.mark.parametrize(
    "bad",
    [
        "http://github.com/x",
        "github.com/x",
        "ftp://x.org/y",
        "https://",
        "https:///path",
        "https://ex ample.org/",
        "https://example.org/\n",
        "https://example.org/\ttab",
        "https://example.org/" + "a" * 281,
        "HTTPS://example.org/",
        "",
        None,
        3,
    ],
)
def test_bad_sources(bad: Any) -> None:
    rejects(rule(source=bad), "source:")


@pytest.mark.parametrize("good", ["2026-11-16", "2024-02-29", "1999-01-01"])
def test_good_verified(good: str) -> None:
    assert parse_rule(rule(verified=good)).verified == good


@pytest.mark.parametrize(
    "bad",
    ["2026-02-30", "2025-02-29", "2026-13-01", "2026-1-16", "20261116", "2026-11-16T00:00",
     "16-11-2026", "2026-11-16\n", "", None, 20261116],
)
def test_bad_verified(bad: Any) -> None:
    rejects(rule(verified=bad), "verified:")


# --------------------------------------------------------------------------- #
# match
# --------------------------------------------------------------------------- #

def test_match_must_be_an_object() -> None:
    rejects(rule(match=["570"]), "match: must be an object")


def test_unknown_match_field_is_rejected() -> None:
    rejects(with_match(log=[LOG_LINE], apps=["570"]), "unknown field 'apps'")


def test_empty_match_is_rejected() -> None:
    rejects(with_match(), "match: needs")


@pytest.mark.parametrize(
    "match",
    [
        {"app_ids": ["570"]},
        {"log": [LOG_LINE]},
        {"when": {"launch_has": ["gamemoderun"]}},
        {"when": {"env_set": ["DXVK_HUD"]}},
    ],
)
def test_match_presence_rule_accepts(match: dict[str, Any]) -> None:
    parse_rule(rule(match=match, severity="advice"))


@pytest.mark.parametrize(
    "when",
    [
        {"gpu_vendor": ["nvidia"]},
        {"session": ["wayland"]},
        {"proton_family": ["ge"], "proton_major_min": 8},
        {"env_unset": ["DXVK_HUD"]},
    ],
)
def test_match_presence_rule_rejects_machine_only_when(when: dict[str, Any]) -> None:
    rejects(rule(match={"when": when}, severity="advice"), "match: needs")


def test_app_ids_without_log_must_be_advice() -> None:
    assert parse_rule(rule(match={"app_ids": ["570"]}, severity="advice")).severity == "advice"
    for severity in ("blocking", "likely"):
        rejects(rule(match={"app_ids": ["570"]}, severity=severity), "must be advice")


def test_app_ids_with_log_may_be_blocking() -> None:
    assert parse_rule(with_match(app_ids=["570"], log=[LOG_LINE])).severity == "blocking"


@pytest.mark.parametrize(
    "bad",
    ["570", 570, [], [570], ["57 0"], ["-570"], ["abc"], ["570\n"], ["٥٧٠"], [None]],
)
def test_bad_app_ids(bad: Any) -> None:
    rejects(rule(match={"app_ids": bad, "log": [LOG_LINE]}), "match.app_ids")


@pytest.mark.parametrize("bad", ["just a string", [], None, {"a": 1}])
def test_bad_log_container(bad: Any) -> None:
    rejects(with_match(log=bad), "match.log")


def test_log_entries_must_be_strings() -> None:
    rejects(with_match(log=[LOG_LINE, 7]), "must be a string")


# --------------------------------------------------------------------------- #
# when
# --------------------------------------------------------------------------- #

def when_rule(**when: Any) -> dict[str, Any]:
    return rule(match={"log": [LOG_LINE], "when": when})


def test_when_must_be_an_object() -> None:
    rejects(rule(match={"log": [LOG_LINE], "when": ["nvidia"]}), "when: must be an object")


def test_empty_when_is_rejected() -> None:
    rejects(when_rule(), "no conditions")


def test_unknown_when_field_is_rejected() -> None:
    rejects(when_rule(gpu_vendors=["nvidia"]), "unknown field 'gpu_vendors'")


@pytest.mark.parametrize(
    "name,good,bad",
    [
        ("gpu_vendor", ["nvidia", "amd", "intel"], ["NVIDIA"]),
        ("session", ["wayland", "x11"], ["xorg"]),
        ("proton_family", ["valve", "ge", "cachyos", "other"], ["proton-ge"]),
    ],
)
def test_when_choice_lists(name: str, good: list[str], bad: list[str]) -> None:
    assert getattr(parse_rule(when_rule(**{name: good})).when, name) == tuple(good)
    rejects(when_rule(**{name: bad}), f"when.{name}")
    rejects(when_rule(**{name: []}), "must not be empty")
    rejects(when_rule(**{name: good[0]}), "must be a list")


@pytest.mark.parametrize("name", ["proton_major_min", "proton_major_max"])
@pytest.mark.parametrize("bad", ["9", 9.0, True, False, -1, None, [9]])
def test_when_ints_reject(name: str, bad: Any) -> None:
    rejects(when_rule(**{name: bad}), f"when.{name}")


@pytest.mark.parametrize("name", ["proton_major_min", "proton_major_max"])
def test_when_ints_accept(name: str) -> None:
    assert getattr(parse_rule(when_rule(**{name: 0})).when, name) == 0
    assert getattr(parse_rule(when_rule(**{name: 10})).when, name) == 10


def test_when_min_above_max_is_rejected() -> None:
    assert parse_rule(when_rule(proton_major_min=9, proton_major_max=9)).when.proton_major_max == 9
    rejects(when_rule(proton_major_min=10, proton_major_max=9), "above")


@pytest.mark.parametrize("bad", [["game moderun"], ["gamemoderun;"], ["a/b"], [""], ["x" * 41], [1]])
def test_when_launch_has_rejects(bad: list[Any]) -> None:
    rejects(when_rule(launch_has=bad), "when.launch_has")


@pytest.mark.parametrize("name", ["env_set", "env_unset"])
@pytest.mark.parametrize("bad", [["1ABC"], ["A-B"], ["A B"], ["A\n"], [""], "DXVK_HUD", []])
def test_when_env_names_reject(name: str, bad: Any) -> None:
    rejects(when_rule(**{name: bad}), f"when.{name}")


def test_when_env_lists_do_not_use_the_forbidden_list() -> None:
    # Conditions only read the launch options; checking for PATH is harmless.
    assert parse_rule(when_rule(env_set=["LD_PRELOAD"])).when.env_set == ("LD_PRELOAD",)


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bad", [None, {}, "env", {"type": "env"}])
def test_actions_must_be_a_list(bad: Any) -> None:
    rejects(rule(actions=bad), "actions: must be a list")


def test_at_most_six_actions() -> None:
    six = [{"type": "game_arg", "value": f"-a{i}"} for i in range(6)]
    assert len(parse_rule(rule(actions=six)).actions) == 6
    seven = [{"type": "game_arg", "value": f"-a{i}"} for i in range(7)]
    rejects(rule(actions=seven), "more than 6")


@pytest.mark.parametrize("bad", ["remove", "", None, 3, "ENV", "user_snippet"])
def test_unknown_action_types(bad: Any) -> None:
    rejects(with_actions({"type": bad, "value": "x"}), "actions[0]")


def test_action_without_type() -> None:
    rejects(with_actions({"key": "A", "value": "1"}), "unknown action type")


def test_action_must_be_an_object() -> None:
    rejects(with_actions("env"), "actions[0]: must be an object")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "action",
    [
        {"type": "env", "key": "A", "value": "1", "text": "x"},
        {"type": "unset_env", "key": "A", "value": ""},
        {"type": "game_arg", "value": "-vulkan", "key": "A"},
        {"type": "remove_word", "value": "gamemoderun", "position": "before"},
        {"type": "default_proton", "value": "GE-Proton9-1"},
        {"type": "manual", "text": "Do it.", "url": "https://x.org"},
    ],
)
def test_unknown_action_fields(action: dict[str, Any]) -> None:
    rejects(with_actions(action), "unknown field")


@pytest.mark.parametrize(
    "action",
    [
        {"type": "env", "key": "A"},
        {"type": "env", "value": "1"},
        {"type": "unset_env"},
        {"type": "game_arg"},
        {"type": "remove_word"},
        {"type": "manual"},
    ],
)
def test_missing_action_fields(action: dict[str, Any]) -> None:
    rejects(with_actions(action), "needs")


@pytest.mark.parametrize(
    "value",
    ["", "1", "fps,frametime", "/tmp/dxvk.log", "a=b", "user@host", "50%", "1.5:2+3-4_x", "x" * 200],
)
def test_env_values_accepted(value: str) -> None:
    (action,) = parse_rule(with_actions({"type": "env", "key": "DXVK_HUD", "value": value})).actions
    assert action.value == value


@pytest.mark.parametrize(
    "value",
    ["a b", "x" * 201, "a;b", "$(id)", "`id`", "'q'", '"q"', "a\nb", "a|b", "a&b", "~", "a*", "%command%",
     "x%command%y", 1, None, True],
)
def test_env_values_rejected(value: Any) -> None:
    rejects(with_actions({"type": "env", "key": "DXVK_HUD", "value": value}), "value")


@pytest.mark.parametrize(
    "key",
    ["PROTON_LOG", "WINE_CPU_TOPOLOGY", "DXVK_HUD", "VKD3D_CONFIG", "MESA_GLTHREAD", "RADV_PERFTEST",
     "__GL_SHADER_DISK_CACHE", "__NV_PRIME_RENDER_OFFLOAD", "SDL_VIDEODRIVER", "MANGOHUD", "MANGOHUD_CONFIG"],
)
@pytest.mark.parametrize("kind", ["env", "unset_env"])
def test_env_keys_accepted(kind: str, key: str) -> None:
    action: dict[str, Any] = {"type": kind, "key": key}
    if kind == "env":
        action["value"] = "1"
    assert parse_rule(with_actions(action)).actions[0].key == key


@pytest.mark.parametrize("key", ["A", "_", "_a1", "mesa_glthread", "MY_VAR", "DXVK", "proton_log"])
def test_env_keys_outside_the_families(key: str) -> None:
    # Setting is limited to the families; removing is not.
    rejects(with_actions({"type": "env", "key": key, "value": "1"}), "not in a family")
    assert parse_rule(with_actions({"type": "unset_env", "key": key})).actions[0].key == key


@pytest.mark.parametrize(
    "key",
    ["", "1A", "A-B", "A B", "A=", "A\n", "ÉTÉ", None, 5,
     "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "PATH", "PYTHONPATH",
     "STEAM_COMPAT_LAUNCHER_SERVICE", "WINEDLLPATH", "STEAM_COMPAT_DATA_PATH", "STEAM_COMPAT_",
     "PROTON_REMOTE_DEBUG_CMD", "SDL_DYNAMIC_API", "WINEDLLOVERRIDES"],
)
@pytest.mark.parametrize("kind", ["env", "unset_env"])
def test_env_keys_rejected(kind: str, key: Any) -> None:
    action: dict[str, Any] = {"type": kind, "key": key}
    if kind == "env":
        action["value"] = "1"
    rejects(with_actions(action), "key")


def test_forbidden_list_is_case_sensitive() -> None:
    # Variables are case sensitive: ``path`` is not ``PATH``.
    assert parse_rule(with_actions({"type": "unset_env", "key": "path"})).actions[0].key == "path"
    rejects(with_actions({"type": "unset_env", "key": "STEAM_COMPAT_CLIENT_INSTALL_PATH"}), "may not")


@pytest.mark.parametrize("value", ["-vulkan", "+fps_max=0", "-dx11", "-a", "+x:y.z", "-" + "a" * 60])
def test_game_arg_accepted(value: str) -> None:
    assert parse_rule(with_actions({"type": "game_arg", "value": value})).actions[0].value == value


@pytest.mark.parametrize(
    "value",
    ["vulkan", "-", "+", "-a b", "-" + "a" * 61, "-a;b", "-$(id)", "-a/b", "%command%", "--x\n", "", 1, None],
)
def test_game_arg_rejected(value: Any) -> None:
    rejects(with_actions({"type": "game_arg", "value": value}), "value")


@pytest.mark.parametrize("value", ["gamemoderun", "mangohud", "obs-gamecapture", "a.b_c", "x" * 40])
def test_remove_word_accepted(value: str) -> None:
    assert parse_rule(with_actions({"type": "remove_word", "value": value})).actions[0].value == value


@pytest.mark.parametrize(
    "value",
    ["", "x" * 41, "/usr/bin/gamemoderun", "a b", "%command%", "A=1", "a;b", "a\n", 1, None],
)
def test_remove_word_rejected(value: Any) -> None:
    rejects(with_actions({"type": "remove_word", "value": value}), "value")


def test_manual_text_limits() -> None:
    assert parse_rule(with_actions({"type": "manual", "text": "x" * 300})).actions[0].text == "x" * 300
    rejects(with_actions({"type": "manual", "text": "x" * 301}), "longer than 300")
    rejects(with_actions({"type": "manual", "text": ""}), "empty")
    rejects(with_actions({"type": "manual", "text": 5}), "string")


def test_default_proton_has_no_fields() -> None:
    assert parse_rule(with_actions({"type": "default_proton"})).actions == (Action("default_proton"),)


@pytest.mark.parametrize(
    "actions",
    [
        [{"type": "env", "key": "DXVK_HUD", "value": "1"}, {"type": "env", "key": "DXVK_HUD", "value": "2"}],
        [{"type": "env", "key": "DXVK_HUD", "value": "1"}, {"type": "unset_env", "key": "DXVK_HUD"}],
        [{"type": "default_proton"}, {"type": "default_proton"}],
        [{"type": "game_arg", "value": "-vulkan"}, {"type": "game_arg", "value": "-vulkan"}],
    ],
)
def test_conflicting_or_repeated_actions(actions: list[dict[str, Any]]) -> None:
    rejects(rule(actions=actions), "actions:")


# --------------------------------------------------------------------------- #
# log expressions
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "pattern",
    [
        LOG_LINE,
        r"\.\.\.\.\.\.\.\.",  # escaped characters are literals
        r"[.][.][.][.][.][.][.][.]",  # a one-member class is that literal
        r"(kern)el32",  # an unquantified group is part of the run
        r"(?:kernel32\.dll){1}",  # a repeat that happens at least once guarantees its text
        r"\S+ kernel32\.dll",  # a repeated class
        r"[0-9a-f]{7} kernel32dll",
        r"(a)+kernel32dll",  # a group of one character is one character
        r"kernel32\.dll|kernel32\.sys",  # both branches share the run
        r"^err:module:import_dll Library \S+ not found$",
        r"(?:\d+ )?err:module:",  # an optional group may hold a repeat
        r"(?=x)kernel32dll",
        r"x{0,1}abcdefgh",
        r"(?>vkCreate)Instance failed",
    ],
)
def test_log_expressions_accepted(pattern: str) -> None:
    assert parse_rule(with_match(log=[pattern])).log[0].pattern == pattern


def test_log_expression_length_limit() -> None:
    exact = "kernel32" + "x" * 292
    assert len(exact) == 300
    parse_rule(with_match(log=[exact]))
    rejects(with_match(log=[exact + "x"]), "longer than 300")


@pytest.mark.parametrize(
    "pattern",
    [
        r"err:",
        r"kernel3",
        r"kernel3.dll",  # . is not a literal
        r"[kK]ernel32",  # a class of two is not a literal
        r"\bkernel\b32dll",  # an anchor breaks the run
        r"abcdefg|abcdefgh",  # one branch is too short
        r"(?:kernel32\.dll){0,1}",  # may not happen at all
        r"(?:kernel32\.dll)?",
        r"(?=kernel32\.dll)",  # lookaround text is not consumed
        r"a{8}",
        r".*",
        r"",
    ],
)
def test_log_expressions_without_a_literal_run(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "8 literal characters")


@pytest.mark.parametrize(
    "pattern",
    [
        r"(a+)+kernel32dll",
        r"(?:a*)*kernel32dll",
        r"(a|b+)*kernel32dll",
        r"(a?)+kernel32dll",
        r"(a{2}){3}kernel32dll",
        r"(?:x(?:y+z)+)+kernel32dll",
        r"(\d+\s)++kernel32dll",
        r"kernel32dll(?=(a+)+)",
        # a repeated group without a repeat inside is refused too
        r"(?:aaaaaaaa|aaaaaaaaaaaaaaaa)+$",
        r"(?:ab){2,50}kernel32dll",
        r"(a|aa){3}kernel32dll",
        r"(?:kernel32\.dll)+",
        r"(?:kernel32\.dll)*",
        r"kernel32dll(?:\.so)?(?:ab)+",
        r"(?:(?:ab)+)?kernel32dll",  # inside an optional group, checked all the same
    ],
)
def test_log_expressions_with_repeated_groups(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "repeats a group")


def test_backtracking_pattern_is_refused_before_it_ever_runs() -> None:
    # The review's example takes exponential time on a line of a's that does
    # not end where $ wants. Asserting the time would flake; what matters is
    # that the loader refuses it, so match_log never gets to run it.
    pattern = r"(?:aaaaaaaa|aaaaaaaaaaaaaaaa)+$"
    msg = rejects(with_match(log=[pattern]), "repeats a group")
    assert msg.startswith("match.log")
    loaded = parse_pack(pack(rule(match={"log": [pattern]})))
    assert loaded.rules == [] and "repeats a group" in loaded.rejected[0][1]


@pytest.mark.parametrize("pattern", [r"kernel32(", r"kernel32[", "kernel32\\", r"*kernel32", r"kernel32{2,1}"])
def test_log_expressions_that_do_not_compile(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "does not compile")


@pytest.mark.parametrize(
    "pattern",
    [
        r"Library (\S+) \(which is needed by .+\) not found",  # two open-ended repeats
        r"kernel32\.dll.*x{2,5}y{0,9}z?",  # bounded repeats do not count
        r"kernel32\.dll(?:a|b)+c*",
    ],
)
def test_log_expressions_with_two_open_repeats(pattern: str) -> None:
    assert parse_rule(with_match(log=[pattern])).log[0].pattern == pattern


@pytest.mark.parametrize(
    "pattern",
    [
        r"aaaaaaaa.*b.*c.*d",
        r"kernel32\.dll x{3,} y+ z*",  # {n,} is open-ended
        r"kernel32\.dll(?:a+|b*|c+)",  # alternation branches are summed
        r"kernel32\.dll(?=a+b+)c*",  # lookarounds count
        r"kernel32\.dll(x+)(y+)(z+?)",  # inside groups, lazy too
    ],
)
def test_log_expressions_with_three_open_repeats(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "open-ended repeats")


def test_log_also_open_repeat_limit() -> None:
    rejects(with_match(log=[LOG_LINE], log_also=[r"aaaaaaaa.*b.*c.*d"]), "match.log_also")


@pytest.mark.parametrize("pattern", [r"(?i)kernel32\.dll", r"(?s)kernel32\.dll", r"(?a)kernel32\.dll"])
def test_log_expressions_with_flags(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "flags")


@pytest.mark.parametrize(
    "pattern",
    [r"(?i:k)ernel32\.dll", r"(a)\1kernel32dll", r"(?P<a>x)(?(a)y|z)kernel32dll"],
)
def test_log_expressions_that_cannot_be_checked(pattern: str) -> None:
    rejects(with_match(log=[pattern]), "cannot be checked")


def test_regex_parser_unavailable_is_a_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fix_pack, "_regex_tree", lambda pattern: None)
    rejects(rule(), "cannot be checked")


def test_regex_parser_surprise_is_a_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    import re._parser as real_parser

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("new layout")

    monkeypatch.setattr(real_parser, "parse", boom)
    assert fix_pack._regex_tree(LOG_LINE) is None


# --------------------------------------------------------------------------- #
# log_also
# --------------------------------------------------------------------------- #

def test_log_also_needs_log() -> None:
    rejects(rule(match={"app_ids": ["570"], "log_also": [LOG_LINE]}, severity="advice"), "together with log")


def test_log_also_parses() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_also=[r"err:module:import_dll", r"Game start failed"]))
    assert [p.pattern for p in r.log_also] == [r"err:module:import_dll", r"Game start failed"]


@pytest.mark.parametrize(
    "bad,fragment",
    [
        ([], "non-empty list"),
        ("err:module:import_dll", "non-empty list"),
        ([7], "must be a string"),
        (["err:"], "8 literal characters"),
        (["(a+)+kernel32dll"], "repeats a group"),
        (["kernel32("], "does not compile"),
        (["kernel32" + "x" * 293], "longer than 300"),
        (["(?i)kernel32dll"], "flags"),
    ],
)
def test_log_also_limits(bad: Any, fragment: str) -> None:
    msg = rejects(with_match(log=[LOG_LINE], log_also=bad), fragment)
    assert msg.startswith("match.log_also")


# --------------------------------------------------------------------------- #
# match_log
# --------------------------------------------------------------------------- #

def test_match_log_returns_first_matching_line_stripped() -> None:
    r = parse_rule(with_match(log=[LOG_LINE, r"err:module:import_dll"]))
    lines = ["fixme:heap:x\n", "  0024:err:module:import_dll Library foo\n", "wine: could not load kernel32.dll\n"]
    assert match_log(r, lines) == "0024:err:module:import_dll Library foo"


def test_match_log_none_without_a_match() -> None:
    r = parse_rule(rule())
    assert match_log(r, ["fixme:heap:x", "all good"]) is None
    assert match_log(r, []) is None


def test_match_log_without_log_part() -> None:
    r = parse_rule(rule(match={"app_ids": ["570"]}, severity="advice"))
    assert match_log(r, ["wine: could not load kernel32.dll"]) is None


def test_match_log_is_case_sensitive() -> None:
    assert match_log(parse_rule(rule()), ["WINE: COULD NOT LOAD KERNEL32.DLL"]) is None


def test_match_log_looks_at_first_2000_characters_only() -> None:
    r = parse_rule(rule())
    hit = "wine: could not load kernel32.dll"
    assert match_log(r, ["x" * (2000 - len(hit)) + hit]) is not None
    assert match_log(r, ["x" * (2001 - len(hit)) + hit]) is None
    long_line = hit + "y" * 5000
    found = match_log(r, [long_line])
    assert found is not None and len(found) == 2000


def test_match_log_end_anchor_ignores_line_ending() -> None:
    r = parse_rule(with_match(log=[r"kernel32\.dll$"]))
    assert match_log(r, ["wine: could not load kernel32.dll\r\n"]) == "wine: could not load kernel32.dll"


def test_match_log_with_log_also_satisfied() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_also=[r"Game start failed", r"err:module:import_dll"]))
    lines = iter([
        "err:module:import_dll Library x not found",
        "wine: could not load kernel32.dll",
        "noise",
        "Game start failed: 5",
    ])  # a one-shot iterable, and the log_also lines come before and after the evidence
    assert match_log(r, lines) == "wine: could not load kernel32.dll"


def test_match_log_with_log_also_on_the_same_line() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_also=[r"could not load"]))
    assert match_log(r, ["wine: could not load kernel32.dll"]) == "wine: could not load kernel32.dll"


def test_match_log_with_log_also_unsatisfied() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_also=[r"Game start failed", r"err:module:import_dll"]))
    lines = ["wine: could not load kernel32.dll", "err:module:import_dll Library x not found"]
    assert match_log(r, lines) is None
    # log_also alone is never evidence
    assert match_log(r, ["Game start failed", "err:module:import_dll"]) is None


def test_match_log_stops_once_answered() -> None:
    r = parse_rule(rule())
    seen: list[str] = []

    def lines() -> Any:
        for line in ["a", "wine: could not load kernel32.dll", "b", "c"]:
            seen.append(line)
            yield line

    assert match_log(r, lines()) is not None
    assert seen == ["a", "wine: could not load kernel32.dll"]


# --------------------------------------------------------------------------- #
# log_none
# --------------------------------------------------------------------------- #

NONE_LINE = r"DXVK: No adapters found\."
HIT = "wine: could not load kernel32.dll"
EXCLUDED = "warn:  DXVK: No adapters found."


def test_log_none_needs_log() -> None:
    rejects(rule(match={"app_ids": ["570"], "log_none": [NONE_LINE]}, severity="advice"), "together with log")


def test_log_none_parses() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_none=[NONE_LINE]))
    assert [p.pattern for p in r.log_none] == [NONE_LINE]
    assert parse_rule(rule()).log_none == ()


@pytest.mark.parametrize(
    "bad,fragment",
    [
        ([], "non-empty list"),
        (NONE_LINE, "non-empty list"),
        ([7], "must be a string"),
        (["DXVK"], "8 literal characters"),
        (["(a+)+kernel32dll"], "repeats a group"),
        (["aaaaaaaa.*b.*c.*d"], "open-ended repeats"),
        (["kernel32("], "does not compile"),
        (["kernel32" + "x" * 293], "longer than 300"),
        (["(?i)kernel32dll"], "flags"),
    ],
)
def test_log_none_limits(bad: Any, fragment: str) -> None:
    msg = rejects(with_match(log=[LOG_LINE], log_none=bad), fragment)
    assert msg.startswith("match.log_none")


@pytest.mark.parametrize(
    "lines",
    [
        [EXCLUDED, HIT],
        [HIT, "noise", EXCLUDED],
        [HIT + " / " + EXCLUDED],
    ],
    ids=["before", "after", "same-line"],
)
def test_log_none_excludes(lines: list[str]) -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_none=[NONE_LINE]))
    assert match_log(r, iter(lines)) is None


def test_log_none_absent_keeps_the_match() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_none=[NONE_LINE]))
    assert match_log(r, iter(["noise", HIT, "more noise"])) == HIT
    assert match_log(r, iter(["noise"])) is None


def test_log_none_any_of_several() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_none=[NONE_LINE, r"Game start failed"]))
    assert match_log(r, [HIT, "Game start failed"]) is None


def test_log_none_stops_on_the_excluding_line() -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_none=[NONE_LINE]))
    seen: list[str] = []

    def lines() -> Any:
        for line in [HIT, EXCLUDED, "after"]:
            seen.append(line)
            yield line

    assert match_log(r, lines()) is None
    assert seen == [HIT, EXCLUDED]


@pytest.mark.parametrize(
    "lines,expected",
    [
        (["Game start failed", HIT], HIT),
        ([HIT, "Game start failed"], HIT),
        ([HIT], None),  # log_also missing
        (["Game start failed", HIT, EXCLUDED], None),  # excluded after both
        ([EXCLUDED, "Game start failed", HIT], None),  # excluded before both
        ([HIT, EXCLUDED, "Game start failed"], None),  # excluded in between
    ],
)
def test_log_none_with_log_also(lines: list[str], expected: str | None) -> None:
    r = parse_rule(with_match(log=[LOG_LINE], log_also=[r"Game start failed"], log_none=[NONE_LINE]))
    assert match_log(r, iter(lines)) == expected


# --------------------------------------------------------------------------- #
# packs
# --------------------------------------------------------------------------- #

def test_parse_pack_minimal() -> None:
    p = parse_pack(pack(rule()))
    assert p.revision == "2026.11.1"
    assert [r.id for r in p.rules] == ["kernel32-missing"]
    assert p.rejected == []


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        "pack",
        {"version": 2, "revision": "2026.11.1", "rules": []},
        pack(format="protonshift-fixes"),
        pack(format=None),
    ],
)
def test_not_a_pack(data: Any) -> None:
    with pytest.raises(PackError, match="not a fix pack"):
        parse_pack(data)


def test_newer_version_rejected_whole() -> None:
    with pytest.raises(PackError, match="newer"):
        parse_pack(pack(rule(), version=PACK_VERSION + 1))


@pytest.mark.parametrize("version", [1, 0, -1, "2", 2.0, True, None])
def test_other_versions_rejected(version: Any) -> None:
    with pytest.raises(PackError, match="version"):
        parse_pack(pack(rule(), version=version))


def test_missing_version_rejected() -> None:
    data = pack(rule())
    del data["version"]
    with pytest.raises(PackError, match="version"):
        parse_pack(data)


@pytest.mark.parametrize(
    "revision",
    ["2026.11", "2026.13.1", "2026.00.1", "26.11.1", "2026.1.1", "2026.11.x", "2026.11.1\n", "", None, 2026],
)
def test_bad_revision(revision: Any) -> None:
    with pytest.raises(PackError, match="revision"):
        parse_pack(pack(revision=revision))


@pytest.mark.parametrize("revision", ["2026.11.0", "2026.01.12", "2027.12.300"])
def test_good_revision(revision: str) -> None:
    assert parse_pack(pack(revision=revision)).revision == revision


@pytest.mark.parametrize("rules", [None, {}, "rules", 3])
def test_rules_must_be_a_list(rules: Any) -> None:
    with pytest.raises(PackError, match="rules"):
        parse_pack(pack(rules=rules))


def test_unknown_pack_field_rejected() -> None:
    with pytest.raises(PackError, match="unknown field 'revison'"):
        parse_pack(pack(revison="2026.11.1"))


def test_bad_rule_does_not_take_good_ones_down() -> None:
    good_a = rule(id="good-a")
    bad = rule(id="bad-one", severity="fatal")
    nameless = {"title": "no id at all"}
    good_b = rule(id="good-b")
    p = parse_pack(pack(good_a, bad, nameless, "not a rule", good_b))
    assert [r.id for r in p.rules] == ["good-a", "good-b"]
    assert [rid for rid, _ in p.rejected] == ["bad-one", "#2", "#3"]
    assert "severity" in dict(p.rejected)["bad-one"]


def test_duplicate_id_later_one_rejected() -> None:
    first = rule(title="First")
    second = rule(title="Second")
    p = parse_pack(pack(first, second))
    assert [r.title for r in p.rules] == ["First"]
    assert p.rejected == [("kernel32-missing", "duplicate id")]


def test_duplicate_id_of_a_rejected_rule_is_still_a_duplicate() -> None:
    p = parse_pack(pack(rule(severity="fatal"), rule()))
    assert p.rules == []
    assert [reason for _, reason in p.rejected][1] == "duplicate id"


def test_parse_pack_does_not_mutate_input() -> None:
    data = pack(rule(), rule(id="other-rule"))
    before = copy.deepcopy(data)
    parse_pack(data)
    assert data == before


# --------------------------------------------------------------------------- #
# load_pack / load_bundled_pack
# --------------------------------------------------------------------------- #

def write(tmp_path: Path, content: str | bytes, name: str = "pack.json") -> Path:
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def test_load_pack_reads_a_file(tmp_path: Path) -> None:
    p = load_pack(write(tmp_path, json.dumps(pack(rule()))))
    assert [r.id for r in p.rules] == ["kernel32-missing"]


def test_load_pack_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PackError, match="cannot read"):
        load_pack(tmp_path / "nope.json")


def test_load_pack_directory(tmp_path: Path) -> None:
    with pytest.raises(PackError):
        load_pack(tmp_path)


@pytest.mark.parametrize("content", ["{ not json", "", "[1, 2"])
def test_load_pack_bad_json(tmp_path: Path, content: str) -> None:
    with pytest.raises(PackError, match="not valid JSON"):
        load_pack(write(tmp_path, content))


def test_load_pack_deeply_nested_json(tmp_path: Path) -> None:
    with pytest.raises(PackError):
        load_pack(write(tmp_path, "[" * 200_000 + "]" * 200_000))


def test_load_pack_not_utf8(tmp_path: Path) -> None:
    with pytest.raises(PackError, match="UTF-8"):
        load_pack(write(tmp_path, b'{"format": "\xff"}'))


def test_load_pack_duplicate_keys(tmp_path: Path) -> None:
    text = json.dumps(pack(rule())).replace('"severity": "blocking"', '"severity": "advice", "severity": "blocking"')
    with pytest.raises(PackError, match="duplicate key 'severity'"):
        load_pack(write(tmp_path, text))


def test_load_pack_size_limit(tmp_path: Path) -> None:
    body = json.dumps(pack(rule()))
    limit = 2 * 1024 * 1024
    at_limit = body[:-1] + " " * (limit - len(body)) + "}"
    assert len(at_limit.encode()) == limit
    assert load_pack(write(tmp_path, at_limit, "at.json")).rules
    with pytest.raises(PackError, match="2 MB"):
        load_pack(write(tmp_path, at_limit + " ", "over.json"))


def test_load_pack_newer_version(tmp_path: Path) -> None:
    with pytest.raises(PackError, match="newer"):
        load_pack(write(tmp_path, json.dumps(pack(version=3))))


def test_load_bundled_pack_never_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fix_pack, "_BUNDLED_PATH", tmp_path / "missing.json")
    p = load_bundled_pack()
    assert p.revision == "" and p.rules == []
    assert len(p.rejected) == 1 and p.rejected[0][0] == "pack"

    monkeypatch.setattr(fix_pack, "_BUNDLED_PATH", write(tmp_path, json.dumps(pack(version=9))))
    p = load_bundled_pack()
    assert p.rejected[0][0] == "pack" and "newer" in p.rejected[0][1]


def test_bundled_pack_is_clean() -> None:
    """CI's guard on the shipped data: every rule in fix_pack.json must load."""
    p = load_bundled_pack()
    problems = [f"{rule_id}: {reason}" for rule_id, reason in p.rejected]
    assert not problems, "bundled fix pack has rejected rules:\n" + "\n".join(problems)
    assert re.fullmatch(r"[0-9]{4}\.[0-9]{2}\.[0-9]+", p.revision), f"bad revision {p.revision!r}"
    for r in p.rules:
        assert r.source.startswith("https://") and len(r.source) > len("https://"), (
            f"{r.id}: source must be an https URL, got {r.source!r}"
        )
        assert r.verified, f"{r.id}: verified date missing"
        assert r.origin == "pack", f"{r.id}: origin {r.origin!r}"
    ids = [r.id for r in p.rules]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"bundled fix pack has duplicate ids: {', '.join(dupes)}"


# --------------------------------------------------------------------------- #
# user_rules
# --------------------------------------------------------------------------- #

@pytest.fixture
def user_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(fixes_mod, "_USER_FIXES_DIR", tmp_path)
    return tmp_path


def write_user(user_dir: Path, app_id: str, entries: Any) -> None:
    (user_dir / f"{app_id}.json").write_text(json.dumps(entries), encoding="utf-8")


def test_user_rules_none_without_a_file(user_dir: Path) -> None:
    assert user_rules("570") == []


def test_user_rules_corrupt_file(user_dir: Path) -> None:
    (user_dir / "570.json").write_text("[ broken", encoding="utf-8")
    assert user_rules("570") == []


def test_user_rules_env_and_launch_arg(user_dir: Path) -> None:
    write_user(user_dir, "570", [
        {"title": "HUD", "description": "Shows fps", "type": "env", "key": "DXVK_HUD", "value": "fps"},
        {"title": "Vulkan", "description": "", "type": "launch_arg", "key": "", "value": " -vulkan "},
    ])
    first, second = user_rules("570")
    assert first.id == "user-1" and second.id == "user-2"
    assert first.origin == second.origin == "user"
    assert first.severity == "advice"
    assert first.app_ids == ("570",)
    assert first.title == "HUD" and first.cause == "Shows fps"
    assert first.source == "" and first.verified == ""
    assert first.log == () and first.log_also == () and first.log_none == ()
    assert first.actions == (Action("env", key="DXVK_HUD", value="fps"),)
    assert second.actions == (Action("user_snippet", value="-vulkan"),)


def test_user_rules_ids_follow_file_position(user_dir: Path) -> None:
    write_user(user_dir, "570", [
        {"title": "bad", "type": "env", "key": "1BAD", "value": "x"},
        "not an entry",
        {"title": "ok", "type": "env", "key": "GOOD", "value": "x"},
    ])
    assert [r.id for r in user_rules("570")] == ["user-3"]


def test_user_rules_values_are_not_held_to_pack_limits(user_dir: Path) -> None:
    write_user(user_dir, "570", [
        {"title": "t", "type": "env", "key": "LD_PRELOAD", "value": "/usr/lib/lib x.so"},
        {"title": "t", "type": "launch_arg", "value": "gamemoderun %command% -dx11"},
    ])
    env, snippet = user_rules("570")
    assert env.actions[0] == Action("env", key="LD_PRELOAD", value="/usr/lib/lib x.so")
    assert snippet.actions[0].value == "gamemoderun %command% -dx11"


@pytest.mark.parametrize(
    "entry",
    [
        {"title": "t", "type": "env", "key": "A", "value": "a\nb"},
        {"title": "t", "type": "env", "key": "A", "value": "a\rb"},
        {"title": "t", "type": "env", "key": "A", "value": "a\0b"},
        {"title": "t", "type": "env", "key": "A B", "value": "1"},
        {"title": "t", "type": "env", "key": "", "value": "1"},
        {"title": "t", "type": "env", "value": "1"},
        {"title": "t", "type": "env", "key": 5, "value": "1"},
        {"title": "t", "type": "env", "key": "A", "value": 1},
        {"title": "t", "type": "launch_arg", "value": "-a\n-b"},
        {"title": "t", "type": "launch_arg", "value": "-a\0"},
        {"title": "t", "type": "launch_arg", "value": "x" * 501},
        {"title": "t", "type": "launch_arg", "value": "   "},
        {"title": "t", "type": "wrapper", "value": "gamemoderun"},
        {"title": 5, "type": "env", "key": "A", "value": "1"},
        {"title": "t", "description": ["x"], "type": "env", "key": "A", "value": "1"},
        ["not", "a", "dict"],
        None,
    ],
)
def test_user_rules_skip_unusable_entries(user_dir: Path, entry: Any) -> None:
    write_user(user_dir, "570", [entry])
    assert user_rules("570") == []


def test_user_rules_entry_without_a_type_is_env(user_dir: Path) -> None:
    # Version 1 read an entry with no type as env.
    write_user(user_dir, "570", [{"title": "t", "key": "DXVK_HUD", "value": "fps"}])
    (only,) = user_rules("570")
    assert only.actions == (Action("env", key="DXVK_HUD", value="fps"),)


def test_user_rules_snippet_cap(user_dir: Path) -> None:
    write_user(user_dir, "570", [{"title": "t", "type": "launch_arg", "value": "x" * 500}])
    assert len(user_rules("570")[0].actions[0].value) == 500


def test_user_rules_text_truncation_and_default_title(user_dir: Path) -> None:
    write_user(user_dir, "570", [
        {"title": "T" * 150, "description": "D" * 500, "type": "env", "key": "A", "value": "1"},
        {"title": "   ", "type": "env", "key": "A", "value": "1"},
        {"type": "env", "key": "A", "value": "1"},
    ])
    long_one, blank, missing = user_rules("570")
    assert long_one.title == "T" * 100 and long_one.cause == "D" * 400
    assert blank.title == missing.title == "Your own fix"
    assert missing.cause == ""


def test_user_rules_only_for_that_game(user_dir: Path) -> None:
    write_user(user_dir, "570", [{"title": "t", "type": "env", "key": "A", "value": "1"}])
    assert user_rules("730") == []
