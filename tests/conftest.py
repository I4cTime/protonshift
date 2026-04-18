"""Shared fixtures.

Tests must never write outside the workspace and must not call out to a real
Steam install. We pin ``HOME`` to a temp dir for every test so any code that
resolves ``Path.home()`` lands in an isolated sandbox.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch) -> Path:
    """Redirect HOME so module-level ``Path.home()`` constants stay safe.

    Several modules cache ``Path.home() / ...`` at import time. We reload them
    after the patch so their constants point at the per-test sandbox.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    import importlib
    for mod_name in (
        "game_setup_hub.env_vars",
        "game_setup_hub.profiles_storage",
        "game_setup_hub.fixes",
        "game_setup_hub.saves",
        "game_setup_hub.mangohud",
    ):
        try:
            importlib.reload(__import__(mod_name, fromlist=["_"]))
        except ModuleNotFoundError:
            pass
    return fake_home


@pytest.fixture
def api_token(monkeypatch) -> str:
    """Set a known token and pin it on the api state module."""
    token = "test-token-abc123"
    monkeypatch.setenv("PROTONSHIFT_API_TOKEN", token)

    from game_setup_hub.api import _state as api_state

    monkeypatch.setattr(api_state, "API_TOKEN", token, raising=False)
    return token


@pytest.fixture
def auth_headers(api_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


def _ensure_pythonpath() -> None:
    """Make `src/` importable when pytest is run from the repo root."""
    src = Path(__file__).resolve().parents[1] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_ensure_pythonpath()
