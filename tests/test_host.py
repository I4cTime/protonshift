"""Host-command plumbing: extra env vars must reach the host command.

``flatpak-spawn --host`` doesn't forward the caller's environment, so inside a
sandbox extra variables have to travel as ``--env=`` flags. Qt-free.
"""

from __future__ import annotations

import subprocess

import pytest

from protonshift.core import host


def test_host_argv_sandboxed_adds_env_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "in_flatpak", lambda: True)
    assert host.host_argv(["winetricks", "vcrun2019"], {"A": "1", "B": "x y"}) == [
        "flatpak-spawn", "--host", "--env=A=1", "--env=B=x y", "winetricks", "vcrun2019",
    ]


def test_host_argv_native_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "in_flatpak", lambda: False)
    assert host.host_argv(["jq", "."], {"A": "1"}) == ["jq", "."]


def test_host_run_native_merges_extra_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "in_flatpak", lambda: False)
    monkeypatch.setenv("PS_TEST_KEEP", "kept")
    seen: dict = {}

    def fake_run(argv, **kwargs):
        seen.update(kwargs, argv=argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(host.subprocess, "run", fake_run)
    host.host_run(["true"], extra_env={"A": "1"})
    assert seen["argv"] == ["true"]
    assert seen["env"]["A"] == "1"
    assert seen["env"]["PS_TEST_KEEP"] == "kept"


def test_host_run_sandboxed_sends_env_as_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "in_flatpak", lambda: True)
    seen: dict = {}

    def fake_run(argv, **kwargs):
        seen.update(kwargs, argv=argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(host.subprocess, "run", fake_run)
    host.host_run(["true"], extra_env={"A": "1"})
    assert seen["argv"] == ["flatpak-spawn", "--host", "--env=A=1", "true"]
    assert "env" not in seen
