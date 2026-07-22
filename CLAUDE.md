# CLAUDE.md

ProtonShift — native Qt Quick (QML) desktop app for managing Linux game
configuration (Steam/Heroic/Lutris, gamescope, MangoHud, ScopeBuddy, gamepads).
See README.md for what it does, ARCHITECTURE.md for how it's built. This file
is conventions and constraints only.

## Stack

- **Python + PySide6 + QML.** There is no Node/JS toolchain in this repo —
  no `package.json`, no pnpm/npm, no bundler. Don't add one or suggest one.
- Packaging is `pyproject.toml` (setuptools). Runtime deps: `PySide6`, `vdf`.
  Dev deps (`pip install -e ".[dev]"`): `ruff`, `pytest`.

## Commands

- `./run.sh` — dev entrypoint. Builds `.venv` on first run, re-syncs deps on
  every run (fast once current), launches the app. Use this, not a bare
  `python -m protonshift`, unless you already have an active venv.
- `ruff check protonshift` — lint. Matches CI.
- `pytest` — test suite (`tests/`). Qt-free by design; runs without a
  display. Matches CI.
- `pyside6-qmllint -I protonshift/qml protonshift/qml/**/*.qml` — QML lint.
  Matches CI (`.github/workflows/ci.yml`).

## Project layout

- `protonshift/core/` — pure-Python domain logic. No PySide6 import here,
  ever — this is what keeps `tests/` Qt-free and fast. Anything that
  touches disk or a subprocess belongs here, not in a controller.
- `protonshift/controllers/` — QObject bridges (`Property`/`Signal`/`Slot`)
  exposing `core/` to QML. Blocking work must run via
  `controllers/_worker.py`'s `start_worker()` on a background thread and
  report back through a queued signal — never call `core/` disk/subprocess
  functions directly from a `Slot` on the GUI thread.
- `protonshift/qml/App/` — the design system (`Theme.qml` singleton + `Ps*`
  components). Read colors from `Theme`, don't hardcode them in a page.
- `flatpak/` — two manifests, not one:
  - `flatpak/io.github.i4ctime.protonshift.yml` — local build, network +
    pip. Use this for a quick local Flatpak build or when testing packaging
    changes day to day.
  - `flatpak/flathub/` — offline Flathub-compliant manifest. No build-time
    network; PySide6 comes from `io.qt.PySide.BaseApp`, not pip. Only touch
    this when working on the actual Flathub submission — it has different
    constraints from the local manifest and the two must not be conflated.

## Security — don't relax without understanding why

- `core/shader_cache.py`'s `app_id` validation (`_APP_ID_RE`, decimal digits
  only, plus `validate_within` containment) closes a path-traversal bug: app
  ids are read from `appmanifest_*.acf` filenames on disk, which aren't
  trusted input, and an id like `..` would make cache deletion `rmtree` the
  wrong directory.
- `core/scopebuddy.py`'s `_KEY_RE` (`^[A-Za-z_][A-Za-z0-9_]*$`) is
  load-bearing: `scb.conf` is bash-sourced at every game launch, so an
  unvalidated key would be persistent command injection into that shell.
  `write_scb_conf` raises before writing a byte if any key fails this check
  — keep it that way.
- If you touch either regex, add/update the corresponding case in
  `tests/test_core_safety.py` in the same change.

## Conventions

- Controllers expose GUI-safe types only (`QVariantList`, `QVariantMap`,
  `str`/`bool`/`int`) — don't leak `core/` dataclasses into QML.
- New controllers follow the pattern in `controllers/games_controller.py`:
  public `Slot` sets a loading flag and calls `start_worker`; a private
  result signal updates state and clears loading on the GUI thread; a
  private error signal clears loading on failure so an exception can't wedge
  the UI in a loading state.
- Adding a palette to `Theme.qml`? Add the matching id to
  `controllers/theme_controller.py`'s `_THEMES` and keep the token keys
  identical to the existing palettes — `tests/test_theme_parity.py` checks
  both.
