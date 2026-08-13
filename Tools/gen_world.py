"""
Erzeugt Tilesets, Ausstattung und Effekt-Sprites.

Die Parallax-Hintergruende stehen in gen_backdrops.py - die sind komponiert,
nicht generiert, und gehoeren deshalb nicht hierher.

Die Welt ist ein Oekosystem aus Klang: Boden traegt Resonanzadern,
Kristalle leuchten im Takt, und die Dissonanz frisst sich als rote
Faeule durch das Gestein.
"""

from __future__ import annotations

import math
from pathlib import Path

from pixelkit import (Atlas, Canvas, Palette as P, Rng, bezier, hash01,
                      hexc, mix, shade)

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Atlas"
TS = 16  # Kachelgroesse

REGIONS = ["hain", "kathedrale", "grotten", "dissonanz", "bruecke"]


# ----------------------------------------------------------------- Kacheln

TILE_OVERHANG = 8   # Platz ueber der Kachel fuer Bewuchs, der ueberhaengt

# Und dasselbe nach unten. Eine Bodenmasse, unter der Luft ist, endete
# bisher an einer geraden Kante mit ein paar Zapfen darauf - ein Brett.
# In den Vorbildern haengt unter jeder freiliegenden Unterseite etwas:
# Wurzeln, Moos, abgebrochener Fels. Der Platz dafuer muss in der Kachel
# stehen, sonst wird er am Raster abgeschnitten.
TILE_UNDERHANG = 12
TILE_H = TS + TILE_OVERHANG + TILE_UNDERHANG


