# Python Backend Review — ProtonShift

Scope: everything under `src/game_setup_hub/` (the FastAPI backend that Electron
spawns), plus the packaging glue in `electron/main.ts` and
`electron/scripts/vendor-python-deps.sh` that wires it up.

- Total Python LoC (backend): **~4,647** across 22 modules
- Tests: **0**
- Linters/typers configured: `ruff`, `pyright` (standard mode, `app.py` excluded)
- Python floor: `>=3.12` (`pyproject.toml`)

Findings are grouped by severity. Each has a concrete fix sketch. Ordering
inside each group roughly reflects impact.

---

## P0 — Fix before next release

### P0-1. Vendored native extensions fundamentally incompatible with AppImage — **PARTIALLY FIXED in v0.9.0**

**Status (2026-04-16):** the read-only-FS bug and the `PYTHONNOUSERSITE`
inversion are both fixed. The maintenance burden of vendoring `pydantic_core`
remains until we adopt option B (`python-build-standalone`).

What landed (see PR linked in the changelog):

- `_vendor_compat.py` was rewritten to **mutate `sys.path` instead of the
  filesystem**. When the vendored `pydantic_core/*.so` does not match the
  runtime SOABI, the system + user site-packages are prepended to `sys.path`
  so the system copy of pydantic_core is found first. The vendor dir stays
  on `sys.path` for the rest of our pure-Python deps. Works on read-only
  squashfs (AppImage) because no FS writes happen.
- `_NATIVE_PACKAGES` reduced from 5 entries to the only one that's actually
  vendored (`pydantic_core`). `yaml`, `uvloop`, `httptools`, `watchfiles`
  were never declared deps.
- `electron/main.ts` no longer sets `PYTHONNOUSERSITE = ""` (which CPython
  reads as truthy and used to *disable* user site-packages, the opposite of
  what we wanted). It now `delete`s the var so the system fallback is real.
- `python-runtime-requirements.txt` and `pyproject.toml` switched
  `uvicorn[standard]` → bare `uvicorn`. That kills 3 of the 4 vendored
  native extensions (uvloop, httptools, watchfiles). The localhost-only
  GUI workload doesn't need the perf.
- New `tests/test_vendor_compat.py` covers: no-op when there's no vendor
  dir, no-op when the `.so` is compatible, sys.path reordering when it
  isn't, no `shutil.rmtree` is ever called, and a graceful warning when
  no system fallback is available.

**Net result.** Bundle size of the vendor dir drops to one native package
(`pydantic_core`). AppImage users on a system Python whose minor version
matches the build → unaffected. AppImage users on a *different* minor →
silently fall back to system pydantic_core if installed (Debian/Fedora/Arch
all ship one); otherwise get a loud, actionable warning telling them to
install it. No more silent `ModuleNotFoundError` from a no-op `rmtree`.

**Still pending — option B.** Bundle our own Python via
`python-build-standalone` to remove the system-pydantic dependency entirely.
Tracked separately; not in this PR.

---

#### Original problem description (kept for archival reference)

The current v0.8.11 fix (`_vendor_compat.py`) tries to detect ABI-mismatched
`.so` files at import time and `shutil.rmtree` them so Python falls back to
system packages.

Why it does not work:

1. AppImages are **read-only squashfs**. `shutil.rmtree(pkg_dir, ignore_errors=True)`
   silently fails on write-protected filesystems, leaving the incompatible
   `pydantic_core/_pydantic_core.cpython-312-*.so` on `sys.path`. The user
   still gets `ModuleNotFoundError` — the "fix" is a no-op.
2. Even on writable targets (`.deb`, `.rpm`), mutating the install dir at
   runtime is hostile to packagers and fails the second time after an
   SELinux/AppArmor denial.
3. The module fixes `sys.path` by deleting files, but `sys.path` itself is
   unchanged. On the second process start, the vendor dir is still first.

Also wrong nearby:

- `electron/main.ts` sets `env.PYTHONNOUSERSITE = ""`. In CPython, the var
  being **present at all** (non-empty or empty) is truthy: it *disables* user
  site-packages. The intent was the opposite. Unset it with
  `delete env.PYTHONNOUSERSITE` or do not touch it.
- `_NATIVE_PACKAGES` in `_vendor_compat.py` lists `yaml` (PyYAML), `uvloop`,
  `httptools`, `watchfiles` — none of which are actually declared
  dependencies. `pydantic_core` is the only real target today.
