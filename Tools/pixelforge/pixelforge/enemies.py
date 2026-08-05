"""Enemy sprites.

Humanoids reuse the character rig from :mod:`chars` with hostile palettes —
that shared silhouette language is what makes a cultist read as "a guy" at a
glance while a crawler reads as "not a guy". Everything non-humanoid gets a
purpose-built rig here, each with its own idle motion so a still room still
feels alive.
"""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .chars import CharSpec, build_character
from .palette import (
    ARCANE, BLOOD, BONE, CLOTH_GREEN, CLOTH_ORANGE, CLOTH_PURPLE, CLOTH_RED,
    CLOTH_TEAL, COPPER, DIRT, FIRE, GOLD, ICE, METAL, PLASMA, RGBA, Ramp,
    SKIN, SKIN_PALE, SOLAR, STEEL, TOXIC, VOID, WOOD, outline_for, tint,
    with_alpha,
)
from .shapes import capsule, dome, gradient_disc, ring, rounded_rect, soft_glow, star

EYE_WHITE: RGBA = (238, 240, 250, 255)
DARK: RGBA = (14, 11, 20, 235)


# ---------------------------------------------------------------------------
# humanoids
# ---------------------------------------------------------------------------


def humanoid_specs() -> list[CharSpec]:
    """Hostile humanoids. Same rig as the player, read as enemies through
    colour temperature and silhouette accessories."""
    return [
        CharSpec("cultist", skin=SKIN_PALE, cloth=CLOTH_PURPLE, accent=ARCANE,
                 hair=VOID, boots=VOID, head_style="hood", eye_style="hollow",
                 glow=(190, 120, 255, 255), build="normal"),
        CharSpec("brigand", skin=SKIN, cloth=DIRT, accent=CLOTH_RED,
                 hair=WOOD, boots=WOOD, head_style="hair", eye_style="angry",
                 scarf=True),
        CharSpec("skelly", skin=BONE, cloth=BONE.shifted("rag", -2),
                 accent=BONE, hair=BONE, boots=BONE.shifted("b", -1),
                 head_style="skull", eye_style="hollow",
                 glow=(120, 240, 190, 255), build="small"),
        CharSpec("warden", skin=SKIN, cloth=STEEL, accent=GOLD, hair=METAL,
                 boots=METAL, head_style="helmet", build="big",
                 shoulders=True),
        CharSpec("hexer", skin=SKIN_PALE, cloth=VOID, accent=TOXIC, hair=ICE,
                 boots=VOID, head_style="hat", cape=True, eye_style="dot",
                 glow=(150, 240, 120, 255)),
        CharSpec("gunner", skin=SKIN, cloth=CLOTH_TEAL, accent=COPPER,
                 hair=CLOTH_ORANGE, boots=METAL, head_style="visor",
                 eye_style="dot", backpack=True),
        CharSpec("zealot", skin=SKIN_PALE, cloth=CLOTH_RED, accent=GOLD,
                 hair=BLOOD, boots=DIRT, head_style="hood", eye_style="angry",
                 horns=True),
        CharSpec("marauder", skin=SKIN, cloth=CLOTH_GREEN, accent=CLOTH_ORANGE,
                 hair=DIRT, boots=WOOD, head_style="hair", eye_style="angry",
                 build="big", shoulders=True),
    ]


def build_humanoid(spec: CharSpec) -> dict[str, list[Canvas]]:
    return build_character(spec)


# ---------------------------------------------------------------------------
# blobs
# ---------------------------------------------------------------------------


