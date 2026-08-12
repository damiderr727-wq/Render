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


def wurzel(z, x: float, y: float, laenge: float, richtung: float, farbe,
           saat: int, tiefe: int = 4) -> None:
    """Eine Wurzel, die sich nach unten verzweigt - Wahrzeichen der Tiefen."""
    if tiefe <= 0 or laenge < 10:
        return
    x1 = x + math.cos(richtung) * laenge
    y1 = y + math.sin(richtung) * laenge
    z.line([x, y, x1, y1], fill=(*farbe[:3], 60 + tiefe * 30), width=tiefe + 1)
    for k in (-1, 1):
        if hash01(saat, tiefe * 5 + k) > 0.2:
            wurzel(z, x1, y1, laenge * 0.66,
                   richtung + k * (0.32 + hash01(int(x1), saat) * 0.42),
                   farbe, saat + 7, tiefe - 1)


def schwarze_sonne(z, x: float, y: float, r: float, farbe) -> None:
    """
    Die Finsternis: eine schwarze Scheibe mit einem Kranz darum.

    Das einzige Wahrzeichen der Welt, das ueber ihr steht statt in ihr -
    und das Letzte, was man sehen wird.
    """
    for k in range(9):
        rr = r * (1.0 + k * 0.16)
        z.ellipse([x - rr, y - rr, x + rr, y + rr],
                  outline=(*farbe[:3], max(0, 130 - k * 15)), width=3)
    z.ellipse([x - r, y - r, x + r, y + r], fill=(*GRUND[:3], 255))
    z.ellipse([x - r, y - r, x + r, y + r], outline=(*farbe[:3], 255), width=5)
    # Strahlen, ungleich lang - eine Korona ist nie regelmaessig.
    for i in range(22):
        a = i / 22 * math.tau
        l = r * (1.25 + hash01(i, 3) * 0.85)
        z.line([x + math.cos(a) * r * 1.05, y + math.sin(a) * r * 1.05,
                x + math.cos(a) * l, y + math.sin(a) * l],
               fill=(*farbe[:3], 90 + int(hash01(i, 9) * 90)), width=2)


# ---------------------------------------------------------------- Gebiete
#
# Von Hand gesetzt, nicht abgeleitet. Jedes Gebiet hat eine Lage in der
# Welt, eine Form, eine Farbe und ein Wahrzeichen - und eine Groesse, die
# dem entspricht, was es werden soll, nicht dem, was schon gebaut ist.

# Die Welt ist ein Querschnitt, kein Fleckenteppich.
#
# Der erste Anlauf setzte vier gleich grosse Kleckse nebeneinander, und
# genau so sah er aus. Eine Welt hat aber ein Oben und ein Unten: hier
# haengt sie unter einem Himmel, den man erst am Ende sieht, und laeuft
# nach unten in etwas aus, das keinen Boden mehr hat.
#
# Darum hat jedes Gebiet eine eigene Form statt einer eigenen Farbe:
# der Hain liegt breit und flach, die Kathedrale steht hoch und schmal,
# die Grotten sind gezackt, die Dissonanz ist eine Wunde, die Tiefen
# sind eine Wurzelmasse ohne Unterkante. Und die Reihenfolge ist die
# Reihenfolge des Spiels - von oben links nach unten, und ganz zuletzt
# wieder hinauf.

GEBIETE = [
    dict(name="DER SCHLAFENDE HAIN", beschriftung=(-40, -10), nummer="I", stand="gebaut",
         leucht=hexc("#8fd8a0"), fuell=hexc("#16301f"), wappen="baum",
         text=["Wo die Welt sich selbst sang.", "Jetzt haelt sie den Atem an."],
         # Breit und flach, mit einer Senke in der Mitte: eine Landschaft,
         # kein Klecks.
         punkte=[(180, 560), (400, 508), (560, 560), (700, 520), (860, 556),
                 (900, 640), (830, 720), (620, 762), (400, 745), (230, 700),
                 (150, 630)]),
    dict(name="DIE KATHEDRALE DER FUGEN", beschriftung=(-130, 40), nummer="II", stand="gebaut",
         leucht=hexc("#b9a6ef"), fuell=hexc("#211a35"), wappen="bogen",
         text=["Vier Stimmen, die einander", "nie ins Wort fielen."],
         # Hoch und schmal, mit einem Turm: das einzige Gebiet, das nach
         # oben strebt statt in die Breite.
         punkte=[(1010, 500), (1080, 300), (1150, 250), (1220, 300),
                 (1290, 430), (1420, 470), (1470, 590), (1380, 700),
                 (1160, 730), (1000, 650)]),
    dict(name="DIE RESONANZKAVERNEN", beschriftung=(30, 46), nummer="III", stand="gebaut",
         leucht=hexc("#7fd4f0"), fuell=hexc("#122736"), wappen="kristall",
         text=["Hier wuchs der Klang zu Stein.",
               "Man hoert sich selbst zurueckkommen."],
         # Gezackt: die Kontur selbst ist schon Kristall.
         punkte=[(620, 880), (740, 830), (830, 880), (960, 815), (1090, 870),
                 (1210, 820), (1300, 900), (1250, 1010), (1120, 1050),
                 (980, 1010), (840, 1055), (700, 1010), (600, 960)]),
    dict(name="DAS HERZ DER DISSONANZ", beschriftung=(150, 10), nummer="IV", stand="gebaut",
         leucht=hexc("#f08a7a"), fuell=hexc("#2e1418"), wappen="riss",
         text=["Nicht still. Alles zugleich."],
         # Eine Wunde: laenglich, aufgerissen, mit zwei Zipfeln.
         punkte=[(1420, 880), (1620, 830), (1800, 870), (1930, 950),
                 (1880, 1040), (1700, 1070), (1560, 1030), (1430, 970)]),
    dict(name="DIE TIEFEN", beschriftung=(340, 66), nummer="V", stand="geplant - endgame",
         leucht=hexc("#6f7fa8"), fuell=hexc("#0d1220"), wappen="wurzel",
         text=["Kein Boden mehr, nur noch Abstand.",
               "Was hier klingt, hat nie jemand gestimmt."],
         # Eine Masse ohne Unterkante: sie laeuft nach unten aus dem Bild.
         punkte=[(360, 1150), (700, 1100), (1050, 1130), (1400, 1090),
                 (1780, 1140), (1980, 1230), (1960, 1450), (1600, 1500),
                 (1150, 1480), (700, 1500), (330, 1440), (280, 1270)]),
    dict(name="DIE FINSTERNIS", beschriftung=(-40, 18), nummer="VI", stand="geplant - danach",
         leucht=hexc("#e0524a"), fuell=hexc("#2a0c10"), wappen="sonne",
         text=["Ganz zuletzt geht es wieder hinauf.",
               "Der Himmel steht rot und still."],
         # Ein Band ganz oben, ueber allem. Man sieht es das ganze Spiel
         # ueber nicht - und dann ist es das Letzte, was man sieht.
         punkte=[(1560, 210), (1900, 175), (2160, 220), (2230, 330),
                 (2120, 430), (1830, 455), (1610, 400), (1530, 300)]),
]

