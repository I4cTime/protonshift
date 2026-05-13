# Fedora 41 (`fedora-41`)

> **In-guest:** `less /mnt/protonshift-build/_docs/fedora-41.md` once the SMB share is mounted (step 1).

**`.rpm` / RPMFusion** Steam stack; **`dnf`** provisioning.

**Host:** [Host prerequisites](host-prerequisites.md) → **`cd electron && pnpm run dist:appimage`**.

**Boot**

```bash
cd vm-test && ./run-vm.sh fedora-41
```

**Guest (installer done, signed in)**

1. **`sudo dnf install -y cifs-utils`**, **[mount `build/`](guest-build-share-appimage.md)**, verify **`_provision/`**.
2.

```bash
sudo bash /mnt/protonshift-build/_provision/fedora.sh
chmod +x /mnt/protonshift-build/ProtonShift-*.AppImage
```

**[AppImage / SCP](guest-build-share-appimage.md)** • **[smoke checklist](../smoke-checklist.md)**
