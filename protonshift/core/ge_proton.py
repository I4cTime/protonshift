"""GE-Proton manager — list, download, verify, install and remove Proton builds.

Everything lives in Steam's ``compatibilitytools.d``. Releases come from the
GitHub API for ``GloriousEggroll/proton-ge-custom``; the tarball is streamed to
a temp file *inside* the compat dir (same filesystem, so the final move is an
atomic ``rename``), checked against the published ``.sha512sum`` when one is
attached, extracted with the ``data`` tar filter, and only then moved into
place. ``remove_tool`` only ever ``rmtree``\\s a direct child of the compat dir
that is a recognised Proton tool — the resolved path must sit under the dir.

The two network touch points (``_get_json`` and ``_open_stream``) are tiny
module-level helpers so the test suite can monkeypatch them and stay offline.
stdlib only, no PySide6.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .compat_tool import get_config_vdf_path, read_compat_tool_mapping
from .paths import PathValidationError, validate_within
from .steam import (
    get_compattools_dir,
    get_steam_root,
    get_system_compattools_dirs,
    read_tool_manifest,
)

GITHUB_API = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases"
USER_AGENT = "ProtonShift/1.2"

_CHUNK = 256 * 1024
_TOOL_MARKERS = ("toolmanifest.vdf", "compatibilitytool.vdf")


class GeProtonError(RuntimeError):
    """Plain-English failure the UI can show verbatim."""


class GeProtonCancelled(GeProtonError):
    """The user cancelled an in-flight download."""


@dataclass(frozen=True)
class GeRelease:
    tag: str
    name: str
    published: str
    tarball_url: str
    sha512_url: str
    size: int


@dataclass(frozen=True)
class InstalledTool:
    name: str            # Steam's internal name (CompatToolMapping key)
    path: Path
    size_bytes: int
    is_ge: bool
    display_name: str = ""
    dir_name: str = ""
    location: str = "user"   # "user" (compatibilitytools.d) or "system" (distro package)
    removable: bool = True
    version: str = ""        # from the tool's ``version`` file, e.g. "GE-Proton11-7"


# --------------------------------------------------------------------------- #
# network helpers (monkeypatched in tests)
# --------------------------------------------------------------------------- #


def _request(url: str, accept: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})


def _network_error(exc: Exception) -> GeProtonError:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0":
            return GeProtonError("GitHub rate limit reached, try again in an hour")
        if exc.code == 404:
            return GeProtonError("GitHub returned 404 - the release asset is gone")
        return GeProtonError(f"GitHub returned HTTP {exc.code}")
    if isinstance(exc, urllib.error.URLError):
        return GeProtonError(f"Couldn't reach GitHub: {exc.reason}")
    if isinstance(exc, TimeoutError):
        return GeProtonError("Couldn't reach GitHub: timed out")
    return GeProtonError(f"Couldn't reach GitHub: {exc}")


def _get_json(url: str, timeout: float = 15) -> object:
    """GET ``url`` and decode the JSON body. Raises :class:`GeProtonError`."""
    try:
        with urllib.request.urlopen(_request(url, "application/vnd.github+json"), timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _network_error(exc) from exc
    try:
        return json.loads(body)
    except ValueError as exc:
        raise GeProtonError("Unexpected response from GitHub") from exc


def _open_stream(url: str, timeout: float = 30):
    """Open ``url`` for streaming. Returns ``(fileobj, total_bytes)``; total is -1 if unknown."""
    try:
        resp = urllib.request.urlopen(_request(url, "application/octet-stream"), timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _network_error(exc) from exc
    try:
        total = int(resp.headers.get("Content-Length") or -1)
    except ValueError:
        total = -1
    return resp, total


# --------------------------------------------------------------------------- #
# releases
# --------------------------------------------------------------------------- #


def _parse_release(item: dict) -> GeRelease | None:
    if not isinstance(item, dict) or item.get("draft"):
        return None
    tag = str(item.get("tag_name") or "")
    if not tag:
        return None
    tarball_url = ""
    sha_url = ""
    size = 0
    for asset in item.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name.endswith(".tar.gz") and not tarball_url:
            tarball_url = url
            try:
                size = int(asset.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
        elif name.endswith(".sha512sum") and not sha_url:
            sha_url = url
    if not tarball_url:
        return None
    return GeRelease(
        tag=tag,
        name=str(item.get("name") or tag),
        published=str(item.get("published_at") or ""),
        tarball_url=tarball_url,
        sha512_url=sha_url,
        size=size,
    )


def fetch_releases(limit: int = 15, timeout: float = 15) -> list[GeRelease]:
    """Latest GE-Proton releases that ship a ``.tar.gz`` asset, newest first."""
    data = _get_json(f"{GITHUB_API}?per_page={int(limit)}", timeout=timeout)
    if not isinstance(data, list):
        raise GeProtonError("Unexpected response from GitHub")
    releases: list[GeRelease] = []
    for item in data:
        rel = _parse_release(item)
        if rel is not None:
            releases.append(rel)
    return releases


# --------------------------------------------------------------------------- #
# installed tools
# --------------------------------------------------------------------------- #

_VERSION_RE = re.compile(r"\d+")


def parse_installed_version(name: str) -> tuple[int, ...]:
    """``GE-Proton9-27`` -> ``(9, 27)``; names without digits sort lowest."""
    return tuple(int(m) for m in _VERSION_RE.findall(name))


def is_ge_name(name: str) -> bool:
    low = name.lower()
    return low.startswith(("ge-proton", "proton-ge"))


def _is_tool_dir(path: Path) -> bool:
    if not path.is_dir() or path.name.startswith("."):
        return False
    if not (path / "proton").exists():
        return False
    return any((path / marker).exists() for marker in _TOOL_MARKERS)


def _tree_size(path: Path) -> int:
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def compattools_dir() -> Path | None:
    """Steam's existing ``compatibilitytools.d`` (None if it doesn't exist yet)."""
    return get_compattools_dir(get_steam_root())


def install_dir() -> Path:
    """Where new builds go: the existing compat dir, else ``<steam_root>/compatibilitytools.d``."""
    existing = compattools_dir()
    if existing is not None:
        return existing
    root = get_steam_root() or (Path.home() / ".steam" / "root")
    return root / "compatibilitytools.d"


def _read_version_file(tool_dir: Path) -> str:
    """GE tarballs ship ``version`` as ``<epoch> GE-Proton11-7``; return the tag."""
    try:
        text = (tool_dir / "version").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    parts = text.split()
    return parts[-1] if parts else ""


def _scan_dir(directory: Path, location: str, with_sizes: bool) -> list[InstalledTool]:
    try:
        children = list(directory.iterdir())
    except OSError:
        return []
    tools: list[InstalledTool] = []
    for child in children:
        if not _is_tool_dir(child):
            continue
        internal, display = read_tool_manifest(child)
        version = _read_version_file(child)
        tools.append(
            InstalledTool(
                name=internal,
                path=child,
                size_bytes=_tree_size(child) if with_sizes else 0,
                is_ge=is_ge_name(internal) or is_ge_name(child.name) or is_ge_name(version),
                display_name=display,
                dir_name=child.name,
                location=location,
                removable=location == "user",
                version=version,
            )
        )
    return tools


def list_installed(with_sizes: bool = True) -> list[InstalledTool]:
    """Proton tools Steam can see: the user's ``compatibilitytools.d`` plus the
    system-wide directories distro packages install into. Newest version first.
    """
    tools: list[InstalledTool] = []
    seen: set[str] = set()
    compat = compattools_dir()
    dirs: list[tuple[Path, str]] = []
    if compat is not None and compat.is_dir():
        dirs.append((compat, "user"))
    dirs.extend((d, "system") for d in get_system_compattools_dirs())
    for directory, location in dirs:
        for tool in _scan_dir(directory, location, with_sizes):
            if tool.name in seen:
                continue  # user copy shadows a system one, like Steam does
            seen.add(tool.name)
            tools.append(tool)
    tools.sort(
        key=lambda t: (parse_installed_version(t.version or t.name), t.name.lower()),
        reverse=True,
    )
    return tools


# --------------------------------------------------------------------------- #
# install
# --------------------------------------------------------------------------- #


def _read_expected_sha512(url: str) -> str:
    stream, _total = _open_stream(url)
    try:
        text = stream.read(4096)
    finally:
        close = getattr(stream, "close", None)
        if close:
            close()
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    token = text.strip().split()
    return token[0].lower() if token else ""


def _extract(tarball: Path, dest: Path) -> None:
    with tarfile.open(tarball, "r:gz") as tar:
        try:
            tar.extractall(dest, filter="data")
        except TypeError:  # Python < 3.12: no ``filter`` kwarg
            tar.extractall(dest)


def download_and_install(
    release: GeRelease,
    progress: Callable[[int, int], None] | None = None,
    cancel: Callable[[], bool] | None = None,
    dest_dir: Path | None = None,
) -> Path:
    """Download, verify, extract and move ``release`` into ``compatibilitytools.d``.

    Returns the installed tool's directory. Raises :class:`GeProtonError` on
    any failure (checksum mismatch, malformed archive, already installed) and
    :class:`GeProtonCancelled` if ``cancel()`` returns True mid-download.
    Nothing is left behind on failure.
    """
    target_dir = dest_dir if dest_dir is not None else install_dir()
    if (target_dir / release.tag).exists():
        raise GeProtonError(f"{release.tag} is already installed")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GeProtonError(f"Couldn't create {target_dir}: {exc}") from exc

    fd, tmp_name = tempfile.mkstemp(prefix=".ge-download-", suffix=".tar.gz", dir=str(target_dir))
    tarball = Path(tmp_name)
    extract_dir: Path | None = None
    try:
        digest = hashlib.sha512()
        stream, total = _open_stream(release.tarball_url)
        if total < 0:
            total = release.size
        downloaded = 0
        try:
            with os.fdopen(fd, "wb") as out:
                fd = -1
                while True:
                    if cancel is not None and cancel():
                        raise GeProtonCancelled("Download cancelled")
                    chunk = stream.read(_CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(downloaded, total)
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()

        if release.sha512_url:
            expected = _read_expected_sha512(release.sha512_url)
            if expected and expected != digest.hexdigest():
                raise GeProtonError(f"Checksum mismatch for {release.tag} - download discarded")

        extract_dir = Path(tempfile.mkdtemp(prefix=".ge-extract-", dir=str(target_dir)))
        try:
            _extract(tarball, extract_dir)
        except (tarfile.TarError, OSError, ValueError) as exc:
            raise GeProtonError(f"Couldn't extract {release.tag}: {exc}") from exc

        entries = [p for p in extract_dir.iterdir()]
        if len(entries) != 1 or not entries[0].is_dir():
            raise GeProtonError(f"Unexpected archive layout for {release.tag}")
        top = entries[0]
        if not (top / "proton").exists():
            raise GeProtonError(f"{release.tag} archive doesn't contain a Proton tool")
        final = target_dir / top.name
        if final.exists():
            raise GeProtonError(f"{top.name} is already installed")
        os.rename(top, final)
        return final
    finally:
        if fd != -1:
            os.close(fd)
        tarball.unlink(missing_ok=True)
        if extract_dir is not None:
            shutil.rmtree(extract_dir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# remove / usage
# --------------------------------------------------------------------------- #


def remove_tool(name: str) -> None:
    """Delete an installed tool. Only direct, recognised children of the compat dir."""
    compat = compattools_dir()
    if compat is None:
        raise GeProtonError("compatibilitytools.d doesn't exist")
    if not name or "/" in name or "\x00" in name or name in (".", ".."):
        raise GeProtonError("Invalid tool name")
    installed = {t.name: t for t in list_installed(with_sizes=False)}
    tool = installed.get(name)
    if tool is None:
        raise GeProtonError(f"{name} isn't an installed Proton tool")
    if not tool.removable:
        raise GeProtonError(f"{name} was installed by your package manager - remove it there")
    candidate = compat / tool.dir_name
    try:
        resolved = validate_within(compat, candidate)
    except PathValidationError as exc:
        raise GeProtonError("Refusing to delete outside compatibilitytools.d") from exc
    if resolved.parent != compat.resolve(strict=False) or candidate.is_symlink():
        raise GeProtonError("Refusing to delete outside compatibilitytools.d")
    try:
        shutil.rmtree(resolved)
    except OSError as exc:
        raise GeProtonError(f"Couldn't remove {name}: {exc}") from exc


def tool_usage(games, steam_root: Path | None = None) -> dict[str, list[str]]:
    """Map ``tool_name -> [game names]`` from Steam's per-game CompatToolMapping."""
    root = steam_root if steam_root is not None else get_steam_root()
    if root is None:
        return {}
    mapping = read_compat_tool_mapping(get_config_vdf_path(root))
    usage: dict[str, list[str]] = {}
    for game in games:
        tool = mapping.get(str(game.app_id), "")
        if tool:
            usage.setdefault(tool, []).append(game.name)
    return usage


def is_in_use(name: str, games, steam_root: Path | None = None) -> list[str]:
    """Names of ``games`` whose Steam compat tool is ``name``."""
    return list(tool_usage(games, steam_root).get(name, []))
