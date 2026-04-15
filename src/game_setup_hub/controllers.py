"""Game controller/input detection and SDL mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ControllerInfo:
    id: str
    name: str
    device_path: str
    controller_type: str  # "xbox", "playstation", "nintendo", "generic"
    vendor_id: str = ""
    product_id: str = ""


def _classify_controller(name: str) -> str:
    """Classify controller type from its name."""
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
    controllers: list[ControllerInfo] = []
    devices_path = Path("/proc/bus/input/devices")

    if not devices_path.exists():
        return _get_controllers_from_js()

    try:
        content = devices_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return _get_controllers_from_js()

    for block in content.split("\n\n"):
        if not block.strip():
            continue

        name = ""
        handlers = ""
        vendor = ""
        product = ""
        is_joystick = False

        for line in block.splitlines():
            if line.startswith("N: Name="):
                name = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("H: Handlers="):
                handlers = line.split("=", 1)[1]
                if "js" in handlers:
                    is_joystick = True
            elif line.startswith("I:"):
                v_match = re.search(r"Vendor=([0-9a-fA-F]+)", line)
                p_match = re.search(r"Product=([0-9a-fA-F]+)", line)
                if v_match:
                    vendor = v_match.group(1)
                if p_match:
                    product = p_match.group(1)

        if not is_joystick or not name:
            continue

        js_match = re.search(r"(js\d+)", handlers)
        js_dev = js_match.group(1) if js_match else "js0"
        device_path = f"/dev/input/{js_dev}"

        controllers.append(ControllerInfo(
            id=f"{vendor}:{product}",
            name=name,
            device_path=device_path,
            controller_type=_classify_controller(name),
            vendor_id=vendor,
            product_id=product,
        ))

    return controllers


def _get_controllers_from_js() -> list[ControllerInfo]:
    """Fallback: detect from /dev/input/js* devices."""
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
            id=js_path.name,
            name=name,
            device_path=str(js_path),
            controller_type=_classify_controller(name),
        ))

    return controllers


def get_sdl_mapping(controller: ControllerInfo) -> str:
    """
    Generate an SDL_GAMECONTROLLERCONFIG entry for a controller.
    This is a basic GUID-based stub; full calibration requires user input.
    """
    guid = f"{controller.vendor_id:>04s}{controller.product_id:>04s}".replace(" ", "0")
    if len(guid) < 8:
        guid = guid.ljust(32, "0")
    else:
        guid = guid.ljust(32, "0")

    # Standard Xbox-style mapping as a starting point
    mapping = (
        f"{guid},{controller.name},"
        "a:b0,b:b1,x:b2,y:b3,"
        "back:b6,start:b7,guide:b8,"
        "leftshoulder:b4,rightshoulder:b5,"
        "leftstick:b9,rightstick:b10,"
        "dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
        "leftx:a0,lefty:a1,rightx:a3,righty:a4,"
        "lefttrigger:a2,righttrigger:a5,"
        "platform:Linux,"
    )
    return mapping
