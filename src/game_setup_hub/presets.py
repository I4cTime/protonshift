"""Launch preset metadata, detection, and install instructions."""

from __future__ import annotations

from dataclasses import dataclass

from game_setup_hub.tool_check import is_scopebuddy_available, is_tool_available


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
    LaunchPreset(
        name="ScopeBuddy",
        value="SCB_AUTO_RES=1 SCB_AUTO_HDR=1 SCB_AUTO_VRR=1 scb --",
        description="Wrap with ScopeBuddy: auto resolution, HDR, and VRR from the primary display.",
        install_command="curl -fsSL https://raw.githubusercontent.com/HikariKnight/ScopeBuddy/refs/heads/main/bin/scopebuddy | sudo tee /usr/local/bin/scopebuddy && sudo chmod +x /usr/local/bin/scopebuddy",
        install_url="https://github.com/OpenGamingCollective/ScopeBuddy",
    ),
]

LAUNCH_PRESETS_MAP: dict[str, str] = {p.name: p.value for p in LAUNCH_PRESETS}
