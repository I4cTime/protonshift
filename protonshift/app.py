"""Application entry point.

Boots a QML engine, registers the controllers as context properties, and loads
the root window. This is the whole shell - compare with the old Electron
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
    AboutController,
    DisplayController,
    EnvController,
    FixesController,
    GamepadController,
    GamesController,
    GamescopeController,
    GameToolsController,
    GeProtonController,
    HeroicController,
    LaunchCheckController,
    LaunchOptionsController,
    MangoHudController,
    PerAppScopeBuddyController,
    PerGameMangoHudController,
    ProfilesController,
    ProtonDbController,
    ProtonLogController,
    ProtontricksController,
    SavesController,
    ScopeBuddyController,
    ScopeBuddyEnvvarsController,
    SoundController,
    SystemController,
    ThemeController,
)

QML_DIR = Path(__file__).parent / "qml"


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ProtonShift")
    app.setOrganizationName("ProtonShift")
    app.setApplicationVersion(__version__)
    # Ties the Wayland/X11 window to the .desktop file (icon, StartupWMClass),
    # which must equal the Flatpak app-id for Flathub.
    app.setDesktopFileName("io.github.i4ctime.protonshift")

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
    display = DisplayController()
    per_app_scb = PerAppScopeBuddyController()
    per_game_mango = PerGameMangoHudController()
    protontricks = ProtontricksController()
    game_tools = GameToolsController()
    profiles = ProfilesController()
    saves = SavesController()
    fixes = FixesController()
    scb_envvars = ScopeBuddyEnvvarsController()
    heroic = HeroicController()
    gamepad = GamepadController()
    theme = ThemeController()
    ge_proton = GeProtonController()
    sounds = SoundController()
    about = AboutController()
    launch_check = LaunchCheckController()
    proton_log = ProtonLogController()
    # Outcome chimes for work that finishes on a worker thread. (Saves that
    # finish at once chime from their Save button in QML.) Where the control
    # already made its own sound - a toggle, a profile row - only a failure
    # is worth a second one.
    launch._saveResult.connect(lambda _app, ok: sounds.chime(ok))
    launch._protonSaveResult.connect(lambda _app, ok, _tool: sounds.chime(ok))
    saves._actionResult.connect(lambda _app, _msg, ok: sounds.chime(ok))
    profiles._actionResult.connect(lambda _msg, ok: sounds.chime(ok))
    game_tools._actionResult.connect(lambda _app, _msg, kind: sounds.chime(kind == "ok"))
    protontricks._runResult.connect(lambda _app, ok, _out: sounds.chime(ok))
    heroic._versionResult.connect(lambda _app, ok, _name: sounds.chime(ok))
    heroic._toggleResult.connect(lambda _app, _key, _value, ok: ok or sounds.chime(False))
    system._powerResult.connect(lambda ok, _msg, _profile: ok or sounds.chime(False))
    display._applyResult.connect(lambda ok, _msg, _output: ok or sounds.chime(False))
    ge_proton._installDone.connect(lambda _name: sounds.chime(True))
    ge_proton._installFailed.connect(lambda _msg, cancelled: cancelled or sounds.chime(False))
    ge_proton._removeDone.connect(lambda _name, error: sounds.chime(not error))
    # installed/removed builds should show up in the per-game Proton picker
    ge_proton.toolsChanged.connect(launch.reloadProton)
    ctx = engine.rootContext()
    ctx.setContextProperty("gamescope", gamescope)
    ctx.setContextProperty("library", library)
    ctx.setContextProperty("env", env)
    ctx.setContextProperty("launch", launch)
    ctx.setContextProperty("protondb", ProtonDbController(parent=app))  # app-owned: outlives the engine
    ctx.setContextProperty("mangohud", mangohud)
    ctx.setContextProperty("scopebuddy", scopebuddy)
    ctx.setContextProperty("system", system)
    ctx.setContextProperty("display", display)
    ctx.setContextProperty("perAppScb", per_app_scb)
    ctx.setContextProperty("perGameMango", per_game_mango)
    ctx.setContextProperty("protontricks", protontricks)
    ctx.setContextProperty("gameTools", game_tools)
    ctx.setContextProperty("profiles", profiles)
    ctx.setContextProperty("saves", saves)
    ctx.setContextProperty("fixes", fixes)
    ctx.setContextProperty("scbEnvvars", scb_envvars)
    ctx.setContextProperty("heroic", heroic)
    ctx.setContextProperty("gamepad", gamepad)
    ctx.setContextProperty("themeCtl", theme)
    ctx.setContextProperty("geProton", ge_proton)
    ctx.setContextProperty("sounds", sounds)
    ctx.setContextProperty("about", about)
    ctx.setContextProperty("launchCheck", launch_check)
    ctx.setContextProperty("protonLog", proton_log)
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
