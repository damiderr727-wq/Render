"""
Konzeptblatt fuer Cadence - noch NICHT im Spiel.

Vier Vorgaben aus den Vorbildern:

  1. Ohren wie bei einem Tier.
  2. Die Hoerner des Frosches - duenne, geknickte Fuehler mit Knoten.
  3. Die Proportion des Maedchens im roten Mantel: gut zwei Koepfe hoch,
     der Mantel ist der ganze Koerper, die Beine sind Andeutung.
  4. Harter Kontrast zwischen Kleidung und Gesicht: das Gesicht ist die
     hellste Flaeche der Figur, alles andere dunkel.

Und der Schlag des Frosches: kein Kreisbogen, sondern ein HAKEN - er
faehrt hinaus, kruemmt sich nach oben und kommt zurueck.

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
# Jede Palette ist dasselbe Wertgefuege in einer anderen Farbe: ein sehr
# dunkler Mantel, zwei Stufen darueber fuer Falte und Lichtkante, und ein
# fast weisses Gesicht. Der Kontrast liegt im WERT, nicht im Farbton -
# darum funktioniert er in jeder Variante gleich.
PALETTEN = {
    "A  Kristall (bisher)": dict(
        mantel=hexc("#123038"), mantel_hi=hexc("#2e6a6a"), mantel_lo=hexc("#08181e"),
        saum=hexc("#5fd6b4"), gesicht=hexc("#eafff4"), gesicht_lo=hexc("#a9d8cd"),
        ohr=hexc("#1a3d44"), horn=hexc("#0a1418"), auge=hexc("#1d2b30"),
        glut=hexc("#ff7ad0")),
    "B  Rotmantel": dict(
        mantel=hexc("#8e1f28"), mantel_hi=hexc("#c4373c"), mantel_lo=hexc("#4a0d16"),
        saum=hexc("#ff9a6a"), gesicht=hexc("#fff0dc"), gesicht_lo=hexc("#d8b294"),
        ohr=hexc("#a82b30"), horn=hexc("#160608"), auge=hexc("#2a1014"),
        glut=hexc("#ffd76a")),
    "C  Tiefviolett": dict(
        mantel=hexc("#241a3e"), mantel_hi=hexc("#4a3a72"), mantel_lo=hexc("#100a1e"),
        saum=hexc("#b088ff"), gesicht=hexc("#f4ecff"), gesicht_lo=hexc("#b7a6cd"),
        ohr=hexc("#2f2350"), horn=hexc("#0a0614"), auge=hexc("#1a1030"),
        glut=hexc("#7ce0ff")),
}


# ------------------------------------------------------------- Die Figur

def cadence(p: dict, *, phase: float = 0.0, ohren: str = "lang",
            schritt: float = 0.0, lean: float = 0.0,
            heben: float = 0.0) -> Canvas:
    """
    Die Gestalt: zwei Koepfe und ein bisschen.

    Aufbau von unten nach oben - Fuesse, Mantelglocke, Kopf, Ohren,
    Hoerner. Der Kopf ist absichtlich fast so breit wie der Mantelsaum:
    genau das macht die Silhouette der Vorbilder aus.
    """
    W, H = 34, 40
    c = Canvas(W, H)
    cx = 17
    boden = H - 2 - heben

    atem = math.sin(phase) * 0.5

    # --- Fuesse: zwei dunkle Stummel, mehr braucht es nicht -----------
    for seite, versatz in ((-1, math.sin(schritt) * 2.0),
                           (1, math.sin(schritt + math.pi) * 2.0)):
        fx = cx + seite * 2 + versatz
        hoch = max(0.0, math.sin(schritt + (0 if seite > 0 else math.pi))) * 2
        c.rect(int(fx), int(boden - hoch), 2, 2, p["mantel_lo"])

    # --- Der Mantel: eine Glocke, unten weit, oben schmal -------------
    # Zwoelf Zeilen. Er ist der Koerper; darunter steckt nichts, was
    # man kennen muesste.
    mantel_oben = boden - 13
    for i in range(13):
        t = i / 12                     # 0 oben .. 1 Saum
        y = mantel_oben + i
        w = 2.6 + 5.4 * t ** 1.25 + atem * 0.3 * t
        sx = cx + lean * (1 - t) * 1.6 + math.sin(schritt) * 0.8 * t
        for dx in range(-int(w) - 1, int(w) + 2):
            if abs(dx) > w:
                continue
            q = dx / max(0.8, w)
            if q > 0.66:
                col = p["mantel_hi"]              # Lichtkante vorn
            elif q < -0.62:
                col = p["mantel_lo"]              # Schattenrand hinten
            else:
                col = p["mantel"]
            # Eine einzige Falte, leicht vor der Mitte.
            if 0.02 < q < 0.24 and t > 0.3:
                col = mix(col, p["mantel_lo"], 0.5)
            c.set(int(sx) + dx, int(y), col)
    # Der Saum leuchtet - eine Zeile, sparsam.
    for dx in range(-8, 9):
        if abs(dx) <= 7 and (dx + int(phase * 2)) % 3 == 0:
            c.set(cx + dx, int(boden - 1), p["saum"])

    # --- Der Kopf: eine breite Kapuze, das Gesicht darin --------------
    kopf_y = mantel_oben - 4 + atem
    kopf_x = cx + lean * 1.2

    # Die Kapuze als Masse: breiter als hoch, hinten hochgezogen.
    for dy in range(-6, 6):
        v = dy / 6
        hw = 7.4 * math.sqrt(max(0.0, 1 - v * v * 0.86))
        if dy > 2:
            hw *= 1 - (dy - 2) * 0.16
        for dx in range(-int(hw) - 1, int(hw) + 2):
            if abs(dx) > hw:
                continue
            q = dx / max(0.8, hw)
            col = p["mantel_hi"] if q > 0.72 else (
                p["mantel_lo"] if q < -0.55 else p["mantel"])
            c.set(int(kopf_x) + dx, int(kopf_y) + dy, col)

    # --- Das Gesicht: die hellste Flaeche der ganzen Figur ------------
    # Es sitzt vorn in der Kapuze und ist bewusst GROSS: der Kontrast
    # traegt die Figur, nicht die Zeichnung darin.
    gx = kopf_x + 1.6
    for dy in range(-3, 5):
        v = (dy + 0.5) / 4.2
        hw = 4.6 * math.sqrt(max(0.0, 1 - v * v * 0.9))
        if dy >= 2:
            hw *= 1 - (dy - 1) * 0.20          # Kinn
        for dx in range(-int(hw) - 1, int(hw) + 2):
            if abs(dx) > hw:
                continue
            q = dx / max(0.8, hw)
            # Nach hinten faellt das Gesicht in den Schatten der Kapuze.
            col = p["gesicht_lo"] if q < -0.45 else p["gesicht"]
            c.set(int(gx) + dx, int(kopf_y) + dy, col)

    # Augen: zwei dunkle Striche, weit auseinander, ruhig.
    for seite in (0, 1):
        ex = int(gx) - 2 + seite * 3
        c.set(ex, int(kopf_y), p["auge"])
        c.set(ex, int(kopf_y) + 1, p["auge"])
    # Ein Funke Glut im vorderen Auge - das Einzige, was von innen kommt.
    c.set(int(gx) + 1, int(kopf_y), p["glut"])

    # --- Die Ohren: Tier, nicht Mensch --------------------------------
    for seite in (-1, 1):
        wurzel_x = kopf_x + seite * 4.6
        wurzel_y = kopf_y - 4.0
        if ohren == "lang":
            laenge, neig, breit = 6.4, 0.52, 2.4
        elif ohren == "kurz":
            laenge, neig, breit = 4.2, 0.70, 2.8
        else:                                   # "haengend"
            laenge, neig, breit = 6.0, 1.00, 2.2
        wippe = math.sin(phase * 1.3 + (0 if seite > 0 else 1.1)) * 0.5
        n = int(laenge * 2)
        for i in range(n + 1):
            u = i / n
            x = wurzel_x + seite * (neig * laenge * u ** 1.5 + wippe * u)
            y = wurzel_y - laenge * u * (1 - neig * 0.35)
            hw = breit * (1 - u) ** 0.55
            for dx in range(-int(hw), int(hw) + 1):
                q = dx * seite / max(0.5, hw)
                col = p["ohr"] if q > -0.3 else p["mantel_lo"]
                # Das Innenohr faengt Licht - sonst ist es ein Zipfel.
                if abs(dx) < hw - 1.1 and u < 0.72:
                    col = mix(p["ohr"], p["gesicht_lo"], 0.45)
                c.set(int(x) + dx, int(y), col)

    # --- Die Hoerner: geknickte Fuehler mit Knoten ---------------------
    # Direkt vom Frosch uebernommen. Sie sind das Merkmal, an dem man
    # die Figur auf zwanzig Meter erkennt: zwei duenne schwarze Striche,
    # die nach oben gehen, im rechten Winkel abknicken und in einem
    # Knoten enden.
    for seite in (-1, 1):
        hx = kopf_x + seite * 1.8
        hy = kopf_y - 5.4
        schwung = math.sin(phase + (0 if seite > 0 else 0.8)) * 0.5
        # Der Schaft steigt STEIL und weit - er muss die Ohren
        # ueberragen, sonst sieht man ihn nicht.
        hoch = 11
        for i in range(hoch):
            u = i / hoch
            c.set(int(hx + seite * i * 0.22 + schwung * u * 1.6),
                  int(hy - i), p["horn"])
            # Eine zweite Spalte im unteren Drittel: unten ist der
            # Fuehler dicker, oben ein Haar.
            if u < 0.35:
                c.set(int(hx + seite * i * 0.22) + seite, int(hy - i),
                      mix(p["horn"], p["mantel_lo"], 0.4))
        # Der Knick: scharf nach aussen, waagerecht.
        kx = hx + seite * hoch * 0.22 + schwung * 1.6
        ky = hy - hoch
        for i in range(1, 5):
            c.set(int(kx + seite * i), int(ky - i * 0.28), p["horn"])
        # Der Knoten am Ende - beim Frosch sitzt dort die Verdickung.
        ex, ey = int(kx + seite * 5), int(ky - 1)
        for dx in (0, seite):
            for dy in (0, -1):
                c.set(ex + dx, ey + dy, p["horn"])
        c.set(ex + seite, ey - 1, mix(p["horn"], p["glut"], 0.6))

    return c


# ----------------------------------------------------------- Der Haken
#
# Der Schlag des Frosches ist KEIN Kreisbogen. Er faehrt hinaus, kruemmt
# sich nach oben und kommt oben zurueck - ein Haken, der sich zur Spitze
# hin verjuengt und ausfranst. Deshalb liest er sich als Peitsche und
# nicht als Rad.

def haken(p: dict, schwung: float, *, breite: int = 46,
          hoehe: int = 26) -> Canvas:
    c = Canvas(breite, hoehe)
    rng = Rng(int(schwung * 100) + 7)
    kern = mix(p["glut"], (255, 255, 255, 255), 0.75)
    saum = p["glut"]

    ansatz_x, ansatz_y = 4, hoehe // 2 + 3
    t = schwung ** 0.8

    # Der Pfad: erst waagerecht hinaus, dann in einem engen Bogen nach
    # oben und zurueck. Die Kruemmung nimmt ueber den Weg ZU - genau das
    # macht den Haken.
    punkte = []
    n = 110
    for i in range(n + 1):
        u = i / n
        weg = u * (0.35 + 0.65 * t)
        # Winkel laeuft von 0 (geradeaus) bis ueber 180 Grad hinaus.
        a = (weg ** 1.55) * math.pi * 1.18
        r = 17.0 * (1 - weg * 0.30)
        x = ansatz_x + math.sin(a) * r * 1.55
        y = ansatz_y - (1 - math.cos(a)) * r * 0.62
        punkte.append((x, y, u, weg))

    for x, y, u, weg in punkte:
        # Dick am Ansatz, spitz am Ende - eine Peitsche, kein Band.
        dicke = 2.9 * (1 - u) ** 0.75 + 0.35
        if weg > 0.86 and hash01(int(x), int(y)) < (weg - 0.86) / 0.14 * 0.7:
            continue
        for j in range(-int(dicke), int(dicke) + 1):
            e = abs(j) / max(0.4, dicke)
            col = kern if e < 0.45 else saum
            c.blend(int(x), int(y) + j,
                    (col[0], col[1], col[2], int(245 * (1 - u * 0.35))))

    # Funken laengs des Wegs - der Frosch hat sie, und sie machen aus
    # einem Strich eine Bewegung.
    for _ in range(14):
        x, y, u, weg = punkte[rng.int(10, n)]
        c.blend(int(x + rng.range(-3, 3)), int(y + rng.range(-3, 3)),
                (255, 255, 255, rng.int(90, 200)))
    return c


# ------------------------------------------------------------- Das Blatt

def blatt() -> Image.Image:
    S = 7                                   # Vergroesserung
    grund = (26, 24, 34, 255)
    spalten, zeilen = 5, 4
    zw, zh = 34 * S, 40 * S
    img = Image.new("RGBA", (spalten * zw + 40, zeilen * zh + 60), grund)

    def setze(canvas: Canvas, sp: int, ze: int, dx: int = 0, dy: int = 0) -> None:
        b = canvas.to_image().resize((canvas.w * S, canvas.h * S), Image.NEAREST)
        img.alpha_composite(b, (20 + sp * zw + dx, 30 + ze * zh + dy))

    namen = list(PALETTEN)

    # Zeile 0: die drei Paletten, ruhig stehend.
    for i, name in enumerate(namen):
        setze(cadence(PALETTEN[name], phase=0.6), i, 0)

    # Zeile 0 rechts: Ohrformen an der gewaehlten Palette.
    for i, form in enumerate(("kurz", "haengend")):
        setze(cadence(PALETTEN["A  Kristall (bisher)"], phase=1.4, ohren=form),
              3 + i, 0)

    # Zeile 1: Gangbilder - vier Schritte.
    for i in range(4):
        setze(cadence(PALETTEN["A  Kristall (bisher)"],
                      phase=i * 1.6, schritt=i / 4 * math.tau,
                      lean=0.8, heben=1 if i % 2 else 0), i, 1)
    # Und ein Sprung.
    setze(cadence(PALETTEN["A  Kristall (bisher)"], phase=2.2,
                  lean=1.4, heben=3), 4, 1)

    # Zeile 2: der Haken in vier Stufen, an der Figur.
    for i, s in enumerate((0.15, 0.45, 0.75, 1.0)):
        fig = cadence(PALETTEN["A  Kristall (bisher)"], phase=1.0, lean=1.6)
        setze(fig, i, 2)
        h = haken(PALETTEN["A  Kristall (bisher)"], s)
        b = h.to_image().resize((h.w * S, h.h * S), Image.NEAREST)
        img.alpha_composite(b, (20 + i * zw + 17 * S, 30 + 2 * zh + 9 * S))

    # Zeile 3: Groessenvergleich gegen das Kachelraster (16 Pixel).
    kachel = Canvas(34, 40)
    for gy in range(0, 40, 16):
        for gx in range(0, 34, 16):
            kachel.rect(gx, gy, 15, 1, (255, 255, 255, 26))
            kachel.rect(gx, gy, 1, 15, (255, 255, 255, 26))
    setze(kachel, 0, 3)
    setze(cadence(PALETTEN["A  Kristall (bisher)"], phase=0.2), 0, 3)
    # Silhouettenprobe: dieselbe Figur ganz schwarz.
    sil = cadence(PALETTEN["A  Kristall (bisher)"], phase=0.2)
    for y in range(sil.h):
        for x in range(sil.w):
            if sil.get(x, y)[3]:
                sil.set(x, y, (0, 0, 0, 255))
    setze(sil, 1, 3)

    return img


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    blatt().save(OUT)
    print(OUT)