def blob_frames(ramp: Ramp, size: int = 16, eyes: int = 2,
                count: int = 6) -> list[Canvas]:
    """A gelatinous cube's little cousin: squash, stretch, wobble.

    The body is translucent, so a darker core shows through — that one trick
    is most of what makes a blob read as *goo* rather than a coloured ball.
    """
    frames: list[Canvas] = []
    w = size + 6
    h = size + 6
    for i in range(count):
        t = i / count * math.tau
        squash = math.sin(t) * 0.18
        rx = size / 2.0 * (1.0 + squash)
        ry = size / 2.0 * (1.0 - squash * 0.9)
        cx = w / 2.0
        cy = h - ry - 2
        c = Canvas(w, h)
        c.ellipse(cx, cy, rx, ry, with_alpha(ramp[2], 225))
        c.ellipse(cx, cy + ry * 0.25, rx * 0.72, ry * 0.6, ramp[1])
        c.ellipse(cx - rx * 0.25, cy - ry * 0.35, rx * 0.45, ry * 0.35,
                  with_alpha(ramp[4], 190))
        c.ellipse(cx - rx * 0.3, cy - ry * 0.45, rx * 0.22, ry * 0.18,
                  (255, 255, 255, 160))
        # Drips forming and falling along the bottom edge.
        for k in range(3):
            dx = int(cx + (k - 1) * rx * 0.55)
            drop = int((math.sin(t + k * 2.0) + 1) * 1.5)
            c.rect(dx, int(cy + ry) - 1, 2, 1 + drop, with_alpha(ramp[2], 200))
        eye_y = int(cy - ry * 0.1)
        if eyes == 1:
            c.rect(int(cx) - 2, eye_y, 4, 4, EYE_WHITE)
            c.rect(int(cx) - 1, eye_y + 1, 2, 2, DARK)
        else:
            for ex in (int(cx) - 4, int(cx) + 1):
                c.rect(ex, eye_y, 3, 3, EYE_WHITE)
                c.rect(ex + 1, eye_y + 1, 2, 2, DARK)
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


# ---------------------------------------------------------------------------
# floaters
# ---------------------------------------------------------------------------


def watcher_frames(ramp: Ramp, count: int = 6) -> list[Canvas]:
    """Floating eye. Bobs, and blinks on the last frame of the cycle."""
    frames: list[Canvas] = []
    w, h = 20, 22
    for i in range(count):
        t = i / count * math.tau
        bob = int(round(math.sin(t) * 2))
        c = Canvas(w, h)
        cx, cy = w / 2.0, 9 + bob
        # Trailing tendrils first so they sit behind the eyeball.
        for k in range(3):
            ang = math.pi / 2 + (k - 1) * 0.5 + math.sin(t + k) * 0.25
            for step in range(5):
                px = cx + math.cos(ang) * (5 + step * 1.6)
                py = cy + math.sin(ang) * (5 + step * 1.6)
                c.put(int(px), int(py), ramp[2 if step < 3 else 1])
        c.disc(cx, cy, 7.0, ramp[1])
        c.disc(cx, cy, 6.2, EYE_WHITE)
        c.disc(cx - 0.5, cy - 0.5, 5.6, (218, 222, 238, 255))
        look = math.sin(t * 0.5) * 1.6
        c.disc(cx + look, cy, 3.2, ramp[2])
        c.disc(cx + look, cy, 2.0, DARK)
        c.put(int(cx + look - 1), int(cy - 1), EYE_WHITE)
        soft_glow(c, cx, cy, 10, with_alpha(ramp[4], 70))
        if i == count - 1:
            c.rect(int(cx) - 7, int(cy) - 3, 14, 6, ramp[2])
            c.hline(int(cx) - 6, int(cy), 12, ramp[1])
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


def mothling_frames(ramp: Ramp, count: int = 4) -> list[Canvas]:
    """Erratic flyer. Wings sweep through four poses, body stays put."""
    frames: list[Canvas] = []
    w, h = 22, 18
    for i in range(count):
        span = (0.35, 0.9, 1.0, 0.6)[i]
        c = Canvas(w, h)
        cx, cy = w / 2.0, 9.0
        for side in (-1, 1):
            wing_w = 2 + span * 7
            wing_h = 3 + span * 4
            c.ellipse(cx + side * (2 + wing_w * 0.5), cy - 1 + (1 - span) * 2,
                      wing_w, wing_h, with_alpha(ramp[3], 210))
            c.ellipse(cx + side * (2 + wing_w * 0.5), cy - 1 + (1 - span) * 2,
                      wing_w * 0.6, wing_h * 0.6, with_alpha(ramp[4], 160))
        capsule(c, int(cx) - 2, int(cy) - 3, 4, 8, ramp[1])
        c.hline(int(cx) - 2, int(cy) - 3, 4, ramp[2])
        for ex in (int(cx) - 2, int(cx) + 1):
            c.rect(ex, int(cy) - 2, 2, 2, (255, 120, 90, 255))
        c.line(int(cx) - 1, int(cy) - 4, int(cx) - 3, int(cy) - 7, ramp[2])
        c.line(int(cx) + 1, int(cy) - 4, int(cx) + 3, int(cy) - 7, ramp[2])
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


# ---------------------------------------------------------------------------
# ground stalkers
# ---------------------------------------------------------------------------