def tile_solid(region: str, variant: int, edges: str) -> Canvas:
    """
    Ein Bodenstueck.

    Die Kachel ist hoeher als das Raster: oben liegen acht Pixel Luft, in die
    Gras, Moos und Wurzeln hineinwachsen duerfen. Ohne diesen Ueberhang endet
    jeder Boden an einer geraden Linie, und genau daran erkennt man ein
    Kachelspiel sofort. Die Kollision bleibt davon unberuehrt - sie kennt nur
    das Raster.

    `edges` enthaelt die freiliegenden Seiten: 't' oben, 'b' unten,
    'l' links, 'r' rechts.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(TS, TILE_H)
    top = TILE_OVERHANG
    rng = Rng(1000 + variant * 7919 + (sum(map(ord, region)) * 131) % 4096)

    # Grundmasse. Die Koernung bleibt flach - bei 16 Pixeln faellt jeder
    # starke Kontrast als Muster auf, sobald sich dieselbe Kachel wiederholt.
    for y in range(TS):
        for x in range(TS):
            # Ein gleichmaessiger Verlauf ueber die Kachelhoehe ergibt bei
            # Wiederholung waagerechte Streifen. Deshalb nur die obersten
            # Reihen aufhellen und den Rest fleckig halten.
            near_top = max(0.0, 1 - y / 6) * 0.16
            mottle = (hash01(x * 3 + variant * 17, y * 5) * 0.5
                      + rng.next() * 0.5) * 0.13
            col = mix(body, shade(body, -0.30), 0.22 + mottle - near_top)
            c.set(x, top + y, col)

    if region in ("kathedrale", "bruecke"):
        # Gemauerter Stein: Quader mit Fugen, versetzt gesetzt.
        for row in range(4):
            yy = top + row * 4
            c.rect(0, yy, TS, 1, shade(body, -0.42))
            offset = 0 if row % 2 == 0 else 4
            for k in range(3):
                c.rect((offset + k * 8) % TS, yy, 1, 4, shade(body, -0.42))
            c.rect(0, yy + 1, TS, 1, shade(body, 0.07))
    elif region == "grotten":
        # Kristalladern ziehen sich durch den Fels.
        for _ in range(2):
            vx, vy = rng.int(1, TS - 2), rng.int(1, TS - 6)
            for i in range(rng.int(4, 9)):
                c.set(vx, top + vy + i, mix(body, accent, 0.30))
                c.set(vx + 1, top + vy + i, mix(body, accent, 0.12))
                if rng.chance(0.45):
                    vx += 1 if rng.chance(0.5) else -1
    elif region == "dissonanz":
        # Faeule frisst sich von oben hinein.
        for x in range(TS):
            if rng.chance(0.3):
                d = rng.int(2, 7)
                for i in range(d):
                    c.set(x, top + i, mix(body, P.ROT_DIM, 0.5 - i / d * 0.4))
    else:
        # Hain: eingelagerte Steine, damit die Masse nicht leer wirkt.
        for _ in range(rng.int(1, 3)):
            px, py = rng.int(2, TS - 4), rng.int(4, TS - 4)
            r = rng.range(1.4, 2.6)
            c.ellipse(px, top + py, r, r * 0.8, shade(body, -0.22))
            c.ellipse(px - 0.4, top + py - 0.5, r * 0.6, r * 0.5, shade(body, -0.08))

    # ---- Das Innere der Masse
    #
    # Bisher war da nur Koernung, und Koernung ist kein Gestein. Aus zwei
    # Metern Abstand blieb der Boden ein grosses gleichmaessiges Feld -
    # bei den Vorbildern ist genau diese Flaeche durchgearbeitet.
    #
    # Der Trick gegen das Raster: **jeder Riss laeuft von Kante zu
    # Kante.** Ein Riss, der mitten in der Kachel anfaengt und aufhoert,
    # zeigt genau, wo die Kachel ist. Einer, der an beiden Enden am Rand
    # ankommt, trifft dort auf den Riss der Nachbarkachel - nicht
    # buendig, aber nah genug, dass das Auge eine durchgehende Kluft
    # sieht statt einer Fuge.
    # Sparsam: zwei bis drei Risse je Kachel ergeben ueber eine Wand
    # hinweg ein Netz, und ein Netz ist wieder ein Muster.
    _risse(c, top, body, rng, anzahl=rng.int(0, 2))

    # Eine angedeutete Schichtung. Sie kippt je nach Variante, damit sich
    # ueber mehrere Kacheln keine Waagerechte bildet.
    neigung = (-0.35, 0.0, 0.28, -0.15, 0.4, -0.28, 0.12, 0.34)[variant % 8]
    for band in range(2):
        y0 = 3 + band * 7 + int(hash01(variant, band) * 3)
        for x in range(TS):
            yy = top + int(y0 + neigung * (x - TS / 2))
            if top <= yy < top + TS - 1:
                c.blend(x, yy, (*shade(body, -0.22)[:3], 90))
                c.blend(x, yy + 1, (*shade(body, 0.10)[:3], 45))

    # ---- Kanten

    if "t" in edges:
        # Der Kamm laeuft unregelmaessig - eine gerade Linie verraet das Raster.
        crest = _crest_profile(variant + 40, amplitude=3)
        for x in range(TS):
            k = crest[x]
            c.rect(x, top - k, 1, k, mix(body, shade(body, -0.2), 0.4))
            c.set(x, top - k, mix(edge, accent, 0.30))
            c.set(x, top - k + 1, edge)
            c.set(x, top - k + 2, mix(edge, body, 0.5))
            # Unter dem Licht wird es sofort dunkel: das gibt der Kante Tiefe.
            c.set(x, top - k + 3, shade(body, -0.14))

        # Bewuchs, der in den Ueberhang hineinragt.
        if region == "hain":
            # Nicht jede Kachel traegt gleich viel: sonst laeuft ueber den
            # ganzen Boden ein gleichmaessiger Kamm.
            density = (0.30, 0.62, 0.44, 0.10, 0.52, 0.22)[variant % 6]
            dark_blade = mix(edge, body, 0.55)
            for x in range(TS):
                if hash01(x * 7 + variant * 31, 9) >= density:
                    continue
                h = 2 + int(hash01(x, variant) * 6)
                lean = -1 if hash01(x, 3) > 0.5 else 1
                # Der Halm steht im Schatten, nur die Spitze faengt Licht.
                for i in range(h):
                    t = i / max(1, h)
                    c.set(x + int(lean * i * 0.35), top - crest[x] - i,
                          mix(dark_blade, edge, t * 0.75))
                tip = mix(edge, accent, 0.30) if hash01(x, 23) > 0.7 else edge
                c.set(x + int(lean * h * 0.35), top - crest[x] - h, tip)
            # Moospolster in den Senken.
            for x in range(TS):
                if crest[x] == 0 and hash01(x, 17) > 0.62:
                    c.set(x, top - 1, mix(edge, body, 0.35))
        elif region == "grotten":
            for _ in range(2):
                x = rng.int(1, TS - 2)
                h = rng.int(2, 5)
                for i in range(h):
                    w = 1 if i > h // 2 else 2
                    c.rect(x, top - crest[x] - i, w, 1,
                           mix(accent, edge, i / max(1, h)))
        elif region == "dissonanz":
            for x in range(TS):
                if hash01(x * 5, variant) > 0.72:
                    h = rng.int(2, 4)
                    for i in range(h):
                        c.set(x, top - crest[x] - i, mix(P.ROT, P.ROT_DIM, i / h))
        else:
            # Kathedrale: eine schmale Simskante, kein Bewuchs.
            c.rect(0, top - 1, TS, 1, shade(edge, 0.10))

        # Wurzeln und Risse laufen von der Kante nach unten in die Masse.
        for _ in range(rng.int(1, 3)):
            rx = rng.int(1, TS - 2)
            depth = rng.int(4, 11)
            for i in range(depth):
                c.set(rx, top + i, shade(body, -0.26))
                if rng.chance(0.35):
                    rx += 1 if rng.chance(0.5) else -1

    if "b" in edges:
        # Die Unterkante bekommt dieselbe Behandlung wie der Kamm, nur
        # andersherum: ein unregelmaessiges Profil statt einer Linie, und
        # darunter haengt etwas in den Unterhang hinein.
        boden = top + TS
        saum = _crest_profile(variant + 90, amplitude=3)
        for x in range(TS):
            k = saum[x]
            for i in range(k):
                c.set(x, boden + i, mix(shade(body, -0.34), shade(body, -0.52),
                                        i / max(1, k)))
            c.set(x, boden + k - 1 if k else boden - 1, shade(body, -0.55))

        if region == "hain":
            # Wurzeln. Sie sind das, was einen Erdvorsprung von einem
            # Brett unterscheidet - unterschiedlich lang, leicht driftend,
            # und die laengsten haengen frei.
            wurzel = mix(shade(body, -0.42), edge, 0.10)
            for x in range(TS):
                if hash01(x * 7 + variant * 29, 61) > 0.52:
                    continue
                laenge = 2 + hash01(x, variant + 7) * (TILE_UNDERHANG - 3)
                drift = (hash01(x, 71) - 0.5) * 0.5
                px = float(x)
                for i in range(int(laenge)):
                    t = i / max(1.0, laenge)
                    px += drift
                    c.set(int(px), boden + saum[x] + i,
                          mix(wurzel, P.INK, 0.15 + t * 0.55))
        elif region == "grotten":
            for x in range(0, TS, 3):
                if hash01(x, variant + 31) > 0.55:
                    ln = 2 + int(hash01(x, 41) * 7)
                    for i in range(ln):
                        c.set(x, boden + saum[x] + i,
                              mix(accent, shade(body, -0.5), 0.3 + i / ln * 0.6))
        elif region == "dissonanz":
            for x in range(TS):
                if hash01(x * 5, variant + 17) > 0.66:
                    ln = 2 + int(hash01(x, 13) * 6)
                    for i in range(ln):
                        c.set(x, boden + saum[x] + i,
                              mix(P.ROT_DIM, P.INK, 0.2 + i / ln * 0.7))
        else:
            # Kathedrale: kein Bewuchs, aber abgebrochener Stein.
            for x in range(TS):
                if hash01(x * 3, variant + 23) > 0.7:
                    c.set(x, boden + saum[x], shade(body, -0.5))
                    c.set(x, boden + saum[x] + 1, shade(body, -0.58))
    # Seitenkanten nur angedeutet: eine durchgezogene Linie ueber mehrere
    # Kacheln hinweg liest sich sofort als Raster.
    if "l" in edges:
        for y in range(TS):
            if hash01(y, variant + 3) > 0.25:
                c.set(0, top + y, mix(edge, body, 0.55))
            if hash01(y, variant + 13) > 0.55:
                c.set(1, top + y, mix(edge, body, 0.78))
    if "r" in edges:
        for y in range(TS):
            if hash01(y, variant + 7) > 0.2:
                c.set(TS - 1, top + y, shade(body, -0.36))
            if hash01(y, variant + 23) > 0.6:
                c.set(TS - 2, top + y, shade(body, -0.18))

    return c


def _risse(c: Canvas, top: int, body, rng: Rng, anzahl: int = 2) -> None:
    """
    Risse durch die Masse - von Kante zu Kante, nie mittendrin endend.

    Ein Riss hat zwei Seiten: die eine liegt im Schatten, die andere
    faengt Licht. Ohne diesen Unterschied ist er ein Kritzel; mit ihm
    ist er eine Kluft, und die Masse bekommt Dicke.
    """
    dunkel = shade(body, -0.32)
    hell = shade(body, 0.12)
    for _ in range(anzahl):
        # Start und Ziel auf zwei verschiedenen Kanten.
        seiten = [0, 1, 2, 3]
        a = seiten.pop(rng.int(0, 3))
        b = seiten.pop(rng.int(0, 2))

        def punkt(seite: int) -> tuple[float, float]:
            t = rng.range(0.15, 0.85)
            if seite == 0:
                return t * TS, 0.0
            if seite == 1:
                return float(TS - 1), t * TS
            if seite == 2:
                return t * TS, float(TS - 1)
            return 0.0, t * TS

        x0, y0 = punkt(a)
        x1, y1 = punkt(b)
        # Ein Knick in der Mitte, damit der Riss nicht gerade laeuft.
        mx = (x0 + x1) / 2 + rng.range(-3.5, 3.5)
        my = (y0 + y1) / 2 + rng.range(-3.5, 3.5)
        schritte = int(max(abs(x1 - x0), abs(y1 - y0))) * 2 + 4
        for i in range(schritte + 1):
            t = i / schritte
            # Quadratische Bezier ueber den Knick.
            u = 1 - t
            px = u * u * x0 + 2 * u * t * mx + t * t * x1
            py = u * u * y0 + 2 * u * t * my + t * t * y1
            xi, yi = int(px), int(py)
            if not (0 <= xi < TS and 0 <= yi < TS):
                continue
            c.set(xi, top + yi, dunkel)
            # Die Lichtseite versetzt, und nur streckenweise - eine
            # durchgezogene Doppellinie sieht gezeichnet aus.
            if hash01(xi * 3, yi * 5) > 0.45 and yi + 1 < TS:
                c.blend(xi, top + yi + 1, (*hell[:3], 70))


def _crest_profile(seed: int, amplitude: int = 2) -> list[int]:
    """
    Ein unregelmaessiger Kamm, dessen Enden auf null liegen.

    Das ist der Trick gegen sichtbare Kachelkanten: variiert die Hoehe frei,
    springt sie an jeder Kachelgrenze. Sind Anfang und Ende festgenagelt,
    treffen sich zwei beliebige Kacheln immer bruchlos - und dazwischen darf
    der Kamm trotzdem tun, was er will.
    """
    profile = []
    for x in range(TS):
        # Zu den Raendern hin auslaufen lassen.
        fade = min(x, TS - 1 - x) / 3.0
        k = hash01(x * 11 + seed * 53, 7) * amplitude
        profile.append(int(min(k, k * fade)))
    return profile


def tile_platform(region: str, variant: int = 0, cap: str = "") -> Canvas:
    """
    Eine durchsteigbare Plattform.

    Sie bekommt dieselbe Behandlung wie der Boden: unregelmaessiger Kamm,
    Licht nur auf der Oberkante, Bewuchs im Ueberhang, ausgefranste
    Unterkante - und auslaufende Enden, damit sie nicht abgeschnitten wirkt.

    Ein Zwischenstand hatte sie doppelt so dick und mit haengendem
    Wurzelwerk. Das war zu viel: bei sieben Pixeln Hoehe wird jedes
    zusaetzliche Detail zu Rauschen, und die klare Silhouette ging dabei
    verloren. Weniger traegt hier weiter.

    `cap` sagt, ob links ('l') oder rechts ('r') das Ende liegt.
    """
    body, edge, accent = P.REGIONS[region][:3]
    # Dicker als bisher und mit Platz nach unten: eine Plattform von
    # sieben Pixeln Hoehe ist ein Brett, und ein Brett bleibt ein Brett,
    # egal was oben darauf waechst. Was sie zu einem gewachsenen
    # Vorsprung macht, ist die Unterseite - Wurzeln, Bruch, Ausfransung -
    # und die braucht Platz ausserhalb des Rasters.
    c = Canvas(TS, 12 + TILE_OVERHANG + TILE_UNDERHANG)
    top = TILE_OVERHANG
    crest = _crest_profile(variant)
    rng = Rng(2100 + variant * 331 + sum(map(ord, region)) * 7)

    # Die Unterkante laeuft frei, wie der Kamm oben. Vorher war sie eine
    # gerade Linie ueber die ganze Plattform - und eine gerade Linie
    # unter einer unregelmaessigen Oberkante liest sich als Brett mit
    # Grasstreifen.
    saum = [2 + int(hash01(x * 5 + variant * 29, 3) * 3)
            + int(math.sin(x * 0.55 + variant) * 1.4 + 1.4) for x in range(TS)]

    for x in range(TS):
        thin = 0
        if "l" in cap:
            thin = max(thin, max(0, 5 - x))
        if "r" in cap:
            thin = max(thin, max(0, x - (TS - 6)))
        if thin >= 5:
            continue
        k = crest[x]
        depth = 8 - thin
        for i in range(depth + k):
            t = i / (depth + k)
            c.set(x, top - k + i, mix(shade(body, 0.10), shade(body, -0.40), t ** 0.6))
        c.set(x, top - k, mix(edge, accent, 0.20))
        c.set(x, top - k + 1, mix(edge, body, 0.28))

        # Die ausgefranste Unterseite, die in den Unterhang reicht.
        unten = top - k + depth + k
        for i in range(max(0, saum[x] - thin)):
            t = i / max(1, saum[x])
            c.set(x, unten + i, mix(shade(body, -0.44), P.INK, 0.10 + t * 0.45))

    # Wurzeln, die aus der Unterseite fallen. Sie sind das eigentliche
    # Kennzeichen: ein Vorsprung haengt unten aus, ein Brett nicht.
    if region in ("hain", "grotten", "dissonanz"):
        wurzel = mix(shade(body, -0.46), P.INK, 0.25)
        for x in range(TS):
            if ("l" in cap and x < 5) or ("r" in cap and x > TS - 6):
                continue
            if hash01(x * 7 + variant * 13, 51) > 0.42:
                continue
            k = crest[x]
            unten = top - k + 8 + k + saum[x]
            laenge = 1 + int(hash01(x, variant + 5) * (TILE_UNDERHANG - 2))
            drift = (hash01(x, 31) - 0.5) * 0.45
            px = float(x)
            for i in range(laenge):
                px += drift
                t = i / max(1, laenge)
                c.set(int(px), unten + i, mix(wurzel, P.INK, t * 0.55))

    if region == "hain":
        for x in range(TS):
            if hash01(x * 9 + variant * 23, 13) < 0.26:
                if ("l" in cap and x < 4) or ("r" in cap and x > TS - 5):
                    continue
                h = 2 + int(hash01(x, variant + 5) * 4)
                lean = -1 if hash01(x, 11) > 0.5 else 1
                for i in range(h):
                    t = i / max(1, h)
                    c.set(x + int(lean * i * 0.3), top - crest[x] - 1 - i,
                          mix(mix(edge, body, 0.55), edge, t * 0.7))
    elif region == "grotten":
        for x in range(0, TS, 5):
            if hash01(x, variant) > 0.45:
                c.set(x, top - crest[x] - 1, mix(accent, edge, 0.4))
                c.set(x, top - crest[x] - 2, mix(accent, edge, 0.7))
    return c


def tile_slope(region: str, variant: int, rise_start: float, rise_end: float) -> Canvas:
    """
    Eine Schraege. `rise_start`/`rise_end` geben die Oberflaeche an linker und
    rechter Kante an, 0 oben und 1 unten.

    45 Grad wirken im Gelaende wie eine Rutsche. Die sanfte Fassung verteilt
    dieselbe Steigung auf zwei Kacheln - das sieht nach gewachsenem Hang aus.
    Zusaetzlich wird die Kante gerundet: an den Enden laeuft sie weicher aus,
    damit der Uebergang zum flachen Boden keinen Knick hat.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(TS, TS + TILE_OVERHANG)
    top = TILE_OVERHANG

    for x in range(TS):
        u = x / (TS - 1)
        rise = rise_start + (rise_end - rise_start) * u
        # Weiche Enden: die Kante wird an den Kachelraendern leicht gerundet.
        bow = math.sin(u * math.pi) * 0.06 * (1 if rise_end < rise_start else -1)
        surface = top + int(round((rise + bow) * TS))
        surface = max(top, min(top + TS - 1, surface))
        surface -= int(hash01(x * 9 + variant * 41, 3) * 2)
        surface = max(top, surface)

        for y in range(surface, top + TS):
            d = (y - surface) / TS
            c.set(x, y, mix(body, shade(body, -0.30), 0.22 + d * 0.35))

        c.set(x, surface, mix(edge, accent, 0.28))
        c.set(x, surface + 1, edge)
        c.set(x, surface + 2, mix(edge, body, 0.5))
        c.set(x, surface + 3, shade(body, -0.14))

        if region == "hain":
            density = (0.34, 0.58, 0.44, 0.16)[variant % 4]
            if hash01(x * 7 + variant * 31, 9) < density:
                h = 2 + int(hash01(x, variant) * 4)
                lean = -1 if hash01(x, 3) > 0.5 else 1
                for i in range(h):
                    t = i / max(1, h)
                    c.set(x + int(lean * i * 0.35), surface - 1 - i,
                          mix(mix(edge, body, 0.55), edge, t * 0.75))
        elif region == "grotten":
            if hash01(x * 5, variant) > 0.82:
                c.set(x, surface - 1, mix(accent, edge, 0.5))
    return c


