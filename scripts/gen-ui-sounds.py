#!/usr/bin/env python3
"""Synthesize ProtonShift's UI sound sets (protonshift/qml/assets/sounds/<set>/*.wav).

The sets are original, generated from first principles (oscillators, noise,
envelopes) - no samples, nothing to license. Same method as MineUI's
scripts/gen-ui-sounds.py; "glass" and "terminal" share its voicing, "pulse" is
ProtonShift's own default set.

    python3 scripts/gen-ui-sounds.py            # all sets
    python3 scripts/gen-ui-sounds.py glass      # one set

Needs numpy (a dev-only tool; the app itself just plays the committed files).
Every sound is levelled to the same per-type average (RMS) with the peak
capped at -3.5 dBFS, so the per-sound volumes in protonshift/core/sounds.py
apply to every set alike and switching sets does not change how loud the app
is. Output is 16-bit mono WAV, which Qt's QSoundEffect plays without a codec.
"""
import pathlib
import sys
import wave

import numpy as np

SR = 44100
PEAK_DB = -3.5
# Target average level of each sound type (dB), shared by every set. The two
# toggles share one target so on/off feel like a pair.
MEAN_DB = {
    "click": -21.7, "back": -23.4,
    "toggle_on": -25.8, "toggle_off": -25.8, "slider": -22.9,
    "success": -19.4, "error": -17.2, "notification": -18.5,
}
ROOT = pathlib.Path(__file__).resolve().parent.parent / "protonshift" / "qml" / "assets" / "sounds"
rng = np.random.default_rng(20261004)  # fixed: regenerating gives the same files


def t(dur):
    return np.arange(int(SR * dur)) / SR


def env(dur, attack=0.004, decay=None, curve=5.0):
    """Fast attack, exponential decay to silence by `dur`."""
    x = t(dur)
    decay = dur if decay is None else decay
    e = np.exp(-curve * x / decay)
    a = np.minimum(1.0, x / max(attack, 1e-4))
    tail = np.minimum(1.0, (dur - x) / 0.006)  # 6 ms release: no click at the end
    return e * a * np.clip(tail, 0, 1)


def osc(freq, dur, shape="sine", glide=None):
    """Oscillator; `glide` = end frequency for a linear pitch slide."""
    x = t(dur)
    f = np.full_like(x, float(freq)) if glide is None else np.linspace(freq, glide, x.size)
    phase = 2 * np.pi * np.cumsum(f) / SR
    if shape == "sine":
        return np.sin(phase)
    if shape == "square":
        return np.sign(np.sin(phase)) * 0.6
    if shape == "triangle":
        return 2 / np.pi * np.arcsin(np.sin(phase))
    if shape == "saw":  # two detuned saws would alias; a soft 6-partial saw does not
        return sum(np.sin(k * phase) / k for k in range(1, 7)) * 0.55
    raise ValueError(shape)


def bell(freq, dur, ratio=3.01, index=2.0, curve=5.0):
    """Two-operator FM bell: the modulation dies faster than the note."""
    x = t(dur)
    mod = np.sin(2 * np.pi * freq * ratio * x) * index * np.exp(-9 * x / dur)
    return np.sin(2 * np.pi * freq * x + mod) * env(dur, 0.003, curve=curve)


def noise(dur, lo=None, hi=None):
    """White noise, optionally band-limited with one-pole filters."""
    n = rng.standard_normal(int(SR * dur))
    if hi:  # low-pass
        a = np.exp(-2 * np.pi * hi / SR)
        out = np.empty_like(n)
        acc = 0.0
        for i, v in enumerate(n):
            acc = (1 - a) * v + a * acc
            out[i] = acc
        n = out
    if lo:  # high-pass = signal minus its low-pass
        a = np.exp(-2 * np.pi * lo / SR)
        out = np.empty_like(n)
        acc = 0.0
        for i, v in enumerate(n):
            acc = (1 - a) * v + a * acc
            out[i] = v - acc
        n = out
    return n / (np.max(np.abs(n)) + 1e-9)


def seq(*parts):
    """Lay (start_seconds, samples) parts onto one buffer."""
    end = max(start + p.size / SR for start, p in parts)
    out = np.zeros(int(SR * end) + 1)
    for start, p in parts:
        i = int(SR * start)
        out[i:i + p.size] += p
    return out


