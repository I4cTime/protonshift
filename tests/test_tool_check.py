"""Smoke tests for tool_check fallback paths.

We can't assume any specific tool exists in CI, so the assertions are about
behaviour (boolean, no crash) rather than concrete results.
"""

from __future__ import annotations

from game_setup_hub.tool_check import find_tool, is_tool_available


def test_is_tool_available_returns_bool() -> None:
    assert isinstance(is_tool_available("python3"), bool)


def test_find_tool_returns_path_or_none() -> None:
    result = find_tool("python3")
    assert result is None or isinstance(result, str)


def test_unknown_tool_is_unavailable() -> None:
    assert is_tool_available("no-such-tool-zzzzz") is False
    assert find_tool("no-such-tool-zzzzz") is None