SLOPE_KINDS = {
    "up": (1.0, 0.0), "down": (0.0, 1.0),
    "uplow": (1.0, 0.5), "uphigh": (0.5, 0.0),
    "downhigh": (0.0, 0.5), "downlow": (0.5, 1.0),
}


def deckenschraege(region: str, variant: int,
                   fall_start: float, fall_end: float) -> Canvas:
    """
    Eine Schraege fuer die Decke - eigenes Bild, keine gekippte Bodenkachel.

    Gekippt sah man es sofort: eine Bodenschraege traegt ihr Licht auf der
    Oberkante und darauf Gras. Kopfueber haengt das Gras dann *unter* der
    Decke und die hellste Linie im Bild liegt an ihrer Unterkante - Licht
    von unten, in einem Wald, in dem es von oben kommt.

    An einer Decke ist es umgekehrt: die Unterkante ist die dunkelste
    Linie im Bild, denn dahinter ist Fels und darunter Luft. Was daran
    haengt, haengt herunter und ist dunkel.

    `fall_start`/`fall_end` sagen, wie tief der Fels an linker und rechter
    Kante herunterreicht: 0 gar nicht, 1 die ganze Kachel.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(TS, TS + TILE_UNDERHANG)
    rng = Rng(3300 + variant * 811 + sum(map(ord, region)) * 17)

    for x in range(TS):
        u = x / (TS - 1)
        fall = fall_start + (fall_end - fall_start) * u
        # Weiche Enden, damit der Uebergang zur flachen Decke keinen Knick hat.
        bogen = math.sin(u * math.pi) * 0.05 * (1 if fall_end > fall_start else -1)
        kante = int(round((fall + bogen) * TS))
        kante = max(0, min(TS, kante + int(hash01(x * 7 + variant * 23, 5) * 2)))
        if kante <= 0:
            continue

        for y in range(kante):
            t = y / max(1, kante)
            # Nach unten hin dunkler: die Masse liegt im eigenen Schatten.
            c.set(x, y, mix(body, shade(body, -0.34), 0.18 + t * 0.52))
        # Die Unterkante als dunkelste Linie, darueber ein schmaler
        # Schimmer - das ist alles an Licht, was hier hingehoert.
        c.set(x, kante - 1, shade(body, -0.55))
        if kante >= 3:
            c.set(x, kante - 2, shade(body, -0.30))
            c.set(x, kante - 3, mix(body, edge, 0.10))

        # Was herunterhaengt: kurz, dunkel, unregelmaessig.
        if region == "hain":
            if hash01(x * 5 + variant * 31, 41) < 0.34:
                laenge = 1 + int(hash01(x, variant + 3) * 4)
                for i in range(laenge):
                    c.set(x, kante + i,
                          mix(shade(body, -0.45), P.INK, 0.2 + i / laenge * 0.5))
        elif region == "grotten":
            if hash01(x * 3, variant + 9) > 0.82:
                laenge = 2 + int(hash01(x, 13) * 4)
                for i in range(laenge):
                    c.set(x, kante + i,
                          mix(accent, shade(body, -0.5), 0.35 + i / laenge * 0.55))
        elif region == "dissonanz":
            if hash01(x * 5, variant + 7) > 0.74:
                for i in range(2 + int(hash01(x, 3) * 3)):
                    c.set(x, kante + i, mix(P.ROT_DIM, P.INK, 0.3 + i * 0.2))

    # Ein paar laengere Zapfen, damit die Kante nicht gleichmaessig franst.
    if region in ("hain", "grotten"):
        for _ in range(rng.int(0, 2)):
            x = rng.int(2, TS - 3)
            u = x / (TS - 1)
            kante = int(round((fall_start + (fall_end - fall_start) * u) * TS))
            if kante < 3:
                continue
            for i in range(rng.int(3, TILE_UNDERHANG)):
                w = 2 if i < 2 else 1
                c.rect(x, kante + i, w, 1,
                       mix(shade(body, -0.5), P.INK, 0.25 + i * 0.06))
    return c


def edge_prop(region: str, variant: int, frame: int = 0, frames: int = 1) -> Canvas:
    """
    Eine Requisite fuer die Bodenkante: Stein, Wurzelknaeuel, Reisig.

    Der eigentliche Grund, warum handgezeichnete Karten kein Raster zeigen,
    ist nicht das Kachelbild - es sind die Dinge, die auf den Naehten liegen.
    Diese Requisiten werden genau ueber die Kachelgrenze gesetzt und brechen
    die Linie dort, wo sie sonst sichtbar waere.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(22, 16)
    rng = Rng(700 + variant * 131 + sum(map(ord, region)))
    kind = variant % 4
    cx, base = 11, 15
    dark = shade(body, -0.16)

    # Alles, was aus dem Boden ragt, wiegt sich. Unten ist es festgewachsen,
    # oben schwingt es am weitesten - deshalb haengt der Ausschlag an der
    # Hoehe ueber dem Boden und nicht an einer festen Verschiebung.
    schwung = math.sin(frame / max(1, frames) * math.tau + variant * 1.3)

    def weht(h: float) -> float:
        return schwung * (h / 12.0) ** 1.35 * 3.4

    if kind == 0:
        # Stein, halb im Boden.
        w = rng.range(5, 9)
        c.blob(cx, base - w * 0.35, w, dark, rng, lumps=6, squash=0.62)
        c.blob(cx - w * 0.3, base - w * 0.55, w * 0.45, shade(body, 0.06), rng, lumps=4)
    elif kind == 1:
        # Wurzelknaeuel, das ueber die Kante quillt.
        for i in range(4):
            a = -2.2 + i * 0.6
            x0, y0 = cx + math.cos(a) * 6, base - 2
            pts = bezier((x0, y0), (x0 + math.cos(a) * 5, y0 - 5),
                         (cx + math.cos(a) * 9 + weht(7), base - 8),
                         (cx + math.cos(a) * 11 + weht(9), base - 6), 14)
            c.stroke(pts, 3.0, 1.0, dark)
        c.blob(cx, base - 2, 7, dark, rng, lumps=5, squash=0.5)
    elif kind == 2:
        # Reisig und Halme.
        for i in range(5):
            lean = rng.range(-0.5, 0.5)
            h = rng.range(5, 12)
            x = cx + rng.range(-7, 7)
            c.stroke([(x + lean * k + weht(k), base - k) for k in range(int(h))],
                     2.0, 1.0, dark)
            c.set(int(x + lean * h + weht(h)), int(base - h), mix(edge, body, 0.5))
    else:
        # Ein Bueschel niedriger Polster.
        for i in range(3):
            c.blob(cx + rng.range(-7, 7), base - rng.range(1, 3),
                   rng.range(3, 6), dark, rng, lumps=5, squash=0.55)

    if region == "grotten":
        c.set(cx + rng.int(-4, 4), base - rng.int(3, 7), mix(accent, edge, 0.5))
    return c


def tile_spike(region: str) -> Canvas:
    """Dissonanzdornen - scharfe, verstimmte Kristallnadeln."""
    body, edge, accent = P.REGIONS[region][:3][:3]
    c = Canvas(TS, TS)
    c.rect(0, TS - 3, TS, 3, shade(body, -0.25))
    for i in range(4):
        bx = i * 4 + 2
        h = 9 + (i % 2) * 3
        for y in range(h):
            t = y / h
            w = max(1, int(round(3 * (1 - t))))
            x0 = bx - w // 2
            col = mix(P.ROT, P.ROT_DIM, t * 0.7)
            c.rect(x0, TS - 3 - y, w, 1, col)
        c.set(bx, TS - 3 - h, mix(P.ROT, P.WARM, 0.5))
    c.glow(TS / 2, TS - 8, 10, (P.ROT[0], P.ROT[1], P.ROT[2], 34))
    return c