- The `.deb`/`.rpm` `python3-pydantic` dependency added for this issue only
  helps Debian/Fedora-family native packages; CachyOS (Arch, where #13 was
  reported) and AppImage users on any distro still break.

**Recommended fix — pick one, in priority order**

A. **Stop vendoring native wheels; replace with a pure-Python stack.**
   - Drop `pydantic`. The API layer only uses `BaseModel` for request/response
     shaping. Replace with `msgspec` (ships as a single pure-Python wheel +
     optional C speedups) **or** hand-rolled `dataclasses` + `fastapi.Body`
     with manual parsing — FastAPI does not require Pydantic for routing
     when you type parameters as primitives/dicts.
   - Drop `uvicorn[standard]` (pulls uvloop, httptools, watchfiles) in favor
     of `uvicorn` (pure-Python asyncio + h11). The performance delta is
     irrelevant on localhost with a GUI frontend.
   - Result: vendor dir has **zero** `.so` files, AppImage works on any
     Python ≥3.12.

B. **Ship our own Python interpreter in the AppImage.**
   Use `python-build-standalone` (Astral publishes portable 3.12 builds).
   The AppImage becomes ~40 MB bigger but is entirely self-contained.
   Build-script change only; no runtime tricks.

C. **Build manylinux wheels per CPython minor version and pick at runtime.**
   Vendor `pydantic_core-cp312-*.so`, `pydantic_core-cp313-*.so`, etc., and
   resolve at import time (small sitecustomize shim). Maintenance cost grows
   linearly with CPython versions.

I recommend **A** as the short-term fix and revisit **B** when we add other
native deps. Delete `_vendor_compat.py` entirely once A lands.

Also in `electron/main.ts`:

```typescript
// Unset, don't set to empty string — empty is still "present"
delete env.PYTHONNOUSERSITE;
```

Files: `src/game_setup_hub/_vendor_compat.py`, `src/game_setup_hub/api.py:5`,
`electron/main.ts:73`, `electron/python-runtime-requirements.txt`,
`pyproject.toml:11-15`.

---

### P0-2. Version drift across three places

- `pyproject.toml` → `version = "0.8.11"`
- `src/game_setup_hub/__init__.py` → `__version__ = "0.8.8"`
- `src/game_setup_hub/api.py:329` → `FastAPI(title=..., version="0.8.8")`

The API reports `0.8.8` in its OpenAPI schema and `/docs` while we ship
`0.8.11`. This broke once during the Bazzite fix when the version bumped but
`__init__.py` was missed.

**Fix**

Single source of truth. Either:

- Read version from installed package metadata in `__init__.py` and `api.py`:
  ```python
  from importlib.metadata import version as _v
  __version__ = _v("protonshift")
  ```
- Or delete `__version__` and `version=` and let the frontend read from the
  OS/package channel.

Also add a CI step that diffs `pyproject.toml` against `__init__.py` and fails
the build on drift.

Files: `src/game_setup_hub/__init__.py`, `src/game_setup_hub/api.py:329`,
`pyproject.toml:7`.

---

### P0-3. Missing explicit dependency on `pydantic`

`pyproject.toml` depends on `fastapi>=0.115,<1` and assumes `pydantic` arrives
transitively. `api.py` imports `from pydantic import BaseModel` directly — if
FastAPI ever switches to an optional Pydantic, or a user installs a broken
FastAPI build, the module fails to import.

Also `electron/python-runtime-requirements.txt` has the same omission.

**Fix**

Add `pydantic>=2.0` to both files. Even if we follow P0-1 option A and drop
Pydantic, fix this in the interim release so the dep graph matches imports.

Files: `pyproject.toml:11-15`, `electron/python-runtime-requirements.txt`.

---

## P1 — Correctness / safety

### P1-1. Path traversal in several endpoints

None of the endpoints that accept caller-supplied paths or filenames validate
them against a safe base. Examples:

- `POST /open-path` (`api.py:899`) opens any path that exists. Low impact
  because the Electron frontend is the only caller, but anyone who can reach
  `127.0.0.1:<port>` (including other local user processes) can ask the
  Python backend to open arbitrary paths via `xdg-open`.
