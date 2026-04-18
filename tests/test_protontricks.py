"""Whitelist tests for the new subprocess input validators."""

from __future__ import annotations

import pytest

from game_setup_hub.protontricks import (
    ProtontricksValidationError,
    _validate_app_id,
    _validate_verb,
)


@pytest.mark.parametrize("good", ["1", "440", "1234567890"])
def test_validate_app_id_accepts_digits(good: str) -> None:
    assert _validate_app_id(good) == good


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "abc",
        "440; rm -rf ~",
        "440 1",
        "../440",
        "1234567890123",  # 13 digits — over our cap
    ],
)
def test_validate_app_id_rejects_garbage(bad: str) -> None:
    with pytest.raises(ProtontricksValidationError):
        _validate_app_id(bad)


def test_validate_verb_accepts_none() -> None:
    assert _validate_verb(None) is None


@pytest.mark.parametrize("good", ["vcrun2022", "dotnet48", "d3dx9", "core-fonts", "a.b.c"])
def test_validate_verb_accepts_alnum(good: str) -> None:
    assert _validate_verb(good) == good


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "vcrun;rm",
        "vcrun 2022",
        "$(whoami)",
        "../escape",
        "x" * 65,
    ],
)
def test_validate_verb_rejects_garbage(bad: str) -> None:
    with pytest.raises(ProtontricksValidationError):
        _validate_verb(bad)
