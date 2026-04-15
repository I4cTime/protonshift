"""Lutris game discovery from pga.db and games YAML."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


LUTRIS_ROOTS = [
    Path.home() / ".local" / "share" / "lutris",
    Path.home() / ".var" / "app" / "net.lutris.Lutris" / "data" / "lutris",
]


@dataclass
class LutrisGame:
    app_id: str  # slug
    name: str
    install_path: Path | None
    prefix_path: Path | None

    @property
    def compatdata_path(self) -> Path | None:
        """Wine prefix, analogous to Steam compatdata."""
        return self.prefix_path


def _get_pga_path() -> Path | None:
    for root in LUTRIS_ROOTS:
        pga = root / "pga.db"
        if pga.exists():
            return pga
    return None


def _get_prefix_from_yaml(slug: str) -> Path | None:
    """Extract prefix path from Lutris game YAML (simple regex, no PyYAML)."""
    for root in LUTRIS_ROOTS:
        games_dir = root / "games"
        if not games_dir.exists():
            continue
        for yml in games_dir.glob(f"*-{slug}.yml"):
            try:
                text = yml.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"^\s*prefix:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
                if m:
                    p = Path(m.group(1).strip())
                    if p.exists():
                        return p
            except (OSError, UnicodeDecodeError):
                pass
    return None


def discover_lutris_games() -> list[LutrisGame]:
    """Discover installed Lutris games from pga.db."""
    pga_path = _get_pga_path()
    if not pga_path:
        return []

    games: list[LutrisGame] = []
    try:
        conn = sqlite3.connect(str(pga_path), timeout=2)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT name, slug, directory, installed FROM games "
            "WHERE installed = 1 AND slug IS NOT NULL AND slug != '' ORDER BY name"
        )
        for row in cur:
            name = row["name"] or row["slug"]
            slug = row["slug"]
            dir_val = row["directory"]
            directory = Path(dir_val) if dir_val else None
            if directory and not directory.exists():
                directory = None
            prefix_path = _get_prefix_from_yaml(slug)
            games.append(
                LutrisGame(
                    app_id=slug,
                    name=str(name),
                    install_path=directory,
                    prefix_path=prefix_path,
                )
            )
        conn.close()
    except (sqlite3.Error, KeyError):
        pass

    return games
