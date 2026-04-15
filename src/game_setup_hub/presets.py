"""Launch preset metadata, detection, and install instructions."""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass
class LaunchPreset:
    """Launch option preset with description and install info."""

    name: str
    value: str
    description: str = ""
    install_command: str = ""
    install_url: str = ""

    def is_installed(self) -> bool:
        """Check if the tool/feature is available."""
        if self.value == "gamemoderun":
            return _check_gamemode()
        if "MANGOHUD" in self.value:
            return _check_mangohud()
        return True  # No check for env vars, Proton Log, NVIDIA dGPU


def _check_gamemode() -> bool:
    """Check if gamemode is installed."""
    return shutil.which("gamemoderun") is not None


def _check_mangohud() -> bool:
    """Check if MangoHud is installed."""
    return shutil.which("mangohud") is not None


LAUNCH_PRESETS: list[LaunchPreset] = [
    LaunchPreset(
        name="Gamemode",
        value="gamemoderun",
        description="Optimizes CPU governor, GPU performance, and process priority for gaming.",
        install_command="sudo apt install gamemode",
        install_url="https://github.com/FeralInteractive/gamemode",
    ),
    LaunchPreset(
        name="Force NVIDIA dGPU",
        value="__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia",
        description="Use NVIDIA GPU on hybrid laptops (Intel+NVIDIA). Requires NVIDIA drivers.",
    ),
    LaunchPreset(
        name="MangoHud (FPS)",
        value="MANGOHUD=1",
        description="FPS overlay with GPU/CPU stats, temps, and frametime graph.",
        install_command="sudo apt install mangohud",
        install_url="https://github.com/flightrecorder/mangohud",
    ),
    LaunchPreset(
        name="Proton Log",
        value="PROTON_LOG=1",
        description="Write Proton debug log to /tmp/proton_*.log. Useful for troubleshooting.",
    ),
]

LAUNCH_PRESETS_MAP: dict[str, str] = {p.name: p.value for p in LAUNCH_PRESETS}
