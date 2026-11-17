"""The rules in the bundled fix pack, checked against real log lines.

``tests/test_fix_pack.py`` checks that the pack is well formed. This file
checks what the rules mean: every log rule matches the lines it was written
for (taken from public reports, or built from the upstream format string with
realistic values) and none of them matches lines that healthy games print.
Settings and per-game rules are checked through ``fix_pack`` only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from protonshift.core import fix_pack
from protonshift.core.fix_pack import Action, Rule, load_bundled_pack, match_log

PACK_PATH = Path(fix_pack.__file__).parent / "data" / "fix_pack.json"
PACK = load_bundled_pack()
RULES: dict[str, Rule] = {r.id: r for r in PACK.rules}

PFX = "/home/user/.local/share/Steam/steamapps/compatdata/1245620/pfx"
EXE = 'L"C:\\\\Program Files\\\\Game\\\\Game.exe"'

# --------------------------------------------------------------------------- #
# lines each rule must match
# --------------------------------------------------------------------------- #

# (rule id, line). The line must be the evidence match_log returns.
MATCHES: list[tuple[str, str]] = [
    # https://github.com/ValveSoftware/Proton/issues/4512 (older Wine, no quotes)
    ("prefix-not-owned",
     "wine: /mount/WindowsDrives/512/SteamLibrary/steamapps/compatdata/397540/pfx is not owned by you"),
    # wine dlls/ntdll/unix/server.c fatal_error("'%s' is not owned by you\n")
    ("prefix-not-owned", f"wine: '{PFX}' is not owned by you"),
    # wine server/request.c fatal_error("%s is not owned by you\n")
    ("prefix-not-owned", f"wineserver: {PFX} is not owned by you"),
    ("prefix-wrong-arch",
     f"wine: '{PFX}' is a 32-bit installation, it cannot support 64-bit applications."),
    ("prefix-wrong-arch",
     f"wine: '{PFX}' is a 64-bit installation, it cannot be used with a 32-bit wineserver."),
    # wine server/registry.c prints the file name relative to the prefix
    ("prefix-registry-corrupt", "system.reg is not a valid registry file"),
    ("prefix-registry-corrupt", "user.reg is not a valid registry file"),
    # fprintf("wineserver: could not save registry branch to %s") + perror(" ")
    ("prefix-write-failed", "wineserver: could not save registry branch to user.reg : No space left on device"),
    # https://github.com/ValveSoftware/Proton/issues/4269
    ("prefix-broken-kernel32", "wine: could not load kernel32.dll, status c0000135"),
    ("wineserver-stuck", "wine: a wine server seems to be running, but I cannot connect to it."),
    ("sync-stale-server",
     ("0024:err:esync:esync_init Failed to open esync shared memory file; make sure no stale wineserver "
      "instances are running without WINEESYNC.")),
    ("sync-stale-server",
     ("1234.567:0024:0028:err:fsync:fsync_init Failed to open fsync shared memory file; make sure no stale "
      "wineserver instances are running without WINEFSYNC.")),
    ("sync-stale-server",
     ("0024:err:esync:esync_init Server is running with WINEESYNC but this process is not, please enable "
      "WINEESYNC or restart wineserver.")),
    ("sync-stale-server",
     ("0024:err:fsync:fsync_init Server is running with WINEFSYNC but this process is not, please enable "
      "WINEFSYNC or restart wineserver.")),
    ("open-files-limit",
     "0130:err:winediag:NtCreateFile Too many open files, ulimit -n probably needs to be increased"),
    # Proton script, log header
    ("low-file-limit-warning",
     "WARNING: Low file descriptor limit: 4096 (see https://github.com/ValveSoftware/Proton/wiki/File-Descriptors)"),
    # https://github.com/ValveSoftware/Proton/issues/8360#issuecomment-2567242733
    ("low-max-map-count", "WARNING: Low /proc/sys/vm/max_map_count: 65530 will prevent some games from working"),
    ("missing-library",
     f"0130:err:module:import_dll Library MSVCP140.dll (which is needed by {EXE}) not found"),
    ("wrong-kind-of-library",
     f"0130:err:module:import_dll Loading library d3d9.dll (which is needed by {EXE}) failed (error c000007b)."),
    # https://github.com/GloriousEggroll/proton-ge-custom/issues/445 (log in a comment)
    ("no-display-driver",
     "0558:err:winediag:nodrv_CreateWindow Application tried to create a window, but no driver could be loaded."),
    ("vulkan-loader-missing", "0024:err:vulkan:vulkan_init_once Failed to load libvulkan.so.1"),
    # DXVK 3.x logs this as a warning, the first line of a multi-line message
    ("vulkan-no-driver", "warn:  DXVK: No adapters found. Please check your device filter settings"),
    ("vulkan-loader-no-drivers",
     "[Vulkan Loader] ERROR | DRIVER:      terminator_CreateInstance: Found no drivers!"),
    ("vulkan-loader-no-drivers", "ERROR: [Loader Message] Code 0 : vkCreateInstance: Found no drivers!"),
    # https://github.com/GloriousEggroll/proton-ge-custom/issues/445 (log in a comment)
    ("dxvk-init-failed", "err:   Failed to initialize DXVK."),
    ("d3d12-driver-lacks-feature",
     ('16063.015:0150:0154:err:vkd3d-proton:vkd3d_check_extensions: Required device extension '
      '"VK_KHR_dynamic_rendering" is not supported.')),
    ("d3d12-driver-lacks-feature",
     "16063.015:0150:0154:err:vkd3d-proton:vkd3d_instance_init: Vulkan 1.3 not supported by loader."),
    # vkd3d-proton's own format when it does not write through Wine
    ("d3d12-driver-lacks-feature",
     '0154:err:vkd3d_check_extensions: Required instance extension "VK_KHR_surface" is not supported.'),
]

# Lines that must also be in the log for a rule with ``log_also``.
CONTEXT: dict[str, list[str]] = {
    "missing-library": [f"0130:err:module:loader_init Importing dlls for {EXE} failed, status c0000135"],
    "wrong-kind-of-library": [f"0130:err:module:loader_init Importing dlls for {EXE} failed, status c0000135"],
}


@pytest.mark.parametrize(("rule_id", "line"), MATCHES)
def test_rule_matches_its_line(rule_id: str, line: str) -> None:
    rule = RULES[rule_id]
    lines = ["======================", "fsync: up and running.", line, *CONTEXT.get(rule_id, [])]
    assert match_log(rule, lines) == line.strip()


@pytest.mark.parametrize("rule_id", sorted(CONTEXT))
def test_log_also_rules_need_the_confirming_line(rule_id: str) -> None:
    line = next(text for rid, text in MATCHES if rid == rule_id)
    assert match_log(RULES[rule_id], [line]) is None


def test_confirming_line_may_come_first() -> None:
    line = next(text for rid, text in MATCHES if rid == "missing-library")
    assert match_log(RULES["missing-library"], [*CONTEXT["missing-library"], line]) == line


def test_missing_library_uses_older_loader_function_names() -> None:
    line = next(text for rid, text in MATCHES if rid == "missing-library")
    older = f"0009:err:module:LdrInitializeThunk Importing dlls for {EXE} failed, status c0000135"
    assert match_log(RULES["missing-library"], [line, older]) == line


# --------------------------------------------------------------------------- #
# lines no rule may match
# --------------------------------------------------------------------------- #

HEALTHY: list[str] = [
    "======================",
    "Proton: 1789520217 GE-Proton11-7",
    "Proton: Upgrading prefix from 10.0-100 to 11.0-100 (/home/user/.local/share/Steam/steamapps/compatdata/570/)",
    "System WINEDEBUG: 0",
    "Effective WINEDEBUG: 0",
    "fsync: up and running.",
    "esync: up and running.",
    "ntsync: up and running.",
    # A helper process can miss a library while the game runs fine.
    f"0130:err:module:import_dll Library MSVCP140.dll (which is needed by {EXE}) not found",
    f"0130:err:module:import_dll Loading library d3d9.dll (which is needed by {EXE}) failed (error c000007b).",
    "info:  Game: Game.exe",
    "info:  DXVK: v3.1-19-g601930949d111ed0",
    "info:  Vulkan: Found vkGetInstanceProcAddr in winevulkan.dll @ 0x6ffffc768a80",
    "info:  Found device: AMD Radeon 780M (RADV PHOENIX)",
    "info:    Skipping: Device does not support required feature 'shaderInt64'",
    "info:    Skipping: Software driver",
    "warn:  OpenXR: Unable to get required Vulkan instance extensions size",
    "0024:fixme:winediag:loader_init wine-staging 11.0 is a testing version containing experimental patches.",
    "0024:fixme:winediag:loader_init Please mention your exact version when filing bug reports on winehq.org.",
    "0130:fixme:ntdll:NtQuerySystemInformation info_class SYSTEM_PERFORMANCE_INFORMATION",
    "0130:fixme:file:NtLockFile I/O completion on lock not implemented yet",
    "0154:err:openxr:get_vulkan_extensions Error getting openxr_vulkan_instance_extensions, status 0x2.",
    "015c:err:service:device_notify_proc failed to get event, error 1726",
    ('00a4:err:ntoskrnl:ZwLoadDriver failed to create driver L"\\\\Registry\\\\Machine\\\\System\\\\'
     'CurrentControlSet\\\\Services\\\\winebth": c0000142'),
    "16063.156:0150:0154:warn:vkd3d-proton:vkd3d_create_device: Invalid feature level 0x1000.",
    "16063.147:0150:0154:info:vkd3d-proton:vkd3d_instance_init: vkd3d-proton - build: af89350cc2eacd9+.",
    "16063.015:0150:0154:warn:vkd3d-proton:openvr_instance_extensions: Failed to wait for VR registry key ready.",
    "16062.599:0150:0154:info:nvapi64:<-NvAPI_Initialize: OK",
    "gamemodeauto: dlopen failed - libgamemode.so: cannot open shared object file: No such file or directory",
    "[2026-09-19 23:33:58.843] [MANGOHUD] [error] [cpu.cpp:794] Failed to initialize CPU power data",
    "pid 336968 != 336956, skipping destruction (fork without exec?)",
]

# A line close to a rule's own that means something else.
NEAR_MISSES: list[tuple[str, str]] = [
    ("dxvk-init-failed", "err:   Failed to initialize DXVK device."),
    # Proton 11's fsync: the kernel lacks futex_waitv, not a stale server
    ("sync-stale-server",
     "0024:err:fsync:fsync_init Server is running with WINEFSYNC but this process can't use __NR_futex_waitv."),
    ("d3d12-driver-lacks-feature",
     ('16063.015:0150:0154:warn:vkd3d-proton:vkd3d_check_extensions: Optional user device extension '
      '"VK_EXT_foo" is not supported.')),
    ("missing-library",
     f"0130:err:module:import_dll Loading library d3d9.dll (which is needed by {EXE}) failed (error c000007b)."),
    ("prefix-not-owned", "Proton: the folder is not owned by you"),
    ("vulkan-no-driver", "info:  Found device: llvmpipe (LLVM 19.1.7, 256 bits)"),
]


def test_no_rule_matches_a_healthy_log() -> None:
    hits = [(r.id, match_log(r, HEALTHY)) for r in PACK.rules if r.log]
    assert [h for h in hits if h[1] is not None] == []


@pytest.mark.parametrize("line", HEALTHY)
def test_no_rule_matches_a_healthy_line(line: str) -> None:
    assert [r.id for r in PACK.rules if match_log(r, [line])] == []


@pytest.mark.parametrize(("rule_id", "line"), NEAR_MISSES)
def test_rule_skips_a_near_miss(rule_id: str, line: str) -> None:
    lines = [line, *CONTEXT.get(rule_id, [])]
    assert match_log(RULES[rule_id], lines) is None


def test_log_rules_ignore_the_settings_alone() -> None:
    # A log rule never matches without a log.
    for r in PACK.rules:
        if r.log:
            assert match_log(r, []) is None, r.id


# --------------------------------------------------------------------------- #
# settings and per-game rules (no log)
# --------------------------------------------------------------------------- #

def unset(key: str) -> Action:
    return Action("unset_env", key=key)


# rule id -> (app_ids, when fields that must be set, actions without manual text)
SETTINGS: dict[str, tuple[tuple[str, ...], dict[str, object], tuple[Action, ...]]] = {
    "mangohud-inside-gamescope": (
        (), {"launch_has": ("mangohud", "gamescope")},
        (Action("remove_word", value="mangohud"),),
    ),
    "esync-switch-obsolete": (
        (), {"env_set": ("PROTON_NO_ESYNC",), "proton_family": ("valve",), "proton_major_min": 11},
        (unset("PROTON_NO_ESYNC"),),
    ),
    "d9vk-switch-obsolete": (
        (), {"env_set": ("PROTON_USE_D9VK",), "proton_family": ("valve",), "proton_major_min": 5},
        (unset("PROTON_USE_D9VK"),),
    ),
    "seccomp-switch-obsolete": (
        (), {"env_set": ("PROTON_USE_SECCOMP",), "proton_family": ("valve",), "proton_major_min": 6},
        (unset("PROTON_USE_SECCOMP"),),
    ),
    "nvapi-switch-wrong-build": (
        (), {"env_set": ("PROTON_ENABLE_NVAPI",), "proton_family": ("valve",), "proton_major_min": 9},
        (unset("PROTON_ENABLE_NVAPI"),),
    ),
    "gamescope-blocks-wayland-game": (
        (), {"env_set": ("PROTON_ENABLE_WAYLAND",), "launch_has": ("gamescope",), "proton_family": ("ge",)},
        (),
    ),
    "cyberpunk-2077-camera-jumps": (
        ("1091500",), {"proton_major_min": 10},
        (Action("env", key="PROTON_DISABLE_HIDRAW", value="1"),),
    ),
    "elden-ring-many-threads": (
        ("1245620",), {},
        (Action("env", key="WINE_CPU_TOPOLOGY", value="16:0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15"),),
    ),
}


@pytest.mark.parametrize("rule_id", sorted(SETTINGS))
def test_settings_rule_shape(rule_id: str) -> None:
    app_ids, when, changes = SETTINGS[rule_id]
    rule = RULES[rule_id]
    assert rule.log == () and rule.log_also == ()
    assert rule.app_ids == app_ids
    for name, value in when.items():
        assert getattr(rule.when, name) == value, name
    unset_fields = {"gpu_vendor", "session", "proton_family", "proton_major_min", "proton_major_max",
                    "launch_has", "env_set", "env_unset"} - set(when)
    for name in unset_fields:
        assert getattr(rule.when, name) in ((), None), name
    assert tuple(a for a in rule.actions if a.type != "manual") == changes


@pytest.mark.parametrize("rule_id", sorted(SETTINGS))
def test_settings_rules_are_advice_unless_they_change_a_broken_setup(rule_id: str) -> None:
    rule = RULES[rule_id]
    expected = "likely" if rule_id == "mangohud-inside-gamescope" else "advice"
    assert rule.severity == expected


def test_settings_rule_actions_parse_again() -> None:
    # The actions survive a round trip through the loader.
    raw = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    for item in raw["rules"]:
        if item["id"] in SETTINGS:
            assert fix_pack.parse_rule(item) == RULES[item["id"]]


def test_mangohud_rule_tells_how_to_keep_the_overlay() -> None:
    texts = [a.text for a in RULES["mangohud-inside-gamescope"].actions if a.type == "manual"]
    assert len(texts) == 1 and "--mangoapp" in texts[0]


def test_wayland_rule_names_both_choices() -> None:
    (action,) = RULES["gamescope-blocks-wayland-game"].actions
    assert action.type == "manual"
    assert "--expose-wayland" in action.text and "PROTON_ENABLE_WAYLAND" in action.text


def test_elden_ring_rule_names_the_thread_count() -> None:
    rule = RULES["elden-ring-many-threads"]
    assert "24" in rule.title and "24" in rule.cause


# --------------------------------------------------------------------------- #
# the pack as a whole
# --------------------------------------------------------------------------- #

ALLOWED_HOSTS = {
    "github.com", "wiki.archlinux.org", "docs.bazzite.gg", "gitlab.steamos.cloud", "gitlab.winehq.org",
}


def test_pack_loads_every_rule() -> None:
    assert PACK.rejected == []
    assert PACK.revision == "2026.11.1"
    assert len(RULES) == len(PACK.rules)


@pytest.mark.parametrize("rule", PACK.rules, ids=lambda r: r.id)
def test_source_host_is_allowed(rule: Rule) -> None:
    assert urlsplit(rule.source).hostname in ALLOWED_HOSTS


@pytest.mark.parametrize("rule", PACK.rules, ids=lambda r: r.id)
def test_source_code_links_are_pinned(rule: Rule) -> None:
    parts = urlsplit(rule.source)
    if "/blob/" in parts.path:
        ref = parts.path.split("/blob/", 1)[1].split("/", 1)[0]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{rule.id}: {ref} is not a commit"
        assert re.fullmatch(r"L[0-9]+", parts.fragment), f"{rule.id}: no line anchor"


def test_every_rule_has_a_test() -> None:
    covered = {rid for rid, _ in MATCHES} | set(SETTINGS)
    assert sorted(set(RULES) - covered) == []
    assert sorted(covered - set(RULES)) == []


def test_every_log_rule_has_a_matching_sample() -> None:
    sampled = {rid for rid, _ in MATCHES}
    assert sorted(r.id for r in PACK.rules if r.log and r.id not in sampled) == []
    assert sorted(r.id for r in PACK.rules if not r.log and r.id not in SETTINGS) == []


def _texts(rule: Rule) -> list[str]:
    return [rule.title, rule.cause, *(a.text for a in rule.actions if a.type == "manual")]


@pytest.mark.parametrize("rule", PACK.rules, ids=lambda r: r.id)
def test_text_is_plain(rule: Rule) -> None:
    for text in _texts(rule):
        assert "\u2014" not in text and "\u2013" not in text, text
        assert "!" not in text, text
        assert not re.search(r"\bsimply\b", text, re.IGNORECASE), text
        assert text == text.strip() and "  " not in text, text


def test_file_has_no_dashes_and_is_indented_by_two() -> None:
    text = PACK_PATH.read_text(encoding="utf-8")
    assert "\u2014" not in text and "\u2013" not in text
    data = json.loads(text)
    assert text == json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def test_keys_are_in_contract_order() -> None:
    data = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    assert list(data) == ["format", "version", "revision", "rules"]
    match_order = ["app_ids", "log", "log_also", "when"]
    for item in data["rules"]:
        assert list(item) == list(fix_pack._RULE_KEYS), item["id"]
        keys = list(item["match"])
        assert keys == [k for k in match_order if k in keys], item["id"]
        for action in item["actions"]:
            assert next(iter(action)) == "type", item["id"]
        assert item["verified"] == "2026-11-16", item["id"]
