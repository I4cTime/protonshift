"""Layout tests for the force-feedback structs in core.input_devices.

These pin the 64-bit kernel ABI: sizeof(struct ff_effect) == 48 with the
rumble union at offset 16 (2 pad bytes after ff_replay), and a 24-byte
input_event (16-byte timeval + type/code/value).
"""

from __future__ import annotations

import struct

from protonshift.core.input_devices import (
    _EV_FF,
    _EVIOCSFF,
    _FF_EFFECT_SIZE,
    _FF_RUMBLE,
    pack_ff_play,
    pack_ff_rumble,
    unpack_ff_effect_id,
)


def test_ff_effect_size() -> None:
    assert _FF_EFFECT_SIZE == 48
    assert len(pack_ff_rumble()) == 48


def test_ff_effect_field_offsets() -> None:
    b = pack_ff_rumble(effect_id=-1, duration_ms=600, strong=0xFFFF, weak=0xC000)
    assert struct.unpack_from("=H", b, 0)[0] == _FF_RUMBLE      # type
    assert struct.unpack_from("=h", b, 2)[0] == -1              # id, signed
    assert struct.unpack_from("=H", b, 4)[0] == 0               # direction
    assert struct.unpack_from("=HH", b, 6) == (0, 0)            # trigger
    assert struct.unpack_from("=HH", b, 10) == (600, 0)         # replay
    assert b[14:16] == b"\x00\x00"                              # union pad
    assert struct.unpack_from("=H", b, 16)[0] == 0xFFFF         # strong @ 16
    assert struct.unpack_from("=H", b, 18)[0] == 0xC000         # weak @ 18
    assert b[20:] == b"\x00" * 28                               # tail padding


def test_negative_id_packs_without_error() -> None:
    # The original bug: `-1 & 0xFFFF` into a signed 'h' raised struct.error
    # on every call. A signed -1 must pack cleanly.
    b = pack_ff_rumble(effect_id=-1)
    assert b[2:4] == b"\xff\xff"


def test_unpack_effect_id_roundtrip() -> None:
    b = bytearray(pack_ff_rumble(effect_id=-1))
    struct.pack_into("=h", b, 2, 7)  # kernel writes the assigned id back
    assert unpack_ff_effect_id(bytes(b)) == 7


def test_play_event_layout() -> None:
    ev = pack_ff_play(7, 1)
    assert len(ev) == 24  # not 16 — timeval is two 8-byte longs on 64-bit
    sec, usec, etype, code, value = struct.unpack("=qqHHi", ev)
    assert (sec, usec) == (0, 0)
    assert etype == _EV_FF
    assert code == 7
    assert value == 1


def test_eviocsff_constant() -> None:
    # _IOW('E', 0x80, struct ff_effect) with size 0x30
    assert _EVIOCSFF == 0x40304580


def test_start_worker_routes_exception() -> None:
    from protonshift.controllers._worker import start_worker

    got: list[str] = []

    def boom() -> None:
        raise RuntimeError("kaput")

    t = start_worker(boom, on_error=got.append)
    t.join(2)
    assert got == ["RuntimeError: kaput"]


def test_start_worker_passes_args() -> None:
    from protonshift.controllers._worker import start_worker

    seen: list[tuple] = []
    t = start_worker(lambda a, b: seen.append((a, b)), 1, "x")
    t.join(2)
    assert seen == [(1, "x")]
