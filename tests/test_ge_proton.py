"""GE-Proton manager tests — offline, Qt-free, everything under tmp_path.

Network is stubbed at the two module seams (``_get_json`` / ``_open_stream``);
the compat dir comes from a monkeypatched ``get_compattools_dir`` so the real
``~/.steam`` is never touched.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.error
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

from protonshift.core import ge_proton
from protonshift.core.ge_proton import (
    GeProtonCancelled,
    GeProtonError,
    GeRelease,
    download_and_install,
    fetch_releases,
    is_in_use,
    list_installed,
    parse_installed_version,
    remove_tool,
)

# --------------------------------------------------------------------------- #
# helpers / fixtures
# --------------------------------------------------------------------------- #


def _release_json(tag: str, *, sha: bool = True, draft: bool = False) -> dict:
    assets = [
        {"name": f"{tag}.tar.gz", "browser_download_url": f"https://x/{tag}.tar.gz", "size": 1234},
        {"name": f"{tag}.txt", "browser_download_url": f"https://x/{tag}.txt", "size": 10},
    ]
    if sha:
        assets.insert(0, {"name": f"{tag}.sha512sum", "browser_download_url": f"https://x/{tag}.sha512sum"})
    return {
        "tag_name": tag,
        "name": tag,
        "draft": draft,
        "published_at": "2025-03-01T10:00:00Z",
        "assets": assets,
    }


@pytest.fixture(autouse=True)
def _no_system_dirs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the machine's /usr/share/steam tools out of every existing test."""
    monkeypatch.setattr(ge_proton, "get_system_compattools_dirs", list)


@pytest.fixture
def compat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "compatibilitytools.d"
    d.mkdir()
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: d)
    monkeypatch.setattr(ge_proton, "get_steam_root", lambda: tmp_path)
    return d


def _make_tool(compat: Path, name: str, size: int = 10) -> Path:
    tool = compat / name
    (tool / "files").mkdir(parents=True)
    (tool / "proton").write_bytes(b"#!/usr/bin/env python\n")
    (tool / "toolmanifest.vdf").write_text('"manifest" {}')
    (tool / "files" / "blob").write_bytes(b"x" * size)
    return tool


def _build_tarball(top: str | None, *, with_proton: bool = True, extra_top: bool = False) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        prefix = f"{top}/" if top else ""
        if with_proton:
            add(f"{prefix}proton", b"#!/usr/bin/env python\n")
        add(f"{prefix}toolmanifest.vdf", b'"manifest" {}')
        add(f"{prefix}files/blob", b"y" * 100)
        if extra_top:
            add("stray.txt", b"nope")
    return buf.getvalue()


class _Stub:
    """Serves ``urls`` (bytes) through ``_open_stream``; records reads."""

    def __init__(self, urls: dict[str, bytes]) -> None:
        self.urls = urls
        self.opened: list[str] = []

    def __call__(self, url: str, timeout: float = 30):
        self.opened.append(url)
        if url not in self.urls:
            raise GeProtonError("GitHub returned 404 — the release asset is gone")
        data = self.urls[url]
        return io.BytesIO(data), len(data)


def _release(tag: str = "GE-Proton9-27", sha: bool = True) -> GeRelease:
    return GeRelease(
        tag=tag,
        name=tag,
        published="2025-03-01T10:00:00Z",
        tarball_url=f"https://x/{tag}.tar.gz",
        sha512_url=f"https://x/{tag}.sha512sum" if sha else "",
        size=0,
    )


# --------------------------------------------------------------------------- #
# fetch_releases
# --------------------------------------------------------------------------- #


def test_fetch_releases_parses_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [_release_json("GE-Proton9-27"), _release_json("GE-Proton9-26", sha=False)]
    seen: list[str] = []

    def fake_get(url: str, timeout: float = 15) -> object:
        seen.append(url)
        return payload

    monkeypatch.setattr(ge_proton, "_get_json", fake_get)
    rels = fetch_releases(limit=2)
    assert seen == [f"{ge_proton.GITHUB_API}?per_page=2"]
    assert [r.tag for r in rels] == ["GE-Proton9-27", "GE-Proton9-26"]
    assert rels[0].tarball_url == "https://x/GE-Proton9-27.tar.gz"
    assert rels[0].sha512_url == "https://x/GE-Proton9-27.sha512sum"
    assert rels[0].size == 1234
    assert rels[0].published == "2025-03-01T10:00:00Z"
    # missing .sha512sum asset is tolerated
    assert rels[1].sha512_url == ""


