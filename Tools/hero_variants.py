"""
Ein Musterbogen fuer die Silhouette der Heldin.

Beschreibungen helfen bei Figurendesign nur begrenzt - "nicht wie ein
Dorito" laesst sich auf tausend Arten befolgen. Dieses Werkzeug zeichnet
deshalb alle Kombinationen aus Maskenform und Kopfaufsatz nebeneinander,
beschriftet sie, und man kann eine auswaehlen.

    python3 Tools/hero_variants.py --out bogen.png --scale 6

Die gewaehlte Kombination traegt man dann in gen_characters.py ein:

    MASK_STYLE, CROWN_STYLE = "schild", "gabel"
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image

from pixelkit import Canvas, Palette as P, hash01, hexc, mix, shade

W, H = 24, 32
GROUND = H - 1

MASKS = ["schild", "rund", "lang", "kantig", "glocke"]
CROWNS = ["gabel", "zinken", "stab", "hut"]


# ------------------------------------------------------------------ Masken

def draw_mask(c: Canvas, mx: int, cy: int, style: str) -> tuple[int, int]:
    """Zeichnet die Maske und meldet ihre Ober- und Unterkante."""
    if style == "schild":
        # Oben breit, zum Kinn schmal.
        top, bot = cy - 3, cy + 4
        for y in range(top, bot + 1):
            t = (y - top) / (bot - top)
            half = 2.9 - (t ** 1.4) * 1.7
            c.rect(int(round(mx - half)), y, max(1, int(round(half * 2))), 1,
                   mix(P.BONE, P.BONE_SH, t * 0.5))
        c.rect(mx - 3, top, 6, 1, P.BONE)

    elif style == "rund":
        top, bot = cy - 4, cy + 4
        c.ellipse(mx, cy, 3.6, 4.2, P.BONE)
        c.ellipse(mx - 1.2, cy + 1.2, 2.6, 2.8, P.BONE_SH)
        c.ellipse(mx + 0.4, cy - 0.6, 3.0, 3.4, P.BONE)

    elif style == "lang":
        # Schmal und hoch - eine Larve, kein Gesicht.
        top, bot = cy - 5, cy + 5
        for y in range(top, bot + 1):
            t = (y - top) / (bot - top)
            half = 2.4 * math.sin(math.pi * (0.12 + t * 0.76)) + 0.6
            c.rect(int(round(mx - half)), y, max(1, int(round(half * 2))), 1,
                   mix(P.BONE, P.BONE_SH, t * 0.55))

    elif style == "kantig":
        # Facettiert wie ein Kristall.
        top, bot = cy - 4, cy + 4
        for y in range(top, bot + 1):
            t = (y - top) / (bot - top)
            half = 1.6 + 2.0 * (1 - abs(t - 0.35) / 0.65)
            c.rect(int(round(mx - half)), y, max(1, int(round(half * 2))), 1,
                   mix(P.BONE, P.BONE_SH, t * 0.5))
        c.set(mx - 3, cy - 1, P.BONE_LO)
        c.set(mx + 2, cy - 2, shade(P.BONE, 0.2))

    else:  # glocke
        top, bot = cy - 4, cy + 3
        for y in range(top, bot + 1):
            t = (y - top) / (bot - top)
            half = 2.2 + t * 2.3
            c.rect(int(round(mx - half)), y, max(1, int(round(half * 2))), 1,
                   mix(P.BONE, P.BONE_SH, t * 0.45))
        c.rect(mx - 4, bot, 9, 1, P.BONE_SH)

    # Resonanzschlitz - bei allen gleich, damit man die Form vergleicht.
    sx, sy = mx + 1, cy - 2
    c.rect(sx, sy, 2, 4, P.EYE)
    c.set(sx - 1, sy, P.EYE)
    c.set(sx + 2, sy + 3, P.EYE)
    return top, bot


# ----------------------------------------------------------------- Aufsatz

def draw_crown(c: Canvas, mx: int, top: int, style: str) -> None:
    if style == "gabel":
        # Zwei duenne Zinken in einem V.
        c.rect(mx - 1, top - 1, 3, 1, P.BONE)
        for side in (-1, 1):
            c.line(mx + side, top - 1, mx + side * 4, 1, P.BONE_SH)
            c.set(mx + side * 4, 1, P.AMBER)

    elif style == "zinken":
        # Parallel, wie eine echte Stimmgabel.
        c.rect(mx - 2, top - 2, 5, 2, P.BONE_SH)
        c.rect(mx - 2, top - 2, 5, 1, P.BONE)
        for side in (-1, 1):
            c.rect(mx + side * 2, 1, 1, top - 3, P.BONE_SH)
            c.set(mx + side * 2, 1, P.AMBER)

    elif style == "stab":
        # Ein einzelner Taktstab, leicht geneigt.
        for i in range(top - 2):
            c.set(mx + 1 + int(i * 0.16), top - 2 - i, P.BONE_SH)
        c.set(mx + 1 + int((top - 3) * 0.16), 1, P.AMBER)
        c.rect(mx - 1, top - 2, 4, 1, P.BONE)

    else:  # hut
        # Breite Krempe: die staerkste Silhouette, aber am wenigsten
        # mit dem Klangthema verbunden.
        brim = top - 1
        c.rect(mx - 7, brim, 15, 1, P.CLOAK_LO)
        c.rect(mx - 6, brim - 1, 13, 1, P.CLOAK)
        c.rect(mx - 3, brim - 5, 7, 4, P.CLOAK)
        c.rect(mx - 3, brim - 5, 7, 1, P.CLOAK_HI)
        c.rect(mx - 3, brim - 2, 7, 1, P.AMBER)
        c.set(mx + 4, brim - 3, P.AMBER)


# -------------------------------------------------------------------- Figur

def draw_variant(mask: str, crown: str) -> Canvas:
    c = Canvas(W, H)
    cx = W // 2
    base = GROUND
    shoulder = base - 15
    mask_cy = base - 20

    # Umhang: fuer den Vergleich bei allen gleich.
    for y in range(shoulder, base + 1):
        t = (y - shoulder) / max(1, base - shoulder)
        back = 2.4 + (t ** 1.15) * 5.4
        front = 2.2 + (t ** 1.9) * 3.0
        if t > 0.72:
            front *= 1 - (t - 0.72) / 0.28 * 0.75
        col = mix(P.CLOAK_HI, P.CLOAK_LO, min(1.0, t * 1.3))
        x0 = int(round(cx - back))
        c.rect(x0, y, max(1, int(round(cx + front)) - x0), 1, col)
    for i in range(8):
        x = cx - 8 + i
        for k in range(int(hash01(x * 7, 3) * 2.4)):
            c.set(x, base - k, None)

    c.rect(cx + 2, base - 5, 2, 5, shade(P.CLOAK_LO, -0.1))
    c.rect(cx + 1, base - 2, 4, 2, P.CLOAK_LO)
    c.rect(cx - 4, shoulder, 8, 2, P.CLOAK_HI)
    c.rect(cx - 5, shoulder + 1, 10, 1, P.CLOAK_HI)
    c.set(cx - 5, shoulder, None)
    c.set(cx + 4, shoulder, None)

    # Notenband
    for i in range(13):
        u = i / 13
        c.set(int(cx - 4 - u * 7), int(shoulder + 1 + math.sin(u * 3.4) * (1.2 + u * 1.9) + u * 2.2),
              mix(P.CLOAK_HI, P.BONE_LO, u * 0.5))

    top, _ = draw_mask(c, cx, mask_cy, mask)
    draw_crown(c, cx, top, crown)
    c.outline(hexc("#04050a", 255))
    return c


def build(out: Path, scale: int) -> None:
    cell_w, cell_h = W + 10, H + 14
    sheet = Image.new("RGBA", (cell_w * len(CROWNS) + 26, cell_h * len(MASKS) + 16),
                      (22, 26, 34, 255))

    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for ci, crown in enumerate(CROWNS):
        draw.text((26 + ci * cell_w + 4, 4), f"{ci + 1} {crown}", fill=(150, 170, 180))
    for ri, mask in enumerate(MASKS):
        draw.text((2, 16 + ri * cell_h + cell_h // 2), chr(65 + ri), fill=(150, 170, 180))
        draw.text((2, 16 + ri * cell_h + cell_h // 2 + 10), mask[:5], fill=(90, 105, 115))
        for ci, crown in enumerate(CROWNS):
            img = draw_variant(mask, crown).to_image()
            sheet.alpha_composite(img, (26 + ci * cell_w + 5, 16 + ri * cell_h + 6))

    sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"Musterbogen -> {out}  ({len(MASKS)}x{len(CROWNS)} Varianten)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="vorschau/heldin_bogen.png")
    ap.add_argument("--scale", type=int, default=6)
    a = ap.parse_args()
    build(Path(a.out), a.scale)