# Gaenge zwischen den Gebieten: von Hand gelegt, wie Wurzeln.
GAENGE = [
    ((880, 600), (1010, 560), False),
    ((820, 720), (760, 850), False),
    ((1180, 730), (1120, 830), False),
    ((1300, 930), (1430, 930), False),
    ((1000, 1040), (1000, 1130), True),
    ((1780, 1050), (1800, 1140), True),
    ((1900, 1160), (2050, 500), True),
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
    for (a, b, geplant) in GAENGE:
        strang = rauschkontur([a, b], 6, saat=int(a[0]) % 97, dichte=6)
        farbe = mix(PERGAMENT, GRUND, 0.45)
        if geplant:
            # Was noch nicht gebaut ist, wird gestrichelt gefuehrt.
            for k in range(0, len(strang) - 3, 6):
                z.line(strang[k:k + 3], fill=(*farbe[:3], 150), width=3)
        else:
            z.line(strang, fill=(*farbe[:3], 80), width=8, joint="curve")
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
        elif g["wappen"] == "wurzel":
            for k in range(9):
                x = x0 + 90 + k * (x1 - x0 - 180) / 8
                wurzel(z, x, y0 + 30, 90 + hash01(k, 4) * 60,
                       math.pi / 2 + (hash01(k, 8) - 0.5) * 0.5, farbe, k * 5)
        elif g["wappen"] == "sonne":
            schwarze_sonne(z, mitte[0], mitte[1], (y1 - y0) * 0.26, farbe)
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
        # Die Beschriftung wird je Gebiet von Hand versetzt. Automatisch
        # ueber die Mitte gesetzt lag sie mal im Titel, mal quer ueber
        # dem Nachbargebiet - eine Karte beschriftet man von Hand.
        dx, dy = g.get("beschriftung", (0, 0))
        cx = (min(xs) + max(xs)) / 2 + dx
        oben = min(ys) - 78 + dy
        # Breit genug fuer Nummer und Namen. Zu knapp bemessen schneidet
        # PIL die Beschriftung einfach ab, und dann fehlt das Ende.
        marke = Image.new("RGBA", ((len(g["name"]) + 10) * 26, 150), (0, 0, 0, 0))
        mz = ImageDraw.Draw(marke, "RGBA")
        mz.text((0, 0), f'{g["nummer"]}.  {g["name"]}',
                fill=(*g["leucht"][:3], 235), font=gross)
        for k, zeile in enumerate(g["text"]):
            mz.text((2, 52 + k * 26), zeile,
                    fill=(*mix(g["leucht"], PERGAMENT, 0.5)[:3], 170), font=klein)
        if g["stand"] != "gebaut":
            mz.text((2, 52 + len(g["text"]) * 26 + 4), f'[ {g["stand"]} ]',
                    fill=(*mix(g["leucht"], GRUND, 0.42)[:3], 200), font=klein)
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
    lx, ly = 110, H - 300
    z.text((lx, ly), "GEBIETE", fill=(*GOLD[:3], 220), font=schrift(24, fett=True))
    for i, g in enumerate(GEBIETE):
        y = ly + 44 + i * 34
        z.ellipse([lx, y, lx + 18, y + 18], fill=(*g["leucht"][:3], 220))
        z.text((lx + 32, y - 2), f'{g["nummer"]}.  {g["name"].title()}',
               fill=(*mix(PERGAMENT, GRUND, 0.3)[:3], 220), font=klein)

    z.text((B - 110, H - 96),
           "Sechs Gebiete, in dieser Reihenfolge. Zehn Raeume stehen. "
           "Gestrichelt: noch Vorhaben.",
           fill=(*mix(PERGAMENT, GRUND, 0.55)[:3], 200), font=klein, anchor="rs")

    AUS.parent.mkdir(exist_ok=True)
    bild.convert("RGB").save(AUS)
    print(f"weltbild -> {AUS} ({bild.width}x{bild.height})")


if __name__ == "__main__":
    build()
