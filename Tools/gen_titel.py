"""
Titelbild und Intro-Tafeln.

Beides sind keine Kulissen, sondern Bilder: sie werden einmal angesehen,
nicht abgelaufen. Darum liegen sie nicht im Atlas, sondern als ganze
PNGs unter Resources/Titel, und duerfen sich Dinge leisten, die eine
Kulisse nicht darf - eine Bildmitte, ein Motiv, eine Leserichtung.

Das Motiv des Titels ist die Sonnenfinsternis. Sie ist der Kern der
Geschichte: das Land, in dem die Sonne schwarz steht, ist das Ziel des
ganzen Spiels - also steht sie vom ersten Bild an am Himmel.
"""
from __future__ import annotations

import math
from pathlib import Path

from pixelkit import Canvas, Rng, hexc, mix, shade, hash01
import gen_characters as chars

W, H = 512, 288
OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Titel"


# ------------------------------------------------------------ Bausteine

def verlauf(c: Canvas, stufen) -> None:
    """Senkrechter Farbverlauf ueber gesetzte Stufen, wie im Kulissenbau."""
    for i in range(len(stufen) - 1):
        (t0, c0), (t1, c1) = stufen[i], stufen[i + 1]
        y0, y1 = int(t0 * c.h), int(t1 * c.h)
        for y in range(y0, min(y1, c.h)):
            t = (y - y0) / max(1, y1 - y0)
            col = mix(c0, c1, t)
            c.rect(0, y, c.w, 1, col)


def finsternis(c: Canvas, cx: int, cy: int, r: int, *, hell=1.0) -> None:
    """
    Die schwarze Sonne.

    Eine Scheibe, die dunkler ist als der Himmel um sie herum, und ein
    duenner Ring Licht, der an ihr vorbeikommt. Die Korona ist bewusst
    ungleichmaessig - ein sauberer Kreis waere ein Auge, keine Sonne.
    """
    # Weiter, warmer Schein - das Licht, das trotzdem noch da ist.
    c.glow(cx, cy, r * 4.2, (255, 226, 180, int(26 * hell)), power=2.2)
    c.glow(cx, cy, r * 2.1, (255, 240, 210, int(40 * hell)), power=1.8)

    # Koronastrahlen, ungleich lang.
    for k in range(26):
        a = k / 26 * math.tau + hash01(k, 3) * 0.2
        laenge = r * (1.25 + hash01(k, 7) * 0.85)
        for i in range(int(r * 1.02), int(laenge)):
            t = (i - r) / max(1, laenge - r)
            x = cx + math.cos(a) * i
            y = cy + math.sin(a) * i * 0.98
            c.blend(int(x), int(y), (255, 236, 200, int(46 * (1 - t) * hell)))

    # Der Ring: hell, einen Pixel breit, mit einer helleren Stelle unten
    # links - der letzte Rand, hinter dem sie verschwindet.
    for k in range(220):
        a = k / 220 * math.tau
        x = cx + math.cos(a) * (r + 1)
        y = cy + math.sin(a) * (r + 1)
        glanz = 1.0 + 1.2 * max(0.0, math.cos(a - 2.4))
        c.blend(int(x), int(y), (255, 244, 214, min(255, int(150 * glanz * hell))))

    # Und die Scheibe selbst: nicht schwarz, sondern das dunkelste Violett
    # des Himmels - reines Schwarz saesse wie ein Loch im Bild.
    c.ellipse(cx, cy, r, r, hexc("#0b0714"))
    c.ellipse(cx - r * 0.25, cy - r * 0.2, r * 0.5, r * 0.4, hexc("#080510"), blend=False)


def bergzug(c: Canvas, y0: float, amp: float, col, seed: int = 0) -> None:
    for x in range(W):
        h = y0 + math.sin(x * 0.011 + seed * 2.1) * amp \
            + math.sin(x * 0.037 + seed) * amp * 0.4
        for y in range(int(h), H):
            c.set(x, y, col)


