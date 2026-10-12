"""The release version must agree everywhere it is written by hand.

pyproject.toml, ``protonshift.__version__``, the newest released CHANGELOG
section and the newest AppStream ``<release>`` are bumped separately for each
release; this catches one being missed. Qt-free.
"""

from __future__ import annotations

import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import protonshift

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _changelog_version() -> str:
    # first "## [X.Y.Z] - date" heading; "## [Unreleased]" is skipped
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    assert m, "CHANGELOG.md has no released version heading"
    return m.group(1)


def _metainfo_version() -> str:
    tree = ET.parse(ROOT / "flatpak" / "io.github.i4ctime.protonshift.metainfo.xml")
    release = tree.getroot().find("releases/release")
    assert release is not None, "metainfo.xml has no <release> entry"
    return release.get("version", "")


def test_package_version_matches_pyproject() -> None:
    assert protonshift.__version__ == _pyproject_version()


def test_changelog_matches_pyproject() -> None:
    assert _changelog_version() == _pyproject_version()


def test_metainfo_matches_pyproject() -> None:
    assert _metainfo_version() == _pyproject_version()