- `PUT /mangohud/per-game/{game_name}` (`mangohud.py:215`). `game_name` is
  sanitized only by replacing `" "`, `"/"`, `"\"` — `..` slips through, so
  `game_name="../../.bashrc"` writes an arbitrary file under
  `~/.config/MangoHud/`. Limited blast radius (fixed dir) but still a bug.
- `POST /games/{app_id}/saves/restore` (`api.py:704`). `backup_path` and
  `target_dir` are taken verbatim. `backup_path="/etc/shadow"` does not leak
  (we only extract), but `target_dir="/home/<user>/.config/…"` can overwrite
  files with a malicious zip (zip slip — `zipfile.extractall` does not
  validate member paths in older Python; 3.12 does, but we should not rely
  on it).
- `profiles_storage._safe_filename` (`profiles_storage.py:36`) strips most
  bad chars but allows leading `.` (creates hidden files) and spaces. The
  mangohud helper re-implements a weaker version.

**Fix**

1. Add a single `paths.py` with:
   ```python
   def safe_join(base: Path, untrusted: str) -> Path: ...
   def sanitize_filename(name: str) -> str: ...
   ```
   Both raise `ValueError` on escape.
2. Apply at every API boundary that takes user paths or names.
3. Gate `/open-path` and `/open-uri` behind an allowlist of prefixes
   (Steam root, compatdata, profiles dir) or a shared secret between Electron
   and Python (already recommended in P1-2).

Files: `api.py:899-927`, `mangohud.py:215-218`, `saves.py:133`,
`profiles_storage.py:36`.

---

### P1-2. Unauthenticated localhost API with `CORS *`

`api.py:329-330`:

```python
app = FastAPI(title="ProtonShift API", version="0.8.8")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

The backend binds `127.0.0.1` so the external attack surface is small, but:

- Any **local** process (browser tabs included, via DNS rebinding to
  `127.0.0.1`) can issue state-changing requests.
- `allow_origins=["*"]` defeats the browser's same-origin check, which is the
  one thing that would block the rebind scenario.

**Fix**

1. Have Electron generate a random 32-byte hex token at startup, pass it to
   Python via env var (`PROTONSHIFT_API_TOKEN`), and include it as a header
   on every renderer request.
2. Add a FastAPI dependency that validates `X-Protonshift-Token` and rejects
   other requests with 401.
3. Narrow `allow_origins` to the Electron static-renderer origin
   (`http://127.0.0.1:<staticRendererPort>`).

Files: `api.py:329-330` plus a new `auth.py` dep.

---

### P1-3. VDF writes are not atomic and not Steam-aware

`vdf_config.set_launch_options` and `set_compat_tool` do:

```python
with open(config_path, "w", encoding="utf-8", newline="\n") as f:
    vdf.dump(data, f, pretty=True)
```

Two problems:

1. **No atomic rename.** A crash (or OS kill) mid-write leaves
   `localconfig.vdf` truncated. For Steam, that can wipe *all* launch options
   and compat tools.
2. **Steam races us.** `is_steam_running()` exists (`steam.py:12`) but nothing
   enforces it before writing. If the user edits launch options while Steam
   is running, Steam will overwrite our file on shutdown.

**Fix**

1. Atomic write helper:
   ```python
   def atomic_write_text(path: Path, data: str) -> None:
       tmp = path.with_suffix(path.suffix + ".tmp")
       tmp.write_text(data, encoding="utf-8", newline="\n")
       os.replace(tmp, path)
   ```
   Use it everywhere we overwrite a user-owned config (`vdf_config`,
   `env_vars`, `mangohud`, `profiles_storage`, `fixes`, `heroic_config`).
2. In `PUT /games/{app_id}/launch-options` and friends, return `409 Conflict`
   with a structured error when `is_steam_running()` is true. Let the
   frontend show the existing "Close Steam" dialog instead of the backend
   silently writing a doomed file.

Files: `vdf_config.py:62-122`, `env_vars.py:62-67`, `mangohud.py:197-212`,
`profiles_storage.py:40-48`, `fixes.py:82-98`, `heroic_config.py:85-90`.

---

### P1-4. `get_power_profiles` returns a hardcoded list, ignoring parsed data

`gpu.py:104-126`:

```python
r = subprocess.run(["powerprofilesctl", "list"], ...)
if r.returncode == 0:
    profiles = []
    for line in r.stdout.split("\n"):
        if "*" in line:
            m = re.search(r"[\*]\s*([\w-]+)", line)
            if m:
                profiles.append(m.group(1))
    if profiles:
        return ["performance", "balanced", "power-saver"]  # <-- wrong
```

