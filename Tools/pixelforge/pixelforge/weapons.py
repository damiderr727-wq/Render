"""Weapon sprites.

Guns are drawn in side view facing right and rotated by the renderer to point
at the crosshair, so each one ships two anchors alongside its pixels:

* ``pivot``  — the grip, which is pinned to the character's hand
* ``muzzle`` — where bullets and the muzzle flash spawn

Getting those two points right matters more than the pixels: a flash that
starts half a barrel behind the tip is the single most obvious way for a
shooter to feel wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .canvas import Canvas
from .palette import (
    ARCANE, BONE, COPPER, FIRE, GOLD, ICE, METAL, PLASMA, RGBA, Ramp, RUBBER,
    SOLAR, STEEL, TOXIC, VOID, WOOD, with_alpha,
)
from .shapes import capsule, gradient_disc, ring, rounded_rect, soft_glow, star

OUTLINE: RGBA = (12, 10, 16, 240)


@dataclass
class WeaponArt:
    name: str
    canvas: Canvas
    pivot: tuple[int, int]
    muzzle: tuple[int, int]

    def to_meta(self) -> dict:
        return {"pivot": list(self.pivot), "muzzle": list(self.muzzle)}


def _grip(c: Canvas, x: int, y: int, w: int, h: int, ramp: Ramp,
          angle: int = 2) -> None:
    """Slanted pistol grip. ``angle`` shears the bottom backwards."""
    for row in range(h):
        off = int(row * angle / max(1, h))
        c.hline(x - off, y + row, w, ramp[2])
        c.put(x - off, y + row, ramp[3])
        c.put(x - off + w - 1, y + row, ramp[1])


def _barrel(c: Canvas, x: int, y: int, w: int, h: int, ramp: Ramp) -> None:
    c.rect(x, y, w, h, ramp[2])
    c.hline(x, y, w, ramp[4])
    c.hline(x, y + h - 1, w, ramp[1])


def peacemaker() -> WeaponArt:
    """Starter revolver. Reliable, high crit, low fire rate."""
    c = Canvas(26, 16)
    _grip(c, 5, 8, 5, 7, WOOD, angle=3)
    rounded_rect(c, 4, 4, 12, 5, METAL[3], radius=1)
    _barrel(c, 15, 5, 9, 3, METAL)
    c.disc(11, 6.5, 3.0, METAL[2])
    ring(c, 11, 6.5, 2.0, 1.0, METAL[4])
    for k in range(5):
        a = k * math.tau / 5
        c.put(11 + math.cos(a) * 2, 6.5 + math.sin(a) * 2, METAL[0])
    c.rect(14, 3, 2, 2, GOLD[3])
    c.put(23, 4, METAL[4])
    c.outline(OUTLINE)
    return WeaponArt("peacemaker", c, (7, 11), (25, 6))


def scattergun() -> WeaponArt:
    """Double-barrel. Wide cone, brutal up close."""
    c = Canvas(30, 16)
    _grip(c, 6, 8, 5, 7, WOOD, angle=3)
    rounded_rect(c, 4, 5, 13, 6, WOOD[2], radius=1)
    c.hline(5, 5, 11, WOOD[3])
    _barrel(c, 16, 4, 13, 3, METAL)
    _barrel(c, 16, 8, 13, 3, METAL)
    c.rect(15, 3, 3, 9, METAL[4])
    c.rect(28, 3, 2, 9, METAL[1])
    c.rect(10, 7, 4, 2, COPPER[3])
    c.outline(OUTLINE)
    return WeaponArt("scattergun", c, (8, 11), (29, 6))


def ripper() -> WeaponArt:
    """Machine pistol. Sprays, climbs, empties fast."""
    c = Canvas(26, 18)
    _grip(c, 7, 8, 4, 7, RUBBER, angle=2)
    rounded_rect(c, 4, 3, 15, 6, STEEL[2], radius=1)
    c.hline(5, 3, 13, STEEL[4])
    _barrel(c, 18, 4, 7, 3, METAL)
    for x in range(19, 24, 2):
        c.vline(x, 4, 3, METAL[1])
    rounded_rect(c, 10, 9, 4, 8, METAL[2], radius=1)
    c.vline(11, 10, 6, METAL[4])
    c.rect(4, 1, 4, 2, STEEL[3])
    c.rect(15, 1, 3, 2, STEEL[3])
    c.outline(OUTLINE)
    return WeaponArt("ripper", c, (9, 11), (25, 5))


def longarm() -> WeaponArt:
    """Marksman rifle. One shot, one very large number."""
    c = Canvas(38, 16)
    _grip(c, 10, 8, 4, 7, WOOD, angle=2)
    rounded_rect(c, 2, 6, 14, 5, WOOD[2], radius=2)
    c.hline(3, 6, 12, WOOD[3])
    rounded_rect(c, 14, 5, 10, 5, METAL[3], radius=1)
    _barrel(c, 23, 6, 14, 3, METAL)
    c.rect(35, 5, 2, 5, METAL[3])
    # scope
    rounded_rect(c, 15, 1, 9, 4, METAL[1], radius=1)
    c.hline(16, 1, 7, METAL[3])
    c.rect(22, 2, 2, 2, (140, 220, 255, 255))
    c.vline(16, 5, 1, METAL[2])
    c.vline(22, 5, 1, METAL[2])
    c.outline(OUTLINE)
    return WeaponArt("longarm", c, (12, 11), (37, 7))


def hexbolt() -> WeaponArt:
    """Wand. Slow arcane bolts that seek a little."""
    c = Canvas(26, 16)
    _grip(c, 5, 7, 4, 8, WOOD, angle=1)
    rounded_rect(c, 4, 5, 14, 4, WOOD[2], radius=1)
    c.hline(5, 5, 12, WOOD[3])
    for x in range(7, 17, 3):
        c.put(x, 6, ARCANE[3])
    # crystal head
    star(c, 21, 7, 5, 2.2, 4, ARCANE[3])
    star(c, 21, 7, 3, 1.4, 4, ARCANE[4])
    soft_glow(c, 21, 7, 7, with_alpha(ARCANE[4], 120))
    c.outline(OUTLINE)
    return WeaponArt("hexbolt", c, (7, 11), (25, 7))


def thumper() -> WeaponArt:
    """Grenade launcher. Arcing shells, generous splash."""
    c = Canvas(30, 18)
    _grip(c, 6, 9, 5, 8, RUBBER, angle=3)
    rounded_rect(c, 4, 5, 14, 7, METAL[2], radius=2)
    c.hline(5, 5, 12, METAL[4])
    c.disc(11, 9, 4.0, METAL[3])
    ring(c, 11, 9, 2.6, 1.2, METAL[1])
    c.disc(11, 9, 1.4, COPPER[3])
    rounded_rect(c, 17, 4, 12, 8, METAL[3], radius=2)
    c.rect(28, 3, 2, 10, METAL[1])
    c.hline(18, 4, 10, METAL[4])
    c.rect(20, 6, 6, 4, (20, 18, 24, 255))
    c.outline(OUTLINE)
    return WeaponArt("thumper", c, (8, 13), (30, 8))


def arc_coil() -> WeaponArt:
    """Tesla coil. Chains between targets."""
    c = Canvas(28, 18)
    _grip(c, 6, 9, 4, 8, RUBBER, angle=2)
    rounded_rect(c, 4, 6, 13, 6, STEEL[2], radius=1)
    c.hline(5, 6, 11, STEEL[4])
    for x in range(17, 24, 3):
        c.rect(x, 5, 2, 8, COPPER[3])
        c.hline(x, 5, 2, COPPER[4])
        c.hline(x, 12, 2, COPPER[1])
    c.rect(24, 7, 3, 4, METAL[3])
    for k in range(4):
        a = k * math.tau / 4 + 0.4
        c.put(26 + math.cos(a) * 3, 9 + math.sin(a) * 3, PLASMA[4])
    soft_glow(c, 26, 9, 6, with_alpha(PLASMA[4], 130))
    c.rect(8, 3, 6, 3, PLASMA[2])
    c.hline(9, 3, 4, PLASMA[4])
    c.outline(OUTLINE)
    return WeaponArt("arc_coil", c, (8, 13), (27, 9))


def flamer() -> WeaponArt:
    """Flamethrower. Short range, applies burn."""
    c = Canvas(30, 18)
    _grip(c, 7, 9, 5, 8, RUBBER, angle=3)
    rounded_rect(c, 5, 6, 15, 6, COPPER[2], radius=2)
    c.hline(6, 6, 13, COPPER[4])
    c.rect(6, 10, 13, 2, COPPER[1])
    rounded_rect(c, 2, 3, 7, 9, METAL[2], radius=2)
    c.hline(3, 3, 5, METAL[4])
    c.rect(4, 6, 3, 4, FIRE[2])
    _barrel(c, 19, 7, 9, 4, METAL)
    ring(c, 28, 9, 2.6, 1.4, METAL[4])
    c.rect(21, 5, 2, 2, FIRE[3])
    soft_glow(c, 28, 9, 5, with_alpha(FIRE[4], 110))
    c.outline(OUTLINE)
    return WeaponArt("flamer", c, (9, 13), (30, 9))


def cryo_lance() -> WeaponArt:
    """Continuous beam that chills and eventually freezes."""
    c = Canvas(32, 16)
    _grip(c, 7, 8, 4, 7, STEEL, angle=2)
    rounded_rect(c, 4, 5, 16, 6, ICE[1], radius=2)
    c.hline(5, 5, 14, ICE[3])
    c.rect(8, 7, 8, 3, ICE[4])
    for x in range(9, 16, 2):
        c.vline(x, 7, 3, ICE[2])
    rounded_rect(c, 19, 6, 8, 4, METAL[3], radius=1)
    for k in range(3):
        px = 27 + k
        c.vline(px, 5 + k, 6 - k * 2, ICE[4])
    soft_glow(c, 29, 8, 6, with_alpha(ICE[4], 120))
    c.outline(OUTLINE)
    return WeaponArt("cryo_lance", c, (9, 11), (31, 8))


def nail_driver() -> WeaponArt:
    """Nailgun. Nails stick in walls, then detonate with the right synergy."""
    c = Canvas(28, 18)
    _grip(c, 7, 9, 5, 8, WOOD, angle=2)
    rounded_rect(c, 4, 5, 14, 7, COPPER[2], radius=1)
    c.hline(5, 5, 12, COPPER[4])
    c.rect(5, 10, 12, 2, COPPER[1])
    rounded_rect(c, 9, 1, 8, 4, METAL[2], radius=1)
    for x in range(10, 16, 2):
        c.vline(x, 1, 4, METAL[4])
    _barrel(c, 17, 7, 10, 3, METAL)
    c.rect(26, 7, 2, 3, METAL[4])
    c.outline(OUTLINE)
    return WeaponArt("nail_driver", c, (9, 13), (28, 8))


def bone_saw() -> WeaponArt:
    """Thrown blade that boomerangs back. Melee-adjacent, infinite ammo."""
    c = Canvas(24, 20)
    _grip(c, 4, 8, 4, 9, BONE, angle=1)
    rounded_rect(c, 3, 6, 9, 4, BONE[2], radius=1)
    c.hline(4, 6, 7, BONE[4])
    c.disc(16, 10, 7.0, METAL[2])
    c.disc(16, 10, 5.0, METAL[3])
    c.disc(16, 10, 2.0, METAL[1])
    for k in range(8):
        a = k * math.tau / 8
        c.rect(16 + math.cos(a) * 7 - 1, 10 + math.sin(a) * 7 - 1, 2, 2,
               METAL[4])
    c.outline(OUTLINE)
    return WeaponArt("bone_saw", c, (6, 12), (23, 10))


def star_caller() -> WeaponArt:
    """Fires slow homing motes that orbit before striking."""
    c = Canvas(26, 18)
    _grip(c, 5, 8, 4, 8, VOID, angle=1)
    rounded_rect(c, 4, 6, 12, 4, VOID[2], radius=1)
    c.hline(5, 6, 10, VOID[3])
    ring(c, 20, 8, 5.0, 1.6, GOLD[3])
    ring(c, 20, 8, 5.0, 0.8, GOLD[4])
    star(c, 20, 8, 3, 1.2, 5, SOLAR[4])
    for k in range(3):
        a = k * math.tau / 3
        c.disc(20 + math.cos(a) * 5, 8 + math.sin(a) * 5, 1.2, SOLAR[3])
    soft_glow(c, 20, 8, 8, with_alpha(SOLAR[4], 100))
    c.outline(OUTLINE)
    return WeaponArt("star_caller", c, (7, 12), (25, 8))


def hand_cannon() -> WeaponArt:
    """Enormous single shot with knockback that moves *you*."""
    c = Canvas(32, 18)
    _grip(c, 7, 9, 6, 8, WOOD, angle=3)
    rounded_rect(c, 4, 4, 16, 8, METAL[2], radius=2)
    c.hline(5, 4, 14, METAL[4])
    c.rect(5, 10, 14, 2, METAL[1])
    _barrel(c, 19, 5, 12, 6, METAL)
    c.rect(30, 4, 2, 8, METAL[1])
    ring(c, 30, 8, 2.6, 1.2, METAL[4])
    c.rect(11, 6, 6, 3, GOLD[2])
    c.hline(11, 6, 6, GOLD[4])
    c.outline(OUTLINE)
    return WeaponArt("hand_cannon", c, (9, 13), (32, 8))


def plague_censer() -> WeaponArt:
    """Swings a censer that leaves lingering poison clouds."""
    c = Canvas(24, 22)
    _grip(c, 4, 4, 4, 9, WOOD, angle=1)
    c.line(7, 5, 15, 5, METAL[3])
    for k in range(4):
        c.vline(15 + k, 5, 3 + k, METAL[2])
    rounded_rect(c, 13, 10, 9, 8, COPPER[2], radius=2)
    c.hline(14, 10, 7, COPPER[4])
    for y in range(12, 17, 2):
        c.hline(14, y, 7, COPPER[1])
    c.rect(16, 13, 3, 3, TOXIC[3])
    soft_glow(c, 17, 15, 6, with_alpha(TOXIC[4], 110))
    c.disc(17, 19, 1.6, TOXIC[2])
    c.outline(OUTLINE)
    return WeaponArt("plague_censer", c, (6, 12), (23, 15))


def void_needle() -> WeaponArt:
    """Hitscan lance that pierces every enemy in a line."""
    c = Canvas(34, 14)
    _grip(c, 6, 7, 4, 7, VOID, angle=2)
    rounded_rect(c, 4, 4, 15, 5, VOID[2], radius=1)
    c.hline(5, 4, 13, VOID[3])
    c.rect(7, 6, 9, 2, ARCANE[3])
    c.hline(7, 6, 9, ARCANE[4])
    for k in range(14):
        y = 6 - k // 8
        c.put(19 + k, y, ARCANE[4] if k % 3 else ARCANE[3])
        c.put(19 + k, y + 1, VOID[1])
    c.put(33, 5, (255, 255, 255, 255))
    soft_glow(c, 32, 6, 5, with_alpha(ARCANE[4], 120))
    c.outline(OUTLINE)
    return WeaponArt("void_needle", c, (8, 10), (34, 6))


def sunburst() -> WeaponArt:
    """Charges, then releases a ring of bolts in every direction."""
    c = Canvas(26, 20)
    _grip(c, 5, 9, 4, 8, GOLD, angle=2)
    rounded_rect(c, 4, 7, 11, 5, GOLD[1], radius=1)
    c.hline(5, 7, 9, GOLD[3])
    gradient_disc(c, 19, 9, 6.0, SOLAR, 4, 1)
    for k in range(8):
        a = k * math.tau / 8
        c.line(19 + math.cos(a) * 6, 9 + math.sin(a) * 6,
               19 + math.cos(a) * 8, 9 + math.sin(a) * 8, SOLAR[4])
    soft_glow(c, 19, 9, 10, with_alpha(SOLAR[4], 110))
    c.outline(OUTLINE)
    return WeaponArt("sunburst", c, (7, 13), (25, 9))


ALL_WEAPONS = (
    peacemaker, scattergun, ripper, longarm, hexbolt, thumper, arc_coil,
    flamer, cryo_lance, nail_driver, bone_saw, star_caller, hand_cannon,
    plague_censer, void_needle, sunburst,
)


def build_weapons() -> list[WeaponArt]:
    return [fn() for fn in ALL_WEAPONS]
