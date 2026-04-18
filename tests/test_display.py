"""Whitelist tests for the display.set_resolution input validators."""

from __future__ import annotations

from unittest.mock import patch

from game_setup_hub.display import MonitorInfo, set_resolution


def _fake_monitor(name: str = "HDMI-1") -> MonitorInfo:
    return MonitorInfo(
        name=name,
        connected=True,
        resolution="1920x1080",
        refresh_rate="60",
        primary=True,
        position="+0+0",
    )


def test_set_resolution_rejects_shell_metachars() -> None:
    with patch("game_setup_hub.display.get_monitors", return_value=[_fake_monitor()]):
        assert set_resolution("HDMI-1; rm -rf ~", 1920, 1080) is False
        assert set_resolution("$(id)", 1920, 1080) is False
        assert set_resolution("HDMI 1", 1920, 1080) is False


def test_set_resolution_rejects_unknown_monitor() -> None:
    with patch("game_setup_hub.display.get_monitors", return_value=[_fake_monitor("HDMI-1")]):
        assert set_resolution("DP-99", 1920, 1080) is False


def test_set_resolution_rejects_oversize_dimensions() -> None:
    with patch("game_setup_hub.display.get_monitors", return_value=[_fake_monitor()]):
        assert set_resolution("HDMI-1", 99999, 1080) is False
        assert set_resolution("HDMI-1", 1920, 0) is False
        assert set_resolution("HDMI-1", -1, 1080) is False


def test_set_resolution_rejects_silly_refresh() -> None:
    with patch("game_setup_hub.display.get_monitors", return_value=[_fake_monitor()]):
        assert set_resolution("HDMI-1", 1920, 1080, refresh=10000) is False
        assert set_resolution("HDMI-1", 1920, 1080, refresh=-1) is False


def test_set_resolution_returns_false_when_xrandr_missing() -> None:
    with patch("game_setup_hub.display.get_monitors", return_value=[_fake_monitor()]), \
         patch("game_setup_hub.display.find_tool", return_value=None):
        assert set_resolution("HDMI-1", 1920, 1080) is False