The `profiles` list is built and then **thrown away**; the function returns
a constant. Also the regex matches the *current* profile (marked `*`), not
every available profile, so `profiles` has at most one entry anyway.

**Fix**

```python
r = subprocess.run(["powerprofilesctl", "list"], ...)
if r.returncode == 0:
    profiles = [
        m.group(1) for line in r.stdout.splitlines()
        if (m := re.match(r"\s*\*?\s*([\w-]+):", line))
    ]
    if profiles:
        return profiles
```

Then remove the hardcoded fallback or keep it only when parsing yields zero.

Files: `gpu.py:104-126`.

---

### P1-5. SDL controller GUID is fabricated

`controllers.get_sdl_mapping` (`controllers.py:119-142`) builds a GUID as:

```python
guid = f"{vendor_id:>04s}{product_id:>04s}".ljust(32, "0")
```

Real SDL2 GUIDs are 16 bytes LE: `bus(2) crc(2) vendor(2) 0000 product(2) 0000 version(2) 0000`. The stub we emit will not match in SDL and the
generated mapping will never apply. This is a latent bug dressed as a
feature.

**Fix**

Either:
- Read the canonical GUID from `/sys/class/input/jsN/device/id/{bustype,vendor,product,version}` and assemble the real 16-byte LE blob, or
- Remove the endpoint until we can do it correctly; the frontend can link
  to upstream `sdl2-jstest` / `antimicrox`.

Files: `controllers.py:119-142`, `api.py:622-629`.

---

### P1-6. `BUILTIN_PROTON` constant is dead; duplicate list in function body

`steam.py:188-201`:

```python
BUILTIN_PROTON = ["proton_experimental", "proton_9_0", ...]  # never used

def get_available_proton_tools(...) -> list[str]:
    tools: list[str] = ["", "proton_experimental", "proton_9_0", ...]
    ...
```

The module-level `BUILTIN_PROTON` constant is imported by nothing; the
function hardcodes a slightly different list. When Proton 10 ships, we will
update one of the two.

**Fix**

Delete `BUILTIN_PROTON` (or use it in the function). Add a comment pointing
at the Steam-side source of truth.

Files: `steam.py:188-201`.

---

### P1-7. `gamescope.build_gamescope_cmd` returns a shell-ready string

`gamescope.py:32-66` returns `" ".join(parts)` with `opts.extra_args`
concatenated unescaped. The string is surfaced in `/gamescope/build-cmd`
intended for copy-paste into Steam launch options, so it is not an
`exec`-style shell-injection issue, but:

- The frontend might eventually execute the string (we've already seen this
  pattern in `run_protontricks`).
- Users who paste `"; rm -rf ~"` in `extra_args` get surprising text back.

**Fix**

Return both `argv: list[str]` and `command: str` (quoted via `shlex.join`).
Frontend shows `command`; any executor uses `argv`.

Files: `gamescope.py:32-66`, `api.py:806-823`.

---

## P2 — Maintainability / quality

### P2-1. No tests, anywhere

4,647 LoC of Python without a single test file. The modules touching the
largest blast radius (`vdf_config`, `_vendor_compat`, `steam`, `heroic`,
`tool_check`, `env_vars`, path-sanitization helpers) are the ones that are
hardest to reason about by reading.

**Fix — minimum viable test suite**

Add `pytest` + a `tests/` tree with:

1. **VDF round-trips**: read a fixture `localconfig.vdf` → mutate → write →
   re-read, assert launch options preserved. Include the "Steam writes new
   keys we don't know about" case (verify we don't strip them).
2. **Tool detection**: `tool_check.find_tool` with monkey-patched `shutil.which`
   and temporary directories for the fallback branch.
3. **Path sanitization**: once P1-1 lands, test `safe_join` against a zip slip
   corpus.
4. **Env file**: `env_vars.read_conf` / `write_conf` with quoted values,
   escapes, comments.
5. **VS_FIXEDFILEINFO parse**: drop a minimal PE fixture and confirm DXVK
   version detection.
6. **API smoke**: `fastapi.testclient.TestClient(app)` hitting every GET
   endpoint against a fixture Steam root (pytest tmp_path).

