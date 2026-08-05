"""Dungeon tiles.

The whole "2D sprites on a 3D-looking map" illusion lives here. A wall is not
one tile, it is two: a **cap** seen from above and a **face** seen from the
front, stacked vertically. Because the face is drawn a tile lower than the cap
and is sorted with the entities, characters walk *in front of* the near wall
and *behind* the far wall — which is what makes a flat floor read as a room
with height.

Wall caps autotile from a 4-bit neighbour mask (N=1, E=2, S=4, W=8) so a room
outline gets correct edges and corners with 16 sprites.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .canvas import Canvas
from .palette import (
    ARCANE, BONE, BRICK, COPPER, DIRT, FLOOR, GOLD, METAL, RGBA, Ramp, STONE,
    TOXIC, VOID, WOOD, tint, with_alpha,
)
from .shapes import dome, ring, rounded_rect, soft_glow, star

TILE = 16
WALL_H = 16  # height of the front-facing wall strip


@dataclass
class Theme:
    """A biome's material set. Every tile generator takes one."""

    name: str
    floor: Ramp
    wall: Ramp
    wall_top: Ramp
    accent: Ramp
    grime: RGBA
    seed: int


THEMES: dict[str, Theme] = {
    "keep": Theme("keep", FLOOR, BRICK, STONE, GOLD, (20, 18, 28, 60), 11),
    "crypt": Theme("crypt", DIRT, VOID, BONE, ARCANE, (16, 10, 22, 70), 23),
    "foundry": Theme("foundry", METAL.shifted("f", -1), BRICK, METAL, COPPER,
                     (28, 16, 8, 55), 37),
    "sanctum": Theme("sanctum", BONE.shifted("s", -1), ARCANE, BONE, TOXIC,
                     (24, 20, 40, 45), 53),
}


# ---------------------------------------------------------------------------
# floors
# ---------------------------------------------------------------------------


def floor_tile(theme: Theme, variant: int) -> Canvas:
    """A stone slab. Seams on the north and west edges only, so slabs tile
    into a grid without doubling up their grout lines."""
    rng = random.Random(theme.seed * 100 + variant)
    c = Canvas(TILE, TILE)
    base = theme.floor
    c.rect(0, 0, TILE, TILE, base[3])

    # Subtle per-tile value shift keeps large rooms from banding.
    if variant % 3 == 1:
        c.rect(0, 0, TILE, TILE, base[4])
    elif variant % 3 == 2:
        c.rect(0, 0, TILE, TILE, base[3])

    for _ in range(26):
        x, y = rng.randrange(TILE), rng.randrange(TILE)
        c.put(x, y, base[3] if rng.random() < 0.5 else base[1])

    c.hline(0, 0, TILE, base[1])
    c.vline(0, 0, TILE, base[1])
    c.hline(0, 1, TILE, base[4])
    c.vline(1, 1, TILE - 1, base[4])

    if variant == 1:
        # Hairline crack. Kept at one ramp step so a floor tiled with these
        # doesn't turn into visible wallpaper.
        x = rng.randrange(4, 11)
        y = 4
        for _ in range(7):
            c.put(x, y, base[1])
            x += rng.choice((-1, 0, 1))
            y += 1
    elif variant == 2:
        # A chipped inset panel, one ramp step deep. Any deeper and a room
        # tiled with these looks perforated.
        rounded_rect(c, 4, 4, 8, 8, base[2], radius=1)
        rounded_rect(c, 4, 4, 8, 7, base[3], radius=1)
        c.hline(5, 4, 6, base[4])
    elif variant == 3:
        for _ in range(5):
            x, y = rng.randrange(2, 14), rng.randrange(2, 14)
            c.rect(x, y, 2, 1, base[1])
    return c


def floor_grate(theme: Theme) -> Canvas:
    c = floor_tile(theme, 0)
    met = METAL
    c.rect(2, 2, 12, 12, (10, 10, 16, 255))
    for i in range(3, 14, 3):
        c.vline(i, 2, 12, met[2])
        c.put(i, 2, met[3])
    c.frame(2, 2, 12, 12, met[3])
    c.hline(3, 13, 10, met[1])
    return c


