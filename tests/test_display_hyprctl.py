"""Hyprland display backend: parse ``hyprctl monitors -j`` and build the apply command."""

from __future__ import annotations

import json

import pytest

from protonshift.core import display

_MONITORS = [
    {
        "id": 0, "name": "eDP-1", "width": 2560, "height": 1600, "refreshRate": 60.00200,
        "x": 0, "y": 0, "scale": 1.25, "focused": True, "disabled": False,
        "availableModes": ["2560x1600@60.00Hz", "2560x1600@165.00Hz", "1920x1200@60.00Hz"],
    },
    {
        "id": 1, "name": "HDMI-A-1", "width": 3840, "height": 2160, "refreshRate": 120.0,
        "x": 2048, "y": 0, "scale": 1.0, "focused": False, "disabled": False,
        "availableModes": ["3840x2160@120.00Hz", "3840x2160@60.00Hz", "weird"],
    },
]


def test_parse_hyprctl_modes_and_current() -> None:
    outs = display.parse_hyprctl(json.dumps(_MONITORS))
    assert [o.name for o in outs] == ["eDP-1", "HDMI-A-1"]
    edp = outs[0]
    assert edp.primary and edp.enabled
    assert [m.key for m in edp.modes] == [
        "2560x1600@60.000", "2560x1600@165.000", "1920x1200@60.000",
    ]
    # 60.00200 (active) snaps to the listed 60.00 mode, so Apply stays disabled
    assert edp.current is not None and edp.current.key == "2560x1600@60.000"
    hdmi = outs[1]
    assert len(hdmi.modes) == 2  # the malformed entry is skipped
    assert hdmi.current.key == "3840x2160@120.000"


def test_parse_hyprctl_tolerates_garbage() -> None:
    assert display.parse_hyprctl("not json") == []
    assert display.parse_hyprctl(json.dumps({"name": "x"})) == []
    assert display.parse_hyprctl(json.dumps([{"width": 1}])) == []


def test_parse_hyprctl_unlisted_active_mode_is_added() -> None:
    mons = [{"name": "DP-1", "width": 1280, "height": 720, "refreshRate": 50.0, "availableModes": []}]
    (out,) = display.parse_hyprctl(json.dumps(mons))
    assert out.current is not None and out.current.key == "1280x720@50.000"
    assert [m.key for m in out.modes] == ["1280x720@50.000"]


def test_detect_backend_prefers_hyprctl_on_hyprland(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    monkeypatch.setattr(display, "find_tool", lambda n: "/usr/bin/" + n if n in ("hyprctl", "xrandr") else None)
    assert display.detect_backend() == "hyprctl"
    # without hyprctl installed we still fall back to xrandr under XWayland
    monkeypatch.setattr(display, "find_tool", lambda n: "/usr/bin/xrandr" if n == "xrandr" else None)
    assert display.detect_backend() == "xrandr"


def test_set_mode_hyprctl_keeps_position_and_scale(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class _R:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run(argv, **_kw):
        calls.append(list(argv))
        # `hyprctl monitors -j` lists the outputs; a successful keyword prints "ok"
        return _R(json.dumps(_MONITORS) if argv[1] == "monitors" else "ok")

    monkeypatch.setattr(display, "detect_backend", lambda: "hyprctl")
    monkeypatch.setattr(display, "host_run", fake_run)
    ok, msg = display.set_mode("eDP-1", 2560, 1600, 165.0)
    assert ok, msg
    assert calls[-1] == ["hyprctl", "keyword", "monitor", "eDP-1,2560x1600@165,0x0,1.25"]


# --- Lua-config Hyprland: the mode is set through `hyprctl eval` ---------------


def test_hypr_monitor_lua() -> None:
    from protonshift.core.display import hypr_monitor_lua

    assert hypr_monitor_lua("eDP-1", "2560x1600@165", "0x0", "1.25") == (
        'hl.monitor({ output = "eDP-1", mode = "2560x1600@165", position = "0x0", scale = 1.25 })'
    )
    assert hypr_monitor_lua("HDMI-A-1", "3440x1440@59.94", "-3440x0", "1") is not None
    assert hypr_monitor_lua("DP-1", "1920x1080", "auto", "1") is not None


def test_hypr_monitor_lua_refuses_unsafe_input() -> None:
    from protonshift.core.display import hypr_monitor_lua

    assert hypr_monitor_lua('eDP-1" }) os.execute("x', "1920x1080@60", "0x0", "1") is None
    assert hypr_monitor_lua("eDP-1", "1920x1080@60; evil", "0x0", "1") is None
    assert hypr_monitor_lua("eDP-1", "1920x1080@60", "0x0", "1) evil(") is None


def test_hypr_set_mode_falls_back_to_eval(monkeypatch) -> None:
    import subprocess

    from protonshift.core import display

    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        out = "ok" if argv[1] == "eval" else "keyword can't work with non-legacy parsers. Use eval."
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    monkeypatch.setattr(display, "host_run", fake_run)
    ok, _ = display._hypr_set_mode("eDP-1", "2560x1600@165", "0x0", "1.25", "done")
    assert ok
    assert [c[1] for c in calls] == ["keyword", "eval"]


def test_hypr_set_mode_reports_a_refusal(monkeypatch) -> None:
    import subprocess

    from protonshift.core import display

    monkeypatch.setattr(
        display, "host_run",
        lambda argv, **_k: subprocess.CompletedProcess(argv, 0, stdout="invalid mode", stderr=""),
    )
    ok, message = display._hypr_set_mode("eDP-1", "2560x1600@999", "0x0", "1", "done")
    assert not ok
    assert "invalid mode" in message
