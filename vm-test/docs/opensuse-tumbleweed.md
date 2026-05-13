# openSUSE Tumbleweed (`opensuse-tumbleweed`)

> **In-guest:** `less /mnt/protonshift-build/_docs/opensuse-tumbleweed.md` once the SMB share is mounted (step 1).

Rolling **`zypper`** / **`.rpm`**.

**Host:** [Host prerequisites](host-prerequisites.md); build **`ProtonShift-*.AppImage`** (**`cd electron && pnpm run dist:appimage`**).

```bash
cd vm-test && ./run-vm.sh opensuse-tumbleweed
```

**Guest**

1. **`sudo zypper install cifs-utils`**, **[mount `build/`](guest-build-share-appimage.md)**.
2.

```bash
sudo bash /mnt/protonshift-build/_provision/opensuse.sh
chmod +x /mnt/protonshift-build/ProtonShift-*.AppImage
```

**[AppImage quirks](guest-build-share-appimage.md)** • **[smoke checklist](../smoke-checklist.md)**
