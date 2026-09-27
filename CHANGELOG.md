# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] — 2026-09-27

### Added
- **Environment variables that reach every desktop** (#47). The Environment
  page now has a "Where variables go" selector: `~/.config/environment.d`
  (systemd user sessions — GNOME, KDE, sway/Hyprland under uwsm),
  `~/.profile` (login shells and display-manager session wrappers) or
  `~/.xsessionrc` (Debian/Ubuntu/Mint X11 sessions). ProtonShift recommends
  the one your session actually reads and offers a one-click switch when the
  selected target isn't it. Shell files get a clearly marked managed block
  (`export KEY='value'`, POSIX-quoted); everything outside it is preserved
  byte-for-byte. A "Copy as Steam launch options" button turns the same rows
  into a `KEY=value … %command%` prefix for the stubborn cases.
- **Proton page: GE-Proton manager.** Lists the custom builds in Steam's
  `compatibilitytools.d` (size, version, which games pin them), fetches the
  latest GloriousEggroll releases, and installs them with sha512 verification
  and a cancellable progress bar — or removes them, warning when a game still
  uses the build. Installed builds appear in the per-game Proton picker right
  away. System-wide builds from distro packages (Arch's
  `proton-ge-custom-bin`, anything in `/usr/share/steam/compatibilitytools.d`)
  are listed too, tagged "system" and left to the package manager to remove.
  Tools are identified by the internal name in `compatibilitytool.vdf` — the
  key Steam actually uses — so "in use by" counts and the picker match what
  Steam does.
- **ProtonDB rating per game.** The game detail pane shows the community tier
  (Platinum → Borked), report count, confidence and trending tier, with a link
  to the ProtonDB page. Results are cached for a day. Lookups send only the
  Steam App ID to protondb.com and can be switched off in the System page's
  Privacy card (or from the pane itself).
- **Profile export / import.** The profiles dialog can export all profiles or
  a single one to a versioned JSON bundle and import a bundle back, skipping
  same-named profiles unless you flip the overwrite switch. Imports are
  validated entry by entry (types, env var keys, no newline injection) and
  report imported / skipped / invalid counts.

- **Settings page.** Appearance moved out of the header into a Settings tab
  and was rebuilt around *styles* instead of fixed palettes: Proton Neon,
  Phosphor Console, Soft Glass and Deepslate, each with default colors, plus
  a system/dark/light mode and an accent color override (eight presets or any
  hex). Existing theme choices migrate automatically. The page also hosts
  the ProtonDB privacy toggle and an About card.

- **Displays: resolution and refresh-rate dropdowns.** Each output gets a
  Resolution select, a Refresh rate select scoped to that resolution, the
  current mode as a caption, and an Apply button that only enables when the
  choice differs from what's active — no more scanning a wall of mode chips.
  Hyprland sessions get a native backend (`hyprctl monitors` / `hyprctl
  keyword monitor`), so every mode the panel offers is listed even without
  wlr-randr installed — the XWayland fallback only ever showed one.
- Theme: `Theme.inkOn(fill)` picks dark or light text for any colored
  surface from its luminance; primary buttons and the ProtonDB tier badges
  use it, so custom accents stay readable.

### Changed
- Visual pass across every page: destructive actions (delete override /
  profile / snippet, preset apply that replaces a whole config) now confirm
  first; status lines color by a real success flag from each controller
  instead of sniffing message text; the System page's power profile list
  scrolls instead of clipping on short windows.
- Flatpak: the sandbox now has `--share=network` (GE-Proton downloads and
  ProtonDB lookups) and may create `~/.profile` / `~/.xsessionrc` for the
  managed env block. Nothing else talks to the network.
- Docs: release flow and contributing notes describe the main-only branching
  model (`develop` is gone since 1.1.1).

## [1.1.1] — 2026-09-15

### Fixed
- **Environment Variables: warn when environment.d can't reach your session**
  (#47). `~/.config/environment.d` is only read by systemd's user manager, so
  on desktops a display manager starts directly (Cinnamon, XFCE, MATE, a bare
  `startx` session) or on systems without systemd the file is written but
  games never see it — MangoHud/Gamemode silently don't activate. The page
  now probes `graphical-session.target` and shows a warning with the
  alternatives (`~/.xsessionrc` / `~/.profile` exports, or per-game Steam
  launch options) instead of letting "Saved" imply it works. Quoting in the
  written file was never the problem.

### Changed
- Lint: ruff 0.16 (wider default rule set) — dropped ~110 stale `noqa`
  markers for rules that were never enabled, and tidied the handful of real
  findings (explicit `check=False` on `subprocess.run`, no call in argument
  defaults, `contextlib.suppress` for best-effort discovery).
- CI: `github/codeql-action` 4.37.9 (init + analyze bumped together — split
  Dependabot bumps fail with a config-version mismatch), `action-gh-release`
  3.0.3.

## [1.1.0] — 2026-08-04

### Changed

- **New brand**: the app icon (Flatpak icon set + scalable SVG) and in-app
  logo (header + splash) are now the "broken ring" sigil mark — a
  summoning circle with a proton core in the Arcane violet gradient —
  replacing the old chevron tile and matching the refreshed
  [protonshift.i4c.studio](https://protonshift.i4c.studio).

## [1.0.1] — 2026-07-25

### Fixed
- **Environment Variables: the ✕ button now removes the row** (#52). QML's
  `model.removeRow(i)` was resolving to QAbstractItemModel's built-in C++
  convenience instead of the same-named Python slot, landing in the default
  `removeRows()` stub that does nothing. The model now overrides the
  `removeRows()` virtual — the supported hook — so removal works and marks
  the editor dirty.

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
