"""Snapshots for Diagnose's Undo: round trip, order, cap, drop, damaged files, path safety.

HOME points at ``tmp_path`` for every test, so nothing touches the real
``~/.config``. Qt-free.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from protonshift.core import snapshots as snap
from protonshift.core.snapshots import GameState

BEFORE = GameState(launch_options="gamemoderun %command%", compat_tool="proton_9")
AFTER = GameState(launch_options="%command%", compat_tool="")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def file_for(app_id: str) -> Path:
    return snap.snapshot_dir() / f"{app_id}.json"


def test_snapshot_dir_follows_home_at_call_time(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert snap.snapshot_dir() == home / ".config" / "protonshift" / "snapshots"
    other = home / "other"
    monkeypatch.setenv("HOME", str(other))
    assert snap.snapshot_dir() == other / ".config" / "protonshift" / "snapshots"


def test_round_trip() -> None:
    s = snap.record("570", "Removed gamemoderun", "wrapper-missing", BEFORE, AFTER)
    assert s.app_id == "570" and s.label == "Removed gamemoderun" and s.finding_id == "wrapper-missing"
    assert s.before == BEFORE and s.after == AFTER
    assert s.taken_at.endswith("+00:00") and "." not in s.taken_at
    assert snap.history("570") == [s]
    assert snap.latest("570") == s
    data = json.loads(file_for("570").read_text())
    assert data["format"] == "protonshift-snapshots" and data["version"] == 1
    assert data["entries"][0]["before"] == {"launch_options": "gamemoderun %command%", "compat_tool": "proton_9"}


def test_history_newest_first_and_ids_unique() -> None:
    made = [snap.record("10", f"fix {i}", "f", BEFORE, AFTER) for i in range(5)]
    got = snap.history("10")
    assert [s.label for s in got] == ["fix 4", "fix 3", "fix 2", "fix 1", "fix 0"]
    assert len({s.id for s in made}) == 5
    assert snap.latest("10").label == "fix 4"


def test_games_are_kept_apart() -> None:
    snap.record("1", "a", "f", BEFORE, AFTER)
    snap.record("2", "b", "f", BEFORE, AFTER)
    assert [s.label for s in snap.history("1")] == ["a"]
    assert [s.label for s in snap.history("2")] == ["b"]


def test_cap_keeps_newest() -> None:
    for i in range(snap.MAX_PER_GAME + 5):
        snap.record("20", f"fix {i}", "f", BEFORE, AFTER)
    got = snap.history("20")
    assert len(got) == snap.MAX_PER_GAME
    assert got[0].label == f"fix {snap.MAX_PER_GAME + 4}"
    assert got[-1].label == "fix 5"


def test_drop() -> None:
    a = snap.record("30", "a", "f", BEFORE, AFTER)
    b = snap.record("30", "b", "f", BEFORE, AFTER)
    assert snap.drop("30", b.id) is True
    assert snap.history("30") == [a]
    assert snap.drop("30", b.id) is False
    assert snap.drop("30", "no-such-id") is False
    assert snap.drop("31", a.id) is False  # no file for that game
    assert snap.drop("30", a.id) is True
    assert snap.history("30") == [] and snap.latest("30") is None


def test_label_is_capped() -> None:
    s = snap.record("40", "x" * 500, "f", BEFORE, AFTER)
    assert len(s.label) == snap.LABEL_MAX
    assert len(snap.latest("40").label) == snap.LABEL_MAX


@pytest.mark.parametrize("bad", ["a\nb", "a\rb", "a\x00b"])
@pytest.mark.parametrize("where", ["label", "finding_id", "before_lo", "before_ct", "after_lo", "after_ct"])
def test_record_rejects_control_characters(bad: str, where: str) -> None:
    label, finding = "ok", "ok"
    before, after = BEFORE, AFTER
    if where == "label":
        label = bad
    elif where == "finding_id":
        finding = bad
    elif where == "before_lo":
        before = GameState(bad, "")
    elif where == "before_ct":
        before = GameState("", bad)
    elif where == "after_lo":
        after = GameState(bad, "")
    else:
        after = GameState("", bad)
    with pytest.raises(ValueError):
        snap.record("50", label, finding, before, after)
    assert not file_for("50").exists()


def test_record_rejects_non_strings() -> None:
    with pytest.raises(ValueError):
        snap.record("51", None, "f", BEFORE, AFTER)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        snap.record("51", "l", "f", GameState(None, ""), AFTER)  # type: ignore[arg-type]


@pytest.mark.parametrize("content", [
    "{ not json",
    "[]",
    json.dumps({"format": "something-else", "version": 1, "entries": []}),
    json.dumps({"format": "protonshift-snapshots", "version": 2, "entries": []}),
    json.dumps({"format": "protonshift-snapshots", "version": 1, "entries": {}}),
    "\udcff",
])
def test_unreadable_file_is_set_aside_not_lost(content: str) -> None:
    path = file_for("60")
    path.parent.mkdir(parents=True)
    raw = content.encode("utf-8", "surrogateescape")
    path.write_bytes(raw)
    assert snap.history("60") == []
    assert snap.latest("60") is None
    assert snap.drop("60", "x") is False
    assert path.read_bytes() == raw  # readers never touch it

    s = snap.record("60", "after damage", "f", BEFORE, AFTER)
    assert snap.history("60") == [s]
    kept = list(path.parent.glob("60.json.corrupt-*"))
    assert len(kept) == 1
    assert kept[0].read_bytes() == raw


def test_two_corrupt_files_in_one_second_both_survive() -> None:
    path = file_for("61")
    path.parent.mkdir(parents=True)
    path.write_text("first bad")
    snap.record("61", "a", "f", BEFORE, AFTER)
    path.write_text("second bad")
    snap.record("61", "b", "f", BEFORE, AFTER)
    kept = sorted(p.read_text() for p in path.parent.glob("61.json.corrupt-*"))
    assert kept == ["first bad", "second bad"]


def test_malformed_entries_are_skipped() -> None:
    good = snap.record("70", "good", "f", BEFORE, AFTER)
    path = file_for("70")
    data = json.loads(path.read_text())
    entry = data["entries"][0]
    data["entries"] = [
        "not a dict",
        {**entry, "id": 5},
        {**entry, "label": None},
        {k: v for k, v in entry.items() if k != "finding_id"},
        {**entry, "before": {"launch_options": "x"}},
        {**entry, "after": "nope"},
        {**entry, "before": {"launch_options": "a\nb", "compat_tool": ""}},
        {**entry, "app_id": "71"},
        {**entry, "id": ""},
        entry,
        {**entry, "extra": "ignored"},
    ]
    path.write_text(json.dumps(data))
    got = snap.history("70")
    assert got == [good, good]


def test_record_raises_oserror_when_it_cannot_write(home: Path) -> None:
    # A file where the folder should be: nothing can be written under it.
    (home / ".config" / "protonshift").mkdir(parents=True)
    (home / ".config" / "protonshift" / "snapshots").write_text("in the way")
    with pytest.raises(OSError):
        snap.record("80", "l", "f", BEFORE, AFTER)


BAD_IDS = ["..", "../x", "1/2", "", "1" * 21, "12a", "12\x0034", "/etc/passwd", "-1", " 12", "12\n",
           "١٢"]


@pytest.mark.parametrize("bad", BAD_IDS)
def test_bad_app_ids_are_refused(bad: str, home: Path) -> None:
    with pytest.raises(ValueError):
        snap.record(bad, "l", "f", BEFORE, AFTER)
    assert snap.history(bad) == []
    assert snap.latest(bad) is None
    assert snap.drop(bad, "x") is False
    assert not (home / ".config" / "protonshift" / "snapshots").exists()


@pytest.mark.parametrize("bad", [None, 570, b"570"])
def test_non_string_app_ids_are_refused(bad: object) -> None:
    with pytest.raises(ValueError):
        snap.record(bad, "l", "f", BEFORE, AFTER)  # type: ignore[arg-type]
    assert snap.history(bad) == []  # type: ignore[arg-type]


def test_twenty_digit_id_is_accepted() -> None:
    big = "1" * 20
    s = snap.record(big, "l", "f", BEFORE, AFTER)
    assert snap.latest(big) == s


def test_symlink_out_of_the_folder_is_refused(home: Path) -> None:
    outside = home / "outside.json"
    outside.write_text("precious")
    folder = snap.snapshot_dir()
    folder.mkdir(parents=True)
    (folder / "90.json").symlink_to(outside)
    with pytest.raises(ValueError):
        snap.record("90", "l", "f", BEFORE, AFTER)
    assert snap.history("90") == []
    assert outside.read_text() == "precious"


def test_symlink_to_another_game_is_refused() -> None:
    other = snap.record("91", "other game", "f", BEFORE, AFTER)
    (snap.snapshot_dir() / "92.json").symlink_to("91.json")
    with pytest.raises(ValueError):
        snap.record("92", "l", "f", BEFORE, AFTER)
    assert snap.history("91") == [other]


def test_no_long_dashes_in_source() -> None:
    source = Path(snap.__file__).read_text(encoding="utf-8")
    assert chr(0x2014) not in source and chr(0x2013) not in source
