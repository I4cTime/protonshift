"""Router collection. Add new routers here so ``_app`` picks them up."""

from __future__ import annotations

from fastapi import APIRouter

from . import games, health, heroic, mangohud, profiles, saves, system, utility

all_routers: list[APIRouter] = [
    health.router,
    games.router,
    system.router,
    saves.router,
    mangohud.router,
    heroic.router,
    profiles.router,
    utility.router,
]