def sockel(region: str, variant: int) -> Canvas:
    """
    Der Unterbau einer Plattform.

    In den Vorbildern schwebt keine Plattform. Jede sitzt auf etwas: auf
    einem gewachsenen Vorsprung, einer Konsole, einem Wurzelballen - und
    dahinter liegt noch eine abgeschattete Ebene. Unsere Plattformen waren
    Bretter in der Luft, und genau daran erkennt man ein Kachelbild.

    Der erste Anlauf machte daraus ueberall dieselbe Konsole: 40 Pixel
    hoch, symmetrisch, nach unten spitz zulaufend. Im Raum las sich das
    als haengender Zapfen, nicht als Unterbau - schmaler als die
    Plattform, hoeher als breit, und in jeder Region gleich. Drei Regeln
    kamen daraus:

      Breiter als hoch. Ein Unterbau traegt, er baumelt nicht.
      Unsymmetrisch. Zwei Spiegelhaelften ergeben immer einen Trichter.
      Regionseigen. Im Hain ist es ein Wurzelballen aus Erde, im Stein
      eine Konsole, im Kristall ein Absatz - nicht dreimal dasselbe.

    Der Sockel wird hinter die Plattform gesetzt (Ursprung oben Mitte) und
    haengt unter ihr heraus.
    """
    body, edge, accent = P.REGIONS[region][:3]
    breite, hoehe = 54, 26
    c = Canvas(breite, hoehe)
    cx = breite / 2
    rng = Rng(2400 + variant * 617 + sum(map(ord, region)) * 29)

    fels = shade(body, -0.10)
    fels_hi = mix(fels, edge, 0.30)
    fels_lo = shade(body, -0.40)

    # Die abgeschattete Platte dahinter - der eigentliche Trick. Sie ist
    # breiter als der Koerper und verliert nach unten die Deckkraft, damit
    # der Hintergrund an dieser Stelle zurueckfaellt.
    for y in range(hoehe):
        halb = 25 - y * 0.55
        if halb < 2:
            break
        a = int(96 * (1 - y / hoehe) ** 0.8)
        c.rect(int(cx - halb), y, int(halb * 2), 1,
               (fels_lo[0], fels_lo[1], fels_lo[2], a))

    # Die Silhouette: eine Unterkante, die ueber die Breite frei laeuft.
    # Links und rechts endet sie flach, in der Mitte haengt die Masse am
    # tiefsten - aber nicht mittig.
    #
    # Die Kurve braucht ein Plateau. Mit einer spitzen Glocke wurde der
    # Sockel ein Dreieck, und ein Dreieck unter einem Brett sieht aus wie
    # ein ausgeschnittenes Stueck Papier. Ein hoher Exponent haelt die
    # Mitte flach und laesst sie erst an den Enden schnell abfallen - das
    # ist ein Klumpen, kein Keil.
    schwer = 0.34 + variant * 0.16          # wo der Ballen am dicksten ist
    unten = []
    for x in range(breite):
        u = x / (breite - 1)
        d = abs(u - schwer) / max(schwer, 1 - schwer)
        h = (1 - d ** 3.2) * (hoehe - 5)
        # Zwei ungleiche Wellen brechen die Kurve auf, damit man sie nicht
        # mehr als Kurve liest.
        h *= 0.80 + 0.13 * math.sin(u * 9.0 + variant) \
             + 0.07 * math.sin(u * 23.0 + variant * 2.1)
        h += hash01(x * 5, variant * 13) * 3.0 - 1.0
        unten.append(max(0, min(hoehe - 1, int(h))))

    for x in range(breite):
        tief = unten[x]
        for y in range(tief):
            t = y / max(1, tief)
            q = (x - cx) / (breite / 2)
            # Licht von rechts oben, aber sparsam: der Sockel liegt unter
            # der Plattform und damit im Schatten. Ein Zwischenstand hat
            # ihn innen aufgehellt, und dann las er sich als *zweite*
            # Platte, die unter der ersten klebt, statt als ihre
            # Unterseite. Was eine Plattform traegt, ist dunkler als sie.
            hell = max(0.0, 0.34 - abs(q - 0.35) * 0.7) * (1 - t) ** 1.3
            c.set(x, y, mix(fels_lo, fels, min(1.0, 0.10 + hell)))
        if tief:
            c.set(x, tief - 1, shade(fels_lo, -0.30))

    if region == "hain":
        # Erdballen: Wurzeln, die aus der Unterkante heraushaengen, und
        # eingelagerte Steine. Das Gras oben liefert die Plattform selbst.
        wurzel = mix(fels_lo, P.INK, 0.35)
        for _ in range(rng.int(4, 7)):
            x = rng.int(6, breite - 7)
            if unten[x] < 5:
                continue
            laenge = rng.range(4, 11)
            drift = rng.range(-0.35, 0.35)
            for i in range(int(laenge)):
                px = x + drift * i + math.sin(i * 0.6) * 1.2
                c.set(int(px), unten[x] + i, wurzel)
                if i < laenge * 0.4:
                    c.set(int(px) + 1, unten[x] + i, mix(wurzel, fels, 0.4))
        for _ in range(rng.int(2, 4)):
            px, py = rng.int(8, breite - 9), rng.int(4, hoehe - 10)
            if py < unten[px] - 3:
                r = rng.range(1.6, 3.0)
                c.ellipse(px, py, r, r * 0.78, shade(fels, -0.20))
                c.ellipse(px + 0.5, py - 0.6, r * 0.6, r * 0.5, mix(fels, edge, 0.25))
    elif region == "kathedrale":
        # Eine Konsole: zwei Absaetze und eine Einrollung, aber nur auf
        # einer Seite - eine Kragsteinkonsole ist nie symmetrisch.
        for y0, w in ((5, 21), (11, 15)):
            c.rect(int(cx - w), y0, w * 2, 1, mix(fels_hi, accent, 0.16))
            c.rect(int(cx - w), y0 + 1, w * 2, 1, fels_lo)
        mx, my = cx + (4 if variant % 2 else -5), hoehe - 9
        for i in range(24):
            a = i / 24 * math.tau * 1.2
            rr = 4.2 * (1 - i / 40)
            c.set(int(mx + math.cos(a) * rr), int(my + math.sin(a) * rr * 0.8),
                  mix(fels_hi, accent, 0.14))
    elif region == "grotten":
        # Kristallnadeln, die unter dem Absatz hervorstehen.
        for _ in range(rng.int(2, 4)):
            x = rng.int(8, breite - 9)
            if unten[x] < 6:
                continue
            ln = rng.int(4, 9)
            for i in range(ln):
                t = i / ln
                w = max(1, int(2.4 * (1 - t)))
                c.rect(x - w // 2, unten[x] - 2 + i, w, 1,
                       mix(accent, fels_lo, 0.3 + t * 0.5))
    else:
        # Dissonanz: die Faeule frisst sich von unten in den Sockel.
        for x in range(breite):
            if unten[x] > 4 and hash01(x * 3, variant) > 0.6:
                d = rng.int(2, 5)
                for i in range(d):
                    c.set(x, unten[x] - 1 - i,
                          mix(P.ROT_DIM, fels_lo, 0.3 + i / d * 0.6))

    # Kein Lichtsaum an der Oberkante. Dort liegt die Plattform auf; eine
    # helle Linie an dieser Stelle zieht genau die Fuge nach, die man
    # nicht sehen soll - und aus zwei Teilen werden sichtbar zwei Teile.
    return c


