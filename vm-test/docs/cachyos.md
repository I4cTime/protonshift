# CachyOS (`cachyos`)

> **In-guest:** `less /mnt/protonshift-build/_docs/cachyos.md` once the SMB share is mounted (step 1).

Arch-style **`pacman`** guest; **`arch.sh`** provisioning (Steam/repos; **protontricks** skipped if absent).

**Host:** [Host prerequisites](host-prerequisites.md); build **`ProtonShift-*.AppImage`** (**`cd electron && pnpm run dist:appimage`**).

```bash
cd vm-test && ./run-vm.sh cachyos
```

**Guest**

1. **`sudo pacman -Sy --needed cifs-utils`**, **[mount `build/`](guest-build-share-appimage.md)**.
2.

```bash
sudo bash /mnt/protonshift-build/_provision/arch.sh
chmod +x /mnt/protonshift-build/ProtonShift-*.AppImage
```

**[AppImage quirks](guest-build-share-appimage.md)** • **[smoke checklist](../smoke-checklist.md)**
