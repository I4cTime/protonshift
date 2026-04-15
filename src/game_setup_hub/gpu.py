"""GPU and power profile detection. Cross-distro: Pop (system76-power), Ubuntu (power-profiles-daemon)."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GPUInfo:
    name: str
    driver: str
    vram_mb: int | None
    temperature: float | None


def get_gpu_info() -> list[GPUInfo]:
    """Get GPU info via nvidia-smi or sysfs."""
    gpus: list[GPUInfo] = []
    # NVIDIA
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                name = parts[0] if len(parts) > 0 else "NVIDIA GPU"
                driver = parts[1] if len(parts) > 1 else ""
                vram = None
                if len(parts) > 2:
                    try:
                        vram = int(float(parts[2].replace(" ", "").replace("MiB", "")))
                    except ValueError:
                        pass
                temp = None
                if len(parts) > 3:
                    try:
                        temp = float(parts[3])
                    except ValueError:
                        pass
                gpus.append(GPUInfo(name=name, driver=driver, vram_mb=vram, temperature=temp))
            return gpus
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: sysfs (basic)
    drm = Path("/sys/class/drm")
    if drm.exists():
        for card in sorted(drm.glob("card[0-9]")):
            if "-" in card.name:
                continue
            uevent = card / "device" / "uevent"
            try:
                if uevent.exists():
                    name = "Unknown GPU"
                    with open(uevent, encoding="utf-8", errors="replace") as f:
                        for line in f:
                            if line.startswith("DRIVER="):
                                name = line.split("=", 1)[1].strip()
                                break
                    temp = _read_hwmon_temp(card / "device")
                    gpus.append(GPUInfo(name=name, driver="", vram_mb=None, temperature=temp))
            except OSError:
                pass
    return gpus


def _read_hwmon_temp(device_path: Path) -> float | None:
    """Read GPU temperature from hwmon sysfs."""
    hwmon_dir = device_path / "hwmon"
    if not hwmon_dir.exists():
        return None
    try:
        for hwmon in sorted(hwmon_dir.iterdir()):
            temp_file = hwmon / "temp1_input"
            if temp_file.exists():
                raw = temp_file.read_text().strip()
                return float(raw) / 1000.0
    except (OSError, ValueError):
        pass
    return None


def get_power_profiles() -> list[str]:
    """Get available power profiles."""
    # system76-power (Pop)
    try:
        r = subprocess.run(["system76-power", "profile", "list"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            profiles = []
            for line in r.stdout.split("\n"):
                if re.match(r"^\s*\*\s*\w+", line):
                    # * Performance, * Balanced, etc.
                    m = re.search(r"\*\s*(\w+)", line)
                    if m:
                        profiles.append(m.group(1).lower().capitalize())
            if profiles:
                return profiles
    except FileNotFoundError:
        pass

    # power-profiles-daemon (Ubuntu)
    try:
        r = subprocess.run(["powerprofilesctl", "list"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            profiles = []
            for line in r.stdout.split("\n"):
                if "*" in line:
                    m = re.search(r"[\*]\s*([\w-]+)", line)
                    if m:
                        profiles.append(m.group(1))
            if profiles:
                return ["performance", "balanced", "power-saver"]
    except FileNotFoundError:
        pass

    return []


def get_current_power_profile() -> str | None:
    """Get current power profile."""
    try:
        r = subprocess.run(["system76-power", "profile"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip().lower().capitalize()
    except FileNotFoundError:
        pass
    try:
        r = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def set_power_profile(profile: str) -> tuple[bool, str]:
    """Set power profile. Returns (success, message)."""
    profile_lower = profile.lower()
    try:
        r = subprocess.run(
            ["system76-power", "profile", profile_lower],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return True, f"Set to {profile}"
        return False, r.stderr or "Failed"
    except FileNotFoundError:
        pass
    try:
        r = subprocess.run(
            ["powerprofilesctl", "set", profile_lower],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return True, f"Set to {profile}"
        return False, r.stderr or "Failed"
    except FileNotFoundError:
        return False, "No power profile tool (system76-power or powerprofilesctl)"
