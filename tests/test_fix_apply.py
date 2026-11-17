"""Tests for planning, applying and undoing Diagnose fixes (pure logic plus VDF files under tmp_path)."""

from __future__ import annotations

from pathlib import Path

import pytest
import vdf

from protonshift.core import fix_apply, snapshots
from protonshift.core.fix_apply import Change, apply_change, plan, read_state, undo_available, undo_latest
from protonshift.core.fix_pack import Action
from protonshift.core.snapshots import GameState

APP = "1091500"


def state(options: str = "", tool: str = "") -> GameState:
    return GameState(launch_options=options, compat_tool=tool)


# --- plan -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("action", "before", "after"),
    [
        (Action("env", key="PROTON_LOG", value="1"), state("gamemoderun %command%"),
         state("PROTON_LOG=1 gamemoderun %command%")),
        (Action("unset_env", key="MANGOHUD"), state("MANGOHUD=1 %command% -novid"),
         state("%command% -novid")),
        (Action("game_arg", value="-vulkan"), state(""), state("%command% -vulkan")),
        (Action("remove_word", value="gamemoderun"), state("gamemoderun mangohud %command%"),
         state("mangohud %command%")),
        (Action("default_proton"), state("%command% -x", "GE-Proton9-20"), state("%command% -x", "")),
        (Action("single_command"), state("%command% %command% -x"), state("%command% -x")),
        (Action("add_command"), state("gamemoderun -novid"), state("gamemoderun %command% -novid")),
        # the user's own launch_arg: with %command% it is merged like any snippet ...
        (Action("user_snippet", value="gamemoderun %command%"), state("%command% -novid"),
         state("gamemoderun %command% -novid")),
        # ... and without it, it is game arguments
        (Action("user_snippet", value="-dx11 -windowed"), state("gamemoderun %command%"),
         state("gamemoderun %command% -dx11 -windowed")),
    ],
)
def test_plan_each_action(action: Action, before: GameState, after: GameState) -> None:
    change = plan([action], before, user=action.type == "user_snippet")
    assert change == Change(before=before, after=after, manual=(), blocked="")
    assert change.changed


def test_plan_manual_changes_nothing() -> None:
    change = plan([Action("manual", text="Install the 32-bit Vulkan driver."),
                   Action("manual", text="Then restart the computer.")], state("%command%"))
    assert not change.changed
    assert change.manual == ("Install the 32-bit Vulkan driver.", "Then restart the computer.")
    assert change.blocked == ""


def test_plan_applies_actions_in_order() -> None:
    change = plan([
        Action("remove_word", value="gamemoderun"),
        Action("env", key="DXVK_ASYNC", value="1"),
        Action("manual", text="Verify the game files."),
        Action("default_proton"),
    ], state("gamemoderun %command%", "GE-Proton9-1"))
    assert change.after == state("DXVK_ASYNC=1 %command%", "")
    assert change.manual == ("Verify the game files.",)


def test_plan_that_changes_nothing() -> None:
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], state("DXVK_ASYNC=1 %command%"))
    assert not change.changed
    assert change.blocked == ""


@pytest.mark.parametrize(
    "value",
    ["a b", "'x'", '"x"', "a;b", "$(id)", "`id`", "a|b", "%command%", "x%command%y", "a" * 201],
)
def test_plan_refuses_an_env_value_outside_the_pack_characters(value: str) -> None:
    before = state("%command%")
    actions = [Action("env", key="DXVK_HUD", value=value), Action("manual", text="Or do it by hand.")]
    change = plan(actions, before)
    assert "characters ProtonShift will not write" in change.blocked
    assert change.after == before and not change.changed
    assert change.manual == ("Or do it by hand.",)


@pytest.mark.parametrize("key", ["LD_PRELOAD", "PATH", "STEAM_COMPAT_DATA_PATH", "A B", "", "1A"])
def test_plan_refuses_keys_it_must_not_touch(key: str) -> None:
    for kind in ("env", "unset_env"):
        change = plan([Action(kind, key=key, value="1")], state("%command%"))
        assert change.blocked
        assert not change.changed


