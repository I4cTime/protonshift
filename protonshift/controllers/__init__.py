"""QObject controllers — the bridge layer between the Python core and QML.

Each controller wraps one slice of the domain core and exposes it to QML as
``Property``/``Signal``/``Slot`` members. This replaces the old FastAPI routes:
same domain logic behind it, but called in-process instead of over HTTP.
"""

from .about_controller import AboutController
from .display_controller import DisplayController
from .env_controller import EnvController
from .fixes_controller import FixesController
from .game_tools_controller import GameToolsController
from .gamepad_controller import GamepadController
from .games_controller import GamesController
from .gamescope_controller import GamescopeController
from .ge_proton_controller import GeProtonController
from .heroic_controller import HeroicController
from .launch_controller import LaunchOptionsController
from .mangohud_controller import MangoHudController
from .per_app_scopebuddy_controller import PerAppScopeBuddyController
from .per_game_mangohud_controller import PerGameMangoHudController
from .profiles_controller import ProfilesController
from .protondb_controller import ProtonDbController
from .protontricks_controller import ProtontricksController
from .saves_controller import SavesController
from .scopebuddy_controller import ScopeBuddyController
from .scopebuddy_envvars_controller import ScopeBuddyEnvvarsController
from .sound_controller import SoundController
from .system_controller import SystemController
from .theme_controller import ThemeController

__all__ = [
    "AboutController",
    "DisplayController",
    "EnvController",
    "FixesController",
    "GameToolsController",
    "GamepadController",
    "GamesController",
    "GamescopeController",
    "GeProtonController",
    "HeroicController",
    "LaunchOptionsController",
    "MangoHudController",
    "PerAppScopeBuddyController",
    "PerGameMangoHudController",
    "ProfilesController",
    "ProtonDbController",
    "ProtontricksController",
    "SavesController",
    "ScopeBuddyController",
    "ScopeBuddyEnvvarsController",
    "SoundController",
    "SystemController",
    "ThemeController",
]
