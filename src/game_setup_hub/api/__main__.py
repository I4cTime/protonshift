"""Allow ``python -m game_setup_hub.api`` (used by Electron's spawn)."""

from __future__ import annotations

from ._app import cli

if __name__ == "__main__":
    cli()