def crawler_frames(ramp: Ramp, count: int = 4) -> list[Canvas]:
    """Six-legged scuttler. Legs alternate in tripods like a real insect."""
    frames: list[Canvas] = []
    w, h = 22, 18
    for i in range(count):
        phase = i / count * math.tau
        c = Canvas(w, h)
        cx, cy = w / 2.0, 10.0
        for side in (-1, 1):
            for k in range(3):
                tri = (k + (0 if side < 0 else 1)) % 2
                lift = math.sin(phase + tri * math.pi) * 2
                ax = cx + side * 4
                ay = cy - 2 + k * 3
                ex = cx + side * (9 + k * 0.5)
                ey = ay + 3 - lift
                c.line(int(ax), int(ay), int(ex), int(ey), ramp[1])
                c.put(int(ex), int(ey), ramp[0])
        c.ellipse(cx, cy, 6.0, 5.0, ramp[2])
        c.ellipse(cx - 1, cy - 1, 4.5, 3.4, ramp[3])
        c.ellipse(cx - 1.5, cy - 2, 2.4, 1.6, ramp[4])
        c.ellipse(cx, cy - 5, 3.6, 2.8, ramp[2])
        for ex in (int(cx) - 3, int(cx) + 1):
            c.rect(ex, int(cy) - 6, 2, 2, (255, 90, 70, 255))
            c.put(ex, int(cy) - 6, (255, 200, 160, 255))
        c.line(int(cx) - 3, int(cy) - 7, int(cx) - 5, int(cy) - 10, ramp[3])
        c.line(int(cx) + 2, int(cy) - 7, int(cx) + 4, int(cy) - 10, ramp[3])
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


def imp_frames(ramp: Ramp, fuse: Ramp = FIRE, count: int = 4) -> list[Canvas]:
    """Kamikaze bomber: swells and glows brighter the closer it is to popping.
    The renderer plays this faster as its timer runs down."""
    frames: list[Canvas] = []
    w, h = 20, 20
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(w, h)
        cx, cy = w / 2.0, 11.0
        r = 6.0 + t * 1.6
        c.disc(cx, cy, r, ramp[2])
        c.disc(cx - 1, cy - 1, r - 2, ramp[3])
        c.disc(cx - 1.5, cy - 2, r - 4, tint(ramp[4], fuse[4], t * 0.8))
        for side in (-1, 1):
            c.line(int(cx + side * 4), int(cy - r + 2),
                   int(cx + side * 6), int(cy - r - 2), ramp[3])
        for ex in (int(cx) - 3, int(cx) + 1):
            c.rect(ex, int(cy) - 2, 3, 3, EYE_WHITE)
            c.rect(ex + 1, int(cy) - 1, 2, 2, DARK)
        c.rect(int(cx) - 2, int(cy) + 2, 5, 2, DARK)
        for side in (-2, 2):
            c.rect(int(cx) + side, int(cy) + 4, 2, 3, ramp[1])
        c.vline(int(cx), int(cy) - r - 3, 3, (70, 60, 50, 255))
        soft_glow(c, cx, cy - r - 3, 2 + t * 3, with_alpha(fuse[4], 160))
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


def turret_frames(ramp: Ramp, count: int = 4) -> list[Canvas]:
    """Static emplacement. Frames are the charge-up, not a walk cycle."""
    frames: list[Canvas] = []
    w, h = 20, 22
    for i in range(count):
        t = i / max(1, count - 1)
        c = Canvas(w, h)
        cx = w / 2.0
        c.rect(3, 16, 14, 4, ramp[1])
        c.hline(3, 16, 14, ramp[2])
        rounded_rect(c, 5, 12, 10, 5, ramp[2], radius=1)
        dome(c, cx, 4, 6.0, 9, ramp[3])
        dome(c, cx - 1, 4, 4.5, 6, ramp[4])
        c.rect(4, 10, 12, 2, ramp[1])
        core = (255, 90, 70, 255)
        gradient_disc(c, cx, 8, 2.0 + t * 1.6, SOLAR, 4, 1)
        soft_glow(c, cx, 8, 4 + t * 5, with_alpha(core, int(70 + t * 120)))
        c.rect(int(cx) - 1, 0, 3, 5, ramp[2])
        c.put(int(cx), 0, ramp[4])
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


