# Flatpak packaging notes

The manifest (`io.github.protonshift.yml`) is a **working skeleton**, not yet a
one-command build, because Flatpak builds are offline and PySide6 must be
fetched from PyPI ahead of time.

## To make it build

1. Install the helper:
   ```bash
   pip install flatpak-pip-generator   # or grab the script from flatpak/flatpak-builder-tools
   ```
2. Generate pinned PySide6 sources:
   ```bash
   flatpak-pip-generator --runtime=org.freedesktop.Sdk//24.08 PySide6
   # produces pip-sources.yml (or python3-PySide6.yml)
   ```
3. Reference it: uncomment the `- pip-sources.yml` line in the manifest.
4. Build & install:
   ```bash
   flatpak-builder --user --install --force-clean build-dir io.github.protonshift.yml
   flatpak run io.github.protonshift
   ```

## Size vs. KDE runtime (later optimization)

This skeleton uses `org.freedesktop.Platform` + the PySide6 wheel, which bundles
its own Qt (~150 MB). That's the *reliable* path. Once the app is stable, moving
to `org.kde.Platform//6.x` (Qt provided by the runtime, PySide6 built against it)
drops that duplication — at the cost of pinning PySide6 to the runtime's exact Qt
version. Do that when size on the Deck matters, not before.

## Still to add for Flathub

- `io.github.protonshift.desktop` (launcher entry)
- `io.github.protonshift.metainfo.xml` (AppStream: screenshots, description)
- An icon (`io.github.protonshift.svg`)
