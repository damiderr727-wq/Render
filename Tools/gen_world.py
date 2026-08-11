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

from pixelkit import Atlas, Canvas, Palette as P, Rng, hash01, hexc, mix, shade

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Atlas"
TS = 16  # Kachelgroesse

REGIONS = ["hain", "kathedrale", "grotten", "dissonanz"]


# ----------------------------------------------------------------- Kacheln

TILE_OVERHANG = 8   # Platz ueber der Kachel fuer Bewuchs, der ueberhaengt


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
    c = Canvas(TS, TS + TILE_OVERHANG)
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

    if region == "kathedrale":
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
        c.rect(0, top + TS - 1, TS, 1, shade(body, -0.45))
        # Ausgefranste Unterkante mit einzelnen Zapfen.
        for x in range(TS):
            if hash01(x * 3, variant + 40) > 0.62:
                c.set(x, top + TS - 2, shade(body, -0.32))
                if hash01(x, 51) > 0.7:
                    c.set(x, top + TS - 3, shade(body, -0.22))
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

    Ein duennes Brett, das zwei Kacheln ueber dem Boden schwebt, sieht aus
    wie eine Spielmechanik - nicht wie Landschaft. Deshalb hat sie hier
    Substanz und einen Grund, da zu sein: im Hain ist sie eine gestuerzte
    Wurzel mit Rinde und herabhaengendem Wurzelwerk, in der Kathedrale ein
    gebrochener Steinbalken, in den Grotten ein Kristallsims, in der
    Dissonanz eine gesprungene Platte.

    `cap` sagt, ob links ('l') oder rechts ('r') das Ende liegt.
    """
    body, edge, accent = P.REGIONS[region][:3]
    depth = 13
    c = Canvas(TS, depth + 8 + TILE_OVERHANG)
    top = TILE_OVERHANG
    crest = _crest_profile(variant)

    for x in range(TS):
        thin = 0
        if "l" in cap:
            thin = max(thin, max(0, 5 - x))
        if "r" in cap:
            thin = max(thin, max(0, x - (TS - 6)))
        if thin >= 5:
            continue
        k = crest[x]
        h = depth - thin * 2
        for i in range(h + k):
            t = i / (h + k)
            c.set(x, top - k + i, mix(shade(body, 0.14), shade(body, -0.42), t ** 0.55))
        c.set(x, top - k, mix(edge, accent, 0.20))
        c.set(x, top - k + 1, mix(edge, body, 0.28))

    if region == "hain":
        # Rinde laengs, dann Wurzeln, die unter der Kante haengen.
        for x in range(TS):
            if hash01(x, variant + 61) > 0.55:
                y0 = top + 3
                for i in range(hash01(x, variant) > 0.5 and 5 or 3):
                    c.set(x, y0 + i, shade(body, -0.24))
        for x in range(TS):
            if hash01(x * 3, variant + 71) > 0.72:
                if ("l" in cap and x < 5) or ("r" in cap and x > TS - 6):
                    continue
                rl = 3 + int(hash01(x, variant + 5) * 7)
                rx = x
                for i in range(rl):
                    c.set(rx, top + depth - 3 + i, shade(body, -0.36))
                    if hash01(rx, i) > 0.6:
                        rx += 1 if hash01(rx, i + 3) > 0.5 else -1
        for x in range(TS):
            if hash01(x * 9 + variant * 23, 13) < 0.26:
                if ("l" in cap and x < 4) or ("r" in cap and x > TS - 5):
                    continue
                hh = 2 + int(hash01(x, variant + 5) * 4)
                lean = -1 if hash01(x, 11) > 0.5 else 1
                for i in range(hh):
                    t = i / max(1, hh)
                    c.set(x + int(lean * i * 0.3), top - crest[x] - 1 - i,
                          mix(mix(edge, body, 0.55), edge, t * 0.7))
    elif region == "kathedrale":
        # Gebrochener Balken: Fugen laengs, ausgebrochene Unterkante.
        for row in range(2):
            yy = top + 4 + row * 5
            c.rect(0, yy, TS, 1, shade(body, -0.30))
            c.rect(0, yy + 1, TS, 1, shade(body, 0.06))
        for x in range(TS):
            if hash01(x * 5, variant + 31) > 0.6:
                c.set(x, top + depth - 2, None)
                c.set(x, top + depth - 3, shade(body, -0.4))
    elif region == "grotten":
        for x in range(0, TS, 5):
            if hash01(x, variant) > 0.45:
                c.set(x, top - crest[x] - 1, mix(accent, edge, 0.4))
                c.set(x, top - crest[x] - 2, mix(accent, edge, 0.7))
        # Kristallzacken unter dem Sims.
        for x in range(TS):
            if hash01(x * 7, variant + 41) > 0.78:
                zl = 3 + int(hash01(x, variant) * 5)
                for i in range(zl):
                    w = 2 if i < zl // 2 else 1
                    c.rect(x, top + depth - 2 + i, w, 1,
                           mix(body, accent, 0.25 - i / zl * 0.2))
    else:
        for x in range(TS):
            if hash01(x * 5, variant + 17) > 0.7:
                c.set(x, top + 4 + int(hash01(x, 3) * 5), P.ROT_DIM)
            if hash01(x * 3, variant + 29) > 0.62:
                c.set(x, top + depth - 2, None)

    # Ausgefranste Unterkante, damit die Plattform nicht gesaegt wirkt.
    for x in range(TS):
        if hash01(x * 3, variant + 9) > 0.5:
            c.set(x, top + depth - 1, shade(body, -0.5))
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
    """Stimmgabel - Rast- und Speicherpunkt."""
    c = Canvas(24, 26)
    pulse = 0.5 + 0.5 * math.sin(frame / 4 * math.tau)
    # Sockel
    c.rect(4, 22, 16, 4, P.STONE_LO)
    c.rect(4, 22, 16, 1, P.STONE)
    c.rect(6, 20, 12, 2, shade(P.STONE, -0.15))
    # Gabel
    c.rect(11, 12, 3, 9, mix(P.STONE_HI, P.WARM, 0.25))
    c.rect(7, 2, 3, 12, mix(P.STONE_HI, P.WARM, 0.25))
    c.rect(15, 2, 3, 12, mix(P.STONE_HI, P.WARM, 0.25))
    c.rect(7, 12, 11, 2, mix(P.STONE_HI, P.WARM, 0.15))
    c.rect(9, 12, 1, 9, shade(P.STONE_HI, -0.3))
    # Klangkrone
    for x in (8, 16):
        c.set(x, 1, mix(P.TRIM, (255, 255, 255, 255), pulse * 0.6))
    c.ring(12.5, 6, 6 + pulse * 3, 1, (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(70 * (1 - pulse))))
    c.outline(hexc("#05060c", 200))
    c.glow(12, 10, 14, (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(28 + 34 * pulse)))
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
}


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
                          pivot=(0, TILE_OVERHANG / (TS + TILE_OVERHANG)))
        for cap in ("mid", "l", "r", "lr"):
            for v in range(4):
                tiles.add(f"{region}_platform_{cap}_{v}",
                          tile_platform(region, v, "" if cap == "mid" else cap),
                          pivot=(0, TILE_OVERHANG / (13 + 8 + TILE_OVERHANG)))
        tiles.add(f"{region}_spike", tile_spike(region), pivot=(0, 0))
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
    props.add_sequence("bench", [tile_bench(f) for f in range(4)], pivot=(0.5, 1.0), fps=4)
    for kind in SIGIL_TINTS:
        props.add_sequence(f"sigil_{kind}", [fx_sigil(kind, f) for f in range(6)],
                           pivot=(0.5, 0.5), fps=8)
    png, js = props.write(OUT)
    print(f"props      -> {png.name} ({len(props.frames)} Frames)")

    fx = Atlas("fx", padding=1, max_width=512)
    for name, tint, r in (("ring_leier", P.GLOW, 22), ("ring_trommel", P.GOLD, 30), ("ring_floete", P.BLOOM, 16)):
        fx.add_sequence(name, [fx_ring(f, 5, tint, r) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    for i, (name, tint) in enumerate((("note_leier", P.GLOW), ("note_trommel", P.GOLD), ("note_floete", P.BLOOM))):
        fx.add(name, fx_note(i, tint), pivot=(0.5, 0.5))
    fx.add("note_dissonanz", fx_note(2, P.ROT), pivot=(0.5, 0.5))
    fx.add_sequence("feather", [fx_feather(f) for f in range(4)], pivot=(0.5, 0.5), fps=18)
    fx.add_sequence("heartbeat", [fx_heart(f) for f in range(4)], pivot=(0.5, 0.5), fps=18)
    fx.add_sequence("burst_glow", [fx_burst(f, P.GLOW) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    fx.add_sequence("burst_rot", [fx_burst(f, P.ROT) for f in range(5)], pivot=(0.5, 0.5), fps=24)
    fx.add_sequence("dust", [fx_dust(f) for f in range(5)], pivot=(0.5, 1.0), fps=18)
    fx.add_sequence("mote", [fx_mote(f, P.GLOW) for f in range(4)], pivot=(0.5, 0.5), fps=6)
    png, js = fx.write(OUT)
    print(f"fx         -> {png.name} ({len(fx.frames)} Frames)")

    # Die Hintergruende baut gen_backdrops - sie sind von Hand komponiert
    # und haben mit dem Kachelsatz nichts zu tun.


if __name__ == "__main__":
    build()
