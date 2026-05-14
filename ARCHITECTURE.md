# Architecture & contributor guide

<p align="center">
  <i>How ProtonShift is built, how the pieces talk, and how to add to it.</i>
</p>

<p align="center">
  <a href="#overview">Overview</a> &middot;
  <a href="#system-diagram">System diagram</a> &middot;
  <a href="#renderer">Renderer</a> &middot;
  <a href="#backend">Backend</a> &middot;
  <a href="#http-api">HTTP API</a> &middot;
  <a href="#project-layout">Project layout</a> &middot;
  <a href="#building-from-source">Building</a> &middot;
  <a href="#vm-testing-harness">VM testing</a> &middot;
  <a href="#pre-commit-checks">Pre-commit</a> &middot;
  <a href="#contributing">Contributing</a> &middot;
  <a href="#release-process">Release</a>
</p>

---

## Overview

ProtonShift is a three-layer desktop app:

1. **An Electron renderer** that ships as a Next.js 16 *static export* — React 19, Tailwind v4, HeroUI v3 (base + Pro). It is the only thing the user sees.
2. **An Electron main process** that spawns the Python backend, owns the window chrome, and exposes a tiny IPC surface (filesystem helpers, the running app version, etc.) over a preload contextBridge.
3. **A Python FastAPI backend** running on `127.0.0.1` that does all the real OS work: scanning Steam/Heroic/Lutris, reading and writing config files, talking to `nvidia-smi`/`xrandr`/`wlr-randr`, managing Wine prefixes, etc.

The renderer never talks to the OS directly. Everything funnels through the backend so the same logic is reusable from CLI tools, tests, or other front-ends.

## System diagram

```
┌──────────────────────────────────────────────────────┐
│  Electron renderer  ·  Next.js 16 (static export)    │
│  React 19  ·  Tailwind v4  ·  HeroUI v3 (+ Pro)      │
│                                                      │
│   /  ─────────────  game library + detail            │
│   /environment  ──  ~/.config/environment.d          │
│   /system  ──────  GPU / displays / power            │
│   /mangohud  ────  global + per-game .conf editor    │
│   /scopebuddy  ──  scb.conf + scb.conf.d/<app>.conf  │
│   /controllers  ─  detection + live gamepad tester   │
└─────────────────────┬────────────────────────────────┘
                      │  preload IPC bridge
                      │  (window.electron.*)
┌─────────────────────▼────────────────────────────────┐
│  Electron main process  ·  electron/main.ts          │
│  Spawns Python, proxies HTTP, exposes app version    │
└─────────────────────┬────────────────────────────────┘
                      │  HTTP on 127.0.0.1
┌─────────────────────▼────────────────────────────────┐
│  Python FastAPI backend  ·  src/game_setup_hub/      │
│                                                      │
│  Sources       steam · heroic · lutris               │
│  Configs       gamescope · scopebuddy · mangohud     │
│  Runtime       gpu · display · controllers · prefix  │
│  Data          env_vars · profiles_storage · saves   │
│  Tooling       protontricks · fixes · tool_check     │
│                                                      │
│  api/routes/   games  heroic  mangohud  profiles     │
│                saves  scopebuddy  system  utility    │
└──────────────────────────────────────────────────────┘
```

The renderer ships as a **static Next.js export** packaged inside Electron, so there is no server runtime at the framework layer — no server actions, no dynamic route handlers, no edge runtime. All dynamic behaviour goes through the IPC bridge to the bundled Python API.

## Renderer

The Electron renderer is a standalone Next.js app under [`electron/renderer/`](electron/renderer/). It is built once with `next build` (static export) and the resulting `out/` directory is what Electron loads at runtime.

**Stack:**

- **Next.js 16** App Router, static export only
- **React 19** with hooks-first conventions
- **Tailwind CSS v4** (no v3 fallback)
- **HeroUI v3** — base components from `@heroui/react`, plus Pro components (`Sheet`, `Command`, charts, `Sidebar`, `Kanban`, etc.) from `@heroui-pro/react`
- **TanStack Query** for server state, **Jotai** for cross-component client state
- **Lucide** icons throughout

**Conventions enforced by [`.cursor/rules/heroui-v3.mdc`](.cursor/rules/heroui-v3.mdc):**

