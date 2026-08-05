"""Passive items and pickups.

Every item has to be identifiable from across the room *and* in a 16px HUD
slot, so each one gets a distinct silhouette rather than a distinct colour —
colour alone stops working the moment two items sit on the same rug.
"""

from __future__ import annotations

import math

from .canvas import Canvas
from .palette import (
    ARCANE, BLOOD, BONE, CLOTH_BLUE, CLOTH_RED, COPPER, FIRE, GOLD, ICE,
    METAL, PLASMA, RGBA, Ramp, SOLAR, STEEL, TOXIC, VOID, WOOD, with_alpha,
)
from .shapes import (
    capsule, dome, gradient_disc, ring, rounded_rect, soft_glow, star,
)

SIZE = 18
OUTLINE: RGBA = (12, 10, 18, 240)


def _new() -> Canvas:
    return Canvas(SIZE, SIZE)


def _gem(c: Canvas, cx: float, cy: float, r: float, ramp: Ramp) -> None:
    c.polygon([(round(cx), round(cy - r)), (round(cx + r), round(cy)),
               (round(cx), round(cy + r)), (round(cx - r), round(cy))],
              ramp[2])
    c.polygon([(round(cx), round(cy - r + 1)), (round(cx + r - 2), round(cy)),
               (round(cx), round(cy + r - 2)), (round(cx - r + 2), round(cy))],
              ramp[3])
    c.line(round(cx - 1), round(cy - r + 2), round(cx - 2), round(cy),
           ramp[4])
    c.put(round(cx - 1), round(cy - 1), (255, 255, 255, 220))


def _vial(c: Canvas, ramp: Ramp) -> None:
    c.rect(6, 2, 6, 3, METAL[2])
    c.hline(6, 2, 6, METAL[4])
    rounded_rect(c, 4, 5, 10, 11, with_alpha(BONE[4], 90), radius=3)
    rounded_rect(c, 5, 8, 8, 7, ramp[2], radius=2)
    c.hline(6, 8, 6, ramp[3])
    c.disc(7, 11, 1.2, ramp[4])
    c.vline(5, 7, 6, with_alpha((255, 255, 255, 255), 90))


# ---------------------------------------------------------------------------
# offence
# ---------------------------------------------------------------------------


def bloodstone() -> Canvas:
    c = _new()
    _gem(c, 9, 9, 6, BLOOD)
    soft_glow(c, 9, 9, 8, with_alpha(BLOOD[4], 90))
    c.outline(OUTLINE)
    return c


def quickpowder() -> Canvas:
    c = _new()
    c.polygon([(3, 13), (11, 3), (15, 5), (7, 15)], WOOD[2])
    c.polygon([(4, 12), (10, 5), (12, 6), (6, 13)], WOOD[3])
    c.rect(11, 2, 4, 4, METAL[3])
    for k in range(4):
        c.put(13 + math.cos(k) * 2, 2 + math.sin(k) * 2, FIRE[4])
    c.outline(OUTLINE)
    return c


def long_lens() -> Canvas:
    c = _new()
    ring(c, 8, 8, 5.5, 1.6, GOLD[3])
    c.disc(8, 8, 4.4, with_alpha(PLASMA[3], 160))
    c.line(5, 11, 3, 13, GOLD[2])
    c.line(4, 5, 11, 11, with_alpha((255, 255, 255, 255), 120))
    c.rect(11, 11, 5, 5, GOLD[2])
    c.hline(11, 11, 5, GOLD[4])
    c.outline(OUTLINE)
    return c


def heavy_slug() -> Canvas:
    c = _new()
    # Casing and jacket need different metals or the round reads as a bar.
    c.rect(5, 8, 9, 8, COPPER[2])
    c.vline(6, 9, 6, COPPER[4])
    c.vline(12, 9, 6, COPPER[1])
    c.hline(5, 8, 9, COPPER[3])
    c.hline(5, 15, 9, COPPER[0])
    c.hline(5, 12, 9, COPPER[1])
    dome(c, 9.5, 1, 4.5, 8, STEEL[3])
    dome(c, 8.5, 1, 3.0, 5, STEEL[4])
    c.hline(5, 7, 9, STEEL[1])
    c.outline(OUTLINE)
    return c