def tuerme(c: Canvas, grund: int, col, seed: int = 0, dichte: int = 7) -> None:
    """Eine Reihe Ruinentuerme als Silhouette: die alte Zivilisation."""
    rng = Rng(700 + seed * 31)
    for k in range(dichte):
        x = int((k + 0.5) / dichte * W + rng.range(-26, 26))
        b = rng.int(7, 16)
        h = rng.int(30, 86)
        # Der Schaft, leicht verjuengt, oben abgebrochen.
        for i in range(h):
            t = i / h
            w = b * (1 - t * 0.25)
            bruch = 1.0 if t < 0.85 else hash01(x + i, seed) * 0.9 + 0.2
            c.rect(int(x - w / 2 * bruch), grund - i, max(1, int(w * bruch)), 1, col)
        # Fensterreihen: Licht faellt NICHT heraus - alles hier ist tot.
        for fy in range(grund - h + 8, grund - 6, 9):
            if rng.chance(0.6):
                c.rect(x - 1, fy, 2, 3, shade(col, -0.35))


def bruecke_silhouette(c: Canvas, deck: int, col) -> None:
    c.rect(0, deck, W, 4, col)
    for x in range(0, W, 9):
        c.rect(x, deck - 3, 1, 3, col)
    for bx in range(40, W + 80, 96):
        for i in range(120):
            a = i / 119 * math.pi
            x = bx - math.cos(a) * 40
            y = deck + 30 - math.sin(a) * 26
            c.rect(int(x), int(y), 1, 3, col)
        for seite in (-1, 1):
            px = bx + seite * 44
            for y in range(deck + 4, min(H, deck + 60)):
                b = 4 + (y - deck) * 0.05
                c.rect(int(px - b), y, int(b * 2), 1, col)


def nebelband(c: Canvas, y0: int, hoehe: int, ton, dichte: float, seed: int = 0) -> None:
    rng = Rng(900 + seed * 17)
    for _ in range(int(26 * dichte)):
        x = rng.range(-40, W + 40)
        y = y0 + rng.range(0, hoehe)
        r = rng.range(24, 70)
        for k in range(4):
            c.ellipse(x + rng.range(-r * 0.5, r * 0.5), y + rng.range(-4, 4),
                      r * rng.range(0.5, 1.0), r * rng.range(0.12, 0.24),
                      (*ton, int(rng.range(10, 26))), blend=True)


def funken(c: Canvas, cx: float, cy: float, anzahl: int, ton, seed: int = 0,
           reichweite: float = 16) -> None:
    """Cadences Flaum - dieselbe Sprache wie im Spiel, nur als Standbild."""
    for k in range(anzahl):
        a = k / anzahl * math.tau + hash01(k, seed) * 0.7
        r = reichweite * (0.35 + hash01(k, seed + 1) * 0.65)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r * 1.3 - r * 0.4
        deck = int(150 * (1 - r / (reichweite * 1.1)))
        c.blend(int(x), int(y), (*ton, max(30, deck)))


def cadence_silhouette(c: Canvas, x: int, boden: int, *, hell: float = 0.22,
                       scale: int = 1) -> None:
    """
    Cadence als dunkle Gestalt mit Randlicht - erkennbar an der Haltung
    und den Funken, nicht an Details.
    """
    fig = chars.draw_heroine(instrument=None, garment="mantel", phase=0.35)
    ton = hexc("#10101e")
    saum = hexc("#9ff0e0")
    for yy in range(fig.h):
        for xx in range(fig.w):
            px = fig.get(xx, yy)
            if not px[3]:
                continue
            # Randlicht: wo darueber nichts mehr ist, faengt sie Licht.
            # Es muss hart sein - eine Silhouette lebt von ihrer Kante,
            # und eine weiche Kante plus Funken ergab einen Wollknaeuel.
            frei = yy == 0 or not fig.get(xx, yy - 1)[3]
            col = mix(saum, ton, 0.25) if frei else \
                mix(ton, hexc("#1c1c30"), hell)
            for sy in range(scale):
                for sx in range(scale):
                    c.set(x + xx * scale - fig.w * scale // 2 + sx,
                          boden - fig.h * scale + yy * scale + sy, col)
    funken(c, x, boden - fig.h * scale * 0.5, 7, (127, 232, 216),
           seed=5, reichweite=7 * scale)