Start with (1), (2), (4), (6) — that's ~4 hours of work and covers the
regression paths we've already hit twice.

---

### P2-2. `app.py` (GTK4) is 1053 lines of dead weight

`src/game_setup_hub/app.py` is the old GTK4 UI, excluded from pyright, and
no longer referenced by the Electron frontend. `pyproject.toml:21` still
declares `protonshift = "game_setup_hub.app:main"` so `pip install` creates a
launcher for it, but the README/packaging flow only uses the Electron app.

It imports `gi` unconditionally. Anyone who installs the wheel on a system
without GTK4 gets an `ImportError` they cannot debug.

**Fix**

1. Decide: do we still ship the GTK app? If no, delete `app.py`, `__main__.py`,
   and remove the `protonshift` console script.
2. If yes, move it under `src/game_setup_hub/gtk/` and gate the import
   (`try: import gi; except ImportError: ...`).

Either way, stop silently compiling 1k LoC that pyright refuses to look at.

Files: `src/game_setup_hub/app.py`, `src/game_setup_hub/__main__.py`,
`pyproject.toml:20-22`.

---

### P2-3. Silent `except Exception: pass` everywhere

Grep: 8 bare `except Exception` in `api.py` and `app.py`, plus ~40
`except OSError: pass` / `except (..., json.JSONDecodeError): return None`
across the backend. Every one of these turns into an empty list / empty
string in the UI with no logs to tell us which path failed.

Examples:

- `api.py:418-419`: `get_game_launch_options` swallows any VDF parse error
  and returns `""`. The user edits a file that was already corrupt and sees
  no warning.
- `heroic.py:68`, `heroic.py:157`: swallow every `KeyError` under
  `json.JSONDecodeError`. A schema change in Heroic == silent empty list.
- `profiles_storage.py:46`, `.64`, `.74`: write failures silently return
  `False` → UI says "saved" and nothing is on disk.

**Fix**

1. Add a module-level logger per file:
   ```python
   import logging
   log = logging.getLogger(__name__)
   ```
2. Configure once in `api.py` `cli()`:
   ```python
   logging.basicConfig(
       level=os.environ.get("PROTONSHIFT_LOG", "INFO"),
       format="%(levelname)s %(name)s: %(message)s",
   )
   ```
3. In every `except`, either log at `warning` (recoverable) or re-raise with
   context. Electron already pipes stderr to the dev console, so these show
   up for free.
4. For `Status`/boolean return values, return a `tuple[bool, str]` or a
   typed error so API endpoints can surface messages instead of bare 500s.

---

### P2-4. `api.py` and `app.py` are both 1k+ lines

`api.py` has 35+ endpoints plus 30+ Pydantic models plus helpers, in one
file. Navigating requires search.

**Fix**

Split by concern under `src/game_setup_hub/api/`:

```
api/__init__.py        # FastAPI app, middleware, CLI entry
api/models.py          # Pydantic response/request types
api/deps.py            # auth, _ensure_steam, _vdf_lock, etc.
api/routes/steam.py
api/routes/heroic.py
api/routes/lutris.py
api/routes/mangohud.py
api/routes/gamescope.py
api/routes/system.py   # gpu, power, display, controllers
api/routes/profiles.py
api/routes/saves.py
api/routes/system_io.py  # open-path, open-uri
```

Each routes file uses `APIRouter`. The top-level `api/__init__.py` wires
them up. This maps to a fresh Electron dev's mental model ("I'm looking for
the MangoHud endpoint" → obvious file).

---

### P2-5. Duplicate `_dir_size` helper in three modules

`saves.py:29-40`, `prefix.py:21-33`, `shader_cache.py:18-29` — same function,
subtle differences (one uses `stat()`, two use `lstat()`; symlink-following
differs). Same bug fix would have to land in three places.

**Fix**

Move to a new `src/game_setup_hub/fsutil.py` exposing `dir_size(path,
follow_symlinks=False) -> int` and a matching `human_size(bytes) -> str`
(which is also duplicated between `api.py:598-603` and the frontend).

---

### P2-6. `discover_games()` called on every request

`_ensure_steam()` caches only the Steam root, not the games list. Every call
to `/games`, `/games/.../saves`, `/games/.../prefix-info`, `/games/.../shader-cache`,
`/games/.../fixes`, and `/games/.../launch-options` re-parses every
`appmanifest_*.acf` on disk.

