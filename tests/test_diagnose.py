"""Tests for Diagnose: facts, rule matching, the ranked list, and collect against a tiny fake Steam tree."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import vdf

from protonshift.core import diagnose as dg
from protonshift.core import fix_pack, fixes, gpu, host, steam, system_checks, tool_check
from protonshift.core.diagnose import Facts, Finding, diagnose, proton_build, rule_finding, summarize, to_row
from protonshift.core.fix_pack import Action, parse_rule
from protonshift.core.gpu import GPUInfo
from protonshift.core.launch_check import finding as launch_finding
from protonshift.core.snapshots import GameState
from protonshift.core.system_checks import Check

LOG_LINE = "0024:err:module:import_dll Library d3dcompiler_47.dll not found"
START_FAILED = "0024:err:module:loader_init Importing dlls for L\"C:\\\\game.exe\" failed"


BASE = Facts(
    app_id="100", steam_app=True, native=False, launch_options="%command%", launch_options_readable=True,
    compat_tool="GE-Proton10-12", proton_family="ge", proton_major=10, gpu_vendors=frozenset({"amd"}),
    session="wayland", log_lines=None, log_modified="", log_path="",
)


def facts(**overrides: Any) -> Facts:
    return dataclasses.replace(BASE, **overrides)


def rule(**overrides: Any) -> fix_pack.Rule:
    raw: dict[str, Any] = {
        "id": "test-rule", "title": "A test rule", "cause": "Because of a test.", "severity": "advice",
        "match": {"app_ids": ["100"]}, "actions": [], "source": "https://example.org/issue/1",
        "verified": "2026-11-16",
    }
    raw.update(overrides)
    return parse_rule(raw)


def when_rule(when: dict[str, Any]) -> fix_pack.Rule:
    return rule(match={"app_ids": ["100"], "when": when})


def ids(findings: list[Finding]) -> list[str]:
    return [f.id for f in findings]


# --- proton_build / gpu_vendors / session --------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # found on the machine this was written on: the Arch proton-ge-custom-bin package
        # (also the CompatToolMapping entries in config.vdf)
        ("Proton-GE", ("ge", None)),
        # Steam's own internal names, every one listed in that machine's appinfo.vdf
        ("proton_experimental", ("valve", None)),
        ("proton_hotfix", ("valve", None)),
        ("proton_11", ("valve", 11)),
        ("proton_10", ("valve", 10)),
        ("proton_9", ("valve", 9)),
        ("proton_8", ("valve", 8)),
        ("proton_7", ("valve", 7)),
        ("proton_63", ("valve", 6)),
        ("proton_513", ("valve", 5)),
        ("proton_5", ("valve", 5)),
        ("proton_42", ("valve", 4)),
        ("proton_411", ("valve", 4)),
        ("proton_37", ("valve", 3)),
        ("proton_316", ("valve", 3)),
        # what older ProtonShift builds offered: not a name Steam knows
        ("proton_9_0", ("other", None)),
        ("proton_8_0", ("other", None)),
        # GE builds
        ("GE-Proton10-12", ("ge", 10)),
        ("GE-Proton9-20", ("ge", 9)),
        ("Proton-6.21-GE-2", ("ge", 6)),
        ("proton-ge-custom", ("ge", None)),
        # CachyOS
        ("proton-cachyos-10.0-20250807-slr", ("cachyos", 10)),
        ("proton-cachyos-9.0-20241220-slr-x86_64_v3", ("cachyos", 9)),
        ("proton-cachyos", ("cachyos", None)),
        # never a guessed number
        ("proton_71", ("valve", None)),
        ("proton_07", ("valve", None)),
        ("proton_next", ("other", None)),
        ("GE-Proton9-20-rtsp15", ("other", None)),
        ("luxtorpeda", ("other", None)),
        ("steamlinuxruntime_sniper", ("other", None)),
        ("", ("", None)),
        ("   ", ("", None)),
    ],
)
def test_proton_build(name: str, expected: tuple[str, int | None]) -> None:
    assert proton_build(name) == expected


def test_every_offered_builtin_is_a_valve_name() -> None:
    offered = steam.get_available_proton_tools(None)
    builtin = [name for name in offered if name.startswith("proton_")]
    assert builtin == [
        "proton_experimental", "proton_hotfix", "proton_11", "proton_10", "proton_9", "proton_8", "proton_7",
    ]
    assert all(proton_build(name)[0] == "valve" for name in builtin)


def gpu_info(name: str, driver: str = "") -> GPUInfo:
    return GPUInfo(name=name, driver=driver, vram_mb=None, temperature=None)


def test_gpu_vendors() -> None:
    # nvidia-smi path: product name and a driver version
    assert dg.gpu_vendors([gpu_info("NVIDIA GeForce RTX 4080 Laptop GPU", "615.78.08")]) == {"nvidia"}
    assert dg.gpu_vendors([gpu_info("NVIDIA GPU")]) == {"nvidia"}
    # sysfs path: the kernel driver as the name
    assert dg.gpu_vendors([gpu_info("amdgpu"), gpu_info("i915")]) == {"amd", "intel"}
    mixed = [gpu_info("xe"), gpu_info("nouveau"), gpu_info("radeon")]
    assert dg.gpu_vendors(mixed) == {"intel", "nvidia", "amd"}
    # nothing telling
    assert dg.gpu_vendors([gpu_info("Unknown GPU"), gpu_info("virtio_gpu"), gpu_info("")]) == frozenset()
    assert dg.gpu_vendors([]) == frozenset()


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"XDG_SESSION_TYPE": "wayland"}, "wayland"),
        ({"WAYLAND_DISPLAY": "wayland-1", "DISPLAY": ":0"}, "wayland"),
        ({"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}, "x11"),
        ({"DISPLAY": ":0"}, ""),
        ({}, ""),
    ],
)
def test_session_type(monkeypatch: pytest.MonkeyPatch, env: dict[str, str], expected: str) -> None:
    for key in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert dg.session_type() == expected


# --- when ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("when", "overrides", "expected"),
    [
        ({"gpu_vendor": ["nvidia"]}, {"gpu_vendors": frozenset({"amd", "nvidia"})}, True),
        ({"gpu_vendor": ["nvidia"]}, {"gpu_vendors": frozenset({"amd"})}, False),
        ({"gpu_vendor": ["nvidia"]}, {"gpu_vendors": frozenset()}, False),
        ({"session": ["x11"]}, {"session": "x11"}, True),
        ({"session": ["x11"]}, {"session": "wayland"}, False),
        ({"session": ["x11", "wayland"]}, {"session": ""}, False),
        ({"proton_family": ["ge", "cachyos"]}, {"proton_family": "ge"}, True),
        ({"proton_family": ["valve"]}, {"proton_family": "ge"}, False),
        ({"proton_family": ["other"]}, {"proton_family": ""}, False),
        ({"proton_major_min": 10}, {"proton_major": 10}, True),
        ({"proton_major_min": 10}, {"proton_major": 9}, False),
        ({"proton_major_min": 0}, {"proton_major": None}, False),
        ({"proton_major_max": 9}, {"proton_major": 9}, True),
        ({"proton_major_max": 9}, {"proton_major": 10}, False),
        ({"proton_major_max": 99}, {"proton_major": None}, False),
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "MANGOHUD=1 gamemoderun %command%"}, True),
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "/usr/bin/gamemoderun %command%"}, True),
        ({"launch_has": ["gamemoderun", "mangohud"]}, {"launch_options": "gamemoderun %command%"}, False),
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "%command% gamemoderun"}, False),
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "gamemoderun"}, False),  # no %command%
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "gamemoderun=1 %command%"}, False),
        ({"launch_has": ["gamemoderun"]}, {"launch_options": "gamemoderun %command%",
                                           "launch_options_readable": False}, False),
        ({"env_set": ["PROTON_LOG"]}, {"launch_options": "PROTON_LOG=1 %command%"}, True),
        ({"env_set": ["PROTON_LOG"]}, {"launch_options": "%command% PROTON_LOG=1"}, False),
        ({"env_set": ["PROTON_LOG"]}, {"launch_options": "PROTON_LOG=1"}, False),  # no %command%
        ({"env_set": ["PROTON_LOG"]}, {"launch_options": "PROTON_LOG=1 %command%",
                                       "launch_options_readable": False}, False),
        ({"env_unset": ["PROTON_LOG"]}, {"launch_options": "gamemoderun %command%"}, True),
        ({"env_unset": ["PROTON_LOG"]}, {"launch_options": "PROTON_LOG=1 %command%"}, False),
        ({"env_unset": ["PROTON_LOG"]}, {"launch_options": "PROTON_LOG=1"}, True),  # an argument, not set
        ({"env_unset": ["PROTON_LOG"]}, {"launch_options_readable": False}, False),
        # every listed condition must hold
        ({"gpu_vendor": ["amd"], "session": ["x11"]}, {}, False),
        ({"gpu_vendor": ["amd"], "session": ["wayland"], "proton_family": ["ge"]}, {}, True),
    ],
)
def test_when_holds(when: dict[str, Any], overrides: dict[str, Any], expected: bool) -> None:
    assert dg.when_holds(when_rule(when).when, facts(**overrides)) is expected


def test_an_unset_when_holds() -> None:
    assert dg.when_holds(fix_pack.When(), facts(gpu_vendors=frozenset(), session="", proton_family=""))


# --- rule_finding -----------------------------------------------------------------------------------


def test_app_ids() -> None:
    r = rule(match={"app_ids": ["100", "200"]}, actions=[{"type": "game_arg", "value": "-dx11"}])
    found = rule_finding(r, facts(app_id="200"))
    assert found is not None
    assert (found.id, found.severity, found.origin, found.evidence) == ("test-rule", "advice", "pack", "")
    assert found.actions == (Action("game_arg", value="-dx11"),)
    assert found.source == "https://example.org/issue/1"
    assert rule_finding(r, facts(app_id="300")) is None


def test_log_rule() -> None:
    r = rule(severity="likely", match={"log": [r"Library d3dcompiler_47\.dll not found"]})
    assert rule_finding(r, facts(log_lines=None)) is None
    assert rule_finding(r, facts(log_lines=("nothing here",))) is None
    found = rule_finding(r, facts(log_lines=("start", "  " + LOG_LINE + "  ", "end")))
    assert found is not None
    assert (found.origin, found.evidence, found.severity) == ("log", LOG_LINE, "likely")


def test_log_also() -> None:
    r = rule(severity="blocking", match={
        "log": [r"Library d3dcompiler_47\.dll not found"], "log_also": [r"loader_init Importing dlls"],
    })
    assert rule_finding(r, facts(log_lines=(LOG_LINE,))) is None
    found = rule_finding(r, facts(log_lines=(LOG_LINE, START_FAILED)))
    assert found is not None and found.evidence == LOG_LINE


def test_log_rule_with_when_and_app_ids() -> None:
    r = rule(severity="likely", match={
        "app_ids": ["100"],
        "log": [r"Library d3dcompiler_47\.dll not found"],
        "when": {"gpu_vendor": ["amd"]},
    })
    lines = (LOG_LINE,)
    assert rule_finding(r, facts(log_lines=lines)) is not None
    assert rule_finding(r, facts(log_lines=lines, gpu_vendors=frozenset({"intel"}))) is None
    assert rule_finding(r, facts(log_lines=lines, app_id="1")) is None


def test_native_games_skip_proton_rules() -> None:
    lines = (LOG_LINE,)
    log_rule = rule(severity="likely", match={"log": [r"Library d3dcompiler_47\.dll not found"]})
    proton_rule = rule(match={"app_ids": ["100"], "when": {"proton_family": ["ge"]}})
    word_rule = rule(match={"when": {"launch_has": ["gamemoderun"]}})
    native = {"native": True, "log_lines": lines, "launch_options": "gamemoderun %command%"}
    assert rule_finding(log_rule, facts(**native)) is None
    assert rule_finding(proton_rule, facts(**native)) is None
    assert rule_finding(word_rule, facts(**native)) is not None
    assert rule_finding(proton_rule, facts()) is not None


def test_evidence_is_the_setting_that_matched() -> None:
    word = rule(match={"when": {"launch_has": ["gamemoderun"], "env_set": ["PROTON_LOG"]}})
    line = "PROTON_LOG=1 /usr/bin/gamemoderun mangohud %command% -x"
    found = rule_finding(word, facts(launch_options=line))
    assert found is not None and found.evidence == "/usr/bin/gamemoderun PROTON_LOG=1"
    build = rule(match={"app_ids": ["100"], "when": {"proton_major_max": 10}})
    found = rule_finding(build, facts())
    assert found is not None and found.evidence == "GE-Proton10-12"


def test_user_rules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fixes, "_USER_FIXES_DIR", tmp_path)
    (tmp_path / "100.json").write_text(json.dumps([
        {"title": "Use DX11", "description": "Runs better for me.", "type": "launch_arg", "value": "-dx11"},
        {"title": "HUD", "description": "", "type": "env", "key": "DXVK_HUD", "value": "fps"},
    ]), encoding="utf-8")
    found = [rule_finding(r, facts()) for r in fix_pack.user_rules("100")]
    assert [(f.id, f.origin, f.severity) for f in found if f] == [("user-1", "user", "advice"),
                                                                   ("user-2", "user", "advice")]
    assert found[0] is not None and found[0].actions == (Action("user_snippet", value="-dx11"),)
    assert all(rule_finding(r, facts(app_id="7")) is None for r in fix_pack.user_rules("100"))


# --- diagnose -------------------------------------------------------------------------------------------


def check(cid: str, state: str) -> Check:
    fix = f"fix for {cid}" if state == "problem" else ""
    return Check(cid, state, f"{cid} {state}", f"detail of {cid}", fix)


def test_severity_mapping_and_order() -> None:
    launch = [
        launch_finding("ok", "Game files are present", id="install-ok"),
        launch_finding("info", "Using Steam's default Proton", id="proton-default"),
        launch_finding("warn", "MangoHud isn't installed", "MANGOHUD=1 is set.", "Install it.",
                       id="env-needs-mangohud", actions=(Action("unset_env", key="MANGOHUD"),)),
        launch_finding("error", "%command% appears more than once", id="command-twice",
                       actions=(Action("single_command"),)),
        launch_finding("error", "The chosen Proton build is gone", id="proton-gone",
                       actions=(Action("default_proton"),)),
    ]
    checks = [check("vulkan", "problem"), check("vulkan-32bit", "problem"), check("disk-library", "ok"),
              check("disk-prefix", "unknown")]
    rules = [rule(id="advice-one"), rule(id="likely-one", severity="likely",
                                         match={"when": {"launch_has": ["gamemoderun"]}})]
    found = diagnose(facts(launch_options="MANGOHUD=1 gamemoderun %command% %command%"),
                     rules=rules, launch_findings=launch, checks=checks)
    assert [(f.id, f.severity, f.origin) for f in found] == [
        ("command-twice", "blocking", "check"),
        ("proton-gone", "blocking", "check"),
        ("vulkan", "blocking", "system"),
        ("env-needs-mangohud", "likely", "check"),
        ("likely-one", "likely", "pack"),
        ("vulkan-32bit", "likely", "system"),
        ("advice-one", "advice", "pack"),
        ("proton-default", "context", "check"),
        ("log-off", "context", "log"),
        ("disk-prefix", "context", "system"),
        ("install-ok", "ok", "check"),
        ("disk-library", "ok", "system"),
    ]
    by_id = {f.id: f for f in found}
    assert by_id["env-needs-mangohud"].cause == "MANGOHUD=1 is set."
    assert by_id["env-needs-mangohud"].fix == "Install it."
    assert by_id["env-needs-mangohud"].evidence == "MANGOHUD=1 gamemoderun %command% %command%"
    assert by_id["proton-gone"].evidence == "GE-Proton10-12"
    assert by_id["vulkan"].fix == "fix for vulkan"
    assert by_id["likely-one"].evidence == "gamemoderun"
    assert summarize(found) == "3 problems that will stop the game from starting, 3 more worth a look."


def test_native_games() -> None:
    launch = [
        launch_finding("error", "The chosen Proton build is gone", id="proton-gone"),
        launch_finding("info", "No Proton prefix yet", id="prefix-none"),
        launch_finding("warn", "Proton EasyAntiCheat Runtime isn't installed", id="anticheat-missing-eac"),
        launch_finding("ok", "Game files are present", id="install-ok"),
    ]
    checks = [check("vulkan", "problem"), check("disk-prefix", "problem"), check("disk-library", "ok")]
    found = diagnose(facts(native=True, proton_family="", proton_major=None, log_lines=("err: x",)),
                     rules=[], launch_findings=launch, checks=checks)
    assert [(f.id, f.severity) for f in found] == [("vulkan", "likely"), ("install-ok", "ok"),
                                                   ("disk-library", "ok")]


def test_dedup_keeps_the_first() -> None:
    launch = [launch_finding("error", "From the check", id="command-twice")]
    rules = [rule(id="command-twice", severity="advice"), rule(id="twice-here", title="first"),
             rule(id="twice-here", title="second")]
    found = diagnose(facts(), rules=rules, launch_findings=launch, checks=[])
    assert ids(found).count("command-twice") == 1
    assert next(f for f in found if f.id == "command-twice").origin == "check"
    assert [f.title for f in found if f.id == "twice-here"] == ["first"]


def test_a_launch_finding_without_id_still_gets_one() -> None:
    found = diagnose(facts(), rules=[], launch_findings=[{"level": "warn", "title": "Old style"}], checks=[])
    assert "check-0" in ids(found)


# --- log rows ---------------------------------------------------------------------------------------------


def log_rows(f: Facts, rules: list[fix_pack.Rule] | None = None) -> list[Finding]:
    found = diagnose(f, rules=rules or [], launch_findings=[], checks=[])
    return [x for x in found if x.id.startswith("log-")]


def test_no_log_offers_to_turn_logging_on() -> None:
    (row,) = log_rows(facts(launch_options="gamemoderun %command%"))
    assert (row.id, row.severity, row.origin) == ("log-off", "context", "log")
    assert row.actions == (Action("env", key="PROTON_LOG", value="1"),)
    (row,) = log_rows(facts(launch_options_readable=False))
    assert row.id == "log-off" and row.actions == ()


def test_no_log_while_logging_is_on() -> None:
    (row,) = log_rows(facts(launch_options="PROTON_LOG=1 %command%"))
    assert row.id == "log-waiting"
    assert "run the game once, then diagnose again" in row.cause.lower()
    assert row.actions == ()


def test_no_log_rows_for_shortcuts_without_a_log_or_native_games() -> None:
    assert log_rows(facts(steam_app=False)) == []
    assert log_rows(facts(native=True)) == []
    assert log_rows(facts(native=True, log_lines=("err: x",))) == []


def test_a_log_says_which_and_when() -> None:
    f = facts(log_lines=("all fine",), log_modified="2026-11-16 01:23", log_path="/home/u/steam-100.log",
              launch_options="PROTON_LOG=1 %command%")
    (row,) = log_rows(f)
    assert row.id == "log-read" and row.severity == "context"
    # The path is the evidence; the sentence names only when the log was written.
    assert "/home/u/steam-100.log" not in row.cause and "2026-11-16 01:23" in row.cause
    assert "2026-11-16 01:23" in row.title
    assert row.evidence == "/home/u/steam-100.log"
    assert "earlier run" not in row.cause
    (row,) = log_rows(dataclasses.replace(f, launch_options="%command%"))
    assert "Logging is off now" in row.cause


def test_unrecognised_problem_lines() -> None:
    lines = ("fine", LOG_LINE, "wine: Unhandled page fault on read access", "fine again")
    rows = log_rows(facts(log_lines=lines))
    assert ids(rows) == ["log-read", "log-unrecognised"]
    assert rows[1].title.startswith("2 lines in the log look like problems")
    assert rows[1].evidence == LOG_LINE
    one = log_rows(facts(log_lines=(LOG_LINE,)))
    assert one[1].title.startswith("1 line in the log looks like a problem")
    # a log rule that recognised a line takes its place
    known = rule(severity="likely", match={"log": [r"Library d3dcompiler_47\.dll not found"]})
    assert ids(log_rows(facts(log_lines=lines), [known])) == ["log-read"]
    # nothing that looks like a problem: no row
    assert ids(log_rows(facts(log_lines=("fine",)))) == ["log-read"]


# --- rows and summary ---------------------------------------------------------------------------------------


def test_to_row() -> None:
    f = Finding("x", "likely", "T", "C", "E", "F", "https://example.org", "pack",
                (Action("manual", text="Install it."), Action("env", key="A", value="1")))
    row = to_row(f)
    assert row == {
        "id": "x", "severity": "likely", "title": "T", "cause": "C", "evidence": "E", "fix": "F",
        "source": "https://example.org", "origin": "pack", "manual": ["Install it."], "canApply": True,
    }
    assert all(isinstance(v, (str, bool, list)) for v in row.values())
    manual_only = to_row(dataclasses.replace(f, actions=(Action("manual", text="Do it."),)))
    assert manual_only["canApply"] is False and manual_only["manual"] == ["Do it."]
    assert to_row(dataclasses.replace(f, actions=()))["canApply"] is False


def sev(*severities: str) -> list[Finding]:
    return [Finding(str(i), s, "", "", "", "", "", "pack", ()) for i, s in enumerate(severities)]


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        (("blocking", "blocking", "likely", "ok"),
         "2 problems that will stop the game from starting, 1 more worth a look."),
        (("blocking",), "1 problem that will stop the game from starting."),
        (("likely", "context"), "Nothing blocks the launch. 1 thing worth a look."),
        (("likely", "likely"), "Nothing blocks the launch. 2 things worth a look."),
        (("advice", "ok"), "No problems found. 1 suggestion you can try."),
        (("context", "ok"), "No problems found."),
        ((), "No problems found."),
    ],
)
def test_summarize(severities: tuple[str, ...], expected: str) -> None:
    assert summarize(sev(*severities)) == expected


# --- collect ----------------------------------------------------------------------------------------------


APP = "100"


@pytest.fixture
def fake_steam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    home = tmp_path / "home"
    root = tmp_path / "steam"
    (root / "steamapps").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "userdata" / "12345" / "config").mkdir(parents=True)
    game = tmp_path / "game"
    game.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    user_fixes = tmp_path / "fixes"
    user_fixes.mkdir()
    localconfig = root / "userdata" / "12345" / "config" / "localconfig.vdf"
    config_vdf = root / "config" / "config.vdf"
    write_steam(localconfig, config_vdf, "gamemoderun %command%", "GE-Proton9-20")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PROTON_LOG_DIR", str(logs))
    monkeypatch.setenv("XDG_DATA_DIRS", "")
    monkeypatch.setattr(steam, "STEAM_ROOTS", [root])
    steam.invalidate_discovery_cache()
    monkeypatch.setattr(fixes, "_USER_FIXES_DIR", user_fixes)
    monkeypatch.setattr(tool_check, "is_tool_available", lambda _name: False)
    monkeypatch.setattr(gpu, "get_gpu_info", lambda: [gpu_info("amdgpu")])
    monkeypatch.setattr(system_checks, "run_checks", lambda **_kw: [check("vulkan", "ok")])
    monkeypatch.setattr(host, "host_run", lambda *_a, **_kw: subprocess.CompletedProcess([], 1, "", ""))
    yield {"root": root, "game": game, "logs": logs, "fixes": user_fixes,
           "localconfig": localconfig, "config_vdf": config_vdf}
    steam.invalidate_discovery_cache()


def write_steam(localconfig: Path, config_vdf: Path, options: str, tool: str) -> None:
    apps = {APP: {"LaunchOptions": options}}
    local = {"UserLocalConfigStore": {"Software": {"Valve": {"Steam": {"apps": apps}}}}}
    mapping = {APP: {"name": tool, "config": "", "priority": "250"}} if tool else {}
    config = {"InstallConfigStore": {"Software": {"Valve": {"Steam": {"CompatToolMapping": mapping}}}}}
    localconfig.write_text(vdf.dumps(local, pretty=True), encoding="utf-8")
    config_vdf.write_text(vdf.dumps(config, pretty=True), encoding="utf-8")


def test_collect_a_steam_game(fake_steam: dict[str, Path]) -> None:
    (fake_steam["logs"] / f"steam-{APP}.log").write_text(f"start\n{LOG_LINE}\nend\n", encoding="utf-8")
    (fake_steam["fixes"] / f"{APP}.json").write_text(json.dumps(
        [{"title": "Use DX11", "description": "", "type": "launch_arg", "value": "-dx11"}]), encoding="utf-8")
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=False, protondb_tier="")
    found = {f.id: f for f in report.findings}
    assert {"wrapper-missing-gamemoderun", "proton-gone", "log-read", "log-unrecognised", "user-1",
            "prefix-none", "vulkan"} <= set(found)
    assert found["wrapper-missing-gamemoderun"].actions == (Action("remove_word", value="gamemoderun"),)
    assert found["log-unrecognised"].evidence == LOG_LINE
    assert report.summary.startswith("2 problems that will stop the game from starting")
    assert report.state == GameState("gamemoderun %command%", "GE-Proton9-20")
    assert report.can_apply is True
    assert report.steam_running is False
    assert report.log_path == str(fake_steam["logs"] / f"steam-{APP}.log")
    assert report.paths == (fake_steam["localconfig"], fake_steam["config_vdf"])
    assert report.findings[0].severity == "blocking"


def test_collect_never_reports_a_valve_build_as_gone(fake_steam: dict[str, Path]) -> None:
    write_steam(fake_steam["localconfig"], fake_steam["config_vdf"], "", "proton_9")
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=False, protondb_tier="")
    found = {f.id for f in report.findings}
    assert "proton-ok" in found and "proton-gone" not in found
    assert "log-off" in found


@pytest.mark.parametrize("tool", ["proton_9", "proton_experimental", "proton_hotfix", "proton_63"])
def test_collect_counts_any_valve_build_as_available(fake_steam: dict[str, Path], tool: str) -> None:
    write_steam(fake_steam["localconfig"], fake_steam["config_vdf"], "", tool)
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=False, protondb_tier="")
    assert "proton-gone" not in {f.id for f in report.findings}


def test_collect_reports_a_name_steam_does_not_know(fake_steam: dict[str, Path]) -> None:
    # Older ProtonShift builds wrote proton_9_0, which Steam never used.
    write_steam(fake_steam["localconfig"], fake_steam["config_vdf"], "", "proton_9_0")
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=False, protondb_tier="")
    gone = next(f for f in report.findings if f.id == "proton-gone")
    assert gone.severity == "blocking"
    assert gone.actions == (Action("default_proton"),)


def test_collect_a_shortcut(fake_steam: dict[str, Path]) -> None:
    report = dg.collect("3000000000", install_path=str(fake_steam["game"]), prefix_path="",
                        shortcut_options="mangohud %command%", native=False, protondb_tier="")
    assert report.state is None and report.can_apply is False
    found = {f.id for f in report.findings}
    assert "wrapper-missing-mangohud" in found
    assert not any(fid.startswith("log-") for fid in found)


def test_collect_a_native_game(fake_steam: dict[str, Path]) -> None:
    (fake_steam["logs"] / f"steam-{APP}.log").write_text(LOG_LINE + "\n", encoding="utf-8")
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=True, protondb_tier="")
    found = {f.id for f in report.findings}
    assert not any(fid.startswith(("proton-", "prefix-", "anticheat-", "log-")) for fid in found)
    assert report.log_path == ""
    assert report.can_apply is True


def test_collect_without_steam(fake_steam: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(steam, "STEAM_ROOTS", [])
    steam.invalidate_discovery_cache()
    report = dg.collect(APP, install_path="", prefix_path="", shortcut_options=None, native=False,
                        protondb_tier="")
    found = {f.id for f in report.findings}
    assert {"launch-unreadable", "install-missing"} <= found
    assert report.state is None and report.can_apply is False
    assert report.paths == (None, None)


def test_collect_survives_failing_helpers(
    fake_steam: dict[str, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_a: object, **_kw: object) -> None:
        raise RuntimeError("broken")

    monkeypatch.setattr(gpu, "get_gpu_info", boom)
    monkeypatch.setattr(system_checks, "run_checks", boom)
    monkeypatch.setattr(host, "host_run", boom)
    report = dg.collect(APP, install_path=str(fake_steam["game"]), prefix_path="", shortcut_options=None,
                        native=False, protondb_tier="")
    assert report.steam_running is None
    assert "wrapper-missing-gamemoderun" in {f.id for f in report.findings}
