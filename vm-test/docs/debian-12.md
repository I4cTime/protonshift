# Debian 12 (`debian-12`)

> **In-guest:** `less /mnt/protonshift-build/_docs/debian-12.md` once the SMB share is mounted (step 1).

Stable **bookworm**, older glibc baseline. There is **no** **`debian.sh`** yet — install **`cifs-utils`**, enable **`contrib`** / **`non-free`** as needed for Steam packages, and mirror what **`ubuntu.sh`** / **`fedora.sh`** pull in (**Steam**, **Flatpak**, **MangoHud**, **Gamemode**, **Gamescope**, **protontricks** when available).

**Host:** [Host prerequisites](host-prerequisites.md); build **`ProtonShift-*.AppImage`** (**`cd electron && pnpm run dist:appimage`**). On bookworm Quickemu usually comes from the **upstream `.deb`** (see prerequisites doc).

```bash
cd vm-test && ./run-vm.sh debian-12
```

**Guest**

1. **`sudo apt install -y cifs-utils`**, **[mount `build/`](guest-build-share-appimage.md)** when using SMB.
2. There is **no** **`debian.sh`**. Install tooling via **`apt`** (enable **`contrib`** / **`non-free`** as needed for **`steam`** / **`steam-installer`**), e.g.

```bash
sudo apt update
sudo apt install -y flatpak dbus-user-session
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
# If your sources allow: steam mangohud gamescope gamemode protontricks (mirror ubuntu.sh/fedora.sh)
```

3. **`chmod +x /mnt/protonshift-build/ProtonShift-*.AppImage`** and launch per **[guest-build-share-appimage.md](guest-build-share-appimage.md)**.
4. **[`../smoke-checklist.md`](../smoke-checklist.md)**.
