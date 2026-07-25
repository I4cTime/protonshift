# Contributing to ProtonShift

Thanks for helping improve ProtonShift! This guide covers the dev
environment, project conventions, and the release-adjacent files you must
keep in sync.

## Dev environment

- **Python** ≥ 3.11 (CI runs 3.11 and 3.12). No Node/JS toolchain in this
  repo — no `package.json`, no pnpm/npm, no bundler.
- Fastest path:

  ```bash
  ./run.sh
  ```

  Builds a `.venv` on first run, installs the app in editable mode
  (`PySide6` + `vdf`), and launches. Re-run any time — it re-syncs
  dependencies and is near-instant once the venv is current.

- Or manually:

  ```bash
  python3 -m venv .venv && . .venv/bin/activate
  pip install -e ".[dev]"
  python -m protonshift
  ```

- Useful commands:

  | Command | What it does |
  |---|---|
  | `ruff check protonshift` | Lint. Matches CI. |
  | `pytest` | Test suite (`tests/`). Qt-free by design; runs headless, no display needed. Matches CI. |
  | `pyside6-qmllint -I protonshift/qml protonshift/qml/**/*.qml` | QML lint. Matches CI. |

- CI (`.github/workflows/ci.yml`) runs all three on Python 3.11 and 3.12,
  headless (`QT_QPA_PLATFORM=offscreen`).

## Branches and commits

- Base your work on **`develop`**; `main` tracks releases.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `chore:`, with optional scope — e.g. `fix(qml): …`),
  matching the existing history and the Dependabot config.
- Before opening a PR, run `ruff check protonshift`, `pytest`, and the
  `pyside6-qmllint` command above — the PR template checklist mirrors CI.

## Project conventions

See [CLAUDE.md](CLAUDE.md) for the layout rules that keep the codebase
consistent — most importantly:

- `protonshift/core/` stays PySide6-free (keeps `tests/` Qt-free and fast).
- `protonshift/controllers/` bridges `core/` to QML; blocking work runs on a
  background thread via `controllers/_worker.py`'s `start_worker()`, never
  directly on the GUI thread.
- `protonshift/qml/App/` is the design system (`Theme.qml` + `Ps*`
  components) — read colors from `Theme`, don't hardcode them in a page.
- Two security-load-bearing regexes (`core/shader_cache.py`'s `_APP_ID_RE`,
  `core/scopebuddy.py`'s `_KEY_RE`) guard against path traversal and shell
  command injection respectively — see CLAUDE.md before touching either, and
  update `tests/test_core_safety.py` in the same change if you do.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full project layout, the
PySide6/QML threading pattern, and the release process.

## Keep these in sync when you change behavior

- **CHANGELOG:** add your change under `[Unreleased]` in `CHANGELOG.md`
  (Keep a Changelog format).
- **Flatpak manifests:** `flatpak/io.github.i4ctime.protonshift.yml` (local
  build, network + pip) and `flatpak/flathub/` (offline Flathub-compliant
  manifest) have different constraints and must not be conflated — see
  CLAUDE.md. A dependency or file-layout change usually needs both updated.
- **Theme parity:** a new palette in `Theme.qml` needs the matching id in
  `controllers/theme_controller.py`'s `_THEMES` with identical token keys —
  `tests/test_theme_parity.py` checks both.

## Security issues

Do **not** open a public issue for vulnerabilities — follow
[SECURITY.md](SECURITY.md).

## License

By contributing you agree your work is licensed under
[AGPL-3.0-or-later](LICENSE), the same license as the project.
