# Architecture

ProtonShift is a Qt Quick (QML) desktop app whose UI is backed by Python. There
is no HTTP layer, no bundled browser, and no IPC protocol to version - the
"API" between Python and QML is a set of Qt `QObject`s exposed as context
properties, using ordinary `Property`/`Signal`/`Slot` bindings.

```
protonshift/
  core/            pure-Python domain logic - no Qt imports, no QML awareness
  controllers/     QObject bridges: expose core/ to QML via Property/Signal/Slot
  qml/
    App/           design-system module: Theme.qml + Ps* components
    *.qml          the 8 top-level pages + main.qml (window/nav) + Splash.qml
  app.py           entry point: builds the QML engine, wires controllers in
flatpak/           packaging manifests (see "Packaging" below)
tests/             pytest suite (core-only, no Qt runtime required)
```

## `core/` - domain logic

Everything under `protonshift/core/` is plain Python: file I/O, subprocess
calls, and parsing, with no PySide6 import anywhere in the package. This is
deliberate - it's what makes `tests/` fast and Qt-free, and it's what a
controller threads off the GUI thread (see below).

Roughly one module per integration or feature:

- **Discovery**: `steam.py`, `steam_shortcuts.py` (Non-Steam shortcuts from
  the binary `shortcuts.vdf`), `heroic.py` (Epic, GOG, Amazon, sideloaded),
  `heroic_config.py`, `lutris.py` - find installed games and their config
  files across native and Flatpak installs of each launcher.
- **Config editors**: `gamescope.py` (command building), `mangohud.py`,
  `scopebuddy.py`, `env_vars.py`, `vdf_config.py` (Steam launch options),
  `launch_merge.py` (places a snippet around `%command%` instead of
  appending it, plus the single edits a Diagnose fix makes: set or unset a
  variable, add a game argument, remove a wrapper word).
- **System**: `display.py` (xrandr/wlr-randr/kscreen-doctor), `gpu.py`
  (nvidia-smi/sysfs + power profiles), `input_devices.py` (gamepad detection,
  SDL mapping, force-feedback rumble via raw `ioctl`/`struct` packing),
  `host.py` (host command execution, see "Flatpak sandboxing" below).