def split_shot() -> Canvas:
    c = _new()
    c.line(2, 9, 8, 9, STEEL[3])
    for dy in (-4, 0, 4):
        c.line(8, 9, 14, 9 + dy, STEEL[3])
        c.polygon([(14, 9 + dy - 2), (17, 9 + dy), (14, 9 + dy + 2)],
                  SOLAR[3])
    c.disc(8, 9, 1.6, SOLAR[4])
    c.outline(OUTLINE)
    return c


def ricochet_ring() -> Canvas:
    c = _new()
    ring(c, 9, 9, 6.0, 1.6, STEEL[3])
    for k in range(3):
        a = k * math.tau / 3 - 0.6
        px, py = 9 + math.cos(a) * 6, 9 + math.sin(a) * 6
        c.polygon([(round(px - 2), round(py - 2)), (round(px + 2), round(py)),
                   (round(px - 2), round(py + 2))], PLASMA[4])
    c.disc(9, 9, 2.0, PLASMA[3])
    c.outline(OUTLINE)
    return c


def piercing_tip() -> Canvas:
    c = _new()
    c.polygon([(9, 1), (13, 11), (9, 16), (5, 11)], STEEL[3])
    c.polygon([(9, 3), (11, 11), (9, 14), (7, 11)], STEEL[4])
    c.line(9, 2, 9, 14, (255, 255, 255, 190))
    c.rect(5, 11, 9, 2, METAL[1])
    c.outline(OUTLINE)
    return c


def homing_chip() -> Canvas:
    c = _new()
    rounded_rect(c, 3, 4, 12, 10, (28, 40, 36, 255), radius=1)
    c.hline(4, 4, 10, (58, 78, 70, 255))
    for x in (2, 15):
        for y in range(6, 13, 2):
            c.hline(x, y, 2, GOLD[3])
    c.ellipse(9, 9, 4.0, 3.0, (232, 236, 246, 255))
    c.disc(9, 9, 1.8, TOXIC[2])
    c.disc(9, 9, 1.0, (16, 20, 18, 255))
    c.put(8, 8, (255, 255, 255, 255))
    c.outline(OUTLINE)
    return c


def bandolier() -> Canvas:
    c = _new()
    c.polygon([(2, 4), (6, 2), (16, 12), (12, 15)], WOOD[2])
    c.polygon([(3, 5), (5, 4), (14, 12), (12, 13)], WOOD[3])
    for k in range(4):
        px, py = 4 + k * 3, 5 + k * 3
        c.rect(px, py, 3, 3, COPPER[3])
        c.hline(px, py, 3, COPPER[4])
        c.hline(px, py + 2, 3, CLOTH_RED[2])
    c.outline(OUTLINE)
    return c


def serpent_eye() -> Canvas:
    c = _new()
    c.ellipse(9, 9, 7.0, 5.0, BONE[4])
    c.ellipse(9, 9, 6.0, 4.2, (222, 226, 238, 255))
    c.ellipse(9, 9, 3.4, 3.8, TOXIC[2])
    c.rect(8, 6, 2, 7, (14, 16, 14, 255))
    c.put(7, 7, (255, 255, 255, 230))
    soft_glow(c, 9, 9, 9, with_alpha(TOXIC[4], 70))
    c.outline(OUTLINE)
    return c


def echo_bell() -> Canvas:
    c = _new()
    dome(c, 9, 3, 6.0, 10, GOLD[2])
    dome(c, 8, 3, 4.0, 6, GOLD[3])
    c.hline(4, 12, 11, GOLD[1])
    c.rect(3, 13, 13, 2, GOLD[3])
    c.disc(9, 16, 1.6, GOLD[1])
    c.vline(9, 0, 3, METAL[2])
    for k in (-1, 1):
        for r in (8, 10):
            c.put(9 + k * r, 7, with_alpha(SOLAR[4], 160))
    c.outline(OUTLINE)
    return c


# ---------------------------------------------------------------------------
# elemental
# ---------------------------------------------------------------------------


def ember_core() -> Canvas:
    c = _new()
    rounded_rect(c, 4, 3, 10, 13, with_alpha(ICE[4], 60), radius=3)
    c.frame(4, 3, 10, 13, METAL[2])
    gradient_disc(c, 9, 10, 4.0, FIRE, 4, 1)
    for k in range(3):
        c.put(9 + (k - 1) * 2, 5 + (k % 2), FIRE[3])
    soft_glow(c, 9, 10, 7, with_alpha(FIRE[4], 110))
    c.outline(OUTLINE)
    return c


