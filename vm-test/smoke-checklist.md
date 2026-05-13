# Protonshift smoke-test checklist

Run inside the VM after `provision/<distro>.sh` completes and the
AppImage is launched.

## 1. App boots cleanly

- [ ] AppImage starts without an error dialog.
- [ ] No `python3: command not found` in stderr (we ship our own).
- [ ] Window decorates correctly and chrome buttons (min/max/close) work.

## 2. Backend is reachable

- [ ] Open the renderer DevTools (`PROTONSHIFT_DEVTOOLS=1` in dev only —
      in packaged builds, observe via `journalctl --user -f`).
- [ ] In a guest terminal:

  ```bash
  pgrep -af 'game_setup_hub.api' | head
  ```

  → should show one process running from
  `/tmp/.mount_*/resources/python/runtime/bin/python3`, *not* `/usr/bin/python3`.

## 3. Game source discovery

- [ ] Library list populates (Steam if installed; Heroic / Lutris too if
      flatpak'd).
- [ ] Source badges render (Steam / Heroic / Lutris).
- [ ] Search filters across sources.

## 4. Tool detection

For each tool that exists in this guest, the matching panel should not be
greyed out:

- [ ] MangoHud
- [ ] Gamescope
- [ ] GameMode (`gamemoderun`)
- [ ] protontricks (if installed)

For tools that are *not* installed, the panel should display the install
hint and stay disabled — never crash.

## 5. Editors

- [ ] Open the MangoHud config editor (no per-game game required); change
      a value → write succeeds.
- [ ] Open the Environment Variables page and toggle a preset → file
      under `~/.config/environment.d/` updates.

## 6. Graceful exit

- [ ] Close the window.
- [ ] `pgrep -af game_setup_hub.api` → empty (Python child was reaped).

## 7. Distro-specific

- **Ubuntu/Debian deb**: `sudo dpkg -i /mnt/protonshift-build/protonshift_*.deb`
  installs cleanly with no missing-deps prompts.
- **Fedora/openSUSE rpm**: `sudo rpm -i …` likewise.
- **Bazzite (immutable)**: only the AppImage path applies; deb/rpm should
  not be attempted.