def test_plan_refuses_unknown_and_malformed_actions() -> None:
    assert "does not know" in plan([Action("run_script", value="x")], state()).blocked
    assert plan([Action("game_arg", value="-a -b")], state()).blocked
    assert plan([Action("remove_word", value="../x")], state()).blocked
    assert plan([Action("user_snippet", value="   ")], state(), user=True).blocked
    # A snippet of free text only ever comes from the user's own fix.
    assert "does not know" in plan([Action("user_snippet", value="-dx11")], state()).blocked


# --- the user's own fixes (docs/fix-pack.md, "User fixes") ----------------------------------


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("DXVK_HUD", "fps", "DXVK_HUD=fps %command%"),
        ("WINEDLLOVERRIDES", "d3d9=n;dinput8=n,b", "WINEDLLOVERRIDES='d3d9=n;dinput8=n,b' %command%"),
        ("MY_VAR", "a b", "MY_VAR='a b' %command%"),
        ("LD_PRELOAD", "/usr/lib/lib x.so", "LD_PRELOAD='/usr/lib/lib x.so' %command%"),
        ("A", "$(id)", "A='$(id)' %command%"),
        ("A", "", "A= %command%"),
    ],
)
def test_plan_user_env_is_single_quoted(key: str, value: str, expected: str) -> None:
    change = plan([Action("env", key=key, value=value)], state(""), user=True)
    assert change.blocked == ""
    assert change.after == state(expected)
    # Applying it again changes nothing.
    assert not plan([Action("env", key=key, value=value)], change.after, user=True).changed


@pytest.mark.parametrize(
    ("value", "fragment"),
    [("it's", "single quote"), ("a\nb", "line break"), ("a\x00b", "line break"),
     ("x %command% y", "%command%")],
)
def test_plan_user_env_refuses_what_quoting_cannot_make_safe(value: str, fragment: str) -> None:
    change = plan([Action("env", key="DXVK_HUD", value=value)], state("%command%"), user=True)
    assert fragment in change.blocked
    assert not change.changed


def test_plan_holds_actions_that_are_not_the_users_to_the_pack_limits() -> None:
    # The pack loader refuses these too; plan() refuses them again for any
    # action that is not the user's own (defence in depth).
    for key in ("BASH_ENV", "WINEDLLOVERRIDES", "SDL_DYNAMIC_API", "A"):
        assert plan([Action("env", key=key, value="1")], state("%command%")).blocked, key
    assert "characters" in plan([Action("env", key="DXVK_HUD", value="a b")], state("%command%")).blocked
    # unset_env is not limited to the families, only by the forbidden list.
    assert plan([Action("unset_env", key="MY_VAR")], state("MY_VAR=1 %command%")).after == state("")
    assert plan([Action("unset_env", key="WINEDLLOVERRIDES")], state("%command%")).blocked
    # The engine's own "turn logging on" row still plans.
    change = plan([Action("env", key="PROTON_LOG", value="1")], state(""))
    assert change.blocked == "" and change.after == state("PROTON_LOG=1 %command%")


def test_plan_refuses_a_line_break() -> None:
    for value in ("-a\n-b", '-a "x\ny"', "-a\r", "-a\x00"):
        change = plan([Action("user_snippet", value=value)], state("%command%"), user=True)
        assert "line break" in change.blocked
        assert not change.changed
    assert plan([Action("env", key="DXVK_ASYNC", value="a\nb")], state("%command%")).blocked
    # one already inside a quoted part of the line survives splitting, and is refused too
    change = plan([Action("game_arg", value="-x")], state('FOO="a\nb" %command%'))
    assert "line break" in change.blocked
    # A blocked step stops later steps, so the result is never a half-applied plan.
    change = plan([Action("env", key="DXVK_ASYNC", value="b c"), Action("default_proton")],
                  state("%command%", "x"))
    assert change.after == state("%command%", "x")


# --- disk helpers ------------------------------------------------------------------------


@pytest.fixture
def files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    localconfig = tmp_path / "localconfig.vdf"
    config_vdf = tmp_path / "config.vdf"
    write_files(localconfig, config_vdf, state("gamemoderun %command%", "GE-Proton9-20"))
    return localconfig, config_vdf


