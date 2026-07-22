# VM test environment

Exercise a **packaged ProtonShift** **AppImage** on **real desktop stacks** inside **KVM/QEMU** guests driven by **[Quickemu](https://github.com/quickemu-project/quickemu)**.

The renderer is **Electron**: you want a composed session (**X11/Wayland**), workable GPU virtio setup, Steam/Wine tooling, and MangoHud/Gamescope — **`scripts/ci/linux-matrix.sh`** Docker runs complement this but **do not replace** it.

---

## Documentation

👉 **[`docs/index.md`](docs/index.md)** — **per-distro** runbooks (**Ubuntu**, **Fedora**, **Debian**, **CachyOS**, **openSUSE**, **Bazzite**).

| Topic | Doc |
| --- | --- |
| Distro index | [`docs/index.md`](docs/index.md) |
| Host: Quickemu, KVM, **`smbd`** (SMB share host) | [`docs/host-prerequisites.md`](docs/host-prerequisites.md) |
| Guest: mount **`build/`**, AppImage **`--no-sandbox`**, SCP | [`docs/guest-build-share-appimage.md`](docs/guest-build-share-appimage.md) |
| **`quickemu/`** paths & **`*.conf`** quirks | [`docs/layout-and-quickemu.md`](docs/layout-and-quickemu.md) |
| Manual QA | [`smoke-checklist.md`](smoke-checklist.md) |

**Boot:** `./run-vm.sh list` • `./run-vm.sh <guest>` • `./run-vm.sh <guest> --status` (see **`run-vm.sh`** header).

**Artifacts staged into the SMB share** (host **`$(repo)/build/`** → guest **`/mnt/protonshift-build/`**, passed via Quickemu **`--public-dir`**):

| Host path | Guest path | What's there |
| --- | --- | --- |
| `build/ProtonShift-*.AppImage` | `/mnt/protonshift-build/` | Packaged build from **`pnpm run dist`** |
| `vm-test/provision/*.sh` | `/mnt/protonshift-build/_provision/` | Per-distro provision scripts (copied by **`run-vm.sh`**) |
| `vm-test/docs/*.md`, `smoke-checklist.md`, `README.md` | `/mnt/protonshift-build/_docs/` | These runbooks — `less` / paste commands directly from the guest |

After mounting the share inside the VM, the per-distro doc is one command away:

```bash
less /mnt/protonshift-build/_docs/README.md          # overview
less /mnt/protonshift-build/_docs/ubuntu-24.04.md    # or whichever guest you booted
```
