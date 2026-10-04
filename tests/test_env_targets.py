"""#47: environment variables that reach desktops systemd didn't start.

Covers the managed shell block (``~/.profile`` / ``~/.xsessionrc``), the
target recommendation matrix, the Steam launch-options prefix and the
read/write dispatch. Qt-free; paths are monkeypatched at module level
(never HOME).
"""

from __future__ import annotations

import pytest

from protonshift.core import env_targets, env_vars, session
from protonshift.core.env_targets import (
    BLOCK_BEGIN,
    BLOCK_END,
    as_launch_prefix,
    read_block,
    read_target,
    recommended_target,
    write_block,
    write_target,
)

_SURROUNDING = (
    "# ~/.profile: executed by the command interpreter for login shells.\r\n"
    "if [ -n \"$BASH_VERSION\" ]; then\n"
    "    . \"$HOME/.bashrc\"\t \n"
    "fi\n"
    "\n"
    "export PATH=\"$HOME/bin:$PATH\"   # user's own line, keep verbatim\n"
)
_TRAILER = "\n# after the block - must survive too\nalias ll='ls -l'\n"


# --- managed block --------------------------------------------------------------


def test_block_round_trip_preserves_surroundings_byte_for_byte(tmp_path):
    path = tmp_path / ".profile"
    path.write_bytes(_SURROUNDING.encode())

    assert write_block(path, {"B": "2", "A": "1"}) is True
    text = path.read_bytes().decode()
    assert text.startswith(_SURROUNDING)
    assert text == _SURROUNDING + f"{BLOCK_BEGIN}\nexport A='1'\nexport B='2'\n{BLOCK_END}\n"
    assert read_block(path) == {"A": "1", "B": "2"}

    # append user content after the block, then rewrite: both sides intact
    path.write_bytes(path.read_bytes() + _TRAILER.encode())
    assert write_block(path, {"C": "3"}) is True
    assert path.read_bytes().decode() == _SURROUNDING + f"{BLOCK_BEGIN}\nexport C='3'\n{BLOCK_END}\n" + _TRAILER
    assert read_block(path) == {"C": "3"}


def test_block_appended_with_newline_when_file_lacks_one(tmp_path):
    path = tmp_path / ".xsessionrc"
    path.write_text("xrdb -merge ~/.Xresources", encoding="utf-8")
    assert write_block(path, {"K": "v"}) is True
    assert path.read_text(encoding="utf-8") == f"xrdb -merge ~/.Xresources\n{BLOCK_BEGIN}\nexport K='v'\n{BLOCK_END}\n"


def test_missing_file_is_created(tmp_path):
    path = tmp_path / "nested" / ".profile"
    assert read_block(path) == {}
    assert write_block(path, {"MANGOHUD": "1"}) is True
    assert path.read_text(encoding="utf-8") == f"{BLOCK_BEGIN}\nexport MANGOHUD='1'\n{BLOCK_END}\n"
    assert read_block(path) == {"MANGOHUD": "1"}


def test_empty_vars_removes_block_entirely(tmp_path):
    path = tmp_path / ".profile"
    path.write_text(_SURROUNDING, encoding="utf-8", newline="")
    write_block(path, {"A": "1"})
    path.write_bytes(path.read_bytes() + _TRAILER.encode())

    assert write_block(path, {}) is True
    assert path.read_bytes().decode() == _SURROUNDING + _TRAILER
    assert BLOCK_BEGIN not in path.read_text(encoding="utf-8")
    assert read_block(path) == {}


def test_empty_vars_on_missing_file_does_not_create_it(tmp_path):
    path = tmp_path / ".profile"
    assert write_block(path, {}) is True
    assert not path.exists()


def test_read_ignores_exports_outside_the_block(tmp_path):
    path = tmp_path / ".profile"
    path.write_text(
        f"export OUTSIDE='1'\n{BLOCK_BEGIN}\nexport INSIDE='2'\n{BLOCK_END}\nexport AFTER='3'\n",
        encoding="utf-8",
    )
    assert read_block(path) == {"INSIDE": "2"}


@pytest.mark.parametrize(
    "value",
    [
        "plain",
        "",
        "has spaces here",
        "it's",
        "'leading and trailing'",
        "$HOME/not/expanded",
        'double "quotes" and $(cmd) `tick` \\ backslash',
        "a'\\''b",  # already looks escaped - must survive as literal text
    ],
)
def test_quoting_round_trips_and_is_single_quoted(tmp_path, value):
    path = tmp_path / ".profile"
    assert write_block(path, {"V": value}) is True
    line = next(ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("export V="))
    quoted = line[len("export V=") :]
    assert quoted.startswith("'") and quoted.endswith("'")
    assert quoted == "'" + value.replace("'", "'\\''") + "'"
    # nothing inside the single quotes can be interpreted by the shell
    assert "$" not in quoted.replace(value.replace("'", "'\\''"), "")
    assert read_block(path) == {"V": value}


@pytest.mark.parametrize("bad", ["", "1ABC", "A-B", "A B", "A=B", "$(rm -rf ~)", "A;B"])
def test_invalid_key_refuses_without_writing(tmp_path, bad):
    path = tmp_path / ".profile"
    path.write_text(_SURROUNDING, encoding="utf-8", newline="")
    with pytest.raises(ValueError):
        write_block(path, {"GOOD": "1", bad: "x"})
    assert path.read_bytes().decode() == _SURROUNDING
    assert not list(tmp_path.glob(".*.tmp"))

    missing = tmp_path / "never"
    with pytest.raises(ValueError):
        write_block(missing, {bad: "x"})
    assert not missing.exists()


