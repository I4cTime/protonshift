"""System checks for Diagnose: every state of every check, with fake runners and fake folders.

No real subprocess, no real /usr: runners return a ``CompletedProcess`` or raise,
and ICD manifests, driver libraries and ELF headers are built under ``tmp_path``.
Qt-free.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections import namedtuple
from pathlib import Path

import pytest

from protonshift.core import system_checks as sc

# Trimmed from `vulkaninfo --summary` (Vulkan Instance Version 1.4.363) on an
# Arch laptop with an NVIDIA RTX 4080 Laptop GPU and the proprietary driver.
REAL_SUMMARY = """\
==========
VULKANINFO
==========

Vulkan Instance Version: 1.4.363


Instance Extensions: count = 27
-------------------------------
VK_EXT_acquire_drm_display             : extension revision 1
VK_KHR_surface                         : extension revision 25

Instance Layers: count = 11
---------------------------
VK_LAYER_MESA_device_select        Linux device selection layer                                 1.4.303  version 1
VK_LAYER_VALVE_steam_overlay_64    Steam Overlay Layer                                          1.3.207  version 1

Devices:
========
GPU0:
\tapiVersion         = 1.4.351
\tdriverVersion      = 615.78.8.0
\tvendorID           = 0x10de
\tdeviceID           = 0x27e0
\tdeviceType         = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
\tdeviceName         = NVIDIA GeForce RTX 4080 Laptop GPU
\tdriverID           = DRIVER_ID_NVIDIA_PROPRIETARY
\tdriverName         = NVIDIA
\tdriverInfo         = 615.78.08
\tconformanceVersion = 1.4.3.3
"""

LLVMPIPE_ONLY = """\
Devices:
========
GPU0:
\tapiVersion         = 1.3.289
\tdeviceType         = PHYSICAL_DEVICE_TYPE_CPU
\tdeviceName         = llvmpipe (LLVM 18.1.8, 256 bits)
\tdriverID           = DRIVER_ID_MESA_LLVMPIPE
"""

GPU_PLUS_LLVMPIPE = """\
Devices:
========
GPU0:
\tdeviceType         = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
\tdeviceName         = AMD Radeon Graphics (RADV RENOIR)
GPU1:
\tdeviceType         = PHYSICAL_DEVICE_TYPE_CPU
\tdeviceName         = llvmpipe (LLVM 18.1.8, 256 bits)
"""

NO_DRIVER_STDERR = """\
ERROR: [Loader Message] Code 0 : vkCreateInstance: Found no drivers!
Cannot create Vulkan instance.
This problem is often caused by a faulty installation of the Vulkan driver or attempting to use a GPU \
that does not support Vulkan.
ERROR at ./vulkaninfo/vulkaninfo.h:573:vkCreateInstance failed with ERROR_INCOMPATIBLE_DRIVER
"""


def runner(returncode: int = 0, stdout: str = "", stderr: str = ""):
    calls: list[tuple[list[str], dict]] = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def raising(exc: BaseException):
    def run(argv, **kwargs):
        raise exc

    return run


def write_manifest(folder: Path, name: str, library_path: object) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps({"file_format_version": "1.0.1", "ICD": {"library_path": library_path}}))
    return path


def write_elf(path: Path, ei_class: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x7fELF" + bytes([ei_class]) + b"\x01\x01" + b"\x00" * 9)
    return path


@pytest.fixture(autouse=True)
def not_sandboxed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "in_flatpak", lambda: False)


# --------------------------------------------------------------------------- #
# steam_flavor / steam_running
# --------------------------------------------------------------------------- #

def test_steam_flavor_flatpak(tmp_path: Path) -> None:
    root = tmp_path / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"
    root.mkdir(parents=True)
    assert sc.steam_flavor(root) == "flatpak"


def test_steam_flavor_flatpak_through_symlink(tmp_path: Path) -> None:
    real = tmp_path / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam"
    real.mkdir(parents=True)
    link = tmp_path / ".steam-steam"
    link.symlink_to(real)
    assert sc.steam_flavor(link) == "flatpak"


def test_steam_flavor_native(tmp_path: Path) -> None:
    root = tmp_path / ".local" / "share" / "Steam"
    root.mkdir(parents=True)
    assert sc.steam_flavor(root) == "native"


def test_steam_flavor_unknown(tmp_path: Path) -> None:
    assert sc.steam_flavor(None) == "unknown"
    assert sc.steam_flavor(tmp_path / "missing") == "unknown"


def test_steam_running_states() -> None:
    run = runner(0)
    assert sc.steam_running(run) is True
    argv, kwargs = run.calls[0]
    assert argv == ["pgrep", "-x", "steam"]
    assert kwargs["timeout"] == 5
    assert sc.steam_running(runner(1)) is False
    assert sc.steam_running(runner(2)) is None
    assert sc.steam_running(raising(FileNotFoundError())) is None
    assert sc.steam_running(raising(subprocess.TimeoutExpired(["pgrep"], 5))) is None


# --------------------------------------------------------------------------- #
# check_vulkan
# --------------------------------------------------------------------------- #

def test_vulkan_ok_on_real_output(tmp_path: Path) -> None:
    run = runner(0, REAL_SUMMARY)
    c = sc.check_vulkan(run, icd_dirs=[tmp_path / "icd.d"])
    assert c.id == "vulkan"
    assert c.state == "ok"
    assert "NVIDIA GeForce RTX 4080 Laptop GPU" in c.detail
    assert c.fix == ""
    argv, kwargs = run.calls[0]
    assert argv == ["vulkaninfo", "--summary"]
    assert kwargs["timeout"] == 5 and kwargs["text"] is True


def test_vulkan_ok_when_a_gpu_sits_beside_llvmpipe(tmp_path: Path) -> None:
    c = sc.check_vulkan(runner(0, GPU_PLUS_LLVMPIPE), icd_dirs=[tmp_path])
    assert c.state == "ok"
    assert "RADV" in c.detail and "llvmpipe" not in c.detail


def test_vulkan_problem_when_only_software(tmp_path: Path) -> None:
    c = sc.check_vulkan(runner(0, LLVMPIPE_ONLY), icd_dirs=[tmp_path])
    assert c.state == "problem"
    assert "llvmpipe" in c.detail
    assert c.fix


def test_vulkan_problem_when_lavapipe_has_no_type_line(tmp_path: Path) -> None:
    out = "Devices:\n========\nGPU0:\n\tdeviceName = lavapipe\n\tdeviceType = PHYSICAL_DEVICE_TYPE_CPU\n"
    assert sc.check_vulkan(runner(0, out), icd_dirs=[tmp_path]).state == "problem"


def test_vulkan_problem_on_driver_failure(tmp_path: Path) -> None:
    c = sc.check_vulkan(runner(1, "", NO_DRIVER_STDERR), icd_dirs=[tmp_path])
    assert c.state == "problem"
    assert c.title == "No Vulkan driver was found"
    assert c.fix


def test_vulkan_nonzero_without_driver_wording_is_unknown(tmp_path: Path) -> None:
    c = sc.check_vulkan(runner(3, REAL_SUMMARY, "Segmentation fault"), icd_dirs=[tmp_path])
    # A crash after printing a GPU still isn't a working Vulkan.
    assert c.state == "unknown"
    assert "3" in c.detail


def test_vulkan_unrecognised_output_is_unknown(tmp_path: Path) -> None:
    assert sc.check_vulkan(runner(0, "something else entirely\n"), icd_dirs=[tmp_path]).state == "unknown"
    assert sc.check_vulkan(runner(0, ""), icd_dirs=[tmp_path]).state == "unknown"


def test_vulkan_device_of_unknown_type_is_not_ok(tmp_path: Path) -> None:
    out = "Devices:\n========\nGPU0:\n\tdeviceType = PHYSICAL_DEVICE_TYPE_OTHER\n\tdeviceName = Mystery\n"
    assert sc.check_vulkan(runner(0, out), icd_dirs=[tmp_path]).state == "unknown"
    out = "Devices:\n========\nGPU0:\n\tdeviceName = Some GPU\n"
    assert sc.check_vulkan(runner(0, out), icd_dirs=[tmp_path]).state == "unknown"


def test_vulkan_timeout_is_unknown(tmp_path: Path) -> None:
    c = sc.check_vulkan(raising(subprocess.TimeoutExpired(["vulkaninfo"], 5)), icd_dirs=[tmp_path])
    assert c.state == "unknown"
    assert "5 seconds" in c.detail


def test_vulkan_other_oserror_is_unknown(tmp_path: Path) -> None:
    assert sc.check_vulkan(raising(PermissionError("denied")), icd_dirs=[tmp_path]).state == "unknown"


def test_vulkan_missing_tool_with_manifests_is_unknown(tmp_path: Path) -> None:
    icd = tmp_path / "share" / "vulkan" / "icd.d"
    write_manifest(icd, "radeon_icd.x86_64.json", "/usr/lib/libvulkan_radeon.so")
    c = sc.check_vulkan(raising(FileNotFoundError()), icd_dirs=[icd])
    assert c.state == "unknown"
    assert "vulkaninfo" in c.detail and "vulkan-tools" in c.detail


def test_vulkan_missing_tool_without_manifests_is_problem(tmp_path: Path) -> None:
    icd = tmp_path / "share" / "vulkan" / "icd.d"
    icd.parent.mkdir(parents=True)
    c = sc.check_vulkan(raising(FileNotFoundError()), icd_dirs=[icd, tmp_path / "etc" / "vulkan" / "icd.d"])
    assert c.state == "problem"
    assert c.title == "No Vulkan driver is installed"


def test_vulkan_missing_tool_and_folders_out_of_sight_is_unknown(tmp_path: Path) -> None:
    # A sandbox without host-os: /run/host/usr/share is not there at all.
    unseen = tmp_path / "run" / "host" / "usr" / "share" / "vulkan" / "icd.d"
    c = sc.check_vulkan(raising(FileNotFoundError()), icd_dirs=[unseen])
    assert c.state == "unknown"


def test_vulkan_missing_host_tool_inside_sandbox_falls_back(tmp_path: Path) -> None:
    icd = tmp_path / "share" / "vulkan" / "icd.d"
    write_manifest(icd, "intel_icd.json", "libvulkan_intel.so")
    stderr = 'Failed to start command: Failed to execute child process "vulkaninfo" (No such file or directory)'
    c = sc.check_vulkan(runner(1, "", stderr), icd_dirs=[icd])
    assert c.state == "unknown"
    assert "vulkan-tools" in c.detail
    assert sc.check_vulkan(runner(127), icd_dirs=[icd]).state == "unknown"


def test_default_icd_dirs_use_host_root_in_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "in_flatpak", lambda: True)
    dirs = [str(d) for d in sc.default_icd_dirs()]
    assert "/run/host/usr/share/vulkan/icd.d" in dirs
    assert "/run/host/etc/vulkan/icd.d" in dirs
    assert "/usr/share/vulkan/icd.d" not in dirs
    monkeypatch.setattr(sc, "in_flatpak", lambda: False)
    assert "/usr/share/vulkan/icd.d" in [str(d) for d in sc.default_icd_dirs()]


# --------------------------------------------------------------------------- #
# check_vulkan_32bit
# --------------------------------------------------------------------------- #

def test_elf_class(tmp_path: Path) -> None:
    assert sc.elf_class(write_elf(tmp_path / "a.so", 1)) == 32
    assert sc.elf_class(write_elf(tmp_path / "b.so", 2)) == 64
    assert sc.elf_class(write_elf(tmp_path / "c.so", 7)) is None
    (tmp_path / "d.so").write_bytes(b"not an elf")
    assert sc.elf_class(tmp_path / "d.so") is None
    assert sc.elf_class(tmp_path / "missing.so") is None


def test_32bit_flatpak_steam_is_unknown(tmp_path: Path) -> None:
    c = sc.check_vulkan_32bit("flatpak", icd_dirs=[tmp_path], lib_dirs=[tmp_path])
    assert c.id == "vulkan-32bit"
    assert c.state == "unknown"
    assert "Flatpak" in c.detail


def test_32bit_ok_with_bare_name_in_lib32(tmp_path: Path) -> None:
    icd, lib32, lib64 = tmp_path / "icd.d", tmp_path / "lib32", tmp_path / "lib"
    write_manifest(icd, "nvidia_icd.json", "libGLX_nvidia.so.0")
    write_elf(lib32 / "libGLX_nvidia.so.0", 1)
    write_elf(lib64 / "libGLX_nvidia.so.0", 2)
    c = sc.check_vulkan_32bit("native", icd_dirs=[icd], lib_dirs=[lib32], lib64_dirs=[lib64])
    assert c.state == "ok"
    assert "libGLX_nvidia.so.0" in c.detail


def test_32bit_ok_with_absolute_paths(tmp_path: Path) -> None:
    icd = tmp_path / "icd.d"
    lib64 = write_elf(tmp_path / "x86_64-linux-gnu" / "libvulkan_radeon.so", 2)
    lib32 = write_elf(tmp_path / "i386-linux-gnu" / "libvulkan_radeon.so", 1)
    write_manifest(icd, "radeon_icd.x86_64.json", str(lib64))
    write_manifest(icd, "radeon_icd.i686.json", str(lib32))
    assert sc.check_vulkan_32bit("native", icd_dirs=[icd], lib_dirs=[], lib64_dirs=[]).state == "ok"


def test_32bit_ok_with_path_relative_to_manifest(tmp_path: Path) -> None:
    icd = tmp_path / "icd.d"
    write_elf(tmp_path / "lib" / "libvk32.so", 1)
    write_manifest(icd, "vk.json", "../lib/libvk32.so")
    assert sc.check_vulkan_32bit("native", icd_dirs=[icd], lib_dirs=[], lib64_dirs=[]).state == "ok"


def test_32bit_problem_when_only_64bit(tmp_path: Path) -> None:
    icd, lib32, lib64 = tmp_path / "icd.d", tmp_path / "lib32", tmp_path / "lib"
    lib32.mkdir()
    write_manifest(icd, "intel_icd.json", "libvulkan_intel.so")
    write_elf(lib64 / "libvulkan_intel.so", 2)
    c = sc.check_vulkan_32bit("native", icd_dirs=[icd], lib_dirs=[lib32], lib64_dirs=[lib64])
    assert c.state == "problem"
    assert c.fix == (
        "Install the 32-bit Vulkan driver for your GPU from your distribution "
        "(often named lib32-... or ...:i386)."
    )
    for manager in ("pacman", "apt", "dnf", "zypper"):
        assert manager not in c.fix


def test_32bit_problem_with_absolute_64bit_path(tmp_path: Path) -> None:
    icd = tmp_path / "icd.d"
    write_manifest(icd, "radeon_icd.x86_64.json", str(write_elf(tmp_path / "libvulkan_radeon.so", 2)))
    assert sc.check_vulkan_32bit("unknown", icd_dirs=[icd], lib_dirs=[], lib64_dirs=[]).state == "problem"


def test_32bit_unknown_without_manifests(tmp_path: Path) -> None:
    c = sc.check_vulkan_32bit("native", icd_dirs=[tmp_path / "none"], lib_dirs=[tmp_path], lib64_dirs=[])
    assert c.state == "unknown"


def test_32bit_unknown_when_libraries_cannot_be_identified(tmp_path: Path) -> None:
    icd = tmp_path / "icd.d"
    write_manifest(icd, "a.json", "libnowhere.so")
    write_manifest(icd, "b.json", str(tmp_path / "missing.so"))
    (tmp_path / "not-elf.so").write_bytes(b"#!/bin/sh\n")
    write_manifest(icd, "c.json", str(tmp_path / "not-elf.so"))
    write_manifest(icd, "d.json", 42)
    (icd / "e.json").write_text("{ broken")
    (icd / "f.json").write_text('["not", "a", "manifest"]')
    c = sc.check_vulkan_32bit("native", icd_dirs=[icd], lib_dirs=[tmp_path], lib64_dirs=[])
    assert c.state == "unknown"


def test_default_lib_dirs_follow_layout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Fake the host root so the Fedora check looks at a tmp layout, not this machine.
    host = tmp_path / "host"
    monkeypatch.setattr(sc, "in_flatpak", lambda: True)
    monkeypatch.setattr(sc, "FLATPAK_HOST_ROOT", host)
    (host / "usr" / "lib").mkdir(parents=True)
    (host / "usr" / "lib64").symlink_to("lib")  # Arch
    assert host / "usr" / "lib" not in sc.default_lib32_dirs()
    (host / "usr" / "lib64").unlink()
    (host / "usr" / "lib64").mkdir()  # Fedora
    dirs = sc.default_lib32_dirs()
    assert host / "usr" / "lib" in dirs
    assert host / "usr" / "lib32" in dirs
    assert all(str(d).startswith(str(host)) for d in dirs + sc.default_lib64_dirs())


# --------------------------------------------------------------------------- #
# check_disk
# --------------------------------------------------------------------------- #

Usage = namedtuple("Usage", "total used free")


def test_disk_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc.shutil, "disk_usage", lambda *_a, **_kw: Usage(100 << 30, 50 << 30, 50 << 30))
    c = sc.check_disk(tmp_path, "library")
    assert (c.id, c.state, c.fix) == ("disk-library", "ok", "")
    assert "50.0 GiB" in c.detail


def test_disk_problem_reports_gib_and_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc.shutil, "disk_usage", lambda *_a, **_kw: Usage(100 << 30, 99 << 30, 400 << 20))
    c = sc.check_disk(tmp_path, "prefix")
    assert (c.id, c.state) == ("disk-prefix", "problem")
    assert "0.4 GiB" in c.detail
    assert str(tmp_path) in c.detail
    assert "Proton prefix" in c.detail
    assert c.fix


def test_disk_threshold_is_configurable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc.shutil, "disk_usage", lambda *_a, **_kw: Usage(10, 5, 5 << 30))
    assert sc.check_disk(tmp_path, "library", min_free_bytes=10 << 30).state == "problem"
    assert sc.check_disk(tmp_path, "library", min_free_bytes=5 << 30).state == "ok"


def test_disk_unknown(tmp_path: Path) -> None:
    assert sc.check_disk(None, "library").state == "unknown"
    c = sc.check_disk(tmp_path / "missing", "prefix")
    assert (c.id, c.state) == ("disk-prefix", "unknown")


def test_disk_real_tmp_path_does_not_raise(tmp_path: Path) -> None:
    assert sc.check_disk(tmp_path, "library", min_free_bytes=0).state == "ok"


# --------------------------------------------------------------------------- #
# run_checks
# --------------------------------------------------------------------------- #

def test_run_checks_order_and_shared_drive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "default_icd_dirs", lambda: [tmp_path / "icd.d"])
    install, prefix = tmp_path / "game", tmp_path / "pfx"
    install.mkdir()
    prefix.mkdir()
    checks = sc.run_checks(steam_root=None, install_path=install, prefix_path=prefix,
                           run=runner(0, REAL_SUMMARY))
    assert [c.id for c in checks] == ["vulkan", "vulkan-32bit", "disk-library"]


def test_run_checks_separate_drives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "default_icd_dirs", lambda: [tmp_path / "icd.d"])
    real_stat = os.stat
    install, prefix = tmp_path / "game", tmp_path / "pfx"
    install.mkdir()
    prefix.mkdir()
    devices = {install: 1, prefix: 2}

    class OtherDevice:
        """The real stat result, on another device; everything but ``st_dev`` is untouched."""

        def __init__(self, real: os.stat_result, dev: int) -> None:
            self._real, self.st_dev = real, dev

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    # sc.os is the os module itself, so anything else calling os.stat during
    # the test (pytest included, with follow_symlinks=) must get the real thing.
    def fake_stat(path: object, *args: object, **kwargs: object) -> object:
        real = real_stat(path, *args, **kwargs)
        try:
            dev = devices.get(Path(path))
        except TypeError:  # a file descriptor
            dev = None
        return real if dev is None else OtherDevice(real, dev)

    monkeypatch.setattr(sc.os, "stat", fake_stat)
    checks = sc.run_checks(steam_root=None, install_path=install, prefix_path=prefix,
                           run=runner(0, REAL_SUMMARY))
    assert [c.id for c in checks] == ["vulkan", "vulkan-32bit", "disk-library", "disk-prefix"]


def test_run_checks_missing_paths_never_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sc, "default_icd_dirs", lambda: [tmp_path / "icd.d"])
    checks = sc.run_checks(steam_root=None, install_path=None, prefix_path=tmp_path / "missing",
                           run=raising(FileNotFoundError()))
    assert [c.id for c in checks] == ["vulkan", "vulkan-32bit", "disk-library", "disk-prefix"]
    assert [c.state for c in checks[2:]] == ["unknown", "unknown"]


def test_text_has_no_long_dashes(tmp_path: Path) -> None:
    source = Path(sc.__file__).read_text(encoding="utf-8")
    assert chr(0x2014) not in source and chr(0x2013) not in source
