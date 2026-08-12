"""
Das Weltbild: die ganze Welt als gemalte Karte.

Es gibt in diesem Werkzeugkasten schon zwei Karten, und beide werden aus
den echten Raumdaten abgeleitet - eine technische zum Pruefen, eine
gezeichnete zum Anschauen. Beide koennen nur zeigen, was schon gebaut
ist, und beide bestehen deshalb aus Kacheln.

Das hier ist etwas anderes. Es ist kein Abbild, sondern ein Vorhaben:
was die Welt werden soll, wenn sie fertig ist. Darum wird hier nichts
abgeleitet - jedes Gebiet ist von Hand gesetzt, hat einen Umriss, einen
Grund, ein Wahrzeichen und eine Farbe. Was heute erst neun Raeume hat,
steht hier schon in voller Groesse.

    python3 Tools/gen_weltbild.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pixelkit import hash01, hexc, mix

WURZEL = Path(__file__).resolve().parent.parent
AUS = WURZEL / "vorschau" / "weltbild.png"

B, H = 2400, 1560

GRUND = hexc("#070a12")
PERGAMENT = hexc("#c9bda0")
GOLD = hexc("#d9b268")


def schrift(groesse: int, fett: bool = False):
    for pfad in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf"
                 % ("-Bold" if fett else ""),
                 "/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf"
                 % ("Bold" if fett else "Regular")):
        try:
            return ImageFont.truetype(pfad, groesse)
        except OSError:
            continue
    return ImageFont.load_default(size=groesse)


# --------------------------------------------------------------- Werkzeug

def rauschkontur(punkte, staerke: float, saat: int, dichte: int = 3):
    """
    Zieht einen Umriss durch gesetzte Punkte und raut ihn auf.

    Zwischen zwei Stuetzpunkten wird interpoliert und jeder Zwischenpunkt
    ein Stueck versetzt. Das ist der Unterschied zwischen einer Form, die
    jemand gezeichnet hat, und einer, die ein Rechner erzeugt hat: die
    Absicht steckt in den Stuetzpunkten, das Leben in der Abweichung.
    """
    aus = []
    n = len(punkte)
    for i in range(n):
        x0, y0 = punkte[i]
        x1, y1 = punkte[(i + 1) % n]
        schritte = max(2, int(math.dist((x0, y0), (x1, y1)) / dichte))
        for k in range(schritte):
            t = k / schritte
            # Weich blenden statt gerade ziehen: Gelaende hat keine Kanten.
            w = t * t * (3 - 2 * t)
            x = x0 + (x1 - x0) * w
            y = y0 + (y1 - y0) * w
            r = (hash01(int(x), saat + i) - 0.5)
            r2 = (hash01(saat + i, int(y)) - 0.5)
            aus.append((x + r * staerke, y + r2 * staerke))
    return aus


def gebiet(bild: Image.Image, punkte, leucht, fuellung, saat: int,
           glut: float = 1.0) -> None:
    """Eine Landmasse: Schein nach aussen, dunkle Flaeche, leuchtender Rand."""
    kontur = rauschkontur(punkte, 9, saat)

    schein = Image.new("RGBA", bild.size, (0, 0, 0, 0))
    ImageDraw.Draw(schein, "RGBA").polygon(kontur, fill=(*leucht[:3], int(60 * glut)))
    bild.alpha_composite(schein.filter(ImageFilter.GaussianBlur(34)))

    flaeche = Image.new("RGBA", bild.size, (0, 0, 0, 0))
    fz = ImageDraw.Draw(flaeche, "RGBA")
    fz.polygon(kontur, fill=(*fuellung[:3], 252))
    # Innen ein zweiter, hellerer Kern - eine Flaeche in einem Ton ist tot.
    innen = rauschkontur([(x + (sum(p[0] for p in punkte) / len(punkte) - x) * 0.32,
                           y + (sum(p[1] for p in punkte) / len(punkte) - y) * 0.32)
                          for x, y in punkte], 7, saat + 5)
    fz.polygon(innen, fill=(*mix(fuellung, leucht, 0.18)[:3], 200))
    bild.alpha_composite(flaeche.filter(ImageFilter.GaussianBlur(1.2)))

    z = ImageDraw.Draw(bild, "RGBA")
    z.line(kontur + [kontur[0]], fill=(*leucht[:3], 110), width=9, joint="curve")
    z.line(kontur + [kontur[0]], fill=(*leucht[:3], 255), width=3, joint="curve")


def baum(z, x: float, y: float, h: float, farbe, saat: int) -> None:
    """Ein Nadelbaum als Silhouette - das Wahrzeichen des Hains."""
    z.line([x, y, x, y - h], fill=(*farbe[:3], 220), width=max(2, int(h * 0.05)))
    lagen = 5
    for i in range(lagen):
        t = i / lagen
        breite = h * 0.34 * (1 - t) + 4
        yy = y - h * (0.28 + t * 0.62)
        z.polygon([(x - breite, yy), (x, yy - h * 0.22), (x + breite, yy)],
                  fill=(*farbe[:3], int(150 + 70 * t)))


def bogen(z, x: float, y: float, w: float, h: float, farbe) -> None:
    """Ein Spitzbogen - das Wahrzeichen der Kathedrale."""
    z.line([x - w, y, x - w, y - h * 0.55], fill=(*farbe[:3], 210), width=3)
    z.line([x + w, y, x + w, y - h * 0.55], fill=(*farbe[:3], 210), width=3)
    schritte = 22
    vor = None
    for i in range(schritte + 1):
        t = i / schritte
        px = x - w + 2 * w * t
        py = y - h * 0.55 - math.sin(t * math.pi) ** 0.7 * h * 0.45
        if vor:
            z.line([vor, (px, py)], fill=(*farbe[:3], 230), width=3)
        vor = (px, py)


def kristall(z, x: float, y: float, h: float, farbe, saat: int) -> None:
    """Ein Kristallzahn - das Wahrzeichen der Grotten."""
    b = h * 0.22
    neig = (hash01(saat, int(x)) - 0.5) * h * 0.25
    z.polygon([(x - b, y), (x + b, y), (x + neig, y - h)],
              fill=(*farbe[:3], 150))
    z.line([(x - b, y), (x + neig, y - h)], fill=(*farbe[:3], 250), width=2)
    z.line([(x + neig, y - h), (x + b, y)], fill=(*mix(farbe, GRUND, 0.5)[:3], 220),
           width=2)


def riss(z, x: float, y: float, laenge: float, richtung: float, farbe,
         saat: int, tiefe: int = 3) -> None:
    """Ein Riss, der sich verzweigt - das Wahrzeichen der Dissonanz."""
    if tiefe <= 0 or laenge < 8:
        return
    x1 = x + math.cos(richtung) * laenge
    y1 = y + math.sin(richtung) * laenge
    z.line([x, y, x1, y1], fill=(*farbe[:3], 120 + tiefe * 35), width=tiefe)
    for k in (-1, 1):
        if hash01(saat, tiefe * 7 + k) > 0.25:
            riss(z, x1, y1, laenge * 0.62,
                 richtung + k * (0.5 + hash01(int(x1), saat) * 0.5),
                 farbe, saat + 3, tiefe - 1)


# ---------------------------------------------------------------- Gebiete
#
# Von Hand gesetzt, nicht abgeleitet. Jedes Gebiet hat eine Lage in der
# Welt, eine Form, eine Farbe und ein Wahrzeichen - und eine Groesse, die
# dem entspricht, was es werden soll, nicht dem, was schon gebaut ist.

GEBIETE = [
    dict(name="DER SCHLAFENDE HAIN", kurz="Hain",
         leucht=hexc("#8fd8a0"), fuell=hexc("#16301f"), wappen="baum",
         text=["Wo die Welt sich selbst sang.", "Jetzt haelt sie den Atem an."],
         punkte=[(240, 640), (470, 585), (720, 605), (860, 680), (900, 810),
                 (820, 940), (600, 990), (360, 950), (215, 850), (190, 730)]),
    dict(name="DIE KATHEDRALE DER FUGEN", kurz="Kathedrale",
         leucht=hexc("#b9a6ef"), fuell=hexc("#211a35"), wappen="bogen",
         text=["Vier Stimmen, die einander",
               "nie ins Wort fielen."],
         punkte=[(940, 350), (1240, 300), (1500, 355), (1560, 490),
                 (1480, 640), (1240, 690), (1010, 630), (900, 500)]),
    dict(name="DIE RESONANZKAVERNEN", kurz="Grotten",
         leucht=hexc("#7fd4f0"), fuell=hexc("#122736"), wappen="kristall",
         text=["Hier wuchs der Klang zu Stein.",
               "Man hoert sich selbst zurueckkommen."],
         punkte=[(1000, 900), (1300, 840), (1620, 890), (1760, 1010),
                 (1700, 1180), (1420, 1250), (1120, 1200), (960, 1060)]),
    dict(name="DAS HERZ DER DISSONANZ", kurz="Dissonanz",
         leucht=hexc("#f08a7a"), fuell=hexc("#2e1418"), wappen="riss",
         text=["Nicht still. Alles zugleich."],
         punkte=[(1790, 620), (2050, 580), (2210, 660), (2240, 810),
                 (2110, 930), (1870, 930), (1760, 790)]),
]

# Gaenge zwischen den Gebieten: von Hand gelegt, wie Wurzeln.
GAENGE = [
    ((870, 700), (990, 520), hexc("#8fd8a0")),
    ((880, 860), (1010, 950), hexc("#8fd8a0")),
    ((1300, 680), (1290, 850), hexc("#b9a6ef")),
    ((1540, 560), (1780, 700), hexc("#b9a6ef")),
    ((1700, 990), (1900, 920), hexc("#7fd4f0")),
]


def build() -> None:
    bild = Image.new("RGBA", (B, H), GRUND)
    z = ImageDraw.Draw(bild, "RGBA")

    # ---- Der Grund: kein Schwarz, sondern Tiefe. Schwaden, dann Staub.
    dunst = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    dz = ImageDraw.Draw(dunst, "RGBA")
    for i in range(120):
        x, y = hash01(i, 3) * B, hash01(i, 7) * H
        r = 80 + hash01(i, 11) * 320
        dz.ellipse([x - r, y - r * 0.45, x + r, y + r * 0.45],
                   fill=(*hexc("#16203a")[:3], 22))
    bild.alpha_composite(dunst.filter(ImageFilter.GaussianBlur(60)))
    for i in range(1400):
        x, y = int(hash01(i, 41) * B), int(hash01(i, 53) * H)
        z.point((x, y), fill=(*PERGAMENT[:3], int(12 + hash01(i, 67) * 40)))

    # ---- Die Gebiete
    for i, g in enumerate(GEBIETE):
        gebiet(bild, g["punkte"], g["leucht"], g["fuell"], saat=i * 31 + 11)

    # ---- Die Gaenge dazwischen, als Wurzelstraenge.
    for (a, b, farbe) in GAENGE:
        strang = rauschkontur([a, b], 6, saat=int(a[0]) % 97, dichte=6)
        z.line(strang, fill=(*farbe[:3], 90), width=7, joint="curve")
        z.line(strang, fill=(*farbe[:3], 190), width=2, joint="curve")

    # ---- Die Wahrzeichen. Sie stehen im Gebiet, nicht daneben - erst sie
    # machen aus einem Fleck einen Ort.
    for i, g in enumerate(GEBIETE):
        xs = [p[0] for p in g["punkte"]]
        ys = [p[1] for p in g["punkte"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        mitte = ((x0 + x1) / 2, (y0 + y1) / 2)
        farbe = g["leucht"]

        # Die Wahrzeichen werden auf eine eigene Ebene gezeichnet und dann
        # auf das Gebiet beschnitten. Sonst ragen sie darueber hinaus -
        # ein Kristall, der aus seiner Hoehle heraussteht, ist kein
        # Wahrzeichen mehr, sondern ein Fehler.
        ebene = Image.new("RGBA", bild.size, (0, 0, 0, 0))
        z = ImageDraw.Draw(ebene, "RGBA")

        if g["wappen"] == "baum":
            # Ein Hain ist eine Reihe: vorn hohe Baeume, dahinter kleine.
            for k in range(11):
                t = k / 10
                x = x0 + 60 + t * (x1 - x0 - 120)
                y = mitte[1] + 90 - abs(t - 0.5) * 90
                hoehe = 95 + hash01(k, 5) * 70 - abs(t - 0.5) * 45
                baum(z, x, y, hoehe, mix(farbe, GRUND, 0.35 + t * 0.2), k)
            # Der gefallene Stamm, quer.
            z.line([x0 + 90, y1 - 70, x1 - 140, y1 - 40],
                   fill=(*mix(farbe, GRUND, 0.45)[:3], 200), width=13)
        elif g["wappen"] == "bogen":
            for k in range(4):
                x = x0 + 130 + k * 145
                bogen(z, x, y1 - 70, 46, 165, mix(farbe, GRUND, 0.25))
            # Die Orgel im Ruecken: Pfeifen verschiedener Laenge.
            for k in range(9):
                x = x0 + 120 + k * 145 / 2.2
                hoehe = 60 + abs(math.sin(k * 1.1)) * 90
                z.line([x, y0 + 120, x, y0 + 120 - hoehe],
                       fill=(*mix(farbe, GRUND, 0.4)[:3], 170), width=9)
        elif g["wappen"] == "kristall":
            for k in range(14):
                t = k / 13
                x = x0 + 70 + t * (x1 - x0 - 140)
                y = mitte[1] + 110 - abs(math.sin(t * 3.1)) * 40
                kristall(z, x, y, 70 + hash01(k, 9) * 95, farbe, k)
            # Der See, aus dem sie wachsen.
            z.line([x0 + 80, mitte[1] + 118, x1 - 80, mitte[1] + 118],
                   fill=(*farbe[:3], 120), width=5)
        else:
            riss(z, mitte[0], y0 + 40, 150, math.pi / 2 + 0.2, farbe, 17, tiefe=4)
            riss(z, mitte[0] - 90, y0 + 60, 120, math.pi / 2 - 0.4, farbe, 29, tiefe=3)
            # Das Herz selbst: zwei Kreise, die nicht zusammenpassen.
            for k, r in enumerate((58, 40, 22)):
                z.ellipse([mitte[0] - r + k * 6, mitte[1] - r,
                           mitte[0] + r + k * 6, mitte[1] + r],
                          outline=(*farbe[:3], 200 - k * 40), width=4)

        maske = Image.new("L", bild.size, 0)
        ImageDraw.Draw(maske).polygon(rauschkontur(g["punkte"], 9, i * 31 + 11),
                                      fill=255)
        maske = maske.filter(ImageFilter.GaussianBlur(2))
        ebene.putalpha(Image.composite(ebene.getchannel("A"),
                                       Image.new("L", bild.size, 0), maske))
        bild.alpha_composite(ebene)

    z = ImageDraw.Draw(bild, "RGBA")

    # ---- Beschriftung
    gross = schrift(40, fett=True)
    klein = schrift(21)
    for g in GEBIETE:
        xs = [p[0] for p in g["punkte"]]
        ys = [p[1] for p in g["punkte"]]
        cx = (min(xs) + max(xs)) / 2
        oben = min(ys) - 78
        marke = Image.new("RGBA", (len(g["name"]) * 30, 120), (0, 0, 0, 0))
        mz = ImageDraw.Draw(marke, "RGBA")
        mz.text((0, 0), g["name"], fill=(*g["leucht"][:3], 235), font=gross)
        for k, zeile in enumerate(g["text"]):
            mz.text((2, 52 + k * 26), zeile,
                    fill=(*mix(g["leucht"], PERGAMENT, 0.5)[:3], 170), font=klein)
        marke = marke.rotate(-2, expand=True, resample=Image.BICUBIC)
        bild.alpha_composite(marke, (int(cx - marke.width / 2), int(oben - 40)))

    # ---- Rahmen und Titel. Eine Karte ohne Rand ist ein Ausschnitt.
    rand = 46
    for i, (breite, alpha) in enumerate(((5, 210), (2, 120))):
        d = rand + i * 12
        z.rectangle([d, d, B - 1 - d, H - 1 - d],
                    outline=(*GOLD[:3], alpha), width=breite)
    # Ecken: vier kleine Stimmgabeln statt Zierrat.
    for ex, ey, sx, sy in ((rand, rand, 1, 1), (B - rand, rand, -1, 1),
                           (rand, H - rand, 1, -1), (B - rand, H - rand, -1, -1)):
        # Ein Stiel diagonal nach innen, daran zwei Zinken nach aussen -
        # dieselbe Gabel, die Cadence in sich traegt.
        z.line([ex + sx * 20, ey + sy * 20, ex + sx * 74, ey + sy * 74],
               fill=(*GOLD[:3], 210), width=4)
        for dx, dy in ((1, 0), (0, 1)):
            z.line([ex + sx * 74, ey + sy * 74,
                    ex + sx * (74 + dx * 46), ey + sy * (74 + dy * 46)],
                   fill=(*GOLD[:3], 210), width=4)
            z.ellipse([ex + sx * (74 + dx * 46) - 5, ey + sy * (74 + dy * 46) - 5,
                       ex + sx * (74 + dx * 46) + 5, ey + sy * (74 + dy * 46) + 5],
                      fill=(*GOLD[:3], 230))

    titel = schrift(96, fett=True)
    unter = schrift(26)
    z.text((B / 2, 108), "RESONANZ", fill=PERGAMENT, font=titel, anchor="mm")
    z.text((B / 2, 168), "DIE WELT, WIE SIE WERDEN SOLL",
           fill=(*mix(PERGAMENT, GRUND, 0.42)[:3], 230), font=unter, anchor="mm")
    z.line([B / 2 - 320, 192, B / 2 + 320, 192], fill=(*GOLD[:3], 150), width=2)

    # ---- Legende unten links, damit die Karte sich selbst erklaert.
    lx, ly = 110, H - 250
    z.text((lx, ly), "GEBIETE", fill=(*GOLD[:3], 220), font=schrift(24, fett=True))
    for i, g in enumerate(GEBIETE):
        y = ly + 44 + i * 34
        z.ellipse([lx, y, lx + 18, y + 18], fill=(*g["leucht"][:3], 220))
        z.text((lx + 32, y - 2), g["name"].title(),
               fill=(*mix(PERGAMENT, GRUND, 0.3)[:3], 220), font=klein)

    z.text((B - 110, H - 96),
           "Vier Gebiete. Neun Raeume stehen. Der Rest ist Vorhaben.",
           fill=(*mix(PERGAMENT, GRUND, 0.55)[:3], 200), font=klein, anchor="rs")

    AUS.parent.mkdir(exist_ok=True)
    bild.convert("RGB").save(AUS)
    print(f"weltbild -> {AUS} ({bild.width}x{bild.height})")


if __name__ == "__main__":
    build()
