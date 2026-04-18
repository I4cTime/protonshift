"""Liveness/readiness probe."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Readiness probe. Exempt from auth so Electron can poll on startup."""
    return {"status": "ok"}