def frost_core() -> Canvas:
    c = _new()
    for k in range(3):
        a = k * math.pi / 3
        c.line(9 - math.cos(a) * 7, 9 - math.sin(a) * 7,
               9 + math.cos(a) * 7, 9 + math.sin(a) * 7, ICE[3])
        c.line(9 - math.cos(a) * 4, 9 - math.sin(a) * 4 + 1,
               9 + math.cos(a) * 4, 9 + math.sin(a) * 4 + 1, ICE[4])
    _gem(c, 9, 9, 4, ICE)
    soft_glow(c, 9, 9, 9, with_alpha(ICE[4], 90))
    c.outline(OUTLINE)
    return c


def venom_vial() -> Canvas:
    c = _new()
    _vial(c, TOXIC)
    soft_glow(c, 9, 11, 7, with_alpha(TOXIC[4], 90))
    c.outline(OUTLINE)
    return c


def tesla_capacitor() -> Canvas:
    c = _new()
    rounded_rect(c, 5, 4, 8, 11, STEEL[2], radius=2)
    c.hline(6, 4, 6, STEEL[4])
    for y in range(6, 14, 3):
        c.hline(5, y, 8, STEEL[1])
    c.rect(7, 1, 2, 3, COPPER[3])
    c.rect(10, 1, 2, 3, COPPER[3])
    c.polygon([(9, 6), (6, 11), (9, 11), (7, 15), (12, 9), (9, 9)],
              PLASMA[4])
    soft_glow(c, 9, 10, 8, with_alpha(PLASMA[4], 100))
    c.outline(OUTLINE)
    return c


def void_prism() -> Canvas:
    c = _new()
    c.polygon([(9, 1), (16, 13), (2, 13)], VOID[2])
    c.polygon([(9, 4), (13, 12), (5, 12)], VOID[1])
    for k in range(4):
        c.line(9, 7 + k, 15 - k, 13, with_alpha(ARCANE[4], 200 - k * 30))
    c.disc(9, 9, 1.6, ARCANE[4])
    c.hline(2, 13, 15, VOID[3])
    soft_glow(c, 9, 9, 8, with_alpha(ARCANE[4], 90))
    c.outline(OUTLINE)
    return c


def sun_medal() -> Canvas:
    c = _new()
    for k in range(8):
        a = k * math.tau / 8
        c.line(9 + math.cos(a) * 4, 9 + math.sin(a) * 4,
               9 + math.cos(a) * 8, 9 + math.sin(a) * 8, SOLAR[3])
    gradient_disc(c, 9, 9, 5.0, GOLD, 4, 1)
    star(c, 9, 9, 3.2, 1.4, 5, SOLAR[4])
    soft_glow(c, 9, 9, 9, with_alpha(SOLAR[4], 100))
    c.outline(OUTLINE)
    return c


def gunpowder_keg() -> Canvas:
    c = _new()
    rounded_rect(c, 3, 5, 12, 11, WOOD[2], radius=2)
    c.vline(4, 7, 7, WOOD[3])
    c.rect(3, 6, 12, 2, METAL[2])
    c.rect(3, 12, 12, 2, METAL[2])
    c.rect(7, 2, 4, 3, METAL[1])
    c.vline(9, 0, 2, FIRE[3])
    c.disc(9, 10, 2.4, FIRE[1])
    soft_glow(c, 9, 0, 4, with_alpha(FIRE[4], 140))
    c.outline(OUTLINE)
    return c


# ---------------------------------------------------------------------------
# defence and utility
# ---------------------------------------------------------------------------


def iron_heart() -> Canvas:
    c = _new()
    c.disc(6, 7, 3.6, CLOTH_RED[2])
    c.disc(12, 7, 3.6, CLOTH_RED[2])
    c.polygon([(2, 8), (16, 8), (9, 16)], CLOTH_RED[2])
    c.disc(5.5, 6.5, 2.0, CLOTH_RED[3])
    c.put(5, 5, CLOTH_RED[4])
    c.rect(7, 6, 4, 7, METAL[2])
    c.hline(7, 6, 4, METAL[4])
    for y in (8, 10):
        c.hline(7, y, 4, METAL[1])
    c.outline(OUTLINE)
    return c