A Steam library with 500 games means ~500 VDF parses per page load.

**Fix**

Cache the result with a TTL (`functools.lru_cache` + a tiny wrapper that
invalidates on write, or `cachetools.TTLCache(maxsize=1, ttl=30)`). Expose
`POST /games/rescan` for the manual refresh button.

Files: `api.py:345-352, 397-408, 660-678, 861-896`.

---

### P2-7. `_human_size` lives in `api.py`, with a type-ignore

`api.py:598-603`:

```python
def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} PB"
```

The `type: ignore` exists because we mutate the `int` parameter into a
`float`. Type signature should be `float` (accepts int via widening) and the
loop variable should be local. Also: move to `fsutil.py` (P2-5).

---

### P2-8. Mixed CPython features and "defensive" `from __future__ import annotations`

Every module has `from __future__ import annotations`, required in 3.8-3.9
but unnecessary under `requires-python = ">=3.12"`. Pyright sees them as
strings, which hides some errors. Combined with the mix of `dict[str, str]`
and `Dict[str, str]`... actually it's clean `dict[str, str]` everywhere.

**Fix**

Keep `from __future__ import annotations` only where it's needed for forward
refs or self-types; remove elsewhere. Optional, but it is a constant source
of pyright confusion.

---

### P2-9. Cross-module private imports

`heroic_config.py:10` imports `heroic._resolve_heroic_root`. The underscore
prefix is a contract: this is private to `heroic.py`. Either promote
`resolve_heroic_root` to public or move the helper into a shared
`heroic_paths.py`.

Files: `heroic_config.py:10`, `heroic.py:30-34`.

---

### P2-10. `print("PORT:…")` IPC is brittle

`api.py:1046-1058` prints a port to stdout and relies on
`electron/main.ts:90-96` regex-matching `/PORT:(\d+)/`. If uvicorn's
`log_level="warning"` ever writes to stdout (it shouldn't but has in
past releases), the match consumes the wrong line.

**Fix**

- Send the port via a Unix domain socket opened by Electron before spawning
  Python, passed as a file descriptor or path in env. Python writes `{port}` and closes.
- Or: Electron picks a free port and passes it via `--port`, skipping the
  discovery dance.

Second option is one line.

Files: `api.py:1046-1058`, `electron/main.ts:81-116`.

---

## P3 — Minor / style

- `api.py:907, 910, 921, 924, 1013, 1016, 1019`: inline `import subprocess`
  inside handlers. Move to module top.
- `api.py:595`: `return StatusResponse(success=ok)` after `raise HTTPException`
  is unreachable — dead code.
- `profiles_storage.py:36`: `_safe_filename` accepts leading `.` → creates
  hidden files. Prepend `profile_` or strip leading dots.
- `controllers.py:124-128`: two identical `guid = ... .ljust(32, "0")`
  branches.
- `heroic.py:10-13`: `HEROIC_ROOTS` picks the first that exists. If a user
  has both the native install and Flatpak, order determines winner silently.
  Prefer whichever has a non-empty `GamesConfig/` or return both.
- `tool_check.py:65`: `@lru_cache(maxsize=32)` on `find_tool` means a user
  installing MangoHud mid-session still sees "not installed" until restart.
  Low frequency in practice; document it.
- `steam.py:89`: `break  # Use first found` inside a loop that appends to
  `paths` — the `break` skips the second libraryfolders.vdf even when the
  first is empty. Move `break` inside the success branch.
- `fixes.py:61-68`: `_common` fixes are appended after app-specific fixes;
  the UI has no way to distinguish. Consider a `scope: "common" | "app"` field.
- `api.py:329`: `FastAPI(title=..., version="0.8.8")` → see P0-2.
- `mangohud.py:215-218`: filename sanitization — see P1-1.
- `env_vars.py:60`: `.replace("\\", "\\\\").replace('"', '\\"')` followed by
  a `"…"` wrap works but is fragile. Prefer `shlex.quote` for shell
  compatibility with `environment.d` parsers.

---

## Dependency hygiene

Declared in `pyproject.toml`:

```toml
dependencies = [
  "vdf>=1.2",
  "fastapi>=0.115",
  "uvicorn[standard]>=0.34",
]
```

Missing from declarations but imported or referenced:

