"""Game controller detection, SDL mapping, live test, and rumble.

Detection + SDL GUID/mapping are ported from the original ProtonShift core
(stdlib only: /proc/bus/input/devices + sysfs). Added here for the native tester:
a live reader of the legacy joystick (``/dev/input/js*``) event stream and a
best-effort force-feedback rumble over the matching ``event*`` node.

Inside a Flatpak this needs ``--device=input`` in the manifest.
"""

from __future__ import annotations

import ctypes
import fcntl
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ControllerInfo:
    id: str
    name: str
    device_path: str
    controller_type: str  # xbox|playstation|nintendo|8bitdo|steam|generic
    vendor_id: str = ""
    product_id: str = ""
    bus_type: str = ""
    version: str = ""


def _classify_controller(name: str) -> str:
    lower = name.lower()
    if any(k in lower for k in ("xbox", "x-box", "microsoft")):
        return "xbox"
    if any(k in lower for k in ("playstation", "ps3", "ps4", "ps5", "dualsense", "dualshock", "sony")):
        return "playstation"
    if any(k in lower for k in ("nintendo", "switch", "pro controller", "joy-con")):
        return "nintendo"
    if any(k in lower for k in ("8bitdo", "8bit")):
        return "8bitdo"
    if any(k in lower for k in ("steam", "valve")):
        return "steam"
    return "generic"


def get_controllers() -> list[ControllerInfo]:
    """Detect connected game controllers via /proc/bus/input/devices."""
    devices_path = Path("/proc/bus/input/devices")
    if not devices_path.exists():
        return _get_controllers_from_js()
    try:
        content = devices_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return _get_controllers_from_js()

    controllers: list[ControllerInfo] = []
    for block in content.split("\n\n"):
        if not block.strip():
            continue
        name = handlers = bus = vendor = product = version = ""
        is_joystick = False
        for line in block.splitlines():
            if line.startswith("N: Name="):
                name = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("H: Handlers="):
                handlers = line.split("=", 1)[1]
                if "js" in handlers:
                    is_joystick = True
            elif line.startswith("I:"):
                if (m := re.search(r"Bus=([0-9a-fA-F]+)", line)):
                    bus = m.group(1)
                if (m := re.search(r"Vendor=([0-9a-fA-F]+)", line)):
                    vendor = m.group(1)
                if (m := re.search(r"Product=([0-9a-fA-F]+)", line)):
                    product = m.group(1)
                if (m := re.search(r"Version=([0-9a-fA-F]+)", line)):
                    version = m.group(1)
        if not is_joystick or not name:
            continue
        js_match = re.search(r"(js\d+)", handlers)
        js_dev = js_match.group(1) if js_match else "js0"
        # The js node is part of the id so two identical pads (same VID:PID)
        # don't collide in id-keyed lookups.
        controllers.append(ControllerInfo(
            id=f"{vendor}:{product}:{js_dev}",
            name=name,
            device_path=f"/dev/input/{js_dev}",
            controller_type=_classify_controller(name),
            vendor_id=vendor, product_id=product, bus_type=bus, version=version,
        ))
    return controllers


def _read_sysfs_id(js_name: str, key: str) -> str:
    p = Path(f"/sys/class/input/{js_name}/device/id/{key}")
    try:
        return p.read_text(encoding="utf-8").strip() if p.exists() else ""
    except OSError:
        return ""


def _get_controllers_from_js() -> list[ControllerInfo]:
    controllers: list[ControllerInfo] = []
    input_dir = Path("/dev/input")
    if not input_dir.exists():
        return controllers
    for js_path in sorted(input_dir.glob("js*")):
        name_path = Path(f"/sys/class/input/{js_path.name}/device/name")
        name = js_path.name
        if name_path.exists():
            try:
                name = name_path.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        controllers.append(ControllerInfo(
            id=js_path.name, name=name, device_path=str(js_path),
            controller_type=_classify_controller(name),
            vendor_id=_read_sysfs_id(js_path.name, "vendor"),
            product_id=_read_sysfs_id(js_path.name, "product"),
            bus_type=_read_sysfs_id(js_path.name, "bustype"),
            version=_read_sysfs_id(js_path.name, "version"),
        ))
    return controllers


