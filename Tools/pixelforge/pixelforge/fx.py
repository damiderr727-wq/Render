"""Projectiles and effects.

Bullets are drawn facing right and rotated by the renderer. In a bullet hell
the projectile sprite is doing real work: it has to stay readable against a
busy floor, against other bullets, and at a glance while you are dodging, so
every one of these is a bright core wrapped in a darker rim and given a
distinctive silhouette rather than being a coloured dot.
"""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .palette import (
    ARCANE, BLOOD, BONE, FIRE, GOLD, ICE, METAL, PLASMA, RGBA, Ramp, SOLAR,
    STEEL, TOXIC, VOID, with_alpha,
)
from .shapes import capsule, gradient_disc, ring, rounded_rect, soft_glow, star


# ---------------------------------------------------------------------------
# projectiles
# ---------------------------------------------------------------------------


def bolt(ramp: Ramp, length: int = 10, width: int = 6) -> Canvas:
    """Standard tapered bullet: hot core, cooler tail."""
    c = Canvas(length + 4, width + 4)
    cy = (width + 4) / 2.0
    for x in range(length):
        t = x / max(1, length - 1)
        half = (width / 2.0) * (0.35 + 0.65 * math.sin(t * math.pi) ** 0.6)
        c.vline(2 + x, cy - half, max(1, half * 2), ramp[2])
    for x in range(length - 2):
        t = x / max(1, length - 3)
        half = (width / 2.0 - 1) * (0.3 + 0.7 * math.sin(t * math.pi) ** 0.6)
        if half >= 0.5:
            c.vline(3 + x, cy - half, max(1, half * 2), ramp[4])
    c.hline(length - 2, cy - 0.5, 3, (255, 255, 255, 230))
    soft_glow(c, 2 + length * 0.6, cy, width, with_alpha(ramp[4], 70))
    return c


def pellet(ramp: Ramp, radius: int = 3) -> Canvas:
    size = radius * 2 + 4
    c = Canvas(size, size)
    gradient_disc(c, size / 2.0, size / 2.0, radius, ramp, 4, 1)
    c.put(size / 2.0 - 1, size / 2.0 - 1, (255, 255, 255, 220))
    soft_glow(c, size / 2.0, size / 2.0, radius + 2, with_alpha(ramp[4], 80))
    return c


def orb(ramp: Ramp, radius: int = 5) -> Canvas:
    """Big slow projectile — the kind you weave between."""
    size = radius * 2 + 6
    c = Canvas(size, size)
    cx = cy = size / 2.0
    c.disc(cx, cy, radius + 1, with_alpha(ramp[0], 200))
    gradient_disc(c, cx, cy, radius, ramp, 4, 1)
    ring(c, cx, cy, radius - 0.5, 1.0, with_alpha(ramp[4], 200))
    c.disc(cx - radius * 0.3, cy - radius * 0.3, radius * 0.3,
           (255, 255, 255, 210))
    soft_glow(c, cx, cy, radius + 4, with_alpha(ramp[4], 90))
    return c


def shard(ramp: Ramp) -> Canvas:
    """Ice/glass sliver."""
    c = Canvas(14, 8)
    c.polygon([(1, 4), (5, 1), (13, 4), (5, 7)], ramp[2])
    c.polygon([(3, 4), (6, 2), (11, 4), (6, 6)], ramp[4])
    c.line(4, 4, 11, 4, (255, 255, 255, 200))
    return c


def nail(ramp: Ramp) -> Canvas:
    c = Canvas(14, 6)
    c.rect(1, 2, 9, 2, ramp[2])
    c.hline(1, 2, 9, ramp[4])
    c.polygon([(10, 1), (13, 3), (10, 5)], ramp[3])
    c.rect(0, 1, 2, 4, ramp[1])
    return c


def grenade(ramp: Ramp) -> Canvas:
    c = Canvas(12, 12)
    c.disc(6, 7, 4.0, ramp[2])
    c.disc(5, 6, 2.6, ramp[3])
    c.disc(4.5, 5.5, 1.2, ramp[4])
    c.rect(5, 2, 3, 3, METAL[3])
    c.hline(5, 2, 3, METAL[4])
    c.vline(7, 0, 3, FIRE[3])
    soft_glow(c, 7, 0, 3, with_alpha(FIRE[4], 150))
    return c


