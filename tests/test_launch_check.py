"""Tests for the launch check and the Proton log reader (pure logic, temp dirs)."""

from __future__ import annotations

from pathlib import Path

import pytest

from protonshift.core import proton_log
from protonshift.core.fix_pack import Action
from protonshift.core.launch_check import check_launch, check_launch_options, detect_anticheat, summarize


def levels(findings: list[dict[str, str]]) -> list[str]:
    return [f["level"] for f in findings]


def titles(findings: list[dict[str, str]]) -> str:
    return " | ".join(f["title"] for f in findings)


def has(_name: str) -> bool:
    return True


def lacks(_name: str) -> bool:
    return False


# --- launch options -----------------------------------------------------------


def test_empty_and_plain_options_pass() -> None:
    assert levels(check_launch_options("", lacks)) == ["ok"]
    assert levels(check_launch_options("-novid -fullscreen", lacks)) == ["ok"]
    assert levels(check_launch_options("MANGOHUD=1 gamemoderun %command% -novid", has)) == ["ok"]


def test_missing_command_placeholder() -> None:
    found = check_launch_options("gamemoderun", has)
    assert levels(found) == ["error"]
    assert "no %command%" in found[0]["title"]
    assert "gamemoderun %command%" in found[0]["fix"]
    assert levels(check_launch_options("PROTON_LOG=1", has)) == ["error"]


def test_duplicate_command_placeholder() -> None:
    assert "more than once" in titles(check_launch_options("gamemoderun %command% %command%", has))


def test_missing_tools() -> None:
    found = check_launch_options("MANGOHUD=1 gamemoderun gamescope -f -- %command%", lacks)
    assert levels(found) == ["warn", "error", "error"]
    assert "MangoHud isn't installed" in titles(found)
    assert "GameMode isn't installed" in titles(found)
    assert "gamescope isn't installed" in titles(found)


def test_tool_named_after_command_is_a_game_argument() -> None:
    # after %command% everything belongs to the game, whatever it is called
    assert levels(check_launch_options("%command% gamescope", lacks)) == ["ok"]


# --- whole check -----------------------------------------------------------------


def run(tmp_path: Path, **overrides) -> list[dict[str, str]]:
    install = tmp_path / "game"
    install.mkdir(exist_ok=True)
    args = dict(
        launch_options="", launch_options_readable=True, compat_tool="", available_tools=["", "GE-Proton10-1"],
        install_path=install, prefix_path=None, installed_app_ids=[], tool_exists=has, protondb_tier="",
    )
    args.update(overrides)
    return check_launch(**args)


def test_healthy_game(tmp_path: Path) -> None:
    found = run(tmp_path)
    assert "error" not in levels(found)
    assert "warn" not in levels(found)
    assert summarize(found) == "No problems found."


def test_removed_proton_build(tmp_path: Path) -> None:
    found = run(tmp_path, compat_tool="GE-Proton9-20")
    assert found[0]["level"] == "error"
    assert "GE-Proton9-20" in found[0]["title"]
    assert "1 problem that will stop" in summarize(found)
    assert "Proton build is installed" in titles(run(tmp_path, compat_tool="GE-Proton10-1"))


def test_missing_install_folder(tmp_path: Path) -> None:
    assert "install folder is missing" in titles(run(tmp_path, install_path=tmp_path / "gone"))


def test_anticheat_runtime(tmp_path: Path) -> None:
    install = tmp_path / "game"
    (install / "Binaries" / "EasyAntiCheat").mkdir(parents=True)
    (install / "BattlEye").mkdir()
    assert detect_anticheat(install) == {"eac", "battleye"}
    found = run(tmp_path)
    assert "Proton EasyAntiCheat Runtime isn't installed" in titles(found)
    assert "Proton BattlEye Runtime isn't installed" in titles(found)
    assert "2 things worth a look" in summarize(found)
    fixed = run(tmp_path, installed_app_ids=["1826330", "1161040"])
    assert "warn" not in levels(fixed)