# --------------------------------------------------------------------------- #
# SDL mapping
# --------------------------------------------------------------------------- #

def _build_sdl_guid(bus: str, vendor: str, product: str, version: str) -> str:
    def _hex16(value: str) -> int:
        try:
            return int(value, 16) & 0xFFFF
        except ValueError:
            return 0

    blob = struct.pack(
        "<HHHHHHHH",
        _hex16(bus), 0, _hex16(vendor), 0, _hex16(product), 0, _hex16(version), 0,
    )
    return blob.hex()


def get_sdl_mapping(c: ControllerInfo) -> str:
    """A generic Xbox-style SDL_GAMECONTROLLERCONFIG entry for a controller."""
    guid = _build_sdl_guid(c.bus_type or "0003", c.vendor_id, c.product_id, c.version)
    name = c.name.replace(",", " ")
    return (
        f"{guid},{name},"
        "a:b0,b:b1,x:b2,y:b3,back:b6,start:b7,guide:b8,"
        "leftshoulder:b4,rightshoulder:b5,leftstick:b9,rightstick:b10,"
        "dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
        "leftx:a0,lefty:a1,rightx:a3,righty:a4,"
        "lefttrigger:a2,righttrigger:a5,platform:Linux,"
    )


# --------------------------------------------------------------------------- #
# Live joystick reader (legacy js interface)
# --------------------------------------------------------------------------- #

# struct js_event { __u32 time; __s16 value; __u8 type; __u8 number; }
_JS_EVENT = struct.Struct("=IhBB")
_JS_EVENT_BUTTON = 0x01
_JS_EVENT_AXIS = 0x02
_JS_EVENT_INIT = 0x80

# ioctls to query button/axis counts: JSIOCGBUTTONS / JSIOCGAXES
_JSIOCGAXES = 0x80016A11
_JSIOCGBUTTONS = 0x80016A12


def js_counts(path: str) -> tuple[int, int]:
    """Return ``(num_axes, num_buttons)`` for a js device, or ``(0, 0)``."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return (0, 0)
    try:
        axes = ctypes.c_uint8(0)
        buttons = ctypes.c_uint8(0)
        fcntl.ioctl(fd, _JSIOCGAXES, axes)
        fcntl.ioctl(fd, _JSIOCGBUTTONS, buttons)
        return (axes.value, buttons.value)
    except OSError:
        return (0, 0)
    finally:
        os.close(fd)


def open_js(path: str) -> int | None:
    """Open a js device non-blocking. Returns fd or None."""
    try:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None


def read_js_events(fd: int) -> list[tuple[str, int, float]]:
    """Drain pending js events. Returns ``[(kind, number, value)]`` where kind is
    ``"button"`` (value 0/1) or ``"axis"`` (value -1.0..1.0). Empty if nothing."""
    events: list[tuple[str, int, float]] = []
    while True:
        try:
            data = os.read(fd, _JS_EVENT.size)
        except (BlockingIOError, InterruptedError):
            break
        except OSError:
            break
        if not data or len(data) < _JS_EVENT.size:
            break
        _t, value, etype, number = _JS_EVENT.unpack(data)
        etype &= ~_JS_EVENT_INIT
        if etype == _JS_EVENT_BUTTON:
            events.append(("button", number, float(value)))
        elif etype == _JS_EVENT_AXIS:
            events.append(("axis", number, max(-1.0, min(1.0, value / 32767.0))))
    return events


# --------------------------------------------------------------------------- #
# Rumble (best-effort, via the matching event device force-feedback)
# --------------------------------------------------------------------------- #

def _event_node_for_js(js_path: str) -> str | None:
    """Find the /dev/input/eventN that shares the js device's parent."""
    js_name = Path(js_path).name
    dev_dir = Path(f"/sys/class/input/{js_name}/device")
    if not dev_dir.exists():
        return None
    for child in dev_dir.glob("event*"):
        return f"/dev/input/{child.name}"
    return None