def feather_boots() -> Canvas:
    c = _new()
    c.polygon([(5, 5), (10, 5), (10, 12), (15, 12), (15, 15), (5, 15)],
              WOOD[2])
    c.hline(6, 5, 4, WOOD[3])
    c.hline(5, 14, 10, WOOD[0])
    for k in range(3):
        c.line(4 - k, 4 + k * 2, 1, 1 + k * 3, PLASMA[3])
        c.line(4 - k, 5 + k * 2, 2, 2 + k * 3, PLASMA[4])
    c.outline(OUTLINE)
    return c


def phase_cloak() -> Canvas:
    c = _new()
    c.polygon([(9, 2), (15, 8), (14, 16), (4, 16), (3, 8)],
              with_alpha(ARCANE[2], 215))
    c.polygon([(9, 4), (13, 9), (12, 15), (6, 15), (5, 9)],
              with_alpha(ARCANE[1], 200))
    for x in range(5, 14, 3):
        c.vline(x, 10, 6, with_alpha(ARCANE[3], 170))
    c.rect(6, 2, 6, 2, GOLD[3])
    for k in range(4):
        c.put(3 + k * 4, 6 + (k % 2) * 3, with_alpha((255, 255, 255, 255), 130))
    c.outline(OUTLINE)
    return c


def thorn_mail() -> Canvas:
    c = _new()
    c.polygon([(9, 2), (15, 5), (15, 11), (9, 16), (3, 11), (3, 5)],
              STEEL[2])
    c.polygon([(9, 4), (13, 6), (13, 10), (9, 14), (5, 10), (5, 6)],
              STEEL[3])
    for k in range(6):
        a = k * math.tau / 6 - 0.3
        px, py = 9 + math.cos(a) * 6.5, 9 + math.sin(a) * 6.5
        c.line(9 + math.cos(a) * 4, 9 + math.sin(a) * 4, px, py, BONE[4])
    c.outline(OUTLINE)
    return c


def vampire_fang() -> Canvas:
    c = _new()
    c.polygon([(5, 2), (13, 2), (11, 9), (9, 16), (7, 9)], BONE[4])
    c.polygon([(6, 3), (10, 3), (9, 9), (9, 13), (8, 9)], BONE[3])
    c.hline(5, 2, 9, BONE[2])
    for k in range(3):
        c.disc(9, 13 + k * 1.5, 1.4 - k * 0.3, with_alpha(BLOOD[3], 220))
    c.outline(OUTLINE)
    return c


def mirror_shard() -> Canvas:
    c = _new()
    c.polygon([(4, 2), (14, 5), (11, 16), (5, 12)], with_alpha(ICE[4], 200))
    c.polygon([(5, 4), (12, 6), (10, 14), (6, 11)], with_alpha(ICE[3], 220))
    c.line(6, 4, 10, 13, (255, 255, 255, 200))
    c.line(9, 4, 12, 8, with_alpha((255, 255, 255, 255), 140))
    c.outline(OUTLINE)
    return c


def clock_spring() -> Canvas:
    c = _new()
    ring(c, 9, 9, 7.0, 1.4, GOLD[2])
    for k in range(12):
        a = k * math.tau / 12
        c.put(9 + math.cos(a) * 6, 9 + math.sin(a) * 6, GOLD[4])
    for k in range(28):
        t = k / 28
        a = t * math.tau * 1.6 - 1.2
        r = 1 + t * 4.5
        c.put(9 + math.cos(a) * r, 9 + math.sin(a) * r, METAL[4])
    c.line(9, 9, 9, 5, METAL[3])
    c.line(9, 9, 12, 10, METAL[3])
    c.outline(OUTLINE)
    return c


def lucky_coin() -> Canvas:
    c = _new()
    c.ellipse(9, 9, 6.0, 7.0, GOLD[2])
    c.ellipse(9, 9, 4.6, 5.6, GOLD[3])
    c.ellipse(8, 8, 2.0, 2.4, GOLD[4])
    star(c, 9, 9, 3.0, 1.2, 4, GOLD[1])
    c.outline(OUTLINE)
    return c


def magnet_core() -> Canvas:
    c = _new()
    for r, col in ((6.5, CLOTH_RED[2]), (4.0, BONE[4])):
        for k in range(36):
            a = math.pi + k / 36 * math.pi
            c.put(9 + math.cos(a) * r, 11 + math.sin(a) * r, col)
    c.rect(1, 11, 4, 5, CLOTH_RED[2])
    c.rect(13, 11, 4, 5, CLOTH_RED[2])
    c.rect(1, 14, 4, 2, METAL[4])
    c.rect(13, 14, 4, 2, METAL[4])
    for k in range(3):
        c.put(9 + (k - 1) * 3, 2 + abs(k - 1), with_alpha(PLASMA[4], 200))
    c.outline(OUTLINE)
    return c


