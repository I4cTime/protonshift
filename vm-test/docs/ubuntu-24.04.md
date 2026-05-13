# Ubuntu 24.04 (`ubuntu-24.04`)

> **In-guest:** `less /mnt/protonshift-build/_docs/ubuntu-24.04.md` once the SMB share is mounted (step 1).

Stock **`.deb`/Steam-heavy** baseline; scripted provisioning matches Noble quirks (gamescope PPA when needed).

**Host:** [Host prerequisites](host-prerequisites.md) → build AppImage (`cd electron && pnpm run dist:appimage`).

**Boot**

```bash
cd vm-test && ./run-vm.sh ubuntu-24.04
```

**Guest (finish the distro installer once, reboot, sign in)**

1. Install **`cifs-utils`**, **[mount the SMB share](guest-build-share-appimage.md)**, confirm **`_provision/`** appears.
2. Run provisioning (also wires **`fstab`** when mount succeeds):

```bash
sudo bash /mnt/protonshift-build/_provision/ubuntu.sh
chmod +x /mnt/protonshift-build/ProtonShift-*.AppImage
```

3. Launch ProtonShift (often **`--no-sandbox`** in VMs): **[guest-build-share-appimage.md](guest-build-share-appimage.md)**.
4. **[`../smoke-checklist.md`](../smoke-checklist.md)**.
