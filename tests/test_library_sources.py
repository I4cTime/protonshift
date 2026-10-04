"""Tests for the non-Steam library sources and the Steam tool filter.

Each test builds the launcher's on-disk files in a temp dir and points the
module's root list at it - no real launcher needed.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import vdf

from protonshift.core import heroic, lutris
from protonshift.core.steam import is_steam_tool
from protonshift.core.steam_shortcuts import read_shortcuts

# --- Steam tools ----------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Proton Experimental", "Proton 9.0 (Beta)", "Proton 8.0", "Proton Hotfix", "Proton EasyAntiCheat Runtime",
     "Proton BattlEye Runtime", "Steam Linux Runtime 4.0", "Steam Linux Runtime 3.0 (sniper)",
     "Steam Linux Runtime 1.0 (scout)", "Steamworks Common Redistributables"],
)
def test_steam_tools_are_recognized(name: str) -> None:
    assert is_steam_tool(name)


@pytest.mark.parametrize("name", ["Manor Lords", "Protonium", "Proton Pulse", "Steam Marines", "Icarus"])
def test_games_are_not_tools(name: str) -> None:
    assert not is_steam_tool(name)


# --- Heroic -----------------------------------------------------------------------


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def heroic_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "heroic"
    root.mkdir()
    monkeypatch.setattr(heroic, "HEROIC_ROOTS", [root])
    return root


def test_heroic_amazon_and_sideload(heroic_root: Path, tmp_path: Path) -> None:
    _write(heroic_root / "nile_config" / "nile" / "installed.json",
           [{"id": "amzn1.adg.product.abc", "version": "1", "path": str(tmp_path / "Games" / "Some Amazon Game")},
            {"version": "no id, skipped"}, "garbage"])
    _write(heroic_root / "store_cache" / "nile_library.json",
           {"library": [{"app_name": "amzn1.adg.product.abc", "title": "Amazon Title"}]})
    _write(heroic_root / "GamesConfig" / "amzn1.adg.product.abc.json",
           {"amzn1.adg.product.abc": {"winePrefix": "/prefixes/amazon"}, "version": "v0"})
    _write(heroic_root / "sideload_apps" / "library.json", {"games": [
        {"app_name": "side1", "title": "Windows Sideload", "is_installed": True, "folder_name": "/games/win",
         "install": {"executable": "/games/win/game.exe", "platform": "Windows"}},
        {"app_name": "side2", "title": "Native Sideload", "is_installed": True,
         "install": {"executable": "/games/native/run.sh", "platform": "linux"}},
        {"app_name": "side3", "title": "Removed", "is_installed": False, "install": {}},
    ]})
    _write(heroic_root / "GamesConfig" / "side1.json", {"side1": {"winePrefix": "/prefixes/side1"}})
    _write(heroic_root / "GamesConfig" / "side2.json", {"side2": {"winePrefix": "/prefixes/default"}})

    games = {g.app_id: g for g in heroic.discover_heroic_games()}
    assert set(games) == {"amzn1.adg.product.abc", "side1", "side2"}

    amazon = games["amzn1.adg.product.abc"]
    assert (amazon.store, amazon.name, amazon.is_native) == ("amazon", "Amazon Title", False)
    assert amazon.prefix_path == Path("/prefixes/amazon")

    win = games["side1"]
    assert (win.store, win.platform, win.install_path) == ("sideload", "windows", Path("/games/win"))
    assert win.prefix_path == Path("/prefixes/side1")

    native = games["side2"]
    assert native.is_native
    assert native.prefix_path is None  # a native game has no prefix even if a default was written
    assert native.install_path == Path("/games/native")


def test_heroic_amazon_title_falls_back_to_folder(heroic_root: Path) -> None:
    _write(heroic_root / "nile_config" / "nile" / "installed.json", [{"id": "x1", "path": "/g/Folder Name"}])
    assert heroic.discover_heroic_games()[0].name == "Folder Name"


def test_heroic_corrupt_store_does_not_hide_others(heroic_root: Path) -> None:
    (heroic_root / "sideload_apps").mkdir()
    (heroic_root / "sideload_apps" / "library.json").write_text("{not json", encoding="utf-8")
    _write(heroic_root / "nile_config" / "nile" / "installed.json", [{"id": "x1", "path": "/g/a"}])
    assert [g.app_id for g in heroic.discover_heroic_games()] == ["x1"]


# --- Lutris -----------------------------------------------------------------------


def test_lutris_runner_and_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "lutris"
    (root / "games").mkdir(parents=True)
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    (root / "games" / "123-wine-game.yml").write_text(f"game:\n  prefix: {prefix}\n", encoding="utf-8")
    conn = sqlite3.connect(root / "pga.db")
    conn.execute("CREATE TABLE games (name TEXT, slug TEXT, directory TEXT, installed INTEGER, "
                 "runner TEXT, service TEXT)")
    conn.executemany("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?)", [
        ("Wine Game", "wine-game", str(tmp_path), 1, "wine", "gog"),
        ("Native Game", "native-game", "", 1, "linux", None),
        ("Not Installed", "nope", "", 0, "wine", None),
    ])
    conn.commit()
    conn.close()
    monkeypatch.setattr(lutris, "LUTRIS_ROOTS", [root])

    games = {g.app_id: g for g in lutris.discover_lutris_games()}
    assert set(games) == {"wine-game", "native-game"}
    assert (games["wine-game"].runner, games["wine-game"].service) == ("wine", "gog")
    assert games["wine-game"].prefix_path == prefix
    assert not games["wine-game"].is_native
    assert games["native-game"].is_native
    assert games["native-game"].service == ""


def test_lutris_old_database_without_runner_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "lutris"
    root.mkdir()
    conn = sqlite3.connect(root / "pga.db")
    conn.execute("CREATE TABLE games (name TEXT, slug TEXT, directory TEXT, installed INTEGER)")
    conn.execute("INSERT INTO games VALUES ('Old', 'old', '', 1)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(lutris, "LUTRIS_ROOTS", [root])
    game = lutris.discover_lutris_games()[0]
    assert (game.app_id, game.runner, game.service) == ("old", "", "")


# --- Steam non-Steam shortcuts ------------------------------------------------------


def test_read_shortcuts(tmp_path: Path) -> None:
    steam_root = tmp_path / "Steam"
    start_dir = tmp_path / "games" / "tool"
    start_dir.mkdir(parents=True)
    signed_id = -1234567890  # Steam stores the id as a signed 32-bit int
    unsigned = signed_id & 0xFFFFFFFF
    (steam_root / "steamapps" / "compatdata" / str(unsigned)).mkdir(parents=True)
    path = tmp_path / "shortcuts.vdf"
    path.write_bytes(vdf.binary_dumps({"shortcuts": {
        "0": {"appid": signed_id, "AppName": "My Game", "Exe": f'"{start_dir}/game.exe"',
              "StartDir": f'"{start_dir}"', "LaunchOptions": "-windowed"},
        "1": {"appid": 42, "appname": "Lowercase Keys", "exe": "/x/y", "StartDir": "/does/not/exist"},
        "2": {"AppName": "No id, skipped"},
    }}))

    shortcuts = {s.name: s for s in read_shortcuts(path, steam_root)}
    assert set(shortcuts) == {"My Game", "Lowercase Keys"}

    game = shortcuts["My Game"]
    assert game.app_id == str(unsigned)
    assert game.game_id == str((unsigned << 32) | 0x02000000)
    assert game.exe == f"{start_dir}/game.exe"
    assert game.start_dir == start_dir
    assert game.launch_options == "-windowed"
    assert game.compatdata_path == steam_root / "steamapps" / "compatdata" / str(unsigned)

    other = shortcuts["Lowercase Keys"]
    assert (other.app_id, other.start_dir, other.compatdata_path) == ("42", None, None)


def test_read_shortcuts_missing_or_corrupt(tmp_path: Path) -> None:
    assert read_shortcuts(tmp_path / "absent.vdf", tmp_path) == []
    bad = tmp_path / "bad.vdf"
    bad.write_bytes(b"\x00\x01garbage")
    assert read_shortcuts(bad, tmp_path) == []


# --- system Proton builds seen from inside a Flatpak --------------------------------


def test_system_compat_dirs_in_flatpak_use_the_host_mount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from protonshift.core import steam

    host = tmp_path / "run-host"
    tools = host / "usr" / "share" / "steam" / "compatibilitytools.d"
    (tools / "proton-ge-custom").mkdir(parents=True)
    monkeypatch.setattr(steam, "FLATPAK_HOST_ROOT", host)
    monkeypatch.setattr(steam, "SYSTEM_COMPAT_DIRS", (Path("/usr/share/steam/compatibilitytools.d"),))
    monkeypatch.setenv("XDG_DATA_DIRS", "")

    # outside a sandbox the host mount is not consulted
    monkeypatch.setattr(steam, "in_flatpak", lambda: False)
    assert tools not in steam.get_system_compattools_dirs()

    monkeypatch.setattr(steam, "in_flatpak", lambda: True)
    assert tools in steam.get_system_compattools_dirs()
    # shown to the user as the path they know, without the sandbox prefix
    assert steam.host_display_path(tools / "proton-ge-custom") == (
        "/usr/share/steam/compatibilitytools.d/proton-ge-custom"
    )


def test_host_display_path_leaves_other_paths_alone() -> None:
    from protonshift.core.steam import host_display_path

    assert host_display_path("/home/u/.steam/root/compatibilitytools.d/GE") == "/home/u/.steam/root/compatibilitytools.d/GE"
    assert host_display_path("/run/hostile/x") == "/run/hostile/x"
    assert host_display_path("/run/host") == "/"