def test_fetch_releases_skips_drafts_and_tarball_less(monkeypatch: pytest.MonkeyPatch) -> None:
    no_tar = _release_json("GE-Proton9-25")
    no_tar["assets"] = [a for a in no_tar["assets"] if not a["name"].endswith(".tar.gz")]
    payload = [_release_json("GE-Proton9-27", draft=True), no_tar, _release_json("GE-Proton9-24")]
    monkeypatch.setattr(ge_proton, "_get_json", lambda *_a, **_k: payload)
    assert [r.tag for r in fetch_releases()] == ["GE-Proton9-24"]


def test_fetch_releases_rejects_non_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ge_proton, "_get_json", lambda *_a, **_k: {"message": "nope"})
    with pytest.raises(GeProtonError):
        fetch_releases()


def test_rate_limit_message(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"

    def boom(*_a, **_k):
        raise urllib.error.HTTPError("https://x", 403, "Forbidden", headers, None)

    monkeypatch.setattr(ge_proton.urllib.request, "urlopen", boom)
    with pytest.raises(GeProtonError, match="rate limit reached"):
        ge_proton._get_json(ge_proton.GITHUB_API)


def test_network_failure_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a, **_k):
        raise urllib.error.URLError("Name or service not known")

    monkeypatch.setattr(ge_proton.urllib.request, "urlopen", boom)
    with pytest.raises(GeProtonError, match="Couldn't reach GitHub"):
        fetch_releases()


# --------------------------------------------------------------------------- #
# list_installed / version parsing
# --------------------------------------------------------------------------- #


def test_list_installed_detects_tools(compat: Path) -> None:
    _make_tool(compat, "GE-Proton9-5", size=50)
    _make_tool(compat, "GE-Proton9-27", size=70)
    _make_tool(compat, "proton-ge-custom", size=5)
    _make_tool(compat, "Proton-Sarek", size=9)
    (compat / "not-a-tool").mkdir()
    (compat / "not-a-tool" / "readme").write_text("x")
    (compat / ".hidden").mkdir()
    (compat / ".hidden" / "proton").write_text("x")
    (compat / ".hidden" / "toolmanifest.vdf").write_text("x")
    (compat / "loose-file").write_text("x")

    tools = list_installed()
    names = [t.name for t in tools]
    assert names == ["GE-Proton9-27", "GE-Proton9-5", "Proton-Sarek", "proton-ge-custom"]
    by_name = {t.name: t for t in tools}
    assert by_name["GE-Proton9-27"].is_ge
    assert by_name["proton-ge-custom"].is_ge
    assert not by_name["Proton-Sarek"].is_ge
    # size: proton script (22) + manifest (13) + blob
    assert by_name["GE-Proton9-27"].size_bytes == 22 + 13 + 70
    assert by_name["GE-Proton9-27"].path == compat / "GE-Proton9-27"


def test_list_installed_missing_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: None)
    monkeypatch.setattr(ge_proton, "get_steam_root", lambda: None)
    assert list_installed() == []


def test_parse_installed_version_sorting() -> None:
    assert parse_installed_version("GE-Proton9-27") == (9, 27)
    assert parse_installed_version("GE-Proton10-1") == (10, 1)
    assert parse_installed_version("proton-ge-custom") == ()
    assert parse_installed_version("GE-Proton9-27") > parse_installed_version("GE-Proton9-5")
    assert parse_installed_version("GE-Proton10-1") > parse_installed_version("GE-Proton9-27")
    names = ["GE-Proton9-5", "GE-Proton10-1", "GE-Proton9-27"]
    assert sorted(names, key=parse_installed_version, reverse=True) == [
        "GE-Proton10-1", "GE-Proton9-27", "GE-Proton9-5",
    ]