def saw(ramp: Ramp, count: int = 4) -> list[Canvas]:
    """Spinning blade — the frames *are* the rotation."""
    frames = []
    for i in range(count):
        c = Canvas(18, 18)
        c.disc(9, 9, 6.0, ramp[2])
        c.disc(9, 9, 4.0, ramp[3])
        c.disc(9, 9, 1.8, ramp[1])
        for k in range(6):
            a = k * math.tau / 6 + i * math.tau / (6 * count)
            c.polygon([
                (round(9 + math.cos(a) * 5), round(9 + math.sin(a) * 5)),
                (round(9 + math.cos(a + 0.35) * 8), round(9 + math.sin(a + 0.35) * 8)),
                (round(9 + math.cos(a + 0.7) * 5), round(9 + math.sin(a + 0.7) * 5)),
            ], ramp[4])
        c.outline((14, 12, 18, 230))
        frames.append(c)
    return frames


def beam_segment(ramp: Ramp) -> Canvas:
    """One tile of a continuous beam; the renderer stretches it."""
    c = Canvas(8, 10)
    c.rect(0, 2, 8, 6, with_alpha(ramp[2], 210))
    c.rect(0, 3, 8, 4, ramp[3])
    c.rect(0, 4, 8, 2, (255, 255, 255, 235))
    c.hline(0, 1, 8, with_alpha(ramp[4], 120))
    c.hline(0, 8, 8, with_alpha(ramp[4], 120))
    return c


def beam_tip(ramp: Ramp) -> Canvas:
    c = Canvas(12, 12)
    gradient_disc(c, 5, 6, 5.0, ramp, 4, 1)
    c.disc(5, 6, 2.0, (255, 255, 255, 240))
    for k in range(6):
        a = k * math.tau / 6
        c.line(5, 6, round(5 + math.cos(a) * 6), round(6 + math.sin(a) * 6),
               with_alpha(ramp[4], 150))
    return c


