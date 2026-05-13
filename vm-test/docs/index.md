# VM test guides

Hands-on flows for exercising a packaged ProtonShift build ([`run-vm.sh`](../run-vm.sh) + Quickemu).

> **Reading these docs *inside* the guest VM.** Booting via `./run-vm.sh <guest>`
> stages this directory into the SMB share. After mounting (see
> [`guest-build-share-appimage.md`](./guest-build-share-appimage.md)):
>
> ```bash
> ls   /mnt/protonshift-build/_docs/
> less /mnt/protonshift-build/_docs/<this-distro>.md
> ```
>
> Copy/paste commands from there instead of alt-tabbing back to the host.

| Config | Distro focus | Doc |
| --- | --- | --- |
| `ubuntu-24.04` | Ubuntu 24.04 LTS | [`ubuntu-24.04.md`](./ubuntu-24.04.md) |
| `fedora-41` | Fedora 41 Workstation | [`fedora-41.md`](./fedora-41.md) |
| `debian-12` | Debian 12 (bookworm) | [`debian-12.md`](./debian-12.md) |
| `cachyos` | CachyOS / Arch-style | [`cachyos.md`](./cachyos.md) |
| `opensuse-tumbleweed` | openSUSE Tumbleweed | [`opensuse-tumbleweed.md`](./opensuse-tumbleweed.md) |
| `bazzite` | Bazzite (immutable) | [`bazzite.md`](./bazzite.md) |

**Shared**

- [**Host prerequisites**](host-prerequisites.md) — Quickemu, QEMU, KVM, Samba (`smbd`)
- [**Guest: share mount + AppImage**](guest-build-share-appimage.md) — CIFS mount, Electron `--no-sandbox`, SCP fallback
- [**Layout & Quickemu quirks**](layout-and-quickemu.md) — **`*.extras.conf`**, avoiding broken **`*.conf`** in git

After install: **[`smoke-checklist.md`](../smoke-checklist.md)**

Add guests by cloning [`quickemu/*.extras.conf`](../quickemu/) and running **`./run-vm.sh`** with a configured short name (see table). Advanced Quickemu: [upstream wiki](https://github.com/quickemu-project/quickemu/wiki/05-Advanced-quickemu-configuration).
