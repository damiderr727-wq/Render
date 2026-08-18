"""
Konzeptblatt fuer Cadence - noch NICHT im Spiel.

Dritter Anlauf, und diesmal mit einem anderen Werkzeug.

Die beiden ersten Entwuerfe waren aus Formeln gebaut: Ellipsen fuer den
Kopf, Bezierstriche fuer die Glieder, ein Kegel fuer den Mantel. Auf
dreissig Pixel Hoehe geht das nicht auf. Zwei ueberlappende Ellipsen
sind dort keine zwei Formen mehr, sondern ein Klecks, und was als Kopf
mit Schnauze gedacht war, wurde ein Keil. Deshalb kamen alle Vorwuerfe
zu Recht: Dorito mit Kopf, keine Beine, Maske statt Gesicht.

Bei dieser Groesse zaehlt jeder einzelne Pixel, also wird jeder einzelne
Pixel gesetzt. Die Figur steht unten als RASTER - eine Zeichnung, kein
Rechenergebnis. Die Animation verformt spaeter dieses Raster; die
Gestalt selbst bleibt, was sie ist.

    python3 Tools/konzept_cadence.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

from pixelkit import Canvas, Rng, hexc, mix, shade, hash01

OUT = Path(__file__).resolve().parent.parent / "vorschau" / "konzept_cadence.png"


# --------------------------------------------------------------- Paletten
#
# Der Kontrast liegt zwischen FELL und KITTEL, und er liegt im Wert:
# helles Fell, dunkler Kittel. Damit steht der Kopf immer vorn, egal
# welche Farbe die Kleidung hat.
PALETTEN = {
    "A  Kristall": dict(
        F=hexc("#cfe6dd"), H=hexc("#f4fffb"), L=hexc("#7d9f99"),
        K=hexc("#173c44"), P=hexc("#2f6f70"), M=hexc("#08181e"),
        g=hexc("#8a5a3c"), s=hexc("#5fd6b4"), o=hexc("#e6a8c4"),
        n=hexc("#12181c"), E=hexc("#12181c"), G=hexc("#ff7ad0"),
        k=hexc("#bff3ff"), K2=hexc("#7fd4e8")),
    "B  Rotmantel": dict(
        F=hexc("#e8d8c4"), H=hexc("#fff6e8"), L=hexc("#9a8270"),
        K=hexc("#8e1f28"), P=hexc("#c4373c"), M=hexc("#3e0c12"),
        g=hexc("#3a2418"), s=hexc("#ffb070"), o=hexc("#e09088"),
        n=hexc("#1a0a0c"), E=hexc("#241014"), G=hexc("#ffd76a"),
        k=hexc("#ffe6c0"), K2=hexc("#d8a870")),
    "C  Tiefviolett": dict(
        F=hexc("#d8cfe8"), H=hexc("#f8f2ff"), L=hexc("#8a80a2"),
        K=hexc("#241a3e"), P=hexc("#4d3d78"), M=hexc("#0e0a1a"),
        g=hexc("#5a4020"), s=hexc("#b088ff"), o=hexc("#c890c0"),
        n=hexc("#0c0814"), E=hexc("#140e24"), G=hexc("#7ce0ff"),
        k=hexc("#cfe0ff"), K2=hexc("#8f9fe0")),
}


# ------------------------------------------------------------- Die Figur
#
# Von oben nach unten gelesen:
#
#   n   die Hoerner des Frosches - duenn, geknickt, mit Knoten
#   L o das Ohr, nach hinten gelegt, innen rosa
#   F H der Schaedel mit Schnauze; E das Auge, G der Funke darin
#   g   der Gurt
#   K P M der Kittel: Koerperton, Lichtkante, Schattenrand
#   s   der leuchtende Saum
#   L   die Beine - digitigrad: Knie vor, Sprunggelenk zurueck, Pfote vor
#   k   die Klinge in der vorderen Hand
#
# Die drei Zonen sind bewusst gleich hoch: Kopf, Rumpf, Beine. Genau das
# unterscheidet ein Tier von einem Kegel.
RUHE = [
    ".........nn......nn...........",
    ".........nn......nn...........",
    "..........nn....nn............",
    "...LL.....nn....nn...LL.......",
    "..LooL.....n....n...LooL......",
    "..LoooL....FFFFFF..LoooL......",
    "...LoooL.FFFFFFFFFFLoooL......",
    "....LLL.FFFFFFFFFFFFLLL.......",
    "........FFFFFFFFFFFFF.........",
    ".........FEEFFFFEEF...........",
    ".........FEGFFFFEGF...........",
    ".........FFFFFFFFFF...........",
    ".........FFFFFFFFFFF..........",
    "..........FFFFFFFFF...........",
    "........KKKKKKKKKKKK..........",
    ".......KKKKKKgKKKKKKK.........",
    "......KKKKKKKgKKKKKKKK........",
    "......KKKKKKKgKKKKKKKKF.......",
    ".....KKKKKKKKgKKKKKKKKFF......",
    ".....KKKKKKKKgKKKKKKKK.FFk....",
    "....KKKKKKKKKgKKKKKKKK...kk...",
    "....KKKKKKKKKgKKKKKKKKK...kk..",
    "...KKKKKKKKKKgKKKKKKKKK....k..",
    "...MKKKKKKKKKgKKKKKKKKKK......",
    "..MMKKKKKKKKKgKKKKKKKKKKM.....",
    "..MMKKKKKKKK.FF.KKKKKKKKM.....",
    "...sKsKsKsK..FF..sKsKsKs......",
    "............FF.FF.............",
    "...........FF..FF.............",
    "...........F....F.............",
    "..........LLL..LLL............",
    "..........LLLL.LLLL...........",
]


# Dieselbe Gestalt, aber der Kopf liegt im Kapuzenschatten: nur die
# Augen gluehen, eine Lichtkante laeuft ueber die Stirn.
MYSTISCH = list(RUHE)
MYSTISCH[5]  = "..LoooL....MMMMMM..LoooL......"
MYSTISCH[6]  = "...LoooL.HMMMMMMMMMLoooL......"
MYSTISCH[7]  = "....LLL.HMMMMMMMMMMMLLL......."
MYSTISCH[8]  = "........HMMMMMMMMMMMM........."
MYSTISCH[9]  = "........HMGGMMMMGGM..........."
MYSTISCH[10] = "........MMGGMMMMGGM..........."
MYSTISCH[11] = "........MMMMMMMMMMM..........."
MYSTISCH[12] = ".........MMMMMMMMMMM.........."
MYSTISCH[13] = "..........MMMMMMMMM..........."


def raster(p: dict, gitter: list[str], *, spiegeln: bool = False) -> Canvas:
    """Setzt ein Zeichenraster in Pixel um."""
    h = len(gitter)
    w = max(len(z) for z in gitter)
    c = Canvas(w, h)
    for y, zeile in enumerate(gitter):
        for x, ch in enumerate(zeile):
            if ch == ".":
                continue
            col = p.get(ch)
            if col is None:
                continue
            c.set(w - 1 - x if spiegeln else x, y, col)
    return c


def verformt(p: dict, *, phase: float = 0.0, schritt: float | None = None,
             heben: float = 0.0, neigung: float = 0.0) -> Canvas:
    """
    Dasselbe Raster, aber lebendig.

    Die Figur wird nicht neu gezeichnet, sondern zeilenweise verschoben:
    oben mehr als unten (Neigung), der Kopf hebt und senkt sich (Atem),
    und die Beine bekommen ihren Schritt. Das ist die billigste ehrliche
    Animation, die es gibt - und bei dieser Groesse die einzige, die die
    Zeichnung nicht zerstoert.
    """
    basis = raster(p, RUHE)
    c = Canvas(basis.w + 6, basis.h + 4)
    atem = 1 if math.sin(phase) > 0.4 else 0
    takt = math.sin(schritt) if schritt is not None else 0.0

    for y in range(basis.h):
        t = 1 - y / basis.h                      # 1 oben .. 0 unten
        versatz = int(neigung * t * 2.6)
        # Der Oberkoerper atmet: alles oberhalb der Huefte eine Zeile hoch.
        hoch = atem if y < 14 else 0
        # Die Beine schreiten: die unteren Zeilen wandern gegenlaeufig.
        if y >= 26 and schritt is not None:
            versatz += int(takt * 2.0 * ((y - 26) / 6))
        for x in range(basis.w):
            px = basis.get(x, y)
            if px[3]:
                c.set(x + 3 + versatz, y + 2 - hoch - int(heben), px)
    return c


# ------------------------------------------------------------ Der Schlag
#
# Der Frosch macht es vor: die Zunge faehrt hinaus, kruemmt sich, und die
# Kruemmung nimmt ueber den Weg ZU. Eine gleichmaessige Kurve ist ein
# Rad; eine zunehmende ist ein Peitschenschlag. Dazu die Klinge vorneweg
# und ein Band dahinter, das nach hinten ausfranst.

def schlag(p: dict, t: float, *, breite: int = 40, hoehe: int = 30) -> Canvas:
    c = Canvas(breite, hoehe)
    rng = Rng(int(t * 97) + 3)
    kern = mix(p["k"], (255, 255, 255, 255), 0.65)
    saum = p["G"]

    ax, ay = 5, hoehe // 2 + 5

    def punkt(u: float):
        # Von unten vorn ueber vorn nach oben vorn - eine Sichel, die
        # sich zur Spitze hin enger zieht.
        a = -1.05 + u * 2.35
        r = 13.0 * (1 - 0.26 * u ** 1.6)
        return ax + math.cos(a) * r * 1.28, ay - math.sin(a) * r * 0.95

    schleppe = 0.52
    u0 = max(0.0, t - schleppe)
    if t - u0 < 0.05:
        return c

    n = 90
    for i in range(n + 1):
        s = i / n
        u = u0 + (t - u0) * s
        x, y = punkt(u)
        # Linsenprofil: an beiden Enden null, in der Mitte am dicksten.
        dicke = 2.5 * math.sin(math.pi * s) ** 0.55
        if dicke < 0.4:
            continue
        if s < 0.28 and hash01(int(x), int(y)) < (0.28 - s) / 0.28 * 0.8:
            continue
        for j in range(-int(dicke), int(dicke) + 1):
            e = abs(j) / max(0.4, dicke)
            col = kern if e < 0.40 else saum
            c.blend(int(x), int(y) + j,
                    (col[0], col[1], col[2], int(250 * (0.4 + 0.6 * s))))

    # Die Klinge an der Spitze - sie schneidet, das Band ist ihre Spur.
    sx, sy = punkt(t)
    vx, vy = punkt(min(1.0, t + 0.04))
    a = math.atan2(vy - sy, vx - sx)
    for i in range(10):
        u = i / 9
        x = sx + math.cos(a + u * 0.45) * u * 8
        y = sy + math.sin(a + u * 0.45) * u * 8
        hw = 1.4 * (1 - u) ** 0.45 + 0.3
        for dy in range(-int(hw), int(hw) + 1):
            c.set(int(x), int(y) + dy,
                  p["k"] if abs(dy) < hw * 0.7 else kern)

    for _ in range(10):
        u = u0 + (t - u0) * rng.next()
        x, y = punkt(u)
        c.blend(int(x + rng.range(-3, 3)), int(y + rng.range(-3, 3)),
                (255, 255, 255, rng.int(80, 190)))
    return c


# ------------------------------------------------------------- Das Blatt

def blatt() -> Image.Image:
    S = 8
    grund = (26, 24, 34, 255)
    zw, zh = 36 * S, 40 * S
    img = Image.new("RGBA", (5 * zw + 40, 3 * zh + 40), grund)

    def setze(canvas: Canvas, sp: int, ze: int, dx: int = 0, dy: int = 0,
              gross: int = 1) -> None:
        b = canvas.to_image().resize((canvas.w * S * gross, canvas.h * S * gross),
                                     Image.NEAREST)
        img.alpha_composite(b, (20 + sp * zw + dx, 20 + ze * zh + dy))

    A = PALETTEN["A  Kristall"]

    # Zeile 0: die offene Fassung, Zeile 1 die verschattete - beide in
    # allen drei Paletten. Rechts daneben Spiegelung und Silhouette.
    for i, name in enumerate(PALETTEN):
        setze(raster(PALETTEN[name], RUHE), i, 0)
        setze(raster(PALETTEN[name], MYSTISCH), i, 1)
    setze(raster(A, RUHE, spiegeln=True), 3, 0)
    setze(raster(A, MYSTISCH, spiegeln=True), 3, 1)
    sil = raster(A, RUHE)
    for y in range(sil.h):
        for x in range(sil.w):
            if sil.get(x, y)[3]:
                sil.set(x, y, (0, 0, 0, 255))
    setze(sil, 4, 0)

    # Zeile 2: der Schlag in drei Stufen, dann der Kopf gross.
    for i, s in enumerate((0.34, 0.62, 0.95)):
        setze(verformt(A, phase=1.0, neigung=1.6), i, 2)
        h = schlag(A, s)
        b = h.to_image().resize((h.w * S, h.h * S), Image.NEAREST)
        img.alpha_composite(b, (20 + i * zw + 8 * S, 20 + 2 * zh + 3 * S))

    kopf = Canvas(22, 14)
    voll = raster(A, RUHE)
    for y in range(14):
        for x in range(22):
            kopf.set(x, y, voll.get(x + 1, y + 2))
    setze(kopf, 3, 2, gross=2)

    return img


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    blatt().save(OUT)
    print(OUT)
