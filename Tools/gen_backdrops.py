"""
Die Hintergruende der vier Regionen - von Hand komponiert.

Zufallsstreuung ergibt Rauschen, kein Bild. Jede Schicht hier ist gesetzt:
was rahmt den Blick, was traegt den Massstab, wo bleibt die Mitte frei fuer
die Figur. Der Zufall darf nur noch die Rinde koernen und die Kanten
ausfransen.

Zwei Regeln gelten ueberall:

  Licht kommt von rechts oben. Jeder Stamm, jede Masse bekommt dort ihre
  hellere Kante - eine einzige Richtung macht aus Formen einen Raum.

  Die Helligkeiten sind gestaffelt: Himmel am hellsten, dann ferne, dann
  nahe Silhouetten. Tiefe entsteht durch Wert, nicht durch Nebel.
"""

from __future__ import annotations

import math
from pathlib import Path

from pixelkit import Atlas, Canvas, Palette as P, Rng, bezier, hash01, hexc, mix, shade

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Atlas"

W, H = 512, 288          # so gross wie das Sichtfeld
LIGHT = 1                # Licht von rechts

REGIONS = ["hain", "kathedrale", "grotten", "dissonanz"]


# ---------------------------------------------------------------- Bausteine

def trunk(c: Canvas, x: float, top: float, bottom: float, width: float,
          col, rng: Rng | None = None, lean: float = 0.0,
          flare: float = 2.2, bark: bool = True) -> None:
    """
    Ein Stamm mit Wurzelanlauf.

    Nach unten wird er breiter - das ist der Unterschied zwischen einem Baum
    und einem Balken. Die Lichtseite bekommt eine schmale helle Kante.
    """
    rng = rng or Rng(3)
    for y in range(int(top), int(bottom)):
        t = (y - top) / max(1.0, bottom - top)
        # Unten Wurzelanlauf, oben leichte Verjuengung.
        w = width * (0.72 + 0.28 * t) * (1 + (flare - 1) * max(0.0, t - 0.82) / 0.18)
        cx = x + lean * (bottom - y)
        x0 = int(cx - w / 2)
        c.rect(x0, y, max(2, int(w)), 1, col)
        if bark:
            # Rinde: senkrechte Streifen, die mitwandern.
            for k in range(int(w / 7)):
                sx = x0 + 2 + k * 7 + int(hash01(k, y // 9) * 3)
                c.set(sx, y, shade(col, -0.12))
            # Lichtkante rechts.
            c.rect(int(cx + w / 2) - 2, y, 2, 1, shade(col, 0.10))
            c.rect(x0, y, 1, 1, shade(col, -0.16))


def frond(c: Canvas, pts, half_width, fill, dark=None, light=None,
          serrate: float = 3.0, back: float = 0.0, direction: int = 1) -> None:
    """
    Fuellt eine Masse entlang einer Kurve - senkrecht zu ihr.

    Das war der eigentliche Fehler in zwei Anlaeufen davor: gefuellt wurde
    entlang der Kurve statt quer dazu, und dann bleibt von einem Zweig nur
    ein Strich uebrig. Mit der Normalen an jedem Punkt entsteht eine
    geschlossene Flaeche; die Zacken kommen erst hinterher an die Kante.

    `half_width` ist eine Funktion ueber 0..1, `back` neigt die Nadeln
    entgegen der Wuchsrichtung.
    """
    dark = dark or shade(fill, -0.16)
    light = light or shade(fill, 0.14)
    n = max(1, len(pts) - 1)

    for i in range(len(pts)):
        px, py = pts[i]
        qx, qy = pts[min(i + 1, n)]
        tx, ty = qx - px, qy - py
        length = math.hypot(tx, ty) or 1.0
        # Normale zur Tangente.
        nx, ny = -ty / length, tx / length
        t = i / n
        hw = half_width(t)
        if hw < 0.6:
            continue
        for side in (-1, 1):
            extent = hw * (1.0 if side > 0 else 0.82)
            for k in range(int(extent) + 1):
                ox = px + nx * side * k - tx / length * back * k
                oy = py + ny * side * k - ty / length * back * k
                shade_amt = -0.04 - (k / max(1.0, extent)) * 0.18
                c.set(int(ox), int(oy), shade(dark if side > 0 else fill, shade_amt))
        # Lichtkante auf der Oberseite.
        c.set(int(px + nx * -1 * hw * 0.75), int(py + ny * -1 * hw * 0.75), light)

    # Kante ausfransen.
    for i in range(0, len(pts), 2):
        px, py = pts[i]
        qx, qy = pts[min(i + 1, n)]
        tx, ty = qx - px, qy - py
        length = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / length, tx / length
        hw = half_width(i / n)
        for side in (-1, 1):
            extent = hw * (1.0 if side > 0 else 0.82)
            notch = hash01(int(px), int(py) + side * 7) * serrate
            for k in range(int(notch)):
                c.set(int(px + nx * side * (extent - k)),
                      int(py + ny * side * (extent - k)), None)


def conifer_bough(c: Canvas, x: float, y: float, span: float, droop: float,
                  col, rng: Rng, direction: int = 1,
                  needle_col=None, sub: int = 2, width: float = 40.0) -> None:
    """Ein Nadelzweig, der von oben ins Bild haengt."""
    needle_col = needle_col or shade(col, -0.06)
    pts = bezier((x, y),
                 (x + direction * span * 0.35, y + droop * 0.10),
                 (x + direction * span * 0.72, y + droop * 0.42),
                 (x + direction * span, y + droop), 72)

    # Tief statt lang: ein Zweig, dessen Nadelmasse nur ein paar Pixel
    # misst, bleibt ein Strich. Die Masse muss im Verhaeltnis zur Spannweite
    # spuerbar sein.
    frond(c, pts, lambda t: width * (1 - t ** 0.9) + 3, needle_col,
          serrate=2.0, back=0.12, direction=direction)
    # Die Mittelrippe zuletzt, damit sie oben liegt.
    c.stroke(pts, 4.0, 1.2, col)

    for _ in range(sub):
        i = rng.int(10, max(11, len(pts) - 22))
        bx, by = pts[i]
        conifer_bough(c, bx, by, span * rng.range(0.30, 0.46),
                      droop * rng.range(0.5, 0.95), shade(col, -0.05), rng,
                      direction, needle_col, sub=0, width=width * 0.58)


def cone_on_chain(c: Canvas, x: float, top: float, length: float, size: float,
                  col, accent) -> None:
    """
    Ein Zapfen an einer Kette.

    Solche Dinge tragen den Massstab: erst an ihnen sieht man, wie hoch der
    Raum ist. Sie haengen in verschiedenen Tiefen und Laengen, nie zwei auf
    derselben Hoehe.
    """
    c.chain(x, top, top + length, shade(col, 0.20), link=5)

    body_h = size * 2.6
    cy = top + length
    # Koerper: oben breit, nach unten spitz - so haengt ein Zapfen.
    for i in range(int(body_h)):
        t = i / body_h
        w = size * (0.35 + 0.65 * math.sin(math.pi * (0.15 + t * 0.72)))
        w *= (1 - t ** 2.6)
        if w < 0.5:
            continue
        col_row = mix(shade(col, 0.06), shade(col, -0.26), t * 0.8)
        c.rect(int(x - w), int(cy + i), max(1, int(w * 2)), 1, col_row)

    # Schuppen: versetzte Reihen kleiner Boegen.
    row = 0
    i = 2
    while i < body_h - 2:
        t = i / body_h
        w = size * (0.35 + 0.65 * math.sin(math.pi * (0.15 + t * 0.72))) * (1 - t ** 2.6)
        if w > 1.5:
            count = max(1, int(w))
            for k in range(count):
                sx = int(x - w + 1 + k * 2.2 + (row % 2) * 1.1)
                c.set(sx, int(cy + i), shade(col, -0.30))
                c.set(sx, int(cy + i - 1), shade(col, 0.10))
        row += 1
        i += 3

    # Aufhaengung und ein Funke Bernstein an der Spitze.
    c.rect(int(x - size * 0.4), int(cy - 1), max(1, int(size * 0.8)), 2, shade(col, 0.18))
    c.set(int(x), int(cy + body_h - 1), mix(accent, col, 0.45))


def light_shaft(c: Canvas, x: float, width: float, tint, strength: int = 26) -> None:
    """Ein schraeger Lichtbalken. Gerastert, damit er nicht cremig wird."""
    for y in range(H):
        t = y / H
        wx = x + y * 0.42
        w = width * (0.5 + t * 0.9)
        a = int(strength * (1 - t) ** 1.4)
        if a <= 0:
            continue
        for i in range(int(w)):
            px = int(wx + i)
            if (px + y) % 3 == 0 or (px * 2 + y) % 7 == 0:
                c.blend(px, y, (tint[0], tint[1], tint[2], a))


def motes(c: Canvas, count: int, rng: Rng, tint, alpha=(12, 46)) -> None:
    for _ in range(count):
        x, y = rng.int(0, W - 1), rng.int(0, H - 1)
        c.blend(x, y, (tint[0], tint[1], tint[2], rng.int(*alpha)))


# ------------------------------------------------------------------- Hain

def hain(layer: int) -> Canvas:
    body, edge, accent, sky, far = P.REGIONS["hain"]
    c = Canvas(W, H)
    rng = Rng(1201 + layer * 17)

    if layer == 0:
        # Himmel: heller Dunst zwischen den Staemmen, oben kuehl, unten warm.
        c.dither_v(0, 0, W, H, sky, mix(far, sky, 0.35), levels=7)

        # Die letzte gehaltene Note steht als bleiche Scheibe im Wald.
        c.glow(392, 74, 62, (255, 250, 235, 30), power=1.6)
        c.ellipse(392, 74, 17, 17, mix(sky, (255, 255, 255, 255), 0.55))
        c.ellipse(388, 70, 13, 13, mix(sky, (255, 255, 255, 255), 0.75))

        # Ferne Staemme, kaum vom Dunst abgesetzt - Tiefe, keine Form.
        veil = mix(far, sky, 0.42)
        for x, w in ((36, 12), (92, 9), (150, 15), (214, 8), (268, 13),
                     (330, 10), (438, 14), (486, 9)):
            trunk(c, x, 0, H, w, veil, rng, lean=rng.range(-0.02, 0.02),
                  flare=1.4, bark=False)
        light_shaft(c, 250, 34, (255, 246, 220), 22)
        light_shaft(c, 330, 20, (255, 246, 220), 16)
        motes(c, 300, rng, (255, 250, 235))
        return c

    if layer == 1:
        col = mix(far, P.FOREGROUND, 0.34)
        # Mittelgrund: ein Hain aus fuenf Staemmen, nach rechts enger
        # gestellt - dadurch zieht der Blick nach rechts, wohin man laeuft.
        for x, w, lean in ((22, 26, 0.01), (108, 34, -0.015), (206, 22, 0.02),
                           (300, 30, 0.0), (398, 24, -0.01), (470, 30, 0.015)):
            trunk(c, x, 0, H, w, col, rng, lean=lean, flare=2.4)

        # Ein Dach aus Zweigen, das den oberen Rand schliesst.
        # Die Nadeln nehmen die Kaelte des Dunstes auf, das Holz bleibt warm.
        # Zwei Zweige, die den oberen Rand von links und rechts her
        # schliessen. Drei uebereinander ergaben nur noch Filz.
        needles = mix(col, sky, 0.42)
        conifer_bough(c, -24, 14, 176, 48, col, rng, 1, needles, sub=1)
        conifer_bough(c, 536, 20, 168, 54, col, rng, -1, needles, sub=1)

        # Zapfen in drei Laengen - nie auf gleicher Hoehe.
        cone_on_chain(c, 152, 0, 96, 11, shade(col, -0.14), accent)
        cone_on_chain(c, 336, 0, 52, 8, shade(col, -0.14), accent)
        cone_on_chain(c, 428, 0, 132, 13, shade(col, -0.14), accent)

        # Unterholz an den Stammfuessen, damit sie nicht abgeschnitten wirken.
        for x in (22, 108, 206, 300, 398, 470):
            c.blob(x + rng.range(-8, 8), H - 6, rng.range(16, 30),
                   shade(col, -0.18), rng, lumps=6, squash=0.5)
        return c

    if layer == 2:
        col = mix(far, P.FOREGROUND, 0.70)
        # Nahe Staemme: nur zwei, dafuer riesig - sie rahmen links und rechts.
        trunk(c, 54, 0, H, 92, col, rng, lean=0.012, flare=2.6)
        trunk(c, 452, 0, H, 108, col, rng, lean=-0.010, flare=2.6)
        # Ein dritter, angeschnitten, weiter hinten in der Mitte rechts.
        trunk(c, 322, 0, H, 44, shade(col, 0.06), rng, flare=2.2)

        # Ein schwerer Ast quer durch das obere Drittel.
        c.branch(90, 34, -0.18, 120, 11, 3, col, rng, leaf=None, curve=0.22)
        needles = mix(col, sky, 0.22)
        conifer_bough(c, 86, 22, 196, 66, col, rng, 1, needles, sub=1)
        conifer_bough(c, 500, 4, 170, 58, col, rng, -1, needles, sub=1)

        cone_on_chain(c, 236, 0, 150, 15, shade(col, 0.05), accent)
        cone_on_chain(c, 392, 0, 84, 12, shade(col, 0.05), accent)

        # Wurzelwerk am Boden.
        for x, r in ((54, 46), (452, 52), (322, 30)):
            c.blob(x, H - 4, r, col, rng, lumps=8, squash=0.42)
        return c

    return c


# ------------------------------------------------------------ Kathedrale

def masonry(c: Canvas, x: int, y: int, w: int, h: int, col, course: int = 9,
            seed: int = 0) -> None:
    """Eine gemauerte Flaeche: versetzte Quader mit angedeuteten Fugen."""
    c.rect(x, y, w, h, col)
    joint = shade(col, -0.16)
    light = shade(col, 0.07)
    for row in range((h // course) + 1):
        yy = y + row * course
        if yy >= y + h:
            break
        c.rect(x, yy, w, 1, joint)
        c.rect(x, yy + 1, w, 1, light)
        offset = (row % 2) * (course * 2)
        for k in range((w // (course * 4)) + 2):
            jx = x + offset + k * course * 4 + int(hash01(k, row + seed) * 4)
            if x <= jx < x + w:
                c.rect(jx, yy, 1, course, joint)


def rose_window(c: Canvas, cx: int, cy: int, r: int, wall, glass, stone,
                accent) -> None:
    """
    Eine Fensterrose, in die Wand eingelassen.

    Der erste Versuch klebte sie als Scheibe vor den Dunst - dabei ist eine
    Rose ein Loch in einer Mauer. Also: erst die Laibung als abgestufter
    Ring in die Wand schneiden, dann das Glas, dann das Masswerk darueber.
    Ohne die Laibung fehlt der Mauer ihre Dicke, und das Fenster schwebt.
    """
    for i, amt in enumerate((0.16, -0.05, -0.24)):
        c.ellipse(cx, cy, r + 9 - i * 3, r + 9 - i * 3, shade(wall, amt))
    c.ellipse(cx, cy, r, r, glass)
    c.ellipse(cx - r * 0.18, cy - r * 0.18, r * 0.82, r * 0.82,
              mix(glass, accent, 0.30))

    # Masswerk: aeusserer Kranz aus Lanzetten, dann Speichen und Ringe.
    for i in range(16):
        a = i / 16 * math.tau
        lx, ly = cx + math.cos(a) * r * 0.80, cy + math.sin(a) * r * 0.80
        c.ellipse(lx, ly, r * 0.115, r * 0.115, mix(glass, accent, 0.55))
        c.ring(lx, ly, r * 0.115, 1, stone)
    for i in range(8):
        a = i / 8 * math.tau + math.pi / 8
        c.line(cx + math.cos(a) * r * 0.22, cy + math.sin(a) * r * 0.22,
               cx + math.cos(a) * r * 0.66, cy + math.sin(a) * r * 0.66, stone)
    c.ring(cx, cy, r * 0.66, 2, stone)
    c.ring(cx, cy, r * 0.22, 2, stone)
    c.ellipse(cx, cy, r * 0.16, r * 0.16, mix(accent, (255, 255, 255, 255), 0.35))
    c.ring(cx, cy, r, 3, stone)
    c.glow(cx, cy, r * 2.4, (accent[0], accent[1], accent[2], 30), power=1.8)


def lancet(c: Canvas, cx: int, top: int, w: int, h: int, wall, glass,
           stone, accent) -> None:
    """Ein hohes Spitzbogenfenster, ebenfalls in die Wand geschnitten."""
    c.gothic_arch(cx, top - 4, w + 8, h + 8, shade(wall, 0.12))
    c.gothic_arch(cx, top - 2, w + 4, h + 6, shade(wall, -0.18))
    c.gothic_arch(cx, top, w, h, glass)
    c.gothic_arch(cx, top + 3, w - 6, h - 6, mix(glass, accent, 0.35))
    c.rect(cx, top + int(h * 0.35), 1, int(h * 0.65), stone)
    c.gothic_arch(cx, top, w, h, stone, filled=False)
    c.glow(cx, top + h * 0.5, w * 1.8, (accent[0], accent[1], accent[2], 22))


def kathedrale(layer: int) -> Canvas:
    body, edge, accent, sky, far = P.REGIONS["kathedrale"]
    c = Canvas(W, H)
    rng = Rng(2202 + layer * 17)

    if layer == 0:
        # Nur Luft und Licht. Die Architektur steht eine Schicht davor -
        # eine frei schwebende Rose im Dunst sieht aufgeklebt aus.
        c.dither_v(0, 0, W, H, sky, mix(far, sky, 0.30), levels=7)
        light_shaft(c, 196, 52, accent, 26)
        light_shaft(c, 318, 30, accent, 18)
        motes(c, 240, rng, accent, alpha=(10, 38))
        return c

    if layer == 1:
        wall = mix(far, P.FOREGROUND, 0.30)
        stone = shade(wall, -0.34)
        glass = mix(sky, accent, 0.42)

        # Die Chorwand traegt alles andere. Unten franst sie aus, damit der
        # Blick zum Boden hin frei bleibt.
        masonry(c, 0, 0, W, 214, wall, course=9, seed=3)
        c.rough_edge(0, 208, W, 8, wall, seed=41)

        # Wandvorlagen gliedern die Flaeche senkrecht.
        for x in (46, 150, 362, 466):
            masonry(c, x - 13, 0, 26, 226, shade(wall, 0.09), course=11, seed=x)
            c.rect(x + 9, 0, 4, 226, shade(wall, 0.18))
            c.rect(x - 13, 0, 2, 226, shade(wall, -0.16))
            c.rect(x - 18, 150, 36, 9, shade(wall, 0.14))     # Kapitell
            c.rect(x - 20, 148, 40, 3, shade(wall, 0.20))

        # Gesims: ein waagerechtes Band trennt Rosen- und Fensterzone.
        c.rect(0, 152, W, 5, shade(wall, 0.16))
        c.rect(0, 157, W, 2, shade(wall, -0.22))
        c.rect(0, 150, W, 2, shade(wall, 0.24))

        rose_window(c, 256, 84, 46, wall, glass, stone, accent)

        for x in (98, 256, 414):
            lancet(c, x, 168, 30, 52, wall, glass, stone, accent)

        # Blendarkade ganz oben, damit die Wand nicht leer beginnt.
        for i in range(9):
            c.gothic_arch(24 + i * 58, 6, 44, 26, shade(wall, -0.12), filled=False)
            c.gothic_arch(24 + i * 58, 8, 40, 22, shade(wall, -0.06), filled=False)

        cone_on_chain(c, 196, 0, 96, 9, shade(wall, -0.26), accent)
        cone_on_chain(c, 318, 0, 142, 11, shade(wall, -0.26), accent)
        return c

    if layer == 2:
        col = mix(far, P.FOREGROUND, 0.72)
        # Zwei schwere Buendelpfeiler am Rand - sie rahmen und schneiden an.
        for x, w in ((-4, 74), (500, 82)):
            masonry(c, x - w // 2, 0, w, H, col, course=13, seed=int(x))
            for k in range(4):
                sx = x - w // 2 + 6 + k * (w // 4)
                c.rect(sx, 0, 5, H, shade(col, 0.08))
                c.rect(sx + 4, 0, 1, H, shade(col, -0.2))
        for i in range(9):
            px = 366 + i * 13
            ph = 92 + int(abs(math.sin(i * 0.9)) * 66)
            c.rect(px, 0, 10, ph, col)
            c.rect(px + 7, 0, 3, ph, shade(col, 0.09))
            c.rect(px, ph - 5, 10, 5, shade(col, -0.22))
            c.rect(px + 3, ph - 17, 4, 5, shade(col, -0.38))   # Aufschnitt
        cone_on_chain(c, 128, 0, 170, 14, shade(col, 0.06), accent)
        return c

    return c


# --------------------------------------------------------------- Grotten

def grotten(layer: int) -> Canvas:
    body, edge, accent, sky, far = P.REGIONS["grotten"]
    c = Canvas(W, H)
    rng = Rng(3303 + layer * 17)

    def spire(x: float, y0: float, length: float, width: float, col,
              down: bool = True) -> None:
        """Ein Kristall - gerade Facetten, keine weichen Kanten."""
        for i in range(int(length)):
            t = i / length
            w = width * (1 - t ** 0.85)
            y = y0 + i if down else y0 - i
            c.rect(int(x - w / 2), int(y), max(1, int(w)), 1,
                   mix(col, shade(col, -0.18), t * 0.5))
        # Facettenkante auf der Lichtseite.
        for i in range(0, int(length), 2):
            t = i / length
            w = width * (1 - t ** 0.85)
            y = y0 + i if down else y0 - i
            c.set(int(x + w / 2) - 1, int(y), shade(col, 0.16))

    if layer == 0:
        c.dither_v(0, 0, W, H, sky, mix(far, sky, 0.25), levels=7)
        # Ferne Kristalladern leuchten durch den Fels.
        for x, y, r in ((88, 190, 34), (300, 120, 46), (430, 210, 28)):
            c.glow(x, y, r * 2.2, (accent[0], accent[1], accent[2], 26), power=1.8)
        motes(c, 320, rng, accent, alpha=(12, 50))
        return c

    if layer == 1:
        col = mix(far, P.FOREGROUND, 0.34)
        # Decke und Boden greifen ineinander - eine Grotte, kein Zimmer.
        c.rough_edge(0, 0, W, 26, col, seed=11)
        c.rect(0, 0, W, 14, col)
        for x, ln, w in ((44, 78, 22), (128, 118, 30), (232, 62, 18),
                         (318, 96, 26), (404, 140, 34), (478, 70, 20)):
            spire(x, 10, ln, w, col, down=True)
        for x, ln, w in ((80, 54, 20), (196, 86, 26), (352, 46, 16), (462, 68, 24)):
            spire(x, H - 6, ln, w, col, down=False)
        # Eine grosse Kristallgruppe als Blickfang links der Mitte.
        for dx, ln, w in ((-16, 62, 14), (0, 92, 20), (14, 70, 15), (26, 46, 11)):
            spire(206 + dx, H - 10, ln, w, mix(col, accent, 0.22), down=False)
            c.glow(206 + dx, H - 10 - ln, 20, (accent[0], accent[1], accent[2], 40))
        return c

    if layer == 2:
        col = mix(far, P.FOREGROUND, 0.72)
        c.rect(0, 0, W, 22, col)
        c.rough_edge(0, 22, W, 16, col, seed=29)
        for x, ln, w in ((16, 130, 40), (150, 90, 30), (330, 160, 46), (486, 110, 36)):
            spire(x, 18, ln, w, col, down=True)
        for x, ln, w in ((60, 96, 34), (268, 62, 24), (430, 120, 40)):
            spire(x, H - 2, ln, w, col, down=False)
        return c

    return c


# ------------------------------------------------------------- Dissonanz

def dissonanz(layer: int) -> Canvas:
    body, edge, accent, sky, far = P.REGIONS["dissonanz"]
    c = Canvas(W, H)
    rng = Rng(4404 + layer * 17)

    if layer == 0:
        c.dither_v(0, 0, W, H, sky, mix(far, P.FOREGROUND, 0.3), levels=6)
        # Kein Blickfang, kein Licht - nur ein Glimmen tief unten.
        c.glow(256, 300, 200, (accent[0], accent[1], accent[2], 30), power=1.4)
        motes(c, 160, rng, accent, alpha=(8, 30))
        return c

    if layer == 1:
        col = mix(far, P.FOREGROUND, 0.38)
        # Alles steht schief. Die Pfeiler sind dieselben wie in der
        # Kathedrale - nur gekippt und gebrochen.
        for x, w, lean, height in ((60, 28, 0.09, 210), (170, 34, -0.13, 168),
                                   (300, 24, 0.16, 232), (420, 30, -0.08, 190)):
            for y in range(height):
                t = y / height
                ww = w * (0.7 + 0.3 * t)
                c.rect(int(x + lean * y - ww / 2), H - y, max(2, int(ww)), 1, col)
            # Bruchkante oben: gezackt statt gerade.
            top = H - height
            for i in range(int(w)):
                c.set(int(x + lean * height - w / 2 + i),
                      top + int(hash01(i, int(x)) * 7), shade(col, -0.3))
        # Ein gesprungener Bogen, der ins Leere fuehrt.
        c.gothic_arch(236, 40, 120, 78, col, filled=False)
        c.gothic_arch(236, 44, 112, 72, col, filled=False)
        c.rect(200, 62, 26, 3, (0, 0, 0, 0))   # herausgebrochenes Stueck
        cone_on_chain(c, 130, 0, 96, 13, shade(col, -0.1), accent)
        return c

    if layer == 2:
        col = mix(far, P.FOREGROUND, 0.74)
        for x, w, lean, height in ((-10, 74, 0.05, 288), (206, 44, -0.2, 150),
                                   (505, 80, -0.04, 288)):
            for y in range(height):
                t = y / height
                ww = w * (0.75 + 0.25 * t)
                c.rect(int(x + lean * y - ww / 2), H - y, max(2, int(ww)), 1, col)
        # Zerbrochene Glocken haengen still an ihren Ketten.
        for x, ln, sz in ((116, 70, 17), (352, 118, 21)):
            c.chain(x, 0, ln, shade(col, 0.16), link=5)
            cy = ln + sz
            for i in range(int(sz * 1.6)):
                t = i / (sz * 1.6)
                bw = sz * (0.45 + 0.55 * t ** 0.7)
                c.rect(int(x - bw), int(cy - sz + i), max(1, int(bw * 2)), 1,
                       mix(col, shade(col, -0.2), t * 0.5))
            # Der Riss, der sie verstummen liess.
            for i in range(int(sz)):
                c.set(int(x + sz * 0.3 - i * 0.35), int(cy - sz + sz * 0.6 + i), (0, 0, 0, 0))
            c.rect(int(x - sz), int(cy + sz * 0.6), int(sz * 2), 2, shade(col, -0.28))
        return c

    return c


# ------------------------------------------------------------ Vordergrund

def foreground(region: str) -> Canvas:
    """
    Die vorderste Schicht: fast schwarz, laeuft schneller als die Kamera.

    Sie hat nur eine Aufgabe - den Blick unten und in den Ecken abzuschliessen.
    Ohne sie klebt das Bild flach am Bildschirm.
    """
    body, edge, accent, sky, far = P.REGIONS[region]
    c = Canvas(W, H)
    rng = Rng(5505 + REGIONS.index(region) * 31)
    col = P.FOREGROUND
    base = H - 14

    # Geschlossener Saum unten.
    c.rect(0, base + 10, W, H - base - 10, col)
    for i in range(34):
        x = i * W / 30 + rng.range(-16, 16)
        c.blob(x, base + rng.range(4, 20), rng.range(20, 54), col, rng,
               lumps=6, squash=0.55)

    if region == "hain":
        # Farnwedel: gefuellte Masse mit gezackter Kante, wie die Zweige
        # oben - nur klein und aufrecht.
        for _ in range(10):
            x = rng.int(-10, W)
            h = rng.int(34, 86)
            lean = rng.range(-0.3, 0.3)
            pts = bezier((x, base + 6), (x + lean * 26, base - h * 0.45),
                         (x + lean * 52, base - h * 0.82), (x + lean * 74, base - h), 26)
            frond(c, pts, lambda t: 11 * (1 - t ** 0.7) + 1.5, col,
                  dark=col, light=col, serrate=2.5, back=0.3)
            c.stroke(pts, 3, 1, col)
        # Ein Ast, der von oben links hereinragt.
        c.branch(-16, 8, 0.34, 96, 9, 3, col, rng, leaf=col, curve=0.3)

    elif region == "kathedrale":
        # Ein Gelaender im Vordergrund - genau wie in einem Kirchenschiff.
        c.rect(0, base - 26, W, 4, col)
        c.rect(0, base - 8, W, 4, col)
        for i in range(W // 18 + 1):
            x = i * 18
            c.rect(x, base - 26, 3, 22, col)
            c.ellipse(x + 1, base - 30, 4, 5, col)     # Knauf
        c.branch(-10, 6, 0.5, 70, 8, 2, col, rng, curve=0.2)

    elif region == "grotten":
        for _ in range(11):
            x = rng.int(0, W)
            ln = rng.int(24, 70)
            w = rng.range(8, 22)
            for i in range(ln):
                t = i / ln
                ww = w * (1 - t ** 0.8)
                c.rect(int(x - ww / 2), base - i, max(1, int(ww)), 1, col)
        for _ in range(5):
            x = rng.int(0, W)
            ln = rng.int(20, 56)
            w = rng.range(9, 20)
            for i in range(ln):
                t = i / ln
                ww = w * (1 - t ** 0.8)
                c.rect(int(x - ww / 2), i, max(1, int(ww)), 1, col)

    else:
        # Dissonanz: Schutt und abgebrochene Zacken.
        for _ in range(16):
            x = rng.int(0, W)
            ln = rng.int(16, 58)
            skew = rng.range(-0.5, 0.5)
            w = rng.range(7, 20)
            for i in range(ln):
                t = i / ln
                ww = w * (1 - t ** 0.7)
                c.rect(int(x + skew * i - ww / 2), base - i, max(1, int(ww)), 1, col)

    return c


# --------------------------------------------------------------------- Bau

BUILDERS = {"hain": hain, "kathedrale": kathedrale,
            "grotten": grotten, "dissonanz": dissonanz}


def build() -> None:
    atlas = Atlas("backdrops", padding=2, max_width=512)
    for region in REGIONS:
        for layer in range(3):
            atlas.add(f"{region}_bg{layer}", BUILDERS[region](layer), pivot=(0, 0),
                      parallax=[0.10, 0.28, 0.52][layer])
        atlas.add(f"{region}_fg", foreground(region), pivot=(0, 0), parallax=1.30)
    png, js = atlas.write(OUT)
    print(f"backdrops  -> {png.name} ({len(atlas.frames)} Frames)")


if __name__ == "__main__":
    build()
