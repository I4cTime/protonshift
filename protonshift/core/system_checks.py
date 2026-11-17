"""System checks for Diagnose: facts about this computer that explain a game not starting.

Launch check looks at one game's settings; these look at the machine under every
game: is there a working Vulkan driver, is there a 32-bit one for 32-bit games and
launchers, is there free space where the game and its Proton prefix live.

Every check answers in three states: ``ok``, ``problem`` or ``unknown``. The rule
that shapes all of them: a check that could not actually be carried out says
``unknown`` and why. It never says ``ok`` on a guess, because a green tick that
is wrong sends the user looking everywhere except the real cause. Functions here
never raise; whatever goes wrong becomes an ``unknown`` result.

Host commands go through :func:`host.host_run` so they reach the host from inside
the Flatpak, and the host's files are read under ``/run/host`` there. The runner
is injectable so tests never start a real process.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .host import host_run, in_flatpak
from .steam import FLATPAK_HOST_ROOT, host_display_path

Runner = Callable[..., subprocess.CompletedProcess]

OK = "ok"
PROBLEM = "problem"
UNKNOWN = "unknown"

_TIMEOUT = 5
_FLATPAK_STEAM_PARTS = (".var", "app", "com.valvesoftware.Steam")
# Driver manifests are a few hundred bytes; anything far larger is not one.
_MAX_MANIFEST_BYTES = 64 * 1024


@dataclass(frozen=True)
class Check:
    id: str
    state: str
    title: str
    detail: str
    fix: str


# --------------------------------------------------------------------------- #
# Steam
# --------------------------------------------------------------------------- #

def _has_flatpak_steam_parts(path: Path) -> bool:
    parts = path.parts
    n = len(_FLATPAK_STEAM_PARTS)
    return any(parts[i:i + n] == _FLATPAK_STEAM_PARTS for i in range(len(parts) - n + 1))


def steam_flavor(steam_root: Path | None) -> str:
    """``"flatpak"`` for Flathub's Steam, ``"native"`` for any other existing root, else ``"unknown"``."""
    if steam_root is None:
        return "unknown"
    try:
        root = Path(steam_root)
        if not root.exists():
            return "unknown"
        # ~/.steam/steam is often a symlink, so the resolved path decides as well.
        if _has_flatpak_steam_parts(root) or _has_flatpak_steam_parts(root.resolve()):
            return "flatpak"
        return "native"
    except (OSError, RuntimeError, TypeError, ValueError):
        return "unknown"


def steam_running(run: Runner = host_run) -> bool | None:
    """Whether Steam is running; ``None`` when that could not be found out."""
    try:
        proc = run(["pgrep", "-x", "steam"], capture_output=True, text=True, timeout=_TIMEOUT)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


# --------------------------------------------------------------------------- #
# Vulkan
# --------------------------------------------------------------------------- #

def _host_path(path: Path) -> Path:
    """``path`` as seen from here: under ``/run/host`` inside the Flatpak."""
    if in_flatpak() and path.is_absolute():
        return FLATPAK_HOST_ROOT / path.relative_to("/")
    return path