def hang_prop(region: str, variant: int, frame: int = 0, frames: int = 1) -> Canvas:
    """
    Was von der Decke haengt: Zapfen, Wurzelbart, Tropfstein.

    Der Boden sieht gut aus, weil Requisiten quer ueber seinen Kacheln
    liegen und die Rasterlinie brechen. Die Decke hatte nichts davon -
    darum blieb sie eine Treppe aus Rechtecken, egal wie fein das
    Hoehenprofil war. Das hier ist dieselbe Behandlung, nur andersherum:
    aufgehaengt an der Oberkante, ueber die Kachelgrenze hinaus.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(20, 26)
    rng = Rng(1500 + variant * 97 + sum(map(ord, region)))
    cx = 10
    fels = shade(body, -0.10)
    fels_hi = mix(fels, edge, 0.30)
    kind = variant % 3

    # Auch Haengendes bewegt sich - unten am weitesten, oben gar nicht.
    schwung = math.sin(frame / max(1, frames) * math.tau + variant * 1.7)

    if kind == 0:
        # Ein Zapfen: breit an der Decke, spitz nach unten, leicht schief.
        laenge = rng.range(11, 22)
        breite = rng.range(3.2, 5.4)
        neigung = rng.range(-0.28, 0.28)
        for i in range(int(laenge)):
            t = i / laenge
            w = max(1, breite * (1 - t) ** 0.72)
            x = cx + neigung * i + schwung * (t ** 2) * 0.8
            for d in range(-int(w), int(w) + 1):
                # Die dem Licht zugewandte Seite bleibt hell, die andere
                # faellt weg - sonst ist der Zapfen ein grauer Strich.
                col = fels_hi if d >= int(w) - 1 else mix(fels, P.INK, t * 0.45)
                c.set(int(round(x)) + d, i, col)
        c.set(int(round(cx + neigung * laenge)), int(laenge),
              mix(fels_hi, accent, 0.25))
    elif kind == 1:
        # Wurzelbart: mehrere duenne Straenge, verschieden lang.
        for k in range(rng.int(3, 5)):
            x0 = cx + rng.range(-6, 6)
            laenge = rng.range(7, 20)
            for i in range(int(laenge)):
                t = i / laenge
                x = x0 + math.sin(i * 0.35 + k) * 1.4 + schwung * (t ** 2) * 1.6
                c.set(int(round(x)), i, mix(fels, P.INK, 0.2 + t * 0.5))
                if i % 5 == 2:
                    c.set(int(round(x)) + 1, i, shade(fels, -0.3))
    else:
        # Ein Vorhang, der ueber die Kante quillt.
        #
        # Hier hing vorher ein rundlicher Klumpen mit ein paar Faeden
        # darunter. Aus zwei Metern Abstand war das ein Wespennest, das
        # mitten im Wald an der Decke klebte - eine Form, die niemand
        # bestellt hat und die man dann ueberall sieht. Ein Vorhang macht
        # dieselbe Arbeit (er nimmt der Stufe ihre Waagerechte) und
        # behauptet nichts.
        breite = int(rng.range(9, 16))
        x0 = cx - breite // 2
        for i in range(breite):
            # Zwei Wellen uebereinander: keine gerade Kante, kein Zacken
            # in gleichem Abstand.
            ln = rng.range(4, 9) + math.sin(i * 0.7 + variant) * 3.0
            ln = max(2.0, ln + math.sin(i * 0.23) * 2.5)
            for k in range(int(ln)):
                t = k / ln
                if t > 0.6 and rng.chance(t * 0.5):
                    continue
                c.set(int(x0 + i + schwung * (t ** 2) * 1.4), k,
                      mix(fels, P.INK, 0.15 + t * 0.55))
            if ln > 4:
                c.set(x0 + i, 0, fels_hi)
        # Und ein paar laengere Straenge, die aus dem Vorhang fallen.
        for _ in range(rng.int(1, 3)):
            x = x0 + rng.int(1, max(2, breite - 1))
            h = rng.int(7, 16)
            for i in range(h):
                t = i / h
                c.set(int(x + schwung * (t ** 2) * 2.2 + math.sin(i * 0.4) * 1.1),
                      i, mix(fels, P.INK, 0.3 + t * 0.5))

    c.shadow_pass((0, 1), -0.20)
    return c


def gedreht(c: Canvas, viertel: int) -> Canvas:
    """
    Dreht eine Kachel um Vielfache von 90 Grad.

    Dornen sind dieselben Dornen, egal ob sie auf dem Boden stehen oder
    von der Decke haengen - sie zeigen nur woandershin. Vorher wurde
    ueberall dieselbe Kachel gesetzt, und an der Decke sah das aus wie
    Gras, das nach oben waechst.
    """
    viertel %= 4
    if viertel == 0:
        return c
    out = Canvas(c.h if viertel % 2 else c.w, c.w if viertel % 2 else c.h)
    for y in range(c.h):
        for x in range(c.w):
            px = c.get(x, y)
            if not px[3]:
                continue
            if viertel == 1:        # 90 Grad im Uhrzeigersinn
                out.set(c.h - 1 - y, x, px)
            elif viertel == 2:
                out.set(c.w - 1 - x, c.h - 1 - y, px)
            else:                   # 270 Grad
                out.set(y, c.w - 1 - x, px)
    return out


def gekippt(c: Canvas) -> Canvas:
    """
    Spiegelt eine Kachel an der Waagerechten - oben wird unten.

    Der Unterschied zu `gedreht(c, 2)` ist genau eine Achse, und genau
    daran hing der Deckenfehler: eine Drehung um 180 Grad spiegelt
    *auch* links und rechts. Eine Bodenschraege, die nach rechts
    ansteigt, wird dabei zu einer Deckenschraege, die nach **links**
    faellt. Die Decke lief also durchweg gegen ihre eigene Richtung.

    Was am Boden unten Fels ist, ist an der Decke oben Fels - mehr
    passiert beim Umbau einer Schraege nicht.
    """
    out = Canvas(c.w, c.h)
    for y in range(c.h):
        for x in range(c.w):
            px = c.get(x, y)
            if px[3]:
                out.set(x, c.h - 1 - y, px)
    return out


def tile_dissowall(frame: int) -> Canvas:
    """Verstimmte Sperre - nur der Basston bricht sie."""
    c = Canvas(TS, TS)
    rng = Rng(4242 + frame)
    pulse = 0.5 + 0.5 * math.sin(frame / 4 * math.tau)
    for y in range(TS):
        for x in range(TS):
            n = rng.next()
            c.set(x, y, mix(hexc("#2a1622"), hexc("#4a1f30"), n * 0.7))
    for _ in range(9):
        x, y = rng.int(1, TS - 2), rng.int(1, TS - 2)
        c.set(x, y, mix(P.ROT, P.ROT_DIM, rng.next()))
    # Rissmuster
    for i in range(TS):
        c.set(i, int(TS / 2 + math.sin(i * 0.7) * 3), mix(P.ROT, P.WARM, 0.35 * pulse))
    c.frame(0, 0, TS, TS, shade(hexc("#2a1622"), -0.4))
    c.glow(TS / 2, TS / 2, 11, (P.ROT[0], P.ROT[1], P.ROT[2], int(24 + 26 * pulse)))
    return c


def tile_crystal(size: int, frame: int, tint) -> Canvas:
    """Klangkristall - pulsiert im Takt der Welt."""
    dim = (10, 14, 20)[size]
    c = Canvas(dim, dim)
    rng = Rng(77 + size * 31)
    pulse = 0.55 + 0.45 * math.sin(frame / 4 * math.tau)
    cx, cy = dim / 2, dim / 2
    shards = 3 + size
    for i in range(shards):
        a = i / shards * math.tau + 0.3
        r = dim * (0.24 + rng.next() * 0.2)
        x0, y0 = cx, cy + dim * 0.32
        x1, y1 = cx + math.cos(a) * r * 1.5, cy - dim * 0.1 + math.sin(a) * r
        c.line(x0, y0, x1, y1, mix(tint, P.INK2, 0.35))
        c.line(x0 + 1, y0, x1 + 1, y1, mix(tint, P.INK2, 0.6))
        c.set(int(x1), int(y1), mix(tint, (255, 255, 255, 255), 0.4 * pulse))
    c.ellipse(cx, cy + dim * 0.28, dim * 0.22, dim * 0.14, mix(tint, P.INK, 0.5))
    c.glow(cx, cy, dim * 0.8, (tint[0], tint[1], tint[2], int(30 + 55 * pulse)))
    return c


def tile_reed(frame: int, tint) -> Canvas:
    """Klangschilf - reagiert auf vorbeiziehenden Schall."""
    c = Canvas(12, 14)
    rng = Rng(9 + frame)
    sway = math.sin(frame / 4 * math.tau)
    for i in range(5):
        x = 1 + i * 2 + rng.int(0, 1)
        h = 7 + rng.int(0, 6)
        for y in range(h):
            t = y / h
            xx = x + sway * t * 1.8 * (0.5 + rng.next() * 0.5)
            c.set(int(round(xx)), 13 - y, mix(tint, P.INK2, 0.35 + t * 0.3))
        c.set(int(round(x + sway * 1.8)), 13 - h, mix(tint, P.WARM, 0.4))
    return c


def tile_bench(frame: int) -> Canvas:
    """
    Die Stimmgabel im Boden: Rast, Heilung, Speicherpunkt.

    Sie ist der einzige Gegenstand, vor dem die Figur stehenbleibt, also
    muss sie mehr sein als ein Symbol. Erzaehlt wird die ganze Geschichte
    der Welt an einem Stueck: unten ein gewachsener Sockel, den der Hain
    sich schon zurueckholt, darueber eine Gabel, die zu gross ist, um von
    hier zu stammen, und dazwischen der Ton, der immer noch haengt.
    """
    c = Canvas(30, 34)
    p = 0.5 + 0.5 * math.sin(frame / 6 * math.tau)
    rng = Rng(4711)
    cx, boden = 15, 33

    stein = mix(P.STONE, P.INK2, 0.25)
    stein_hi = shade(stein, 0.22)
    metall = mix(P.STONE_HI, P.WARM, 0.30)
    metall_hi = mix(metall, P.BONE, 0.45)
    metall_lo = shade(metall, -0.42)

    # --- Sockel: ein Findling, kein Quader ---------------------------------
    c.blob(cx, boden - 3, 9.5, stein, rng, lumps=7, squash=0.42)
    c.blob(cx - 2, boden - 5, 6.0, stein_hi, rng, lumps=5, squash=0.40)
    for x in range(cx - 10, cx + 11):
        h = 2 + int(hash01(x, 7) * 3)
        for i in range(h):
            if hash01(x, 30 + i) > 0.35:
                c.set(x, boden - i, shade(stein, -0.30 + i * 0.05))
    # Risse, aus denen die Gabel gewachsen ist.
    for k in range(3):
        rx = cx - 5 + k * 5
        for i in range(rng.int(3, 6)):
            c.set(rx + int(hash01(rx, i) * 2) - 1, boden - 4 - i, shade(stein, -0.45))

    # --- Die Gabel ---------------------------------------------------------
    stiel_oben = boden - 12
    for y in range(stiel_oben, boden - 3):
        w = 3 if y > stiel_oben + 2 else 2
        c.rect(cx - w // 2, y, w, 1, metall)
        c.set(cx - w // 2, y, metall_lo)
        c.set(cx + w // 2 - (1 if w % 2 == 0 else 0), y, metall_hi)

    # Der Steg, leicht gewoelbt statt als Balken.
    for dx in range(-6, 7):
        dy = int(abs(dx) * 0.28)
        c.set(cx + dx, stiel_oben - 1 + dy, metall_hi)
        c.set(cx + dx, stiel_oben + dy, metall)
        c.set(cx + dx, stiel_oben + 1 + dy, metall_lo)

    # Zwei Zinken, oben leicht nach aussen geneigt.
    for seite in (-1, 1):
        for i in range(14):
            v = i / 13
            x = cx + seite * (6 + v * 1.6)
            y = stiel_oben - 1 - i
            c.set(int(x), int(y), metall)
            c.set(int(x) - seite, int(y), metall_lo)
            c.set(int(x) + seite, int(y), metall_hi if i % 5 else metall)
        spitze_y = stiel_oben - 15
        c.set(int(cx + seite * 7.6), int(spitze_y), mix(P.TRIM, P.BONE, 0.5 + 0.4 * p))

    # --- Der Ton, der noch haengt ------------------------------------------
    # Zwischen den Zinken steht die Luft. Das ist der Grund, warum man hier
    # ausruhen kann - nicht die Bank, sondern der gehaltene Ton.
    for i in range(9):
        y = stiel_oben - 3 - i
        breite = 5.0 * math.sin((i / 9) * math.pi) ** 0.7
        a = int((60 + 90 * p) * (1 - abs(i / 9 - 0.5)))
        for dx in range(-int(breite), int(breite) + 1):
            if hash01(cx + dx, y + int(frame)) > 0.55:
                c.blend(cx + dx, y, (P.TRIM[0], P.TRIM[1], P.TRIM[2], a))

    # Funken, die vom Steg aufsteigen.
    for k in range(4):
        u = (k / 4 + frame / 6) % 1.0
        fy = stiel_oben - 2 - u * 14
        fx = cx + math.sin(u * 5 + k * 2.1) * (2 + u * 4)
        c.set(int(fx), int(fy), (P.WARM[0], P.WARM[1], P.WARM[2], int(220 * (1 - u))))

    # --- Bewuchs: der Hain holt sie sich zurueck ---------------------------
    for x in range(cx - 9, cx + 10):
        if hash01(x, 3) > 0.55:
            h = 1 + int(hash01(x, 11) * 3)
            for i in range(h):
                c.set(x, boden - 5 - i, mix(P.REGIONS["hain"][1], P.INK, 0.25))
    for k, (bx, by, r) in enumerate(((cx - 7, boden - 7, 2.0), (cx + 8, boden - 6, 1.6))):
        c.ellipse(bx, by, r, r * 0.8, mix(P.TRIM, P.INK2, 0.55))
        c.set(int(bx), int(by - r), mix(P.TRIM, P.BONE, 0.4 * p))

    c.glow(cx, stiel_oben - 4, 16, (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(26 + 30 * p)))
    return c


# ------------------------------------------------------------- Hintergruende

# ------------------------------------------------------------------ Effekte

def fx_ring(frame: int, frames: int, tint, max_r: float, thickness: float = 2) -> Canvas:
    """Ausbreitende Schallwelle."""
    dim = int(max_r * 2 + 6)
    c = Canvas(dim, dim)
    t = frame / max(1, frames - 1)
    r = max_r * (0.18 + t * 0.82)
    a = int(230 * (1 - t) ** 1.5)
    c.ring(dim / 2, dim / 2, r, thickness * (1 - t * 0.5) + 0.6, (tint[0], tint[1], tint[2], a))
    c.ring(dim / 2, dim / 2, r * 0.72, 1, (tint[0], tint[1], tint[2], int(a * 0.45)))
    return c



def fx_klinge(frame: int, frames: int, art: str) -> Canvas:
    """
    Der Schlagbogen einer Schallklinge.

    Alle Klingen schlagen gleich - der Bogen ist das Einzige, woran man
    sieht, welche man fuehrt. Deshalb steckt hier die ganze Vielfalt und
    sonst nirgends: dieselbe Bewegung, drei Handschriften.
    """
    dim = 40
    c = Canvas(dim, dim)
    cx = cy = dim / 2
    t = frame / max(1, frames - 1)
    r = 8 + t * 10
    a = int(240 * (1 - t) ** 1.3)
    # Der Bogen laeuft von oben nach unten durch und wird dabei duenner.
    spann = math.pi * (0.62 + t * 0.22)
    mitte = -math.pi / 2 + math.pi * (0.10 + t * 0.55)
    tint = {"schlicht": P.GLOW, "gezackt": P.GOLD, "glas": P.BLOOM}[art]

    schritte = 44
    for i in range(schritte + 1):
        u = i / schritte
        winkel = mitte - spann / 2 + spann * u
        dicke = (1 - abs(u - 0.5) * 1.7) * (2.4 - t * 1.4)
        if art == "gezackt":
            # Der Bogen bricht in Zacken, statt sauber durchzulaufen.
            dicke *= 0.55 + 0.75 * ((i // 4) % 2)
        if art == "glas":
            # Zwei duenne Bahnen statt einer breiten.
            dicke *= 0.5
        if dicke <= 0:
            continue
        for k in range(int(dicke) + 1):
            rr = r + k - dicke / 2
            x = cx + math.cos(winkel) * rr
            y = cy + math.sin(winkel) * rr
            fade = int(a * (1 - abs(u - 0.5) * 0.8))
            c.blend(int(x), int(y), (tint[0], tint[1], tint[2], max(0, fade)))
        if art == "glas":
            for versatz in (-3, 3):
                x = cx + math.cos(winkel) * (r + versatz)
                y = cy + math.sin(winkel) * (r + versatz)
                c.blend(int(x), int(y), (tint[0], tint[1], tint[2], int(a * 0.5)))
    return c


def fx_note(kind: int, tint) -> Canvas:
    """Notenkopf als Geschoss - der sichtbare Ton."""
    c = Canvas(12, 14)
    if kind == 0:      # Viertelnote
        c.ellipse(4, 10, 3.2, 2.4, tint)
        c.rect(6, 2, 2, 8, mix(tint, P.WARM, 0.25))
        c.set(2, 9, mix(tint, (255, 255, 255, 255), 0.5))
    elif kind == 1:    # Achtelnote mit Faehnchen
        c.ellipse(4, 10, 3.0, 2.2, tint)
        c.rect(6, 1, 2, 9, mix(tint, P.WARM, 0.25))
        for i in range(4):
            c.rect(8, 1 + i, 3 - i // 2, 1, mix(tint, P.WARM, 0.4))
    else:              # Pausenzeichen / dissonanter Splitter
        c.line(2, 2, 9, 11, tint)
        c.line(9, 2, 2, 11, tint)
        c.ellipse(5.5, 6.5, 2, 2, mix(tint, P.WARM, 0.4))
    c.glow(5, 8, 8, (tint[0], tint[1], tint[2], 60))
    return c


def fx_feather(frame: int) -> Canvas:
    """Fluegelschlag - Doppelsprung."""
    c = Canvas(20, 16)
    t = frame / 3
    spread = 0.4 + t * 0.9
    for side in (-1, 1):
        for i in range(7):
            u = i / 6
            x = 10 + side * (2 + u * 8 * spread)
            y = 10 - math.sin(u * math.pi) * 6 * spread
            col = mix(P.TRIM, P.BLOOM, u)
            c.set(int(x), int(y), (col[0], col[1], col[2], int(230 * (1 - t * 0.6))))
            c.set(int(x), int(y) + 1, (col[0], col[1], col[2], int(140 * (1 - t * 0.6))))
    c.glow(10, 9, 10, (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(70 * (1 - t))))
    return c


def fx_heart(frame: int) -> Canvas:
    """Herzschlag - Dash-Impuls."""
    c = Canvas(18, 18)
    t = frame / 3
    beat = 1 + math.sin(t * math.pi) * 0.35
    cx, cy = 9, 9
    for dy in range(-6, 7):
        for dx in range(-7, 8):
            x = dx / (5.2 * beat)
            y = -dy / (5.2 * beat)  # Pixelraster zaehlt nach unten
            v = (x * x + y * y - 0.55) ** 3 - x * x * (y ** 3) * 1.1
            if v <= 0:
                c.blend(cx + dx, cy + dy + 1, mix(P.ROT, P.WARM, 0.25))
    c.glow(cx, cy, 9 * beat, (P.ROT[0], P.ROT[1], P.ROT[2], int(90 * (1 - t * 0.5))))
    return c


def fx_burst(frame: int, tint) -> Canvas:
    """Treffer-Funken."""
    c = Canvas(22, 22)
    rng = Rng(31 + frame)
    t = frame / 4
    for i in range(10):
        a = i / 10 * math.tau + rng.range(-0.2, 0.2)
        r0 = 2 + t * 8
        r1 = r0 + 3 * (1 - t)
        x0, y0 = 11 + math.cos(a) * r0, 11 + math.sin(a) * r0
        x1, y1 = 11 + math.cos(a) * r1, 11 + math.sin(a) * r1
        col = mix(tint, P.WARM, 0.3)
        c.line(x0, y0, x1, y1, (col[0], col[1], col[2], int(240 * (1 - t))))
    c.glow(11, 11, 10 * (0.5 + t), (tint[0], tint[1], tint[2], int(120 * (1 - t))))
    return c


def fx_dust(frame: int) -> Canvas:
    """Staubwolke bei Landung und Dash."""
    c = Canvas(20, 12)
    rng = Rng(55)
    t = frame / 4
    for i in range(8):
        a = rng.range(0, math.tau)
        r = t * 8 * rng.range(0.4, 1.0)
        x = 10 + math.cos(a) * r
        y = 9 - abs(math.sin(a)) * r * 0.5
        s = max(1, int(3 * (1 - t)))
        col = mix(P.STONE_HI, P.INK2, 0.4)
        c.ellipse(x, y, s, s * 0.7, (col[0], col[1], col[2], int(170 * (1 - t))), blend=True)
    return c


def fx_flamme(frame: int, frames: int = 8) -> Canvas:
    """
    Ihre Flamme - die Gestalt, die sie an der Stimmgabel wieder annimmt.

    Sie ist das, was von ihr uebrig ist, wenn das Gefaess weg ist: ein
    Klang ohne Umriss. Deshalb hat sie keine feste Silhouette, sondern
    eine, die in jedem Bild anders steht - unten schmal, wo sie an der
    Gabel haengt, oben breit und ausgefranst.

    Zwei Toene: innen ihr blasses Kristallgruen, aussen der warme Saum,
    den man sonst nur an ihrem Kern sieht.
    """
    c = Canvas(22, 34)
    p = frame / max(1, frames) * math.tau
    kern = mix(P.BONE, P.TRIM, 0.35)
    kern_hell = mix(P.BONE, (255, 255, 255, 255), 0.5)
    saum = mix(P.AMBER, P.WARM, 0.35)
    cx = 11.0

    hoehe = 27 + math.sin(p) * 2.5
    for i in range(int(hoehe)):
        t = i / hoehe                       # 0 unten, 1 oben
        # Die Flanke: unten spitz an der Gabel, in der Mitte am
        # breitesten, oben ausgefranst.
        breite = (1.6 + 4.6 * math.sin(math.pi * min(1.0, t * 0.92 + 0.08)) ** 0.8)
        breite *= 1.0 + math.sin(p * 1.7 + t * 5.0) * 0.16
        # Die Spitze zuckt seitlich, der Fuss steht still.
        versatz = math.sin(p + t * 3.4) * (t ** 2) * 2.6
        y = int(33 - i)
        x0 = cx + versatz - breite
        x1 = cx + versatz + breite
        q = x0
        while q <= x1:
            u = abs(q - (cx + versatz)) / max(0.6, breite)
            if u > 0.72 and hash01(int(q * 3), i + frame * 7) > 1.35 - u:
                q += 0.5
                continue
            if u < 0.35:
                col, a = kern_hell, 235
            elif u < 0.72:
                col, a = kern, 205
            else:
                col, a = saum, 150
            c.blend(int(q), y, (col[0], col[1], col[2], int(a * (1 - t * 0.35))))
            q += 0.5

    # Ein Funkenpaar, das mit aufsteigt.
    for k in range(2):
        fx = cx + math.sin(p * 1.3 + k * 2.2) * 4.5
        fy = 26 - ((frame + k * 4) % frames) / frames * 22
        c.blend(int(fx), int(fy), (saum[0], saum[1], saum[2], 190))

    c.glow(cx, 20, 15, (saum[0], saum[1], saum[2], 44), power=1.7)
    return c


def fx_mote(frame: int, tint) -> Canvas:
    """Klangfunke - Resonanz, die man aufsammelt."""
    c = Canvas(8, 8)
    p = 0.55 + 0.45 * math.sin(frame / 4 * math.tau)
    c.ellipse(4, 4, 1.4 * p + 0.6, 1.4 * p + 0.6, mix(tint, (255, 255, 255, 255), 0.4))
    c.glow(4, 4, 4, (tint[0], tint[1], tint[2], int(120 * p)))
    return c


SIGIL_TINTS = {
    "fluegelschlag": P.TRIM, "herzschlag": P.ROT,
    "klangschritt": P.BLOOM, "basston": P.GOLD,
    "leier": P.GLOW, "trommel": P.GOLD, "floete": P.BLOOM,
    "metronom": P.WARM, "glocke": P.GOLD, "orgelpfeife": P.TRIM,
}


# Die Fassungen. Der Wert ist die Zahl der Oeffnungen - genau die, die auch
# im Spiel steht, denn das Siegel ist nichts als ihr Querschnitt.
EQUIPMENT_SIGILS = {
    "mantel": (4, P.BONE_SH),
    "lauschband": (2, P.AMBER),
    "flickmantel": (6, hexc("#9a8f7a")),
    "enge_fassung": (1, P.GOLD),
    "offene_fassung": (9, P.GLOW),
    "schlagfassung": (2, P.ROT),
    "gerissenes_gewand": (14, P.WARM),
}


def fx_equipment_sigil(openings: int, tint, frame: int) -> Canvas:
    """
    Das Siegel einer Fassung: der Querschnitt eines Gefaesses.

    Die Kontur ist geschlossen, bis auf genau so viele Luecken, wie die
    Fassung Oeffnungen hat - und aus jeder Luecke faehrt der Druck heraus.
    Je weniger Luecken, desto laenger die Strahlen. Man sieht der Rueckseite
    des Bildes also an, was sie im Kampf tut.
    """
    c = Canvas(28, 28)
    cx, cy = 14, 14
    p = 0.5 + 0.5 * math.sin(frame / 6 * math.tau)
    ink = mix(tint, P.INK, 0.55)

    # Gefaessform: unten bauchig, oben verjuengt - eine Urne, kein Ring.
    def radius(a: float) -> float:
        return 6.5 + 1.9 * math.sin(a) + 0.5 * math.sin(a * 2)

    # Wo die Oeffnungen sitzen. Die erste zeigt immer nach vorn - dorthin,
    # wohin auch der Fernklang geht.
    gaps = [(i * math.tau / openings) % math.tau for i in range(openings)]
    half = min(0.30, 1.1 / openings + 0.06)

    def offen(a: float) -> bool:
        return any(min(abs(a - g), math.tau - abs(a - g)) < half for g in gaps)

    # Der Koerper: dunkel gefuellt, damit das Zeichen einen Bauch hat.
    for y in range(28):
        for x in range(28):
            dx, dy = x - cx, (y - cy) / 0.96
            d = math.hypot(dx, dy)
            if d < 0.6:
                continue
            if d <= radius(math.atan2(dy, dx) % math.tau) - 1.2:
                c.blend(x, y, (ink[0], ink[1], ink[2], 190))

    steps = 260
    for i in range(steps):
        a = i / steps * math.tau
        if offen(a):
            continue
        r = radius(a)
        c.set(int(round(cx + math.cos(a) * r)),
              int(round(cy + math.sin(a) * r * 0.96)), tint)

    # Der Druck faehrt aus den Luecken. Wenige Luecken, langer Strahl.
    laenge = min(6.0, 1.8 + 6.0 / openings) * (0.78 + 0.3 * p)
    for g in gaps:
        r = radius(g) - 0.5
        c.line(cx + math.cos(g) * r, cy + math.sin(g) * r * 0.96,
               cx + math.cos(g) * (r + laenge), cy + math.sin(g) * (r + laenge) * 0.96,
               (tint[0], tint[1], tint[2], 220))
        c.set(int(round(cx + math.cos(g) * (r + laenge + 1))),
              int(round(cy + math.sin(g) * (r + laenge + 1) * 0.96)),
              (tint[0], tint[1], tint[2], 110))

    # Der Klang darin.
    c.ellipse(cx, cy + 1, 3.2 + p * 0.8, 3.0 + p * 0.8,
              (tint[0], tint[1], tint[2], int(60 + 50 * p)), blend=True)
    c.glow(cx, cy, 12, (tint[0], tint[1], tint[2], int(40 + 30 * p)))
    return c



# Siegel. Die Kerben am Rand sind die Kosten - man sieht dem Fundstueck
# also an, was es belegt, bevor man es aufhebt.
SIEGEL_SIGILS = {
    "scherbenherz": (2, P.ROT),
    "bleisiegel":   (2, P.STONE_HI),
    "taubes_ohr":   (2, hexc("#6d7a94")),
    "pilgerstab":   (1, P.WARM),
    "kreiselsiegel": (3, P.GLOW),
    "nadelsiegel":  (3, P.BLOOM),
    "nachhall":   (1, P.GLOW),
    "dauerton":   (2, P.TRIM),
    "bruchstein": (2, P.STONE_HI),
    "federstaub": (1, P.BLOOM),
    "windschliff": (3, hexc("#9fe8ff")),
    "hohlklang":  (2, P.WARM),
    "stille":     (1, P.BONE_SH),
    "wurzelmark": (1, hexc("#8a6b48")),
    "stammklang": (2, hexc("#7fbf9a")),
    "glockenmund": (2, hexc("#e8c76a")),
    "spiegelgrund": (2, hexc("#9fe8ff")),
    "taubwerk": (3, hexc("#5c6470")),
    "hoerrohr": (1, hexc("#c9a86a")),
    "muenzsiegel": (2, hexc("#e0c060")),
}



# Die Klingen. Sie unterscheiden sich nur im Bild - deshalb steht hier auch
# nur ein Umriss und kein Wert.
KLINGEN_SIGILS = {
    "schlicht": P.GLOW,
    "gezackt": P.GOLD,
    "glas": P.BLOOM,
}


def fx_klingen_sigil(art: str, tint, frame: int) -> Canvas:
    """Das Siegel einer Schallklinge: die Klinge selbst, senkrecht stehend."""
    c = Canvas(28, 28)
    cx, cy = 14, 15
    p = 0.5 + 0.5 * math.sin(frame / 6 * math.tau)
    kante = mix(tint, P.BONE, 0.55)

    # Griff
    c.rect(cx - 1, cy + 5, 3, 5, mix(P.BONE_LO, P.CLOAK, 0.4))
    c.rect(cx - 3, cy + 4, 7, 1, mix(tint, P.BONE_SH, 0.4))

    # Blatt: nach oben schmaler werdend.
    for i in range(15):
        t = i / 14
        w = max(1, int(3.2 * (1 - t) ** 0.6))
        y = cy + 3 - i
        if art == "gezackt" and i % 3 == 2:
            w += 1
        for dx in range(-w, w + 1):
            rand = abs(dx) >= w
            if art == "glas" and abs(dx) < w - 1 and i % 2:
                continue                       # durchscheinend
            c.set(cx + dx, y, kante if rand else mix(tint, P.INK, 0.45))
    c.set(cx, cy - 12, mix(tint, P.BONE, 0.8))
    c.glow(cx, cy - 4, 11, (tint[0], tint[1], tint[2], int(40 + 45 * p)))
    return c


def fx_siegel(kerben: int, tint, frame: int) -> Canvas:
    """
    Das Siegel eines Splitters: eine Scheibe mit so vielen Kerben am Rand,
    wie sie belegt. Innen ein Zeichen, das mit dem Takt aufleuchtet.
    """
    c = Canvas(28, 28)
    cx = cy = 14
    p = 0.5 + 0.5 * math.sin(frame / 6 * math.tau)
    ink = mix(tint, P.INK, 0.62)

    kerbwinkel = [(-math.pi / 2 + i * math.tau / max(1, kerben)) % math.tau
                  for i in range(kerben)]
    for i in range(240):
        a = i / 240 * math.tau
        gekerbt = any(min(abs(a - k), math.tau - abs(a - k)) < 0.22 for k in kerbwinkel)
        r = 8.2 - (2.6 if gekerbt else 0)
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        c.set(int(round(x)), int(round(y)), tint if not gekerbt else mix(tint, P.INK, 0.4))

    # Fuellung
    for y in range(28):
        for x in range(28):
            d = math.hypot(x - cx, y - cy)
            if d < 7.0:
                c.blend(x, y, (ink[0], ink[1], ink[2], 205))

    # Das Zeichen: ein liegender Ton, der im Takt heller wird.
    c.rect(cx - 3, cy - 1, 7, 1, mix(tint, P.BONE, 0.3 + 0.5 * p))
    c.set(cx - 4, cy, tint)
    c.set(cx + 4, cy - 2, tint)
    c.glow(cx, cy, 11, (tint[0], tint[1], tint[2], int(45 + 35 * p)))
    return c


def fx_sigil(kind: str, frame: int) -> Canvas:
    """Siegel: das schwebende Zeichen eines Fundstuecks vor dem Aufnehmen."""
    tint = SIGIL_TINTS[kind]
    c = Canvas(28, 28)
    p = 0.5 + 0.5 * math.sin(frame / 6 * math.tau)
    cx = cy = 14
    c.ring(cx, cy, 9 + p, 1, (tint[0], tint[1], tint[2], 150))
    c.ring(cx, cy, 12 + p * 2, 1, (tint[0], tint[1], tint[2], int(70 * (1 - p * 0.5))))
    if kind == "fluegelschlag":
        for side in (-1, 1):
            for i in range(6):
                u = i / 5
                c.set(int(cx + side * (1 + u * 6)), int(cy - math.sin(u * math.pi) * 5), tint)
    elif kind == "herzschlag":
        # EKG-Linie
        pts = [(-8, 0), (-4, 0), (-3, -4), (-1, 5), (1, -6), (3, 2), (5, 0), (8, 0)]
        for i in range(len(pts) - 1):
            c.line(cx + pts[i][0], cy + pts[i][1], cx + pts[i + 1][0], cy + pts[i + 1][1], tint)
    elif kind == "klangschritt":
        for i in range(3):
            c.rect(cx - 6 + i * 5, cy - 5 + i * 3, 3, 7, tint)
    elif kind == "leier":
        # Rahmen mit Saiten
        c.rect(cx - 4, cy - 6, 1, 11, tint)
        c.rect(cx + 4, cy - 6, 1, 11, tint)
        c.rect(cx - 4, cy + 5, 9, 1, tint)
        for i in range(3):
            c.rect(cx - 2 + i * 2, cy - 4, 1, 9, mix(tint, P.WARM, 0.4))
    elif kind == "trommel":
        c.ellipse(cx, cy, 6, 4.6, mix(tint, P.INK, 0.45))
        c.ring(cx, cy, 5.4, 1.2, tint)
        c.rect(cx - 5, cy - 1, 11, 1, mix(tint, P.WARM, 0.5))
    elif kind == "floete":
        c.rect(cx - 7, cy - 1, 15, 2, mix(tint, P.STONE_HI, 0.3))
        for i in range(4):
            c.set(cx - 4 + i * 3, cy - 1, P.INK)
        c.set(cx + 7, cy - 1, mix(tint, P.WARM, 0.5))
    elif kind == "metronom":
        # Ein Keil mit Arm.
        c.line(cx - 3, cy + 5, cx, cy - 5, tint)
        c.line(cx + 3, cy + 5, cx, cy - 5, tint)
        c.rect(cx - 4, cy + 5, 9, 1, tint)
        a = -math.pi / 2 + math.sin(frame) * 0.5
        c.line(cx, cy + 4, cx + math.cos(a) * 8, cy + 4 + math.sin(a) * 8,
               mix(tint, P.BONE, 0.4))
    elif kind == "glocke":
        for i in range(7):
            w = 1.6 + i * 0.7
            c.rect(int(cx - w), cy - 5 + i, int(w * 2) + 1, 1,
                   tint if i in (0, 6) else mix(tint, P.INK, 0.45))
        c.rect(cx - 6, cy + 2, 13, 1, tint)
        c.set(cx, cy + 4, mix(tint, P.BONE, 0.6))
    elif kind == "orgelpfeife":
        c.rect(cx - 2, cy - 8, 5, 15, mix(tint, P.INK, 0.4))
        c.rect(cx - 2, cy - 8, 5, 1, tint)
        c.rect(cx - 2, cy + 6, 5, 1, tint)
        c.rect(cx - 2, cy, 5, 1, mix(tint, P.BONE, 0.5))
    elif kind == "basston":
        for i in range(3):
            c.ring(cx, cy, 3 + i * 2.4, 1, (tint[0], tint[1], tint[2], int(200 - i * 45)))
    c.glow(cx, cy, 13, (tint[0], tint[1], tint[2], int(50 + 40 * p)))
    return c


# --------------------------------------------------------------------- Bau

def build() -> None:
    tiles = Atlas("tiles", padding=1, max_width=512)
    # Alle sechzehn Nachbarschaften. Vorher fehlten vier davon, und die
    # betroffenen Kacheln fielen auf "Mitte" zurueck - genau dort blieb die
    # Felswand dann schnurgerade, weil sie gar keine Kante bekam.
    EDGE_SETS = ['', 't', 'l', 'r', 'b', 'tl', 'tr', 'tb', 'lr', 'lb', 'rb', 'tlr', 'tlb', 'trb', 'lrb', 'tlrb']
    for region in REGIONS:
        for edges in EDGE_SETS:
            for v in range(6):
                tiles.add(f"{region}_solid_{edges or 'mid'}_{v}",
                          tile_solid(region, v, edges),
                          pivot=(0, TILE_OVERHANG / TILE_H))
        for v in range(4):
            for name, (a, b) in SLOPE_KINDS.items():
                tiles.add(f"{region}_slope_{name}_{v}", tile_slope(region, v, a, b),
                          pivot=(0, TILE_OVERHANG / (TS + TILE_OVERHANG)))
            # Deckenschraegen: dieselbe Schraege, senkrecht gespiegelt. Was
            # am Boden unten Fels ist, ist an der Decke oben Fels - und
            # damit hoert die Decke auf, eine Treppe zu sein.
            # Deckenschraegen. `fall` sagt, wie tief der Fels herunterreicht:
            # faellt die Decke nach rechts, waechst er nach rechts.
            for aus, (fa, fb) in (("downhigh", (0.0, 0.5)),
                                  ("downlow", (0.5, 1.0)),
                                  ("uplow", (1.0, 0.5)),
                                  ("uphigh", (0.5, 0.0))):
                tiles.add(f"{region}_ceil_{aus}_{v}",
                          deckenschraege(region, v, fa, fb), pivot=(0, 0))
        for cap in ("mid", "l", "r", "lr"):
            for v in range(4):
                tiles.add(f"{region}_platform_{cap}_{v}",
                          tile_platform(region, v, "" if cap == "mid" else cap),
                          pivot=(0, TILE_OVERHANG
                                 / (12 + TILE_OVERHANG + TILE_UNDERHANG)))
        dorn = tile_spike(region)
        tiles.add(f"{region}_spike", dorn, pivot=(0, 0))
        # Decke, linke Wand, rechte Wand. Die Kachel wird gedreht, nicht neu
        # gezeichnet: es sind dieselben Dornen.
        tiles.add(f"{region}_spike_down", gedreht(dorn, 2), pivot=(0, 0))
        tiles.add(f"{region}_spike_right", gedreht(dorn, 1), pivot=(0, 0))
        tiles.add(f"{region}_spike_left", gedreht(dorn, 3), pivot=(0, 0))
    for region in REGIONS:
        for v in range(6):
            # Requisiten wiegen sich: eine starre Kante faellt sofort auf,
            # sobald alles andere im Bild atmet.
            tiles.add_sequence(f"edge_{region}_{v}",
                               [edge_prop(region, v, f, 6) for f in range(6)],
                               pivot=(0.5, 1.0), fps=4)
            # Der Unterbau einer Plattform: dahinter und darunter.
            if v < 3:
                tiles.add(f"sockel_{region}_{v}", sockel(region, v), pivot=(0.5, 0.0))
            # Dasselbe fuer die Decke, aufgehaengt an der Oberkante.
            tiles.add_sequence(f"hang_{region}_{v}",
                               [hang_prop(region, v, f, 6) for f in range(6)],
                               pivot=(0.5, 0.0), fps=4)
    for f in range(4):
        tiles.add(f"dissowall_{f}", tile_dissowall(f), pivot=(0, 0), fps=6)
    png, js = tiles.write(OUT)
    print(f"tiles      -> {png.name} ({len(tiles.frames)} Frames)")

    props = Atlas("props", padding=1, max_width=512)
    for region, tint in (("hain", P.GLOW), ("kathedrale", P.BLOOM), ("grotten", hexc("#8fd7ff")), ("dissonanz", P.ROT)):
        for size in range(3):
            props.add_sequence(f"crystal_{region}_{size}",
                               [tile_crystal(size, f, tint) for f in range(4)], pivot=(0.5, 1.0), fps=4)
        props.add_sequence(f"reed_{region}", [tile_reed(f, tint) for f in range(4)], pivot=(0.5, 1.0), fps=5)
    props.add_sequence("bench", [tile_bench(f) for f in range(6)], pivot=(0.5, 1.0), fps=5)
    for kind in SIGIL_TINTS:
        props.add_sequence(f"sigil_{kind}", [fx_sigil(kind, f) for f in range(6)],
                           pivot=(0.5, 0.5), fps=8)
    for kid, tint in KLINGEN_SIGILS.items():
        props.add_sequence(f"sigil_klinge_{kid}",
                           [fx_klingen_sigil(kid, tint, f) for f in range(6)],
                           pivot=(0.5, 0.5), fps=8)
    for sid, (kerben, tint) in SIEGEL_SIGILS.items():
        props.add_sequence(f"sigil_{sid}",
                           [fx_siegel(kerben, tint, f) for f in range(6)],
                           pivot=(0.5, 0.5), fps=8)
    for eid, (openings, tint) in EQUIPMENT_SIGILS.items():
        props.add_sequence(f"sigil_{eid}",
                           [fx_equipment_sigil(openings, tint, f) for f in range(6)],
                           pivot=(0.5, 0.5), fps=8)
    png, js = props.write(OUT)
    print(f"props      -> {png.name} ({len(props.frames)} Frames)")

    fx = Atlas("fx", padding=1, max_width=512)
    # Klangringe nach Groesse - sie gehoeren keiner Waffe.
    for name, tint, r in (("ring_mittel", P.GLOW, 22), ("ring_gross", P.GOLD, 30),
                          ("ring_klein", P.BLOOM, 16)):
        fx.add_sequence(name, [fx_ring(f, 5, tint, r) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    # Die Schlagboegen der Klingen.
    for art in ("schlicht", "gezackt", "glas"):
        fx.add_sequence(f"klinge_{art}", [fx_klinge(f, 5, art) for f in range(5)],
                        pivot=(0.5, 0.5), fps=26)
    for i, (name, tint) in enumerate((("note_leier", P.GLOW), ("note_trommel", P.GOLD),
                                      ("note_floete", P.BLOOM))):
        fx.add(name, fx_note(i, tint), pivot=(0.5, 0.5))
    fx.add("note_stimmgabel", fx_note(1, P.TRIM), pivot=(0.5, 0.5))
    fx.add("note_dissonanz", fx_note(2, P.ROT), pivot=(0.5, 0.5))
    fx.add_sequence("feather", [fx_feather(f) for f in range(4)], pivot=(0.5, 0.5), fps=18)
    fx.add_sequence("heartbeat", [fx_heart(f) for f in range(4)], pivot=(0.5, 0.5), fps=18)
    fx.add_sequence("burst_glow", [fx_burst(f, P.GLOW) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    fx.add_sequence("burst_rot", [fx_burst(f, P.ROT) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    fx.add_sequence("dust", [fx_dust(f) for f in range(5)], pivot=(0.5, 1.0), fps=18)
    fx.add_sequence("mote", [fx_mote(f, P.GLOW) for f in range(4)], pivot=(0.5, 0.5), fps=6)
    # Ihre Flamme an der Stimmgabel. Der Ursprung sitzt unten Mitte: sie
    # steht auf der Gabel, sie schwebt nicht daneben.
    fx.add_sequence("flamme", [fx_flamme(f, 8) for f in range(8)],
                    pivot=(0.5, 1.0), fps=12)
    png, js = fx.write(OUT)
    print(f"fx         -> {png.name} ({len(fx.frames)} Frames)")

    # Die Hintergruende baut gen_backdrops - sie sind von Hand komponiert
    # und haben mit dem Kachelsatz nichts zu tun.


if __name__ == "__main__":
    build()
