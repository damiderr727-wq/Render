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

# Wie schnell eine Schicht mitlaeuft. 0 heisst: sie klebt am Bildschirm
# und bewegt sich gar nicht; 1 heisst: sie liegt in der Welt und laeuft
# mit ihr.
#
# Die Werte waren vorher deutlich hoeher, und das war der Grund, warum
# die Wiederholung der Schichten auffiel: eine Kachelfuge, die schnell
# durchs Bild zieht, sieht man. Dieselbe Fuge, die sich kaum bewegt,
# liest sich als Ferne. Die Vorbilder machen genau das - ihre
# Hintergruende sind ebenfalls wiederholt, sie kriechen nur.
#
# Seit dem Blick auf Silksong sind es vier statt drei. Dort hat der
# Hintergrund selbst noch einen Hintergrund: hinter den Baeumen, die man
# als Baeume erkennt, steht eine zweite Waldwand, die nur noch Wert ist -
# keine Form, keine Kante, kein Detail. Ohne sie sitzen die erkennbaren
# Silhouetten direkt auf dem Himmel, und der Wald hoert genau dort auf,
# wo man hinsieht.
#
#   0  Luft. Himmel, Sonne, Staub. Steht voellig still.
#   1  Die ferne Wand: Werte ohne Form.
#   2  Der Mittelgrund: hier faengt Gestalt an.
#   3  Der nahe Rahmen: was den Blick links und rechts abschliesst.
PARALLAX = [0.0, 0.06, 0.14, 0.27]
PARALLAX_VORN = 1.16

# So hoch wie der hoechste Raum: so weit reicht die ferne Wand.
HOCH = 560
SCHICHTEN = len(PARALLAX)

REGIONS = ["hain", "kathedrale", "grotten", "dissonanz"]

# Schicht 0 wird beim Bau zweimal gebraucht: einmal ganz - daraus kommt
# der Dunstverlauf - und einmal ohne ihren Verlauf, also nur Mond,
# Lichtbalken und Staub auf durchsichtigem Grund.
#
# Der Grund: der Verlauf gehoert nicht in eine 288 Pixel hohe Kachel. Ein
# Raum ist oft doppelt so hoch, und dann endet der Himmel auf halber
# Hoehe und darunter steht eine Flaeche in einer anderen Farbe. Der
# Verlauf liegt deshalb als eigener, ueber die ganze Raumhoehe gedehnter
# Streifen ganz hinten (`{region}_himmel`), und Schicht 0 traegt nur noch
# das, was *im* Himmel steht.
OHNE_VERLAUF = False


# ---------------------------------------------------------------- Bausteine

def luftraum(c: Canvas, stufen) -> None:
    """
    Der Himmel als Verlauf ueber mehrere Farbstufen.

    Zwei Stufen reichen nicht. Ein linearer Verlauf zwischen einem kalten
    dunklen und einem warmen hellen Ton laeuft in der Mitte durch genau
    den Punkt, an dem sich beide aufheben - und der ist grau. In einem
    Raum, der hoeher ist als ein Bildschirm, liegt dieses graue Stueck
    ausgerechnet dort, wo sonst nichts steht, und dann ist das obere
    Drittel des Bildes eine leere graue Flaeche. Genau das war zu sehen.

    Mit drei oder vier gesetzten Stufen laeuft der Verlauf um den
    Graupunkt herum: oben blaugruen und fast schwarz, in der Mitte
    tiefes Tannengruen, unten der warme Dunst, gegen den sich die
    Staemme abheben. Jede Stufe ist eine Entscheidung, keine Rechnung.

    `stufen` ist eine Liste (Anteil an der Hoehe, Farbe), von oben nach
    unten.
    """
    for i in range(len(stufen) - 1):
        (t0, c0), (t1, c1) = stufen[i], stufen[i + 1]
        y0, y1 = int(t0 * c.h), int(t1 * c.h)
        c.dither_v(0, y0, c.w, max(1, y1 - y0), c0, c1, levels=7)


def hochgezogen(bild: Canvas, hoehe: int) -> Canvas:
    """
    Zieht eine Schicht nach oben aus, indem jede Spalte ihre oberste
    Zeile fortsetzt.

    Die Kulissen sind bildschirmhoch, viele Raeume sind doppelt so hoch.
    Ueber der Kulisse stand deshalb nichts als Himmel - und ein Wald,
    der auf halber Hoehe aufhoert, ist kein Wald, sondern eine Tapete.

    Fuer die ferne Wand geht das Fortsetzen sauber auf: sie besteht aus
    senkrechten Staemmen, und ein Stamm, der nach oben weiterlaeuft, ist
    genau das, was ein Stamm tut. Fuer Schichten mit Aesten und Kronen
    waere derselbe Griff falsch - die wuerden zu Schlieren.
    """
    c = Canvas(bild.w, hoehe)
    dy = hoehe - bild.h
    for y in range(bild.h):
        for x in range(bild.w):
            px = bild.get(x, y)
            if px[3]:
                c.set(x, y + dy, px)
    for x in range(bild.w):
        px = bild.get(x, 0)
        if px[3] < 190:
            continue
        for y in range(dy):
            c.set(x, y, px)
    return c