def default_icd_dirs() -> list[Path]:
    system = [Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d")]
    return [_host_path(d) for d in system] + [Path.home() / ".local/share/vulkan/icd.d"]


def _icd_manifests(icd_dirs: Sequence[Path]) -> list[Path]:
    found: list[Path] = []
    for d in icd_dirs:
        try:
            found.extend(sorted(p for p in Path(d).glob("*.json") if p.is_file()))
        except OSError:
            continue
    return found


def _could_look(icd_dirs: Sequence[Path]) -> bool:
    """True when the main ICD folder's parent tree (the first in the list) is visible to us.

    Inside a sandbox without the host-os permission, ``/run/host/usr/share`` is
    simply absent; finding no manifests there is not evidence that none exist.
    Only the first folder counts: ``~/.local/share`` always exists, so it would
    vouch for a search that never saw the system's drivers.
    """
    if not icd_dirs:
        return False
    try:
        return Path(icd_dirs[0]).parent.parent.is_dir()
    except OSError:
        return False


_SOFTWARE_NAMES = ("llvmpipe", "lavapipe", "softpipe", "swiftshader")
_HARDWARE_TYPES = (
    "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU",
    "PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU",
    "PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU",
)
_GPU_HEADER_RE = re.compile(r"^\s*GPU\s*(\d+)\s*:\s*$")
_FIELD_RE = re.compile(r"^\s*(deviceType|deviceName)\s*=\s*(.+?)\s*$")

# Loader and vulkaninfo wording when Vulkan itself cannot start (no driver, or a
# driver that does not load). Matched case-insensitively.
_DRIVER_FAILURE_MARKERS = (
    "error_incompatible_driver",
    "error_initialization_failed",
    "found no drivers",
    "cannot create vulkan instance",
    "vkenumeratephysicaldevices failed",
    "failed to find a physical device",
)
# How a missing host tool shows up through flatpak-spawn (it exists, the host tool doesn't).
_TOOL_MISSING_MARKERS = (
    "failed to execute child process",
    "failed to start command",
    "command not found",
)


def _parse_devices(text: str) -> list[tuple[str, str]]:
    """``(deviceType, deviceName)`` per ``GPUn:`` block of ``vulkaninfo --summary``.

    Only the ``Devices:`` section's ``GPUn:`` blocks are read, and only two keys
    in them; both have been stable across vulkaninfo versions for years. A missing
    key comes back as ``""`` so the caller can refuse to judge that device.
    """
    devices: list[list[str]] = []
    for line in text.splitlines():
        if _GPU_HEADER_RE.match(line):
            devices.append(["", ""])
            continue
        if not devices:
            continue
        m = _FIELD_RE.match(line)
        if m:
            idx = 0 if m.group(1) == "deviceType" else 1
            if not devices[-1][idx]:
                devices[-1][idx] = m.group(2)
    return [(t, n) for t, n in devices]


def _is_software(dev_type: str, name: str) -> bool:
    return "TYPE_CPU" in dev_type or any(s in name.lower() for s in _SOFTWARE_NAMES)


def _is_hardware(dev_type: str, name: str) -> bool:
    return dev_type in _HARDWARE_TYPES and bool(name) and not _is_software(dev_type, name)


def _first_line(text: str, markers: Sequence[str]) -> str:
    for line in text.splitlines():
        low = line.lower()
        if any(m in low for m in markers):
            return line.strip()[:200]
    return ""


_VULKAN_UNKNOWN = "Couldn't check Vulkan"


def _vulkan_from_manifests(icd_dirs: Sequence[Path]) -> Check:
    manifests = _icd_manifests(icd_dirs)
    if manifests:
        return Check(
            "vulkan", UNKNOWN, _VULKAN_UNKNOWN,
            "Vulkan driver files were found, but the tool that tests them (vulkaninfo, usually in "
            "the vulkan-tools package) is not installed, so ProtonShift can't tell whether they work.",
            "Install vulkan-tools from your distribution if you want this checked.",
        )
    if not _could_look(icd_dirs):
        return Check(
            "vulkan", UNKNOWN, _VULKAN_UNKNOWN,
            "ProtonShift can't see the folders where Vulkan drivers are installed, and vulkaninfo "
            "isn't available to ask instead.",
            "",
        )
    return Check(
        "vulkan", PROBLEM, "No Vulkan driver is installed",
        "No Vulkan driver files were found on this computer. Games that run through Proton need "
        "Vulkan, so they won't start without one.",
        "Install the Vulkan driver for your graphics card from your distribution (Mesa's Vulkan "
        "drivers for AMD and Intel, the NVIDIA driver for NVIDIA cards), then restart the computer.",
    )


def check_vulkan(run: Runner = host_run, icd_dirs: Sequence[Path] | None = None) -> Check:
    """Does Vulkan work on a real graphics card? Asks ``vulkaninfo``, else reads driver manifests."""
    dirs = list(icd_dirs) if icd_dirs is not None else default_icd_dirs()
    try:
        proc = run(["vulkaninfo", "--summary"], capture_output=True, text=True, timeout=_TIMEOUT)
    except FileNotFoundError:
        return _vulkan_from_manifests(dirs)
    except subprocess.TimeoutExpired:
        return Check(
            "vulkan", UNKNOWN, _VULKAN_UNKNOWN,
            "The Vulkan test (vulkaninfo) took longer than 5 seconds and was stopped, so there is "
            "no answer.",
            "",
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return Check("vulkan", UNKNOWN, _VULKAN_UNKNOWN, f"The Vulkan test could not be run ({exc}).", "")

    out = proc.stdout if isinstance(proc.stdout, str) else ""
    err = proc.stderr if isinstance(proc.stderr, str) else ""
    both = out + "\n" + err

    if proc.returncode != 0:
        reason = _first_line(both, _DRIVER_FAILURE_MARKERS)
        if reason:
            return Check(
                "vulkan", PROBLEM, "No Vulkan driver was found",
                f"Vulkan could not start on this computer (\"{reason}\"). Games that run through "
                "Proton need Vulkan, so they won't start.",
                "Install or reinstall the Vulkan driver for your graphics card from your distribution, "
                "then restart the computer.",
            )
        if proc.returncode == 127 or _first_line(both, _TOOL_MISSING_MARKERS):
            return _vulkan_from_manifests(dirs)
        return Check(
            "vulkan", UNKNOWN, _VULKAN_UNKNOWN,
            f"The Vulkan test (vulkaninfo) stopped with error code {proc.returncode} without saying "
            "why, so there is no answer.",
            "",
        )

    devices = _parse_devices(out)
    hardware = [n for t, n in devices if _is_hardware(t, n)]
    if hardware:
        names = ", ".join(dict.fromkeys(hardware))
        return Check("vulkan", OK, "Vulkan works", f"Vulkan is running on {names}.", "")
    if devices and all(_is_software(t, n) for t, n in devices):
        name = devices[0][1] or "a software renderer"
        return Check(
            "vulkan", PROBLEM, "Vulkan only works in software mode",
            f"The only Vulkan device is {name}, which draws on the processor instead of the graphics "
            "card. Games will be very slow or refuse to start.",
            "Install the Vulkan driver for your graphics card from your distribution (Mesa's Vulkan "
            "drivers for AMD and Intel, the NVIDIA driver for NVIDIA cards), then restart the computer.",
        )
    return Check(
        "vulkan", UNKNOWN, _VULKAN_UNKNOWN,
        "The Vulkan test ran, but ProtonShift couldn't make sense of what it printed.",
        "",
    )


# --------------------------------------------------------------------------- #
# 32-bit Vulkan
# --------------------------------------------------------------------------- #

def default_lib32_dirs() -> list[Path]:
    dirs = [Path("/usr/lib32"), Path("/usr/lib/i386-linux-gnu"), Path("/usr/lib/i686-linux-gnu")]
    lib64 = _host_path(Path("/usr/lib64"))
    try:
        # Fedora keeps 32-bit libraries in /usr/lib and 64-bit ones in a real /usr/lib64.
        # On Arch /usr/lib64 is a symlink to lib, and /usr/lib holds the 64-bit ones.
        fedora = lib64.is_dir() and not lib64.is_symlink()
    except OSError:
        fedora = False
    if fedora:
        dirs.append(Path("/usr/lib"))
    return [_host_path(d) for d in dirs]


def default_lib64_dirs() -> list[Path]:
    dirs = [Path("/usr/lib64"), Path("/usr/lib/x86_64-linux-gnu"), Path("/usr/lib")]
    return [_host_path(d) for d in dirs]


def elf_class(path: Path) -> int | None:
    """32 or 64 from the ELF header's EI_CLASS byte; ``None`` when not a readable ELF file."""
    try:
        with open(path, "rb") as f:
            head = f.read(5)
    except OSError:
        return None
    if len(head) < 5 or head[:4] != b"\x7fELF":
        return None
    return {1: 32, 2: 64}.get(head[4])


def _manifest_library(manifest: Path) -> str | None:
    try:
        if manifest.stat().st_size > _MAX_MANIFEST_BYTES:
            return None
        data = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    icd = data.get("ICD") if isinstance(data, dict) else None
    lib = icd.get("library_path") if isinstance(icd, dict) else None
    if isinstance(lib, str) and lib and "\x00" not in lib:
        return lib
    return None


def _library_candidates(manifest: Path, lib: str, search: Sequence[Path]) -> list[Path]:
    # Same rules as the Vulkan loader: an absolute path is used as is, a path with
    # a slash is relative to the manifest, a bare name is looked up like dlopen does.
    if lib.startswith("/"):
        return [_host_path(Path(lib))]
    if "/" in lib:
        return [manifest.parent / lib]
    return [Path(d) / lib for d in search]


def check_vulkan_32bit(
    flavor: str,
    icd_dirs: Sequence[Path] | None = None,
    lib_dirs: Sequence[Path] | None = None,
    lib64_dirs: Sequence[Path] | None = None,
) -> Check:
    """Is there a 32-bit Vulkan driver? Judged from the driver libraries' ELF headers.

    ``lib_dirs`` are the 32-bit library folders, ``lib64_dirs`` the 64-bit ones.
    Both are searched for bare library names and the ELF class decides, since a
    folder's name alone doesn't say which kind it holds on every distribution.
    """
    title_unknown = "Couldn't check for a 32-bit Vulkan driver"
    if flavor == "flatpak":
        return Check(
            "vulkan-32bit", UNKNOWN, title_unknown,
            "Steam runs as a Flatpak and brings its own drivers, so the ones installed on this "
            "computer don't decide this.",
            "",
        )
    try:
        dirs = list(icd_dirs) if icd_dirs is not None else default_icd_dirs()
        lib32 = list(lib_dirs) if lib_dirs is not None else default_lib32_dirs()
        lib64 = list(lib64_dirs) if lib64_dirs is not None else default_lib64_dirs()
        search = lib32 + [d for d in lib64 if d not in lib32]

        manifests = _icd_manifests(dirs)
        found32: list[str] = []
        found64: list[str] = []
        for manifest in manifests:
            lib = _manifest_library(manifest)
            if lib is None:
                continue
            for candidate in _library_candidates(manifest, lib, search):
                cls = elf_class(candidate)
                if cls == 32:
                    found32.append(lib)
                elif cls == 64:
                    found64.append(lib)
    except (OSError, RuntimeError, ValueError) as exc:
        return Check("vulkan-32bit", UNKNOWN, title_unknown, f"The driver files could not be read ({exc}).", "")

    if found32:
        names = ", ".join(dict.fromkeys(found32))
        return Check(
            "vulkan-32bit", OK, "A 32-bit Vulkan driver is installed",
            f"32-bit games and launchers can use Vulkan through {names}.", "",
        )
    if manifests and found64:
        return Check(
            "vulkan-32bit", PROBLEM, "No 32-bit Vulkan driver was found",
            "The Vulkan driver on this computer is only installed for 64-bit programs. Many Windows "
            "games and their launchers are 32-bit and won't start without the 32-bit driver.",
            "Install the 32-bit Vulkan driver for your GPU from your distribution "
            "(often named lib32-... or ...:i386).",
        )
    if not manifests:
        detail = "No Vulkan driver files were found, so there was nothing to check for a 32-bit version."
    else:
        detail = (
            "Vulkan driver files were found, but ProtonShift couldn't find the driver libraries they "
            "point to, so it can't tell whether a 32-bit one is installed."
        )
    return Check("vulkan-32bit", UNKNOWN, title_unknown, detail, "")


# --------------------------------------------------------------------------- #
# Disk space
# --------------------------------------------------------------------------- #

_DISK_WORDING = {
    "library": ("disk-library", "the drive holding the game"),
    "prefix": ("disk-prefix", "the drive holding the game's Proton prefix"),
}


def check_disk(path: Path | None, which: str, min_free_bytes: int = 1 << 30) -> Check:
    """Free space on the drive under ``path``; ``which`` is ``"library"`` or ``"prefix"``."""
    check_id, where = _DISK_WORDING.get(which, _DISK_WORDING["library"])
    title_unknown = f"Couldn't check free space on {where}"
    if path is None:
        return Check(check_id, UNKNOWN, title_unknown, f"ProtonShift doesn't know where {where} is.", "")
    shown = host_display_path(path)
    try:
        free = shutil.disk_usage(path).free
    except (OSError, ValueError, TypeError):
        return Check(
            check_id, UNKNOWN, title_unknown,
            f"The folder {shown} couldn't be read, so its free space is unknown.", "",
        )
    gib = f"{free / (1 << 30):.1f} GiB"
    if free < min_free_bytes:
        return Check(
            check_id, PROBLEM, f"{where[0].upper()}{where[1:]} is almost full",
            f"Only {gib} is free on {where} ({shown}). Games can fail to start or crash when they "
            "can't write saves, shader caches or updates.",
            "Free up space on that drive, for example by deleting files you no longer need or moving "
            "a game to another drive.",
        )
    return Check(
        check_id, OK, f"Enough free space on {where}",
        f"{gib} is free on {where} ({shown}).", "",
    )


def _same_device(a: Path | None, b: Path | None) -> bool:
    if a is None or b is None:
        return False
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except (OSError, ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# All together
# --------------------------------------------------------------------------- #

def run_checks(
    *,
    steam_root: Path | None,
    install_path: Path | None,
    prefix_path: Path | None,
    run: Runner = host_run,
) -> list[Check]:
    """Every system check for one game, in display order."""
    checks = [
        check_vulkan(run),
        check_vulkan_32bit(steam_flavor(steam_root)),
        check_disk(install_path, "library"),
    ]
    # One drive, one answer: the same free space twice reads like two problems.
    if not _same_device(install_path, prefix_path):
        checks.append(check_disk(prefix_path, "prefix"))
    return checks
