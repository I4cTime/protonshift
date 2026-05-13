# Host prerequisites (one-time)

Quickemu exposes the repo’s **`build/`** to guests via `--public-dir` as **`smb://10.0.2.4/qemu`**. KVM should be usable by your user; **`smbd`** must run on the **host**.

## KVM check

```bash
egrep -c '(vmx|svm)' /proc/cpuinfo   # > 0 ⇒ CPU virtualization
ls -l /dev/kvm                       # must exist; readable by kvm group / your user
```

```bash
sudo usermod -aG kvm "$USER"   # then re-login
```

## Quickemu + QEMU (+ OVMF where applicable)

Quickemu may be missing from older distro repos — use community packages or upstream.

### Pop!_OS, Ubuntu 22.04 / 24.04, Mint, elementary, Zorin

```bash
sudo apt-add-repository ppa:flexiondotorg/quickemu
sudo apt update
sudo apt install quickemu qemu-system-x86 qemu-system-modules-spice ovmf
```

### Ubuntu 25.04+ (Quickemu in Universe)

```bash
sudo apt install quickemu qemu-system-x86 qemu-system-modules-spice ovmf
```

### Debian 13+ (trixie)

```bash
sudo apt install quickemu qemu-system-x86 ovmf
```

### Debian 12 (bookworm) — upstream `.deb`

```bash
# Replace x.y.z with the latest tag from releases.
curl -fsSLO https://github.com/quickemu-project/quickemu/releases/latest/download/quickemu_x.y.z-1_all.deb
sudo apt install ./quickemu_x.y.z-1_all.deb
```

### Fedora 41+, Bazzite, Nobara

```bash
sudo dnf install quickemu qemu-system-x86 edk2-ovmf
```

### Arch / CachyOS / Manjaro / EndeavourOS

```bash
yay -S quickemu
```

### Source fallback

```bash
git clone --filter=blob:none https://github.com/quickemu-project/quickemu
cd quickemu/docs && sudo make install
```

Runtime deps: [Quickemu installation wiki](https://github.com/quickemu-project/quickemu/wiki/01-Installation).

## Samba (`smbd`) for `--public-dir`

Without **`smbd`**, VMs still boot; guests won’t mount **`//10.0.2.4/qemu`** (use SCP instead — see [guest-build-share-appimage.md](guest-build-share-appimage.md)).

```bash
sudo apt install --no-install-recommends samba   # Pop!_OS / Debian / Ubuntu
sudo dnf install samba                           # Fedora / Bazzite
sudo pacman -S samba                             # Arch / CachyOS
```
