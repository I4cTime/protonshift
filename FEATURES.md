# ProtonShift — Feature Tracker

Statuses: `done` | `in-progress` | `planned` | `idea`

---

## 1. Core Game Management

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Steam game discovery | done | `steam.py` | Games page | libraryfolders.vdf + appmanifest ACF |
| Heroic game discovery (Epic + GOG) | done | `heroic.py` | Games page | Legendary JSON + GOG install info |
| Lutris game discovery | done | `lutris.py` | Games page | pga.db + YAML prefix |
| Steam launch options edit | done | `vdf_config.py` | Games page | Read/write localconfig.vdf |
| Heroic launch options edit | done | `heroic_config.py` | Games page | Read/write GamesConfig JSON otherOptions |
| Proton/compat tool selection | done | `vdf_config.py`, `steam.py` | Games page | Built-in + compatibilitytools.d |
| Heroic Wine/Proton selection | done | `heroic_config.py` | Games page | Scan tools/wine + tools/proton dirs |
| Heroic settings toggles | done | `heroic_config.py` | Games page | Esync, Fsync, DXVK, VKD3D, MangoHud, GameMode, NVIDIA Prime |
| Launch option presets | done | `presets.py` | Games page | Gamemode, NVIDIA dGPU, MangoHud, Proton Log. Works for Steam + Heroic. |
| Protontricks integration | done | `protontricks.py` | Games page | Native + Flatpak, GUI + quick verbs |
| Configuration profiles | done | `profiles_storage.py` | Games page | Save/load launch opts + compat + env + power. Available for all game sources. |
| Launch in Steam / Heroic | done | `api.py` | Games page | `steam://rungameid/` and `heroic://launch/` URIs |
| Open install/prefix folder | done | `api.py` | Games page | xdg-open / gio. Works for all game sources. |
| Steam-running warning | done | `steam.py` | Games page | pgrep check before VDF edits |
| Copy App ID | done | — | Games page | Clipboard copy |

## 2. Environment Variables

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Global gaming env editor | done | `env_vars.py` | Environment page | ~/.config/environment.d/ |
| Env presets (NVIDIA, Debug, Gamemode) | done | `env_vars.py` | Environment page | Quick-apply preset groups |

## 3. System / GPU

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| GPU detection (NVIDIA + sysfs) | done | `gpu.py` | System page | nvidia-smi + /sys/class/drm |
| GPU temperature | done | `gpu.py` | System page | nvidia-smi + hwmon |
| GPU VRAM display | done | `gpu.py` | System page | nvidia-smi only |
| Power profile switching | done | `gpu.py` | System page | system76-power + powerprofilesctl |
| Open MangoHud config folder | done | — | GTK only | ~/.config/MangoHud |

## 4. Electron UI Parity

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Profiles UI (save/load/delete) | done | `profiles_storage.py` | Games page | Full save/load: launch opts, compat, env vars, power profile. Auto-match by game name. |
| Steam-running warning banner | done | `steam.py` | Games page | Show when editing with Steam open |
| Launch in Steam button | done | `api.py` | Games page | POST /open-uri endpoint |
| Open install/prefix folder | done | `api.py` | Games page | POST /open-path endpoint |
| Open MangoHud config folder | done | `api.py` | System page | POST /open-path endpoint |

## 5. Wine/Proton Prefix Management

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Show prefix size + creation date | done | `prefix.py` | Games page | du + stat. Works for Steam, Heroic, and Lutris. |
| Detect DXVK version in prefix | done | `prefix.py` | Games page | system32/d3d11.dll version |
| Detect VKD3D-Proton version | done | `prefix.py` | Games page | system32/d3d12.dll version |
| Delete prefix | done | `prefix.py` | Games page | With confirmation. Generic: accepts prefix_path for non-Steam games. |
| Open prefix in file manager | done | `api.py` | Games page | Via POST /open-path |

## 6. Shader Cache Management

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Per-game shader cache size | done | `shader_cache.py` | Games page | steamapps/shadercache/ |
| Clear shader cache per game | done | `shader_cache.py` | Games page | Delete shadercache/{app_id} |
| Total shader cache size | done | `shader_cache.py` | System page | Sum all app caches |
| Shader env var toggles | planned | `shader_cache.py` | Environment page | RADV_PERFTEST, MESA_SHADER_CACHE_DISABLE |