# --------------------------------------------------------------------------- #
# download_and_install
# --------------------------------------------------------------------------- #


def test_install_end_to_end_with_sha(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-27"
    tarball = _build_tarball(tag)
    sha = hashlib.sha512(tarball).hexdigest()
    stub = _Stub({
        f"https://x/{tag}.tar.gz": tarball,
        f"https://x/{tag}.sha512sum": f"{sha}  {tag}.tar.gz\n".encode(),
    })
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    monkeypatch.setattr(ge_proton, "_CHUNK", 64)
    progress: list[tuple[int, int]] = []

    path = download_and_install(_release(tag), progress=lambda d, t: progress.append((d, t)))

    assert path == compat / tag
    assert (path / "proton").exists()
    assert (path / "files" / "blob").read_bytes() == b"y" * 100
    assert progress, "progress callback never fired"
    assert progress[-1] == (len(tarball), len(tarball))
    assert all(t == len(tarball) for _d, t in progress)
    # no temp files left behind
    assert sorted(p.name for p in compat.iterdir()) == [tag]
    assert [t.name for t in list_installed()] == [tag]


def test_install_without_sha_asset(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-26"
    stub = _Stub({f"https://x/{tag}.tar.gz": _build_tarball(tag)})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    path = download_and_install(_release(tag, sha=False))
    assert path == compat / tag
    assert stub.opened == [f"https://x/{tag}.tar.gz"]


def test_install_sha_mismatch_cleans_up(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-27"
    stub = _Stub({
        f"https://x/{tag}.tar.gz": _build_tarball(tag),
        f"https://x/{tag}.sha512sum": b"deadbeef  x.tar.gz\n",
    })
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    with pytest.raises(GeProtonError, match="Checksum mismatch"):
        download_and_install(_release(tag))
    assert list(compat.iterdir()) == []


def test_install_refuses_already_installed(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-27"
    _make_tool(compat, tag)
    stub = _Stub({f"https://x/{tag}.tar.gz": _build_tarball(tag)})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    with pytest.raises(GeProtonError, match="already installed"):
        download_and_install(_release(tag, sha=False))
    assert stub.opened == []  # refused before downloading a byte
    assert (compat / tag / "files" / "blob").read_bytes() == b"x" * 10  # untouched


def test_install_refuses_when_archive_dir_collides(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # tag differs from the archive's top-level dir, which is already present
    _make_tool(compat, "GE-Proton9-27")
    stub = _Stub({"https://x/GE-Proton9-27-hotfix.tar.gz": _build_tarball("GE-Proton9-27")})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    with pytest.raises(GeProtonError, match="already installed"):
        download_and_install(_release("GE-Proton9-27-hotfix", sha=False))
    assert sorted(p.name for p in compat.iterdir()) == ["GE-Proton9-27"]


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"top": None}, "Unexpected archive layout"),
        ({"top": "GE-Proton9-27", "extra_top": True}, "Unexpected archive layout"),
        ({"top": "GE-Proton9-27", "with_proton": False}, "doesn't contain a Proton tool"),
    ],
)
def test_install_enforces_single_top_level_dir(
    compat: Path, monkeypatch: pytest.MonkeyPatch, kwargs: dict, match: str
) -> None:
    tag = "GE-Proton9-27"
    stub = _Stub({f"https://x/{tag}.tar.gz": _build_tarball(**kwargs)})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    with pytest.raises(GeProtonError, match=match):
        download_and_install(_release(tag, sha=False))
    assert list(compat.iterdir()) == []


def test_install_rejects_garbage_archive(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-27"
    stub = _Stub({f"https://x/{tag}.tar.gz": b"this is not a tarball"})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    with pytest.raises(GeProtonError, match="Couldn't extract"):
        download_and_install(_release(tag, sha=False))
    assert list(compat.iterdir()) == []


def test_install_cancel_mid_download(compat: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tag = "GE-Proton9-27"
    stub = _Stub({f"https://x/{tag}.tar.gz": _build_tarball(tag)})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    monkeypatch.setattr(ge_proton, "_CHUNK", 32)
    calls = {"n": 0}

    def cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(GeProtonCancelled):
        download_and_install(_release(tag, sha=False), cancel=cancel)
    assert list(compat.iterdir()) == []


def test_install_creates_missing_compat_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: None)
    monkeypatch.setattr(ge_proton, "get_steam_root", lambda: tmp_path / "steam")
    tag = "GE-Proton9-27"
    stub = _Stub({f"https://x/{tag}.tar.gz": _build_tarball(tag)})
    monkeypatch.setattr(ge_proton, "_open_stream", stub)
    path = download_and_install(_release(tag, sha=False))
    assert path == tmp_path / "steam" / "compatibilitytools.d" / tag
    assert (path / "proton").exists()


# --------------------------------------------------------------------------- #
# remove_tool
# --------------------------------------------------------------------------- #


def test_remove_tool_deletes_installed(compat: Path) -> None:
    _make_tool(compat, "GE-Proton9-27")
    _make_tool(compat, "GE-Proton9-5")
    remove_tool("GE-Proton9-27")
    assert sorted(p.name for p in compat.iterdir()) == ["GE-Proton9-5"]


@pytest.mark.parametrize("bad", ["..", "../victim", "/tmp", "", ".", "GE-Proton9-27/files", "victim"])
def test_remove_tool_traversal_guard(compat: Path, tmp_path: Path, bad: str) -> None:
    victim = tmp_path / "victim"
    _make_tool(tmp_path, "victim")  # a *valid-looking* tool outside the compat dir
    _make_tool(compat, "GE-Proton9-27")
    with pytest.raises(GeProtonError):
        remove_tool(bad)
    assert victim.exists()
    assert (compat / "GE-Proton9-27").exists()
    assert tmp_path.exists()


def test_remove_tool_refuses_symlinked_entry(compat: Path, tmp_path: Path) -> None:
    victim = _make_tool(tmp_path, "victim")
    (compat / "GE-Proton9-27").symlink_to(victim, target_is_directory=True)
    with pytest.raises(GeProtonError):
        remove_tool("GE-Proton9-27")
    assert (victim / "proton").exists()


def test_remove_tool_without_compat_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: None)
    monkeypatch.setattr(ge_proton, "get_steam_root", lambda: None)
    with pytest.raises(GeProtonError):
        remove_tool("GE-Proton9-27")


# --------------------------------------------------------------------------- #
# is_in_use
# --------------------------------------------------------------------------- #


def _write_config_vdf(root: Path, mapping: dict[str, str]) -> None:
    entries = "".join(
        f'\t\t\t\t\t"{app}"\n\t\t\t\t\t{{\n\t\t\t\t\t\t"name"\t\t"{tool}"\n'
        f'\t\t\t\t\t\t"config"\t\t""\n\t\t\t\t\t\t"priority"\t\t"250"\n\t\t\t\t\t}}\n'
        for app, tool in mapping.items()
    )
    text = (
        '"InstallConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n'
        '\t\t\t\t"CompatToolMapping"\n\t\t\t\t{\n' + entries + "\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n"
    )
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "config.vdf").write_text(text)


