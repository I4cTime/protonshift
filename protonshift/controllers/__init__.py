"""QObject controllers — the bridge layer between the Python core and QML.

Each controller wraps one slice of the domain core and exposes it to QML as
``Property``/``Signal``/``Slot`` members. This replaces the old FastAPI routes:
same domain logic behind it, but called in-process instead of over HTTP.
"""

from .gamescope_controller import GamescopeController

__all__ = ["GamescopeController"]
