"""ProtonDB community rating lookup, with an on-disk cache.

ProtonDB publishes a per-app summary at
``https://www.protondb.com/api/v1/reports/summaries/<appid>.json`` (tier,
confidence, report count, trending tier). This module fetches it with stdlib
``urllib`` only, caches each summary as a JSON file under ``CACHE_DIR`` for
``CACHE_TTL`` seconds, and degrades gracefully: a network failure returns the
stale cached copy when one exists, and a 404 means "no reports yet" (tier
``pending``) rather than an error.

Privacy: a lookup sends the Steam app id to protondb.com. The controller gates
every call behind a user-visible opt-in setting; nothing here fires on its own.

Deliberately PySide-free (core/ rule) so ``tests/test_protondb.py`` can
exercise it with monkeypatched ``_get_json`` / ``CACHE_DIR`` / ``time.time``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http.client import HTTPException
from pathlib import Path

from .fsutil import atomic_write_text

PROTONDB_SUMMARY_URL = "https://www.protondb.com/api/v1/reports/summaries/{appid}.json"
PROTONDB_PAGE_URL = "https://www.protondb.com/app/{appid}"
USER_AGENT = "ProtonShift/1.2"
CACHE_DIR = Path("~/.cache/protonshift/protondb").expanduser()
CACHE_TTL = 24 * 3600
# Refuse absurd payloads — the real summary is ~150 bytes.
_MAX_BODY = 64 * 1024

# ProtonDB's tiers, best to worst. Anything else normalises to "pending".
TIERS = ("platinum", "gold", "silver", "bronze", "borked", "pending")

_TIER_LABELS = {
    "platinum": "Platinum",
    "gold": "Gold",
    "silver": "Silver",
    "bronze": "Bronze",
    "borked": "Borked",
    "pending": "Pending",
}

# Theme.qml token *names* (not colors) — the page resolves them against the
# singleton so core/ never holds a hex value.
_TIER_COLOR_KEYS = {
    "platinum": "tierPlatinum",
    "gold": "tierGold",
    "silver": "tierSilver",
    "bronze": "tierBronze",
    "borked": "tierBorked",
    "pending": "tierPending",
}


class ProtonDbError(RuntimeError):
    """ProtonDB could not be reached or returned something unusable."""


@dataclass(frozen=True)
class ProtonDbSummary:
    appid: int
    tier: str
    confidence: str
    score: float
    total: int
    trending_tier: str
    best_reported_tier: str
    fetched_at: float

    @property
    def page_url(self) -> str:
        return PROTONDB_PAGE_URL.format(appid=self.appid)

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) > CACHE_TTL

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_tier(value: object) -> str:
    """Lower-case a tier string; unknown/missing values become ``pending``."""
    tier = str(value or "").strip().lower()
    return tier if tier in TIERS else "pending"


def tier_label(tier: str) -> str:
    """Human label for a tier ("Pending" for pending/unknown)."""
    return _TIER_LABELS[normalize_tier(tier)]


def tier_color_key(tier: str) -> str:
    """Name of the Theme.qml color token for a tier (``tierGold`` ...)."""
    return _TIER_COLOR_KEYS[normalize_tier(tier)]


def age_label(fetched_at: float, now: float | None = None) -> str:
    """"updated 3 h ago"-style caption for a cache timestamp (empty if unset)."""
    if not fetched_at:
        return ""
    age = max(0.0, (time.time() if now is None else now) - fetched_at)
    if age < 60:
        return "updated just now"
    if age < 3600:
        return f"updated {int(age // 60)} min ago"
    if age < 86400:
        return f"updated {int(age // 3600)} h ago"
    return f"updated {int(age // 86400)} d ago"


def _check_appid(appid: object) -> int:
    """App ids come from appmanifest filenames — coerce to a positive int so a
    cache path can only ever be ``<digits>.json`` under CACHE_DIR."""
    try:
        value = int(str(appid).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid app id: {appid!r}") from exc
    if value <= 0:
        raise ValueError(f"invalid app id: {appid!r}")
    return value


# --- network ------------------------------------------------------------------


def _get_json(url: str, timeout: float = 10) -> dict | None:
    """GET ``url`` and decode JSON. ``None`` on 404 (no reports); raises
    :class:`ProtonDbError` on any other failure. Monkeypatched in tests."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        # https only, fixed host: the URL is built from a validated int app id.
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(_MAX_BODY + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise ProtonDbError(f"ProtonDB returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, HTTPException, TimeoutError, OSError) as exc:
        raise ProtonDbError(f"ProtonDB unreachable: {exc}") from exc
    if len(body) > _MAX_BODY:
        raise ProtonDbError("ProtonDB response too large")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtonDbError("ProtonDB returned invalid JSON") from exc
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ProtonDbError("ProtonDB returned an unexpected payload")
    return data


def parse_summary(appid: int, data: dict | None, *, fetched_at: float | None = None) -> ProtonDbSummary:
    """Build a summary from the API payload. Missing keys fall back to
    pending/empty/zero; ``None`` (a 404) is a "no reports yet" summary."""
    appid = _check_appid(appid)
    data = data if isinstance(data, dict) else {}
    tier = normalize_tier(data.get("tier"))
    try:
        score = float(data.get("score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    try:
        total = int(data.get("total") or 0)
    except (TypeError, ValueError):
        total = 0
    return ProtonDbSummary(
        appid=appid,
        tier=tier,
        confidence=str(data.get("confidence") or "").strip().lower(),
        score=score,
        total=max(0, total),
        trending_tier=normalize_tier(data.get("trendingTier")) if data.get("trendingTier") else tier,
        best_reported_tier=normalize_tier(data.get("bestReportedTier")) if data.get("bestReportedTier") else tier,
        fetched_at=time.time() if fetched_at is None else fetched_at,
    )


def fetch_summary(appid: int) -> ProtonDbSummary:
    """Fetch a fresh summary from ProtonDB (no cache)."""
    appid = _check_appid(appid)
    data = _get_json(PROTONDB_SUMMARY_URL.format(appid=appid))
    return parse_summary(appid, data)


# --- cache --------------------------------------------------------------------


def _cache_path(appid: int) -> Path:
    return CACHE_DIR / f"{_check_appid(appid)}.json"


def load_cached(appid: int) -> ProtonDbSummary | None:
    """The cached summary for ``appid`` (stale or not), or ``None``."""
    path = _cache_path(appid)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        fetched_at = float(raw.get("fetched_at") or 0.0)
        score = float(raw.get("score") or 0.0)
        total = int(raw.get("total") or 0)
    except (TypeError, ValueError):
        return None
    if fetched_at <= 0:
        return None
    return ProtonDbSummary(
        appid=_check_appid(appid),
        tier=normalize_tier(raw.get("tier")),
        confidence=str(raw.get("confidence") or ""),
        score=score,
        total=max(0, total),
        trending_tier=normalize_tier(raw.get("trending_tier")),
        best_reported_tier=normalize_tier(raw.get("best_reported_tier")),
        fetched_at=fetched_at,
    )


def save_cached(summary: ProtonDbSummary) -> None:
    """Atomically write ``summary`` to its cache file. Cache failures are
    non-fatal: the lookup already succeeded, we just won't remember it."""
    try:
        atomic_write_text(_cache_path(summary.appid), json.dumps(summary.to_dict(), indent=2))
    except OSError:
        pass


def lookup(appid: int, force: bool = False) -> ProtonDbSummary:
    """Cached summary when fresh (unless ``force``); otherwise fetch and cache.

    On a network error the stale cached copy is returned if there is one;
    with no cache at all the :class:`ProtonDbError` propagates.
    """
    appid = _check_appid(appid)
    cached = load_cached(appid)
    if cached is not None and not force and not cached.is_stale:
        return cached
    try:
        fresh = fetch_summary(appid)
    except ProtonDbError:
        if cached is not None:
            return cached
        raise
    save_cached(fresh)
    return fresh