def sentry_frames(ramp: Ramp, count: int = 4) -> list[Canvas]:
    """Hovering drone with a shield ring — the enemy that punishes greed."""
    frames: list[Canvas] = []
    w, h = 22, 22
    for i in range(count):
        t = i / count * math.tau
        bob = int(round(math.sin(t) * 1.5))
        c = Canvas(w, h)
        cx, cy = w / 2.0, 10.0 + bob
        ring(c, cx, cy, 9.0, 1.6, with_alpha(PLASMA[3], 130))
        for k in range(4):
            a = t * 1.4 + k * math.pi / 2
            px = cx + math.cos(a) * 9
            py = cy + math.sin(a) * 9
            c.disc(px, py, 1.4, PLASMA[4])
        rounded_rect(c, int(cx) - 5, int(cy) - 4, 10, 8, ramp[2], radius=2)
        c.hline(int(cx) - 3, int(cy) - 4, 6, ramp[4])
        c.rect(int(cx) - 3, int(cy) - 2, 6, 3, (18, 22, 30, 255))
        c.rect(int(cx) - 2 + (i % 3), int(cy) - 1, 2, 1, PLASMA[4])
        c.rect(int(cx) - 6, int(cy) - 1, 2, 4, ramp[1])
        c.rect(int(cx) + 4, int(cy) - 1, 2, 4, ramp[1])
        soft_glow(c, cx, cy + 5, 5, with_alpha(PLASMA[3], 90))
        c.outline(outline_for(ramp))
        frames.append(c)
    return frames


# ---------------------------------------------------------------------------
# bosses
# ---------------------------------------------------------------------------


def boss_colossus(count: int = 4) -> list[Canvas]:
    """Floor 1 boss: a siege-plate golem. Slow shoulder roll, glowing core."""
    frames: list[Canvas] = []
    w, h = 52, 56
    for i in range(count):
        t = i / count * math.tau
        sway = int(round(math.sin(t) * 2))
        breathe = int(round(math.cos(t) * 1))
        c = Canvas(w, h)
        cx = w / 2.0
        met, gold = STEEL, GOLD
        # legs
        for side in (-1, 1):
            lx = int(cx + side * 10) - 4
            rounded_rect(c, lx, 40, 8, 14, met[1], radius=2)
            c.hline(lx, 40, 8, met[3])
            c.rect(lx - 1, 51, 10, 4, met[2])
            c.hline(lx - 1, 51, 10, met[3])
        # torso
        rounded_rect(c, int(cx) - 14, 18 + breathe, 28, 24, met[2], radius=4)
        c.hline(int(cx) - 10, 18 + breathe, 20, met[4])
        c.rect(int(cx) - 12, 34 + breathe, 24, 6, met[1])
        for y in range(22 + breathe, 34 + breathe, 4):
            c.hline(int(cx) - 13, y, 26, met[1])
        gradient_disc(c, cx, 28 + breathe, 6.5, SOLAR, 4, 1)
        ring(c, cx, 28 + breathe, 8.0, 1.5, gold[3])
        soft_glow(c, cx, 28 + breathe, 14, with_alpha(SOLAR[4], 90))
        # arms
        for side in (-1, 1):
            ax = int(cx + side * 18) - 4 + side * sway
            rounded_rect(c, ax, 20, 9, 18, met[3], radius=3)
            c.hline(ax + 1, 20, 7, met[4])
            c.rect(ax - 1, 36, 11, 8, met[2])
            c.hline(ax - 1, 36, 11, met[4])
            c.hline(ax, 43, 9, met[0])
        # shoulders
        for side in (-1, 1):
            sx = int(cx + side * 15) - 5
            dome(c, sx + 5, 14, 7.0, 9, gold[2])
            dome(c, sx + 4, 14, 5.0, 6, gold[3])
            c.hline(sx + 1, 22, 9, gold[0])
        # head
        rounded_rect(c, int(cx) - 7, 6 + breathe, 14, 12, met[3], radius=3)
        c.hline(int(cx) - 5, 6 + breathe, 10, met[4])
        c.rect(int(cx) - 6, 11 + breathe, 12, 4, (14, 16, 22, 255))
        c.hline(int(cx) - 5, 12 + breathe, 10, (255, 120, 60, 255))
        c.rect(int(cx) - 4, 12 + breathe, 2, 1, (255, 230, 180, 255))
        c.rect(int(cx) + 2, 12 + breathe, 2, 1, (255, 230, 180, 255))
        c.vline(int(cx), 2 + breathe, 5, gold[3])
        star(c, cx, 2 + breathe, 3, 1.2, 4, gold[4])
        c.outline(DARK)
        frames.append(c)
    return frames