- Compound components everywhere (`Card.Header` not `<CardHeader />`)
- `onPress`, not `onClick`, for interactive elements
- Prefer HeroUI semantic tokens (`border-border`, `bg-surface`, `text-foreground`) over hand-rolled colour utilities
- Reserve renderer-local tokens (`neon-*`, `glow-*`, `blob-*`) for accent glow & ambient effects only
- Toasts go through `appShowToast` in [`electron/renderer/src/lib/app-toast.ts`](electron/renderer/src/lib/app-toast.ts)
- No parallel UI libraries — if HeroUI doesn't have it, write a thin local primitive under `electron/renderer/src/components/`

**Renderer routes** map 1:1 to the nav items:

| Route | Component | What it does |
|---|---|---|
| `/` | `app/page.tsx` | Unified game library + per-game detail panes |
| `/environment` | `app/environment/page.tsx` | `~/.config/environment.d/` editor + presets |
| `/system` | `app/system/page.tsx` | GPU info, displays, power profiles, quick actions |
| `/mangohud` | `app/mangohud/page.tsx` | Global `MangoHud.conf` + per-game `wine-*.conf` |
| `/scopebuddy` | `app/scopebuddy/page.tsx` | `scb.conf` + `scb.conf.d/<appid>.conf` editor |
| `/controllers` | `app/controllers/page.tsx` | Detection + SDL mapping + live gamepad tester |

The command palette (<kbd>Ctrl</kbd>+<kbd>K</kbd>) lives in [`electron/renderer/src/components/app-command.tsx`](electron/renderer/src/components/app-command.tsx) and dispatches through events in [`electron/renderer/src/lib/command-palette-events.ts`](electron/renderer/src/lib/command-palette-events.ts).

## Backend

The Python backend is a normal FastAPI app under [`src/game_setup_hub/`](src/game_setup_hub/). It can run standalone for development or be spawned automatically by the Electron main process for the packaged app.

**Module layout:**

- **Library sources** — `steam.py`, `heroic.py`, `heroic_config.py`, `lutris.py` discover games and expose a uniform shape
- **Config surfaces** — `gamescope.py`, `scopebuddy.py`, `mangohud.py`, `env_vars.py`, `vdf_config.py`, `presets.py`
- **OS runtime** — `gpu.py`, `display.py`, `controllers.py`, `prefix.py`, `paths.py`, `fsutil.py`
- **Data & state** — `profiles_storage.py`, `saves.py`, `shader_cache.py`, `fixes.py`
- **Tooling** — `protontricks.py`, `tool_check.py`
- **Compat shim** — `_vendor_compat.py` smooths over differences between bundled and host Python

The FastAPI app itself lives in [`src/game_setup_hub/api/`](src/game_setup_hub/api/):

- `_app.py` — app factory
- `_state.py` — shared, lazily-initialised dependencies (split out from `_app.py` for testability)
- `_models.py` — Pydantic models
- `_helpers.py` — common request/response helpers
- `routes/` — one router file per surface

The version string in [`src/game_setup_hub/__init__.py`](src/game_setup_hub/__init__.py) is the single source of truth for the Python package and AppStream metadata. The Electron app version (in [`electron/package.json`](electron/package.json)) is surfaced to the renderer at runtime via the `getVersion` IPC handler so the nav-bar badge never drifts from the actual packaged version.

## HTTP API

Both the UI and the backend share the same FastAPI server. The Electron app spawns it automatically, but you can also run it standalone:

```bash
pip install -e .
protonshift-api --port 8000
# or, equivalent:
python -m game_setup_hub.api --port 8000
```

Endpoint groups (see [`src/game_setup_hub/api/routes/`](src/game_setup_hub/api/routes/) for the full surface):

| Group | Highlights |
|---|---|
| `games` | unified library, per-game detail, launch helpers |
| `heroic` | Heroic-specific toggles & compat tool selection |
| `mangohud` | global + per-game config CRUD |
| `scopebuddy` | global `scb.conf`, per-app overrides, env detection |
| `profiles` | save/apply/delete configuration profiles |
| `saves` | discover, backup, restore |
| `system` | GPU, displays, power profiles, shader cache totals |
| `utility` | tool detection, controllers, fixes DB, misc |
| `health` | liveness probe |

Open `http://127.0.0.1:8000/docs` for the live OpenAPI explorer when the API is running standalone.

## Project layout

