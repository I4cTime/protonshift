"""MangoHud configuration management."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

MANGOHUD_CONFIG_DIR = Path.home() / ".config" / "MangoHud"
MANGOHUD_GLOBAL_CONF = MANGOHUD_CONFIG_DIR / "MangoHud.conf"

MANGOHUD_PRESETS: dict[str, dict[str, str]] = {
    "minimal": {
        "fps": "",
        "fps_only": "",
    },
    "standard": {
        "fps": "",
        "frametime": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "gpu_stats": "",
        "gpu_temp": "",
        "vram": "",
        "ram": "",
    },
    "full": {
        "fps": "",
        "frametime": "",
        "frame_timing": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "cpu_power": "",
        "cpu_mhz": "",
        "gpu_stats": "",
        "gpu_temp": "",
        "gpu_power": "",
        "gpu_core_clock": "",
        "gpu_mem_clock": "",
        "vram": "",
        "ram": "",
        "swap": "",
        "procmem": "",
        "io_read": "",
        "io_write": "",
        "wine": "",
        "vulkan_driver": "",
        "engine_version": "",
        "arch": "",
        "gamemode": "",
    },
    "fps-only": {
        "fps": "",
        "fps_only": "",
        "position": "top-right",
        "font_size": "24",
        "background_alpha": "0",
    },
    "cpu-gpu": {
        "fps": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "cpu_mhz": "",
        "gpu_stats": "",
        "gpu_temp": "",
        "gpu_core_clock": "",
        "gpu_mem_clock": "",
        "vram": "",
    },
    "benchmark": {
        "fps": "",
        "frametime": "",
        "frame_timing": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "cpu_power": "",
        "cpu_mhz": "",
        "gpu_stats": "",
        "gpu_temp": "",
        "gpu_power": "",
        "gpu_core_clock": "",
        "vram": "",
        "ram": "",
        "io_read": "",
        "io_write": "",
        "output_folder": "~/mangohud_logs",
    },
    "battery-saver": {
        "fps": "",
        "cpu_temp": "",
        "gpu_temp": "",
        "fps_limit": "30",
        "background_alpha": "0.2",
    },
    "streaming": {
        "fps": "",
        "frametime": "",
        "cpu_stats": "",
        "gpu_stats": "",
        "position": "top-right",
        "font_size": "18",
        "background_alpha": "0.5",
    },
    "debug": {
        "fps": "",
        "frametime": "",
        "frame_timing": "",
        "cpu_stats": "",
        "cpu_temp": "",
        "cpu_power": "",
        "cpu_mhz": "",
        "gpu_stats": "",
        "gpu_temp": "",
        "gpu_power": "",
        "gpu_core_clock": "",
        "gpu_mem_clock": "",
        "vram": "",
        "ram": "",
        "swap": "",
        "procmem": "",
        "io_read": "",
        "io_write": "",
        "wine": "",
        "vulkan_driver": "",
        "engine_version": "",
        "arch": "",
        "gamemode": "",
        "output_folder": "~/mangohud_logs",
    },
}

# All known MangoHud toggle/value parameters
MANGOHUD_PARAMS: list[dict[str, str]] = [
    {"key": "fps", "label": "FPS Counter", "type": "toggle"},
    {"key": "fps_only", "label": "FPS Only (minimal)", "type": "toggle"},
    {"key": "frametime", "label": "Frame Time", "type": "toggle"},
    {"key": "frame_timing", "label": "Frame Time Graph", "type": "toggle"},
    {"key": "cpu_stats", "label": "CPU Usage", "type": "toggle"},
    {"key": "cpu_temp", "label": "CPU Temperature", "type": "toggle"},
    {"key": "cpu_power", "label": "CPU Power", "type": "toggle"},
    {"key": "cpu_mhz", "label": "CPU Frequency", "type": "toggle"},
    {"key": "gpu_stats", "label": "GPU Usage", "type": "toggle"},
    {"key": "gpu_temp", "label": "GPU Temperature", "type": "toggle"},
    {"key": "gpu_power", "label": "GPU Power", "type": "toggle"},
    {"key": "gpu_core_clock", "label": "GPU Core Clock", "type": "toggle"},
    {"key": "gpu_mem_clock", "label": "GPU Mem Clock", "type": "toggle"},
    {"key": "vram", "label": "VRAM Usage", "type": "toggle"},
    {"key": "ram", "label": "RAM Usage", "type": "toggle"},
    {"key": "swap", "label": "Swap Usage", "type": "toggle"},
    {"key": "procmem", "label": "Process Memory", "type": "toggle"},
    {"key": "io_read", "label": "IO Read", "type": "toggle"},
    {"key": "io_write", "label": "IO Write", "type": "toggle"},
    {"key": "wine", "label": "Wine/Proton Version", "type": "toggle"},
    {"key": "vulkan_driver", "label": "Vulkan Driver", "type": "toggle"},
    {"key": "engine_version", "label": "Engine Version", "type": "toggle"},
    {"key": "arch", "label": "Architecture", "type": "toggle"},
    {"key": "gamemode", "label": "GameMode Status", "type": "toggle"},
    {"key": "no_display", "label": "No Display (logging only)", "type": "toggle"},
    {"key": "fps_limit", "label": "FPS Limit", "type": "value"},
    {"key": "position", "label": "Position", "type": "value"},
    {"key": "font_size", "label": "Font Size", "type": "value"},
    {"key": "background_alpha", "label": "Background Opacity", "type": "value"},
    {"key": "toggle_hud", "label": "Toggle Hotkey", "type": "value"},
    {"key": "output_folder", "label": "Log Output Folder", "type": "value"},
]


def is_mangohud_available() -> bool:
    """Check if MangoHud is installed."""
    return shutil.which("mangohud") is not None


def read_mangohud_config(path: Path | None = None) -> dict[str, str]:
    """Parse a MangoHud config file into key-value pairs.
    Toggle-only params have empty string values.
    """
    if path is None:
        path = MANGOHUD_GLOBAL_CONF
    if not path.exists():
        return {}
    config: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
            else:
                config[line] = ""
    except OSError:
        pass
    return config


def write_mangohud_config(config: dict[str, str], path: Path | None = None) -> bool:
    """Write a MangoHud config file from key-value pairs."""
    if path is None:
        path = MANGOHUD_GLOBAL_CONF
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for key, value in config.items():
        if value:
            lines.append(f"{key}={value}")
        else:
            lines.append(key)
    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def get_per_game_config_path(game_name: str) -> Path:
    """Get the per-game config path for MangoHud."""
    safe_name = game_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return MANGOHUD_CONFIG_DIR / f"wine-{safe_name}.conf"


def list_per_game_configs() -> list[dict[str, str]]:
    """List all existing per-game MangoHud config files."""
    if not MANGOHUD_CONFIG_DIR.exists():
        return []
    configs: list[dict[str, str]] = []
    for conf in sorted(MANGOHUD_CONFIG_DIR.glob("wine-*.conf")):
        name = conf.stem.replace("wine-", "")
        configs.append({"name": name, "path": str(conf)})
    return configs
