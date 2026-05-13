# Bazzite (`bazzite`)

> **In-guest:** if you can mount the SMB share, `less /mnt/protonshift-build/_docs/bazzite.md`. Otherwise SCP this file (or the whole `_docs/` directory) over and `less ./bazzite.md`.

Immutable **rpm-ostree** — Steam, MangoHud, Gamescope, and GameMode are present by default. **`provision/bazzite.sh`** avoids installing **`cifs-utils`** via **`rpm-ostree`** (would need a reboot). Prefer **SSH/SCP** for the AppImage; the script enables **Heroic/Lutris** via **Flatpak** (**`--user`**).

**Host:** [Host prerequisites](host-prerequisites.md); build **`ProtonShift-*.AppImage`** (**`cd electron && pnpm run dist:appimage`**).

```bash
cd vm-test && ./run-vm.sh bazzite
```

**Guest**

1. Prefer **SSH/SCP** to copy **`ProtonShift-*.AppImage`** (+ **`provision/bazzite.sh`** if needed) — see **[SCP fallback](guest-build-share-appimage.md)**. **Alternatively**, if **`cifs-utils`** is available without **`rpm-ostree`**, **[mount `build/`](guest-build-share-appimage.md)** and skip manual copy.
2. Run **Flatpak wiring** **without sudo** where your login session owns **`--user`** Flatpak:

```bash
bash /mnt/protonshift-build/_provision/bazzite.sh   # SMB path
# or: bash ./bazzite.sh   # copied into $HOME via SCP
```

3. Typical launch after **`chmod +x`**:

```bash
chmod +x ~/protonshift-build/ProtonShift-*.AppImage
~/protonshift-build/ProtonShift-*.AppImage --no-sandbox
```

**[Electron / `--no-sandbox`](guest-build-share-appimage.md)** • **[smoke checklist](../smoke-checklist.md)**