def write_files(localconfig: Path, config_vdf: Path, st: GameState, app_id: str = APP) -> None:
    apps = {
        app_id: {"LaunchOptions": st.launch_options, "LastPlayed": "1"},
        "10": {"LaunchOptions": "-other"},
    }
    local = {"UserLocalConfigStore": {"Software": {"Valve": {"Steam": {"apps": apps}}}}}
    mapping: dict[str, dict[str, str]] = {"10": {"name": "proton_9", "config": "", "priority": "250"}}
    if st.compat_tool:
        mapping[app_id] = {"name": st.compat_tool, "config": "", "priority": "250"}
    config = {"InstallConfigStore": {"Software": {"Valve": {"Steam": {"CompatToolMapping": mapping}}}}}
    localconfig.write_text(vdf.dumps(local, pretty=True), encoding="utf-8")
    config_vdf.write_text(vdf.dumps(config, pretty=True), encoding="utf-8")


def test_read_state(files: tuple[Path, Path], tmp_path: Path) -> None:
    localconfig, config_vdf = files
    assert read_state(localconfig, config_vdf, APP) == state("gamemoderun %command%", "GE-Proton9-20")
    assert read_state(localconfig, config_vdf, "999") == state()
    assert read_state(tmp_path / "missing.vdf", config_vdf, APP) is None
    assert read_state(None, config_vdf, APP) is None
    broken = tmp_path / "broken.vdf"
    broken.write_text('"UserLocalConfigStore"\n{\n  "Software"\n', encoding="utf-8")
    assert read_state(broken, config_vdf, APP) is None
    assert read_state(localconfig, broken, APP) is None


# --- apply ----------------------------------------------------------------------------------


