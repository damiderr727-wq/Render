#!/usr/bin/env python3
"""Procedural sound effects, generated the same way as the art.

    python3 Tools/pixelforge/soundforge.py --out Assets/generated/sfx

Everything is synthesised from oscillators and envelopes — no samples, no
dependencies beyond the standard library. The point is the same as PixelForge:
a tweak to a sound is a diff, not a binary blob, and the whole soundscape
stays consistent because every effect is built from the same handful of
primitives.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import struct
import wave

RATE = 22050


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def envelope(length: int, attack: float, decay: float, sustain: float,
             release: float) -> list[float]:
    """ADSR over ``length`` samples, with the four stages given as fractions."""
    total = attack + decay + release
    if total > 1.0:
        attack, decay, release = attack / total, decay / total, release / total
    a = max(1, int(length * attack))
    d = max(1, int(length * decay))
    r = max(1, int(length * release))
    s = max(0, length - a - d - r)

    out: list[float] = []
    out += [i / a for i in range(a)]
    out += [1 - (1 - sustain) * (i / d) for i in range(d)]
    out += [sustain] * s
    out += [sustain * (1 - i / r) for i in range(r)]
    return (out + [0.0] * length)[:length]


def sweep(length: int, start: float, end: float, curve: float = 1.0) -> list[float]:
    """Per-sample frequency, swept from ``start`` to ``end``."""
    return [start + (end - start) * ((i / max(1, length - 1)) ** curve)
            for i in range(length)]


def oscillate(freqs: list[float], shape: str, rng: random.Random,
              duty: float = 0.5) -> list[float]:
    """Runs an oscillator over a per-sample frequency track."""
    out: list[float] = []
    phase = 0.0
    for f in freqs:
        phase += f / RATE
        phase -= math.floor(phase)
        if shape == "sine":
            out.append(math.sin(phase * math.tau))
        elif shape == "square":
            out.append(1.0 if phase < duty else -1.0)
        elif shape == "saw":
            out.append(2.0 * phase - 1.0)
        elif shape == "triangle":
            out.append(4 * abs(phase - 0.5) - 1)
        else:  # noise
            out.append(rng.uniform(-1, 1))
    return out


def mix(*layers: list[float]) -> list[float]:
    length = max((len(layer) for layer in layers), default=0)
    out = [0.0] * length
    for layer in layers:
        for i, value in enumerate(layer):
            out[i] += value
    return out


def apply(samples: list[float], env: list[float], gain: float = 1.0) -> list[float]:
    return [s * e * gain for s, e in zip(samples, env)]


def lowpass(samples: list[float], strength: float = 0.5) -> list[float]:
    """One-pole filter. Takes the fizz off noise so it reads as a thump."""
    out: list[float] = []
    previous = 0.0
    for value in samples:
        previous += (value - previous) * (1 - strength)
        out.append(previous)
    return out


def bitcrush(samples: list[float], levels: int = 32) -> list[float]:
    """Quantise the amplitude. The cheapest way to sound like 1994."""
    return [round(s * levels) / levels for s in samples]


def seconds(value: float) -> int:
    return max(1, int(RATE * value))


# ---------------------------------------------------------------------------
# effects
# ---------------------------------------------------------------------------


def pew(rng, length=0.14, start=900, end=180, shape="square",
        gain=0.5) -> list[float]:
    """The generic gunshot: a fast downward sweep with a noise transient."""
    n = seconds(length)
    tone = oscillate(sweep(n, start, end, curve=0.4), shape, rng)
    body = apply(tone, envelope(n, 0.01, 0.2, 0.4, 0.7), gain)
    crack = apply(oscillate([0] * seconds(0.02), "noise", rng),
                  envelope(seconds(0.02), 0.01, 0.4, 0.1, 0.5), gain * 0.7)
    return mix(body, crack)


def boom(rng, length=0.55, gain=0.85) -> list[float]:
    n = seconds(length)
    rumble = oscillate(sweep(n, 160, 34, curve=0.5), "square", rng)
    blast = lowpass(oscillate([0] * n, "noise", rng), 0.72)
    return mix(apply(rumble, envelope(n, 0.005, 0.35, 0.25, 0.6), gain * 0.7),
               apply(blast, envelope(n, 0.002, 0.25, 0.18, 0.75), gain))


def thud(rng, length=0.2, freq=140, gain=0.7) -> list[float]:
    n = seconds(length)
    tone = oscillate(sweep(n, freq, freq * 0.35), "sine", rng)
    return apply(tone, envelope(n, 0.005, 0.3, 0.2, 0.65), gain)


def blip(rng, freqs, step=0.055, shape="square", gain=0.45) -> list[float]:
    """A little arpeggio — pickups, menu confirmations, level-ups."""
    out: list[float] = []
    for freq in freqs:
        n = seconds(step)
        tone = oscillate([freq] * n, shape, rng)
        out += apply(tone, envelope(n, 0.05, 0.2, 0.7, 0.5), gain)
    return out


def whoosh(rng, length=0.26, gain=0.4) -> list[float]:
    n = seconds(length)
    air = lowpass(oscillate([0] * n, "noise", rng), 0.85)
    return apply(air, envelope(n, 0.25, 0.25, 0.5, 0.5), gain)


def zap(rng, length=0.22, gain=0.5) -> list[float]:
    n = seconds(length)
    tone = oscillate(sweep(n, 1400, 300, curve=0.3), "saw", rng)
    fizz = oscillate([0] * n, "noise", rng)
    return mix(apply(tone, envelope(n, 0.005, 0.3, 0.3, 0.6), gain),
               apply(fizz, envelope(n, 0.01, 0.5, 0.1, 0.5), gain * 0.3))


def SOUNDS(rng: random.Random) -> dict[str, list[float]]:
    """Every cue the simulation emits, keyed by the name in `GameEvent.sound`."""
    out: dict[str, list[float]] = {}

    # Weapons — each one gets a timbre that matches how it plays.
    out["shoot_peacemaker"] = pew(rng, 0.16, 1000, 160, "square", 0.55)
    out["shoot_scattergun"] = mix(
        pew(rng, 0.26, 520, 80, "saw", 0.5),
        apply(lowpass(oscillate([0] * seconds(0.26), "noise", rng), 0.6),
              envelope(seconds(0.26), 0.002, 0.3, 0.2, 0.7), 0.6))
    out["shoot_ripper"] = pew(rng, 0.07, 760, 260, "square", 0.32)
    out["shoot_longarm"] = mix(pew(rng, 0.34, 1500, 90, "saw", 0.6),
                               thud(rng, 0.3, 190, 0.4))
    out["shoot_hexbolt"] = blip(rng, [880, 1180], 0.07, "sine", 0.4)
    out["shoot_thumper"] = thud(rng, 0.24, 260, 0.6)
    out["shoot_arc_coil"] = zap(rng, 0.2, 0.45)
    out["shoot_flamer"] = apply(
        lowpass(oscillate([0] * seconds(0.1), "noise", rng), 0.5),
        envelope(seconds(0.1), 0.15, 0.3, 0.6, 0.4), 0.3)
    out["shoot_cryo_lance"] = apply(
        oscillate(sweep(seconds(0.2), 2200, 1400), "sine", rng),
        envelope(seconds(0.2), 0.1, 0.2, 0.7, 0.4), 0.3)
    out["shoot_nail_driver"] = pew(rng, 0.06, 1400, 500, "square", 0.34)
    out["shoot_bone_saw"] = whoosh(rng, 0.3, 0.45)
    out["shoot_star_caller"] = blip(rng, [660, 990, 1320], 0.06, "sine", 0.35)
    out["shoot_hand_cannon"] = mix(boom(rng, 0.4, 0.7), pew(rng, 0.2, 400, 70,
                                                            "saw", 0.5))
    out["shoot_plague_censer"] = mix(
        pew(rng, 0.24, 340, 110, "triangle", 0.4),
        apply(oscillate([0] * seconds(0.24), "noise", rng),
              envelope(seconds(0.24), 0.1, 0.3, 0.3, 0.5), 0.2))
    out["shoot_void_needle"] = mix(
        apply(oscillate(sweep(seconds(0.3), 120, 60), "sine", rng),
              envelope(seconds(0.3), 0.01, 0.2, 0.6, 0.5), 0.5),
        zap(rng, 0.28, 0.3))
    out["shoot_sunburst"] = mix(blip(rng, [520, 780, 1040], 0.05, "square", 0.4),
                                boom(rng, 0.3, 0.4))

    # Combat feedback
    out["enemy_shoot"] = pew(rng, 0.13, 620, 200, "triangle", 0.3)
    out["boss_shoot"] = pew(rng, 0.2, 420, 120, "saw", 0.4)
    out["explosion"] = boom(rng, 0.6, 0.9)
    out["crit"] = blip(rng, [1320, 1760], 0.045, "square", 0.4)
    out["player_hurt"] = mix(pew(rng, 0.24, 420, 90, "saw", 0.5),
                             thud(rng, 0.22, 120, 0.5))
    out["armor_break"] = mix(zap(rng, 0.18, 0.35),
                             blip(rng, [880, 620], 0.05, "square", 0.35))
    out["break"] = apply(lowpass(oscillate([0] * seconds(0.22), "noise", rng), 0.45),
                         envelope(seconds(0.22), 0.005, 0.35, 0.15, 0.6), 0.5)

    # Movement and utility
    out["dodge"] = whoosh(rng, 0.22, 0.38)
    out["dash"] = whoosh(rng, 0.3, 0.45)
    out["blank"] = mix(
        apply(oscillate(sweep(seconds(0.5), 1800, 200, 0.35), "sine", rng),
              envelope(seconds(0.5), 0.004, 0.25, 0.35, 0.7), 0.55),
        boom(rng, 0.45, 0.4))
    out["reload"] = mix(blip(rng, [300], 0.05, "square", 0.35),
                        thud(rng, 0.1, 220, 0.3))
    out["weapon_switch"] = blip(rng, [520, 700], 0.04, "square", 0.3)
    out["pickup"] = blip(rng, [880, 1320], 0.05, "sine", 0.4)
    out["refused"] = blip(rng, [320, 220], 0.07, "square", 0.35)

    # Room and floor beats
    out["doors_close"] = mix(thud(rng, 0.4, 90, 0.7),
                             apply(lowpass(oscillate([0] * seconds(0.4), "noise",
                                                     rng), 0.8),
                                   envelope(seconds(0.4), 0.1, 0.3, 0.3, 0.5), 0.3))
    out["room_cleared"] = blip(rng, [660, 880, 1320], 0.075, "sine", 0.4)
    out["boss_intro"] = mix(
        apply(oscillate(sweep(seconds(1.1), 60, 150, 0.6), "saw", rng),
              envelope(seconds(1.1), 0.25, 0.2, 0.75, 0.35), 0.5),
        boom(rng, 0.9, 0.5))

    return out


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------


def normalise(samples: list[float], peak: float = 0.85) -> list[float]:
    loudest = max((abs(s) for s in samples), default=0.0)
    if loudest < 1e-6:
        return samples
    scale = peak / loudest
    return [s * scale for s in samples]


def write_wav(path: str, samples: list[float]) -> None:
    samples = bitcrush(normalise(samples), levels=48)
    # A few milliseconds of fade at each end; a hard edge clicks.
    fade = min(64, len(samples) // 4)
    for i in range(fade):
        samples[i] *= i / fade
        samples[-1 - i] *= i / fade

    frames = b"".join(
        struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
        for s in samples)
    with wave.open(path, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(RATE)
        fh.writeframes(frames)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="Assets/generated/sfx")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)
    sounds = SOUNDS(rng)

    total = 0
    for name, samples in sounds.items():
        path = os.path.join(args.out, f"{name}.wav")
        write_wav(path, samples)
        total += os.path.getsize(path)

    print(f"wrote {len(sounds)} sounds to {args.out} "
          f"({total // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