def ammo_belt() -> Canvas:
    c = _new()
    c.polygon([(1, 6), (17, 10), (17, 14), (1, 10)], WOOD[2])
    c.polygon([(1, 7), (16, 11), (16, 12), (1, 9)], WOOD[3])
    for k in range(5):
        px = 1 + k * 3.4
        py = 5 + k * 0.9
        c.rect(px, py, 3, 4, COPPER[3])
        c.hline(px, py, 3, GOLD[4])
        c.hline(px, py + 3, 3, COPPER[1])
    c.outline(OUTLINE)
    return c


def speed_loader() -> Canvas:
    c = _new()
    ring(c, 9, 9, 6.0, 2.0, METAL[3])
    for k in range(6):
        a = k * math.tau / 6
        c.disc(9 + math.cos(a) * 6, 9 + math.sin(a) * 6, 1.8, COPPER[3])
        c.put(9 + math.cos(a) * 6, 9 + math.sin(a) * 6, GOLD[4])
    c.disc(9, 9, 2.2, METAL[2])
    c.disc(9, 9, 1.0, METAL[4])
    c.outline(OUTLINE)
    return c


def glass_cannon() -> Canvas:
    c = _new()
    # Solid enough to hold a silhouette; the cracks are the read, but they
    # need a body to be cracks *in*.
    rounded_rect(c, 2, 5, 13, 8, with_alpha(ICE[2], 235), radius=2)
    rounded_rect(c, 3, 6, 11, 5, with_alpha(ICE[3], 220), radius=1)
    c.hline(3, 6, 11, with_alpha(ICE[4], 230))
    c.rect(14, 4, 3, 10, METAL[2])
    c.hline(14, 4, 3, METAL[4])
    c.rect(3, 13, 5, 4, METAL[1])
    c.hline(3, 13, 5, METAL[3])
    for a, b in (((5, 5), (8, 12)), ((8, 5), (6, 12)), ((11, 6), (12, 12))):
        c.line(a[0], a[1], b[0], b[1], (255, 255, 255, 235))
        c.line(a[0] + 1, a[1], b[0] + 1, b[1], with_alpha(ICE[0], 160))
    c.outline(OUTLINE)
    return c


def hex_tome() -> Canvas:
    c = _new()
    rounded_rect(c, 2, 3, 14, 13, VOID[2], radius=1)
    c.rect(3, 4, 12, 11, VOID[1])
    c.vline(9, 3, 13, VOID[0])
    c.rect(2, 3, 2, 13, ARCANE[2])
    c.hline(2, 3, 14, VOID[3])
    star(c, 12, 9, 3.0, 1.2, 5, ARCANE[4])
    for y in (6, 8, 10, 12):
        c.hline(4, y, 4, with_alpha(BONE[4], 150))
    soft_glow(c, 12, 9, 6, with_alpha(ARCANE[4], 90))
    c.outline(OUTLINE)
    return c


def orbital_shard() -> Canvas:
    c = _new()
    for k in range(40):
        a = k / 40 * math.tau
        c.put(9 + math.cos(a) * 7, 9 + math.sin(a) * 3.2,
              with_alpha(PLASMA[3], 150))
    gradient_disc(c, 9, 9, 3.5, VOID, 3, 1)
    c.disc(8, 8, 1.2, ARCANE[4])
    for cxp, cyp in ((16, 9), (2, 9)):
        c.polygon([(cxp, cyp - 2), (cxp + 2, cyp), (cxp, cyp + 2),
                   (cxp - 2, cyp)], STEEL[4])
    c.outline(OUTLINE)
    return c


# ---------------------------------------------------------------------------
# consumable pickups
# ---------------------------------------------------------------------------


def heart_pickup(half: bool = False) -> Canvas:
    c = Canvas(14, 14)
    r = CLOTH_RED
    c.disc(4.5, 5.5, 3.2, r[2])
    c.disc(9.5, 5.5, 3.2, r[2])
    c.polygon([(1, 6), (13, 6), (7, 13)], r[2])
    c.disc(4, 5, 1.6, r[3])
    c.put(3, 4, r[4])
    if half:
        for y in range(14):
            for x in range(7, 14):
                p = c.get(x, y)
                if p[3]:
                    c.set(x, y, (60, 56, 72, 220))
    c.outline(OUTLINE)
    return c