- **Game maintenance**: `shader_cache.py`, `saves.py` (backup/restore),
  `prefix.py`, `protontricks.py`, `fixes.py` (the user's own fixes),
  `launch_presets.py`, `profiles_storage.py`, `compat_tool.py`,
  `proton_log.py` (tail of `steam-<appid>.log`).
- **Diagnose**: `diagnose.py` (one ranked list of findings; `collect` reads,
  the rest is pure), fed by `launch_check.py`, `proton_log.py`, `fix_pack.py`
  (the bundled `core/data/fix_pack.json` plus the user's fixes) and
  `system_checks.py`; `fix_apply.py` plans, applies and undoes a fix, with
  `snapshots.py` keeping what Undo needs.
- **The app itself**: `appearance.py` (styles, mode, accent), `sounds.py`
  (sound sets and stored settings), `updates.py` (manual update check).
- **Shared low-level helpers**: `fsutil.py` (atomic writes, dir sizing),
  `paths.py` (path containment / filename sanitization - see
  [CLAUDE.md](CLAUDE.md) for the security note on this), `tool_check.py`
  (`which`-style tool detection), `host.py`.

## `controllers/` - the QML bridge

Each controller is a `QObject` subclass exposed to QML as a context property
in `app.py` (e.g. `GamesController` → `library`, `GamescopeController` →
`gamescope`). A controller's job is narrow: translate QML-friendly
`Property`/`Signal`/`Slot` calls into `core/` function calls, and translate the
results back into QML-friendly types (`QVariantList`, `QVariantMap`, plain
`str`/`bool`/`int`).

### Threading pattern

Anything in `core/` that touches disk or spawns a subprocess is blocking, and
blocking the GUI thread freezes the window. Controllers push that work onto a
worker thread and report back through a **queued** Qt signal, using the shared
helper in `protonshift/controllers/_worker.py`:

```python
start_worker(self._work, on_error=self._workError.emit)
```

`start_worker` runs `target` on a daemon `threading.Thread`. Any exception
raised inside `target` - expected or not - is caught and routed to
`on_error` as a short string, rather than silently killing the thread. Before
this existed, an unexpected exception in a worker body could kill the thread
before its result signal fired, permanently wedging the controller's
`loading`/`busy` flag with no way to recover short of restarting the app.

The typical controller shape (see `controllers/games_controller.py` for a full
example):

1. A public `Slot()` (e.g. `refresh()`) sets `_loading = True`, emits
   `loadingChanged`, and calls `start_worker(self._work, ...)`.
2. `_work()` runs on the worker thread, calls into `core/`, and emits a
   private `Signal` (e.g. `_resultReady`) carrying the result.
3. Because the signal was connected with `QObject.connect` from the GUI
   thread and Qt's default connection type resolves to `QueuedConnection`
   across threads, the connected slot (`_on_result`) runs back on the GUI
   thread - safe to mutate state QML is bound to and to emit
   `*Changed` signals from.
4. A second private signal (`_workError`) is connected to a handler that
   clears `loading` and surfaces the error, so an unhandled exception can't
   leave the UI stuck in a loading state.

`_worker.py` itself is deliberately PySide-free (no Qt import), so its
exception-routing behavior is covered by a plain pytest test with no Qt
runtime involved.

### Diagnose flow

`DiagnoseController` follows the same pattern, with the reading and the
writing kept apart:

1. **Collect on a worker.** `run` starts `diagnose.collect`, which reads
   Steam's config, the Proton log tail, the system checks (host commands go
   through `host_run`), the bundled fix pack and the user's fixes, and passes
   a `Facts` to the pure `diagnose()`, which ranks the findings. Each run
   carries a token; a result from an older run or another game is dropped.
2. **Plan, pure.** "Fix this" calls `fix_apply.plan(actions, state)` on the
   GUI thread. It reads nothing and returns the before and after `GameState`
   (launch options and compatibility tool), which the dialog shows.
3. **Snapshot, then write.** Apply plans again on a worker and calls
   `apply_change`, which re-reads Steam's files and refuses if they no longer
   match the plan's `before`, records a snapshot
   (`~/.config/protonshift/snapshots/<appid>.json`, last 20 per game) and
   writes nothing if that fails, then writes `localconfig.vdf` and
   `config.vdf`, putting the first back if the second write fails.
4. **Undo.** `undo_latest` writes the latest snapshot's `before` back and
   drops it. If the settings are neither that snapshot's `before` nor its
   `after`, someone changed them since, and it refuses unless forced.
   Snapshots are on disk, so Undo survives a restart.

After a write, `settingsWritten` makes `app.py` reload the launch options
editor and the diagnosis runs again. Non-Steam shortcuts get findings but no
apply: there is no writer for the binary `shortcuts.vdf`.

The fix pack (`core/data/fix_pack.json`) is data, not code. Its actions are
a closed set (set or unset one variable, add one game argument, remove one
wrapper word, use Steam's default Proton, or an instruction for the user),
so no rule can put free text into launch options, which Steam hands to a
shell. The format, the loader's limits and how to add a rule are in
[docs/fix-pack.md](docs/fix-pack.md); `tests/test_fix_pack.py` enforces them
for the bundled pack.

## `qml/` - pages and design system

`qml/App/` is a local QML module (see `qmldir`) providing:

- `Theme.qml` - a singleton holding every design token (colors, spacing,
  fonts) as properties. The look is a visual **style** (`neon`, `console`,
  `soft`, `slate`: neutrals and shape) times a resolved dark/light **mode**
  times an **accent** color, all three bound in from `ThemeController`.
  Every accent-family token is derived from the accent in `Theme.qml`.
  `tests/test_theme_parity.py` checks that the style ids match
  `core/appearance.py` and that each style's dark and light palettes define
  the same token keys.
- `Ps*.qml` components (`PsButton`, `PsCard`, `PsDialog`, `PsSlider`,
  `PsSwitchRow`, `PsSelect`, `PsSectionHeader`, `PsNumberField`, `EnvField`,
  `PsChip`, `PsIconButton`, `PsRowButton`, `GlowBackground`) - the shared component vocabulary every page is built
  from, all reading colors from `Theme` rather than hardcoding them.

`qml/main.qml` is the application window: it hosts the `Binding`s that drive
`Theme` from `themeCtl`, an ambient `GlowBackground`, and the navigation. The
nine pages are grouped by what they act on - Games (`GamesPage`), Tools
(`ProtonPage`, `GamescopeBuilderPage`), All games (`EnvironmentPage`,
`MangoHudPage`, `ScopeBuddyPage`), This PC (`DisplayPage`, `SystemPage`,
`ControllersPage`) - and `SettingsPage` sits in the header. The shared Ps*
controls play interface sounds through the `sounds` controller; a controller
named like a `Button` property (`display`) must be reached through a page
property inside button handlers, or the button's own property shadows it.
`Splash.qml` is a startup splash shown while the engine loads.

## Flatpak sandboxing

`core/host.py` provides `host_run()`, which prefixes `flatpak-spawn --host`
when running inside a Flatpak sandbox (detected via `/.flatpak-info` or
`FLATPAK_ID`) and is a transparent pass-through otherwise. Every `core/`
module that shells out to a host tool the sandbox doesn't provide -
`nvidia-smi`, `powerprofilesctl`, `gamescope`, `protontricks`, `xrandr`,
etc. - goes through it, so the same code path works identically native or
sandboxed.

## Packaging (`flatpak/`)

Two manifests share one app ID (`io.github.i4ctime.protonshift`):

- **`flatpak/io.github.i4ctime.protonshift.yml`** - local build. Allows
  network at build time and `pip install`s PySide6 and `vdf` directly. Fast
  path to a running package; not Flathub-eligible.
- **`flatpak/flathub/`** - offline Flathub manifest. No build-time network;
  PySide6 comes from `io.qt.PySide.BaseApp` (Flathub's blessed way to ship
  PySide6 without duplicating Qt) rather than being pip-vendored, and only
  the pure-Python `vdf` dependency is vendored (`flatpak/flathub/gen-vendor.sh`
  regenerates it).

See [flatpak/README.md](flatpak/README.md) and
[flatpak/flathub/README.md](flatpak/flathub/README.md) for build commands and
the Flathub submission checklist.

## `tests/`

Pytest suite, all Qt-free by design so it runs without a display or a Qt
runtime:

- `test_core_safety.py` - path-traversal, command-injection, tolerant-decoding,
  and fail-closed-write regressions across `shader_cache`, `scopebuddy`,
  `heroic_config`, `saves`, `vdf_config`, and the fix pack's action limits.
- `test_fix_pack.py` and `test_fix_pack_rules.py` - the pack loader against
  [docs/fix-pack.md](docs/fix-pack.md), and a real sample line for every log
  rule plus lines from healthy runs that no rule may match.
- `test_input_devices_structs.py` - pins the 64-bit kernel force-feedback ABI
  (`struct ff_effect` layout, `input_event` size) that `input_devices.py`
  packs by hand.
- `test_theme_parity.py` - cross-checks `Theme.qml`'s palettes against
  `theme_controller.py`'s palette ids, as plain text/regex (no Qt import).

CI (`.github/workflows/ci.yml`) runs `ruff check`, `pyside6-qmllint` over
`protonshift/qml`, and `pytest`, on Python 3.11 and 3.12, with
`QT_QPA_PLATFORM=offscreen` so nothing needs a real display.

## Release flow

1. Work on a feature branch; CI runs lint + qmllint + tests on every push
   and on PRs into `main` (the only long-lived branch).
2. Open a PR into `main`; merge once checks are green.
3. Tag the merge commit `vX.Y.Z` and publish a GitHub Release from that tag.
4. Publishing the release triggers `.github/workflows/build-release.yml`,
   which builds the Flatpak bundle (via the local, network-enabled manifest -
   the same command documented in [flatpak/README.md](flatpak/README.md)) and
   uploads `io.github.i4ctime.protonshift-<tag>.flatpak` as a release asset.

There is no AppImage, `.deb`, or `.rpm` build anymore - Flatpak is the only
distribution format.
