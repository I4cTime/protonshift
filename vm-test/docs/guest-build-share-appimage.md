# Guest: mount `build/` and run the AppImage

Assume the host exported **`$(repo)/build`** via `./run-vm.sh …` (**`--public-dir`**). Provision scripts expect **`build/`** to contain **`ProtonShift-*.AppImage`** and **`_provision/`** (staging from **`run-vm.sh`**).

## Mount the SMB share (Linux guest)

Needs **`cifs-utils`** (install via your distro if not already pulled in by provisioning).

```bash
sudo mkdir -p /mnt/protonshift-build
sudo mount -t cifs //10.0.2.4/qemu /mnt/protonshift-build \
  -o "guest,vers=3.0,ro,uid=$(id -u),gid=$(id -g),forceuid,forcegid"
ls /mnt/protonshift-build/
```

You should see **`ProtonShift-*.AppImage`** and **`_provision/`**. **`mount`(8)** error **`(2)`** ⇒ install **`smbd`** on the host, restart the VM with **`run-vm.sh`**.

**Running `_provision/*.sh`** — Scripts are staged by the host under **`build/_provision/`**; mount the share **first**, then run the script for your distro (e.g. **`sudo bash /mnt/protonshift-build/_provision/ubuntu.sh`**). Filenames are listed per guest in **[docs/index.md](index.md)**.

## Electron AppImage on Linux guests (`/tmp` / sandbox)

Unpack usually uses **`/tmp/.mount_*`**. If **`/tmp` is `nosuid`**, Chromium’s setuid helper fails (**`chrome-sandbox`**, mode **4755**). Easiest VM smoke:

```bash
/mnt/protonshift-build/ProtonShift-*.AppImage --no-sandbox
```

Alternatives: **`TMPDIR`** under **`$HOME`**, or extract with **`--appimage-extract`**, **`chown/chmod`** **`chrome-sandbox`**, **`./squashfs-root/AppRun`**. Don’t plain **`sudo ./ProtonShift-*.AppImage`** — Electron rejects root without **`--no-sandbox`**.

## Python backend **`exited with code 1`**

Packaged trees are often read-only; current Electron builds set **`PYTHONDONTWRITEBYTECODE=1`** for packaged runs. **Rebuild** the AppImage from a current checkout. Check terminal **`[python] …`** for the traceback.

## SCP fallback (host → guest)

On the host (VM running):

```bash
cd vm-test
PORT=$(awk -F= '/ssh_port/{print $2}' quickemu/<guest-dir>/<basename>.ports)
scp -P "$PORT" ../build/ProtonShift-*.AppImage YOUR_USER@localhost:~/
```

Guest: **`chmod +x`** and run from **`~/`**. Copy **`provision/*.sh`** with adjusted paths if you skip SMB.