## 7. Gamescope Launch Builder

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Detect gamescope installed | done | `gamescope.py` | Games page | which gamescope |
| Visual command builder | done | `gamescope.py` | Games page | Resolution, FPS, FSR, HDR, integer scale. Available for Steam + Heroic. |
| Preview generated command | done | `gamescope.py` | Games page | Live preview string |
| Insert into launch options | done | `gamescope.py` | Games page | Prepend to existing |

## 8. Game-Specific Fixes Database

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Built-in fixes database | done | `fixes.py` | Games page | data/known_fixes.json |
| Show applicable fixes per game | done | `fixes.py` | Games page | Based on App ID + common. Available for all game sources. |
| One-click apply fix | done | `fixes.py` | Games page | Add env var or launch arg. Works for Steam + Heroic. |
| User-added fixes | done | `fixes.py` | Games page | ~/.config/protonshift/fixes/ |

## 9. MangoHud Config Editor

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Visual config editor | done | `mangohud.py` | MangoHud page | Toggle params, set values |
| Global config read/write | done | `mangohud.py` | MangoHud page | ~/.config/MangoHud/MangoHud.conf |
| Per-game config | done | `mangohud.py` | MangoHud page | wine-{name}.conf discovery + edit |
| MangoHud presets | done | `mangohud.py` | MangoHud page | Minimal, Standard, Full |

## 10. Game Save Backup/Restore

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Detect save locations | done | `saves.py` | Games page | Native + Proton prefix paths. Generic: accepts prefix_path for non-Steam games. |
| Show save size | done | `saves.py` | Games page | Per-game total |
| Backup saves (zip) | done | `saves.py` | Games page | ~/.config/protonshift/backups/ |
| Restore from backup | done | `saves.py` | Games page | Pick backup, extract |
| Auto-backup before prefix delete | planned | `saves.py` | Games page | Triggered by prefix management |

## 11. Display/Monitor Management

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Detect monitors | done | `display.py` | System page | xrandr (X11) / wlr-randr (Wayland) |
| Show resolution + refresh rate | done | `display.py` | System page | Per-monitor |
| Per-game display target | planned | `display.py` | Games page | DISPLAY env or gamescope --prefer-output |
| Quick resolution switch | done | `display.py` | System page | xrandr --mode via API |

## 12. Controller/Input Management

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Detect game controllers | done | `controllers.py` | Controllers page | /proc/bus/input + /dev/input |
| Show controller name + type | done | `controllers.py` | Controllers page | Xbox, PlayStation, Nintendo, generic |
| SDL controller mapping | done | `controllers.py` | Controllers page | SDL_GAMECONTROLLERCONFIG env |
| Per-game controller override | planned | `controllers.py` | Games page | Launch option env |

## 13. Heroic/Lutris Coverage Expansion

| Feature | Status | Module | UI | Notes |
|---------|--------|--------|----|-------|
| Heroic GamesConfig read/write | done | `heroic_config.py` | Games page | Read/write per-game JSON config |
| Heroic launch options editor | done | `heroic_config.py` | Games page | Edit `otherOptions` field |
| Heroic Wine/Proton selector | done | `heroic_config.py` | Games page | Scan tools/wine + tools/proton, write wineVersion |
| Heroic toggles (esync, fsync, DXVK, VKD3D, MangoHud, GameMode, NVIDIA Prime) | done | `heroic_config.py` | Games page | Toggle switches for GamesConfig booleans |
| Launch via Heroic URI | done | `api.py` | Games page | `heroic://launch/{app_id}` |
| Generic prefix-info endpoint | done | `prefix.py`, `api.py` | Games page | `?prefix_path=` query param for non-Steam |
| Generic saves endpoint | done | `saves.py`, `api.py` | Games page | `?prefix_path=` query param for non-Steam |
| Un-gated shared features | done | `game-detail.tsx` | Games page | Prefix, saves, gamescope, fixes, profiles now work for Heroic/Lutris |
| Quick presets for Heroic | done | `presets.py` | Games page | Same presets insert into Heroic launch options |
