# ProtonShift — Qt Quick edition

Native rewrite of ProtonShift: a Linux gaming setup tool. The UI is **Qt Quick
(QML)** driven from **Python via PySide6**; the domain logic is the original
ProtonShift Python core, lifted unchanged. No Electron, no bundled Chromium, no
Next.js, no FastAPI, no localhost HTTP server, no bearer token.

```
protonshift/
  core/          # pure-Python domain logic (lifted from the old backend)
    gamescope.py     tool_check.py
  controllers/   # QObject bridges: Property / Signal / Slot  ->  QML
    gamescope_controller.py
  qml/
    main.qml               # root window
    GamescopeBuilderPage.qml
    App/                   # the "App" QML module = design system
      Theme.qml   (singleton: the violet tokens)
      PsButton.qml PsCard.qml PsSwitchRow.qml PsNumberField.qml
      PsSlider.qml PsSectionHeader.qml GlowBackground.qml
flatpak/
  io.github.protonshift.yml
```

## Current status — vertical slice

This is the **first slice**: the gamescope command builder, wired end-to-end to
the real Python core, plus the design system (Theme singleton + branded
components) and the packaging skeleton. It proves the stack — the shine survives
in QML, the Python binding is ergonomic, and it packages for Flatpak — before
the rest of the app is ported.

It also fixes the FSR bug from the old app (issue #24): the toggle now actually
emits `-F fsr`, not just the sharpness value.

## Run it (dev)

```bash
./run.sh
```

First run builds a `.venv`, installs PySide6, and launches. Or manually:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
python -m protonshift
```

## Architecture in one paragraph

A QML `Property`/`Signal`/`Slot` object *is* the entire IPC story. QML binds
directly to `GamescopeController`; edits flow into a `GamescopeOptions`
dataclass; the `command` property rebuilds via `core.gamescope`. Because there is
no network boundary, the whole class of transport bugs from the old FastAPI
layer (token exfiltration, fail-open auth, CORS, response-shape mismatches)
cannot exist here.

## Packaging

Primary target is **Flatpak** (installs from Discover on Steam Deck Desktop
Mode, survives immutable-distro updates). See [flatpak/](flatpak/) — the manifest
is a working skeleton; the one manual step is generating the PySide6 pip sources
(offline builds can't hit PyPI). Notes are in `flatpak/README.md`.