```
protonshift/
├── electron/                    # Electron app
│   ├── main.ts                  #   main process + IPC handlers
│   ├── preload.ts               #   contextBridge surface
│   ├── package.json             #   electron-builder config + app version (source of truth)
│   └── renderer/                #   Next.js renderer (static export)
│       └── src/
│           ├── app/             #     routes: /, /environment, /system,
│           │                    #             /mangohud, /scopebuddy, /controllers
│           ├── components/      #     UI components (HeroUI v3 base + Pro)
│           ├── lib/             #     api client, app-toast, events
│           └── types/           #     window.electron typings
├── src/game_setup_hub/          # Python FastAPI backend
│   ├── api/
│   │   ├── _app.py              #   FastAPI app factory
│   │   ├── _state.py            #   shared lazy deps
│   │   ├── _models.py           #   Pydantic models
│   │   └── routes/              #   one router per surface
│   ├── steam.py heroic.py       #   library sources
│   ├── lutris.py                #
│   ├── gamescope.py             #   gamescope command builder + detection
│   ├── scopebuddy.py            #   scb.conf + scb.conf.d/* I/O
│   ├── mangohud.py              #   global + per-game configs
│   ├── prefix.py saves.py       #   Wine prefix inspection, save backup
│   ├── fixes.py profiles_storage.py
│   ├── gpu.py display.py controllers.py
│   ├── env_vars.py presets.py
│   └── ...
├── assets/                      # icons, AppStream metainfo, social card
├── docs/                        # public docs
│   └── internal/                #   reviews, release snapshots
├── scripts/                     # dev/automation
│   └── ci/                      #   linux-matrix.sh (cross-distro python check)
├── tests/                       # pytest suite (mirrors src/game_setup_hub)
├── vm-test/                     # Quickemu-based VM test harness
│   ├── run-vm.sh                #   one-shot launcher per distro
│   ├── provision/               #   per-distro guest provisioners
│   ├── quickemu/                #   .extras.conf per distro
│   ├── docs/                    #   per-distro runbooks (also mounted in-guest)
│   └── smoke-checklist.md       #   manual smoke test
├── .github/workflows/
│   ├── ci.yml                   #   ruff + pytest + linux-matrix + renderer build
│   ├── build-release.yml        #   AppImage / deb / rpm / flatpak on release
│   └── codeql.yml               #   security analysis
└── pyproject.toml               # Python package metadata
```

## Building from source

### Python backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check
protonshift-api --port 8000              # run standalone
```

### Renderer (dev)

```bash
cd electron/renderer
pnpm install
pnpm dev                                 # next dev with hot reload
```

`@heroui-pro/react` is a private package — set `HEROUI_AUTH_TOKEN` in your shell before `pnpm install`, otherwise the postinstall step stops at a skeleton and TypeScript can't resolve the imports. Local devs store it in [q-ring](https://github.com/I4cTime/q-ring); CI pulls from the `HEROUI_AUTH_TOKEN` GitHub Actions secret (wired up in [`ci.yml`](.github/workflows/ci.yml) and [`build-release.yml`](.github/workflows/build-release.yml)).

```bash
# Local equivalent:
export HEROUI_AUTH_TOKEN=$(qring get HEROUI_AUTH_TOKEN)
pnpm install
```

### Electron app

```bash
cd electron
pnpm install
pnpm dev                                 # spawns Python + opens an Electron window
pnpm build                               # produces AppImage / deb / rpm / flatpak via electron-builder
```

`pnpm build` calls `next build` for the renderer first (static export to `out/`), then `electron-builder` bundles `out/`, the main process, the preload bundle, and a portable CPython 3.12 with the API stack pre-installed. Outputs land in `electron/dist/` and (for CI) are copied to `build/` at repo root.

## VM testing harness

[`vm-test/`](vm-test/) is a Quickemu-based harness for end-to-end-testing ProtonShift packages on real desktop distros without rebooting the host. It launches throwaway VMs, exposes the host's `build/` directory over SMB to the guest (`/mnt/protonshift-build/`), and stages both per-distro provisioning scripts *and* the runbook docs themselves into that share so you can `less /mnt/protonshift-build/_docs/<distro>.md` from inside the guest and paste the commands.

Currently supported guests:

- `ubuntu-24.04`
- `fedora-41`
- `bazzite` (atomic, gnome edition)
- `cachyos`
- `opensuse-tumbleweed`
- `debian-12`

```bash
vm-test/run-vm.sh ubuntu-24.04
# inside the guest, after the SMB share auto-mounts:
ls   /mnt/protonshift-build                    # AppImage / .deb / .rpm + _provision/ + _docs/
less /mnt/protonshift-build/_docs/ubuntu-24.04.md
sudo /mnt/protonshift-build/_provision/ubuntu.sh
```

Per-distro runbooks live under [`vm-test/docs/`](vm-test/docs/) and the smoke checklist at [`vm-test/smoke-checklist.md`](vm-test/smoke-checklist.md). Host prerequisites (Quickemu, KVM, samba) are documented in [`vm-test/docs/host-prerequisites.md`](vm-test/docs/host-prerequisites.md).

## Pre-commit checks

Local CI mirror — all of these are also enforced by [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

```bash
# Python
ruff check src tests
pytest -q
scripts/ci/linux-matrix.sh                 # cross-distro Python compat check