# --- recommendation matrix ---------------------------------------------------------


@pytest.mark.parametrize(
    ("support", "session_type", "expected"),
    [
        (session.SYSTEMD, "x11", "environment.d"),
        (session.SYSTEMD, "wayland", "environment.d"),
        (session.NOT_SYSTEMD, "x11", "xsessionrc"),  # Cinnamon on LightDM (#47)
        (session.NOT_SYSTEMD, "X11", "xsessionrc"),
        (session.NOT_SYSTEMD, "wayland", "profile"),
        (session.NOT_SYSTEMD, "tty", "profile"),
        (session.NOT_SYSTEMD, None, "profile"),
        (session.NO_SYSTEMD, "x11", "xsessionrc"),
        (session.NO_SYSTEMD, "", "profile"),
        (session.UNKNOWN, "x11", "environment.d"),
        (session.UNKNOWN, None, "environment.d"),
        ("garbage", "x11", "environment.d"),
    ],
)
def test_recommended_target_matrix(monkeypatch, support, session_type, expected):
    if session_type is None:
        monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    else:
        monkeypatch.setenv("XDG_SESSION_TYPE", session_type)
    assert recommended_target(support, "Cinnamon") == expected
    assert recommended_target(support) == expected


def test_target_warning_only_when_selection_differs():
    assert env_targets.target_warning(session.NOT_SYSTEMD, "Cinnamon", "xsessionrc", "xsessionrc") == ""
    assert env_targets.target_warning(session.UNKNOWN, "", "profile", "environment.d") == ""
    msg = env_targets.target_warning(session.NOT_SYSTEMD, "Cinnamon", "environment.d", "xsessionrc")
    assert "Your Cinnamon session isn't started by systemd" in msg
    assert "~/.xsessionrc" in msg and "Switch the target" in msg
    msg = env_targets.target_warning(session.NO_SYSTEMD, "", "environment.d", "profile")
    assert "no systemd" in msg and "~/.profile" in msg
    msg = env_targets.target_warning(session.SYSTEMD, "GNOME", "profile", "environment.d")
    assert "started by systemd" in msg and "environment.d" in msg


def test_targets_table_is_complete():
    ids = [t.id for t in env_targets.targets()]
    assert tuple(ids) == env_targets.ENV_TARGETS == ("environment.d", "profile", "xsessionrc")
    for t in env_targets.targets():
        assert t.label and t.read_by and t.description and t.path.is_absolute()
    with pytest.raises(ValueError):
        env_targets.get_target("bogus")


# --- Steam launch options ------------------------------------------------------


def test_as_launch_prefix_quoting():
    assert as_launch_prefix({}) == ""
    assert as_launch_prefix({"MANGOHUD": "1"}) == "MANGOHUD=1 %command%"
    assert (
        as_launch_prefix({"A": "gpl,ngg", "B": "/usr/lib:/opt", "C": "x=y+z-1.0"})
        == "A='gpl,ngg' B=/usr/lib:/opt C=x=y+z-1.0 %command%"
    )
    assert as_launch_prefix({"S": "two words"}) == "S='two words' %command%"
    assert as_launch_prefix({"D": "$HOME"}) == "D='$HOME' %command%"
    assert as_launch_prefix({"Q": "it's"}) == "Q='it'\\''s' %command%"
    assert as_launch_prefix({"E": ""}) == "E='' %command%"
    # insertion order is kept (matches the editor rows); invalid keys are skipped
    assert as_launch_prefix({"Z": "1", "A": "2", "bad key": "3"}) == "Z=1 A=2 %command%"


# --- dispatch --------------------------------------------------------------------


@pytest.fixture
def patched_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(env_vars, "ENV_D_DIR", tmp_path / "environment.d")
    monkeypatch.setattr(env_targets, "PROFILE_PATH", tmp_path / ".profile")
    monkeypatch.setattr(env_targets, "XSESSIONRC_PATH", tmp_path / ".xsessionrc")
    return tmp_path


def test_read_write_target_dispatch(patched_paths):
    tmp = patched_paths
    assert read_target("environment.d") == {}
    assert read_target("profile") == {}
    assert read_target("xsessionrc") == {}

    assert write_target("environment.d", {"A": "1"}) is True
    conf = tmp / "environment.d" / env_vars.GAMING_CONF
    assert conf.exists() and 'A="1"' in conf.read_text(encoding="utf-8")
    assert env_targets.target_path("environment.d") == conf

    assert write_target("profile", {"B": "2"}) is True
    assert BLOCK_BEGIN in (tmp / ".profile").read_text(encoding="utf-8")
    assert not (tmp / ".xsessionrc").exists()

    assert write_target("xsessionrc", {"C": "3"}) is True
    assert "export C='3'" in (tmp / ".xsessionrc").read_text(encoding="utf-8")

    # each target reads back only its own file
    assert read_target("environment.d") == {"A": "1"}
    assert read_target("profile") == {"B": "2"}
    assert read_target("xsessionrc") == {"C": "3"}


def test_write_target_rejects_invalid_key_for_every_target(patched_paths):
    tmp = patched_paths
    for target in env_targets.ENV_TARGETS:
        with pytest.raises(ValueError):
            write_target(target, {"A B": "1"})
    assert not (tmp / "environment.d").exists()
    assert not (tmp / ".profile").exists()
    assert not (tmp / ".xsessionrc").exists()


def test_unknown_target_is_rejected(patched_paths):
    with pytest.raises(ValueError):
        read_target("bogus")
    with pytest.raises(ValueError):
        write_target("bogus", {"A": "1"})
