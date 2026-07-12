# Flatpak packaging

Two build variants share one manifest shape.

## Local build (works today)

`io.github.protonshift.yml` allows network during the build and pip-installs
PySide6 + vdf straight into `/app`. This is the fast path to a running package —
including on a Steam Deck in Desktop Mode.

```bash
# one-time tooling
flatpak install -y flathub org.flatpak.Builder org.freedesktop.Sdk//24.08

# build + install into the user flatpak installation
flatpak run org.flatpak.Builder --user --install --force-clean \
  build-dir io.github.protonshift.yml

flatpak run io.github.protonshift
```

## Flathub build (offline — follow-up)

Flathub forbids network access during the build, so PySide6 must be vendored:

1. `pip install requirements-parser`
2. Fetch the generator from
   [flatpak/flatpak-builder-tools](https://github.com/flatpak/flatpak-builder-tools/tree/master/pip):
   ```bash
   flatpak-pip-generator --runtime=org.freedesktop.Sdk//24.08 PySide6 vdf
   ```
   → produces `python3-modules.yml` with pinned wheel URLs + hashes.
3. In the manifest: drop the `--share=network` build-arg and the `pip3 install
   PySide6 vdf` step; add `- python3-modules.yml` before the `protonshift` module
   and keep only `pip3 install --prefix=${FLATPAK_DEST} .`.

## Size note (KDE runtime)

Both variants use `org.freedesktop.Platform` + a bundled Qt (~150 MB via the
PySide6 wheel). Moving to `org.kde.Platform//6.x` (Qt from the runtime, PySide6
built against it) removes that duplication — do it when Deck image size matters,
not before.

## Assets in this dir

- `io.github.protonshift.yml` — the manifest
- `io.github.protonshift.desktop` — launcher entry
- `io.github.protonshift.metainfo.xml` — AppStream (name, summary, release notes)
- `io.github.protonshift.svg` — app icon (violet chevrons)

## App ID

Currently `io.github.protonshift`. For a Flathub submission the ID must map to a
domain/repo you control — likely `io.github.i4ctime.protonshift` (repo is
`I4cTime/protonshift`). Renaming touches all four filenames above plus the
manifest `app-id`; do it as one step at submission time.