def boss_hive_mother(count: int = 4) -> list[Canvas]:
    """Floor 2 boss: a bloated queen that splits into blobs."""
    frames: list[Canvas] = []
    w, h = 56, 52
    for i in range(count):
        t = i / count * math.tau
        pulse = math.sin(t)
        c = Canvas(w, h)
        cx, cy = w / 2.0, 30.0
        rx = 22 + pulse * 1.5
        ry = 17 - pulse * 1.2
        c.ellipse(cx, cy, rx, ry, with_alpha(TOXIC[2], 230))
        c.ellipse(cx, cy + 3, rx * 0.8, ry * 0.7, TOXIC[1])
        c.ellipse(cx - 5, cy - 6, rx * 0.5, ry * 0.4, with_alpha(TOXIC[4], 170))
        # Larvae swimming inside the sac.
        rng = random.Random(9 + i)
        for _ in range(7):
            lx = cx + rng.uniform(-rx * 0.6, rx * 0.6)
            ly = cy + rng.uniform(-ry * 0.5, ry * 0.5)
            c.ellipse(lx, ly, 2.4, 1.6, with_alpha(BONE[3], 190))
            c.put(int(lx), int(ly), BONE[4])
        # crown of eyes
        for k in range(5):
            a = math.pi + k * math.pi / 4
            ex = cx + math.cos(a) * (rx - 5)
            ey = cy - 6 + math.sin(a) * 6
            c.disc(ex, ey, 3.0, EYE_WHITE)
            c.disc(ex + math.sin(t + k) * 0.8, ey, 1.6, DARK)
        # mandibles
        for side in (-1, 1):
            mx = cx + side * (rx - 3)
            c.line(int(mx), int(cy + 6), int(mx + side * 6), int(cy + 12),
                   TOXIC[0])
            c.line(int(mx), int(cy + 7), int(mx + side * 5), int(cy + 13),
                   TOXIC[1])
        # spawn ports along the underside
        for k in range(4):
            px = cx + (k - 1.5) * 10
            c.ellipse(px, cy + ry - 2, 3.2, 2.2, TOXIC[0])
            if i % 2 == 0:
                c.ellipse(px, cy + ry, 2.0, 1.4, TOXIC[3])
        soft_glow(c, cx, cy, 26, with_alpha(TOXIC[4], 45))
        c.outline(outline_for(TOXIC))
        frames.append(c)
    return frames


def boss_clockwork_choir(count: int = 4) -> list[Canvas]:
    """Floor 3 boss: a stack of orbiting brass rings around a singing core."""
    frames: list[Canvas] = []
    w, h = 52, 56
    for i in range(count):
        t = i / count * math.tau
        c = Canvas(w, h)
        cx, cy = w / 2.0, 26.0
        for k, rad in enumerate((22, 17, 12)):
            squash = 0.35 + 0.12 * math.sin(t + k)
            steps = 44
            for stp in range(steps):
                a = stp / steps * math.tau + t * (1 + k * 0.4)
                px = cx + math.cos(a) * rad
                py = cy + math.sin(a) * rad * squash
                shade = COPPER[3] if math.sin(a) > 0 else COPPER[1]
                c.put(int(px), int(py), shade)
                c.put(int(px), int(py) + 1, COPPER[0])
        gradient_disc(c, cx, cy, 8.0, SOLAR, 4, 1)
        ring(c, cx, cy, 9.5, 1.6, GOLD[3])
        soft_glow(c, cx, cy, 18, with_alpha(SOLAR[4], 80))
        # face plate
        rounded_rect(c, int(cx) - 6, int(cy) - 5, 12, 10, METAL[2], radius=3)
        c.hline(int(cx) - 4, int(cy) - 5, 8, METAL[4])
        for ex in (int(cx) - 4, int(cx) + 2):
            c.rect(ex, int(cy) - 2, 3, 3, (20, 24, 32, 255))
            c.rect(ex, int(cy) - 2, 2, 2, SOLAR[4])
        mouth = 2 + (i % 3)
        c.rect(int(cx) - 2, int(cy) + 2, 5, mouth, (18, 14, 22, 255))
        # pendulum
        swing = math.sin(t) * 8
        c.line(int(cx), int(cy) + 10, int(cx + swing), 48, COPPER[2])
        c.disc(cx + swing, 49, 4.0, GOLD[3])
        c.disc(cx + swing - 1, 48, 2.0, GOLD[4])
        c.outline(DARK)
        frames.append(c)
    return frames


