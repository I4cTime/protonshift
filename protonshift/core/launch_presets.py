"""Launch-option quick presets: common snippets you append to a game's launch
options, each gated on whether the underlying tool is installed.

Ported from the original ProtonShift ``presets.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tool_check import is_scopebuddy_available, is_tool_available


@dataclass
class LaunchPreset:
    name: str
    value: str
    description: str = ""
    install_url: str = ""

    def is_installed(self) -> bool:
        if self.value == "gamemoderun":
            return is_tool_available("gamemoderun")
        if "MANGOHUD" in self.value:
            return is_tool_available("mangohud")
        if self.name == "ScopeBuddy" or " scb --" in self.value or " scopebuddy --" in self.value:
            return is_scopebuddy_available()
        return True


LAUNCH_PRESETS: list[LaunchPreset] = [
    LaunchPreset(
        name="Gamemode",
        value="gamemoderun",
        description="Optimizes CPU governor, GPU performance, and process priority for gaming.",
        install_url="https://github.com/FeralInteractive/gamemode",
    ),
    LaunchPreset(
        name="Force NVIDIA dGPU",
        value="__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia",
        description="Use the NVIDIA GPU on hybrid laptops (Intel+NVIDIA). Requires NVIDIA drivers.",
    ),
    LaunchPreset(
        name="MangoHud (FPS)",
        value="MANGOHUD=1",
        description="FPS overlay with GPU/CPU stats, temps, and frametime graph.",
        install_url="https://github.com/flightlessmango/MangoHud",
    ),
    LaunchPreset(
        name="Proton Log",
        value="PROTON_LOG=1",
        description="Write a Proton debug log to /tmp/proton_*.log. Useful for troubleshooting.",
    ),
    LaunchPreset(
        name="ScopeBuddy",
        value="SCB_AUTO_RES=1 SCB_AUTO_HDR=1 SCB_AUTO_VRR=1 scb --",
        description="Wrap with ScopeBuddy: auto resolution, HDR, and VRR from the primary display.",
        install_url="https://github.com/HikariKnight/ScopeBuddy",
    ),
]


def launch_presets() -> list[dict]:
    """Presets as plain dicts for QML, each tagged with live install status."""
    return [
        {
            "name": p.name,
            "value": p.value,
            "description": p.description,
            "installUrl": p.install_url,
            "installed": p.is_installed(),
        }
        for p in LAUNCH_PRESETS
    ]
