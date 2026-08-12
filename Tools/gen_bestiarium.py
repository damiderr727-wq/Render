"""
Zeichnet das Bestiarium: alle Kreaturen nebeneinander, mit ihren Zahlen.

Wie die Karte ist das kein gemaltes Blatt, sondern ein abgeleitetes: die
Bilder kommen aus demselben Code wie die Frames im Atlas, und die Werte
werden aus `Enemy.swift` gelesen. Ein Steckbrief, der andere Zahlen
zeigt als das Spiel, waere schlimmer als gar keiner.

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
QUELLE = WURZEL / "Sources" / "ResonanzCore" / "Entities" / "Enemy.swift"
AUS = WURZEL / "vorschau" / "bestiarium.png"

Z = 4                       # Vergroesserung der Sprites
SPALTE = 380                # Breite eines Steckbriefs

# Nur die Zeichnung und der Text stehen hier - Leben und Schaden kommen
# aus dem Spiel.
KREATUREN = [
    ("gabelmaus", "GABELMAUS", 8,
     ["Huscht in Schueben und laeuft geradeaus",
      "an einem vorbei, statt zu verfolgen.",
      "Gefaehrlich nur, wenn man stehenbleibt.",
      "",
      "Ihre Ohren sind eine Stimmgabel: sie",
      "traegt den Ton spazieren, der Cadence",
      "fehlt. Erster Gegner im Hain."]),
    ("klangmotte", "KLANGMOTTE", 6,
     ["Taumelt auf einer Sinuslinie und driftet",
      "dabei heran. Fliegt, faellt nie.",
      "",
      "Ihre Fluegel sind Wellen, keine Haut.",
      "Was von ihr abfaellt, ist Staub aus",
      "Toenen, die schon verklungen sind."]),
    ("stilleschreiter", "STILLESCHREITER", 6,
     ["Patrouilliert, laedt auf kurze Distanz",
      "durch. Steckt mehr ein als alles andere",
      "im Hain und nimmt anderthalb Kristalle.",
      "",
      "Das Gegenstueck zu Cadence: ein Gefaess",
      "ohne Licht. Er traegt keine Leuchtfarbe -",
      "nur in seinen Fugen steht noch ein Rest."]),
    ("dissonanzknospe", "DISSONANZKNOSPE", 6,
     ["Waechst fest, bewegt sich nie, spuckt",
      "drei schiefe Toene faecherfoermig.",
      "",
      "Keine Blume: eine Schale, die",
      "aufgesprungen ist. Innen stehen drei",
      "Linien, die nicht zueinander passen -",
      "man sieht den Missklang, bevor er kommt."]),
    ("auftakt", "DER GROSSE AUFTAKT", 3,
     ["Erster Boss. Viermal so hoch wie sie,",
      "schwarz, mit einer Krone, die gar nicht",
      "zu ihm gehoert. In der Kapuze: nichts.",
      "",
      "Er kann genau eine Sache - den Takt",
      "vorgeben - und sagt sie viel zu lange",
      "vorher an. Genau dafuer ist er da."]),
    ("echoscherbe", "ECHOSCHERBE", 6,
     ["Prallt frei umher; jede Wand dreht sie",
      "um. Sie zielt nicht, sie ist nur im Weg.",
      "",
      "Hinter ihr stehen zwei blassere Kopien",
      "aelterer Drehungen. Was man trifft, ist",
      "die scharfe vorn - die anderen sind schon",
      "vorbei."]),
]

ZEICHNER = {
    "auftakt": G.draw_auftakt,
    "gabelmaus": G.draw_gabelmaus,
    "klangmotte": G.draw_klangmotte,
    "stilleschreiter": G.draw_stilleschreiter,
    "dissonanzknospe": G.draw_dissonanzknospe,
    "echoscherbe": G.draw_echoscherbe,
}


def werte() -> dict[str, dict[str, int]]:
    """Liest Leben und Schaden aus dem Swift-Quelltext."""
    text = QUELLE.read_text()
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
    zahlen = werte()
    hoehe = 240
    breite = SPALTE * len(KREATUREN) + 40
    bild = Image.new("RGBA", (breite, hoehe + 96), hexc("#080a12"))
    z = ImageDraw.Draw(bild, "RGBA")

    z.text((24, 22), "RESONANZ - DIE BEWOHNER DER VERSTIMMTEN WELT", fill=P.BONE)
    z.text((24, 38),
           "Keiner von ihnen ist boese. Wo Cadence eine Scherbe traegt, "
           "haben sie ein Loch - und das ist gezeichnet.",
           fill=mix(P.BONE, P.INK, 0.45))

    for i, (art, name, bilder, zeilen) in enumerate(KREATUREN):
        ox = 24 + i * SPALTE
        oy = 76
        z.text((ox, oy), name, fill=P.TRIM)

        w = zahlen.get(art, {})
        z.text((ox, oy + 14),
               f"Leben {w.get('maxHealth', '?')}   "
               f"Schaden {halbe(w.get('contactDamage', 0))} Kristall",
               fill=mix(P.BONE, P.INK, 0.35))

        # Die Animation, Bild neben Bild - so sieht man die Bewegung.
        x = ox
        for k in range(bilder):
            c = ZEICHNER[art](k / bilder * math.tau)
            # Erst pruefen, dann setzen: sonst haengt das letzte Bild in
            # der Nachbarspalte, und der grosse Schreiter tat genau das.
            if x + c.w * Z > ox + SPALTE - 24:
                break
            im = c.to_image().resize((c.w * Z, c.h * Z), Image.NEAREST)
            bild.alpha_composite(im, (x, oy + 34 + (120 - c.h * Z)))
            x += c.w * Z + 4

        for k, zeile in enumerate(zeilen):
            z.text((ox, oy + 164 + k * 12), zeile, fill=mix(P.BONE, P.INK, 0.42))

    AUS.parent.mkdir(exist_ok=True)
    bild.save(AUS)
    print(f"bestiarium -> {AUS} ({bild.width}x{bild.height})")


if __name__ == "__main__":
    build()
