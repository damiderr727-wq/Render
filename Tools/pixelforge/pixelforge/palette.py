"""Color ramps for PixelForge.

Every material in the game is described by a *ramp*: an ordered list of
colours from darkest to lightest. Sprite code never picks a raw colour, it
picks ``ramp[i]`` — that is what keeps hundreds of procedurally generated
sprites looking like they came from the same artist.

The palette is deliberately small and slightly desaturated in the mid tones
with punchy highlights, which is what gives Enter the Gungeon / Blazing Beaks
their readable-at-16px look.
"""

from __future__ import annotations

RGBA = tuple[int, int, int, int]


def _hex(value: str, alpha: int = 255) -> RGBA:
    value = value.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


class Ramp:
    """A 5-step shading ramp: 0 = outline/darkest, 4 = highlight."""

    __slots__ = ("name", "colors")

    def __init__(self, name: str, *hexes: str) -> None:
        self.name = name
        self.colors: list[RGBA] = [_hex(h) for h in hexes]

    def __getitem__(self, index: int) -> RGBA:
        # Clamp instead of wrapping: shading maths often over/undershoots by
        # one and a wrapped highlight in place of a shadow looks broken.
        index = max(0, min(len(self.colors) - 1, index))
        return self.colors[index]

    def __len__(self) -> int:
        return len(self.colors)

    @property
    def dark(self) -> RGBA:
        return self.colors[0]

    @property
    def mid(self) -> RGBA:
        return self.colors[len(self.colors) // 2]

    @property
    def light(self) -> RGBA:
        return self.colors[-1]

    def shifted(self, name: str, delta: int) -> "Ramp":
        """A copy of this ramp biased darker (negative) or lighter."""
        out = Ramp.__new__(Ramp)
        out.name = name
        out.colors = [self[i + delta] for i in range(len(self.colors))]
        return out


TRANSPARENT: RGBA = (0, 0, 0, 0)

# --- structural -----------------------------------------------------------
STONE = Ramp("stone", "#0d0c14", "#171525", "#2a2740", "#4b4668", "#7d78a0")
BRICK = Ramp("brick", "#161018", "#2f2130", "#4a3245", "#67485c", "#8b6478")
# Warmer and lighter than the walls on purpose: the floor is where the
# player looks, so it is the brightest large surface in the frame.
FLOOR = Ramp("floor", "#2a2430", "#3e3644", "#544a58", "#6b5f6d", "#847686")
DIRT = Ramp("dirt", "#26191d", "#3b2a2e", "#523c3e", "#6b5150", "#886a66")
WOOD = Ramp("wood", "#1c1210", "#3d2419", "#5e3a24", "#835734", "#ab7c4f")
BONE = Ramp("bone", "#2b2722", "#544d43", "#867c6b", "#b6ab94", "#e4d9bd")

# --- materials ------------------------------------------------------------
METAL = Ramp("metal", "#0e1016", "#22262f", "#3c424f", "#616a79", "#98a1ad")
STEEL = Ramp("steel", "#101823", "#1e2f42", "#345066", "#557a91", "#8bb2c4")
GOLD = Ramp("gold", "#2f1c07", "#6b4310", "#a9761b", "#dfb03a", "#ffe58f")
COPPER = Ramp("copper", "#2a1208", "#5c2a11", "#8f481f", "#c0733a", "#e8a866")
RUBBER = Ramp("rubber", "#0a0a0d", "#16161d", "#24242f", "#343443", "#474758")

# --- character ------------------------------------------------------------
SKIN = Ramp("skin", "#48281a", "#7a4a2d", "#b06f43", "#d69a68", "#f2c496")
SKIN_PALE = Ramp("skin_pale", "#4b3328", "#7d5a45", "#b08a6c", "#d8b494", "#f6e0c4")
CLOTH_BLUE = Ramp("cloth_blue", "#0f1a35", "#1d3160", "#2f4f99", "#5079cc", "#87abee")
CLOTH_RED = Ramp("cloth_red", "#2f0c14", "#5f1622", "#98262f", "#c94a4a", "#ee8175")
CLOTH_GREEN = Ramp("cloth_green", "#0d2418", "#1a4327", "#2b6f39", "#48a04e", "#84cf70")
CLOTH_PURPLE = Ramp("cloth_purple", "#1b1030", "#331b57", "#542f8b", "#7f52c2", "#b088e6")
CLOTH_TEAL = Ramp("cloth_teal", "#08262b", "#0f454c", "#1a7078", "#2ea6a4", "#68d8c8")
CLOTH_ORANGE = Ramp("cloth_orange", "#331405", "#63290a", "#9c4712", "#d4762a", "#f6ac55")

# --- energy / vfx ---------------------------------------------------------
FIRE = Ramp("fire", "#3d0c04", "#872006", "#cd4b0c", "#f5921d", "#ffe07a")
TOXIC = Ramp("toxic", "#0f2a12", "#245f1f", "#43992a", "#79cf39", "#c2f566")
ICE = Ramp("ice", "#0c2733", "#154b62", "#277f9b", "#59b6cc", "#b4ecf4")
ARCANE = Ramp("arcane", "#1d0b33", "#3a1663", "#642aa1", "#9a55d8", "#d29cf7")
VOID = Ramp("void", "#07060d", "#150f22", "#261a3c", "#3d2b5c", "#5b4483")
BLOOD = Ramp("blood", "#2a050a", "#560a13", "#8c141d", "#c02a29", "#e85d4a")
PLASMA = Ramp("plasma", "#062c33", "#0a5a63", "#12939c", "#3ad6d0", "#a6fbf0")
SOLAR = Ramp("solar", "#3a2405", "#7a4c07", "#c08211", "#f4c62c", "#fff6a8")

# --- ui -------------------------------------------------------------------
UI_DARK = Ramp("ui_dark", "#08080d", "#101018", "#1b1b26", "#282836", "#3a3a4c")
UI_LIGHT = Ramp("ui_light", "#4a4a5e", "#6d6d84", "#9494a8", "#bcbccb", "#eeeef5")

ALL_RAMPS: dict[str, Ramp] = {
    ramp.name: ramp
    for ramp in (
        STONE, BRICK, FLOOR, DIRT, WOOD, BONE,
        METAL, STEEL, GOLD, COPPER, RUBBER,
        SKIN, SKIN_PALE, CLOTH_BLUE, CLOTH_RED, CLOTH_GREEN,
        CLOTH_PURPLE, CLOTH_TEAL, CLOTH_ORANGE,
        FIRE, TOXIC, ICE, ARCANE, VOID, BLOOD, PLASMA, SOLAR,
        UI_DARK, UI_LIGHT,
    )
}

# Outlines are never pure black — a very dark tint of the sprite's dominant
# hue keeps sprites from looking like stickers pasted on the floor.
OUTLINE_ALPHA = 235


def outline_for(ramp: Ramp) -> RGBA:
    r, g, b, _ = ramp[0]
    return (max(0, r - 6), max(0, g - 6), max(0, b - 8), OUTLINE_ALPHA)


def tint(color: RGBA, other: RGBA, amount: float) -> RGBA:
    """Blend ``color`` toward ``other``. Used for rim light and team colours."""
    amount = max(0.0, min(1.0, amount))
    return (
        round(color[0] + (other[0] - color[0]) * amount),
        round(color[1] + (other[1] - color[1]) * amount),
        round(color[2] + (other[2] - color[2]) * amount),
        color[3],
    )


def with_alpha(color: RGBA, alpha: int) -> RGBA:
    return (color[0], color[1], color[2], max(0, min(255, alpha)))
