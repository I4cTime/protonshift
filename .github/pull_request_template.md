<!--
  Thanks for contributing to ProtonShift. Keep PRs focused; one logical
  change per PR. CI (ruff + pytest + qmllint, matrix on Python 3.11/3.12)
  and CodeQL are required before merge on develop/main.
-->

## Summary

<!-- What does this change, and why? -->

## Type

- [ ] Feature
- [ ] Fix
- [ ] Security
- [ ] Docs
- [ ] Chore / CI / deps

## Checklist

- [ ] `ruff check protonshift` passes
- [ ] `pytest` passes
- [ ] `pyside6-qmllint -I protonshift/qml protonshift/qml/**/*.qml` passes (QML changes)
- [ ] `CHANGELOG.md` updated under `[Unreleased]` (for user-facing changes)
- [ ] Docs (README / ARCHITECTURE.md / CLAUDE.md) updated if behavior or layout changed
- [ ] Flatpak manifests updated if dependencies or packaged files changed (`flatpak/io.github.i4ctime.protonshift.yml` and, if relevant, `flatpak/flathub/`)
- [ ] If touching `core/shader_cache.py`'s `_APP_ID_RE` or `core/scopebuddy.py`'s `_KEY_RE`: corresponding case added/updated in `tests/test_core_safety.py`
- [ ] If adding a `Theme.qml` palette: matching entry added to `controllers/theme_controller.py`'s `_THEMES` with identical token keys (`tests/test_theme_parity.py`)

## Breaking changes

<!-- None — or describe the impact and migration steps. -->