- `pydantic` (directly imported — see P0-3)
- `uvloop`, `httptools`, `watchfiles`, `yaml` (listed in `_vendor_compat._NATIVE_PACKAGES` but not depended on — dead list entries)

No upper bound on `vdf`. The `vdf` package is sparsely maintained; pin to a
known-good range (`"vdf>=1.2,<4"`).

---

## Packaging / runtime env

### Vendoring script (`electron/scripts/vendor-python-deps.sh`)

- Fine as long as we ship zero native deps (P0-1 option A).
- `python3 -m pip install -t "${TARGET}"` picks up whatever `python3` is on
  the CI runner. The `actions/setup-python@v5` pin is correct, but document
  that changing the CI runner Python version is a breaking change.
- The `.dist-info` pruning keeps `METADATA`, `top_level.txt`, `RECORD`. FastAPI
  uses `importlib.metadata.version("fastapi")` at startup (for the `/docs`
  render); test that we haven't broken that.

### Electron `getPythonCommand` (`electron/main.ts:40-79`)

- `EXTRA_PATH_DIRS` now covers Bazzite/SteamOS/NixOS — good.
- `env.PATH = \`${env.PATH}:${EXTRA_PATH_DIRS}\`` only runs when
  `!env.PATH.includes("/var/usrlocal/bin")`. If PATH already has
  `/var/usrlocal/bin` but nothing else from the list (unlikely but possible
  on a weird base image), we skip the augmentation. Safer to always
  deduplicate-and-merge.
- `PYTHONNOUSERSITE = ""` → see P0-1.

---

## Suggested implementation order

1. **P0-1** (drop native deps → switch to pure-Python stack) + **P0-2**
   (single version source) + **P0-3** (declare pydantic) → cut **v0.8.12**.
   This unblocks AppImage users on any Python.
2. **P1-2** (API token) + **P1-1** (path sanitization) → security hardening
   patch, **v0.9.0**.
3. **P2-1** (tests for VDF, tool_check, env_vars, API smoke) and **P2-2**
   (delete GTK app or isolate it) as cleanup before **v0.9.x**.
4. **P2-4** (split `api.py`) + **P2-3** (logging) once tests exist so the
   refactor is safe.
5. **P1-3** (atomic VDF writes + Steam-running guard) — user-reported
   corruption risk, schedule for **v0.9.x**.

Everything in P3 and leftover P2 can be rolled into whichever PR touches
the file.

---

## Appendix: file-by-file one-line assessment

| File | LoC | State |
| --- | --- | --- |
| `__init__.py` | 3 | Version drift (P0-2) |
| `__main__.py` | 6 | Points at dead GTK app (P2-2) |
| `_vendor_compat.py` | 70 | Broken on read-only FS (P0-1) — delete once P0-1A lands |
| `api.py` | 1062 | Oversized, needs split (P2-4); version drift (P0-2) |
| `app.py` | 1053 | Dead GTK UI (P2-2) |
| `controllers.py` | 142 | GUID is fake (P1-5) |
| `display.py` | 174 | Clean |
| `env_vars.py` | 128 | Missing atomic write (P1-3) |
| `fixes.py` | 98 | Missing atomic write (P1-3) |
| `gamescope.py` | 66 | Returns unescaped string (P1-7) |
| `gpu.py` | 175 | `get_power_profiles` bug (P1-4) |
| `heroic.py` | 179 | Clean, cross-module private (P2-9) |
| `heroic_config.py` | 196 | Missing atomic write (P1-3), private import (P2-9) |
| `lutris.py` | 91 | Clean |
| `mangohud.py` | 229 | Filename sanitize gap (P1-1); missing atomic write (P1-3) |
| `prefix.py` | 132 | Duplicate `_dir_size` (P2-5); full-file read for DLL |
| `presets.py` | 56 | Clean |
| `profiles_storage.py` | 76 | Weak `_safe_filename` (P1-1); missing atomic write (P1-3) |
| `protontricks.py` | 84 | Clean |
| `saves.py` | 145 | Duplicate `_dir_size` (P2-5); no zip size cap |
| `shader_cache.py` | 66 | Duplicate `_dir_size` (P2-5) |
| `steam.py` | 201 | Dead constant (P1-6); `break` placement bug (P3) |
| `tool_check.py` | 93 | Clean — the healthy module to model others on |
| `vdf_config.py` | 122 | No atomic write; no Steam-running check (P1-3) |