def note(n):
    """MIDI note number -> Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


# --------------------------------------------------------------------------
# pulse - short synth plucks: a soft saw with a sine underneath and a small
# upward pitch settle. Pairs with Proton Neon; the default set.
# --------------------------------------------------------------------------
def pulse():
    def pluck(n, dur, curve=6.0, bend=0.985):
        f = note(n)
        body = osc(f * bend, dur, "saw", glide=f) * 0.5 + osc(f, dur) * 0.7
        return body * env(dur, 0.003, curve=curve)

    return {
        "click": pluck(76, 0.11, 7),
        "back": pluck(69, 0.12, 7, bend=1.02),
        "toggle_on": seq((0, pluck(72, 0.09, 7)), (0.07, pluck(79, 0.14, 6))),
        "toggle_off": seq((0, pluck(79, 0.09, 7)), (0.07, pluck(72, 0.14, 6))),
        "slider": pluck(88, 0.045, 9) * 0.6,
        "success": seq((0, pluck(72, 0.12)), (0.09, pluck(79, 0.12)), (0.18, pluck(84, 0.34, 4))),
        "error": seq((0, pluck(57, 0.18, 4, bend=1.03)), (0.16, pluck(53, 0.28, 4, bend=1.03))),
        "notification": seq((0, pluck(81, 0.13)), (0.12, pluck(88, 0.32, 4))),
    }


# --------------------------------------------------------------------------
# glass - soft FM bells and rounded sines, longer tails, nothing sharp.
# Pairs with Soft Glass.
# --------------------------------------------------------------------------
def glass():
    def soft(n, dur, curve=5.0):
        return osc(note(n), dur) * env(dur, 0.008, curve=curve)

    return {
        "click": bell(note(81), 0.22, 2.0, 1.2),
        "back": bell(note(74), 0.2, 2.0, 1.0),
        "toggle_on": seq((0, bell(note(76), 0.16, 2.0, 1.0)), (0.09, bell(note(83), 0.18, 2.0, 1.0))),
        "toggle_off": seq((0, bell(note(83), 0.16, 2.0, 1.0)), (0.09, bell(note(76), 0.18, 2.0, 1.0))),
        "slider": soft(93, 0.07, 9) * 0.6,
        "success": seq((0, bell(note(76), 0.3, 3.01, 1.6)), (0.1, bell(note(81), 0.3, 3.01, 1.6)),
                       (0.2, bell(note(88), 0.38, 3.01, 1.8, 4))),
        "error": seq((0, bell(note(58), 0.22, 1.41, 2.4)), (0.16, bell(note(57), 0.28, 1.41, 2.4))),
        "notification": seq((0, bell(note(84), 0.26, 3.01, 1.5)), (0.14, bell(note(91), 0.38, 3.01, 1.5, 4))),
    }


# --------------------------------------------------------------------------
# terminal - relay ticks, short noise clicks and terse low beeps: a machine
# room, not a melody. Pairs with Phosphor Console.
# --------------------------------------------------------------------------
def terminal():
    def tick(dur=0.03, lo=1800, hi=7000, curve=10):
        return noise(dur, lo, hi) * env(dur, 0.0005, curve=curve)

    def thump(freq, dur, curve=7):
        return osc(freq, dur, glide=freq * 0.6) * env(dur, 0.001, curve=curve)

    def beep(freq, dur, curve=3.5):
        return osc(freq, dur, "square") * env(dur, 0.002, curve=curve) * 0.7

    return {
        "click": seq((0, tick(0.035)), (0, thump(220, 0.09)), (0.06, beep(880, 0.07, 6) * 0.5)),
        "back": seq((0, tick(0.035, 1200, 5000)), (0, thump(160, 0.11))),
        "toggle_on": seq((0, tick(0.03)), (0, thump(180, 0.06)), (0.09, tick(0.03, 2500, 9000)),
                         (0.09, beep(660, 0.1, 5) * 0.5)),
        "toggle_off": seq((0, tick(0.03, 2500, 9000)), (0, beep(660, 0.07, 6) * 0.5),
                          (0.09, tick(0.03)), (0.09, thump(150, 0.09))),
        "slider": tick(0.02, 4000, 10000) * 0.6,
        "success": seq((0, tick(0.03)), (0, beep(523.25, 0.09)), (0.11, beep(659.25, 0.09)),
                       (0.22, beep(1046.5, 0.22, 4))),
        "error": seq((0, tick(0.04, 600, 3000)), (0, beep(196, 0.14, 2.5)), (0.17, beep(185, 0.22, 2.5))),
        "notification": seq((0, tick(0.03)), (0, beep(880, 0.09)), (0.14, beep(880, 0.09)), (0.28, beep(1174.7, 0.16, 4))),
    }


SETS = {"pulse": pulse, "glass": glass, "terminal": terminal}


def write_wav(samples, path, mean_db):
    samples = np.asarray(samples, dtype=np.float64)
    samples = samples - np.mean(samples)
    rms = np.sqrt(np.mean(samples ** 2))
    peak = np.max(np.abs(samples))
    # Match the type's average level; never exceed the peak cap.
    gain = min(10 ** (mean_db / 20) / rms, 10 ** (PEAK_DB / 20) / peak)
    pcm = (np.clip(samples * gain, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    wanted = sys.argv[1:] or list(SETS)
    for name in wanted:
        out = ROOT / name
        out.mkdir(parents=True, exist_ok=True)
        for sound, samples in SETS[name]().items():
            write_wav(samples, out / f"{sound}.wav", MEAN_DB[sound])
        print(f"{name}: {len(list(out.glob('*.wav')))} files -> {out}")


if __name__ == "__main__":
    main()
