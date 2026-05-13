# Layout and Quickemu quirks

## Repository paths

| Path | Role |
| --- | --- |
| `quickemu/<name>.extras.conf` | `quickget` args (**`QG_*`**) + Quickemu overrides; committed fragments only. |
| `quickemu/<vm>/…` (local) | **`quickget` output** (**`.conf`** with **`iso=`** / disks). Recreated when broken or stale. |

**[`run-vm.sh`](../run-vm.sh)** merges **`.extras.conf`** into the generated **`.conf`**, and passes **`$(repo)/build`** via **`--public-dir`**.

Guests mount **`//10.0.2.4/qemu`** at **`/mnt/protonshift-build`** when **`smbd`** runs on the host; see **[guest-build-share-appimage.md](./guest-build-share-appimage.md)**.

## Avoid committing hand-written **`*.conf`**

`quickget` writes **`iso=`** lines only when the machine **`.conf`** does **not** already exist (e.g. **`quickemu/ubuntu-24.04/ubuntu-24.04.conf`**). A tracked **`.conf`** that lacks **`iso=`** prevents regeneration ⇒ Quickemu errors with **`You haven't specified a .iso`**. **`run-vm.sh`** removes broken files and reruns **`quickget`**.

Heavy outputs (ISOs, **`disk.qcow2`**, merged **`*.conf`**) are **`gitignore`d** ([`quickemu/.gitignore`](../quickemu/.gitignore)).
