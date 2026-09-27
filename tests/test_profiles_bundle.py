"""Profile export/import bundles (1.2.0): round-trip, validation, collisions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from protonshift.core import profiles_storage as ps


@pytest.fixture(autouse=True)
def _isolated_profiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "profiles"
    monkeypatch.setattr(ps, "PROFILES_DIR", d)
    return d


def _prof(name: str, **kw) -> ps.ApplicationProfile:
    base = {
        "launch_options": "-novid %command%",
        "compat_tool": "GE-Proton9-27",
        "env_vars": {"DXVK_ASYNC": "1"},
        "power_profile": "performance",
    }
    base.update(kw)
    return ps.ApplicationProfile(name=name, **base)


def test_export_import_round_trip(tmp_path: Path) -> None:
    assert ps.save_profile(_prof("Cyberpunk"))
    assert ps.save_profile(_prof("Elden Ring", env_vars={"PROTON_USE_WINED3D": "1"}))
    out = tmp_path / "bundle.json"
    assert ps.export_profiles(["Cyberpunk", "Elden Ring", "missing"], out) == 2
    data = json.loads(out.read_text())
    assert data["format"] == ps.BUNDLE_FORMAT and data["version"] == ps.BUNDLE_VERSION
    assert [p["name"] for p in data["profiles"]] == ["Cyberpunk", "Elden Ring"]

    # wipe and import back
    for n in ps.list_profiles():
        ps.delete_profile(n)
    res = ps.import_profiles(out)
    assert res.imported == ["Cyberpunk", "Elden Ring"]
    assert res.skipped_existing == [] and res.invalid == 0
    assert ps.load_profile("Elden Ring") == _prof("Elden Ring", env_vars={"PROTON_USE_WINED3D": "1"})


def test_import_skips_existing_unless_overwrite(tmp_path: Path) -> None:
    ps.save_profile(_prof("Keep", launch_options="local"))
    out = tmp_path / "b.json"
    ps.export_profiles(["Keep"], out)
    ps.save_profile(_prof("Keep", launch_options="changed"))

    res = ps.import_profiles(out)
    assert res.skipped_existing == ["Keep"] and res.imported == []
    assert ps.load_profile("Keep").launch_options == "changed"
    assert "skipped 1 existing" in res.summary

    res = ps.import_profiles(out, overwrite=True)
    assert res.imported == ["Keep"]
    assert ps.load_profile("Keep").launch_options == "local"


def test_invalid_entries_are_dropped(tmp_path: Path) -> None:
    bundle = {
        "format": ps.BUNDLE_FORMAT, "version": 1,
        "profiles": [
            {"name": "ok", "launch_options": "", "compat_tool": "", "env_vars": {}, "power_profile": ""},
            {"name": "", "launch_options": ""},                       # empty name
            {"name": "badkey", "env_vars": {"1BAD": "x"}},           # invalid env key
            {"name": "newline", "launch_options": "a\nb"},           # newline injection
            {"name": "types", "env_vars": {"A": 1}},                 # non-string value
            "not a dict",
            {"name": "../escape", "env_vars": {}},                   # sanitized on save
        ],
    }
    src = tmp_path / "mixed.json"
    src.write_text(json.dumps(bundle))
    res = ps.import_profiles(src)
    assert res.imported == ["ok", "../escape"]
    assert res.invalid == 5
    assert "ignored 5 invalid" in res.summary
    # the escape attempt lands as a plain file inside PROFILES_DIR
    names = ps.list_profiles()
    assert all("/" not in n and ".." not in n for n in names)
    assert not (tmp_path / "escape.json").exists()


@pytest.mark.parametrize(
    ("content", "msg"),
    [
        ("{not json", "Not a JSON"),
        (json.dumps([1, 2]), "Not a ProtonShift"),
        (json.dumps({"format": "other", "profiles": []}), "Not a ProtonShift"),
        (json.dumps({"format": ps.BUNDLE_FORMAT, "version": 99, "profiles": []}), "newer ProtonShift"),
        (json.dumps({"format": ps.BUNDLE_FORMAT, "version": 1}), "no profiles"),
    ],
)
def test_bad_bundles_raise(tmp_path: Path, content: str, msg: str) -> None:
    src = tmp_path / "x.json"
    src.write_text(content)
    with pytest.raises(ps.BundleError, match=msg):
        ps.import_profiles(src)


def test_missing_file_and_oversize(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ps.BundleError, match="Couldn't read"):
        ps.read_bundle(tmp_path / "nope.json")
    monkeypatch.setattr(ps, "MAX_BUNDLE_BYTES", 10)
    big = tmp_path / "big.json"
    big.write_text(json.dumps({"format": ps.BUNDLE_FORMAT, "version": 1, "profiles": []}))
    with pytest.raises(ps.BundleError, match="too large"):
        ps.read_bundle(big)


def test_export_creates_parent_dirs(tmp_path: Path) -> None:
    ps.save_profile(_prof("A"))
    out = tmp_path / "deep" / "er" / "bundle.json"
    assert ps.export_profiles(["A"], out) == 1
    assert out.exists()
