# Flathub submission

This directory holds the **offline** build used for Flathub, kept separate from
the fast local build in the parent `flatpak/` dir.

## Why it differs from the local build

| | Local (`../io.github.i4ctime.protonshift.yml`) | Flathub (here) |
|---|---|---|
| Network at build | yes (`--share=network`) | **no** (forbidden) |
| PySide6 | `pip install PySide6` | **`io.qt.PySide.BaseApp`** |
| Runtime | `org.freedesktop.Platform//24.08` | `org.kde.Platform//6.11` |
| krb5 | bundled module | provided by KDE runtime |
| vdf | pip | vendored wheel (`python3-vdf.yaml`) |

`flatpak-pip-generator` **refuses to vendor the PySide6 wheel** and points to
`io.qt.PySide.BaseApp` — that is the correct, Flathub-blessed way to ship a
PySide6 app. The BaseApp provides PySide6/shiboken6 built against Qt from
`org.kde.Platform`, so we don't duplicate ~150 MB of Qt. We only vendor the tiny
pure-Python `vdf`.

## Files

- `io.github.i4ctime.protonshift.yml` — the offline manifest (BaseApp + KDE runtime)
- `python3-vdf.yaml` — vendored `vdf` wheel (pinned URL + sha256), generated
- `gen-vendor.sh` — regenerates `python3-vdf.yaml` after a dependency bump

## Test the offline build locally

```bash
flatpak install -y flathub \
  org.kde.Sdk//6.11 org.kde.Platform//6.11 io.qt.PySide.BaseApp//6.11

flatpak run org.flatpak.Builder --user --install --force-clean \
  build-dir flatpak/flathub/io.github.i4ctime.protonshift.yml

flatpak run io.github.i4ctime.protonshift
```

The builder should succeed **without** `--share=network`; if it reaches out, a
dependency isn't vendored.

## Submission checklist

- [x] App ID is `io.github.i4ctime.protonshift` (maps to `github.com/I4cTime`)
- [x] `.desktop`, `.metainfo.xml`, `.svg` all renamed to the app ID
- [x] `metainfo.xml` has `<id>`, `<launchable>`, license, developer, OARS rating
- [x] Offline manifest builds on the PySide BaseApp (no network)
- [x] **Screenshots**: three 1440x900 captures in `flatpak/screenshots/`
      (library, MangoHud, Gamescope), referenced from `metainfo.xml` via
      raw.githubusercontent URLs.
- [x] **Runtime version**: bumped to `6.11` (2026-08-06) — matches the PySide6
      version the app is developed against; BaseApp publishes `branch/6.11`.
- [x] Validate metadata: `appstreamcli validate --pedantic
      flatpak/io.github.i4ctime.protonshift.metainfo.xml` passes (screenshot
      URLs resolve once pushed).
- [ ] Fork `flathub/flathub`, add the manifest, open a PR against `new-pr`.
- [x] The Flathub manifest's source is `type: git`, pinned to the packaging
      commit on `main` (update `commit:` on each release before the flathub
      update PR).

## aarch64

`gen-vendor.sh` resolves `vdf` as a pure-Python wheel (`py2.py3-none-any`), so it
is arch-independent. `io.qt.PySide.BaseApp` publishes aarch64, so no per-arch
work is needed here — Flathub will build both from this one manifest.
