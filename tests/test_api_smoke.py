"""End-to-end FastAPI smoke + auth tests via TestClient.

Network calls are the wrong layer to exercise here; we just want to confirm
the app boots, auth enforcement works, CORS is locked down, and the
public-ish endpoints don't raise.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(api_token):
    from game_setup_hub.api import _state as api_state
    from game_setup_hub.api import app

    api_state.API_TOKEN = api_token
    return TestClient(app)


def test_health_works_without_auth(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_protected_endpoint_rejects_missing_token(client) -> None:
    resp = client.get("/system")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_protected_endpoint_rejects_wrong_token(client) -> None:
    resp = client.get("/system", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_protected_endpoint_accepts_correct_token(client, auth_headers) -> None:
    resp = client.get("/system", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "gpus" in body
    assert "power_profiles" in body


def test_steam_running_guard_on_launch_options(client, auth_headers, monkeypatch) -> None:
    """If Steam is running, edits to localconfig.vdf must be rejected."""
    from game_setup_hub.api import _state as api_state
    from game_setup_hub.api.routes import games as games_route

    monkeypatch.setattr(games_route, "is_steam_running", lambda: True)
    monkeypatch.setattr(api_state, "config_path", "fake.vdf", raising=False)
    monkeypatch.setattr(api_state, "steam_discovered", True, raising=False)

    resp = client.put(
        "/games/440/launch-options",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"options": "-novid"},
    )
    assert resp.status_code == 409
    assert "Steam is running" in resp.json()["detail"]


def test_open_path_rejects_outside_home(client, auth_headers) -> None:
    resp = client.post(
        "/open-path",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"path": "/etc/passwd"},
    )
    assert resp.status_code == 400


def test_delete_prefix_rejects_outside_home(client, auth_headers) -> None:
    resp = client.delete(
        "/games/12345/prefix",
        headers=auth_headers,
        params={"prefix_path": "/etc"},
    )
    assert resp.status_code == 400


def test_gamescope_build_returns_argv(client, auth_headers) -> None:
    resp = client.post(
        "/gamescope/build-cmd",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"output_width": 1920, "output_height": 1080},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["argv"][0] == "gamescope"
    assert body["argv"][-1] == "--"
    assert "1920" in body["command"]
