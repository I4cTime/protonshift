"""SDL GUID + classification logic for controllers."""

from __future__ import annotations

from game_setup_hub.controllers import (
    ControllerInfo,
    _build_sdl_guid,
    _classify_controller,
    get_sdl_mapping,
)


def test_classify_xbox() -> None:
    assert _classify_controller("Microsoft Xbox Series X Controller") == "xbox"


def test_classify_playstation() -> None:
    assert _classify_controller("Sony Interactive Entertainment DualSense") == "playstation"


def test_classify_nintendo() -> None:
    assert _classify_controller("Nintendo Switch Pro Controller") == "nintendo"


def test_classify_unknown_is_generic() -> None:
    assert _classify_controller("Random USB Joystick") == "generic"


def test_build_sdl_guid_is_32_hex_chars() -> None:
    guid = _build_sdl_guid("0003", "045e", "02ea", "0301")
    assert len(guid) == 32
    assert all(c in "0123456789abcdef" for c in guid)


def test_build_sdl_guid_endianness() -> None:
    """Verify the little-endian layout: bus, crc=0, vendor, 0, product, 0, version, 0."""
    guid = _build_sdl_guid("0003", "045e", "02ea", "0301")
    # bus 0x0003 -> "0300"; crc 0x0000 -> "0000"; vendor 0x045e -> "5e04"; ...
    assert guid.startswith("03000000")
    assert guid[8:16] == "5e040000"
    assert guid[16:24] == "ea020000"
    assert guid[24:32] == "01030000"


def test_build_sdl_guid_handles_invalid_hex() -> None:
    guid = _build_sdl_guid("zzzz", "", "", "")
    assert guid == "0" * 32


def test_get_sdl_mapping_includes_guid_and_platform() -> None:
    ctrl = ControllerInfo(
        id="045e:02ea",
        name="Xbox Wireless Controller",
        device_path="/dev/input/js0",
        controller_type="xbox",
        vendor_id="045e",
        product_id="02ea",
        bus_type="0003",
        version="0301",
    )
    mapping = get_sdl_mapping(ctrl)
    parts = mapping.split(",")
    assert len(parts[0]) == 32  # GUID
    assert parts[1] == "Xbox Wireless Controller"
    assert "platform:Linux" in mapping


def test_get_sdl_mapping_strips_commas_from_name() -> None:
    ctrl = ControllerInfo(
        id="x", name="Brand, Model, X", device_path="/dev/input/js0",
        controller_type="xbox", vendor_id="0", product_id="0", bus_type="0003",
    )
    mapping = get_sdl_mapping(ctrl)
    # Name field (index 1) must not contain commas, so the mapping fields parse correctly
    parts = mapping.split(",")
    assert parts[1] == "Brand  Model  X"