def koernung(c: Canvas, staerke: int = 8, seed: int = 1) -> None:
    """Feines Korn ueber alles - haelt grosse Flaechen lebendig."""
    for y in range(c.h):
        for x in range(c.w):
            n = hash01(x * 7 + seed, y * 13)
            if n < 0.5:
                continue
            r, g, b, a = c.get(x, y)
            d = int((n - 0.5) * 2 * staerke)
            c.set(x, y, (min(255, r + d), min(255, g + d), min(255, b + d), a))


# ------------------------------------------------------------ Titelbild

def titelbild() -> Canvas:
    c = Canvas(W, H)
    rng = Rng(4242)

    # Daemmerhimmel, unten warm: das letzte Licht unter der Finsternis.
    verlauf(c, [(0.00, hexc("#120b24")), (0.30, hexc("#251536")),
                (0.58, hexc("#472549")), (0.80, hexc("#7a4150")),
                (1.00, hexc("#3a2138"))])

    finsternis(c, 256, 66, 24)

    # Sterne, nur oben - unter einer Finsternis kommen sie heraus.
    for _ in range(70):
        x, y = rng.int(0, W - 1), rng.int(0, int(H * 0.42))
        if abs(x - 256) < 70 and abs(y - 66) < 60:
            continue
        c.blend(x, y, (255, 250, 235, rng.int(20, 90)))

    # Die Welt in Schichten, hinten nach vorn.
    bergzug(c, H * 0.62, 20, hexc("#33203f"), seed=1)
    tuerme(c, int(H * 0.72), hexc("#281838"), seed=2, dichte=6)
    bergzug(c, H * 0.74, 13, hexc("#221331"), seed=3)
    nebelband(c, int(H * 0.71), 18, (220, 170, 160), 0.45, seed=1)

    bruecke_silhouette(c, int(H * 0.78), hexc("#170e28"))
    # Der Nebel liegt UNTER der Bruecke in der Schlucht, nicht auf ihr.
    nebelband(c, int(H * 0.87), 26, (200, 150, 150), 0.9, seed=2)

    # Vorn links die Klippe, auf der sie steht.
    for x in range(0, 190):
        kante = H * 0.72 + (x / 190) ** 2.2 * 26 \
            + math.sin(x * 0.13) * 2.2 + hash01(x, 9) * 2
        for y in range(int(kante), H):
            t = (y - kante) / 40
            c.set(x, y, mix(hexc("#0e0918"), hexc("#070410"), min(1, t)))
        c.set(x, int(kante), hexc("#2c2040"))

    # Ein paar Kristalle an der Klippenkante, die ihr Licht halten.
    for kx, kh in ((26, 7), (64, 5), (154, 6)):
        for i in range(kh):
            t = i / kh
            c.rect(kx - int((1 - t) * 2), int(H * 0.72 + (kx / 190) ** 2.2 * 26) - i,
                   max(1, int((1 - t) * 4)), 1,
                   mix(hexc("#2e8a84"), hexc("#d8fff0"), t * 0.7))
        c.glow(kx, int(H * 0.72 + (kx / 190) ** 2.2 * 26) - kh, 8,
               (127, 232, 216, 40), power=1.6)

    cadence_silhouette(c, 96, int(H * 0.72 + (96 / 190) ** 2.2 * 26) + 1, hell=0.3)

    # Staub im letzten Licht.
    for _ in range(150):
        x, y = rng.int(0, W - 1), rng.int(int(H * 0.4), H - 1)
        c.blend(x, y, (255, 226, 200, rng.int(6, 26)))

    koernung(c, 6)
    return c


# ------------------------------------------------------------ Die Tafeln
#
# Fuenf Bilder, eine Geschichte: warum sie ihre sichere Heimat verlaesst.
# Der Text liegt NICHT im Bild - er wird von der App gesetzt, scharf und
# austauschbar. Die Bilder muessen ohne ihn lesbar sein.

