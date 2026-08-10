"""
Erzeugt Tilesets, Parallax-Hintergruende und Effekt-Sprites.

Die Welt ist ein Oekosystem aus Klang: Boden traegt Resonanzadern,
Kristalle leuchten im Takt, und die Dissonanz frisst sich als rote
Faeule durch das Gestein.
"""

from __future__ import annotations

import math
from pathlib import Path

from pixelkit import Atlas, Canvas, Palette as P, Rng, hexc, mix, shade

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Atlas"
TS = 16  # Kachelgroesse

REGIONS = ["hain", "kathedrale", "grotten", "dissonanz"]


# ----------------------------------------------------------------- Kacheln

def tile_solid(region: str, variant: int, edges: str) -> Canvas:
    """
    Ein Bodenstueck. `edges` enthaelt die freiliegenden Seiten:
    't' oben, 'b' unten, 'l' links, 'r' rechts.
    """
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(TS, TS)
    rng = Rng(1000 + variant * 7919 + (sum(map(ord, region)) * 131) % 4096)

    # Grundmasse mit koerniger Struktur. Die Koernung bleibt flach - bei
    # 16 Pixeln faellt jeder starke Kontrast als Muster auf, sobald sich
    # dieselbe Kachel wiederholt.
    for y in range(TS):
        for x in range(TS):
            n = rng.next()
            depth = y / TS
            col = mix(body, shade(body, -0.30), depth * 0.55 + n * 0.10)
            c.set(x, y, col)

    # Adern aus erstarrtem Klang - nur angedeutet.
    if rng.chance(0.5):
        vx = rng.int(2, TS - 3)
        vy = rng.int(3, TS - 5)
        for i in range(rng.int(2, 4)):
            c.set(vx, vy + i, mix(body, accent, 0.06))
            if rng.chance(0.4):
                vx += 1 if rng.chance(0.5) else -1

    # Kanten
    if "t" in edges:
        c.rect(0, 0, TS, 1, mix(edge, accent, 0.35))
        c.rect(0, 1, TS, 1, edge)
        c.rect(0, 2, TS, 1, mix(edge, body, 0.55))
        for x in range(TS):
            if rng.chance(0.28):
                c.set(x, 3, mix(edge, body, 0.7))
    if "b" in edges:
        c.rect(0, TS - 1, TS, 1, shade(body, -0.45))
        for x in range(TS):
            if rng.chance(0.3):
                c.set(x, TS - 2, shade(body, -0.3))
    if "l" in edges:
        c.rect(0, 0, 1, TS, mix(edge, body, 0.45))
        c.rect(1, 0, 1, TS, mix(edge, body, 0.75))
    if "r" in edges:
        c.rect(TS - 1, 0, 1, TS, shade(body, -0.35))
        c.rect(TS - 2, 0, 1, TS, shade(body, -0.18))

    # Regionsspezifischer Bewuchs auf der Oberkante
    if "t" in edges:
        if region == "hain":
            for x in range(TS):
                if rng.chance(0.35):
                    h = rng.int(1, 3)
                    for i in range(h):
                        c.set(x, -1 + 0 - i, None)
                    c.set(x, 0, mix(accent, edge, 0.35))
        elif region == "grotten":
            for _ in range(2):
                x = rng.int(1, TS - 2)
                c.set(x, 0, accent)
                c.set(x, 1, mix(accent, body, 0.5))
        elif region == "dissonanz":
            for x in range(TS):
                if rng.chance(0.22):
                    c.set(x, 1, P.ROT)
                    c.set(x, 2, mix(P.ROT_DIM, body, 0.4))
    return c


def tile_platform(region: str) -> Canvas:
    """Durchsteigbare Plattform - schwebende Notenlinie."""
    body, edge, accent = P.REGIONS[region][:3]
    c = Canvas(TS, 6)
    c.rect(0, 0, TS, 1, mix(edge, accent, 0.5))
    c.rect(0, 1, TS, 2, edge)
    c.rect(0, 3, TS, 1, mix(body, edge, 0.5))
    c.rect(0, 4, TS, 1, shade(body, -0.3))
    for x in range(0, TS, 4):
        c.set(x, 4, mix(accent, body, 0.5))
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

BG_W, BG_H = 512, 288   # so gross wie das Sichtfeld: ein Bild fuellt den Blick


