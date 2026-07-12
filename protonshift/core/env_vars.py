"""Environment variables editor for ~/.config/environment.d/.

Lifted from the old backend, with the read/write escaping made symmetric
(review #29): ``read_conf`` now properly inverts ``write_conf``'s escaping
instead of a naive quote-strip, so values containing quotes or backslashes
survive a save/read round-trip instead of rotting each cycle.
"""

from __future__ import annotations

import re
from pathlib import Path

from .fsutil import atomic_write_text

ENV_D_DIR = Path.home() / ".config" / "environment.d"
GAMING_CONF = "70-protonshift.conf"


def _valid_key(key: str) -> bool:
    """Check if key is valid (alphanumeric + underscore)."""
    return bool(key and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key))


def get_env_d_dir() -> Path:
    """Get environment.d directory, creating if needed."""
    ENV_D_DIR.mkdir(parents=True, exist_ok=True)
    return ENV_D_DIR


def list_conf_files() -> list[Path]:
    """List .conf files in environment.d."""
    if not ENV_D_DIR.exists():
        return []
    return sorted(ENV_D_DIR.glob("*.conf"))


def _unescape(inner: str) -> str:
    """Invert ``write_conf``'s escaping in a single pass.

    ``write_conf`` turns ``\\`` into ``\\\\`` and ``"`` into ``\\"``. A pair of
    ``str.replace`` calls to undo that is order-dependent and corrupts values
    like ``a\\"b`` — so scan once and consume each backslash-escape explicitly.
    """
    out: list[str] = []
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner) and inner[i + 1] in ("\\", '"'):
            out.append(inner[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def read_conf(path: Path) -> dict[str, str]:
    """Read KEY=value pairs from a .conf file. Skips comments and empty lines."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                # invert write_conf: strip one layer of matching quotes, then
                # unescape (double-quoted only — single quotes are literal in
                # environment.d, matching systemd's parser).
                if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                    val = _unescape(val[1:-1])
                elif len(val) >= 2 and val[0] == "'" and val[-1] == "'":
                    val = val[1:-1]
                if key:
                    result[key] = val
    return result


def write_conf(path: Path, vars_dict: dict[str, str], header: str = "") -> bool:
    """Write KEY=value pairs to a .conf file atomically."""
    lines: list[str] = []
    if header:
        for h in header.strip().split("\n"):
            lines.append(f"# {h}" if not h.startswith("#") else h)
        lines.append("")
    for k, v in sorted(vars_dict.items()):
        if not _valid_key(k):
            continue
        escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{k}="{escaped}"')
    try:
        atomic_write_text(path, "\n".join(lines) + "\n")
    except OSError:
        return False
    return True


def get_gaming_conf_path() -> Path:
    """Path for our gaming env vars config."""
    return get_env_d_dir() / GAMING_CONF


def read_gaming_env() -> dict[str, str]:
    """Read ProtonShift env vars."""
    return read_conf(get_gaming_conf_path())


def write_gaming_env(vars_dict: dict[str, str]) -> bool:
    """Write ProtonShift env vars."""
    return write_conf(
        get_gaming_conf_path(),
        vars_dict,
        header="ProtonShift — global env vars for Steam/Proton.\nLogout and login for session-wide effect.",
    )


# Presets for quick apply
ENV_PRESETS: dict[str, dict[str, str]] = {
    "Proton (NVIDIA)": {
        "PROTON_ENABLE_WAYLAND": "1",
        "__GL_SHADER_DISK_CACHE": "1",
        "__GL_SHADER_DISK_CACHE_SKIP_CLEANUP": "1",
    },
    "Proton (AMD)": {
        "PROTON_ENABLE_WAYLAND": "1",
        "RADV_PERFTEST": "gpl,ngg_streamout",
        "AMD_VULKAN_ICD": "RADV",
    },
    "DXVK / VKD3D": {
        "DXVK_ASYNC": "1",
        "DXVK_STATE_CACHE": "1",
        "VKD3D_CONFIG": "dxr",
    },
    "Shader cache": {
        "__GL_SHADER_DISK_CACHE": "1",
        "__GL_SHADER_DISK_CACHE_SKIP_CLEANUP": "1",
        "MESA_SHADER_CACHE_DISABLE": "false",
        "MESA_SHADER_CACHE_MAX_SIZE": "4G",
        "RADV_PERFTEST": "gpl",
    },
    "Wayland": {
        "PROTON_ENABLE_WAYLAND": "1",
        "SDL_VIDEODRIVER": "wayland",
        "GDK_BACKEND": "wayland",
        "QT_QPA_PLATFORM": "wayland",
    },
    "Gamemode": {
        "STEAM_GAMEMODE": "1",
    },
    "Proton (Debug)": {
        "PROTON_LOG": "1",
        "WINEDEBUG": "+tid",
        "DXVK_LOG_LEVEL": "info",
        "VKD3D_DEBUG": "warn",
    },
}
