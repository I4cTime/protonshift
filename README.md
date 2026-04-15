# ProtonShift

Linux game configuration toolkit: GPU/display, launch options, Proton, environment variables.  
Like Nexus Mod Manager, but for game setup — not mods.

**Target:** Pop!_OS, Ubuntu 22.04+, Linux Mint, elementary OS.

## Features

- **Steam game list** — Discover installed games from Steam, Heroic, and Lutris
- **Launch options** — Edit per-game launch options (env vars + `%command%`)
- **Proton tools** — Select Proton/GE compatibility tools
- **Quick Install** — One-click Protontricks: vcrun2022, dotnet48, d3dx9, corefonts, arial
- **Environment** — Global gaming env vars in `~/.config/environment.d/`
- **System** — GPU info, temperature, power profile switching
- **Profiles** — Save/load game configuration profiles

## Two Frontends

### Electron (recommended)

Modern UI built with Next.js, React 19, Tailwind CSS v4, and HeroUI v3.  
Packages as AppImage (any Linux) and .deb (Ubuntu/Pop/Mint).

```bash
cd electron && pnpm install

# Development (Next.js dev server + Electron)
pnpm run dev

# Build AppImage + .deb
pnpm run dist
```

### GTK (native fallback)

Original GTK4 + libadwaita interface.

```bash
sudo apt install libgtk-4-1 libadwaita-1-0 gir1.2-gtk-4.0 gir1.2-adw-1 python3-vdf
pip install -e .
protonshift
```

Or: `./run.sh`

## Python API

Both frontends share the same Python backend. The Electron version spawns it automatically.  
You can also run it standalone:

```bash
pip install -e .
protonshift-api --port 8000
```

Endpoints: `/games`, `/env-vars`, `/system`, `/profiles`, `/presets`, and more.

## Architecture

```
┌─────────────────────────────────────┐
│  Electron / Next.js UI              │
│  (React 19 + Tailwind + HeroUI v3) │
└──────────┬──────────────────────────┘
           │ IPC (preload bridge)
┌──────────▼──────────────────────────┐
│  Electron Main Process              │
│  (spawns Python, proxies requests)  │
└──────────┬──────────────────────────┘
           │ HTTP localhost
┌──────────▼──────────────────────────┐
│  Python FastAPI Backend             │
│  steam.py │ gpu.py │ vdf_config.py  │
│  heroic.py│lutris.py│profiles.py    │
└─────────────────────────────────────┘
```