def tafel_heimat() -> Canvas:
    """Die verborgene Heimat: warm, eng, das letzte sichere Licht."""
    c = Canvas(W, H)
    rng = Rng(11)
    # Hoehlendunkel mit warmem Kern. Das Bild muss WARM lesen - es ist
    # das einzige der Reihe, in dem nichts droht.
    verlauf(c, [(0.0, hexc("#0a0714")), (0.45, hexc("#161022")),
                (1.0, hexc("#241726"))])
    c.glow(256, 200, 240, (255, 186, 110, 42), power=2.2)
    c.glow(256, 210, 130, (255, 196, 122, 48), power=1.8)

    # Die Hoehlendecke haengt tief - Sicherheit heisst hier: ein Dach.
    for x in range(W):
        decke = 34 + math.sin(x * 0.02) * 15 + math.sin(x * 0.09) * 5
        for y in range(0, int(decke)):
            c.set(x, y, hexc("#080510"))
        if hash01(x, 3) > 0.85:
            ln = int(5 + hash01(x, 5) * 12)
            for i in range(ln):
                # Zapfen sind Decke, nicht Licht: dunkler als der Raum.
                c.set(x, int(decke) + i, mix(hexc("#080510"), hexc("#161022"),
                                             i / ln * 0.5))
        # Kristalle an der Decke, die das Dorf mit beleuchten.
        if hash01(x, 11) > 0.965:
            c.glow(x, int(decke) + 4, 10, (127, 232, 216, 36), power=1.5)
            c.rect(x, int(decke), 1, 4, mix(hexc("#2e8a84"), hexc("#d8fff0"), 0.6))

    # Boden.
    for x in range(W):
        boden = H - 40 + math.sin(x * 0.03) * 6
        for y in range(int(boden), H):
            c.set(x, y, mix(hexc("#181020"), hexc("#0c0816"),
                            min(1, (y - boden) / 30)))

    # Behausungen: Kuppeln mit warmen Tueren, ins Licht gebaut.
    for hx, hw, hh in ((72, 48, 42), (168, 38, 34), (266, 54, 48),
                       (366, 40, 36), (452, 44, 36)):
        grund = int(H - 38 + math.sin(hx * 0.03) * 6)
        for i in range(hh):
            t = i / hh
            b = hw * math.cos(t * math.pi / 2) ** 0.7
            # Lichtseite zur Mitte hin: die Kuppeln stehen im Feuerschein.
            zur_mitte = 1 if hx < 256 else -1
            c.rect(int(hx - b / 2), grund - i, max(1, int(b)), 1, hexc("#1c1326"))
            c.set(int(hx + zur_mitte * b / 2) - (1 if zur_mitte > 0 else 0),
                  grund - i, hexc("#3a2838"))
        # Die Tuer: ein warmer Bogen mit Lichtkegel davor.
        for i in range(12):
            b = max(1, int(7 * math.cos(i / 12 * math.pi / 2) ** 0.6))
            c.rect(hx - b // 2, grund - i, b, 1,
                   mix(hexc("#ffc270"), hexc("#b06a34"), i / 12))
        c.glow(hx, grund - 5, 20, (255, 180, 100, 70), power=1.5)
        # Ein rundes Fenster, ebenfalls warm.
        c.rect(hx - hw // 4 - 1, grund - hh + 9, 3, 3, hexc("#e8a860"))
        c.glow(hx - hw // 4, grund - hh + 10, 7, (255, 180, 110, 46), power=1.4)

    # Kristallsaeulen zwischen den Kuppeln.
    for kx in (120, 316, 412):
        grund = int(H - 38 + math.sin(kx * 0.03) * 6)
        kh = 14 + (kx % 7)
        for i in range(kh):
            t = i / kh
            b = max(1, int(4 * (1 - t)))
            c.rect(kx - b // 2, grund - i, b, 1,
                   mix(hexc("#1e5a58"), hexc("#9ff0e0"), t * 0.8))
        c.glow(kx, grund - kh, 13, (127, 232, 216, 46), power=1.5)

    # Das Feuer in der Mitte, und um es herum die letzten ihrer Art.
    c.glow(256, 216, 34, (255, 170, 90, 120), power=1.3)
    for i in range(6):
        c.set(253 + i * 2 - (i % 2), 212 - (i % 3), hexc("#ffd894"))
    c.rect(251, 214, 10, 2, hexc("#3a2418"))
    for fx, seite in ((224, 1), (290, -1), (238, 1), (276, -1), (256, 1)):
        if fx == 256:
            continue
        hoehe = 12 + (fx % 4)
        for i in range(hoehe):
            t = i / hoehe
            b = max(1, int(5 * (1 - t * 0.55)))
            c.rect(fx - b // 2, 224 - i, b, 1, hexc("#120b1a"))
        # Feuerschein auf der zugewandten Seite, Funkenkrone oben.
        for i in range(3, hoehe):
            c.set(fx + seite * 2, 224 - i, hexc("#4a2e28"))
        c.set(fx, 224 - hoehe, hexc("#9ff0e0"))
        c.set(fx - seite, 224 - hoehe + 1, hexc("#5aa89a"))

    koernung(c, 5, seed=2)
    return c


def tafel_riss() -> Canvas:
    """Der Riss: die Huelle gross im Bild, und aus ihr tritt die Flamme."""
    c = Canvas(W, H)
    verlauf(c, [(0.0, hexc("#0a0612")), (1.0, hexc("#120a1c"))])

    # Die Huelle als grosse, stille Form - Cadence' Kopf, formatfuellend
    # angeschnitten. Keine Augen im Detail, nur die Masse und der Riss.
    cx, cy, r = 250, 150, 92
    for y in range(H):
        for x in range(W):
            dx = (x - cx) / r
            dy = (y - cy) / (r * 1.12)
            d = dx * dx + dy * dy
            if d <= 1.0:
                t = max(0.0, 1 - d)
                grund = mix(hexc("#141422"), hexc("#232338"), t * 0.7)
                # Licht von oben rechts.
                licht = max(0.0, -dx * 0.4 + -dy * 0.8)
                c.set(x, y, mix(grund, hexc("#3a4658"), licht * 0.5))

    # Der Riss: ein Blitz quer ueber die Form, aus dem Licht tritt.
    rosa = hexc("#ff7ad0")
    weiss = hexc("#ffe9f6")
    x, y = cx - 60, cy - 74
    pfad = []
    while y < cy + 80 and x < cx + r:
        pfad.append((x, y))
        y += 2
        x += int((hash01(x, y) - 0.35) * 5)
    for i, (px, py) in enumerate(pfad):
        t = i / max(1, len(pfad) - 1)
        breite = 1 + int(2.2 * math.sin(math.pi * t))
        c.glow(px, py, 7 + breite * 3, (255, 122, 208, 26), power=1.8)
        for b in range(breite):
            c.set(px + b, py, mix(weiss, rosa, 0.3 + 0.4 * t))
            c.set(px + b, py + 1, mix(rosa, hexc("#8a2a68"), t))
    # Nebenrisse.
    for k in (len(pfad) // 3, len(pfad) * 2 // 3):
        px, py = pfad[k]
        for i in range(10):
            c.set(px + i, py + int(i * 0.5 * ((k % 2) * 2 - 1)),
                  mix(rosa, hexc("#5a1c46"), i / 10))

    # Funken, die aus dem Riss treiben - nach oben, gegen die Schwere.
    for k in range(26):
        px, py = pfad[int(hash01(k, 1) * (len(pfad) - 1))]
        dx = (hash01(k, 2) - 0.3) * 20
        dy = -hash01(k, 3) * 36 - 4
        deck = int(160 * (1 - abs(dy) / 42))
        c.blend(int(px + dx), int(py + dy), (255, 150, 220, max(30, deck)))

    koernung(c, 5, seed=3)
    return c


def tafel_abschied() -> Canvas:
    """Das Tor der Heimat: hinter ihr warm, vor ihr nichts als Wald."""
    c = Canvas(W, H)
    rng = Rng(13)
    verlauf(c, [(0.0, hexc("#0b0816")), (0.55, hexc("#141024")),
                (1.0, hexc("#1c1428"))])

    # Boden zuerst - alles steht darauf.
    for x in range(W):
        for y in range(H - 40, H):
            c.set(x, y, mix(hexc("#151020"), hexc("#0b0714"),
                            min(1, (y - (H - 40)) / 26)))

    # Links die Felswand der Heimat, ueber die ganze Hoehe, mit einem
    # Torbogen darin. Erst die Wand, dann wird der Bogen hineingeschnitten
    # und mit Licht gefuellt - so bleibt die Geometrie ehrlich.
    wand = hexc("#0b0816")
    for x in range(0, 118):
        kante = 118 - (x / 118) ** 0.5 * 8 + math.sin(x * 0.2) * 2
        for y in range(0, H):
            if x < kante or y < H * 0.16 + x * 0.1:
                c.set(x, y, wand)
    for x in range(0, 118):
        for y in range(int(H * 0.16), H - 38):
            c.set(x, y, wand)
    # Die Kante der Wand, sonst verschwindet sie im Dunkel dahinter.
    for y in range(int(H * 0.14), H - 38):
        kx = 117 - int(math.sin(y * 0.06) * 3 + hash01(y, 7) * 2)
        c.set(kx, y, hexc("#221a30"))
        c.set(kx - 1, y, hexc("#161020"))
        for x in range(kx + 1, 122):
            c.set(x, y, mix(hexc("#0b0816"), hexc("#141024"),
                            (x - kx) / 5))
    # Der Bogen: 26 breit, 52 hoch, Fuss auf dem Boden.
    tor_x, tor_b, tor_h = 58, 15, 54
    for y in range(H - 40 - tor_h, H - 38):
        t = max(0.0, 1 - (H - 40 - y) / tor_h)
        b = tor_b * math.sin(min(1.0, t * 1.6) * math.pi / 2) ** 0.55
        for x in range(int(tor_x - b), int(tor_x + b)):
            tiefe = 1 - abs(x - tor_x) / max(1.0, b)
            c.set(x, y, mix(hexc("#5a3620"), hexc("#ffc478"), tiefe * 0.9))
    c.glow(tor_x, H - 64, 52, (255, 190, 120, 60), power=1.9)
    # Lichtteppich, der aus dem Tor auf den Weg faellt.
    for x in range(tor_x, 248):
        t = min(1.0, (x - tor_x) / 190)
        for y in range(H - 42, H - 30):
            c.blend(x, y, (255, 180, 110, int(46 * (1 - t) ** 1.5)))

    # Rechts der Wald, in den sie geht: Staemme, immer dichter.
    for k in range(14):
        x = 200 + int((k / 14) ** 1.3 * 290) + rng.int(-8, 8)
        b = rng.int(4, 10)
        ton = mix(hexc("#171226"), hexc("#0a0714"), k / 14)
        for y in range(int(H * 0.05), H - 38):
            w = b + math.sin(y * 0.05 + k) * 1.5
            c.rect(int(x - w / 2), y, max(1, int(w)), 1, ton)
        # Astansaetze.
        for _ in range(3):
            ay = rng.int(30, 150)
            for i in range(rng.int(8, 20)):
                c.set(x + i * rng.pick([-1, 1]), ay - i // 3, ton)

    nebelband(c, H - 90, 40, (140, 130, 160), 0.9, seed=4)

    # Cadence, klein, auf der Schwelle zwischen Licht und Wald.
    cadence_silhouette(c, 176, H - 41, hell=0.35)

    koernung(c, 5, seed=4)
    return c


def tafel_kernschatten() -> Canvas:
    """Das Ziel, von weitem: das Land, ueber dem die Sonne schwarz steht."""
    c = Canvas(W, H)
    rng = Rng(17)
    verlauf(c, [(0.00, hexc("#0d0616")), (0.36, hexc("#1e0f2c")),
                (0.66, hexc("#3c1a3a")), (0.88, hexc("#67293c")),
                (1.00, hexc("#2a1226"))])

    finsternis(c, 256, 84, 30, hell=1.2)

    # Das Land darunter: Tuerme und Zacken der alten Zivilisation, in
    # mehreren Schichten bis zum Horizont.
    bergzug(c, H * 0.66, 16, hexc("#301b3a"), seed=5)
    tuerme(c, int(H * 0.76), hexc("#241330"), seed=6, dichte=9)
    bergzug(c, H * 0.80, 10, hexc("#1a0d26"), seed=7)
    tuerme(c, int(H * 0.92), hexc("#120a1e"), seed=8, dichte=7)

    # Ein einzelner gewaltiger Turm in der Mitte, direkt unter der Sonne:
    # dorthin geht die ganze Reise.
    for i in range(150):
        t = i / 150
        b = 15 * (1 - t * 0.7)
        c.rect(int(256 - b / 2), int(H * 0.9) - i, max(1, int(b)), 1, hexc("#0e0818"))
    c.rect(252, int(H * 0.9) - 150 - 3, 2, 4, hexc("#0e0818"))
    c.rect(258, int(H * 0.9) - 146, 1, 5, hexc("#0e0818"))

    nebelband(c, int(H * 0.72), 60, (180, 110, 120), 1.3, seed=6)

    for _ in range(60):
        x, y = rng.int(0, W - 1), rng.int(0, int(H * 0.4))
        if abs(x - 256) < 80 and abs(y - 84) < 70:
            continue
        c.blend(x, y, (255, 240, 220, rng.int(16, 70)))

    koernung(c, 6, seed=5)
    return c


def tafel_aufbruch() -> Canvas:
    """Sie geht. Eine Strasse, eine kleine Gestalt, das Ziel am Himmel."""
    c = Canvas(W, H)
    rng = Rng(19)
    verlauf(c, [(0.00, hexc("#100a1e")), (0.42, hexc("#241332")),
                (0.72, hexc("#4a2440")), (1.00, hexc("#241224"))])

    finsternis(c, 396, 62, 17, hell=0.8)

    bergzug(c, H * 0.68, 18, hexc("#2a1836"), seed=9)
    tuerme(c, int(H * 0.78), hexc("#20112c"), seed=10, dichte=5)
    nebelband(c, int(H * 0.70), 34, (190, 130, 130), 0.9, seed=8)

    # Der Grund: dunkles Land bis zum unteren Rand.
    for x in range(W):
        kante = H * 0.86 + math.sin(x * 0.02 + 1) * 5
        for y in range(int(kante), H):
            c.set(x, y, mix(hexc("#191126"), hexc("#0c0816"),
                            min(1, (y - kante) / 34)))

    # Die Strasse: ein Band, das von links unten auf die Sonne zulaeuft
    # und sich dabei verjuengt - kein gefuelltes Dreieck, ein Weg.
    for x in range(W):
        t = x / W
        mitte = H - 26 - t * 46 + math.sin(x * 0.015) * 2
        breite = 13 * (1 - t * 0.85) + 1
        for y in range(int(mitte - breite), int(mitte + breite)):
            rand = abs(y - mitte) / breite
            # Zur Ferne hin nimmt die Luft die Strasse in den Himmel.
            col = mix(hexc("#241a34"), hexc("#151020"), rand)
            c.set(x, y, mix(col, hexc("#4a2440"), t * 0.55))
        # Plattenfugen: kurz und nur nah - quer durch die ganze Breite
        # gezogen sahen sie aus wie ein Gelaender.
        if t < 0.55 and int(x / (7 + t * 16)) != int((x + 1) / (7 + t * 16)):
            c.rect(x, int(mitte - breite * 0.3), 1, max(1, int(breite * 0.7)),
                   hexc("#100a1e"))

    # Cadence auf der Strasse, ein Drittel des Wegs, von hinten.
    cadence_silhouette(c, 172, H - 46, hell=0.28)
    # Ihre Funkenspur hinter ihr - der Weg, den sie schon hat.
    for k in range(18):
        t = k / 18
        x = 172 - 14 - t * 120
        y = H - 52 - t * 4 + math.sin(k * 1.7) * 4
        c.blend(int(x), int(y), (127, 232, 216, int(90 * (1 - t))))

    koernung(c, 5, seed=6)
    return c


# ---------------------------------------------------------------- Bau

def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bilder = {
        "titel": titelbild,
        "intro_0": tafel_heimat,
        "intro_1": tafel_riss,
        "intro_2": tafel_abschied,
        "intro_3": tafel_kernschatten,
        "intro_4": tafel_aufbruch,
    }
    for name, fn in bilder.items():
        fn().to_image().save(OUT / f"{name}.png")
    print(f"titel      -> {len(bilder)} Bilder in Resources/Titel")


if __name__ == "__main__":
    build()