def floor_pit(theme: Theme) -> Canvas:
    """Bottomless hole — gradient into black with a lit lip."""
    c = Canvas(TILE, TILE)
    c.rect(0, 0, TILE, TILE, (6, 5, 10, 255))
    for i in range(4):
        a = 40 - i * 10
        c.frame(i, i, TILE - i * 2, TILE - i * 2,
                with_alpha(theme.floor[1], max(0, a)))
    c.hline(0, 0, TILE, theme.floor[0])
    return c


def floor_rug(theme: Theme, part: str) -> Canvas:
    """Shop and boss-room carpets: ``center``, ``edge_n``, ``corner_nw``."""
    c = floor_tile(theme, 0)
    rug = theme.accent
    if part == "center":
        c.rect(0, 0, TILE, TILE, rug[1])
        for y in range(0, TILE, 4):
            c.hline(0, y, TILE, rug[2])
    elif part.startswith("edge"):
        c.rect(0, 0, TILE, TILE, rug[1])
        side = part.split("_")[1]
        if side == "n":
            c.hline(0, 0, TILE, rug[3])
            c.hline(0, 2, TILE, rug[2])
        elif side == "s":
            c.hline(0, TILE - 1, TILE, rug[0])
            c.hline(0, TILE - 3, TILE, rug[2])
        elif side == "w":
            c.vline(0, 0, TILE, rug[3])
            c.vline(2, 0, TILE, rug[2])
        else:
            c.vline(TILE - 1, 0, TILE, rug[0])
            c.vline(TILE - 3, 0, TILE, rug[2])
    else:
        c.rect(0, 0, TILE, TILE, rug[1])
        c.hline(0, 0, TILE, rug[3])
        c.vline(0, 0, TILE, rug[3])
        c.rect(3, 3, 3, 3, rug[3])
    return c


# ---------------------------------------------------------------------------
# walls
# ---------------------------------------------------------------------------


def wall_cap(theme: Theme, mask: int) -> Canvas:
    """Top surface of a wall block, seen straight down.

    Deliberately *not* brickwork: the cap is the only surface the camera sees
    from above, so it reads as big flat flagstones. Keeping it a lighter value
    than the front face is what makes the wall look like it has thickness.

    ``mask`` bits mark neighbours that are also wall (N=1, E=2, S=4, W=8);
    exposed sides get a rim, so a room outline gains real edges and corners.
    """
    rng = random.Random(theme.seed * 977 + mask)
    c = Canvas(TILE, TILE)
    top = theme.wall_top
    # Kept a step darker than you might expect. The gaps between rooms are
    # solid wall, so cap tiles cover most of the screen — at full brightness
    # they swamp the rooms the player is actually looking at.
    c.rect(0, 0, TILE, TILE, top[0])
    for _ in range(24):
        c.put(rng.randrange(TILE), rng.randrange(TILE),
              top[1] if rng.random() < 0.5 else top[0])
    # Two big flagstones per tile with a soft seam between them.
    seam = 7 if mask % 2 == 0 else 8
    c.hline(0, seam, TILE, top[1])
    if mask & 3 == 3:
        c.vline(9, 0, seam, top[1])
    else:
        c.vline(5, seam + 2, TILE - seam - 2, top[1])

    # Exposed edges. North catches the light, south falls into shadow, and
    # the east/west rims give the block its chamfer.
    # Only the exposed edges catch the light. That contrast is what reads as
    # a room's outline once the field of caps behind it is dark.
    if not mask & 1:
        c.hline(0, 0, TILE, top[4])
        c.hline(0, 1, TILE, top[3])
        c.hline(0, 2, TILE, top[2])
    if not mask & 8:
        c.vline(0, 0, TILE, top[3])
        c.vline(1, 0, TILE, top[2])
    if not mask & 2:
        c.vline(TILE - 1, 0, TILE, top[0])
        c.vline(TILE - 2, 0, TILE, top[1])
    if not mask & 4:
        c.hline(0, TILE - 1, TILE, top[0])
        c.hline(0, TILE - 2, TILE, top[0])
    # Inner corners need their own nick or two straight rims meet in a
    # visibly wrong square.
    if mask & 1 and mask & 8 and not mask & 16:
        c.put(0, 0, top[2])
    return c


