# Flatpak packaging

Two build variants share one manifest shape.

## Local build (works today)

`io.github.i4ctime.protonshift.yml` allows network during the build and
pip-installs PySide6 + vdf straight into `/app`. This is the fast path to a
running package — including on a Steam Deck in Desktop Mode.

```bash
# one-time tooling
flatpak install -y flathub org.flatpak.Builder org.freedesktop.Sdk//24.08

# build + install into the user flatpak installation
flatpak run org.flatpak.Builder --user --install --force-clean \
  build-dir io.github.i4ctime.protonshift.yml

flatpak run io.github.i4ctime.protonshift
```

## Flathub build (offline)

Lives in [`flathub/`](flathub/). It is a *different* manifest: Flathub forbids
build-time network, and — importantly — PySide6 must **not** be pip-vendored.
`flatpak-pip-generator` refuses PySide6 and points to `io.qt.PySide.BaseApp`,
which is the correct way to ship it (PySide6 built against `org.kde.Platform`,
no 150 MB Qt duplication). We vendor only the tiny pure-Python `vdf`.

See [`flathub/README.md`](flathub/README.md) for the build/test commands and the
submission checklist. Regenerate vendored deps with `flathub/gen-vendor.sh`.

## Size note (KDE runtime)

Both variants use `org.freedesktop.Platform` + a bundled Qt (~150 MB via the
PySide6 wheel). Moving to `org.kde.Platform//6.x` (Qt from the runtime, PySide6
built against it) removes that duplication — do it when Deck image size matters,
not before.

## Assets in this dir

- `io.github.i4ctime.protonshift.yml` — the local manifest
- `io.github.i4ctime.protonshift.desktop` — launcher entry
- `io.github.i4ctime.protonshift.metainfo.xml` — AppStream (name, summary, release notes)
- `io.github.i4ctime.protonshift.svg` — app icon (violet chevrons)
- `flathub/` — the offline Flathub manifest + vendored deps + submission checklist

## App ID

`io.github.i4ctime.protonshift` — maps to `github.com/I4cTime` as Flathub
requires. The app sets `QGuiApplication.setDesktopFileName()` to the same ID so
the Wayland/X11 window picks up the icon and `StartupWMClass`. Both manifests,
all three asset files, and the `.metainfo.xml` `<id>`/`<launchable>` use it.
