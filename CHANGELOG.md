# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Docs
- Dropped the stale-release caveat from the README now that `v1.0.0` is
  published.

## [1.0.0] — 2026-07-22

First stable release: a ground-up rewrite from the Electron prototype to a
native **Qt Quick (QML) + PySide6** desktop app. No Electron, no bundled
browser, no backend server.

### Added
- **Unified game library** — Steam, Heroic (Epic + GOG), and Lutris games in
  one searchable list with per-source counts and one-click launch,
  install-folder, and Wine-prefix access.
- **Launch options** editing with quick presets (GameMode, NVIDIA dGPU
  offload, MangoHud, Proton debug logging, ScopeBuddy wrapper).
- **Compatibility tool selection** — Proton/Wine build picker across Steam's
  `compatibilitytools.d` and Heroic's `tools/wine` and `tools/proton`.
- **Heroic per-game toggles** — Esync/Fsync, DXVK/VKD3D auto-install,
  MangoHud, GameMode, NVIDIA Prime offload.
- **Gamescope command builder** with resolution/FPS/FSR/HDR presets, a live
  command preview, and an alternate ScopeBuddy-override output mode.
- **ScopeBuddy integration** — a dedicated `scb.conf` editor (global + per-app
  overrides) that preserves comments and existing bash structure on write.
- **MangoHud config editor** for global and per-game overlay configs.
- **Environment variable management** persisted to
  `~/.config/environment.d/70-protonshift.conf`.
- **Wine/Proton prefix, shader cache, and save-backup tools** — per-game
  prefix size and DXVK/VKD3D-Proton detection with one-click delete,
  shader-cache size/clear, and timestamped ZIP save backup/restore.
- **Configuration profiles** — save and reapply a game's launch options,
  compatibility tool, environment variables, and power profile.
- **Game-specific fixes database**, matched per App ID or applied
  universally, extensible via `~/.config/protonshift/fixes/`.
- **Protontricks integration** (GUI launch + quick-run common verbs; native
  and Flatpak installs supported).
- **System info & display management** — GPU detection (NVIDIA/AMD/Intel)
  with live temps, power-profile switching, and per-monitor resolution/
  refresh-rate control across X11 and Wayland compositors.
- **Controllers tab** — gamepad detection, `SDL_GAMECONTROLLERCONFIG`
  mapping generation, live button/axis tester, and rumble test.
- **Theming** — six built-in palettes (including a system light/dark
  follower), backed by a token-based design system (`Theme.qml`).
- **Branded startup splash screen.**
- **Flatpak packaging** — a local-build manifest and a Flathub-compliant
  offline manifest in prep for Flathub submission; tagged releases attach a
  prebuilt `.flatpak` bundle.

### Changed
- CI rewritten for the Python/PySide6/Flatpak stack: `ruff check`, `pytest`,
  and `pyside6-qmllint` across Python 3.11 and 3.12, headless
  (`QT_QPA_PLATFORM=offscreen`).
- Tag-triggered release automation (`build-release.yml`) — pushing a `v*` tag
  builds the Flatpak bundle and attaches it to the GitHub release, guarded by
  a version check against `pyproject.toml`.
- Electron packaging trimmed to AppImage-only ahead of the Qt migration, then
  retired once the Qt rewrite landed as the new `main`.

### Fixed
- Host tool calls (`nvidia-smi`, `gamescope`, `protontricks`, `xrandr`, etc.)
  now route through `flatpak-spawn --host` from inside the sandbox.
- Rumble/controller worker-exception handling rewritten to share a common
  guard instead of leaving the UI in an inconsistent state on failure.
- Design-system token and accessibility fixes across QML pages (focus
  states, contrast failures in the light palettes, page-level token
  migration).

### Security
- **Closed a shader-cache path-traversal bug** — `core/shader_cache.py` now
  validates `app_id` (decimal digits only) and containment before any
  `rmtree`, since app IDs are read from on-disk filenames and aren't
  trusted input.
- **Closed a ScopeBuddy config-injection bug** — `core/scopebuddy.py` now
  validates env-var keys (`^[A-Za-z_][A-Za-z0-9_]*$`) before writing
  `scb.conf`, which is bash-sourced at every game launch; an unvalidated key
  was a persistent command-injection vector.
