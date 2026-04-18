"""Internal helpers shared across routers."""

from __future__ import annotations

from ..heroic import HeroicGame
from ..lutris import LutrisGame
from ..steam import SteamGame
from ._models import HeroicGameResponse, LutrisGameResponse, SteamGameResponse


def steam_game_to_response(g: SteamGame) -> SteamGameResponse:
    return SteamGameResponse(
        app_id=g.app_id,
        name=g.name,
        install_dir=g.install_dir,
        last_played=g.last_played,
        library_path=str(g.library_path),
        compatdata_path=str(g.compatdata_path) if g.compatdata_path else None,
        has_compatdata=g.has_compatdata,
        install_path=str(g.install_path) if g.install_path else None,
    )


def heroic_game_to_response(g: HeroicGame) -> HeroicGameResponse:
    return HeroicGameResponse(
        app_id=g.app_id,
        name=g.name,
        store=g.store,
        install_path=str(g.install_path) if g.install_path else None,
        prefix_path=str(g.prefix_path) if g.prefix_path else None,
    )


def lutris_game_to_response(g: LutrisGame) -> LutrisGameResponse:
    return LutrisGameResponse(
        app_id=g.app_id,
        name=g.name,
        install_path=str(g.install_path) if g.install_path else None,
        prefix_path=str(g.prefix_path) if g.prefix_path else None,
    )