def test_apply_writes_the_change_and_records_a_snapshot(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    assert before is not None
    change = plan([Action("remove_word", value="gamemoderun"), Action("default_proton")], before)
    result = apply_change(localconfig, config_vdf, APP, change, label="GameMode is missing",
                          finding_id="wrapper-missing-gamemoderun")
    assert result.ok, result.message
    assert result.state == state("", "")
    assert read_state(localconfig, config_vdf, APP) == state("", "")
    snap = undo_available(APP)
    assert snap is not None and snap.id == result.snapshot_id
    assert (snap.before, snap.after, snap.finding_id) == (before, change.after, "wrapper-missing-gamemoderun")
    # Other games' entries are left alone.
    assert read_state(localconfig, config_vdf, "10") == state("-other", "proton_9")


def test_apply_writes_only_what_changed(files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    localconfig, config_vdf = files

    def no_compat_write(*_args: object) -> bool:
        raise AssertionError("config.vdf must not be written for a launch-options change")

    monkeypatch.setattr(fix_apply, "set_compat_tool", no_compat_write)
    change = plan([Action("env", key="PROTON_LOG", value="1")], read_state(localconfig, config_vdf, APP))
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="log-off").ok


def test_apply_refuses_when_the_settings_moved(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    change = plan([Action("env", key="PROTON_LOG", value="1")], read_state(localconfig, config_vdf, APP))
    write_files(localconfig, config_vdf, state("mangohud %command%", "GE-Proton9-20"))
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="log-off")
    assert not result.ok
    assert result.message == "The settings changed since the check. Run Diagnose again."
    assert result.state == state("mangohud %command%", "GE-Proton9-20")
    assert read_state(localconfig, config_vdf, APP) == state("mangohud %command%", "GE-Proton9-20")
    assert undo_available(APP) is None


def test_apply_refuses_blocked_unchanged_and_unreadable(files: tuple[Path, Path], tmp_path: Path) -> None:
    localconfig, config_vdf = files
    current = read_state(localconfig, config_vdf, APP)
    blocked = plan([Action("env", key="DXVK_ASYNC", value="a b")], current)
    result = apply_change(localconfig, config_vdf, APP, blocked, label="x", finding_id="y")
    assert result.message == blocked.blocked
    same = plan([Action("manual", text="Do it.")], current)
    assert not apply_change(localconfig, config_vdf, APP, same, label="x", finding_id="y").ok
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], current)
    result = apply_change(tmp_path / "missing.vdf", config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok and "could not be read" in result.message
    assert undo_available(APP) is None


def test_snapshot_failure_blocks_the_write(files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    localconfig, config_vdf = files
    original = localconfig.read_bytes(), config_vdf.read_bytes()

    def fail(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(snapshots, "record", fail)
    both = [Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")]
    change = plan(both, read_state(localconfig, config_vdf, APP))
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok
    assert "undo" in result.message and "nothing was changed" in result.message
    assert (localconfig.read_bytes(), config_vdf.read_bytes()) == original


def test_second_write_failure_puts_the_first_back(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    monkeypatch.setattr(fix_apply, "set_compat_tool", lambda *_a: False)
    change = plan([Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")], before)
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok
    assert "put back" in result.message
    assert read_state(localconfig, config_vdf, APP) == before
    assert result.snapshot_id == "" and undo_available(APP) is None


def test_failed_rollback_keeps_the_snapshot_so_undo_can_finish(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    real_lo, real_ct = fix_apply.set_launch_options, fix_apply.set_compat_tool
    calls: list[str] = []

    def first_only(path: Path, app_id: str, options: str) -> bool:
        calls.append(options)
        return real_lo(path, app_id, options) if len(calls) == 1 else False

    monkeypatch.setattr(fix_apply, "set_launch_options", first_only)
    monkeypatch.setattr(fix_apply, "set_compat_tool", lambda *_a: (_ for _ in ()).throw(OSError("boom")))
    both = [Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")]
    change = plan(both, before)
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok
    assert '"DXVK_ASYNC=1 gamemoderun %command%"' in result.message
    assert '"gamemoderun %command%"' in result.message
    assert "Undo" in result.message
    half = state("DXVK_ASYNC=1 gamemoderun %command%", "GE-Proton9-20")
    assert result.state == half and read_state(localconfig, config_vdf, APP) == half
    assert result.launch_changed
    # The only record of "before" is kept ...
    snap = undo_available(APP)
    assert snap is not None and snap.id == result.snapshot_id and snap.before == before
    # ... and Undo finishes the job without asking, since nothing in the
    # half state was written by anyone but the fix.
    monkeypatch.setattr(fix_apply, "set_launch_options", real_lo)
    monkeypatch.setattr(fix_apply, "set_compat_tool", real_ct)
    undone = undo_latest(localconfig, config_vdf, APP)
    assert undone.ok and not undone.conflict, undone.message
    assert read_state(localconfig, config_vdf, APP) == before
    assert undo_available(APP) is None


def test_failed_first_write_drops_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    monkeypatch.setattr(fix_apply, "set_launch_options", lambda *_a: False)
    change = plan([Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")], before)
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok and "nothing was changed" in result.message
    # Read back as before, so the snapshot has nothing left to undo.
    assert read_state(localconfig, config_vdf, APP) == before
    assert result.snapshot_id == "" and undo_available(APP) is None
    assert not result.launch_changed


def test_a_write_that_says_no_but_landed_keeps_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    real = fix_apply.set_launch_options

    def writes_then_fails(path: Path, app_id: str, options: str) -> bool:
        real(path, app_id, options)
        return False

    monkeypatch.setattr(fix_apply, "set_launch_options", writes_then_fails)
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], before)
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok
    assert "nothing was changed" not in result.message and "Undo" in result.message
    assert result.snapshot_id and undo_available(APP) is not None


def test_apply_checks_what_landed(files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    localconfig, config_vdf = files
    monkeypatch.setattr(fix_apply, "set_launch_options", lambda *_a: True)  # says yes, writes nothing
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], read_state(localconfig, config_vdf, APP))
    result = apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y")
    assert not result.ok and "do not show it" in result.message
    # The undo point stays, so whatever did land can still be put back.
    assert result.snapshot_id and undo_available(APP) is not None


# --- undo --------------------------------------------------------------------------------------


def test_undo_round_trip_restores_the_exact_text(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    original = state('FOO="a  b" X=c\\d   gamemoderun  %command%  -novid', "GE-Proton9-20")
    write_files(localconfig, config_vdf, original)
    change = plan([Action("remove_word", value="gamemoderun"), Action("default_proton")], original)
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    assert read_state(localconfig, config_vdf, APP) == change.after

    result = undo_latest(localconfig, config_vdf, APP)
    assert result.ok, result.message
    assert read_state(localconfig, config_vdf, APP) == original
    assert result.state == original
    assert undo_available(APP) is None
    assert not undo_latest(localconfig, config_vdf, APP).ok  # nothing left to undo


def test_undo_refuses_to_overwrite_later_changes(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    change = plan([Action("env", key="PROTON_LOG", value="1")], before)
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="log-off").ok
    write_files(localconfig, config_vdf, state("PROTON_LOG=1 mangohud %command%", "GE-Proton9-20"))

    result = undo_latest(localconfig, config_vdf, APP)
    assert not result.ok and result.conflict
    assert "changed after the fix was applied" in result.message
    assert '"PROTON_LOG=1 mangohud %command%"' in result.message
    assert '"gamemoderun %command%"' in result.message
    later = state("PROTON_LOG=1 mangohud %command%", "GE-Proton9-20")
    assert read_state(localconfig, config_vdf, APP) == later
    assert undo_available(APP) is not None

    forced = undo_latest(localconfig, config_vdf, APP, force=True)
    assert forced.ok and not forced.conflict
    assert read_state(localconfig, config_vdf, APP) == before
    assert undo_available(APP) is None


def test_undo_when_already_back(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], before)
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    write_files(localconfig, config_vdf, before)
    result = undo_latest(localconfig, config_vdf, APP)
    assert result.ok and "already back" in result.message
    assert undo_available(APP) is None


def test_undo_first_write_failure_keeps_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], read_state(localconfig, config_vdf, APP))
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    monkeypatch.setattr(fix_apply, "set_launch_options", lambda *_a: False)
    result = undo_latest(localconfig, config_vdf, APP)
    assert not result.ok and "the fix is still in place" in result.message
    assert read_state(localconfig, config_vdf, APP) == change.after
    assert not result.launch_changed
    assert undo_available(APP) is not None


def test_undo_failed_rollback_keeps_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    change = plan([Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")], before)
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    real_lo, real_ct = fix_apply.set_launch_options, fix_apply.set_compat_tool
    calls: list[str] = []

    def first_only(path: Path, app_id: str, options: str) -> bool:
        calls.append(options)
        return real_lo(path, app_id, options) if len(calls) == 1 else False

    monkeypatch.setattr(fix_apply, "set_launch_options", first_only)
    monkeypatch.setattr(fix_apply, "set_compat_tool", lambda *_a: False)
    result = undo_latest(localconfig, config_vdf, APP)
    assert not result.ok and "could not be put back" in result.message
    half = state("gamemoderun %command%", "")
    assert read_state(localconfig, config_vdf, APP) == half
    assert result.launch_changed
    # Not at "before", so the snapshot stays, and a second Undo finishes.
    assert undo_available(APP) is not None
    monkeypatch.setattr(fix_apply, "set_launch_options", real_lo)
    monkeypatch.setattr(fix_apply, "set_compat_tool", real_ct)
    again = undo_latest(localconfig, config_vdf, APP)
    assert again.ok and not again.conflict, again.message
    assert read_state(localconfig, config_vdf, APP) == before
    assert undo_available(APP) is None


def test_undo_that_does_not_land_keeps_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    change = plan([Action("env", key="DXVK_ASYNC", value="1")], read_state(localconfig, config_vdf, APP))
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    monkeypatch.setattr(fix_apply, "set_launch_options", lambda *_a: True)  # says yes, writes nothing
    result = undo_latest(localconfig, config_vdf, APP)
    assert not result.ok and "do not show them" in result.message
    assert undo_available(APP) is not None


def test_results_say_whether_the_launch_options_changed(files: tuple[Path, Path]) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    proton_only = plan([Action("default_proton")], before)
    applied = apply_change(localconfig, config_vdf, APP, proton_only, label="x", finding_id="y")
    assert applied.ok and not applied.launch_changed
    undone = undo_latest(localconfig, config_vdf, APP)
    assert undone.ok and not undone.launch_changed
    launch = plan([Action("env", key="PROTON_LOG", value="1")], before)
    applied = apply_change(localconfig, config_vdf, APP, launch, label="x", finding_id="y")
    assert applied.ok and applied.launch_changed
    undone = undo_latest(localconfig, config_vdf, APP)
    assert undone.ok and undone.launch_changed


def test_undo_write_failure_keeps_the_snapshot(
    files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    localconfig, config_vdf = files
    before = read_state(localconfig, config_vdf, APP)
    change = plan([Action("env", key="DXVK_ASYNC", value="1"), Action("default_proton")], before)
    assert apply_change(localconfig, config_vdf, APP, change, label="x", finding_id="y").ok
    monkeypatch.setattr(fix_apply, "set_compat_tool", lambda *_a: False)
    result = undo_latest(localconfig, config_vdf, APP)
    assert not result.ok
    assert "the fix is still in place" in result.message
    assert read_state(localconfig, config_vdf, APP) == change.after
    assert undo_available(APP) is not None