def boss_void_sovereign(count: int = 4) -> list[Canvas]:
    """Final boss: a crowned silhouette that is mostly absence, with a
    starfield where its body should be."""
    frames: list[Canvas] = []
    w, h = 56, 60
    for i in range(count):
        t = i / count * math.tau
        c = Canvas(w, h)
        cx = w / 2.0
        rng = random.Random(31)
        # cloak
        pts = []
        for k in range(13):
            u = k / 12.0
            px = cx + (u - 0.5) * 44
            py = 54 - math.sin(u * math.pi) * 10 + math.sin(t + u * 6) * 1.5
            pts.append((int(px), int(py)))
        body = [(int(cx - 10), 16), (int(cx + 10), 16)] + list(reversed(pts))
        c.polygon(body, VOID[1])
        c.polygon([(int(cx - 8), 18), (int(cx + 8), 18),
                   (int(cx + 16), 46), (int(cx - 16), 46)], VOID[2])
        # starfield inside the cloak
        for _ in range(40):
            sx = rng.randrange(int(cx) - 18, int(cx) + 18)
            sy = rng.randrange(18, 52)
            if c.get(sx, sy)[3] > 0:
                a = 120 + int(120 * abs(math.sin(t + sx * 0.3 + sy * 0.2)))
                c.put(sx, sy, with_alpha(ARCANE[4], a))
        # head — a cowl, wider than it is tall, so the crown has something
        # to actually sit on
        dome(c, cx, 8, 11.0, 12, VOID[1])
        rounded_rect(c, int(cx) - 10, 17, 20, 6, VOID[1], radius=3)
        for ex in (int(cx) - 6, int(cx) + 2):
            c.rect(ex, 14, 5, 3, (10, 8, 16, 255))
            c.rect(ex, 14, 4, 2, ARCANE[4])
            c.put(ex + 1, 14, (255, 255, 255, 255))
        soft_glow(c, cx - 3, 15, 7, with_alpha(ARCANE[4], 110))
        # crown, rooted into the cowl rather than hovering over it
        c.rect(int(cx) - 10, 6, 20, 3, GOLD[1])
        c.hline(int(cx) - 10, 6, 20, GOLD[2])
        for k in range(5):
            hx = int(cx - 8 + k * 4)
            hh = 6 if k % 2 == 0 else 4
            c.vline(hx, 7 - hh, hh + 1, GOLD[3])
            c.vline(hx + 1, 8 - hh, hh, GOLD[2])
            c.put(hx, 7 - hh, GOLD[4])
        # hands
        for side in (-1, 1):
            hx = cx + side * (16 + math.sin(t) * 2)
            c.disc(hx, 32, 3.5, VOID[2])
            gradient_disc(c, hx, 32, 2.4, ARCANE, 4, 2)
        c.outline(DARK)
        frames.append(c)
    return frames


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


NON_HUMANOID: dict[str, tuple] = {
    "blob_green": (blob_frames, (TOXIC, 16, 2)),
    "blob_red": (blob_frames, (BLOOD, 14, 1)),
    "blob_ice": (blob_frames, (ICE, 18, 2)),
    "watcher": (watcher_frames, (ARCANE,)),
    "watcher_void": (watcher_frames, (VOID,)),
    "mothling": (mothling_frames, (CLOTH_PURPLE,)),
    "mothling_ember": (mothling_frames, (FIRE,)),
    "crawler": (crawler_frames, (DIRT,)),
    "crawler_steel": (crawler_frames, (STEEL,)),
    "imp": (imp_frames, (CLOTH_RED,)),
    "turret": (turret_frames, (METAL,)),
    "sentry": (sentry_frames, (STEEL,)),
}

BOSSES: dict[str, object] = {
    "colossus": boss_colossus,
    "hive_mother": boss_hive_mother,
    "clockwork_choir": boss_clockwork_choir,
    "void_sovereign": boss_void_sovereign,
}


def build_non_humanoids() -> dict[str, list[Canvas]]:
    out: dict[str, list[Canvas]] = {}
    for name, (fn, args) in NON_HUMANOID.items():
        out[name] = fn(*args)
    return out


def build_bosses() -> dict[str, list[Canvas]]:
    return {name: fn() for name, fn in BOSSES.items()}
