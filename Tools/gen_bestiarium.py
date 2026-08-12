"""
Zeichnet das Bestiarium als Blatt - dasselbe, das im Spiel aufgeschlagen
werden kann.

Der Text stand frueher hier, und damit gab es ihn genau einmal, an der
falschen Stelle. Jetzt steht er in `Bestiarium.swift` und wird hier
gelesen: das Spiel und das Blatt koennen nicht mehr Verschiedenes
behaupten. Leben und Schaden kommen aus `Enemy.swift`, aus demselben
Grund.

    python3 Tools/gen_bestiarium.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw

from pixelkit import Palette as P, hexc, mix
import gen_characters as G

WURZEL = Path(__file__).resolve().parent.parent
GEGNER = WURZEL / "Sources" / "ResonanzCore" / "Entities" / "Enemy.swift"
TEXTE = WURZEL / "Sources" / "ResonanzCore" / "Progress" / "Bestiarium.swift"
AUS = WURZEL / "vorschau" / "bestiarium.png"

Z = 4                       # Vergroesserung der Sprites
SPALTE = 380                # Breite eines Steckbriefs

ZEICHNER = {
    "gabelmaus": G.draw_gabelmaus,
    "klangmotte": G.draw_klangmotte,
    "stilleschreiter": G.draw_stilleschreiter,
    "dissonanzknospe": G.draw_dissonanzknospe,
    "echoscherbe": G.draw_echoscherbe,
    "auftakt": G.draw_auftakt,
}

# Wie viele Bilder je Kreatur nebeneinander stehen. Der Schreiter und der
# Boss sind breit, von ihnen passen weniger.
BILDER = {"gabelmaus": 8, "auftakt": 3}


def texte() -> list[dict]:
    """Liest die Eintraege aus dem Swift-Quelltext."""
    quelle = TEXTE.read_text()
    aus = []
    for block in re.findall(r"Eintrag\(\s*\n(.*?)\n\s*schwelle: (\d+)\)",
                            quelle, re.S):
        koerper, schwelle = block
        art = re.search(r"art: \.(\w+)", koerper)
        name = re.search(r'name: "([^"]+)"', koerper)
        if not art or not name:
            continue

        def zeilen(feld: str) -> list[str]:
            m = re.search(rf"{feld}: \[(.*?)\]", koerper, re.S)
            return re.findall(r'"([^"]*)"', m.group(1)) if m else []

        aus.append(dict(art=art.group(1), name=name.group(1),
                        verhalten=zeilen("verhalten"),
                        deutung=zeilen("deutung"),
                        schwelle=int(schwelle)))
    return aus


def werte() -> dict[str, dict[str, int]]:
    """Liest Leben und Schaden aus dem Spiel."""
    text = GEGNER.read_text()
    aus: dict[str, dict[str, int]] = {}
    for feld in ("maxHealth", "contactDamage"):
        block = re.search(rf"var {feld}: Int \{{(.*?)\n    \}}", text, re.S)
        if not block:
            continue
        for art, zahl in re.findall(r"case \.(\w+): return (\d+)", block.group(1)):
            aus.setdefault(art, {})[feld] = int(zahl)
    return aus


def halbe(n: int) -> str:
    """Schaden steht im Spiel in halben Kristallen - hier lesbar."""
    return f"{n // 2}" if n % 2 == 0 else f"{n // 2},5"


def build() -> None:
    eintraege = texte()
    if not eintraege:
        raise SystemExit("Keine Eintraege in Bestiarium.swift gefunden")
    zahlen = werte()

    hoehe = 240
    breite = SPALTE * len(eintraege) + 40
    bild = Image.new("RGBA", (breite, hoehe + 96), hexc("#080a12"))
    z = ImageDraw.Draw(bild, "RGBA")

    z.text((24, 22), "RESONANZ - DIE BEWOHNER DER VERSTIMMTEN WELT", fill=P.BONE)
    z.text((24, 38),
           "Im Spiel aufschlagbar mit B. Ein Eintrag oeffnet sich erst, "
           "wenn man der Kreatur oft genug begegnet ist.",
           fill=mix(P.BONE, P.INK, 0.45))

    for i, e in enumerate(eintraege):
        ox, oy = 24 + i * SPALTE, 76
        z.text((ox, oy), e["name"], fill=P.TRIM)

        w = zahlen.get(e["art"], {})
        z.text((ox, oy + 14),
               f"Leben {w.get('maxHealth', '?')}   "
               f"Schaden {halbe(w.get('contactDamage', 0))} Kristall   "
               f"oeffnet nach {e['schwelle']}",
               fill=mix(P.BONE, P.INK, 0.35))

        x = ox
        for k in range(BILDER.get(e["art"], 6)):
            c = ZEICHNER[e["art"]](k / BILDER.get(e["art"], 6) * math.tau)
            if x + c.w * Z > ox + SPALTE - 24:
                break
            im = c.to_image().resize((c.w * Z, c.h * Z), Image.NEAREST)
            bild.alpha_composite(im, (x, oy + 34 + (120 - c.h * Z)))
            x += c.w * Z + 4

        y = oy + 164
        for zeile in e["verhalten"]:
            z.text((ox, y), zeile, fill=mix(P.BONE, P.INK, 0.35))
            y += 12
        y += 6
        for zeile in e["deutung"]:
            z.text((ox, y), zeile, fill=mix(P.BONE, P.INK, 0.55))
            y += 12

    AUS.parent.mkdir(exist_ok=True)
    bild.save(AUS)
    print(f"bestiarium -> {AUS} ({bild.width}x{bild.height}), "
          f"{len(eintraege)} Eintraege aus dem Spiel gelesen")


if __name__ == "__main__":
    build()
