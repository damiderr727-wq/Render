"""Top-down 3/4 character rig.

One parametric rig produces the player characters *and* every humanoid enemy.
The camera sits above and slightly in front of the actor — you see the crown
of the head and the face at the same time, which is exactly the cheat Enter
the Gungeon and Blazing Beaks use to make flat sprites sit convincingly on a
floor that is drawn in perspective.

Frames are 20x24 with the feet on row 20, so the renderer anchors every
character identically no matter how tall its hat is.

Vertical layout (rows, top-down):
    0..1    hat / crest / horns
    2..10   head          (cranium 6 rows, jaw 3, face in the lower half)
    11..17  torso
    18..20  legs and boots
    21      ground line — the contact shadow is drawn separately
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .canvas import Canvas
from .palette import (
    BONE, CLOTH_BLUE, CLOTH_GREEN, CLOTH_ORANGE, CLOTH_PURPLE, CLOTH_RED,
    CLOTH_TEAL, COPPER, DIRT, GOLD, ICE, METAL, RGBA, Ramp, SKIN, SKIN_PALE,
    STEEL, TOXIC, VOID, WOOD, outline_for, tint, with_alpha,
)
from .shapes import capsule, dome, rounded_rect

FRAME_W = 20
FRAME_H = 24
GROUND_Y = 21
LEG_TOP = 18
TORSO_TOP = 11
HEAD_BOTTOM = 11

EYE_DARK: RGBA = (20, 16, 30, 255)
EYE_WHITE: RGBA = (238, 240, 250, 255)


@dataclass
class CharSpec:
    """Everything that distinguishes one humanoid from another."""

    name: str
    skin: Ramp = SKIN
    cloth: Ramp = CLOTH_BLUE
    accent: Ramp = GOLD
    hair: Ramp = BONE
    boots: Ramp = WOOD
    head_style: str = "hair"       # hair|hood|helmet|hat|bare|skull|beak|visor
    eye_style: str = "normal"      # normal|angry|dot|cyclops|hollow|goggles
    build: str = "normal"          # small|normal|big
    cape: bool = False
    backpack: bool = False
    shoulders: bool = False
    scarf: bool = False
    horns: bool = False
    glow: RGBA | None = None
    extras: dict = field(default_factory=dict)

    @property
    def body_w(self) -> int:
        return {"small": 9, "normal": 11, "big": 13}[self.build]

    @property
    def head_w(self) -> int:
        return {"small": 10, "normal": 12, "big": 13}[self.build]

    @property
    def head_h(self) -> int:
        return {"small": 8, "normal": 9, "big": 10}[self.build]

    @property
    def lift(self) -> int:
        """Small builds sit lower in the frame, big ones stand taller."""
        return {"small": 2, "normal": 0, "big": -1}[self.build]


# ---------------------------------------------------------------------------
# body parts
# ---------------------------------------------------------------------------


def _legs(c: Canvas, spec: CharSpec, cx: int, top: int, stride: int,
          facing: str) -> None:
    """``stride`` in -1..1 drives the walk cycle; legs lift, never slide."""
    boot = spec.boots
    lw = 3 if spec.build != "big" else 4
    gap = 2 if facing != "side" else 1
    lx = cx - gap - lw + (1 if facing == "side" else 0)
    rx = cx + gap - (1 if facing == "side" else 0)
    for x, lift in ((lx, max(0, stride)), (rx, max(0, -stride))):
        h = 3 + lift
        rounded_rect(c, x, top - lift, lw, h, boot[2], radius=1)
        # Lit cuff at the top, dark sole at the bottom: without this contrast
        # the legs disappear into the torso at gameplay zoom.
        c.hline(x, top - lift, lw, boot[3])
        c.hline(x, top - lift + h - 1, lw, boot[0])


def _torso(c: Canvas, spec: CharSpec, cx: int, top: int, facing: str) -> None:
    w = spec.body_w if facing != "side" else spec.body_w - 3
    h = 7 if spec.build != "small" else 6
    x = cx - w // 2
    cloth = spec.cloth
    rounded_rect(c, x, top, w, h, cloth[2], radius=2)
    c.hline(x + 2, top, w - 4, cloth[3])         # lit shoulder line
    c.vline(x, top + 2, h - 3, cloth[1])
    c.vline(x + w - 1, top + 2, h - 3, cloth[1])
    c.rect(x + 1, top + h - 2, w - 2, 2, cloth[1])

    if facing == "back":
        if spec.backpack:
            pack = spec.accent.shifted("pack", -1)
            rounded_rect(c, cx - 4, top + 1, 8, 5, pack[2], radius=1)
            c.hline(cx - 3, top + 1, 6, pack[3])
            c.hline(cx - 3, top + 3, 6, pack[1])
        else:
            c.vline(cx, top + 1, h - 3, cloth[1])  # spine seam
    else:
        c.line(x + 2, top + 1, x + w - 3, top + h - 4, spec.accent[1])
        c.put(x + 3, top + 2, spec.accent[3])

    if spec.shoulders:
        pad = METAL
        for px in (x - 1, x + w - 2):
            c.rect(px, top - 1, 3, 3, pad[3])
            c.hline(px, top - 1, 3, pad[4])
            c.hline(px, top + 1, 3, pad[1])

    if spec.scarf:
        c.rect(x + 1, top - 1, w - 2, 2, spec.accent[3])
        c.hline(x + 1, top, w - 2, spec.accent[2])
        if facing == "front":
            c.rect(x + w - 3, top + 1, 2, 4, spec.accent[2])
        elif facing == "side":
            c.rect(x - 2, top + 1, 2, 5, spec.accent[2])

    belt = spec.cloth.shifted("belt", -2)
    c.hline(x + 1, top + h - 3, w - 2, belt[1])
    if facing == "front":
        c.rect(cx - 1, top + h - 3, 2, 1, spec.accent[3])


def _arms(c: Canvas, spec: CharSpec, cx: int, top: int, facing: str,
          swing: int) -> None:
    w = spec.body_w if facing != "side" else spec.body_w - 3
    x = cx - w // 2
    sleeve = spec.cloth.shifted("sleeve", -1)
    hand = spec.skin
    if facing == "side":
        # Profile shows one arm swinging forward, the far arm is hidden.
        ay = top + 1 + max(0, swing)
        capsule(c, x + w, ay, 2, 4, sleeve[2])
        c.rect(x + w, ay + 4, 2, 2, hand[2])
        c.put(x + w + 1, ay + 4, hand[3])
        return
    left_y = top + 1 + max(0, swing)
    right_y = top + 1 + max(0, -swing)
    for ax, ay in ((x - 2, left_y), (x + w, right_y)):
        capsule(c, ax, ay, 2, 4, sleeve[2])
        c.rect(ax, ay + 4, 2, 2, hand[2])
    c.put(x - 2, left_y + 4, hand[3])
    c.put(x + w + 1, right_y + 4, hand[3])


def _eye(c: Canvas, spec: CharSpec, x: int, y: int, flip: bool) -> None:
    """A 3x3 eye: white sclera, dark pupil, one specular pixel.

    Big readable eyes are most of what makes these characters likable at
    12 pixels of head.
    """
    style = spec.eye_style
    glow = spec.glow
    if style == "dot":
        c.rect(x + 1, y + 1, 2, 2, glow or EYE_DARK)
        return
    if style == "hollow":
        c.rect(x, y, 3, 3, (12, 10, 18, 255))
        if glow:
            c.rect(x + 1, y + 1, 2, 2, glow)
            c.put(x + 1, y + 1, with_alpha(glow, 255))
        return
    c.rect(x, y, 3, 3, EYE_WHITE)
    px = x + (0 if flip else 1)
    c.rect(px, y + 1, 2, 2, glow or EYE_DARK)
    c.put(px + (1 if flip else 0), y + 1, EYE_WHITE if glow is None
          else with_alpha(glow, 200))
    if style == "angry":
        c.hline(x, y - 1, 3, spec.skin[0])
        c.put(x + (2 if flip else 0), y, spec.skin[0])


def _face(c: Canvas, spec: CharSpec, cx: int, eye_y: int, facing: str) -> None:
    if facing == "back":
        return
    if spec.eye_style == "cyclops":
        c.rect(cx - 2, eye_y, 5, 4, EYE_WHITE)
        c.rect(cx - 1, eye_y + 1, 3, 2, spec.glow or EYE_DARK)
        c.put(cx - 1, eye_y + 1, EYE_WHITE)
        return
    if spec.eye_style == "goggles":
        c.rect(cx - 6, eye_y - 1, 12, 5, METAL[1])
        c.hline(cx - 6, eye_y - 1, 12, METAL[2])
        for gx in (cx - 5, cx + 1):
            c.rect(gx, eye_y, 4, 3, (58, 168, 196, 255))
            c.rect(gx, eye_y, 2, 1, (150, 232, 244, 255))
        return
    if facing == "side":
        _eye(c, spec, cx + 1, eye_y, flip=True)
        return
    _eye(c, spec, cx - 4, eye_y, flip=False)
    _eye(c, spec, cx + 2, eye_y, flip=True)


def _head_shape(c: Canvas, spec: CharSpec, cx: int, top: int, hw: int,
                hh: int, ramp: Ramp, facing: str) -> None:
    """Cranium dome plus a narrower jaw — never a plain ball."""
    crown_h = hh - 3
    jaw_w = hw - 2
    dome(c, cx, top, hw / 2.0, crown_h, ramp[2])
    rounded_rect(c, cx - jaw_w // 2, top + crown_h - 1, jaw_w, 4, ramp[2],
                 radius=2)
    dome(c, cx - 1, top, hw / 2.0 - 1.5, 3, ramp[3])
    c.hline(cx - 3, top, 3, ramp[4])
    c.vline(cx + hw // 2 - 1, top + 2, crown_h, ramp[1])
    c.hline(cx - jaw_w // 2 + 1, top + hh - 1, jaw_w - 2, ramp[1])
    if facing == "side":
        # Nose wedge and a shaded ear are what sell a profile at this size.
        c.put(cx + hw // 2, top + hh - 5, ramp[3])
        c.rect(cx + hw // 2, top + hh - 4, 2, 2, ramp[3])
        c.put(cx + hw // 2 + 1, top + hh - 3, ramp[2])
        c.rect(cx - hw // 2 + 1, top + hh - 5, 2, 3, ramp[1])
        c.vline(cx - hw // 2, top + 2, hh - 4, ramp[1])


def _hair_and_hat(c: Canvas, spec: CharSpec, cx: int, top: int, hw: int,
                  hh: int, facing: str) -> None:
    style = spec.head_style
    hair = spec.hair
    if style == "hair":
        dome(c, cx, top - 1, hw / 2.0 + 0.5, 4, hair[2])
        dome(c, cx - 1, top - 1, hw / 2.0 - 1.5, 3, hair[3])
        c.hline(cx - 2, top - 1, 3, hair[4])
        for side in (-1, 1):
            sx = cx + side * (hw // 2) - (1 if side > 0 else 0)
            c.vline(sx, top + 1, 3, hair[1])
        if facing == "back":
            rounded_rect(c, cx - hw // 2, top, hw, hh - 1, hair[2], radius=3)
            dome(c, cx - 1, top - 1, hw / 2.0 - 1, 4, hair[3])
            c.hline(cx - hw // 2 + 1, top + hh - 2, hw - 2, hair[1])
    elif style == "hood":
        hood = spec.cloth
        dome(c, cx, top - 2, hw / 2.0 + 1, 6, hood[2])
        dome(c, cx - 1, top - 2, hw / 2.0 - 1, 4, hood[3])
        for side in (-1, 1):
            sx = cx + side * (hw // 2 + 1) - (1 if side > 0 else 0)
            c.vline(sx, top, 6, hood[1])
        if facing == "back":
            rounded_rect(c, cx - hw // 2 - 1, top, hw + 2, hh, hood[2],
                         radius=3)
            c.hline(cx - hw // 2, top + hh - 1, hw, hood[1])
        else:
            c.rect(cx - hw // 2, top + 2, hw, 2,
                   tint(hood[0], (0, 0, 0, 255), 0.4))
    elif style in ("helmet", "visor"):
        met = METAL if style == "helmet" else spec.cloth
        dome(c, cx, top - 2, hw / 2.0 + 1, 6, met[3])
        dome(c, cx - 1, top - 2, hw / 2.0 - 1, 4, met[4])
        c.hline(cx - hw // 2 - 1, top + 3, hw + 2, met[1])
        c.vline(cx, top - 2, 2, spec.accent[3])
        if facing != "back":
            slit_y = top + hh - 5
            c.rect(cx - hw // 2, slit_y - 1, hw, 4, (16, 18, 26, 255))
            c.hline(cx - hw // 2 + 1, slit_y, hw - 2, spec.accent[3])
            c.put(cx - hw // 2 + 2, slit_y, EYE_WHITE)
        else:
            rounded_rect(c, cx - hw // 2, top, hw, hh - 1, met[3], radius=3)
            c.hline(cx - hw // 2 + 1, top + hh - 2, hw - 2, met[1])
    elif style == "hat":
        dome(c, cx, top - 1, hw / 2.0, 3, hair[2])
        brim = spec.accent
        c.rect(cx - hw // 2 - 3, top, hw + 6, 2, brim[1])
        c.hline(cx - hw // 2 - 3, top, hw + 6, brim[2])
        crown_top = top - 6
        rounded_rect(c, cx - hw // 2 + 2, crown_top, hw - 4, 7, spec.cloth[2],
                     radius=2)
        c.vline(cx - hw // 2 + 2, crown_top + 1, 5, spec.cloth[3])
        c.hline(cx - hw // 2 + 2, crown_top, hw - 4, spec.cloth[3])
        c.rect(cx - hw // 2 + 2, top - 1, hw - 4, 1, spec.accent[3])
    elif style == "beak":
        dome(c, cx, top - 1, hw / 2.0, 3, hair[3])
        for i, dy in enumerate((-4, -5, -4)):
            c.vline(cx - 1 + i, top + dy, abs(dy) - 1, spec.accent[3 - (i % 2)])
    elif style == "skull":
        c.rect(cx - 3, top + hh - 3, 6, 2, BONE[0])
        for i in range(4):
            c.vline(cx - 3 + i * 2, top + hh - 3, 2, BONE[3])
        c.hline(cx - hw // 2 + 1, top + 1, hw - 2, BONE[4])

    if spec.horns:
        for side in (-1, 1):
            bx = cx + side * (hw // 2)
            c.line(bx, top + 1, bx + side * 2, top - 3, BONE[3])
            c.line(bx, top + 2, bx + side * 2, top - 2, BONE[2])
            c.put(bx + side * 2, top - 4, BONE[4])


def _head(c: Canvas, spec: CharSpec, cx: int, top: int, facing: str) -> None:
    hw = spec.head_w - (3 if facing == "side" else 0)
    hh = spec.head_h
    skin = BONE if spec.head_style == "skull" else spec.skin
    covered = spec.head_style in ("helmet", "visor") or (
        facing == "back" and spec.head_style in ("hair", "hood"))

    if not covered:
        _head_shape(c, spec, cx, top, hw, hh, skin, facing)
    _hair_and_hat(c, spec, cx, top, hw, hh, facing)

    if covered:
        return
    eye_y = top + hh - 5
    _face(c, spec, cx, eye_y, facing)
    if spec.head_style == "beak":
        bill = spec.accent
        if facing == "side":
            c.rect(cx + 1, eye_y + 3, 5, 2, bill[3])
            c.hline(cx + 2, eye_y + 4, 4, bill[1])
        else:
            c.rect(cx - 2, eye_y + 3, 5, 2, bill[3])
            c.hline(cx - 1, eye_y + 4, 3, bill[1])
    elif facing == "front" and spec.eye_style not in ("goggles",):
        c.put(cx, eye_y + 3, skin[1])
        c.put(cx - 1, eye_y + 3, skin[1])


def _cape(c: Canvas, spec: CharSpec, cx: int, top: int, sway: int) -> None:
    cape = spec.accent.shifted("cape", -1)
    w = spec.body_w + 4
    x = cx - w // 2 + sway
    rounded_rect(c, x, top, w, 10, cape[1], radius=2)
    c.rect(x + 1, top + 1, w - 2, 7, cape[2])
    c.hline(x + 2, top + 1, w - 4, cape[3])
    for i in range(0, w - 2, 3):
        c.vline(x + 1 + i, top + 6, 4, cape[1])


# ---------------------------------------------------------------------------
# pose assembly
# ---------------------------------------------------------------------------


def _pose(spec: CharSpec, facing: str, bob: int = 0, stride: int = 0,
          swing: int = 0, cape_sway: int = 0, lean: int = 0) -> Canvas:
    c = Canvas(FRAME_W, FRAME_H)
    cx = FRAME_W // 2
    lift = spec.lift
    torso_h = 7 if spec.build != "small" else 6
    leg_top = LEG_TOP + lift
    torso_top = leg_top - torso_h + 1 + bob
    head_top = torso_top - spec.head_h + 1

    if spec.cape:
        _cape(c, spec, cx, torso_top - 1, cape_sway)
    _legs(c, spec, cx, leg_top, stride, facing)
    _arms(c, spec, cx, torso_top, facing, swing)
    _torso(c, spec, cx, torso_top, facing)
    # Neck shadow: the single line that stops head and torso reading as one
    # block. Drawn onto the torso *after* it, before the head goes on top.
    body_w = spec.body_w if facing != "side" else spec.body_w - 3
    c.hline(cx - body_w // 2 + 1, torso_top, body_w - 2,
            tint(spec.cloth[1], (0, 0, 0, 255), 0.3))
    _head(c, spec, cx + lean + (1 if facing == "side" else 0),
          head_top, facing)

    c.outline(outline_for(spec.cloth))
    return c


def _roll_frames(spec: CharSpec) -> list[Canvas]:
    """A tumble: tuck, spin, land.

    Squash-and-stretch on a tucked silhouette with the head and a boot
    orbiting it, because truly rotating a 20px sprite shreds its edges.
    """
    frames: list[Canvas] = []
    cx = FRAME_W // 2
    steps = [
        (0, 11, 9, 0.05),
        (3, 12, 8, 0.35),
        (5, 10, 10, 0.62),
        (3, 9, 11, 0.85),
        (0, 12, 8, 1.0),
    ]
    boot = spec.boots
    for lift, bw, bh, spin in steps:
        c = Canvas(FRAME_W, FRAME_H)
        top = GROUND_Y - bh - lift
        cy = top + bh / 2.0
        rounded_rect(c, cx - bw // 2, top, bw, bh, spec.cloth[2], radius=4)
        c.hline(cx - bw // 2 + 3, top, bw - 6, spec.cloth[3])
        c.rect(cx - bw // 2 + 1, top + bh - 2, bw - 2, 2, spec.cloth[1])
        ang = spin * math.tau

        def orbit(offset: float, rad_scale: float) -> tuple[int, int]:
            a = ang + offset
            return (cx + int(round(math.cos(a) * (bw / 2.0) * rad_scale)),
                    int(round(cy + math.sin(a) * (bh / 2.0) * rad_scale)))

        bx, by = orbit(0.0, 1.15)
        rounded_rect(c, bx - 1, by - 1, 3, 3, boot[3], radius=1)
        c.put(bx, by, boot[4])
        # The head keeps its own colours through the tumble, otherwise the
        # roll reads as a featureless ball of cloth.
        hx, hy = orbit(math.pi, 1.05)
        skin = BONE if spec.head_style == "skull" else spec.skin
        rounded_rect(c, hx - 3, hy - 3, 6, 6, skin[2], radius=2)
        c.hline(hx - 2, hy - 3, 4, skin[3])
        c.rect(hx - 3, hy - 3, 6, 2, spec.hair[2])
        c.hline(hx - 2, hy - 3, 4, spec.hair[3])
        c.rect(hx - 2, hy, 2, 2, EYE_WHITE)
        c.put(hx - 1, hy + 1, EYE_DARK)
        c.outline(outline_for(spec.cloth))
        frames.append(c)
    return frames


def _hurt_frames(spec: CharSpec) -> list[Canvas]:
    """Knocked back and squinting. The white hit-flash is a renderer effect,
    so the sprite itself stays readable in the atlas."""
    c = _pose(spec, "front", bob=-1, stride=0, swing=-1, lean=-1)
    cx = FRAME_W // 2
    eye_y = (LEG_TOP + spec.lift - (7 if spec.build != "small" else 6) + 1
             - spec.head_h + 1 - 1) + spec.head_h - 5
    if spec.eye_style not in ("goggles", "hollow", "cyclops"):
        for ex in (cx - 5, cx + 1):
            c.rect(ex, eye_y + 1, 3, 1, spec.skin[0])
    return [c]


def _death_frames(spec: CharSpec) -> list[Canvas]:
    """Flatten into the floor while puffing apart."""
    frames: list[Canvas] = []
    base = _pose(spec, "front", stride=0, swing=0)
    for i, squash in enumerate((0, 4, 8, 11)):
        c = Canvas(FRAME_W, FRAME_H)
        alpha = 1.0 - i * 0.2
        for y in range(base.h):
            for x in range(base.w):
                p = base.get(x, y)
                if p[3] == 0:
                    continue
                ty = GROUND_Y - 1 - int((GROUND_Y - 1 - y) *
                                        (1.0 - squash / 13.0))
                tx = x + int(round((x - FRAME_W / 2.0) * squash / 26.0))
                c.put(tx, ty, with_alpha(p, int(p[3] * alpha)))
        for k in range(i * 3):
            ang = k * 1.9 + i
            px = FRAME_W // 2 + int(math.cos(ang) * (3 + i * 2))
            py = GROUND_Y - 5 + int(math.sin(ang) * (2 + i)) - i
            c.put(px, py, with_alpha(spec.cloth[3], max(40, 190 - i * 40)))
        frames.append(c)
    return frames


def build_character(spec: CharSpec) -> dict[str, list[Canvas]]:
    """Full animation set for one humanoid.

    Side frames face right; the renderer mirrors them for left, which halves
    the atlas and guarantees the two sides match.
    """
    anims: dict[str, list[Canvas]] = {}
    for facing in ("front", "side", "back"):
        anims[f"idle_{facing}"] = [
            _pose(spec, facing),
            _pose(spec, facing, bob=-1, cape_sway=1),
        ]
        anims[f"walk_{facing}"] = [
            _pose(spec, facing, bob=0, stride=1, swing=1),
            _pose(spec, facing, bob=-1, stride=1, swing=1, cape_sway=1),
            _pose(spec, facing, bob=0, stride=0, swing=0),
            _pose(spec, facing, bob=0, stride=-1, swing=-1),
            _pose(spec, facing, bob=-1, stride=-1, swing=-1, cape_sway=-1),
            _pose(spec, facing, bob=0, stride=0, swing=0),
        ]
    anims["roll"] = _roll_frames(spec)
    anims["hurt"] = _hurt_frames(spec)
    anims["die"] = _death_frames(spec)
    return anims


def build_portrait(spec: CharSpec, size: int = 32) -> Canvas:
    """Bust shot for character select and the HUD."""
    c = Canvas(size, size)
    bg = spec.cloth.shifted("bg", -2)
    c.rect(0, 0, size, size, bg[1])
    for y in range(0, size, 4):
        c.hline(0, y, size, bg[2])
    zoom = _pose(spec, "front").scaled(2)
    c.blit(zoom, size // 2 - FRAME_W, -4)
    c.frame(0, 0, size, size, spec.accent[2])
    c.frame(1, 1, size - 2, size - 2, spec.accent[0])
    return c


# ---------------------------------------------------------------------------
# roster
# ---------------------------------------------------------------------------


def player_specs() -> list[CharSpec]:
    """The six playable characters. Each pairs a silhouette with a fantasy."""
    return [
        CharSpec("marshal", skin=SKIN, cloth=CLOTH_BLUE, accent=GOLD,
                 hair=COPPER, boots=WOOD, head_style="hat", scarf=True,
                 extras={"title": "The Marshal"}),
        CharSpec("stray", skin=SKIN_PALE, cloth=CLOTH_PURPLE, accent=CLOTH_TEAL,
                 hair=BONE, boots=DIRT, head_style="hood", cape=True,
                 eye_style="dot",
                 extras={"title": "The Stray"}),
        CharSpec("bulwark", skin=SKIN, cloth=STEEL, accent=GOLD, hair=METAL,
                 boots=METAL, head_style="helmet", build="big", shoulders=True,
                 extras={"title": "The Bulwark"}),
        CharSpec("tinker", skin=SKIN_PALE, cloth=CLOTH_ORANGE, accent=COPPER,
                 hair=CLOTH_RED, boots=COPPER, head_style="hair",
                 eye_style="goggles",
                 backpack=True, build="small", extras={"title": "The Tinker"}),
        CharSpec("beak", skin=BONE, cloth=CLOTH_GREEN, accent=CLOTH_ORANGE,
                 hair=CLOTH_GREEN, boots=CLOTH_ORANGE, head_style="beak",
                 eye_style="dot",
                 build="small", extras={"title": "The Beak"}),
        CharSpec("hexe", skin=SKIN_PALE, cloth=VOID, accent=TOXIC, hair=ICE,
                 boots=CLOTH_PURPLE, head_style="hat", cape=True,
                 eye_style="hollow",
                 glow=(140, 240, 180, 255), extras={"title": "The Hexe"}),
    ]