def flame_puff(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(18, 18)
        r = 3 + t * 5
        gradient_disc(c, 9, 9, r, FIRE, 4 if t < 0.5 else 3, 1)
        rng = random.Random(i * 7)
        for _ in range(int(6 * (1 - t) + 2)):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(r * 0.5, r + 2)
            c.put(9 + math.cos(a) * d, 9 + math.sin(a) * d,
                  with_alpha(FIRE[3], 200))
        soft_glow(c, 9, 9, r + 4, with_alpha(FIRE[4], int(120 * (1 - t))))
        frames.append(c)
    return frames


PROJECTILES: dict[str, object] = {
    "bolt_player": (bolt, (SOLAR, 10, 6)),
    "bolt_heavy": (bolt, (GOLD, 14, 8)),
    "bolt_enemy": (bolt, (BLOOD, 9, 6)),
    "bolt_arcane": (bolt, (ARCANE, 11, 7)),
    "bolt_toxic": (bolt, (TOXIC, 10, 6)),
    "pellet_player": (pellet, (SOLAR, 3)),
    "pellet_enemy": (pellet, (ARCANE, 3)),
    "pellet_small": (pellet, (PLASMA, 2)),
    "orb_enemy": (orb, (BLOOD, 5)),
    "orb_void": (orb, (VOID, 6)),
    "orb_plasma": (orb, (PLASMA, 5)),
    "shard_ice": (shard, (ICE,)),
    "shard_bone": (shard, (BONE,)),
    "nail": (nail, (STEEL,)),
    "grenade": (grenade, (METAL,)),
    "beam_seg_ice": (beam_segment, (ICE,)),
    "beam_seg_void": (beam_segment, (ARCANE,)),
    "beam_tip_ice": (beam_tip, (ICE,)),
    "beam_tip_void": (beam_tip, (ARCANE,)),
}


def build_projectiles() -> dict[str, list[Canvas]]:
    out: dict[str, list[Canvas]] = {}
    for name, (fn, args) in PROJECTILES.items():
        out[name] = [fn(*args)]
    out["saw"] = saw(METAL)
    out["flame_puff"] = flame_puff()
    return out


# ---------------------------------------------------------------------------
# effects
# ---------------------------------------------------------------------------


def muzzle_flash(count: int = 3) -> list[Canvas]:
    """Points right, anchored at the muzzle. Short and bright."""
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(20, 16)
        scale = 1.0 - t * 0.55
        cx, cy = 3.0, 8.0
        for k in range(5):
            a = (k - 2) * 0.42
            ln = (12 - abs(k - 2) * 3) * scale
            c.line(cx, cy, cx + math.cos(a) * ln, cy + math.sin(a) * ln,
                   with_alpha(SOLAR[3], int(230 * (1 - t))))
        gradient_disc(c, cx + 2 * scale, cy, 5 * scale, SOLAR, 4, 2)
        c.disc(cx + 1, cy, 2 * scale, (255, 255, 250, 240))
        soft_glow(c, cx + 3, cy, 9 * scale, with_alpha(SOLAR[4], int(140 * (1 - t))))
        frames.append(c)
    return frames


def impact_spark(ramp: Ramp = SOLAR, count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(16, 16)
        rng = random.Random(3)
        for k in range(7):
            a = rng.uniform(0, math.tau)
            d0 = 1 + t * 5
            d1 = d0 + 2.5 * (1 - t) + 1
            c.line(8 + math.cos(a) * d0, 8 + math.sin(a) * d0,
                   8 + math.cos(a) * d1, 8 + math.sin(a) * d1,
                   with_alpha(ramp[4], int(240 * (1 - t))))
        c.disc(8, 8, 3 * (1 - t), with_alpha(ramp[3], 220))
        frames.append(c)
    return frames


def explosion(count: int = 6, size: int = 40) -> list[Canvas]:
    """Big, orange, and gone in a third of a second."""
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(size, size)
        cx = cy = size / 2.0
        r = size * 0.5 * (0.25 + 0.75 * math.sqrt(t))
        rng = random.Random(11 + i)
        # billowing lobes
        for k in range(7):
            a = k * math.tau / 7 + t * 0.6
            d = r * (0.45 + 0.25 * rng.random())
            lr = r * (0.42 - t * 0.15) + 2
            col = FIRE[4] if t < 0.35 else FIRE[3] if t < 0.7 else FIRE[1]
            c.disc(cx + math.cos(a) * d, cy + math.sin(a) * d, lr,
                   with_alpha(col, int(240 - t * 120)))
        if t < 0.6:
            gradient_disc(c, cx, cy, r * 0.55, FIRE, 4, 2)
            c.disc(cx, cy, r * 0.22, (255, 252, 230, 250))
        else:
            for k in range(9):
                a = rng.uniform(0, math.tau)
                d = r * rng.uniform(0.5, 1.0)
                c.disc(cx + math.cos(a) * d, cy + math.sin(a) * d,
                       2.5 * (1 - t) + 1, with_alpha((60, 50, 58, 200), 150))
        ring(c, cx, cy, r, 1.2, with_alpha(SOLAR[4], int(200 * (1 - t))))
        soft_glow(c, cx, cy, r + 6, with_alpha(FIRE[4], int(120 * (1 - t))))
        frames.append(c)
    return frames


def smoke_puff(count: int = 5) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(20, 20)
        rng = random.Random(5)
        for k in range(4):
            a = k * math.tau / 4 + t
            d = t * 5
            c.disc(10 + math.cos(a) * d, 10 + math.sin(a) * d - t * 3,
                   4 * (1 - t * 0.4), (86, 80, 96, int(170 * (1 - t))))
        frames.append(c)
    return frames


def dust_ring(count: int = 4) -> list[Canvas]:
    """Kicked up by a dodge roll and by anything landing."""
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(28, 14)
        r = 4 + t * 9
        ring(c, 14, 8, r, 1.6, (150, 140, 155, int(190 * (1 - t))))
        for k in range(6):
            a = k * math.tau / 6 + t
            c.disc(14 + math.cos(a) * r, 8 + math.sin(a) * r * 0.45,
                   2 * (1 - t) + 0.8, (170, 162, 178, int(180 * (1 - t))))
        frames.append(c)
    return frames


def blood_splat(ramp: Ramp = BLOOD, count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(20, 20)
        rng = random.Random(17)
        for k in range(9):
            a = rng.uniform(0, math.tau)
            d = (2 + t * 7) * rng.uniform(0.4, 1.0)
            c.disc(10 + math.cos(a) * d, 10 + math.sin(a) * d,
                   2.4 * (1 - t * 0.5), with_alpha(ramp[2], int(230 - t * 60)))
        c.disc(10, 10, 3.5 * (1 - t * 0.4), ramp[1])
        frames.append(c)
    return frames


def heal_sparkle(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(20, 24)
        for k in range(4):
            a = k * math.tau / 4 + t * 2
            px = 10 + math.cos(a) * (6 - t * 3)
            py = 18 - t * 14 + math.sin(a) * 2
            star(c, px, py, 2.5 * (1 - t * 0.5), 1.0, 4,
                 with_alpha((150, 255, 190, 255), int(240 * (1 - t))))
        frames.append(c)
    return frames


def pickup_shine(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / count
        c = Canvas(20, 20)
        star(c, 10, 10, 3 + math.sin(t * math.tau) * 2, 1.2, 4,
             with_alpha(SOLAR[4], 220))
        ring(c, 10, 10, 6 + t * 3, 1.0, with_alpha(SOLAR[3], int(150 * (1 - t))))
        frames.append(c)
    return frames


def portal_frames(count: int = 6) -> list[Canvas]:
    """The stairs down. Reads as a hole with something moving in it."""
    frames = []
    for i in range(count):
        t = i / count
        c = Canvas(36, 24)
        cx, cy = 18.0, 12.0
        c.ellipse(cx, cy, 15, 9, (10, 8, 18, 235))
        for k in range(4):
            rr = 13 - k * 3
            phase = t * math.tau + k * 0.9
            for stp in range(40):
                a = stp / 40 * math.tau + phase
                c.put(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.6,
                      ARCANE[4 - (k % 3)])
        gradient_disc(c, cx, cy, 4, ARCANE, 4, 1)
        soft_glow(c, cx, cy, 16, with_alpha(ARCANE[4], 80))
        frames.append(c)
    return frames


def shockwave(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(48, 32)
        # Capped so the widest ring still clears the canvas edge — a clipped
        # ring reads as an octagon, which is worse than a smaller circle.
        r = 6 + t * 8
        ring(c, 24, 16, r, 2.0 * (1 - t) + 0.8,
             with_alpha((235, 240, 255, 255), int(200 * (1 - t))))
        ring(c, 24, 16, r - 2, 1.0, with_alpha(PLASMA[4], int(140 * (1 - t))))
        frames.append(c)
    return frames


def freeze_shatter(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(24, 24)
        rng = random.Random(29)
        for k in range(8):
            a = rng.uniform(0, math.tau)
            d = 2 + t * 9
            px, py = 12 + math.cos(a) * d, 12 + math.sin(a) * d
            c.polygon([(round(px), round(py - 2)), (round(px + 2), round(py)),
                       (round(px), round(py + 2)), (round(px - 2), round(py))],
                      with_alpha(ICE[3], int(230 * (1 - t))))
        if t < 0.4:
            c.disc(12, 12, 5 * (1 - t), with_alpha(ICE[4], 200))
        frames.append(c)
    return frames


def poison_cloud(count: int = 5) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(32, 26)
        rng = random.Random(41)
        for k in range(6):
            a = k * math.tau / 6 + t * 1.5
            d = 4 + t * 6
            c.disc(16 + math.cos(a) * d, 14 + math.sin(a) * d * 0.6,
                   5 - t * 1.5, with_alpha(TOXIC[2], int(120 - t * 40)))
        for _ in range(6):
            c.put(rng.randrange(4, 28), rng.randrange(4, 22),
                  with_alpha(TOXIC[4], 180))
        frames.append(c)
    return frames


def lightning_arc(count: int = 3) -> list[Canvas]:
    """One horizontal span of chain lightning; the renderer scales and
    rotates it between the two ends of a chain."""
    frames = []
    for i in range(count):
        c = Canvas(32, 16)
        rng = random.Random(97 + i)
        y = 8.0
        prev = (0, 8)
        for x in range(0, 33, 4):
            ny = 8 + rng.uniform(-4, 4) * math.sin(x / 32 * math.pi)
            c.line(prev[0], prev[1], x, ny, (255, 255, 255, 240))
            c.line(prev[0], prev[1] + 1, x, ny + 1,
                   with_alpha(PLASMA[4], 190))
            if rng.random() < 0.4:
                bx = x + rng.randint(-3, 3)
                c.line(x, ny, bx, ny + rng.randint(-5, 5),
                       with_alpha(PLASMA[3], 150))
            prev = (x, ny)
        frames.append(c)
    return frames


def teleport_frames(count: int = 4) -> list[Canvas]:
    frames = []
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(24, 28)
        h = 26 * (1 - t)
        w = 3 + t * 8
        c.rect(12 - w / 2, 26 - h, w, h, with_alpha(ARCANE[3], int(220 * (1 - t))))
        c.rect(12 - w / 4, 26 - h, w / 2, h, with_alpha((255, 255, 255, 255),
                                                        int(200 * (1 - t))))
        ring(c, 12, 26, 4 + t * 8, 1.2, with_alpha(ARCANE[4], int(190 * (1 - t))))
        frames.append(c)
    return frames


EFFECTS: dict[str, object] = {
    # Also registered under proj/ — the flamer uses the same art as its
    # projectile, its muzzle flash and its impact.
    "flame_puff": flame_puff,
    "muzzle_flash": muzzle_flash,
    "impact_spark": impact_spark,
    "explosion": explosion,
    "smoke_puff": smoke_puff,
    "dust_ring": dust_ring,
    "blood_splat": blood_splat,
    "heal_sparkle": heal_sparkle,
    "pickup_shine": pickup_shine,
    "portal": portal_frames,
    "shockwave": shockwave,
    "freeze_shatter": freeze_shatter,
    "poison_cloud": poison_cloud,
    "lightning_arc": lightning_arc,
    "teleport": teleport_frames,
}


def build_effects() -> dict[str, list[Canvas]]:
    return {name: fn() for name, fn in EFFECTS.items()}
