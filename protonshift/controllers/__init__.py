"""QObject controllers — the bridge layer between the Python core and QML.

Each controller wraps one slice of the domain core and exposes it to QML as
``Property``/``Signal``/``Slot`` members. This replaces the old FastAPI routes:
same domain logic behind it, but called in-process instead of over HTTP.
"""

from .env_controller import EnvController
from .games_controller import GamesController
from .gamescope_controller import GamescopeController
from .launch_controller import LaunchOptionsController

__all__ = [
    "EnvController",
    "GamescopeController",
    "GamesController",
    "LaunchOptionsController",
]
