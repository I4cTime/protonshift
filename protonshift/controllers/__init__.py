"""QObject controllers — the bridge layer between the Python core and QML.

Each controller wraps one slice of the domain core and exposes it to QML as
``Property``/``Signal``/``Slot`` members. This replaces the old FastAPI routes:
same domain logic behind it, but called in-process instead of over HTTP.
"""

from .display_controller import DisplayController
from .env_controller import EnvController
from .game_tools_controller import GameToolsController
from .games_controller import GamesController
from .gamescope_controller import GamescopeController
from .launch_controller import LaunchOptionsController
from .mangohud_controller import MangoHudController
from .per_app_scopebuddy_controller import PerAppScopeBuddyController
from .per_game_mangohud_controller import PerGameMangoHudController
from .protontricks_controller import ProtontricksController
from .scopebuddy_controller import ScopeBuddyController
from .system_controller import SystemController

__all__ = [
    "DisplayController",
    "EnvController",
    "GameToolsController",
    "GamescopeController",
    "GamesController",
    "LaunchOptionsController",
    "MangoHudController",
    "PerAppScopeBuddyController",
    "PerGameMangoHudController",
    "ProtontricksController",
    "ScopeBuddyController",
    "SystemController",
]