def test_anticheat_scan_is_shallow(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "d" / "EasyAntiCheat"
    deep.mkdir(parents=True)
    assert detect_anticheat(tmp_path) == set()


def test_protondb_and_unreadable_options(tmp_path: Path) -> None:
    assert "Borked" in titles(run(tmp_path, protondb_tier="Borked"))
    found = run(tmp_path, launch_options_readable=False)
    assert "Couldn't read the launch options" in titles(found)
    # most serious first
    assert levels(found) == sorted(levels(found), key=["error", "warn", "info", "ok"].index)


# --- ids and actions -------------------------------------------------------------


def by_id(findings: list[dict]) -> dict[str, dict]:
    return {f["id"]: f for f in findings}


@pytest.mark.parametrize(
    ("options", "exists", "fid", "actions"),
    [
        ("", lacks, "launch-empty", ()),
        ("-novid", lacks, "launch-ok", ()),
        ("gamemoderun %command% %command%", has, "command-twice", (Action("single_command"),)),
        ("gamemoderun -novid", has, "command-missing", (Action("add_command"),)),
        # no leading wrapper to put %command% after: no button that would do nothing
        ("-novid gamemoderun", has, "command-missing", ()),
        ("gamemoderun %command%", lacks, "wrapper-missing-gamemoderun",
         (Action("remove_word", value="gamemoderun"),)),
        ("/usr/bin/prime-run %command%", lacks, "wrapper-missing-prime-run",
         (Action("remove_word", value="prime-run"),)),
        ("MANGOHUD=1 %command%", lacks, "env-needs-mangohud", (Action("unset_env", key="MANGOHUD"),)),
    ],
)
def test_option_findings_have_ids_and_actions(options: str, exists, fid: str, actions: tuple) -> None:
    found = by_id(check_launch_options(options, exists))
    assert fid in found
    assert found[fid]["actions"] == actions


def test_every_finding_has_a_stable_id(tmp_path: Path) -> None:
    install = tmp_path / "game"
    (install / "EasyAntiCheat").mkdir(parents=True)
    prefix = tmp_path / "pfx"
    prefix.mkdir()
    found = run(tmp_path, compat_tool="GE-Proton9-20", prefix_path=prefix, protondb_tier="bronze",
                launch_options="gamemoderun %command% %command%", tool_exists=lacks)
    ids = [f["id"] for f in found]
    assert all(ids) and len(ids) == len(set(ids))
    assert {"install-ok", "proton-gone", "anticheat-missing-eac", "prefix-ok", "protondb-bronze",
            "command-twice", "wrapper-missing-gamemoderun"} <= set(ids)
    assert by_id(found)["proton-gone"]["actions"] == (Action("default_proton"),)
    again = run(tmp_path, compat_tool="GE-Proton9-20", prefix_path=prefix, protondb_tier="bronze",
                launch_options="gamemoderun %command% %command%", tool_exists=lacks)
    assert ids == [f["id"] for f in again]

    other = by_id(run(tmp_path, install_path=tmp_path / "gone", compat_tool="GE-Proton10-1",
                      launch_options_readable=False, protondb_tier="borked", installed_app_ids=["1826330"]))
    expected = {"install-missing", "launch-unreadable", "proton-ok", "prefix-none", "protondb-borked"}
    assert expected <= set(other)
    assert by_id(run(tmp_path))["proton-default"]["actions"] == ()
    assert "anticheat-ok-eac" in by_id(run(tmp_path, installed_app_ids=["1826330"]))


def test_findings_keep_their_old_keys(tmp_path: Path) -> None:
    for f in run(tmp_path, compat_tool="GE-Proton9-20"):
        assert {"level", "title", "detail", "fix", "id", "actions"} <= set(f)
        assert isinstance(f["actions"], tuple)


# --- Proton log --------------------------------------------------------------------


def test_log_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROTON_LOG_DIR", str(tmp_path))
    assert proton_log.log_path("1091500") == tmp_path / "steam-1091500.log"
    assert proton_log.log_path("../../etc") is None
    assert proton_log.log_path("") is None
    monkeypatch.delenv("PROTON_LOG_DIR")
    assert proton_log.log_path("7") == Path.home() / "steam-7.log"


@pytest.mark.parametrize(
    ("options", "expected"),
    [("PROTON_LOG=1 %command%", True), ("gamemoderun %command%", False), ("", False),
     ("PROTON_LOG=0 %command%", False), ("MY_PROTON_LOG=1 %command%", False)],
)
def test_logging_enabled(options: str, expected: bool) -> None:
    assert proton_log.logging_enabled(options) is expected


def test_read_tail(tmp_path: Path) -> None:
    path = tmp_path / "steam-1.log"
    lines = [f"line {i}" for i in range(50)]
    lines[10] = "0124:err:module:import_dll Library steam_api64.dll not found"
    lines[40] = "wine: Unhandled page fault on read access"
    path.write_text("\n".join(lines), encoding="utf-8")

    whole = proton_log.read_tail(path)
    assert (whole.truncated, whole.problem_count) == (False, 2)
    assert whole.text.splitlines()[-1] == "line 49"

    only = proton_log.read_tail(path, problems_only=True)
    assert only.text.splitlines() == [lines[10], lines[40]]

    short = proton_log.read_tail(path, max_lines=5)
    assert short.truncated
    assert short.text.splitlines() == lines[-5:]

    tiny = proton_log.read_tail(path, max_bytes=60)
    assert tiny.truncated
    assert tiny.text.splitlines()[-1] == "line 49"
    assert not tiny.text.startswith("ine")  # the cut first line is dropped


def test_read_tail_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        proton_log.read_tail(tmp_path / "absent.log")


def test_old_protonshift_build_name_is_explained_not_called_uninstalled(tmp_path):
    # proton_9_0 is a name ProtonShift up to 1.3.2 wrote; Steam's is proton_9.
    rows = run(tmp_path, compat_tool="proton_9_0", available_tools=["", "proton_9"])
    gone = next(f for f in rows if f["id"] == "proton-gone")
    assert "Older versions of ProtonShift" in gone["detail"]
    assert "reinstall" not in gone["fix"]
    removed = next(f for f in run(tmp_path, compat_tool="GE-Proton9-1", available_tools=[""])
                   if f["id"] == "proton-gone")
    assert "no longer installed" in removed["detail"]