def wall_face(theme: Theme, variant: int = 0) -> Canvas:
    """The camera-facing brick strip below a wall cap — the tile that gives
    the map its apparent height."""
    rng = random.Random(theme.seed * 31 + variant)
    c = Canvas(TILE, WALL_H)
    wall = theme.wall
    c.rect(0, 0, TILE, WALL_H, wall[2])
    # Ambient occlusion down the height of the wall: bright where the cap
    # overhangs it, sinking to near-black where it meets the floor.
    c.hline(0, 0, TILE, wall[3])
    c.hline(0, 1, TILE, wall[2])
    for y in range(WALL_H - 6, WALL_H):
        t = (y - (WALL_H - 6)) / 6.0
        c.hline(0, y, TILE, wall[1] if t < 0.6 else wall[0])

    brick_h = 4
    for row in range(0, WALL_H, brick_h):
        c.hline(0, row, TILE, wall[1])
        off = 0 if (row // brick_h) % 2 == 0 else 8
        for x in range(off, TILE + 8, 16):
            if 0 <= x < TILE:
                c.vline(x, row, brick_h, wall[1])
            if 0 <= x + 1 < TILE:
                c.vline(x + 1, row + 1, brick_h - 1, wall[3])
        c.hline(0, row + 1, TILE, wall[3])

    for _ in range(18):
        c.put(rng.randrange(TILE), rng.randrange(WALL_H),
              wall[3] if rng.random() < 0.4 else wall[1])

    if variant == 1:
        # Cracked brick.
        x, y = rng.randrange(3, 12), 3
        for _ in range(8):
            c.put(x, y, wall[0])
            x += rng.choice((-1, 0, 1))
            y += 1
    elif variant == 2:
        # Recessed alcove with a candle — free light source for the artist.
        rounded_rect(c, 5, 4, 6, 8, wall[0], radius=1)
        c.rect(6, 9, 4, 2, (240, 210, 140, 255))
        soft_glow(c, 8, 8, 5, (255, 200, 120, 120))
    elif variant == 3:
        # Hanging banner in the theme accent.
        acc = theme.accent
        c.rect(5, 0, 6, 12, acc[2])
        c.vline(5, 0, 12, acc[3])
        c.vline(10, 0, 12, acc[1])
        c.hline(5, 11, 6, acc[0])
        star(c, 8, 5, 3, 1.2, 5, acc[4])
    return c


def wall_shadow() -> Canvas:
    """Soft gradient the floor gets right below a wall face."""
    c = Canvas(TILE, 6)
    for y in range(6):
        a = int(90 * (1.0 - y / 6.0))
        c.hline(0, y, TILE, (8, 6, 14, a))
    return c


def wall_side(theme: Theme) -> Canvas:
    """Left/right wall run seen edge-on: mostly cap with a thin lit lip."""
    c = wall_cap(theme, 1 | 4)
    top = theme.wall_top
    c.vline(0, 0, TILE, top[3])
    c.vline(TILE - 1, 0, TILE, top[1])
    return c


def door_tile(theme: Theme, state: str, axis: str) -> Canvas:
    """``state`` in closed|open|locked|boss, ``axis`` in h|v."""
    c = Canvas(TILE, TILE)
    frame_ramp = METAL if state != "boss" else theme.accent
    wood = WOOD

    if state == "open":
        c.rect(0, 0, TILE, TILE, (0, 0, 0, 0))
        c.rect(0, 0, 3, TILE, frame_ramp[2])
        c.rect(TILE - 3, 0, 3, TILE, frame_ramp[2])
        c.vline(1, 0, TILE, frame_ramp[3])
        c.vline(TILE - 2, 0, TILE, frame_ramp[1])
        if axis == "h":
            return c.rotated(90)
        return c

    c.rect(0, 0, TILE, TILE, wood[2])
    for x in range(0, TILE, 4):
        c.vline(x, 0, TILE, wood[1])
        c.vline(x + 1, 0, TILE, wood[3])
    c.rect(0, 0, TILE, 2, frame_ramp[3])
    c.rect(0, TILE - 2, TILE, 2, frame_ramp[1])
    c.frame(0, 0, TILE, TILE, frame_ramp[1])

    if state == "locked":
        lock = GOLD
        rounded_rect(c, 5, 5, 6, 6, lock[3], radius=1)
        c.rect(7, 7, 2, 3, lock[0])
        ring(c, 8, 4, 2.0, 1.0, lock[2])
    elif state == "boss":
        acc = theme.accent
        star(c, 8, 8, 5, 2.0, 5, acc[3])
        star(c, 8, 8, 3, 1.2, 5, acc[4])
        soft_glow(c, 8, 8, 8, with_alpha(acc[4], 90))
    if axis == "h":
        return c.rotated(90)
    return c


# ---------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------


def barrel(theme: Theme, explosive: bool = False) -> Canvas:
    c = Canvas(16, 20)
    body = COPPER if explosive else WOOD
    hoop = METAL
    rounded_rect(c, 3, 4, 10, 14, body[2], radius=2)
    c.vline(4, 6, 11, body[3])
    c.vline(11, 6, 11, body[1])
    c.rect(3, 5, 10, 2, hoop[2])
    c.rect(3, 14, 10, 2, hoop[2])
    c.hline(3, 5, 10, hoop[3])
    dome(c, 8, 3, 5.0, 3, body[3])
    c.hline(5, 3, 6, body[4])
    if explosive:
        c.rect(6, 9, 4, 4, (220, 60, 40, 255))
        c.rect(7, 10, 2, 2, (255, 220, 150, 255))
        c.vline(8, 0, 3, (60, 50, 40, 255))
    c.outline((14, 10, 16, 235))
    return c


def crate(theme: Theme) -> Canvas:
    c = Canvas(16, 18)
    w = WOOD
    rounded_rect(c, 2, 3, 12, 13, w[2], radius=1)
    c.frame(2, 3, 12, 13, w[1])
    c.line(3, 4, 12, 14, w[3])
    c.line(12, 4, 3, 14, w[3])
    c.hline(3, 4, 10, w[3])
    c.hline(3, 14, 10, w[1])
    c.outline((14, 10, 16, 235))
    return c


def chest(theme: Theme, state: str = "closed") -> Canvas:
    """``closed``, ``open`` or ``rare`` (gold-trimmed)."""
    c = Canvas(20, 20)
    body = WOOD
    trim = GOLD if state == "rare" else METAL
    rounded_rect(c, 2, 8, 16, 10, body[2], radius=1)
    c.hline(3, 8, 14, body[3])
    c.rect(3, 15, 14, 3, body[1])
    if state == "open":
        dome(c, 10, 1, 8.0, 6, body[1])
        c.rect(3, 6, 14, 2, (10, 8, 14, 255))
        for i in range(6):
            gx = 5 + i * 2
            c.rect(gx, 9 + (i % 2), 2, 2, GOLD[3])
            c.put(gx, 9 + (i % 2), GOLD[4])
        soft_glow(c, 10, 9, 9, (255, 220, 140, 110))
    else:
        dome(c, 10, 3, 8.0, 6, body[2])
        dome(c, 9, 3, 6.5, 4, body[3])
        c.hline(6, 3, 8, body[4])
    c.rect(2, 7, 16, 2, trim[2])
    c.hline(2, 7, 16, trim[3])
    c.rect(8, 10, 4, 4, trim[3])
    c.rect(9, 11, 2, 2, (20, 16, 24, 255))
    c.outline((14, 10, 16, 235))
    return c


def torch_frames(theme: Theme, count: int = 4) -> list[Canvas]:
    """Wall torch — the main animated light in every room.

    Sized to exactly one wall-face tile so it can be anchored to the bottom of
    the face. A taller sprite spills onto the cap above and the flame ends up
    floating over the rock instead of burning on the wall.
    """
    frames: list[Canvas] = []
    for i in range(count):
        c = Canvas(12, TILE)
        rng = random.Random(theme.seed + i * 17)
        # bracket, bolted to the lower half of the face
        c.rect(5, 9, 2, 6, METAL[2])
        c.vline(5, 9, 6, METAL[3])
        c.rect(3, 7, 6, 3, METAL[3])
        c.hline(3, 7, 6, METAL[4])
        c.hline(3, 9, 6, METAL[1])
        # flame: three lobes that wobble per frame
        phase = i / count * math.tau
        for lobe, (dx, scale) in enumerate(((0, 1.0), (-1, 0.7), (1, 0.6))):
            wob = math.sin(phase + lobe * 2.1)
            cx = 6 + dx + wob * 0.8
            h = 7 * scale + wob
            for y in range(int(h)):
                t = y / max(1.0, h)
                half = (1.0 - t) * 2.4 * scale + 0.6
                c.hline(int(cx - half), 7 - y, max(1, int(half * 2)),
                        (255, 200, 90, 255) if t < 0.35 else
                        (240, 140, 40, 255) if t < 0.7 else
                        (200, 70, 20, 255))
        c.rect(5, 4, 2, 2, (255, 244, 200, 255))
        soft_glow(c, 6, 5, 8, (255, 170, 60, 110))
        for _ in range(2):
            c.put(rng.randrange(3, 9), rng.randrange(0, 3),
                  (255, 190, 100, 180))
        frames.append(c)
    return frames


def pillar(theme: Theme) -> Canvas:
    c = Canvas(16, 28)
    top = theme.wall_top
    rounded_rect(c, 4, 6, 8, 18, top[2], radius=1)
    c.vline(5, 8, 15, top[3])
    c.vline(10, 8, 15, top[1])
    for y in range(9, 23, 4):
        c.hline(4, y, 8, top[1])
    c.rect(2, 3, 12, 4, top[3])
    c.hline(2, 3, 12, top[4])
    c.rect(2, 23, 12, 4, top[3])
    c.hline(2, 26, 12, top[0])
    c.outline((14, 10, 16, 235))
    return c


def statue(theme: Theme) -> Canvas:
    c = Canvas(20, 30)
    st = BONE
    c.rect(3, 24, 14, 5, st[1])
    c.hline(3, 24, 14, st[2])
    rounded_rect(c, 6, 12, 8, 13, st[2], radius=2)
    dome(c, 10, 4, 4.0, 8, st[2])
    dome(c, 9, 4, 3.0, 4, st[3])
    c.rect(7, 9, 2, 2, (16, 14, 22, 255))
    c.rect(11, 9, 2, 2, (16, 14, 22, 255))
    c.rect(3, 13, 3, 8, st[1])
    c.rect(14, 13, 3, 8, st[1])
    soft_glow(c, 10, 9, 6, with_alpha(theme.accent[4], 60))
    c.outline((14, 10, 16, 235))
    return c


def shop_counter(theme: Theme) -> Canvas:
    c = Canvas(32, 22)
    w = WOOD
    rounded_rect(c, 1, 6, 30, 14, w[2], radius=1)
    c.hline(1, 6, 30, w[4])
    c.hline(1, 7, 30, w[3])
    c.rect(2, 17, 28, 3, w[1])
    for x in range(4, 30, 6):
        c.vline(x, 9, 8, w[1])
    c.rect(0, 4, 32, 3, w[3])
    c.hline(0, 4, 32, w[4])
    c.outline((14, 10, 16, 235))
    return c


def pedestal(theme: Theme) -> Canvas:
    c = Canvas(16, 20)
    st = theme.wall_top
    c.rect(2, 15, 12, 4, st[1])
    c.hline(2, 15, 12, st[2])
    rounded_rect(c, 5, 6, 6, 10, st[2], radius=1)
    c.vline(6, 7, 8, st[3])
    c.rect(2, 3, 12, 4, st[3])
    c.hline(2, 3, 12, st[4])
    soft_glow(c, 8, 2, 8, with_alpha(theme.accent[4], 70))
    c.outline((14, 10, 16, 235))
    return c


def bone_pile(theme: Theme) -> Canvas:
    rng = random.Random(theme.seed + 5)
    c = Canvas(16, 12)
    for _ in range(7):
        x = rng.randrange(1, 12)
        y = rng.randrange(5, 11)
        ln = rng.randrange(3, 6)
        c.hline(x, y, ln, BONE[3])
        c.put(x, y, BONE[4])
        c.put(x + ln - 1, y, BONE[4])
    dome(c, 5, 4, 3.0, 4, BONE[3])
    c.rect(4, 5, 1, 1, (20, 16, 24, 255))
    c.rect(6, 5, 1, 1, (20, 16, 24, 255))
    c.outline((14, 10, 16, 200))
    return c


def all_props(theme: Theme) -> dict[str, Canvas | list[Canvas]]:
    return {
        "barrel": barrel(theme),
        "barrel_explosive": barrel(theme, explosive=True),
        "crate": crate(theme),
        "chest_closed": chest(theme, "closed"),
        "chest_open": chest(theme, "open"),
        "chest_rare": chest(theme, "rare"),
        "torch": torch_frames(theme),
        "pillar": pillar(theme),
        "statue": statue(theme),
        "shop_counter": shop_counter(theme),
        "pedestal": pedestal(theme),
        "bone_pile": bone_pile(theme),
    }
