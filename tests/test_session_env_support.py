"""#47: environment.d silently does nothing on non-systemd desktop sessions.

The core probe classifies the session from ``systemctl --user is-active
graphical-session.target``; the Environment page shows a warning for the
classes where the file is never read. Qt-free: ``host_run`` is monkeypatched.
"""

from __future__ import annotations

import subprocess

import pytest

from protonshift.core import session


def _cp(stdout: str, rc: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr="")


@pytest.mark.parametrize(
    ("stdout", "rc", "expected"),
    [
        ("active\n", 0, session.SYSTEMD),  # GNOME / Plasma / uwsm
        ("inactive\n", 3, session.NOT_SYSTEMD),  # Cinnamon on LMDE (#47)
        ("failed\n", 3, session.NOT_SYSTEMD),
        ("", 1, session.NO_SYSTEMD),  # Flatpak: host has no systemctl
        ("garbage\n", 0, session.UNKNOWN),
    ],
)
def test_classification(monkeypatch, stdout, rc, expected):
    monkeypatch.setattr(session, "host_run", lambda *a, **k: _cp(stdout, rc))
    assert session.session_env_support() == expected


def test_missing_systemctl_is_no_systemd(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(session, "host_run", boom)
    assert session.session_env_support() == session.NO_SYSTEMD


def test_timeout_is_unknown_not_a_false_alarm(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="systemctl", timeout=5)

    monkeypatch.setattr(session, "host_run", slow)
    assert session.session_env_support() == session.UNKNOWN


def test_desktop_name_strips_x_prefix(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "X-Cinnamon")
    assert session.current_desktop() == "Cinnamon"
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE:Unity")
    assert session.current_desktop() == "KDE"
    monkeypatch.delenv("XDG_CURRENT_DESKTOP")
    assert session.current_desktop() == ""


def test_warning_only_for_broken_classes():
    assert session.env_d_warning(session.SYSTEMD) == ""
    assert session.env_d_warning(session.UNKNOWN) == ""
    msg = session.env_d_warning(session.NOT_SYSTEMD, "Cinnamon")
    assert msg.startswith("Your Cinnamon session isn't started by systemd")
    assert "%command%" in msg and ".xsessionrc" in msg
    assert "no systemd" in session.env_d_warning(session.NO_SYSTEMD)