# Renderer
cd electron/renderer
pnpm lint
pnpm build                                 # next build (static export); fails on type errors

# Electron typecheck (main + preload)
cd ../
pnpm typecheck
```

If you only touched one layer, you can scope down — but at minimum run `ruff` + `pytest` for backend changes and `pnpm build` (in `electron/renderer/`) for renderer changes. The renderer build is the strictest gate; it surfaces any type drift between the API client and the FastAPI Pydantic models.

## Contributing

PRs are welcome. The basic flow:

1. **Backend first.** Add the module under `src/game_setup_hub/`, write tests in `tests/`, expose a FastAPI router under `src/game_setup_hub/api/routes/`, register it in [`src/game_setup_hub/api/routes/__init__.py`](src/game_setup_hub/api/routes/__init__.py). Keep route handlers thin — push the work into a regular module so it's testable without a TestClient.
2. **Then the renderer.** Add the API client method in [`electron/renderer/src/lib/api.ts`](electron/renderer/src/lib/api.ts), wire TanStack Query hooks, build the UI with HeroUI v3 (see [Renderer](#renderer) conventions). No parallel UI libraries.
3. **Smoke it in a VM** with [`vm-test/run-vm.sh`](vm-test/run-vm.sh) before opening a PR if you've touched anything that talks to the OS — paths, sockets, system tools, packaging.
4. **Branching.** Feature branches → PR into `develop`. Releases ship from `develop` → `main` via a PR. Don't push directly to `main`.
5. **Commits.** Imperative-mood subject lines. Body should explain *why*, not what — the diff already shows the what.
6. **Secrets.** Never commit `.env`, tokens, or credentials. Use [q-ring](https://github.com/I4cTime/q-ring) locally and GitHub Actions secrets for CI. See [`.cursor/rules/`](.cursor/rules/) for the project's secret-hygiene rule.

For a deeper look at backend-side conventions, see [`docs/internal/python-review.md`](docs/internal/python-review.md). For renderer-side conventions, see [`.cursor/rules/heroui-v3.mdc`](.cursor/rules/heroui-v3.mdc).

## Release process

1. Bump versions to `X.Y.Z` in:
   - [`electron/package.json`](electron/package.json) — single source of truth for the app
   - [`electron/renderer/package.json`](electron/renderer/package.json)
   - [`src/game_setup_hub/__init__.py`](src/game_setup_hub/__init__.py)
   - [`assets/io.github.protonshift.metainfo.xml`](assets/io.github.protonshift.metainfo.xml) — add a new `<release>` entry
   - [`.github/ISSUE_TEMPLATE/bug_report.yml`](.github/ISSUE_TEMPLATE/bug_report.yml) — bump the placeholder
2. Run the [pre-commit checks](#pre-commit-checks) locally.
3. Commit on `develop`, push, open a PR from `develop` to `main`.
4. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
5. Create a GitHub Release for the tag — this fires [`build-release.yml`](.github/workflows/build-release.yml), which builds the AppImage / deb / rpm / flatpak and attaches them to the release.
6. Merge the PR into `main`.

To peek at download counts and per-format breakdowns for prior releases:

```bash
gh api repos/I4cTime/protonshift/releases --paginate \
  --jq '.[] | "\(.tag_name)\t\(.published_at[:10])\t\(.assets | map(.download_count) | add)"' \
  | column -t -s $'\t'
```

---

If something here is wrong or unclear, [open an issue](https://github.com/I4cTime/protonshift/issues/new/choose) — this doc is the contract between the codebase and the next person editing it.