def _trunk(c: Canvas, x: int, width: int, col, taper: float = 0.35,
           rng: Rng | None = None) -> None:
    """Ein Stamm oder Pfeiler ueber die volle Bildhoehe."""
    rng = rng or Rng(7)
    lean = rng.range(-0.10, 0.10)
    for y in range(BG_H):
        t = y / BG_H
        w = int(width * (1 - taper * (1 - t)))
        cx = x + int(lean * (BG_H - y))
        c.rect(cx - w // 2, y, max(2, w), 1, col)
    # Rindenkanten: eine Spur heller an der Lichtseite.
    hi = shade(col, 0.10)
    for y in range(0, BG_H, 3):
        t = y / BG_H
        w = int(width * (1 - taper * (1 - t)))
        cx = x + int(lean * (BG_H - y))
        c.rect(cx - w // 2, y, 1, 2, hi)


def _hanging(c: Canvas, x: int, y: int, length: int, size: int, col, accent) -> None:
    """
    Etwas, das an einem Faden haengt: Zapfen, Rauchfass, Kristall.

    Solche Objekte geben dem Bild Massstab - erst an ihnen sieht man, wie
    gross die Halle ist. In den Vorlagen sind sie das, was den Raum tief
    macht.
    """
    for i in range(length):
        c.set(x, y + i, mix(col, accent, 0.15 if i % 4 else 0.35))
    cy = y + length + size
    c.ellipse(x, cy, size * 0.55, size, col)
    c.ellipse(x - size * 0.18, cy - size * 0.2, size * 0.35, size * 0.7, shade(col, 0.12))
    for i in range(int(size)):
        c.set(int(x + size * 0.3), int(cy - size + i * 2), shade(col, -0.25))


def _canopy(c: Canvas, x: int, y: int, span: int, col, rng: Rng) -> None:
    """Ein Zweig mit Nadeln, der von oben ins Bild ragt."""
    for i in range(span):
        t = i / span
        bx = x + i
        by = y + int(t * t * 22)
        c.rect(bx, by, 1, 2, col)
        needles = int(10 * (1 - t) + 3)
        for n in range(needles):
            u = n / max(1, needles)
            c.set(bx, by + 2 + int(u * 9), mix(col, shade(col, -0.2), u))
            c.set(bx, by - 2 - int(u * 7), mix(col, shade(col, -0.2), u))


def backdrop(region: str, layer: int) -> Canvas:
    """
    Eine Parallax-Schicht.

    Die Helligkeiten sind fest gestaffelt: Schicht 0 ist der helle Himmel,
    Schicht 1 die ferne Silhouette, Schicht 2 die nahe. Dadurch entsteht
    Tiefe durch Wert, nicht durch Nebel - und die Figur hebt sich als
    heller Fleck gegen dunkles Vorn ab.
    """
    body, edge, accent, sky, far = P.REGIONS[region]
    c = Canvas(BG_W, BG_H)
    rng = Rng(100 + layer * 7 + REGIONS.index(region) * 91)

    if layer == 0:
        # Himmel: der hellste Wert im ganzen Bild.
        for y in range(BG_H):
            t = y / BG_H
            c.rect(0, y, BG_W, 1, mix(sky, far, t ** 0.8))
        # Staubkoerner im Licht.
        for _ in range(260):
            x, y = rng.int(0, BG_W - 1), rng.int(0, BG_H - 1)
            c.blend(x, y, (255, 255, 255, rng.int(10, 40)))
        # Ganz ferne Andeutungen, kaum abgesetzt.
        veil = mix(far, sky, 0.35)
        for i in range(7):
            _trunk(c, rng.int(0, BG_W), rng.int(14, 34), veil, 0.5, rng)
        return c

    # Silhouetten: Schicht 1 mittel, Schicht 2 dunkel.
    col = mix(far, P.FOREGROUND, 0.35 if layer == 1 else 0.68)
    count = 5 if layer == 1 else 3

    if region in ("hain", "grotten"):
        for i in range(count):
            x = int((i + 0.5) * BG_W / count + rng.range(-40, 40))
            _trunk(c, x, rng.int(38, 84) if layer == 2 else rng.int(22, 52), col, 0.30, rng)
        if region == "hain":
            # Zweige von oben, Zapfen an Faeden - der Massstab des Waldes.
            for i in range(3 if layer == 1 else 2):
                _canopy(c, rng.int(-30, BG_W - 60), rng.int(-6, 30),
                        rng.int(70, 150), shade(col, -0.12), rng)
            for _ in range(2 if layer == 1 else 3):
                _hanging(c, rng.int(30, BG_W - 30), 0,
                         rng.int(40, 130), rng.int(7, 14), shade(col, -0.15), accent)
        else:
            # Grotten: Kristalle haengen von der Decke.
            for _ in range(3 if layer == 1 else 4):
                x = rng.int(20, BG_W - 20)
                h = rng.int(50, 130)
                w = rng.int(10, 26)
                for y in range(h):
                    t = y / h
                    c.rect(int(x - w * (1 - t) / 2), y, max(1, int(w * (1 - t))), 1, col)
                c.glow(x, h, 18, (accent[0], accent[1], accent[2], 26 if layer == 1 else 16))

    elif region == "kathedrale":
        # Pfeiler und Bogenfenster - das Licht kommt von hinten durch.
        for i in range(count):
            x = int((i + 0.5) * BG_W / count)
            width = rng.int(46, 78) if layer == 2 else rng.int(26, 46)
            c.rect(x - width // 2, 0, width, BG_H, col)
            # Fenster: heller Ausschnitt im Pfeilerzwischenraum.
            if layer == 1 and i < count - 1:
                wx = int((i + 1) * BG_W / count)
                ww, wh = 26, 96
                top = 46
                for y in range(wh):
                    t = y / wh
                    glass = mix(sky, accent, 0.25 + 0.25 * (1 - t))
                    c.rect(wx - ww // 2, top + y, ww, 1, glass)
                for a in range(180):
                    rad = math.radians(a)
                    c.set(int(wx + math.cos(rad) * ww / 2),
                          int(top - math.sin(rad) * ww / 2), glass)
                c.glow(wx, top + wh // 2, 46, (accent[0], accent[1], accent[2], 22))
        # Haengende Rauchfaesser.
        for _ in range(2 if layer == 1 else 3):
            _hanging(c, rng.int(40, BG_W - 40), 0,
                     rng.int(50, 140), rng.int(6, 12), shade(col, -0.2), accent)

    else:
        # Dissonanz: gekippte, gebrochene Formen. Nichts steht mehr gerade.
        for i in range(count + 3):
            x = rng.int(0, BG_W)
            h = rng.int(int(BG_H * 0.45), BG_H)
            skew = rng.range(-0.45, 0.45)
            w0 = rng.int(14, 46)
            for y in range(h):
                t = y / h
                w = int(w0 * (0.35 + t * 0.65))
                c.rect(int(x + skew * (h - y) - w // 2), BG_H - y, max(2, w), 1, col)
        for _ in range(3):
            _hanging(c, rng.int(30, BG_W - 30), 0,
                     rng.int(30, 110), rng.int(8, 15), shade(col, -0.15), accent)

    return c


def foreground(region: str) -> Canvas:
    """
    Die vorderste Schicht: fast schwarze Massen am unteren Bildrand.

    Sie steht vor allem anderen und laeuft schneller als die Kamera. Ohne
    sie klebt das Bild flach am Bildschirm - mit ihr schaut man in eine
    Tiefe hinein.
    """
    body, edge, accent, sky, far = P.REGIONS[region]
    c = Canvas(BG_W, BG_H)
    rng = Rng(555 + REGIONS.index(region) * 37)
    col = P.FOREGROUND

    # Unterer Saum: eine geschlossene, unruhige Masse. Einzelne duenne
    # Halme lesen sich aus der Entfernung als Antennen - es braucht Volumen.
    base = BG_H - 10
    for i in range(60):
        x = int(i * BG_W / 52 + rng.range(-18, 18))
        r = rng.range(22, 62)
        c.ellipse(x, base + rng.range(0, 26), r, r * rng.range(0.45, 0.85), col)
    c.rect(0, base + 16, BG_W, BG_H - base - 16, col)

    # Wenige, dafuer dicke Formen, die aus der Masse aufragen.
    for _ in range(7):
        x = rng.int(0, BG_W)
        h = rng.int(26, 78)
        lean = rng.range(-0.25, 0.25)
        for y in range(h):
            t = y / h
            w = max(2, int(7 * (1 - t * 0.75)))
            c.rect(int(x + lean * y) - w // 2, base - y, w, 1, col)
        if region == "hain":
            # Ein paar Blattkronen auf den Halmen.
            top = base - h
            c.ellipse(int(x + lean * h), top, 7, 9, col)
        elif region == "grotten":
            c.ellipse(int(x + lean * h), top if False else base - h, 5, 12, col)

    # Oben hereinragende Aeste, damit der Blick gerahmt ist.
    for _ in range(3):
        x = rng.int(-40, BG_W)
        span = rng.int(80, 200)
        for i in range(span):
            t = i / span
            c.rect(x + i, int(t * t * 30), 1, int(6 * (1 - t)) + 2, col)
    return c


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
    EDGE_SETS = ["", "t", "tl", "tr", "tlr", "l", "r", "lr", "b", "tb", "blr", "tblr"]
    for region in REGIONS:
        for edges in EDGE_SETS:
            for v in range(4):
                tiles.add(f"{region}_solid_{edges or 'mid'}_{v}",
                          tile_solid(region, v, edges), pivot=(0, 0))
        tiles.add(f"{region}_platform", tile_platform(region), pivot=(0, 0))
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

    bg = Atlas("backdrops", padding=2, max_width=512)
    for region in REGIONS:
        for layer in range(3):
            bg.add(f"{region}_bg{layer}", backdrop(region, layer), pivot=(0, 0),
                   parallax=[0.10, 0.28, 0.52][layer])
        bg.add(f"{region}_fg", foreground(region), pivot=(0, 0), parallax=1.30)
    png, js = bg.write(OUT)
    print(f"backdrops  -> {png.name} ({len(bg.frames)} Frames)")


if __name__ == "__main__":
    build()
