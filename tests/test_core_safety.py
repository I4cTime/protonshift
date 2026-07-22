"""Security / file-safety regression tests for protonshift.core.

Pure-core tests: no Qt imports, everything runs against tmp_path.
Covers the audit fixes: app_id path traversal (shader cache), bash-key
injection (ScopeBuddy), tolerant decoding, fail-closed JSON writes
(Heroic, user fixes), VDF Apps/apps merge, and backup filename uniqueness.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import vdf

from protonshift.core import fixes as fixes_mod
from protonshift.core import heroic_config, saves
from protonshift.core.mangohud import read_mangohud_config
from protonshift.core.scopebuddy import parse_scb_conf, write_scb_conf
from protonshift.core.shader_cache import clear_shader_cache, get_shader_cache_info
from protonshift.core.steam import get_userdata_dir
from protonshift.core.vdf_config import read_launch_options, set_launch_options


# --------------------------------------------------------------------------- #
# 1 — shader cache: app_id validation + containment
# --------------------------------------------------------------------------- #

@pytest.fixture
def steam_root(tmp_path: Path) -> Path:
    root = tmp_path / "steam"
    cache = root / "steamapps" / "shadercache" / "12345"
    cache.mkdir(parents=True)
    (cache / "blob.bin").write_bytes(b"x" * 64)
    return root


def test_shader_cache_valid_app_id(steam_root: Path) -> None:
    info = get_shader_cache_info(steam_root, "12345")
    assert info.exists
    assert info.size_bytes == 64
    assert clear_shader_cache(steam_root, "12345")
    assert not (steam_root / "steamapps" / "shadercache" / "12345").exists()


@pytest.mark.parametrize("bad_id", ["..", "../..", "12345/../..", "", "abc", "12 34", "1;rm"])
def test_shader_cache_rejects_bad_app_id(steam_root: Path, bad_id: str) -> None:
    info = get_shader_cache_info(steam_root, bad_id)
    assert not info.exists
    assert clear_shader_cache(steam_root, bad_id) is False
    # the critical bit: steamapps itself must survive
    assert (steam_root / "steamapps").exists()
    assert (steam_root / "steamapps" / "shadercache" / "12345").exists()


def test_shader_cache_rejects_symlink_escape(steam_root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "victim.txt").write_text("keep me")
    link = steam_root / "steamapps" / "shadercache" / "666"
    link.symlink_to(outside)
    assert clear_shader_cache(steam_root, "666") is False
    assert (outside / "victim.txt").exists()


# --------------------------------------------------------------------------- #
# 2 — ScopeBuddy: key injection rejected, valid round-trip
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "bad_key",
    ["$(reboot)", "X; rm -rf ~", "KEY WITH SPACE", "1LEADING_DIGIT", "", "a-b", "PATH\n"],
)
def test_write_scb_conf_rejects_bad_keys(tmp_path: Path, bad_key: str) -> None:
    conf = tmp_path / "scb.conf"
    with pytest.raises(ValueError):
        write_scb_conf(conf, {bad_key: "1"})
    assert not conf.exists()  # nothing written


def test_scb_conf_round_trip(tmp_path: Path) -> None:
    conf = tmp_path / "scb.conf"
    cfg = {
        "SCB_GAMESCOPE_ARGS": "-W 3840 -H 2160 -f -b",
        "SCB_AUTO_HDR": "1",
        "SCB_DEBUG": "",
        "MY_VAR": "value with 'quotes' and #hash",
    }
    assert write_scb_conf(conf, cfg)
    assert parse_scb_conf(conf) == cfg


def test_write_scb_conf_preserves_comments_and_bash(tmp_path: Path) -> None:
    conf = tmp_path / "scb.conf"
    conf.write_text(
        "# keep this comment\n"
        "if [ -n \"$X\" ]; then\n"
        "  INNER=1\n"
        "fi\n"
        "SCB_AUTO_VRR=0\n",
        encoding="utf-8",
    )
    assert write_scb_conf(conf, {"SCB_AUTO_VRR": "1"})
    text = conf.read_text(encoding="utf-8")
    assert "# keep this comment" in text
    assert "INNER=1" in text
    assert "SCB_AUTO_VRR=1" in text


# --------------------------------------------------------------------------- #
# 3 — non-UTF-8 bytes must not raise
# --------------------------------------------------------------------------- #

def test_parse_scb_conf_bad_bytes(tmp_path: Path) -> None:
    conf = tmp_path / "scb.conf"
    conf.write_bytes(b"SCB_DEBUG=1\n\xff\xfe garbage\nSCB_AUTO_RES=0\n")
    parsed = parse_scb_conf(conf)
    assert parsed["SCB_DEBUG"] == "1"
    assert parsed["SCB_AUTO_RES"] == "0"


def test_write_scb_conf_over_bad_bytes(tmp_path: Path) -> None:
    conf = tmp_path / "scb.conf"
    conf.write_bytes(b"# \xff comment\nSCB_DEBUG=0\n")
    assert write_scb_conf(conf, {"SCB_DEBUG": "1"})
    assert parse_scb_conf(conf)["SCB_DEBUG"] == "1"


def test_read_mangohud_config_bad_bytes(tmp_path: Path) -> None:
    conf = tmp_path / "MangoHud.conf"
    conf.write_bytes(b"fps\n\xffbroken=\xfe\nfont_size=24\n")
    parsed = read_mangohud_config(conf)
    assert parsed["fps"] == ""
    assert parsed["font_size"] == "24"


# --------------------------------------------------------------------------- #
# 4 — Heroic config: fail closed on corrupt JSON, guard non-dict slots
# --------------------------------------------------------------------------- #

@pytest.fixture
def heroic_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg_dir = tmp_path / "GamesConfig"
    cfg_dir.mkdir()
    monkeypatch.setattr(heroic_config, "_get_games_config_dir", lambda: cfg_dir)
    return cfg_dir


def test_heroic_write_refuses_corrupt_file(heroic_dir: Path) -> None:
    cfg_file = heroic_dir / "game1.json"
    cfg_file.write_text("{ not json !!", encoding="utf-8")
    assert heroic_config.set_heroic_launch_options("game1", "PROTON_LOG=1 %command%") is False
    assert cfg_file.read_text(encoding="utf-8") == "{ not json !!"  # untouched


def test_heroic_write_refuses_non_dict_top_level(heroic_dir: Path) -> None:
    cfg_file = heroic_dir / "game1.json"
    cfg_file.write_text("[1, 2, 3]", encoding="utf-8")
    assert heroic_config.set_heroic_launch_options("game1", "x") is False


def test_heroic_write_preserves_other_settings(heroic_dir: Path) -> None:
    cfg_file = heroic_dir / "game1.json"
    cfg_file.write_text(
        json.dumps({"game1": {"winePrefix": "/p", "enableEsync": True}, "version": "v0"}),
        encoding="utf-8",
    )
    assert heroic_config.set_heroic_launch_options("game1", "opts")
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert data["game1"]["winePrefix"] == "/p"
    assert data["game1"]["enableEsync"] is True
    assert data["game1"]["otherOptions"] == "opts"
    assert data["version"] == "v0"


def test_heroic_read_non_dict_app_slot(heroic_dir: Path) -> None:
    (heroic_dir / "game1.json").write_text(json.dumps({"game1": "oops"}), encoding="utf-8")
    cfg = heroic_config.get_heroic_game_config("game1")
    assert cfg.exists is False  # no AttributeError, treated as unreadable


# --------------------------------------------------------------------------- #
# 5 — user fixes: fail closed on corrupt JSON
# --------------------------------------------------------------------------- #

def test_add_user_fix_refuses_corrupt_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fixes_mod, "_USER_FIXES_DIR", tmp_path)
    corrupt = tmp_path / "123.json"
    corrupt.write_text("[ broken", encoding="utf-8")
    assert fixes_mod.add_user_fix("123", "t", "d", "env", "K", "V") is False
    assert corrupt.read_text(encoding="utf-8") == "[ broken"  # untouched


def test_add_user_fix_appends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fixes_mod, "_USER_FIXES_DIR", tmp_path)
    assert fixes_mod.add_user_fix("123", "first", "d", "env", "A", "1")
    assert fixes_mod.add_user_fix("123", "second", "d", "env", "B", "2")
    saved = json.loads((tmp_path / "123.json").read_text(encoding="utf-8"))
    assert [f["title"] for f in saved] == ["first", "second"]


# --------------------------------------------------------------------------- #
# 6 — VDF: "Apps" merged into "apps", not dropped
# --------------------------------------------------------------------------- #

def test_vdf_both_casings_merged(tmp_path: Path) -> None:
    cfg = tmp_path / "localconfig.vdf"
    data = {
        "UserLocalConfigStore": {
            "Software": {
                "Valve": {
                    "Steam": {
                        "apps": {"111": {"LaunchOptions": "keep-lower"}},
                        "Apps": {
                            "222": {"LaunchOptions": "keep-upper"},
                            "111": {"LaunchOptions": "loser-on-collision"},
                        },
                    }
                }
            }
        }
    }
    with open(cfg, "w", encoding="utf-8") as f:
        vdf.dump(data, f, pretty=True)

    assert set_launch_options(cfg, "333", "new-opts")

    ok, opts = read_launch_options(cfg, "222")
    assert ok and opts == "keep-upper"  # previously discarded wholesale
    ok, opts = read_launch_options(cfg, "111")
    assert ok and opts == "keep-lower"  # lowercase wins on collision
    ok, opts = read_launch_options(cfg, "333")
    assert ok and opts == "new-opts"


# --------------------------------------------------------------------------- #
# 7 — userdata dir: deterministic multi-account pick
# --------------------------------------------------------------------------- #

def test_get_userdata_dir_prefers_recent_localconfig(tmp_path: Path) -> None:
    import os

    userdata = tmp_path / "userdata"
    for sid, mtime in (("100", 1000), ("200", 2000), ("300", 1500)):
        cfg = userdata / sid / "config"
        cfg.mkdir(parents=True)
        lc = cfg / "localconfig.vdf"
        lc.write_text("", encoding="utf-8")
        os.utime(lc, (mtime, mtime))
    picked = get_userdata_dir(tmp_path)
    assert picked is not None and picked.name == "200"


def test_get_userdata_dir_fallback_highest_id(tmp_path: Path) -> None:
    userdata = tmp_path / "userdata"
    for sid in ("5", "42", "7"):
        (userdata / sid).mkdir(parents=True)
    picked = get_userdata_dir(tmp_path)
    assert picked is not None and picked.name == "42"


# --------------------------------------------------------------------------- #
# 8 — backup filename uniqueness
# --------------------------------------------------------------------------- #

class _FrozenDatetime:
    """Stand-in for saves.datetime with a constant now()."""

    _FIXED = datetime(2026, 7, 22, 12, 0, 0, 123456, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):  # noqa: ANN001, ANN206
        return cls._FIXED

    fromtimestamp = datetime.fromtimestamp


def test_backup_same_instant_gets_unique_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(saves, "_BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr(saves, "datetime", _FrozenDatetime)

    save_dir = tmp_path / "SavedGames"
    save_dir.mkdir()
    (save_dir / "slot1.sav").write_bytes(b"data")

    first = saves.backup_saves("123", [str(save_dir)])
    second = saves.backup_saves("123", [str(save_dir)])
    assert first is not None and second is not None
    assert first != second
    assert Path(first).exists() and Path(second).exists()
