"""ProtonDB lookup core: parsing, cache round-trip, TTL, and fallbacks.

Qt-free and network-free: ``_get_json`` is monkeypatched for every call that
would touch protondb.com, ``CACHE_DIR`` points at ``tmp_path``, and staleness
is driven by monkeypatching ``time.time``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from protonshift.core import protondb

APPID = 620
FULL = {
    "bestReportedTier": "platinum",
    "confidence": "strong",
    "score": 0.91,
    "tier": "gold",
    "total": 1234,
    "trendingTier": "platinum",
}
THEME_QML = Path(__file__).resolve().parent.parent / "protonshift" / "qml" / "App" / "Theme.qml"


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(protondb, "CACHE_DIR", tmp_path / "protondb")


def _freeze(monkeypatch, now: float) -> None:
    monkeypatch.setattr(protondb.time, "time", lambda: now)


def _serve(monkeypatch, payload, calls: list | None = None):
    def fake(url, timeout=10):
        if calls is not None:
            calls.append(url)
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(protondb, "_get_json", fake)


# --- parse_summary ------------------------------------------------------------


def test_parse_full_payload(monkeypatch):
    _freeze(monkeypatch, 1_000.0)
    s = protondb.parse_summary(APPID, FULL)
    assert s.appid == APPID
    assert s.tier == "gold"
    assert s.confidence == "strong"
    assert s.score == pytest.approx(0.91)
    assert s.total == 1234
    assert s.trending_tier == "platinum"
    assert s.best_reported_tier == "platinum"
    assert s.fetched_at == 1_000.0
    assert s.page_url == "https://www.protondb.com/app/620"


def test_parse_partial_payload_is_tolerant():
    s = protondb.parse_summary(APPID, {"tier": "Silver", "total": "7"})
    assert s.tier == "silver"
    assert s.total == 7
    assert s.confidence == ""
    assert s.score == 0.0
    # missing trending/best fall back to the overall tier, not "pending"
    assert s.trending_tier == "silver"
    assert s.best_reported_tier == "silver"


def test_parse_garbage_values_do_not_raise():
    s = protondb.parse_summary(APPID, {"tier": "mythril", "score": "n/a", "total": None})
    assert s.tier == "pending"
    assert s.score == 0.0
    assert s.total == 0


def test_404_means_pending_not_error(monkeypatch):
    _serve(monkeypatch, None)
    s = protondb.fetch_summary(APPID)
    assert s.tier == "pending"
    assert s.total == 0
    assert protondb.tier_label(s.tier) == "Pending"


@pytest.mark.parametrize("bad", ["", "abc", "-1", "0", "..", "1/2"])
def test_invalid_appid_rejected(bad):
    with pytest.raises(ValueError):
        protondb.parse_summary(bad, FULL)
    with pytest.raises(ValueError):
        protondb.load_cached(bad)


# --- cache ----------------------------------------------------------------------


def test_cache_round_trip(monkeypatch, tmp_path):
    _freeze(monkeypatch, 5_000.0)
    s = protondb.parse_summary(APPID, FULL)
    protondb.save_cached(s)
    path = tmp_path / "protondb" / "620.json"
    assert path.is_file()
    assert json.loads(path.read_text())["tier"] == "gold"
    assert protondb.load_cached(APPID) == s
    assert protondb.load_cached(999) is None


def test_staleness_follows_ttl(monkeypatch):
    _freeze(monkeypatch, 10_000.0)
    s = protondb.parse_summary(APPID, FULL)
    assert not s.is_stale
    _freeze(monkeypatch, 10_000.0 + protondb.CACHE_TTL - 1)
    assert not s.is_stale
    _freeze(monkeypatch, 10_000.0 + protondb.CACHE_TTL + 1)
    assert s.is_stale


def test_corrupt_cache_file_is_ignored(tmp_path):
    (tmp_path / "protondb").mkdir()
    (tmp_path / "protondb" / "620.json").write_text("{not json")
    assert protondb.load_cached(APPID) is None


# --- lookup ---------------------------------------------------------------------


def test_lookup_uses_fresh_cache_without_network(monkeypatch):
    _freeze(monkeypatch, 20_000.0)
    protondb.save_cached(protondb.parse_summary(APPID, FULL))
    calls: list = []
    _serve(monkeypatch, {"tier": "borked"}, calls)
    s = protondb.lookup(APPID)
    assert s.tier == "gold"
    assert calls == []


def test_lookup_refetches_when_stale_and_caches(monkeypatch):
    _freeze(monkeypatch, 20_000.0)
    protondb.save_cached(protondb.parse_summary(APPID, FULL))
    _freeze(monkeypatch, 20_000.0 + protondb.CACHE_TTL + 5)
    calls: list = []
    _serve(monkeypatch, {"tier": "platinum", "total": 2000, "confidence": "strong"}, calls)
    s = protondb.lookup(APPID)
    assert s.tier == "platinum"
    assert calls == [protondb.PROTONDB_SUMMARY_URL.format(appid=APPID)]
    cached = protondb.load_cached(APPID)
    assert cached is not None and cached.tier == "platinum"
    assert cached.fetched_at == 20_000.0 + protondb.CACHE_TTL + 5


def test_lookup_force_bypasses_fresh_cache(monkeypatch):
    _freeze(monkeypatch, 30_000.0)
    protondb.save_cached(protondb.parse_summary(APPID, FULL))
    calls: list = []
    _serve(monkeypatch, {"tier": "bronze"}, calls)
    assert protondb.lookup(APPID, force=True).tier == "bronze"
    assert len(calls) == 1


def test_lookup_falls_back_to_stale_cache_on_network_error(monkeypatch):
    _freeze(monkeypatch, 40_000.0)
    protondb.save_cached(protondb.parse_summary(APPID, FULL))
    _freeze(monkeypatch, 40_000.0 + 2 * protondb.CACHE_TTL)
    _serve(monkeypatch, protondb.ProtonDbError("boom"))
    s = protondb.lookup(APPID)
    assert s.tier == "gold"
    assert s.is_stale


def test_lookup_raises_when_no_cache_and_network_fails(monkeypatch):
    _serve(monkeypatch, protondb.ProtonDbError("boom"))
    with pytest.raises(protondb.ProtonDbError):
        protondb.lookup(APPID)
    assert protondb.load_cached(APPID) is None


# --- labels / tokens ------------------------------------------------------------


@pytest.mark.parametrize(
    ("tier", "label", "key"),
    [
        ("platinum", "Platinum", "tierPlatinum"),
        ("gold", "Gold", "tierGold"),
        ("silver", "Silver", "tierSilver"),
        ("bronze", "Bronze", "tierBronze"),
        ("borked", "Borked", "tierBorked"),
        ("pending", "Pending", "tierPending"),
        ("GOLD", "Gold", "tierGold"),
        ("", "Pending", "tierPending"),
        ("unobtainium", "Pending", "tierPending"),
    ],
)
def test_tier_label_and_color_key(tier, label, key):
    assert protondb.tier_label(tier) == label
    assert protondb.tier_color_key(tier) == key


def test_tier_color_keys_exist_in_theme():
    """Every token name core/ hands to QML must be a real Theme.qml property."""
    theme = THEME_QML.read_text(encoding="utf-8")
    for tier in protondb.TIERS:
        key = protondb.tier_color_key(tier)
        assert f"readonly property color {key}:" in theme, key
    assert "readonly property color tierInk:" in theme


def test_age_label():
    assert protondb.age_label(0) == ""
    assert protondb.age_label(1000, now=1030) == "updated just now"
    assert protondb.age_label(1000, now=1000 + 5 * 60) == "updated 5 min ago"
    assert protondb.age_label(1000, now=1000 + 3 * 3600) == "updated 3 h ago"
    assert protondb.age_label(1000, now=1000 + 2 * 86400) == "updated 2 d ago"
