"""Regression tests for ``_vendor_compat.fixup_vendor_path``.

Goal: prove the read-only-AppImage scenario actually works. The previous
implementation tried to ``shutil.rmtree`` the offending vendor dir, which
silently no-op'd on squashfs. The current implementation must:

* Detect an ABI-mismatched vendored ``.so`` without writing to the FS.
* Prepend system site-packages to ``sys.path`` so the system copy wins
  import resolution.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

from game_setup_hub import _vendor_compat


@pytest.fixture
def vendor_dir(tmp_path: Path) -> Path:
    """Build a fake AppImage-style vendor dir with an ABI-incompatible .so."""
    vd = tmp_path / "vendor"
    vd.mkdir()
    pkg = vd / "pydantic_core"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    # Tag the .so with an obviously wrong SOABI so the compat check fails.
    (pkg / "_pydantic_core.cpython-999-totally-wrong.so").write_text("")
    return vd


@pytest.fixture
def system_site(tmp_path: Path) -> Path:
    sp = tmp_path / "system-site-packages"
    sp.mkdir()
    return sp


def test_no_vendor_dir_is_noop(monkeypatch) -> None:
    monkeypatch.setattr(sys, "path", ["/some/random/dir"])
    _vendor_compat.fixup_vendor_path()
    assert sys.path == ["/some/random/dir"]


def test_compatible_so_leaves_path_alone(tmp_path: Path, monkeypatch) -> None:
    vd = tmp_path / "vendor"
    vd.mkdir()
    pkg = vd / "pydantic_core"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    soabi = _vendor_compat._SOABI or "cpython-312-x86_64-linux-gnu"
    monkeypatch.setattr(_vendor_compat, "_SOABI", soabi)
    (pkg / f"_pydantic_core.{soabi}.so").write_text("")

    original = [str(vd), "/usr/lib/python3/dist-packages"]
    monkeypatch.setattr(sys, "path", list(original))
    _vendor_compat.fixup_vendor_path()
    assert sys.path == original, "compat .so must not trigger reordering"


def test_incompatible_so_prepends_system_site_packages(
    vendor_dir: Path, system_site: Path, monkeypatch
) -> None:
    monkeypatch.setattr(_vendor_compat, "_SOABI", "cpython-312-x86_64-linux-gnu")
    monkeypatch.setattr(sys, "path", [str(vendor_dir), "/usr/lib/python3.12"])
    monkeypatch.setattr(_vendor_compat, "_system_site_dirs", lambda: [str(system_site)])

    _vendor_compat.fixup_vendor_path()

    assert sys.path[0] == str(system_site), "system site-packages must win resolution"
    assert str(vendor_dir) in sys.path, "vendor dir stays for non-conflicting deps"


def test_does_not_touch_filesystem(vendor_dir: Path, system_site: Path, monkeypatch) -> None:
    """The whole point of the rewrite: never mutate the vendored dir."""
    monkeypatch.setattr(_vendor_compat, "_SOABI", "cpython-312-x86_64-linux-gnu")
    monkeypatch.setattr(sys, "path", [str(vendor_dir)])
    monkeypatch.setattr(_vendor_compat, "_system_site_dirs", lambda: [str(system_site)])

    pkg_dir = vendor_dir / "pydantic_core"
    files_before = sorted(p.name for p in pkg_dir.iterdir())

    with mock.patch("shutil.rmtree") as m_rmtree:
        _vendor_compat.fixup_vendor_path()

    assert m_rmtree.call_count == 0, "must not rmtree on read-only FS"
    files_after = sorted(p.name for p in pkg_dir.iterdir())
    assert files_before == files_after


def test_no_system_site_packages_is_warning_not_crash(
    vendor_dir: Path, monkeypatch, caplog
) -> None:
    """Worst case: AppImage on a system without pydantic — log loudly, don't crash."""
    monkeypatch.setattr(_vendor_compat, "_SOABI", "cpython-312-x86_64-linux-gnu")
    monkeypatch.setattr(sys, "path", [str(vendor_dir)])
    monkeypatch.setattr(_vendor_compat, "_system_site_dirs", lambda: [])

    with caplog.at_level("WARNING", logger="protonshift.vendor_compat"):
        _vendor_compat.fixup_vendor_path()

    assert any("ABI mismatch" in r.message for r in caplog.records)