def test_is_in_use(tmp_path: Path) -> None:
    root = tmp_path / "steam"
    _write_config_vdf(root, {"10": "GE-Proton9-27", "20": "proton_experimental", "30": "GE-Proton9-27"})
    games = [
        SimpleNamespace(app_id="10", name="Alpha"),
        SimpleNamespace(app_id="20", name="Beta"),
        SimpleNamespace(app_id="30", name="Gamma"),
        SimpleNamespace(app_id="40", name="Delta"),
    ]
    assert is_in_use("GE-Proton9-27", games, root) == ["Alpha", "Gamma"]
    assert is_in_use("proton_experimental", games, root) == ["Beta"]
    assert is_in_use("GE-Proton9-5", games, root) == []
    assert ge_proton.tool_usage(games, root) == {
        "GE-Proton9-27": ["Alpha", "Gamma"],
        "proton_experimental": ["Beta"],
    }


def test_is_in_use_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    games = [SimpleNamespace(app_id="10", name="Alpha")]
    assert is_in_use("GE-Proton9-27", games, tmp_path) == []
    monkeypatch.setattr(ge_proton, "get_steam_root", lambda: None)
    assert is_in_use("GE-Proton9-27", games) == []


# --------------------------------------------------------------------------- #
# system-wide tools (distro packages) + manifest names
# --------------------------------------------------------------------------- #