# struct ff_effect (linux/input.h) on 64-bit userspace (x86-64 / aarch64):
#
#   __u16 type;                                    offset  0
#   __s16 id;                                      offset  2
#   __u16 direction;                               offset  4
#   struct ff_trigger { __u16 button, interval; }  offset  6
#   struct ff_replay  { __u16 length, delay;    }  offset 10
#   <2 pad bytes — the union below embeds a pointer (ff_periodic_effect
#    .custom_data), so the union is 8-aligned>
#   union u { ... struct ff_rumble_effect {
#       __u16 strong_magnitude, weak_magnitude; } ... }  offset 16
#
# sizeof(struct ff_effect) == 48. The previous implementation packed the id
# as `-1 & 0xFFFF` into a signed 'h' (always raised struct.error), omitted the
# 2 pad bytes (magnitudes landed at offset 14), and wrote a 16-byte play event
# where the kernel expects 24 — all three fixed here, layout pinned by tests.
_FF_EFFECT_SIZE = 48
_FF_RUMBLE = 0x50
_EV_FF = 0x15
# _IOW('E', 0x80, struct ff_effect) — direction 0x40000000 | size<<16 | 'E'<<8 | nr
_EVIOCSFF = 0x40000000 | (_FF_EFFECT_SIZE << 16) | (ord("E") << 8) | 0x80

# struct input_event on 64-bit: struct timeval { long tv_sec, tv_usec; } (16)
# + __u16 type + __u16 code + __s32 value == 24 bytes.
_INPUT_EVENT = struct.Struct("=qqHHi")


def pack_ff_rumble(
    effect_id: int = -1,
    duration_ms: int = 600,
    strong: int = 0xFFFF,
    weak: int = 0xC000,
) -> bytes:
    """Pack a rumble ``struct ff_effect`` (64-bit layout, exactly 48 bytes)."""
    return struct.pack(
        "=HhHHHHHxxHH28x",
        _FF_RUMBLE,                # type
        effect_id,                 # id (signed; -1 -> kernel assigns one)
        0,                         # direction
        0, 0,                      # trigger: button, interval
        duration_ms & 0xFFFF, 0,   # replay: length, delay
        strong & 0xFFFF,           # union.rumble.strong_magnitude (offset 16)
        weak & 0xFFFF,             # union.rumble.weak_magnitude   (offset 18)
    )


def unpack_ff_effect_id(buf: bytes) -> int:
    """Read the kernel-assigned effect id back out of an uploaded ff_effect."""
    return struct.unpack_from("=h", buf, 2)[0]


def pack_ff_play(effect_id: int, value: int = 1) -> bytes:
    """Pack the ``input_event`` that starts (value=1) or stops (0) an effect."""
    return _INPUT_EVENT.pack(0, 0, _EV_FF, effect_id & 0xFFFF, value)


def rumble(js_path: str, duration_ms: int = 600) -> tuple[bool, str]:
    """Fire a strong+weak rumble on the controller's FF event node."""
    event_node = _event_node_for_js(js_path)
    if not event_node:
        return False, "No force-feedback device found for this controller."
    try:
        fd = os.open(event_node, os.O_RDWR)
    except OSError as exc:
        return False, f"Couldn't open {event_node}: {exc}"
    try:
        buf = ctypes.create_string_buffer(
            pack_ff_rumble(duration_ms=duration_ms), _FF_EFFECT_SIZE
        )
        fcntl.ioctl(fd, _EVIOCSFF, buf)  # upload; kernel writes the id back
        new_id = unpack_ff_effect_id(buf.raw)
        if new_id < 0:
            return False, "Device did not assign a force-feedback effect id."
        os.write(fd, pack_ff_play(new_id, 1))
        return True, "Rumble sent."
    except OSError as exc:
        return False, f"Rumble not supported: {exc}"
    finally:
        os.close(fd)