def trunk(c: Canvas, x: float, top: float, bottom: float, width: float,
          col, rng: Rng | None = None, lean: float = 0.0,
          flare: float = 2.2, bark: bool = True) -> None:
    """
    Ein Stamm mit Wurzelanlauf.

    Nach unten wird er breiter - das ist der Unterschied zwischen einem Baum
    und einem Balken. Die Lichtseite bekommt eine schmale helle Kante.
    """
    rng = rng or Rng(3)
    kerbe = int(x) * 13 + int(width)         # eigener Wuchs je Stamm
    for y in range(int(top), int(bottom)):
        t = (y - top) / max(1.0, bottom - top)
        # Unten Wurzelanlauf, oben leichte Verjuengung.
        w = width * (0.72 + 0.28 * t) * (1 + (flare - 1) * max(0.0, t - 0.82) / 0.18)
        # Ein Stamm ist keine Saeule. Zwei langsame Wellen ueber die
        # Hoehe machen aus dem glatten Kegel etwas Gewachsenes - ohne
        # dass die Silhouette unruhig wird.
        w *= 1.0 + math.sin(y * 0.035 + kerbe) * 0.045 \
            + math.sin(y * 0.011 + kerbe * 0.3) * 0.055
        cx = x + lean * (bottom - y)
        x0 = int(cx - w / 2)
        c.rect(x0, y, max(2, int(w)), 1, col)
        if bark:
            # Rinde: senkrechte Risse, die mitwandern und aufreissen.
            for k in range(max(1, int(w / 6))):
                sx = x0 + 2 + k * 6 + int(hash01(k, y // 11) * 4)
                tief = hash01(k * 7, y // 5 + kerbe)
                if tief > 0.55:
                    c.set(sx, y, shade(col, -0.20))
                    if tief > 0.85:
                        c.set(sx + 1, y, shade(col, -0.09))
                elif tief < 0.12:
                    c.set(sx, y, shade(col, 0.08))
            # Lichtkante rechts, Schattenkante links.
            c.rect(int(cx + w / 2) - 2, y, 2, 1, shade(col, 0.12))
            c.set(int(cx + w / 2) - 1, y, shade(col, 0.20))
            c.rect(x0, y, 1, 1, shade(col, -0.20))


def _verdichtet(pts, schritt: float = 0.7):
    """
    Legt Stuetzpunkte im gleichen Abstand auf eine Polylinie.

    Wer eine Flaeche quer zu einer Kurve fuellt, braucht die Kurve in
    Pixelabstand - sonst hat die Flaeche Loecher. Bezier gibt aber eine
    feste Anzahl Punkte zurueck, und die liegen bei langen Kurven weit
    auseinander.
    """
    if len(pts) < 2:
        return pts
    aus = [pts[0]]
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d / schritt))
        for k in range(1, n + 1):
            u = k / n
            aus.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
    return aus


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

    Der dritte Fehler steckte in der Abtastung. Die Kurve kam mit rund
    zwei Pixeln Abstand zwischen den Stuetzpunkten herein, und an jedem
    Stuetzpunkt wurde eine *ein Pixel breite* Linie quer dazu gesetzt.
    Zwischen zwei solchen Linien bleibt Luft, sobald die Kurve schraeg
    laeuft - und genau daher kam das Zerbrochene an den Aesten: keine
    Masse, sondern ein Kamm aus Strichen. Die Kurve wird jetzt vorher
    auf Pixelabstand verdichtet, und quer dazu wird in halben Schritten
    gefuellt. Dann schliesst sich die Flaeche.
    """
    dark = dark or shade(fill, -0.16)
    light = light or shade(fill, 0.14)
    pts = _verdichtet(pts, 0.7)
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
            k = 0.0
            while k <= extent:
                ox = px + nx * side * k - tx / length * back * k
                oy = py + ny * side * k - ty / length * back * k
                shade_amt = -0.04 - (k / max(1.0, extent)) * 0.18
                c.set(int(ox), int(oy), shade(dark if side > 0 else fill, shade_amt))
                k += 0.5
        # Lichtkante auf der Oberseite.
        c.set(int(px + nx * -1 * hw * 0.75), int(py + ny * -1 * hw * 0.75), light)

    # Kante ausfransen. Der Abstand der Kerben richtet sich nach der
    # Laenge, nicht nach der Anzahl der Stuetzpunkte - sonst wird aus
    # einer verdichteten Kurve ein Kamm mit Kerbe an jedem Pixel.
    for i in range(0, len(pts), max(2, int(3 / 0.7))):
        px, py = pts[i]
        qx, qy = pts[min(i + 1, n)]
        tx, ty = qx - px, qy - py
        length = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / length, tx / length
        hw = half_width(i / n)
        for side in (-1, 1):
            extent = hw * (1.0 if side > 0 else 0.82)
            notch = hash01(int(px), int(py) + side * 7) * serrate
            k = 0.0
            while k < notch:
                c.set(int(px + nx * side * (extent - k)),
                      int(py + ny * side * (extent - k)), None)
                k += 0.5


def conifer_bough(c: Canvas, x: float, y: float, span: float, droop: float,
                  col, rng: Rng, direction: int = 1,
                  needle_col=None, sub: int = 2, width: float = 40.0) -> None:
    """
    Ein Nadelzweig, der von oben ins Bild haengt.

    Zwei Anlaeufe daneben, aus entgegengesetzten Gruenden.

    Der erste fuellte die Masse mit Luecken - ein Kamm aus Strichen statt
    einer Flaeche, und genau das sah zerbrochen aus. Der zweite fuellte
    sie sauber, aber als *eine* Flaeche: ein Keil von achtzig Pixeln
    Dicke mit weicher Kante, und der liest sich als graue Planke, die
    schraeg durchs Bild liegt.

    Ein Nadelzweig ist keine Flaeche. Er ist eine Rippe, an der Bueschel
    sitzen - erst der Umriss aus lauter kleinen Spitzen macht ihn
    erkennbar, nicht die Menge Farbe. Also wird die Rippe gezogen und an
    ihr entlang werden Bueschel gesetzt, nach hinten geneigt und nach
    aussen hin kuerzer. Was dazwischen frei bleibt, muss frei bleiben:
    durch einen Zweig sieht man hindurch.
    """
    needle_col = needle_col or shade(col, -0.06)
    pts = bezier((x, y),
                 (x + direction * span * 0.35, y + droop * 0.10),
                 (x + direction * span * 0.72, y + droop * 0.42),
                 (x + direction * span, y + droop), 72)
    pts = _verdichtet(pts, 1.0)
    n = len(pts) - 1
    dunkel = shade(needle_col, -0.20)
    hell = shade(needle_col, 0.16)

    # Abstand der Bueschel: eng genug, dass sie sich beruehren, weit
    # genug, dass zwischen ihnen Kerben stehen bleiben.
    schritt = max(3, int(width * 0.16))
    for i in range(0, n, schritt):
        px, py = pts[i]
        qx, qy = pts[min(i + 3, n)]
        tx, ty = qx - px, qy - py
        laenge_t = math.hypot(tx, ty) or 1.0
        tx, ty = tx / laenge_t, ty / laenge_t
        nx, ny = -ty, tx
        t = i / n
        # Nach aussen wird der Zweig schmaler, mit einem weichen Anlauf
        # an der Ansatzstelle.
        buendel = width * (1 - t ** 0.85) * min(1.0, 0.35 + t * 4.0) + 2.5

        for side in (-1, 1):
            reihen = max(1, int(buendel / 3.4))
            for k in range(reihen):
                u = (k + 0.5) / reihen
                # Jedes Bueschel etwas anders lang - sonst entsteht wieder
                # eine glatte Kante.
                lang = buendel * (0.55 + 0.45 * u) \
                    * (0.72 + hash01(i * 3 + k, int(x) + side * 7) * 0.5)
                if side < 0:
                    lang *= 0.84
                # Richtung: quer zur Rippe, aber deutlich nach hinten
                # geneigt - Nadeln zeigen nie nach vorn.
                dx = nx * side * 0.92 - tx * 0.42
                dy = ny * side * 0.92 - ty * 0.42
                d = math.hypot(dx, dy) or 1.0
                dx, dy = dx / d, dy / d
                # Ansatzpunkt leicht versetzt, damit die Bueschel nicht
                # alle aus demselben Punkt kommen.
                ax = px + tx * (k * 0.9) + nx * side * 1.2
                ay = py + ty * (k * 0.9) + ny * side * 1.2
                dicke = 2.2 * (1 - u * 0.45)
                j = 0.0
                while j < lang:
                    v = j / max(1.0, lang)
                    w = dicke * (1 - v ** 0.75)
                    ton = mix(dunkel if side > 0 else needle_col,
                              hell, max(0.0, 0.35 - v * 0.35) if side < 0 else 0.0)
                    q = -w
                    while q <= w:
                        c.set(int(ax + dx * j - dy * q), int(ay + dy * j + dx * q), ton)
                        q += 0.6
                    j += 0.6

    # Die Mittelrippe zuletzt, damit sie oben liegt.
    c.stroke(pts, 3.4, 1.1, col)
    c.stroke(pts, 1.2, 0.5, shade(col, 0.14))

    for _ in range(sub):
        i = rng.int(10, max(11, len(pts) - 22))
        bx, by = pts[i]
        conifer_bough(c, bx, by, span * rng.range(0.30, 0.46),
                      droop * rng.range(0.5, 0.95), shade(col, -0.05), rng,
                      direction, needle_col, sub=0, width=width * 0.58)


def haengender_vorhang(c: Canvas, x: float, breite: float, laenge: float,
                       col, rng: Rng) -> None:
    """
    Ein Vorhang aus Flechten, der von oben ins Bild haengt.

    Er ersetzt den Zapfen an der Kette. Der hat den Massstab getragen,
    ja - aber er hing an einer *Kette*, mitten im Wald, und mit seinen
    Schuppenreihen las er sich als Wespennest. Etwas, das an einer Kette
    haengt, gehoert an eine Decke, die jemand gebaut hat; im Hain haengt
    nichts an Ketten. Ein Vorhang traegt denselben Massstab und stellt
    dabei keine Fragen.
    """
    for i in range(int(breite)):
        px = x + i
        # Zwei ueberlagerte Wellen: die Unterkante darf nirgends gerade
        # sein und nirgends regelmaessig zacken.
        ln = laenge * (0.34 + 0.66 * abs(math.sin(i * 0.13 + x * 0.07)))
        ln *= 0.6 + hash01(i, int(x)) * 0.7
        for k in range(int(ln)):
            t = k / max(1.0, ln)
            if t > 0.6 and hash01(i * 5 + k, int(x) + 11) > 1.4 - t:
                continue
            c.set(int(px + math.sin(k * 0.09 + i) * 2.2), int(k),
                  shade(col, 0.06 - t * 0.30))
    # Ein Ast, an dem der Vorhang sitzt - sonst haengt er im Nichts.
    c.rect(int(x - 3), 0, int(breite) + 6, 2, shade(col, -0.18))
    c.rect(int(x - 3), 2, int(breite) + 6, 1, shade(col, 0.10))


def cone_on_chain(c: Canvas, x: float, top: float, length: float, size: float,
                  col, accent) -> None:
    """
    Ein Zapfen an einer Kette.

    Nicht mehr im Hain und nicht mehr in der Kathedrale in Gebrauch: dort
    las er sich als Wespennest, und in der Kathedrale hing er ausserdem
    zwischen Rosetten herum, wo er nie hingehoert hat. Bleibt fuer die
    Dissonanz, wo Dinge an Ketten haengen sollen.
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


# ------------------------------------------------------- Waldbewuchs
#
# Was den Wald in den Vorbildern dicht macht, sind nicht die Staemme -
# es ist alles, was an ihnen haengt. Ein Stamm allein ist ein Balken.
# Derselbe Stamm mit Moosbart, Baumschwamm und einer Ranke davor ist ein
# Baum, an dem seit Jahren niemand vorbeigekommen ist.

def moosbart(c: Canvas, x: float, y: float, breite: float, laenge: float,
             col, rng: Rng) -> None:
    """Moos, das in ungleichen Straehnen von einem Ast herunterhaengt."""
    hell = shade(col, 0.10)
    for i in range(int(breite)):
        px = x + i
        # Die Laenge folgt einer weichen Welle, nicht dem Zufall allein -
        # sonst wird der Bart ein Kamm.
        ln = laenge * (0.35 + 0.65 * abs(math.sin(i * 0.21 + x * 0.05)))
        ln *= 0.7 + hash01(i, int(x)) * 0.6
        for k in range(int(ln)):
            t = k / max(1.0, ln)
            # Nach unten franst er aus: nicht jeder Pixel wird gesetzt.
            if t > 0.55 and hash01(i * 7 + k, int(x) + 3) > 1.25 - t:
                continue
            c.set(int(px + math.sin(k * 0.24) * 1.2), int(y + k),
                  shade(col, -0.10 - t * 0.16))
        if ln > 3:
            c.set(int(px), int(y), hell)


def baumschwamm(c: Canvas, x: float, y: float, r: float, col, seite: int = 1) -> None:
    """
    Ein Baumschwamm - eine flache Konsole am Stamm.

    Der erste Anlauf war ein Dreieck mit heller Oberkante, und aus zwei
    Metern Abstand sass an jedem Stamm ein weisser Keil. Zwei Sachen
    dagegen: die Oberkante ist eine *Kurve*, kein Anstieg, und der
    Helligkeitsunterschied zum Stamm bleibt klein. Ein Pilz im
    Hintergrund soll die Silhouette des Stammes brechen, nicht sich
    selbst vorstellen.
    """
    hoehe = r * 0.62
    for i in range(int(hoehe)):
        t = i / max(1.0, hoehe)
        # Halbkreisartig: vorne weit ausladend, dann schnell zum Stamm
        # zurueck - so haengt ein Schwamm an der Rinde.
        w = r * math.sqrt(max(0.0, 1 - t * t)) * (1 - t * 0.35)
        if w < 1:
            continue
        c.rect(int(x if seite > 0 else x - w), int(y + i), max(1, int(w)), 1,
               mix(shade(col, 0.06), shade(col, -0.22), t ** 0.5))
    # Ein schmaler Lichtsaum oben, ein dunkler Strich unten. Beide duenn.
    for i in range(int(r)):
        u = i / max(1.0, r)
        if math.sqrt(max(0.0, 1 - 0.0)) * r < i:
            break
        c.set(int(x + seite * i), int(y), shade(col, 0.13 - u * 0.10))
    c.set(int(x + seite * int(r * 0.5)), int(y + hoehe), shade(col, -0.30))


def ranke(c: Canvas, x: float, y: float, laenge: float, col, rng: Rng,
          blatt: float = 0.5) -> None:
    """Eine Ranke: ein duenner Strang mit Blaettern, die abwechselnd sitzen."""
    drift = rng.range(-0.14, 0.14)
    for i in range(int(laenge)):
        t = i / laenge
        px = x + drift * i + math.sin(i * 0.13 + x) * (1.6 + t * 2.4)
        c.set(int(px), int(y + i), shade(col, -0.06))
        if i % 7 == 3 and hash01(i, int(x)) < blatt:
            seite = 1 if (i // 7) % 2 == 0 else -1
            for k in range(1, rng.int(3, 6)):
                c.set(int(px + seite * k), int(y + i + k // 2), shade(col, 0.08))
                c.set(int(px + seite * k), int(y + i + k // 2 + 1), shade(col, -0.14))


def farnbueschel(c: Canvas, x: float, boden: float, hoehe: float, col,
                 rng: Rng) -> None:
    """Ein Farn am Stammfuss - drei bis fuenf Wedel aus einem Punkt."""
    for _ in range(rng.int(3, 6)):
        lean = rng.range(-0.85, 0.85)
        h = hoehe * rng.range(0.6, 1.0)
        pts = bezier((x, boden), (x + lean * h * 0.3, boden - h * 0.55),
                     (x + lean * h * 0.6, boden - h * 0.85),
                     (x + lean * h * 0.95, boden - h), 20)
        frond(c, pts, lambda t: h * 0.16 * (1 - t ** 0.7) + 1.2, col,
              serrate=2.0, back=0.25)


# ------------------------------------------------------------------- Hain

def hain(layer: int) -> Canvas:
    body, edge, accent, sky, far = P.REGIONS["hain"]
    c = Canvas(W, H)
    rng = Rng(1201 + layer * 17)

    if layer == 0:
        # Nur Luft. Kein Stamm, keine Silhouette, keine Kante - alles, was
        # eine Form hat, steht eine Schicht davor. Diese hier bewegt sich
        # ueberhaupt nicht, sie ist der Grund, auf dem der Wald liegt.
        # Oben dunkel, nach unten heller.
        #
        # Andersherum war es falsch, und man sah es sofort in hohen
        # Raeumen: ueber der Kulisse stand ein grosses helles Feld, und
        # das ganze obere Drittel eines Raumes war schlicht grau. Nachts
        # ist der Himmel oben am dunkelsten; hell wird es dort, wo Dunst
        # zwischen den Staemmen steht, also unten.
        if not OHNE_VERLAUF:
            luftraum(c, [(0.00, hexc("#0a1015")), (0.34, hexc("#15211e")),
                         (0.64, hexc("#2b3931")), (0.86, hexc("#4d5945")),
                         (1.00, hexc("#657053"))])

        # Die letzte gehaltene Note steht als bleiche Scheibe im Wald.
        # Sie haengt hoch: dort sind die Kulissenschichten in ihre obersten
        # Reihen hinein durchsichtig gezeichnet, und der Mond steht
        # zwischen ihnen statt mitten in einem Stamm.
        c.glow(392, 34, 74, (255, 250, 235, 26), power=1.7)
        c.ellipse(392, 34, 13, 13, mix(sky, (255, 255, 255, 255), 0.62))
        c.ellipse(389, 31, 10, 10, mix(sky, (255, 255, 255, 255), 0.82))

        light_shaft(c, 250, 34, (255, 246, 220), 22)
        light_shaft(c, 330, 20, (255, 246, 220), 16)
        motes(c, 300, rng, (255, 250, 235))
        return c

    if layer == 1:
        # Die ferne Waldwand. Sie darf keine lesbare Form haben - kein
        # Ast, keine Rinde, keine Lichtkante. Nur Werte, die sich vom
        # Himmel abheben und nach oben in ihm verschwinden.
        #
        # Sie ist dunkler als der Dunst - ein Wald in der Ferne ist eine
        # Masse, durch die Licht nicht kommt. Wie viel dunkler, entscheidet
        # aber nicht diese Funktion, sondern `in_ferne` beim Zusammenbau.
        #
        # Ein Zwischenstand hat hier selbst abgedunkelt *und* nachher noch
        # in die Ferne gezogen. Das Ergebnis war eine Schicht, die
        # schwaerzer war als der Mittelgrund davor - also genau
        # andersherum als die Luft es macht. Was weiter weg ist, ist naeher
        # am Dunst. Immer.
        veil = mix(far, P.FOREGROUND, 0.30)
        tiefer = mix(far, P.FOREGROUND, 0.52)

        # Eine Wand aus dicht stehenden Staemmen, die zwischen sich nur
        # Schlitze freilaesst. Entscheidend ist der Rhythmus: gleiche
        # Abstaende ergeben einen Lattenzaun, und den erkennt das Auge
        # sofort als Muster. Also in Gruppen - zwei, drei Staemme dicht
        # beieinander, dann eine Luecke, in der der Dunst steht.
        x = -8.0
        i = 0
        while x < W + 12:
            gruppe = 1 + int(hash01(i, 3) * 3)
            for k in range(gruppe):
                w = 4 + hash01(i * 7 + k, 11) * 13
                # Drei Tiefen, nicht zwei: erst damit staffelt sich die
                # Wand in sich selbst.
                ton = (tiefer, veil, mix(far, P.FOREGROUND, 0.41))[(i + k) % 3]
                trunk(c, x, 0, H, w, ton, rng,
                      lean=rng.range(-0.015, 0.015), flare=1.35, bark=False)
                x += w * rng.range(0.75, 1.25) + 2
            x += rng.range(6, 26)          # die Luecke dazwischen
            i += 1

        # Und ganz hinten zwei Baumriesen, die nur als Wert dastehen.
        for gx, w in ((128, 40), (368, 46)):
            trunk(c, gx, 0, H, w, mix(far, P.FOREGROUND, 0.60), rng,
                  flare=1.6, bark=False)

        # Unterholz als geschlossenes Band am Fuss - der Boden der Ferne.
        # Es muss oben ausgefranst sein, sonst zieht sich eine waagerechte
        # Kante durch das Bild, und die verraet die Schicht als Tapete.
        for i in range(46):
            c.blob(i * 12 + rng.range(-10, 10), H - rng.range(0, 22),
                   rng.range(12, 34), tiefer, rng, lumps=6, squash=0.5)
        return c

    if layer == 2:
        col = mix(far, P.FOREGROUND, 0.34)
        # Mittelgrund: ein Hain aus sechs Staemmen, nach rechts enger
        # gestellt - dadurch zieht der Blick nach rechts, wohin man laeuft.
        staemme = ((22, 26, 0.01), (108, 34, -0.015), (206, 22, 0.02),
                   (300, 30, 0.0), (398, 24, -0.01), (470, 30, 0.015))
        for x, w, lean in staemme:
            trunk(c, x, 0, H, w, col, rng, lean=lean, flare=2.4)

        # Ein Dach aus Zweigen, das den oberen Rand schliesst.
        # Die Nadeln nehmen die Kaelte des Dunstes auf, das Holz bleibt warm.
        # Zwei Zweige, die den oberen Rand von links und rechts her
        # schliessen. Drei uebereinander ergaben nur noch Filz.
        # Alles, was an dieser Schicht haengt, bleibt in ihrem Wertband.
        # Vorher wurde jedes Blatt und jedes Moos zum *Himmel* hin
        # gemischt - dann haengt an einem dunklen Stamm ein weisser
        # Fetzen, und der zieht mehr Blick auf sich als die Heldin.
        # Die Tiefe traegt die Schicht, nicht das einzelne Ding darin.
        needles = shade(col, -0.07)
        conifer_bough(c, -24, 14, 176, 48, col, rng, 1, needles, sub=1)
        conifer_bough(c, 536, 20, 168, 54, col, rng, -1, needles, sub=1)

        # Was an den Staemmen haengt: Baumschwaemme in Gruppen, Moos in
        # den Astgabeln, Ranken davor. Erst das macht aus sechs Balken
        # einen Wald.
        # Baumschwaemme wachsen in Staffeln uebereinander, nicht einzeln
        # ueber den ganzen Stamm verteilt - verteilt sahen sie aus wie
        # Sprossen einer Leiter.
        for x, w, _ in staemme:
            if rng.chance(0.35):
                continue
            y0 = rng.range(70, H - 90)
            seite = 1 if rng.chance(0.5) else -1
            for k in range(rng.int(2, 4)):
                baumschwamm(c, x + seite * w * 0.38, y0 + k * rng.range(5, 9),
                            rng.range(4, 10) * (1 - k * 0.18),
                            shade(col, 0.04), seite)
            moosbart(c, x - w * 0.4, rng.range(30, 90), w * 0.8,
                     rng.range(10, 26), shade(col, -0.14), rng)
        for x in (66, 172, 254, 352, 436):
            ranke(c, x, rng.range(-6, 30), rng.range(70, 190),
                  shade(col, -0.05), rng, blatt=0.75)

        # Zapfen in drei Laengen - nie auf gleicher Hoehe.
        haengender_vorhang(c, 138, 34, 78, shade(col, -0.10), rng)
        haengender_vorhang(c, 330, 22, 44, shade(col, -0.10), rng)
        haengender_vorhang(c, 412, 40, 104, shade(col, -0.10), rng)

        # Unterholz an den Stammfuessen, damit sie nicht abgeschnitten wirken.
        for x, _, _ in staemme:
            c.blob(x + rng.range(-8, 8), H - 6, rng.range(16, 30),
                   shade(col, -0.18), rng, lumps=6, squash=0.5)
            farnbueschel(c, x + rng.range(-16, 16), H - 4, rng.range(20, 38),
                         shade(col, -0.10), rng)
        return c

    if layer == 3:
        col = mix(far, P.FOREGROUND, 0.70)
        # Nahe Staemme: nur zwei, dafuer riesig - sie rahmen links und rechts.
        trunk(c, 54, 0, H, 92, col, rng, lean=0.012, flare=2.6)
        trunk(c, 452, 0, H, 108, col, rng, lean=-0.010, flare=2.6)
        # Ein dritter, angeschnitten, weiter hinten in der Mitte rechts.
        trunk(c, 322, 0, H, 44, shade(col, 0.06), rng, flare=2.2)

        # Ein schwerer Ast quer durch das obere Drittel.
        c.branch(90, 34, -0.18, 120, 11, 3, col, rng, leaf=None, curve=0.22)
        needles = shade(col, -0.05)
        conifer_bough(c, 86, 22, 196, 66, col, rng, 1, needles, sub=1)
        conifer_bough(c, 500, 4, 170, 58, col, rng, -1, needles, sub=1)

        # In dieser Naehe traegt jeder Stamm sichtbar etwas: schwere
        # Schwaemme in Staffeln, Moos ueber dem Ast, Ranken davor.
        for x, w in ((54, 92), (452, 108), (322, 44)):
            y0 = rng.range(60, H - 110)
            seite = 1 if rng.chance(0.5) else -1
            for k in range(rng.int(2, 4)):
                baumschwamm(c, x + seite * w * 0.42, y0 + k * rng.range(8, 14),
                            rng.range(8, 16) * (1 - k * 0.16),
                            shade(col, 0.03), seite)
        moosbart(c, 96, 30, 96, 34, shade(col, -0.12), rng)
        moosbart(c, 400, 16, 84, 28, shade(col, -0.12), rng)
        for x in (30, 118, 300, 344, 476):
            ranke(c, x, rng.range(-10, 20), rng.range(90, 220),
                  shade(col, -0.04), rng, blatt=0.6)

        haengender_vorhang(c, 218, 52, 128, shade(col, -0.09), rng)
        haengender_vorhang(c, 380, 34, 70, shade(col, -0.09), rng)

        # Wurzelwerk am Boden.
        for x, r in ((54, 46), (452, 52), (322, 30)):
            c.blob(x, H - 4, r, col, rng, lumps=8, squash=0.42)
            farnbueschel(c, x + rng.range(-30, 30), H - 2, rng.range(30, 54),
                         shade(col, -0.06), rng)
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
        if not OHNE_VERLAUF:
            luftraum(c, [(0.00, hexc("#0c0b14")), (0.40, hexc("#1d1a2c")),
                         (0.74, hexc("#382f49")), (1.00, hexc("#584c66"))])
        light_shaft(c, 196, 52, accent, 26)
        light_shaft(c, 318, 30, accent, 18)
        motes(c, 240, rng, accent, alpha=(10, 38))
        return c

    if layer == 1:
        # Die Ferne des Kirchenschiffs: eine Flucht von Arkaden, die sich
        # nach hinten verliert. Keine Details, nur Boegen als Wert - sie
        # geben dem Raum die Laenge, die eine einzelne Wand nie hat.
        dunst = mix(far, sky, 0.36)
        tiefer = mix(far, sky, 0.20)
        c.rect(0, 0, W, 40, tiefer)
        for i in range(7):
            bx = 34 + i * 76
            c.gothic_arch(bx, 40, 58, 150, dunst)
            c.gothic_arch(bx, 48, 44, 136, tiefer)
            c.rect(bx - 34, 30, 8, 210, dunst)
        c.rect(0, 236, W, H - 236, dunst)
        for i in range(24):
            c.blob(i * 22 + rng.range(-8, 8), 240, rng.range(12, 24),
                   tiefer, rng, lumps=4, squash=0.5)
        return c

    if layer == 2:
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

        # Hier hingen zwei Zapfen an Ketten. In einer Kirche.
        return c

    if layer == 3:
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
        if not OHNE_VERLAUF:
            luftraum(c, [(0.00, hexc("#070d16")), (0.40, hexc("#12202e")),
                         (0.74, hexc("#264057")), (1.00, hexc("#44607d"))])
        # Ferne Kristalladern leuchten durch den Fels.
        for x, y, r in ((88, 190, 34), (300, 120, 46), (430, 210, 28)):
            c.glow(x, y, r * 2.2, (accent[0], accent[1], accent[2], 26), power=1.8)
        motes(c, 320, rng, accent, alpha=(12, 50))
        return c

    if layer == 1:
        # Die ferne Hoehlenwand: ein Feld aus Nadeln, das oben und unten
        # ineinandergreift und nach hinten im Dunst verschwindet.
        dunst = mix(far, sky, 0.34)
        tiefer = mix(far, sky, 0.18)
        c.rough_edge(0, 0, W, 18, dunst, seed=61)
        c.rect(0, 0, W, 8, dunst)
        c.rough_edge(0, H - 26, W, 22, dunst, seed=67)
        c.rect(0, H - 8, W, 8, dunst)
        for i in range(22):
            x = i * 24 + int(hash01(i, 3) * 15)
            spire(x, 6, 20 + hash01(i, 9) * 70, 8 + hash01(i, 17) * 16,
                  tiefer if i % 2 else dunst, down=True)
        for i in range(16):
            x = i * 33 + int(hash01(i, 23) * 18)
            spire(x, H - 4, 16 + hash01(i, 29) * 58, 7 + hash01(i, 31) * 14,
                  tiefer if i % 2 else dunst, down=False)
        return c

    if layer == 2:
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

    if layer == 3:
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
        if not OHNE_VERLAUF:
            luftraum(c, [(0.00, hexc("#0d070b")), (0.42, hexc("#1c1016")),
                         (0.76, hexc("#2e1a20")), (1.00, hexc("#43262a"))])
        # Kein Blickfang, kein Licht - nur ein Glimmen tief unten.
        c.glow(256, 300, 200, (accent[0], accent[1], accent[2], 30), power=1.4)
        motes(c, 160, rng, accent, alpha=(8, 30))
        return c

    if layer == 1:
        # Die Ferne: eine Skyline aus abgebrochenen Pfeilern, alle gekippt,
        # keiner ganz. Nur Umriss, kein Detail.
        dunst = mix(far, P.FOREGROUND, 0.20)
        tiefer = mix(far, P.FOREGROUND, 0.34)
        for i in range(20):
            x = i * 27 + int(hash01(i, 5) * 16)
            w = 10 + hash01(i, 13) * 22
            hoehe = 70 + hash01(i, 19) * 170
            lean = (hash01(i, 23) - 0.5) * 0.3
            col_i = tiefer if i % 3 == 0 else dunst
            for y in range(int(hoehe)):
                t = y / hoehe
                ww = w * (0.7 + 0.3 * t)
                c.rect(int(x + lean * y - ww / 2), H - y, max(2, int(ww)), 1, col_i)
        c.rect(0, H - 18, W, 18, tiefer)
        return c

    if layer == 2:
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

    if layer == 3:
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


# ------------------------------------------------------------------ Tempel
#
# Der Schattentempel liegt im Hain und darf trotzdem nicht wie er
# aussehen. Beim ersten Anlauf lieh er sich einfach die Kulisse der
# Kathedrale - das war keine Loesung, sondern eine Abkuerzung, und man
# sah es sofort: dieselben Rosetten, dieselben Boegen, nur dunkler.
#
# Er hat jetzt eine eigene. Sie folgt einer anderen Regel als alle
# anderen Kulissen im Spiel: **kein Himmel, keine Ferne, keine Luft.**
# Wo sonst hinten Licht steht, steht hier eine Wand. Der Blick hat kein
# Entkommen - und das ist das Einzige, was eine Arena vom uebrigen
# Gebiet unterscheiden muss.

def tempel(layer: int) -> Canvas:
    wand = hexc("#12141d")
    stein = hexc("#1b1f2b")
    stein_hi = hexc("#2a3040")
    gold = mix(P.GOLD, wand, 0.55)
    c = Canvas(W, H)
    rng = Rng(9100 + layer * 31)

    if layer == 0:
        # Die Rueckwand. Grosse Quader, und darauf ein Relief: eine
        # Stimmgabel, so hoch wie die Wand, halb abgeschlagen.
        c.dither_v(0, 0, W, H, mix(wand, stein, 0.35), wand, levels=6)
        masonry(c, 0, 0, W, H, wand, course=26, seed=7)

        cx = 256
        for k in (-1, 1):
            # Die zwei Zinken - unten breiter, oben angeschlagen.
            for y in range(40, 190):
                t = (y - 40) / 150
                x = cx + k * (34 - t * 6)
                breite = int(9 - t * 3)
                if k > 0 and y < 96 and hash01(y, 3) > 0.5:
                    continue        # rechts fehlt ein Stueck
                c.rect(int(x - breite / 2), y, breite, 1,
                       mix(stein, gold, 0.10 + t * 0.10))
                c.set(int(x + breite / 2) - 1, y, mix(stein_hi, gold, 0.25))
        c.rect(cx - 40, 188, 80, 14, mix(stein, gold, 0.14))
        for y in range(202, 262):
            t = (y - 202) / 60
            halb = int(11 - t * 4)
            c.rect(cx - halb, y, halb * 2, 1, mix(stein, gold, 0.12))
            c.set(cx + halb - 1, y, mix(stein_hi, gold, 0.2))

        # Fackelnischen: die einzigen Lichter im Raum.
        for x in (74, 438):
            c.rect(x - 7, 96, 14, 34, hexc("#070810"))
            c.glow(x, 118, 26, (255, 196, 120, 34), power=2.2)
            c.ellipse(x, 120, 3.2, 5.0, mix(P.WARM, P.GOLD, 0.4))
        return c

    if layer == 1:
        # Zwischen Wand und Saeulen liegt noch ein Gang. Man sieht ihn
        # nicht als Raum, nur als eine zweite, tiefere Reihe - und genau
        # daran merkt man, dass der Tempel weitergeht.
        col = mix(stein, hexc("#07080e"), 0.55)
        for x in range(-30, W + 40, 68):
            for y in range(52, 232):
                halb = 6 + (y - 52) / 180 * 1.5
                c.rect(int(x - halb), y, int(halb * 2), 1, col)
            c.rect(x - 10, 44, 20, 8, mix(col, stein_hi, 0.14))
            c.rect(x - 11, 232, 22, 8, mix(col, stein_hi, 0.10))
        c.rect(0, 36, W, 8, col)
        c.rect(0, 240, W, 10, col)
        return c

    if layer == 2:
        # Eine Reihe Saeulen, weit hinten, mit Kapitell und Sockel.
        col = mix(stein, wand, 0.35)
        for x in (46, 148, 250, 352, 454):
            for y in range(28, 250):
                t = (y - 28) / 222
                halb = 9 + t * 2
                for px in range(int(x - halb), int(x + halb)):
                    q = (px - x) / halb
                    c.set(px, y, mix(col, stein_hi,
                                     max(0.0, 0.55 - abs(q + 0.35) * 0.7)))
                c.set(int(x - halb), y, hexc("#0a0c14"))
            c.rect(x - 15, 20, 30, 10, mix(col, stein_hi, 0.25))
            c.rect(x - 13, 30, 26, 4, col)
            c.rect(x - 16, 250, 32, 12, mix(col, stein_hi, 0.18))
        # Ein durchlaufendes Gesims darueber.
        c.rect(0, 8, W, 12, mix(col, stein_hi, 0.3))
        c.rect(0, 20, W, 3, hexc("#0a0c14"))
        return c

    if layer == 3:
        # Nahe Saeulen: nur zwei, dafuer schwer. Sie rahmen das Bild.
        col = mix(stein, hexc("#05060c"), 0.45)
        for x in (18, 494):
            for y in range(0, H):
                halb = 26 + (y / H) * 5
                for px in range(int(x - halb), int(x + halb)):
                    q = (px - x) / halb
                    c.set(px, y, mix(col, stein_hi,
                                     max(0.0, 0.4 - abs(q + 0.3) * 0.55)))
            c.rect(int(x - 34), 0, 68, 22, mix(col, stein_hi, 0.16))
        # Ketten mit Schalen, die von der Decke haengen.
        for x, laenge in ((150, 74), (362, 52)):
            c.chain(x, 0, laenge, mix(col, stein_hi, 0.3), link=6)
            c.ellipse(x, laenge + 6, 9, 4.4, mix(col, stein_hi, 0.22))
            c.glow(x, laenge + 4, 16, (255, 196, 120, 26), power=2.0)
        return c

    return c


# --------------------------------------------------------------------- Bau

BUILDERS = {"hain": hain, "kathedrale": kathedrale,
            "grotten": grotten, "dissonanz": dissonanz}


def in_dunst(c: Canvas, hoehe: int = 72) -> Canvas:
    """
    Loest die oberen Reihen einer Schicht in Luft auf.

    Die Schichten sind genau bildschirmhoch. In einem Raum, der hoeher
    ist, endeten sie mitten in der Luft - eine harte Kante quer durchs
    Bild. Der erste Versuch, die oberste Zeile nach oben zu strecken,
    machte daraus lange senkrechte Schlieren, also nur eine andere Art
    Fehler.

    Die Loesung ist keine technische, sondern eine malerische: eine
    Schicht darf oben gar nicht aufhoeren. Sie verliert nach oben ihre
    Deckkraft und verschwindet im Dunst, und was darueber steht, ist
    Himmel - so wie ein Wald sich nach oben eben in Nebel verliert. Damit
    ist es voellig gleich, wie hoch der Raum ist.
    """
    for y in range(min(hoehe, c.h)):
        t = y / hoehe                       # 0 ganz oben .. 1 unten
        f = t * t * (3 - 2 * t)             # weich anlaufen, weich enden
        for x in range(c.w):
            r, g, b, a = c.get(x, y)
            if a:
                c.set(x, y, (r, g, b, int(a * f)))
    return c


def dunstverlauf(himmel: Canvas) -> list[tuple[int, int, int]]:
    """
    Der Dunst einer Kulisse: pro Bildzeile ein Wert, waagerecht der Median.

    Nicht dasselbe wie der Himmel. Im Himmel stehen Mond, Lichtbalken und
    Staub, und die gehoeren *nicht* in den Dunst - sonst passiert genau
    das, was hier passiert ist: die Ferne wurde zur Himmelsfarbe an
    derselben Stelle hin gemischt, und weil dort der Mond steht, trug
    jede Schicht seine bleiche Scheibe mit sich herum. Man sah ihn dann
    dreimal, einmal pro Schicht, mitten auf den Staemmen.

    Luft ist waagerecht gleich. Nur der Verlauf von oben nach unten
    zaehlt, und den bekommt man, indem man jede Zeile ueber ihre ganze
    Breite mittelt.
    """
    verlauf = []
    for y in range(himmel.h):
        zeile = [himmel.get(x, y) for x in range(himmel.w)]
        zeile = [px for px in zeile if px[3]]
        if not zeile:
            verlauf.append((0, 0, 0))
            continue
        # Median, nicht Mittelwert. Der Mond ist heller als alles andere;
        # gemittelt hebt er die Zeilen an, in denen er steht, und dann
        # laeuft ein heller Balken quer durch jede Schicht davor.
        mitte = len(zeile) // 2
        verlauf.append(tuple(sorted(px[k] for px in zeile)[mitte]
                             for k in range(3)))

    # Und dann senkrecht glaetten. Der Verlauf ist gerastert gezeichnet,
    # also springen benachbarte Zeilen zwischen zwei Werten hin und her.
    # Der Median greift einen davon heraus, und wenn dieser Streifen
    # nachher ueber die ganze Raumhoehe gedehnt wird, werden aus dem
    # Sprung waagerechte Balken quer durchs Bild.
    weich = []
    for y in range(len(verlauf)):
        fenster = verlauf[max(0, y - 4):y + 5]
        weich.append(tuple(sum(f[k] for f in fenster) // len(fenster)
                           for k in range(3)))
    return weich


def in_ferne(bild: Canvas, verlauf, menge: float) -> Canvas:
    """
    Zieht eine Schicht in die Ferne, indem sie ihre Farbe zum Dunst hin
    verschiebt - nicht ihre Deckkraft.

    Das war ein echter Fehler und kein Geschmack: die Schichten wurden
    beim Zeichnen halbdurchsichtig gestellt, damit sie zurueckfallen.
    Halbdurchsichtig heisst aber *durchsichtig*, und dann sieht man den
    Mond durch den Baumstamm. Ein Baum vor dem Mond verdeckt ihn. Was in
    der Ferne mit einer Form passiert, ist etwas anderes: sie verliert
    Kontrast, weil Luft dazwischen steht - sie wird heller und faerbt
    sich zum Dunst hin. Genau das macht diese Funktion, und die Schicht
    bleibt dabei deckend.
    """
    for y in range(bild.h):
        # Der Verlauf ist bildschirmhoch, die Schicht kann hoeher sein.
        # Abgetastet wird darum ueber den Anteil, nicht ueber die Zeile.
        hr, hg, hb = verlauf[min(len(verlauf) - 1,
                                 int(y / max(1, bild.h - 1) * (len(verlauf) - 1)))]
        for x in range(bild.w):
            r, g, b, a = bild.get(x, y)
            if not a:
                continue
            bild.set(x, y, (int(r + (hr - r) * menge),
                            int(g + (hg - g) * menge),
                            int(b + (hb - b) * menge), a))
    return bild


# Wie weit jede Schicht in die Luft zurueckfaellt. Schicht 0 ist die Luft
# selbst.
FERNE = [0.0, 0.68, 0.46, 0.24]


def himmelsstreifen(verlauf) -> Canvas:
    """
    Der Himmelsverlauf als schmaler, dehnbarer Streifen.

    Er liegt hinter allem und wird auf die volle Raumhoehe gezogen. Damit
    ist es voellig gleich, wie hoch ein Raum ist - vorher stand ueber dem
    oberen Rand der Kulisse eine einzelne Flaeche, und die traf deren
    Farbe nur an einem Ende.
    """
    c = Canvas(8, len(verlauf))
    for y, (r, g, b) in enumerate(verlauf):
        c.rect(0, y, 8, 1, (r, g, b, 255))
    return c


def build() -> None:
    global OHNE_VERLAUF
    atlas = Atlas("backdrops", padding=2, max_width=512)
    for region in REGIONS:
        verlauf = dunstverlauf(BUILDERS[region](0))
        atlas.add(f"{region}_himmel", himmelsstreifen(verlauf), pivot=(0, 0))

        OHNE_VERLAUF = True
        luft = BUILDERS[region](0)
        OHNE_VERLAUF = False

        for layer in range(SCHICHTEN):
            bild = luft if layer == 0 else BUILDERS[region](layer)
            # Die ferne Wand deckt die volle Raumhoehe ab, nicht nur den
            # Bildschirm - sonst steht ueber ihr in hohen Raeumen nichts
            # als Himmel.
            if layer == 1:
                bild = hochgezogen(bild, HOCH)
            # Der Himmel selbst bleibt deckend - hinter ihm liegt nichts
            # mehr, was durchscheinen koennte.
            if layer > 0:
                bild = in_dunst(in_ferne(bild, verlauf, FERNE[layer]),
                                52 + layer * 20)
            atlas.add(f"{region}_bg{layer}", bild, pivot=(0, 0),
                      parallax=PARALLAX[layer])
        atlas.add(f"{region}_fg", in_dunst(foreground(region), 56),
                  pivot=(0, 0), parallax=PARALLAX_VORN)

    # Der Tempel ist keine Region, aber eine Kulisse. Er bekommt keinen
    # Dunst nach oben: hinter ihm ist Wand, kein Himmel, und eine Wand
    # loest sich nicht auf.
    wand = tempel(0)
    wand_verlauf = dunstverlauf(wand)
    atlas.add("tempel_himmel", himmelsstreifen(wand_verlauf), pivot=(0, 0))
    for layer in range(SCHICHTEN):
        bild = wand if layer == 0 else in_ferne(tempel(layer), wand_verlauf,
                                                FERNE[layer] * 0.7)
        atlas.add(f"tempel_bg{layer}", bild, pivot=(0, 0),
                  parallax=PARALLAX[layer])
    atlas.add("tempel_fg", in_dunst(foreground("kathedrale"), 40),
              pivot=(0, 0), parallax=PARALLAX_VORN)
    png, js = atlas.write(OUT)
    print(f"backdrops  -> {png.name} ({len(atlas.frames)} Frames)")


if __name__ == "__main__":
    build()
