"""Application entry point.

Boots a QML engine, registers the controllers as context properties, and loads
the root window. This is the whole shell — compare with the old Electron
``main.ts`` + ``preload.ts`` + FastAPI launch dance.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from . import __version__
from .controllers import (
    EnvController,
    GamescopeController,
    GamesController,
    LaunchOptionsController,
    MangoHudController,
    ScopeBuddyController,
    SystemController,
)

QML_DIR = Path(__file__).parent / "qml"


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ProtonShift")
    app.setOrganizationName("ProtonShift")
    app.setApplicationVersion(__version__)

    engine = QQmlApplicationEngine()

    # Make the `App` QML module (Theme singleton + Ps* components) importable.
    engine.addImportPath(str(QML_DIR))

    # Controllers exposed to QML. Kept alive by holding references here.
    gamescope = GamescopeController()
    library = GamesController()
    env = EnvController()
    launch = LaunchOptionsController()
    mangohud = MangoHudController()
    scopebuddy = ScopeBuddyController()
    system = SystemController()
    ctx = engine.rootContext()
    ctx.setContextProperty("gamescope", gamescope)
    ctx.setContextProperty("library", library)
    ctx.setContextProperty("env", env)
    ctx.setContextProperty("launch", launch)
    ctx.setContextProperty("mangohud", mangohud)
    ctx.setContextProperty("scopebuddy", scopebuddy)
    ctx.setContextProperty("system", system)
    ctx.setContextProperty("appVersion", __version__)

    engine.load(QUrl.fromLocalFile(str(QML_DIR / "main.qml")))
    if not engine.rootObjects():
        print("error: failed to load QML root object", file=sys.stderr)
        return 1

    # Tear the engine down while the controllers are still alive; otherwise
    # every binding re-evaluates against nulled context properties on exit and
    # floods stderr with harmless-but-ugly TypeErrors.
    app.aboutToQuit.connect(engine.deleteLater)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
