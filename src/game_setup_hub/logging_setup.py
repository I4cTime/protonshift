"""Logging configuration for the ProtonShift backend.

Centralised so every entry point (api server, tests, ad-hoc scripts) gets
the same format. Honors ``PROTONSHIFT_LOG_LEVEL`` (default ``INFO``).
"""

from __future__ import annotations

import logging
import os
import sys


def configure(level: str | None = None) -> None:
    """Configure root logging once. Idempotent."""
    chosen = (level or os.environ.get("PROTONSHIFT_LOG_LEVEL") or "INFO").upper()
    numeric = getattr(logging, chosen, logging.INFO)

    root = logging.getLogger()
    if getattr(configure, "_done", False):
        root.setLevel(numeric)
        return

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(numeric)

    # Tame noisy 3rd-party loggers.
    for noisy in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    configure._done = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Module-level helper so callers don't need to import :mod:`logging`."""
    return logging.getLogger(name)