_MANIFEST = """"compatibilitytools"
{
  "compat_tools"
  {
    "Proton-GE"
    {
      "install_path" "."
      "display_name" "Proton-GE (Arch)"
      "from_oslist"  "windows"
      "to_oslist"    "linux"
    }
  }
}
"""


def _make_sys_tool(root, dir_name: str, manifest: str | None = None, version: str = "") -> None:
    d = root / dir_name
    d.mkdir(parents=True)
    (d / "proton").write_text("#!/bin/sh\n")
    (d / "toolmanifest.vdf").write_text('"manifest" { "version" "2" }\n')
    if manifest is not None:
        (d / "compatibilitytool.vdf").write_text(manifest)
    if version:
        (d / "version").write_text(f"1789520217 {version}\n")


def test_system_tools_listed_read_only(tmp_path, monkeypatch):
    user = tmp_path / "user"
    user.mkdir()
    system = tmp_path / "usr-share"
    _make_sys_tool(user, "GE-Proton9-27", version="GE-Proton9-27")
    _make_sys_tool(system, "proton-ge-custom", _MANIFEST, version="GE-Proton11-7")
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: user)
    monkeypatch.setattr(ge_proton, "get_system_compattools_dirs", lambda: [system])

    tools = ge_proton.list_installed(with_sizes=False)
    assert [t.name for t in tools] == ["Proton-GE", "GE-Proton9-27"]  # newest version first
    sys_tool = tools[0]
    assert sys_tool.location == "system" and not sys_tool.removable
    assert sys_tool.dir_name == "proton-ge-custom"
    assert sys_tool.display_name == "Proton-GE (Arch)"
    assert sys_tool.version == "GE-Proton11-7" and sys_tool.is_ge
    assert tools[1].location == "user" and tools[1].removable

    with pytest.raises(ge_proton.GeProtonError, match="package manager"):
        ge_proton.remove_tool("Proton-GE")
    assert (system / "proton-ge-custom").is_dir()


def test_user_copy_shadows_system_copy(tmp_path, monkeypatch):
    user = tmp_path / "user"
    system = tmp_path / "sys"
    _make_sys_tool(user, "GE-Proton11-7", version="GE-Proton11-7")
    _make_sys_tool(system, "GE-Proton11-7", version="GE-Proton11-7")
    monkeypatch.setattr(ge_proton, "get_compattools_dir", lambda *_a: user)
    monkeypatch.setattr(ge_proton, "get_system_compattools_dirs", lambda: [system])
    tools = ge_proton.list_installed(with_sizes=False)
    assert len(tools) == 1 and tools[0].location == "user"


def test_available_tools_use_internal_names(tmp_path, monkeypatch):
    from protonshift.core import steam

    user = tmp_path / "user"
    system = tmp_path / "sys"
    _make_sys_tool(user, "GE-Proton9-27")
    _make_sys_tool(system, "proton-ge-custom", _MANIFEST)
    monkeypatch.setattr(steam, "get_compattools_dir", lambda *_a: user)
    monkeypatch.setattr(steam, "get_system_compattools_dirs", lambda: [system])
    tools = steam.get_available_proton_tools(None)
    assert "GE-Proton9-27" in tools and "Proton-GE" in tools
    assert "proton-ge-custom" not in tools


def test_read_tool_manifest_fallback(tmp_path):
    from protonshift.core.steam import read_tool_manifest

    d = tmp_path / "MyTool"
    d.mkdir()
    assert read_tool_manifest(d) == ("MyTool", "MyTool")
    (d / "compatibilitytool.vdf").write_text("not vdf at all {{{")
    assert read_tool_manifest(d) == ("MyTool", "MyTool")