def armor_pickup() -> Canvas:
    c = Canvas(14, 14)
    c.polygon([(7, 1), (13, 4), (13, 8), (7, 13), (1, 8), (1, 4)], STEEL[3])
    c.polygon([(7, 3), (11, 5), (11, 8), (7, 11), (3, 8), (3, 5)], STEEL[4])
    c.line(7, 3, 7, 11, STEEL[2])
    c.outline(OUTLINE)
    return c


def ammo_pickup() -> Canvas:
    c = Canvas(16, 14)
    rounded_rect(c, 1, 4, 14, 9, WOOD[2], radius=1)
    c.hline(2, 4, 12, WOOD[3])
    c.rect(2, 10, 12, 3, WOOD[1])
    for k in range(4):
        px = 3 + k * 3
        c.rect(px, 1, 2, 4, COPPER[3])
        c.hline(px, 1, 2, GOLD[4])
    c.outline(OUTLINE)
    return c


def key_pickup() -> Canvas:
    c = Canvas(16, 12)
    ring(c, 4, 6, 3.0, 1.6, GOLD[3])
    c.rect(6, 5, 9, 2, GOLD[3])
    c.hline(6, 5, 9, GOLD[4])
    c.rect(11, 7, 2, 3, GOLD[3])
    c.rect(14, 7, 2, 2, GOLD[3])
    c.outline(OUTLINE)
    return c


def coin_pickup() -> Canvas:
    c = Canvas(12, 12)
    c.ellipse(6, 6, 4.0, 5.0, GOLD[2])
    c.ellipse(6, 6, 3.0, 4.0, GOLD[3])
    c.ellipse(5, 5, 1.2, 1.6, GOLD[4])
    c.outline(OUTLINE)
    return c


def blank_pickup() -> Canvas:
    """Screen-clearing charge. Reads as a rune-etched disc."""
    c = Canvas(14, 14)
    c.disc(7, 7, 6.0, STEEL[2])
    c.disc(7, 7, 4.6, STEEL[3])
    ring(c, 7, 7, 3.2, 1.0, (240, 246, 255, 255))
    star(c, 7, 7, 2.4, 1.0, 6, (240, 246, 255, 255))
    soft_glow(c, 7, 7, 8, with_alpha(PLASMA[4], 110))
    c.outline(OUTLINE)
    return c


ITEMS: dict[str, object] = {
    "bloodstone": bloodstone,
    "quickpowder": quickpowder,
    "long_lens": long_lens,
    "heavy_slug": heavy_slug,
    "split_shot": split_shot,
    "ricochet_ring": ricochet_ring,
    "piercing_tip": piercing_tip,
    "homing_chip": homing_chip,
    "bandolier": bandolier,
    "serpent_eye": serpent_eye,
    "echo_bell": echo_bell,
    "ember_core": ember_core,
    "frost_core": frost_core,
    "venom_vial": venom_vial,
    "tesla_capacitor": tesla_capacitor,
    "void_prism": void_prism,
    "sun_medal": sun_medal,
    "gunpowder_keg": gunpowder_keg,
    "iron_heart": iron_heart,
    "feather_boots": feather_boots,
    "phase_cloak": phase_cloak,
    "thorn_mail": thorn_mail,
    "vampire_fang": vampire_fang,
    "mirror_shard": mirror_shard,
    "clock_spring": clock_spring,
    "lucky_coin": lucky_coin,
    "magnet_core": magnet_core,
    "ammo_belt": ammo_belt,
    "speed_loader": speed_loader,
    "glass_cannon": glass_cannon,
    "hex_tome": hex_tome,
    "orbital_shard": orbital_shard,
}

PICKUPS: dict[str, object] = {
    "heart": lambda: heart_pickup(False),
    "heart_half": lambda: heart_pickup(True),
    "armor": armor_pickup,
    "ammo_box": ammo_pickup,
    "key": key_pickup,
    "coin": coin_pickup,
    "blank": blank_pickup,
}


def build_items() -> dict[str, Canvas]:
    return {name: fn() for name, fn in ITEMS.items()}


def build_pickups() -> dict[str, Canvas]:
    return {name: fn() for name, fn in PICKUPS.items()}
