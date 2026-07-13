"""MangoHud configuration management.

Lifted from the old backend. Three changes:
* ``read_mangohud_config`` lets a real read error (OSError) propagate instead of
  swallowing it into ``{}`` — the controller distinguishes "couldn't read" from
  "empty config" and refuses to save over an unread file (same safety as env).
* per-game listing uses ``removeprefix`` not ``replace`` (review #L1), so a name
  like ``wine-my_wine-game`` no longer collapses its inner ``wine-``.
* ``write_mangohud_config`` merges into the existing file, preserving comments
  and blank lines (review #L2) instead of rewriting from the dict.
"""

from __future__ import annotations

from pathlib import Path

from .fsutil import atomic_write_text
from .paths import sanitize_filename
from .tool_check import is_tool_available

MANGOHUD_CONFIG_DIR = Path.home() / ".config" / "MangoHud"
MANGOHUD_GLOBAL_CONF = MANGOHUD_CONFIG_DIR / "MangoHud.conf"

MANGOHUD_PRESETS: dict[str, dict[str, str]] = {
    "minimal": {"fps": "", "fps_only": ""},
    "standard": {
        "fps": "", "frametime": "", "cpu_stats": "", "cpu_temp": "",
        "gpu_stats": "", "gpu_temp": "", "vram": "", "ram": "",
    },
    "full": {
        "fps": "", "frametime": "", "frame_timing": "", "cpu_stats": "",
        "cpu_temp": "", "cpu_power": "", "cpu_mhz": "", "gpu_stats": "",
        "gpu_temp": "", "gpu_power": "", "gpu_core_clock": "", "gpu_mem_clock": "",
        "vram": "", "ram": "", "swap": "", "procmem": "", "io_read": "",
        "io_write": "", "wine": "", "vulkan_driver": "", "engine_version": "",
        "arch": "", "gamemode": "",
    },
    "fps-only": {
        "fps": "", "fps_only": "", "position": "top-right",
        "font_size": "24", "background_alpha": "0",
    },
    "cpu-gpu": {
        "fps": "", "cpu_stats": "", "cpu_temp": "", "cpu_mhz": "",
        "gpu_stats": "", "gpu_temp": "", "gpu_core_clock": "",
        "gpu_mem_clock": "", "vram": "",
    },
    "benchmark": {
        "fps": "", "frametime": "", "frame_timing": "", "cpu_stats": "",
        "cpu_temp": "", "cpu_power": "", "cpu_mhz": "", "gpu_stats": "",
        "gpu_temp": "", "gpu_power": "", "gpu_core_clock": "", "vram": "",
        "ram": "", "io_read": "", "io_write": "", "output_folder": "~/mangohud_logs",
    },
    "battery-saver": {
        "fps": "", "cpu_temp": "", "gpu_temp": "", "fps_limit": "30",
        "background_alpha": "0.2",
    },
    "streaming": {
        "fps": "", "frametime": "", "cpu_stats": "", "gpu_stats": "",
        "position": "top-right", "font_size": "18", "background_alpha": "0.5",
    },
}

# All known MangoHud toggle/value parameters (key, label, type)
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
    return is_tool_available("mangohud")


def read_mangohud_config(path: Path | None = None) -> dict[str, str]:
    """Parse a MangoHud config file into key-value pairs (toggles map to "").

    A missing file returns ``{}``. A read error is **not** swallowed — it
    propagates so the caller can tell "couldn't read" from "empty".
    """
    if path is None:
        path = MANGOHUD_GLOBAL_CONF
    if not path.exists():
        return {}
    config: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
        else:
            config[line] = ""
    return config


def _format_param(key: str, value: str) -> str:
    return f"{key}={value}" if value else key


def write_mangohud_config(config: dict[str, str], path: Path | None = None) -> bool:
    """Write a MangoHud config, merging into the existing file (review #L2).

    Comments and blank lines are preserved in place; parameter lines are updated
    from ``config``; parameters no longer in ``config`` are dropped; new ones are
    appended. Not bash, so no block handling is needed — just line-oriented merge.
    """
    if path is None:
        path = MANGOHUD_GLOBAL_CONF
    try:
        existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        return False

    written: set[str] = set()
    out: list[str] = []
    for raw in existing:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            out.append(raw)  # comment / blank — keep verbatim
            continue
        key = stripped.partition("=")[0].strip() if "=" in stripped else stripped
        if key in config:
            out.append(_format_param(key, config[key]))
            written.add(key)
        # else: parameter removed in the UI — drop it

    for key, value in config.items():
        if key and key not in written:
            out.append(_format_param(key, value))

    body = "\n".join(out)
    if body and not body.endswith("\n"):
        body += "\n"
    try:
        MANGOHUD_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, body)
        return True
    except OSError:
        return False


def get_per_game_config_path(game_name: str) -> Path:
    """Per-game config path. ``game_name`` is sanitised against traversal."""
    safe_name = sanitize_filename(game_name.replace(" ", "_"), fallback="game")
    return MANGOHUD_CONFIG_DIR / f"wine-{safe_name}.conf"


def list_per_game_configs() -> list[dict[str, str]]:
    """List existing per-game MangoHud config files."""
    if not MANGOHUD_CONFIG_DIR.exists():
        return []
    configs: list[dict[str, str]] = []
    for conf in sorted(MANGOHUD_CONFIG_DIR.glob("wine-*.conf")):
        configs.append({"name": conf.stem.removeprefix("wine-"), "path": str(conf)})
    return configs


def read_per_game_config(game_name: str) -> tuple[bool, dict[str, str]]:
    """``(exists, config)`` for a per-game override. Read errors propagate."""
    path = get_per_game_config_path(game_name)
    if not path.exists():
        return False, {}
    return True, read_mangohud_config(path)


def write_per_game_config(game_name: str, config: dict[str, str]) -> bool:
    """Write a per-game override (merge-preserving, atomic)."""
    return write_mangohud_config(config, get_per_game_config_path(game_name))


def delete_per_game_config(game_name: str) -> bool:
    """Remove a per-game override file."""
    try:
        get_per_game_config_path(game_name).unlink(missing_ok=True)
        return True
    except OSError:
        return False
