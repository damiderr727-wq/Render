"""
Erzeugt den Charakter-Atlas: Cadence (die Heldin), die Kreaturen der
verstimmten Welt und den Kantor.

Alle Figuren werden parametrisch gezeichnet - eine Pose ist eine Handvoll
Zahlen, kein handgemaltes Bild. Dadurch lassen sich Animationen aus
Formeln erzeugen und Silhouetten global nachziehen.
"""

from __future__ import annotations

import math
from pathlib import Path

from pixelkit import Atlas, Canvas, Palette as P, Rng, hash01, hexc, mix, shade

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Atlas"

# Die Leinwand ist breiter als die Gestalt: ein Cape braucht Platz
# neben ihr, sonst schneidet der Rahmen es ab.
# Die Groesse der Figur an einer Stelle. Alles andere leitet sich davon ab,
# damit man sie im Ganzen groesser oder kleiner ziehen kann, ohne dass die
# Verhaeltnisse auseinanderlaufen.
HERO_SCALE = 1.3
HERO_W, HERO_H = int(round(28 * HERO_SCALE)), int(round(30 * HERO_SCALE))
BODY_H = 20.0 * HERO_SCALE

# Wo die Flamme aufhoert und die Beine anfangen, als Anteil der Hoehe.
# Darunter ist sie fest, darueber loest sie sich auf - der Uebergang ist
# das Interessanteste an ihr.
LEG_T = 0.32
GROUND = HERO_H - 1  # unterste Pixelzeile = Fussboden


# ------------------------------------------------------------------ Heldin
#
# Cadence hat keinen Koerper, sie hat eine Gestalt.
#
# Vorher stand hier eine Figur mit Maske, Umhang und Beinen - und jeder
# Anlauf lief auf etwas Bekanntes hinaus. Der Grund lag nicht in den
# Pixeln: eine Heldin in einer Welt aus Klang muss nicht aussehen wie
# jemand, der Klang benutzt. Sie ist selbst welcher.
#
# Also: eine flammenartige Masse, die nach oben ausfranst und unten den
# Boden kaum beruehrt. Kein Gesicht, keine Glieder - dafuer ein einziger
# harter Gegenstand darin, eine Stimmgabel, die halb in ihr steckt. Sie
# ist das, was die Gestalt zusammenhaelt, und das Einzige an ihr, das eine
# Kante hat.
#
# Das Instrument verformt sie: die Leier zieht sie lang, die Trommel
# druckt sie breit und schwer, die Floete spitzt sie zu. Man sieht also
# an ihrer Silhouette, womit sie gerade spielt.

def _profile(t: float, instrument: str) -> float:
    """
    Breite der Gestalt an der Stelle `t` (0 unten, 1 oben).

    Eine Flamme ist unten schmal, hat tief unten ihren Bauch und laeuft
    oben spitz aus. Das Instrument verschiebt diesen Bauch.
    """
    if instrument == "trommel":
        a, low, high = 12.0, 0.30, 0.85    # schwer, breiter Bauch tief unten
    elif instrument == "floete":
        a, low, high = 7.2, 0.55, 0.40     # schmal, hoch, spitz
    elif instrument == "leier":
        a, low, high = 9.4, 0.38, 0.60     # ausgewogen
    elif instrument == "glocke":
        a, low, high = 11.4, 0.28, 0.90    # schwer, sitzt tief
    elif instrument == "orgelpfeife":
        a, low, high = 6.8, 0.60, 0.34     # sehr schlank, sehr hoch
    elif instrument == "metronom":
        a, low, high = 8.2, 0.44, 0.58     # aufrecht, schmal
    else:
        a, low, high = 8.6, 0.42, 0.55     # Stimmgabel: schlank, unauffaellig
    return a * ((t * 1.1 + 0.06) ** low) * ((1 - t) ** high)


# --------------------------------------------------------------- Fassungen
#
# Die Kleidung ist kein Kostuem, sie ist ein Gefaess.
#
# Cadence wuerde sich ohne sie zerstreuen - der Mantel ist das, was sie
# beisammenhaelt. Deshalb darf er nicht steif auf ihr liegen: er hat keine
# eigene Form, er nimmt ihre an. Gezeichnet wird er darum aus demselben
# Profil wie die Gestalt, nur eine Spur weiter - und mit Verzoegerung. Der
# Saum folgt der Neigung eine Spur spaeter als der Koerper, weht beim Lauf
# nach hinten aus und schwingt nach, wenn sie stehenbleibt.
#
# Die Oeffnungen sind dieselben wie im Spielwert: wo der Stoff eine Luecke
# hat, tritt ihr Licht heraus. Eine Fassung mit einer einzigen Oeffnung ist
# fast geschlossen; ein gerissenes Gewand ist mehr Schlitz als Stoff.

GARMENTS = {
    # Ohne alles. Das ist sie selbst - und genau das zeigt das Inventar,
    # damit man sieht, wie weit sie schon ist.
    "ohne": dict(openings=0, cut="keins", deckung=0.0,
                 stoff=P.CLOAK, licht=P.TRIM),
    # Der Schnitt bestimmt die Silhouette, die Oeffnungen den Spielwert.
    #
    #   mantel   - lose, faellt weit, laeuft dem Koerper hinterher
    #   harnisch - starr, geschlossen, laesst nur den Kopf frei
    #   cape     - haengt nur an der Schulter und schwirrt umher
    "mantel": dict(
        openings=4, cut="mantel", deckung=0.66,
        stoff=mix(P.CLOAK, P.STONE, 0.55), licht=P.TRIM),
    "cape": dict(
        openings=6, cut="cape", deckung=0.72,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.5), P.BLOOM, 0.16), licht=P.BLOOM),
    "enge_fassung": dict(
        openings=1, cut="harnisch", deckung=0.70,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.5), P.GOLD, 0.20), licht=P.GOLD),
    "offene_fassung": dict(
        openings=9, cut="mantel", deckung=0.58,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.6), P.TRIM, 0.16), licht=P.TRIM),
    "schlagfassung": dict(
        openings=2, cut="harnisch", deckung=0.66,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.5), P.ROT, 0.20), licht=P.ROT),
    "gerissenes_gewand": dict(
        openings=14, cut="cape", deckung=0.60,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.6), P.WARM, 0.14), licht=P.AMBER),
    "chorpanzer": dict(
        openings=3, cut="harnisch", deckung=0.68,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.6), P.STONE_HI, 0.30), licht=P.TRIM),
    "pfeifenharnisch": dict(
        openings=1, cut="harnisch", deckung=0.72,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.5), P.BILE, 0.16), licht=P.WARM),
    "flimmerhemd": dict(
        openings=12, cut="mantel", deckung=0.60,
        stoff=mix(mix(P.CLOAK, P.STONE, 0.55), P.BLOOM, 0.20), licht=P.BLOOM),
    # Der Bruch: kein Gefaess mehr, nur noch Fetzen an ihr. Was bleibt,
    # traegt nichts - es haengt nur noch dran.
    "bruch": dict(
        openings=99, cut="bruch", deckung=0.42,
        stoff=mix(mix(P.CLOAK, P.ROT, 0.30), P.AMBER, 0.10), licht=P.AMBER),
}


def _garment_slits(openings: int) -> list[tuple[float, int, float]]:
    """
    Verteilt die Oeffnungen ueber die Hoehe des Stoffs.

    Rueckgabe je Oeffnung: Hoehe (0 Saum .. 1 Kragen), Seite (-1/1), Laenge.
    Die erste zeigt immer nach vorn - dorthin, wohin auch der Fernklang
    geht. Danach wechseln sie die Seite, damit das Gewand nicht auf einer
    Seite ausfranst und auf der anderen zu bleibt.
    """
    out = []
    for i in range(openings):
        u = 0.10 + (i + 0.5) / openings * 0.80
        seite = 1 if i % 2 == 0 else -1
        # Wenige Oeffnungen: lange Schlitze. Viele: kurze Risse.
        laenge = min(0.24, 0.07 + 0.22 / openings)
        out.append((u, seite, laenge))
    return out




# ------------------------------------------------------------------- Kerne
#
# Der Kern ist das Ding, das in ihr steckt - der einzige harte Gegenstand an
# ihr und der Grund, warum sie ueberhaupt eine Gestalt hat. Er ist
# austauschbar: die Stimmgabel ist nur der erste, den sie findet.
#
# Gezeichnet wird er immer nach derselben Regel: der Fuss verliert sich
# unten in der Masse, der Koerper liegt in ihr, und nur das obere Ende steht
# frei heraus. So sitzt er *in* ihr und nicht *auf* ihr - egal welcher.



def _draw_arme(c: Canvas, *, cx: int, base: float, height: float, phase: float,
               lean: float, leg_phase: float | None, arm_front: float,
               arm_back: float, whip: float, smear: float) -> None:
    """
    Zwei Spitzen als Arme.

    Dieselbe Regel wie unten: kein Oberarm, kein Ellbogen, keine Hand -
    zwei duenne Nadeln, die aus der Flamme herauswachsen und spitz enden.
    Der vordere greift, der hintere zieht nach; im Lauf pendeln sie
    gegenlaeufig zu den Beinen, sonst haengen sie fast still.
    """
    S = HERO_SCALE
    schulter_t = 0.56
    sy = base - schulter_t * height
    laenge = height * 0.30

    schritt = (leg_phase or 0.0) + math.pi
    ader = mix(P.TRIM, P.BONE, 0.55)
    schale = mix(P.CLOAK, P.STONE, 0.22)

    for seite in (-1, 1):
        vorn = seite > 0
        takt = math.sin(schritt + (0 if vorn else math.pi))
        # Ruhe: leicht nach hinten unten. Schlag: nach vorn gerissen.
        winkel = (0.95 - takt * 0.38
                  - (arm_front if vorn else arm_back) * 1.3
                  - whip * 0.9)
        sx = cx + seite * (1.4 * S) + lean * 0.6

        n = max(3, int(laenge))
        for i in range(n + 1):
            v = i / n
            x = sx + seite * math.cos(winkel) * laenge * v - smear * 2.4 * v
            y = sy + math.sin(winkel) * laenge * v
            w = 1.2 - 1.15 * v ** 0.6
            for dx in range(-int(w) - 1, int(w) + 2):
                if abs(dx) > w + 0.35:
                    continue
                col = (mix(schale, ader, 0.45 - 0.22 * v) if dx * seite > 0
                       else shade(schale, -0.28))
                c.set(int(x) + dx, int(y), col)
        c.set(int(sx + seite * math.cos(winkel) * laenge),
              int(sy + math.sin(winkel) * laenge), mix(schale, ader, 0.35))


def _draw_klinge(c: Canvas, *, cx: int, base: float, height: float, phase: float,
                 lean: float, sway: float) -> None:
    """
    Die Schallklinge auf ihrem Ruecken.

    Sie ist das einzige Rosa an ihr - und das mit Absicht: alles andere ist
    kalt und blass, also traegt genau ein Gegenstand die Gegenfarbe, und
    man sieht schon an der Silhouette, dass sie bewaffnet ist. Kristall,
    nicht Metall: die Klinge ist gewachsen wie die Nadeln, an denen sie
    geht.
    """
    S = HERO_SCALE
    # Etwas dunkler als ihre Augen: die Klinge ist rosa, aber sie ist nicht
    # das Erste, was man ansieht.
    rosa = mix(hexc("#ff7ad0"), P.CLOAK, 0.22)
    rosa_hi = mix(rosa, P.BONE, 0.45)
    rosa_lo = mix(rosa, P.CLOAK, 0.55)

    # Schraeg ueber den Ruecken: Griff unten rechts, Spitze oben links.
    # Die Stimmgabel steht nach oben rechts - die Klinge muss in die
    # Gegenrichtung, sonst kreuzen sich beide zu einem Gestruepp.
    a = -(math.pi - 1.00)
    mx = cx + 0.8 * S + lean * 0.3
    my = base - 0.42 * height
    ax, ay = math.cos(a), math.sin(a)
    laenge = height * 0.62

    # Griff und Parierstueck
    for i in range(int(3 * S)):
        c.set(int(mx - ax * (i + 2)), int(my - ay * (i + 2)), mix(rosa_lo, P.CLOAK, 0.4))
    for k in (-1, 1):
        c.set(int(mx - ax * 1.5 - ay * k), int(my - ay * 1.5 + ax * k), rosa_lo)

    # Das Blatt: zum Ende hin schmaler, mit heller Schneide vorn.
    for i in range(int(laenge)):
        v = i / laenge
        w = (1.9 - 1.5 * v ** 0.8) * S
        px = mx + ax * i
        py = my + ay * i
        for dq in range(-int(w), int(w) + 1):
            qx = px - ay * dq
            qy = py + ax * dq
            if dq > 0:
                col = rosa_hi if dq >= int(w) else rosa
            else:
                col = rosa_lo
            c.set(int(qx), int(qy), col)
        # Ein Glanz laeuft die Schneide hinauf.
        if abs(v - (0.5 + 0.5 * math.sin(phase * 1.4 + sway))) < 0.10:
            c.set(int(px - ay * w), int(py + ax * w), mix(rosa_hi, P.BONE, 0.6))

    c.set(int(mx + ax * laenge), int(my + ay * laenge), mix(rosa_hi, P.BONE, 0.4))
    c.glow(mx + ax * laenge * 0.6, my + ay * laenge * 0.6, 6 * S,
           (rosa[0], rosa[1], rosa[2], 40))


def _draw_beine(c: Canvas, *, cx: int, base: float, height: float, phase: float,
                lean: float, leg_phase: float | None, leg_spread: float,
                crouch: float, settle: float, smear: float) -> None:
    """
    Zwei Spitzen, keine Beine.

    Der Klang hat sich unten abgesetzt und ist zu Kristall erstarrt - und
    zwar zu zwei duennen, spitz zulaufenden Nadeln, auf denen sie steht.
    Kein Oberschenkel, keine Wade, kein Fuss: das waere Anatomie, und
    Anatomie hat sie nicht. Sie beruehrt den Boden an genau zwei Punkten.

    `leg_phase` treibt den Schritt. Ohne sie stehen beide still.
    """
    S = HERO_SCALE
    laenge = height * LEG_T - settle * 0.4
    if laenge < 3:
        return

    schritt = leg_phase or 0.0
    ader = mix(P.TRIM, P.BONE, 0.55)
    schale = mix(P.CLOAK, P.STONE, 0.22)
    hueft_y = base - laenge

    for seite in (-1, 1):
        takt = math.sin(schritt + (0 if seite > 0 else math.pi))
        heben = max(0.0, takt) * laenge * 0.40
        vor = takt * (1.8 + abs(lean) * 0.6) * S

        hx = cx + seite * (1.3 * S + leg_spread * 1.3) + lean * 0.35
        sx = hx + vor
        sy = base - heben - crouch * 2

        n = max(3, int(laenge))
        for i in range(n + 1):
            v = i / n                                   # 0 oben .. 1 Spitze
            x = hx + (sx - hx) * v ** 1.25 - smear * 3.0 * v
            y = hueft_y + (sy - hueft_y) * v
            # Sie laeuft wirklich spitz aus: oben zwei Pixel, unten einer.
            w = 1.4 - 1.35 * v ** 0.55
            for dx in range(-int(w) - 1, int(w) + 2):
                if abs(dx) > w + 0.35:
                    continue
                # Die Nadel ist dunkel, ihre Vorderkante faengt Licht.
                if dx * seite > 0:
                    col = mix(schale, ader, 0.35 - 0.20 * v)
                else:
                    col = shade(schale, -0.30)
                c.set(int(x) + dx, int(y), col)
            # Ein Glanzpunkt wandert die Nadel hinab - der Ton laeuft
            # sichtbar durch den Kristall.
            if abs(v - (0.5 + 0.5 * math.sin(phase * 1.8 - seite))) < 0.14:
                c.set(int(x), int(y), ader)

        # Die Spitze laeuft aus. Ein heller Punkt am Ende sieht aus wie ein
        # Fuss, und einen Fuss hat sie nicht.
        c.set(int(sx), int(sy), mix(schale, ader, 0.30))

    # Wo die Flamme in den Kristall uebergeht, glimmt die Naht.
    for dx in range(-int(2.6 * S), int(2.6 * S) + 1):
        if hash01(cx + dx, int(hueft_y) + int(phase * 3)) > 0.5:
            c.set(cx + dx + int(lean * 0.3), int(hueft_y), mix(ader, P.AMBER, 0.2))


def _draw_kern(c: Canvas, *, kern: str, cx: int, base: float, height: float,
               phase: float, lean: float, glow: float, mid) -> None:
    """
    Der Kern in ihr - nach einer Regel, die fuer alle gilt.

    Der erste Anlauf zeichnete jeden Kern als das, was er ist: eine Glocke
    war eine Glocke, ein Metronom ein Metronom. Das sah aus wie Spielzeug,
    das sie mit sich herumtraegt, und hatte keinen Gedanken dahinter.

    Die Regel lautet jetzt:

    1. **Es ist immer eine Scherbe, nie ein Gegenstand.** Nichts davon ist
       heil. Ein Stueck Glockenrand, der Arm eines Metronoms ohne Kasten,
       das Mundstueck einer Pfeife ohne Pfeife. Halb in ihr, an der
       Bruchkante rau.
    2. **Man sieht nicht die Form, sondern den Klang.** Ueber jeder Scherbe
       steht ihre Signatur aus Licht: Ringe bei der Glocke, eine stehende
       Luftsaeule bei der Orgelpfeife, die Bahn des Arms beim Metronom. Das
       ist der eigentliche Gegenstand - die Scherbe ist nur, was davon
       uebrig ist.
    3. **Hart und dunkel unten, weich und hell oben.** Die Scherbe hat
       Kanten, die Signatur hat keine.

    Damit sieht man einem Kern an, wie er klingt, bevor man ihn benutzt -
    und alle sieben gehoeren sichtbar zusammen.
    """
    S = HERO_SCALE
    t = 0.52
    fy = base - t * height
    fx = cx + lean * t + math.sin(t * 2.6 + phase) * 1.2

    # Die Scherbe muss sich gegen die Flamme durchsetzen, in der sie steckt.
    # Deshalb hell mit dunkler Fuge darunter - nicht dunkel: dunkel geht in
    # der hellen Masse unter.
    scherbe = P.BONE_SH
    scherbe_hi = mix(P.BONE, (255, 255, 255, 255), 0.35)
    schatten = mix(P.CLOAK, P.INK, 0.5)
    bruch = mix(P.BONE_LO, mid, 0.55)
    licht = {"stimmgabel": P.AMBER, "leier": P.TRIM, "trommel": P.GOLD,
             "floete": P.BLOOM, "metronom": P.WARM, "glocke": P.GOLD,
             "orgelpfeife": P.TRIM}.get(kern, P.AMBER)
    p = 0.5 + 0.5 * math.sin(phase * 1.8)

    def strahl(x: float, y: float, a: int) -> None:
        # Alles, was ueber den Rahmen hinausgeht, wird abgeschnitten - sonst
        # klebt ein Strahl am oberen Bildrand fest und wandert beim
        # Zeichnen in den Nachbarrahmen.
        xi, yi = int(x), int(y)
        if 0 <= xi < c.w and 1 <= yi < c.h - 1:
            c.blend(xi, yi, (licht[0], licht[1], licht[2], max(0, min(255, a))))

    def kante(x: float, y: float) -> None:
        """Eine dunkle Fuge unter der Scherbe, damit sie sich abhebt."""
        xi, yi = int(x), int(y) + 1
        if 0 <= xi < c.w and 0 <= yi < c.h:
            c.blend(xi, yi, (schatten[0], schatten[1], schatten[2], 190))

    # --- Die Scherbe ------------------------------------------------------
    if kern == "stimmgabel":
        # Zwei Zinken, einer abgebrochen, quer zur Koerperachse.
        a = -1.16 + lean * 0.03
        ax, ay = math.cos(a), math.sin(a)
        nx, ny = -ay, ax
        for i in range(int(4 * S)):
            c.set(int(fx - ax * i), int(fy - ay * i), scherbe if i else scherbe_hi)
        for k in range(-2, 3):
            c.set(int(fx + nx * k), int(fy + ny * k),
                  scherbe_hi if abs(k) < 2 else scherbe)
        for seite, laenge in ((1, int(height * 0.34)), (-1, int(height * 0.17))):
            for i in range(laenge):
                px = fx + nx * seite * 1.7 * S + ax * i
                py = fy + ny * seite * 1.7 * S + ay * i
                c.set(int(px), int(py), scherbe_hi if i % 4 else scherbe)
            if seite < 0:
                c.set(int(fx + nx * seite * 1.7 * S + ax * laenge),
                      int(fy + ny * seite * 1.7 * S + ay * laenge), bruch)
        # Signatur: der Ton steht als schmales Band zwischen den Zinken.
        for i in range(int(height * 0.30)):
            v = i / (height * 0.30)
            strahl(fx + ax * i + nx * 0.6, fy + ay * i + ny * 0.6,
                   int(150 * (1 - v) * (0.5 + 0.5 * p)))

    elif kern == "leier":
        # Ein Arm mit drei Saiten, am unteren Ende abgerissen.
        bogen = int(9 * S)
        for i in range(bogen):
            v = i / bogen
            x = fx - 2.6 * S + math.sin(v * 1.3) * 2.4 * S
            c.set(int(x), int(fy - 1 - i), scherbe_hi if i % 3 else scherbe)
        c.set(int(fx - 2.6 * S), int(fy), bruch)
        c.rect(int(fx - 3 * S), int(fy - 1), int(5 * S), 1, scherbe)
        # Signatur: drei Saiten, die im Takt schwingen.
        for k in range(3):
            sx = fx - 1.0 * S + k * 1.5 * S
            for i in range(int(8 * S)):
                v = i / (8 * S)
                aus = math.sin(phase * 3 + k * 2.1 + v * 6) * (1 - abs(v - 0.5) * 2) * 1.6
                strahl(sx + aus, fy - 2 - i, int(210 * (1 - v * 0.5)))

    elif kern == "trommel":
        # Ein Stueck Reifen, quer durch sie hindurch. Kein ganzer Ring.
        for i in range(-int(5 * S), int(5 * S) + 1):
            dy = int(abs(i) ** 1.7 / (5 * S) ** 1.7 * 3 * S)
            c.set(int(fx + i), int(fy - 2 * S + dy), scherbe_hi)
            c.set(int(fx + i), int(fy - 2 * S + dy + 1), scherbe)
            kante(fx + i, fy - 2 * S + dy + 1)
        c.set(int(fx - 5 * S), int(fy - 2 * S + int(3 * S)), bruch)
        # Signatur: Druckringe, die sich waagerecht ausbreiten.
        for k in range(3):
            r = (2 + k * 2.6 + p * 2.4) * S
            for i in range(20):
                a = i / 20 * math.tau
                strahl(fx + math.cos(a) * r * 1.5, fy - 2 * S + math.sin(a) * r * 0.55,
                       int(120 * (1 - k / 3) * (1 - p * 0.4)))

    elif kern == "floete":
        # Ein Rohrstueck mit zwei Loechern, schraeg abgebrochen.
        laenge = int(9 * S)
        for i in range(laenge):
            x = int(fx + i * 0.16)
            c.set(x, int(fy - 1 - i), scherbe_hi if i % 5 else scherbe)
            c.set(x + 1, int(fy - 1 - i), scherbe)
            kante(x + 1, fy - 1 - i)
            if i in (int(3 * S), int(6 * S)):
                c.set(x, int(fy - 1 - i), bruch)
        c.set(int(fx), int(fy), bruch)
        # Signatur: ein einziger gerader Strahl nach oben. Kurz genug, dass
        # er im Rahmen bleibt - sonst haengt er oben fest.
        strecke = min(height * 0.16, max(0.0, fy - laenge - 5))
        for i in range(max(0, int(strecke))):
            v = i / max(1.0, strecke)
            if (i + int(phase * 6)) % 3:
                strahl(fx + laenge * 0.16, fy - 2 - laenge - i, int(200 * (1 - v)))

    elif kern == "metronom":
        # Kein Kasten, kein Gehaeuse: nur der Arm mit dem Gewicht, der in
        # ihr steckt. Der Kasten ist das, was fehlt.
        a = -math.pi / 2 + math.sin(phase * 2.2) * 0.60
        laenge = int(10 * S)
        for i in range(laenge):
            c.set(int(fx + math.cos(a) * i), int(fy - 1 + math.sin(a) * i),
                  scherbe_hi if i % 4 else scherbe)
        gx = int(fx + math.cos(a) * laenge * 0.78)
        gy = int(fy - 1 + math.sin(a) * laenge * 0.78)
        c.rect(gx - 1, gy, 3, 2, scherbe_hi)
        c.set(int(fx), int(fy), bruch)
        # Signatur: die Bahn, die er schon gegangen ist - ein Bogen aus
        # Nachbildern. Man sieht den Takt, nicht das Geraet.
        for k in range(9):
            aa = -math.pi / 2 + (-0.60 + k * 0.15)
            naehe = 1 - abs(aa - a) / 0.7
            for i in range(int(4 * S), laenge):
                strahl(fx + math.cos(aa) * i, fy - 1 + math.sin(aa) * i,
                       int(90 * max(0.0, naehe) ** 2))

    elif kern == "glocke":
        # Nur der Rand einer Glocke - ein Bogen, mehr nicht. Der Kloeppel
        # haengt frei darunter und schwingt nach.
        for i in range(-int(5 * S), int(5 * S) + 1):
            v = abs(i) / (5 * S)
            y = fy - 4 * S + v ** 1.8 * 4 * S
            c.set(int(fx + i), int(y), scherbe_hi)
            c.set(int(fx + i), int(y + 1), scherbe)
            kante(fx + i, y + 1)
        for seite in (-1, 1):
            c.set(int(fx + seite * 5 * S), int(fy), bruch)
        kx = fx + math.sin(phase * 1.2) * 2.4 * S
        c.set(int(kx), int(fy - 2 * S), scherbe)
        c.set(int(kx), int(fy - 2 * S + 1), scherbe_hi)
        # Signatur: Ringe, die weit ueber sie hinausgehen. Das ist die
        # Aura - eine Glocke ist der Hall, nicht das Metall.
        for k in range(4):
            r = ((k * 3.2 + p * 3.2) % 12.8 + 2) * S
            a0 = int(110 * (1 - r / (13 * S)))
            for i in range(26):
                a = i / 26 * math.tau
                strahl(fx + math.cos(a) * r, fy - 4 * S + math.sin(a) * r * 0.82, a0)

    elif kern == "orgelpfeife":
        # Das Mundstueck einer Pfeife, kurz abgebrochen. Die Pfeife selbst
        # ist nicht mehr da - sie steht als Luftsaeule darueber.
        fuss = int(5 * S)
        for i in range(fuss):
            for dx in (-1, 0, 1):
                c.set(int(fx + dx * S), int(fy - i),
                      scherbe_hi if dx == 0 else scherbe)
        for dx in range(-int(1.6 * S), int(1.8 * S)):
            kante(fx + dx, fy - fuss)
        c.rect(int(fx - 1.6 * S), int(fy - fuss), int(3.4 * S), 1, scherbe_hi)
        c.rect(int(fx - 1.2 * S), int(fy - fuss + 1), int(2.6 * S), 1, bruch)
        c.set(int(fx), int(fy + 1), bruch)
        # Signatur: eine stehende Luftsaeule. Drei Baeuche, die wandern -
        # das ist die Orgel, nicht das Rohr.
        hoehe = height * 0.42
        for i in range(int(hoehe)):
            v = i / hoehe
            bauch = abs(math.sin(v * math.pi * 3 - phase * 1.6))
            breite = (0.6 + bauch * 2.6) * S
            for dx in range(-int(breite), int(breite) + 1):
                rand = abs(dx) >= int(breite) - 0
                strahl(fx + dx, fy - fuss - 1 - i,
                       int((150 if rand else 55) * (1 - v * 0.75)))

    if glow > 0:
        c.glow(fx, fy - 2 * S, 9 * S,
               (licht[0], licht[1], licht[2], int((70 + 60 * p) * glow)))


def _draw_garment(c: Canvas, *, garment: str, kind: str, cx: int, base: float,
                  height: float, phase: float, lean: float, smear: float,
                  split: float, sway: float, hinter: bool) -> float:
    """
    Zeichnet die getragene Fassung ueber die Gestalt.

    Der Stoff bekommt kein eigenes Skelett: er laeuft ueber dasselbe
    Rueckgrat wie die Gestalt, nur verzoegert. Unten haengt er am weitesten
    hinterher, oben sitzt er fast auf - dadurch folgt er jeder Bewegung,
    ohne dass eine Pose von Hand gesetzt waere.

    Drei Schnitte, und der Schnitt entscheidet ueber alles Weitere:

      mantel    Lose. Faellt weit ueber den Bauch der Gestalt hinaus,
                schwingt nach und weht beim Lauf hinter ihr her.
      harnisch  Starr. Liegt eng an, in waagerechten Schienen, und laesst
                nur den Kopf frei. Er schwingt nicht - er ist Metall.
      cape      Haengt nur an der Schulter. Der Koerper bleibt frei, das
                Tuch schwirrt hinter ihr umher und faengt jeden Sprung.
    """
    g = GARMENTS.get(garment, GARMENTS["mantel"])
    openings, cut, coverage = g["openings"], g["cut"], g["deckung"]
    stoff, saum_licht = g["stoff"], g["licht"]
    stoff_hi = shade(stoff, 0.42)
    slits = _garment_slits(openings)
    # Gezeichnet werden hoechstens vier. Der Spielwert kennt vierzehn
    # Oeffnungen, aber vierzehn Kerben in einem vierzig Pixel hohen Umriss
    # sind keine Fassung mehr, sondern ein Saegeblatt.
    sichtbar = slits[:4] if len(slits) > 4 else slits

    # Ein Cape haengt hinter ihr, ein Mantel liegt auf ihr. Deshalb wird das
    # eine vor der Gestalt gezeichnet und das andere danach. Zurueck kommt
    # die Hoehe des Kragens - bis dorthin deckt der Stoff.
    if cut == "keins":
        return LEG_T           # nichts deckt, die Flamme faengt unten an
    if (cut == "cape") != hinter:
        return LEG_T if cut == "cape" else coverage

    if cut == "cape":
        _draw_cape(c, kind=kind, cx=cx, base=base, height=height, phase=phase,
                   lean=lean, smear=smear, sway=sway, coverage=coverage,
                   slits=slits, stoff=stoff, stoff_hi=stoff_hi, licht=saum_licht)
        return LEG_T

    if cut == "bruch":
        _draw_fetzen(c, kind=kind, cx=cx, base=base, height=height, phase=phase,
                     lean=lean, smear=smear, sway=sway, coverage=coverage,
                     stoff=stoff, licht=saum_licht)
        return LEG_T

    starr = cut == "harnisch"
    rows = max(2, int(height * (coverage - LEG_T * 0.78)))
    # Der Bauch der Flamme gibt das Mass fuer den ganzen Schnitt.
    bauch = _profile(0.26, kind)

    for i in range(rows + 1):
        u = i / rows                      # 0 Saum, 1 Kragen
        # Der Saum endet ueber den Knien, sonst verdeckt er die Beine -
        # und dann steht sie wieder als Kegel da.
        t = LEG_T * 0.78 + u * (coverage - LEG_T * 0.78)
        y = base - t * height
        hang = (1 - u) ** 2               # wie frei der Stoff haengt
        # Die Breite richtet sich nach der Flamme, nicht nach der Hoehe.
        tf = max(0.0, (t - LEG_T) / max(0.001, 1 - LEG_T))

        if starr:
            # Metall haengt nicht. Es sitzt auf ihr und folgt nur der Neigung.
            sx = cx + lean * t
            sx += math.sin(t * 2.6 + phase) * (0.6 + t * 0.9) * 0.5
            # Ein Harnisch ist getrieben, nicht gebaut: er sitzt eng an und
            # wird nach unten schmaler. Waagerechte Schienen ueber die ganze
            # Hoehe machen daraus eine Tonne - die gibt es nur noch unten,
            # wo die Beintaschen sitzen.
            w = bauch * (0.66 + 0.16 * hang) + 0.5
        else:
            # Lose: der Saum haengt weit hinterher und schwingt nach.
            sx = cx + lean * t * (1 - 0.42 * hang)
            sx += math.sin(t * 2.6 + phase - 1.1 * hang) * (0.9 + t * 1.7) * 0.85
            sx += (-lean * 0.75 - smear * 5.5) * hang
            sx += math.sin(phase * 1.3 + sway * 3.0 + u * 2.2) * hang * (1.5 + sway * 2.8)
            # Schmal. Er legt sich an, statt sie einzupacken - eine
            # Glockenform macht aus jeder Figur einen Kegel, und ein Kegel
            # ist nicht schlank. Nur der Saum darf nach hinten ausschlagen,
            # und zwar auf einer Seite, nicht rundum.
            w = bauch * (0.62 + 0.10 * hang) + 0.6
            if u < 0.20:
                w *= 0.55 + 2.2 * u
        w *= 1 + smear * 0.20
        if split > 0:
            sx += math.sin(t * 9.0 + phase * 2) * split * 3.0

        # Eine Oeffnung ist eine Kerbe im Rand, kein fehlendes Stueck: der
        # Stoff weicht dort zurueck, und in der Kerbe steht ihr Licht.
        def kerbe(seite: int) -> float:
            for su, s_, laenge in sichtbar:
                if s_ == seite and abs(u - su) < laenge / 2:
                    tief = 1 - abs(u - su) / (laenge / 2)
                    return (1.6 + 1.6 * tief) * min(1.0, w / 4)
            return 0.0

        # Der Schlag nach hinten liegt auf einer Seite. Beidseitig waere
        # es ein Rock, einseitig ist es ein Mantel im Wind.
        hinten_raus = 0.0 if starr else max(0.0, -(lean * 0.9 + smear * 4.0)) * hang
        links = int(sx - w - hinten_raus + kerbe(-1))
        rechts = int(sx + w - kerbe(1))
        # Geschlossen fuellen. Jedes Loch im Stoff bricht die Silhouette,
        # und eine gebrochene Silhouette ist bei vierzig Pixeln nicht mehr
        # zu lesen - daran ist der erste Anlauf gescheitert.
        for x in range(links, rechts + 1):
            rand = x <= links or x >= rechts
            if rand:
                # Ihr Licht sitzt hinter dem Stoff: der Rand glueht.
                col = mix(stoff, saum_licht, 0.45)
            elif starr and u < 0.34 and i % 3 == 0:
                col = shade(stoff, -0.42)          # Fuge der Beintaschen
            elif starr and u < 0.34 and i % 3 == 1:
                col = stoff_hi                     # Grat darueber
            elif starr and abs(x - int(sx)) <= 1:
                # Der Mittelgrat des Brustpanzers - eine senkrechte Linie
                # statt lauter waagerechter. Das macht ihn schlank.
                col = stoff_hi
            elif starr and abs(x - int(sx)) == 2:
                col = shade(stoff, -0.28)
            elif abs(x - int(sx)) <= 1:
                col = shade(stoff, 0.16)           # Licht laeuft mittig durch
            else:
                col = stoff
            c.set(x, int(y), col)

        # Nur die unterste Kante franst aus - der Rest bleibt geschlossen.
        if not starr and u < 0.08:
            for x in range(links, rechts + 1):
                if hash01(x, int(y) + int(phase * 4)) < 0.42:
                    c.set(x, int(y), None)

        for seite, kante in ((-1, links), (1, rechts)):
            if kerbe(seite) > 0:
                c.set(kante, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 235))
                c.blend(kante + seite, int(y),
                        (saum_licht[0], saum_licht[1], saum_licht[2], 70))

        # Der Kragen haelt sie zusammen. Beim Harnisch steht er als Kehle
        # hoch und laesst genau den Kopf frei.
        if u > 0.90:
            c.set(links, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 190))
            c.set(rechts, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 190))
            if starr:
                # Kehle und Schulterspitzen. Der Kragen steht hoch und
                # laesst genau den Kopf frei - und an den Ecken sitzt je
                # eine Spitze, damit die Schulter eine Kante bekommt.
                for x in range(links + 1, rechts):
                    c.set(x, int(y - 1), stoff_hi)
                for seite, kante in ((-1, links), (1, rechts)):
                    c.set(kante, int(y - 1), mix(stoff, saum_licht, 0.5))
                    c.set(kante + seite, int(y - 1), stoff)
                    c.set(kante + seite, int(y - 2), mix(stoff, saum_licht, 0.65))

    return coverage


def _draw_fetzen(c: Canvas, *, kind: str, cx: int, base: float, height: float,
                 phase: float, lean: float, smear: float, sway: float,
                 coverage: float, stoff, licht) -> None:
    """
    Was nach dem Bruch von der Fassung uebrig ist.

    Keine geschlossene Bahn mehr, sondern einzelne Fetzen, die an ihr
    haengen und im eigenen Takt flattern. Sie decken nichts - man sieht
    ueberall durch sie hindurch, und genau das ist der Punkt: das Gefaess
    ist auf, sie klingt nach allen Seiten zugleich.
    """
    S = HERO_SCALE
    # Zehn schmale Streifen, die an ihr haengen. Sie beginnen genau auf der
    # Silhouette und fallen nach unten weg - Stoff, der reisst, faellt; er
    # steht nicht ab. Dunkel bleiben sie auch: sonst verliert sie den Umriss
    # ganz, und ohne Umriss ist sie im Kampf nicht mehr zu lesen.
    for k in range(10):
        u = LEG_T + (k / 10) * (coverage - LEG_T)
        y = base - u * height
        seite = 1 if k % 2 == 0 else -1
        w = _profile(max(0.0, (u - LEG_T) / (1 - LEG_T)), kind) * 0.92 + 0.6 * S
        eigen = math.sin(phase * (1.2 + k * 0.23) + k * 2.1 + sway * 1.4)
        laenge = (3.0 + (k % 4) * 2.0) * S
        x = cx + lean * u + seite * w

        for i in range(int(laenge)):
            v = i / max(1.0, laenge)
            # Er faellt, und weht dabei nach hinten - der Ausschlag waechst
            # zum Zipfel hin, wie bei allem, was nur oben festhaengt.
            fx = x + seite * v * 1.4 + eigen * v ** 1.5 * 3.2 - smear * 6.0 * v
            fy = y + i * (1.05 + 0.25 * abs(eigen))
            if fy > base:
                break
            col = shade(stoff, -0.18) if i % 3 else stoff
            c.set(int(fx), int(fy), col)
            # Nur die Aussenkante faengt Licht.
            if i and hash01(int(fx), int(fy) + int(phase * 5)) > 0.62:
                c.set(int(fx) + seite, int(fy), mix(stoff, licht, 0.55))
        # Dort, wo er reisst, glimmt sie durch.
        c.set(int(x), int(y), (licht[0], licht[1], licht[2], 230))


def _draw_cape(c: Canvas, *, kind: str, cx: int, base: float, height: float,
               phase: float, lean: float, smear: float, sway: float,
               coverage: float, slits, stoff, stoff_hi, licht) -> None:
    """
    Ein Cape haengt an der Schulter und sonst nirgends.

    Es traegt nichts und deckt nichts - es faengt nur die Bewegung. Beim
    Sprung schwirrt es weit hinter ihr her, beim Stehen sinkt es zurueck.
    Gezeichnet wird es als Bahn, die von der Schulter nach hinten unten
    laeuft: eine Mittellinie mit Breite, keine Kontur um einen Koerper.
    """
    hinten = -1 if lean >= 0 else 1        # es haengt der Bewegung entgegen
    sy = base - coverage * height
    sx = cx + lean * coverage * 0.6

    # Wie weit es aussteht. Schon im Stand haengt es ein Stueck hinter ihr,
    # sonst waere es hinter der Gestalt gar nicht zu sehen.
    wurf = 4.2 + abs(lean) * 1.4 + smear * 8.0 + abs(sway) * 3.4
    laenge = height * (0.86 + smear * 0.16)

    punkte = []
    schritte = int(laenge) + 1
    for i in range(schritte + 1):
        v = i / schritte                                  # 0 Schulter .. 1 Zipfel
        # Die Bahn faellt und weht dabei nach hinten aus.
        x = sx + hinten * (2.0 + wurf * v ** 1.15)
        x += math.sin(v * 3.2 + phase * 1.6 + sway * 2.4) * (0.5 + v * 2.2)
        y = sy + laenge * v * (0.92 - 0.34 * abs(sway))
        punkte.append((x, y))

    for i, (x, y) in enumerate(punkte):
        v = i / schritte
        # Am Kragen schmal, dann breit, am Zipfel wieder spitz.
        w = 1.0 + 4.6 * math.sin(min(1.0, v * 1.15) * math.pi) ** 0.55
        offen = any(abs(v - (1 - su)) < laenge_ / 2 for su, _, laenge_ in slits)
        for dx in range(-int(w) - 1, int(w) + 2):
            d = abs(dx) / max(0.8, w)
            if d > 1:
                continue
            if offen and d > 0.5:
                if d > 0.78:
                    c.blend(int(x) + dx, int(y), (licht[0], licht[1], licht[2], 150))
                continue
            # Der Zipfel franst aus.
            if v > 0.82 and hash01(int(x) + dx, int(y) + int(phase * 4)) < (v - 0.82) * 3.4:
                continue
            if d > 0.74:
                col = mix(stoff, licht, 0.38)
            elif d < 0.24:
                col = stoff_hi
            else:
                col = stoff
            c.set(int(x) + dx, int(y), col)

    # Die Spange an der Schulter - das Einzige daran, das eine Kante hat.
    c.set(int(sx), int(sy), (licht[0], licht[1], licht[2], 235))
    c.set(int(sx) + hinten, int(sy), mix(stoff, licht, 0.55))
    c.set(int(sx), int(sy) + 1, mix(stoff, licht, 0.35))


def draw_heroine(
    *,
    instrument: str | None = "leier",
    garment: str = "mantel",
    sway: float = 0.0,        # Nachschwingen des Stoffs

    phase: float = 0.0,       # Flackern
    lean: float = 0.0,        # Neigung nach vorn
    stretch: float = 1.0,     # senkrechte Dehnung (Sprung)
    smear: float = 0.0,       # waagerechtes Verwischen (Herzschlag)
    split: float = 0.0,       # Resonanz zieht die Gestalt auseinander
    whip: float = 0.0,        # Ausschlag beim Schlag
    settle: float = 0.0,      # Absinken (Rast, Landung)
    aim: float = 0.0,
    glow: float = 1.0,
    alpha_body: int = 255,
    # Von den Animationen weitergereicht, hier ohne Wirkung:
    bob: float = 0.0, leg_phase=None, leg_spread: float = 0.0,
    arm_front: float = 0.0, arm_back: float = 0.0,
    hair_sway: float = 0.0, cloak_sway: float = 0.0, cloak_lift: float = 0.0,
    crouch: float = 0.0,
) -> Canvas:
    c = Canvas(HERO_W, HERO_H)
    cx = HERO_W // 2
    base = GROUND - settle

    kind = instrument or "leier"
    height = (BODY_H + (BODY_H * 0.10 if kind == "floete" else 0.0)) * stretch - settle * 0.6
    top_y = base - height

    core = mix(P.BONE, hexc("#dffaf2"), 0.55)
    mid = mix(P.TRIM, P.BONE, 0.35)
    rim = mix(P.TRIM, P.CLOAK, 0.45)

    # Was hinter ihr haengt, kommt zuerst - sonst laege das Cape vor ihr.
    _ = _draw_garment(c, garment=garment, kind=kind, cx=cx, base=base,
                      height=height, phase=phase, lean=lean, smear=smear,
                      split=split, sway=sway, hinter=True)

    # Die Klinge liegt auf ihrem Ruecken, also hinter allem anderen.
    _draw_klinge(c, cx=cx, base=base, height=height, phase=phase,
                 lean=lean, sway=sway)

    # --- Die Beine --------------------------------------------------------
    #
    # Unten ist sie nicht formlos. Der Klang hat sich dort zu Kristall
    # gesetzt - zwei kurze, gedrungene Beine mit einer hellen Ader darin.
    # Vorher lief die Gestalt nach unten einfach spitz zu und schleifte
    # ueber den Boden; das sah aus, als kroeche sie.
    _draw_beine(c, cx=cx, base=base, height=height, phase=phase, lean=lean,
                leg_phase=leg_phase, leg_spread=leg_spread, crouch=crouch,
                settle=settle, smear=smear)

    _draw_arme(c, cx=cx, base=base, height=height, phase=phase, lean=lean,
               leg_phase=leg_phase, arm_front=arm_front, arm_back=arm_back,
               whip=whip, smear=smear)

    # Der Mantel ist die Grundform, nicht die Verzierung: er wird zuerst
    # gesetzt, geschlossen und undurchsichtig. Die Flamme sitzt darauf.
    # Andersherum franst sie ueber den Rand hinaus, und die Silhouette
    # zerfaellt in Sprenkel - genau daran ist der erste Anlauf gescheitert.
    kragen = _draw_garment(c, garment=garment, kind=kind, cx=cx, base=base,
                           height=height, phase=phase, lean=lean, smear=smear,
                           split=split, sway=sway, hinter=False)

    # --- Die Gestalt ------------------------------------------------------
    hueft = base - LEG_T * height          # wo die Flamme aufsitzt
    flamme = height * (1 - LEG_T)
    # Unterhalb des Kragens deckt der Stoff ohnehin - dort wuerde die
    # Flamme nur seitlich herausfransen.
    ab = max(0.0, (kragen - LEG_T) / (1 - LEG_T) - 0.10)
    steps = int(flamme) + 1
    for i in range(steps):
        t = i / max(1, steps - 1)
        if t < ab:
            continue
        y = hueft - t * flamme

        w = _profile(t, kind) * (1 + smear * 0.5)
        # Der Schlag treibt eine Welle durch sie hindurch.
        w *= 1 + whip * math.sin(t * math.pi * 1.6) * 0.5

        # Rueckgrat: Neigung, plus ein langsames Wehen.
        sx = cx + lean * t + math.sin(t * 2.6 + phase) * (0.9 + t * 1.7)
        sx += smear * 3.0 * (1 - t) * -1
        # Resonanz zieht die Gestalt in waagerechte Baender auseinander.
        if split > 0:
            sx += math.sin(t * 9.0 + phase * 2) * split * 4.0

        for dx in range(-int(w) - 1, int(w) + 2):
            d = abs(dx) / max(0.8, w)
            if d > 1:
                continue
            # Der Rand franst aus und flackert.
            noise = hash01(int(sx) + dx, int(y) * 3 + int(phase * 6))
            if d > 0.55 and noise < (d - 0.55) / 0.45 * 0.85:
                continue
            # Sie ist Klang, kein Fleisch: der Grund scheint durch sie
            # hindurch. Dicht in der Mitte, duenner zum Rand und nach oben,
            # wo sie ohnehin ausfranst.
            if d < 0.34:
                col = core
                deckung = 0.86 - 0.20 * t
            elif d < 0.68:
                col = mid
                deckung = 0.74 - 0.24 * t
            else:
                col = rim
                deckung = 0.58 - 0.26 * t
            a = int(255 * max(0.18, deckung))
            c.set(int(sx) + dx, int(y), (col[0], col[1], col[2], a))

    # Funken. Sie steigen aus der Flamme auf, werden nach oben hin duenner
    # und wehen mit ihrer Neigung mit - ein Kopf aus Feuer, der nichts
    # absondert, sieht aus wie gemalter Rauch.
    for k in range(9):
        u = (k / 9 + phase * 0.22) % 1.0
        fy = hueft - flamme * (0.55 + u * 0.75)
        fx = cx + lean * (0.6 + u) + math.sin(u * 6.2 + phase * 2.4 + k) * (2 + u * 6)
        if hash01(k * 3, int(phase * 7) + k) < 0.30:
            continue
        hell = mix(mid, P.AMBER, 0.25 + u * 0.5)
        c.set(int(fx), int(fy), (hell[0], hell[1], hell[2], int(235 * (1 - u * 0.7))))
        if u < 0.35:
            c.set(int(fx), int(fy) + 1, (hell[0], hell[1], hell[2], 90))

    # --- Die Augen --------------------------------------------------------
    #
    # Zwei rosa Pixel. Mehr braucht sie nicht, und mehr vertraegt sie auch
    # nicht: alles andere an ihr ist kalt und blass, also reichen zwei
    # Punkte in der Gegenfarbe, damit aus einer Erscheinung jemand wird,
    # der einen ansieht. Es ist dieselbe Farbe wie die Klinge auf ihrem
    # Ruecken - das Rosa gehoert ihr, nicht der Welt.
    #
    # Sie blinzelt selten und kurz. Ein Blinzeln, das man erwartet, ist
    # Mechanik; eines, das man verpasst, ist Leben.
    augen_t = 0.80
    ay_ = int(base - augen_t * height)
    ax_ = int(cx + lean * augen_t + math.sin(augen_t * 2.6 + phase) * 1.5)
    rosa = hexc("#ff7ad0")
    zu = math.sin(phase * 0.8) > 0.93
    for seite in (-1, 1):
        ex = ax_ + seite
        if zu:
            # Geschlossen: nur ein gedaempfter Strich bleibt stehen.
            c.set(ex, ay_, mix(rosa, P.CLOAK, 0.5))
        else:
            # Sie sind das hellste Rosa im ganzen Bild - heller als die
            # Klinge. Sonst sucht das Auge zuerst die Waffe und dann erst
            # sie.
            c.set(ex, ay_, mix(rosa, (255, 255, 255, 255), 0.30))
            c.glow(ex, ay_, 3.0 * HERO_SCALE, (rosa[0], rosa[1], rosa[2], 95))

    # --- Der Kern ---------------------------------------------------------
    _draw_kern(c, kern=kind, cx=cx, base=base, height=height,
               phase=phase, lean=lean, glow=glow, mid=mid)

    if glow > 0:
        c.glow(cx, base - height * 0.45, 11,
               (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(38 * glow)), power=2.2)

    if alpha_body < 255:
        for i in range(len(c.px)):
            c.px[i][3] = int(c.px[i][3] * alpha_body / 255)
    return c


def draw_instrument(c: Canvas, kind: str, hx: int, hy: int, glow: float) -> None:
    """Nicht mehr in Gebrauch: das Instrument verformt die Gestalt, statt
    von ihr getragen zu werden. Bleibt als Vorlage fuer Anzeigesymbole."""
    """
    Das Instrument bleibt eine Andeutung. Es darf die Silhouette der Maske
    nicht schlagen - man soll die Figur erkennen, nicht ihr Werkzeug.
    """
    if kind == "leier":
        c.rect(hx, hy - 3, 1, 6, P.BONE_SH)
        c.rect(hx + 3, hy - 3, 1, 6, P.BONE_SH)
        c.rect(hx, hy + 2, 4, 1, P.BONE_LO)
        c.set(hx + 1, hy - 4, P.BONE_SH)
        c.set(hx + 2, hy - 4, P.BONE_SH)
        for i in range(2):
            c.rect(hx + 1 + i, hy - 2, 1, 4, mix(P.AMBER, P.BONE_LO, 0.55))
        c.glow(hx + 2, hy, 5, (P.AMBER[0], P.AMBER[1], P.AMBER[2], int(52 * glow)))
    elif kind == "trommel":
        c.ellipse(hx + 1, hy, 3.2, 2.8, P.BONE_LO)
        c.ellipse(hx + 1, hy - 0.5, 2.6, 2.2, P.BONE_SH)
        c.set(hx, hy - 1, P.BONE)
        c.glow(hx + 1, hy, 5, (P.AMBER[0], P.AMBER[1], P.AMBER[2], int(46 * glow)))
    else:
        c.rect(hx - 1, hy - 1, 7, 1, P.BONE_SH)
        c.rect(hx - 1, hy, 7, 1, P.BONE_LO)
        for i in range(2):
            c.set(hx + 1 + i * 2, hy - 1, P.EYE)
        c.set(hx + 6, hy - 1, P.AMBER)
        c.glow(hx + 5, hy, 5, (P.AMBER[0], P.AMBER[1], P.AMBER[2], int(52 * glow)))


# ------------------------------------------------------ Animations-Sequenzen

def hero_animations(instrument: str, garment: str = "mantel") -> dict[str, list[Canvas]]:
    """
    Weil die Gestalt formlos ist, braucht sie keine Gliedmassen, die
    zueinander passen muessen - jede Bewegung ist eine Verformung der
    ganzen Masse. Das macht die Animation freier als bei einer Figur.
    """
    anims: dict[str, list[Canvas]] = {}

    def frames(count: int, **kw) -> list[Canvas]:
        out = []
        for i in range(count):
            p = i / count * math.tau
            out.append(draw_heroine(instrument=instrument, garment=garment,
                                    phase=p, sway=math.sin(p) * 0.6, **kw))
        return out

    # Ruhe: sie flackert und atmet.
    anims["idle"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i / 10 * math.tau,
                     # Ein Atemzug: sie hebt sich, sinkt zurueck, und der
                     # Saum kommt eine Spur spaeter nach.
                     stretch=1.0 + math.sin(i / 10 * math.tau) * 0.055,
                     settle=0.5 - 0.5 * math.sin(i / 10 * math.tau),
                     lean=math.sin(i / 10 * math.tau + 0.6) * 0.35,
                     sway=math.sin(i / 10 * math.tau - 0.9) * 0.75,
                     glow=0.85 + 0.25 * (0.5 + 0.5 * math.sin(i / 10 * math.tau)))
        for i in range(10)
    ]

    # Lauf: sie neigt sich und zieht einen Schweif hinter sich her.
    anims["run"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i / 8 * math.tau * 2,
                     lean=2.4 + math.sin(i / 8 * math.tau) * 0.9,
                     # Zwei Schritte je Runde: der Koerper hebt sich zweimal.
                     stretch=0.93 + abs(math.sin(i / 8 * math.tau)) * 0.12,
                     settle=1.0 - abs(math.sin(i / 8 * math.tau)),
                     # Der Schritt laeuft doppelt so schnell wie der Rumpf:
                     # zwei Schritte auf eine Runde des Koerpers.
                     leg_phase=i / 8 * math.tau,
                     smear=0.16, sway=math.sin(i / 8 * math.tau + 1.1) * 1.5)
        for i in range(8)
    ]

    # Sprung: Absprung streckt sie, dann traegt sie der Schwung, und im
    # Scheitel sinkt der Mantel wieder auf sie herab. Drei Bilder reichen -
    # aber ein einziges reicht eben nicht, dann steht sie in der Luft.
    anims["jump"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=0.6,
                     lean=1.6, stretch=1.30, smear=0.08, sway=-1.7,
                     leg_phase=1.2, leg_spread=0.6, crouch=1.4),
        draw_heroine(instrument=instrument, garment=garment, phase=1.5,
                     lean=1.3, stretch=1.22, smear=0.04, sway=-1.1,
                     leg_phase=1.9, leg_spread=0.3, crouch=0.8),
        draw_heroine(instrument=instrument, garment=garment, phase=2.4,
                     lean=1.0, stretch=1.12, sway=-0.5, glow=1.1,
                     leg_phase=2.6, crouch=0.3),
    ]

    # Fall: sie zieht sich lang, das Tuch steht nach oben weg und flattert.
    anims["fall"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i * 1.4,
                     lean=0.6, stretch=0.86 + i * 0.02, smear=0.18,
                     leg_phase=3.4 + i * 0.4, leg_spread=0.8,
                     sway=1.5 + math.sin(i * 1.9) * 0.5)
        for i in range(4)
    ]

    # Landung: erst staucht es sie zusammen, dann federt sie zurueck.
    anims["land"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=1.1,
                     stretch=0.68, settle=3, smear=0.36, sway=2.1,
                     leg_spread=1.4, crouch=2.6),
        draw_heroine(instrument=instrument, garment=garment, phase=1.8,
                     stretch=0.84, settle=1, smear=0.18, sway=1.2,
                     leg_spread=0.7, crouch=1.2),
        draw_heroine(instrument=instrument, garment=garment, phase=2.5,
                     stretch=1.04, smear=0.05, sway=0.4),
    ]

    # Herzschlag: die Gestalt zerreisst waagerecht und zieht nach.
    anims["dash"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i * 1.7, lean=4.0 - i,
                     stretch=0.82, smear=0.9 - i * 0.2, split=0.5 - i * 0.15,
                     glow=1.4, alpha_body=235 - i * 30)
        for i in range(3)
    ]

    anims["wall"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i * 1.6,
                     lean=-1.8, stretch=1.10 - i * 0.02, smear=0.1,
                     sway=-0.7 - i * 0.25)
        for i in range(3)
    ]

    # Nahkampf: eine Welle laeuft durch sie hindurch.
    anims["melee"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=0.2, lean=-1.2, whip=-0.35,
                     stretch=1.06, glow=1.1),
        draw_heroine(instrument=instrument, garment=garment, phase=1.4, lean=3.4, whip=0.85,
                     stretch=0.92, smear=0.3, glow=1.6),
        draw_heroine(instrument=instrument, garment=garment, phase=2.6, lean=1.6, whip=0.30,
                     stretch=1.0, glow=1.2),
    ]

    # Fernkampf: sie zieht sich zusammen und stoesst den Ton aus.
    anims["cast"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=0.3, stretch=0.90,
                     lean=-0.8, glow=1.0),
        draw_heroine(instrument=instrument, garment=garment, phase=1.6, stretch=1.16,
                     lean=1.2, split=0.28, glow=1.8),
        draw_heroine(instrument=instrument, garment=garment, phase=2.8, stretch=1.04,
                     lean=0.4, glow=1.3),
    ]

    # Treffer: sie zerfaellt fast.
    anims["hurt"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=1.9, lean=-3.4,
                     stretch=0.84, split=0.85, smear=0.45, sway=-2.2,
                     glow=0.4, alpha_body=195),
        draw_heroine(instrument=instrument, garment=garment, phase=2.9, lean=-2.2,
                     stretch=0.90, split=0.45, smear=0.25, sway=-1.2,
                     glow=0.6, alpha_body=220),
        draw_heroine(instrument=instrument, garment=garment, phase=3.9, lean=-1.0,
                     stretch=0.97, split=0.15, sway=-0.4,
                     glow=0.85, alpha_body=240),
    ]

    # Rast: sie sinkt zu einer Lache zusammen.
    anims["rest"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i / 5 * math.tau,
                     stretch=0.58, settle=4, glow=1.2,
                     sway=math.sin(i / 5 * math.tau) * 0.35)
        for i in range(5)
    ]

    return anims


def draw_klangmotte(phase: float) -> Canvas:
    """Klangmotte - taumelnder Falter aus verklungenen Toenen."""
    c = Canvas(16, 14)
    cx, cy = 8, 7
    flap = math.sin(phase)
    span = 4 + flap * 2.4
    for side in (-1, 1):
        for i in range(int(span)):
            t = i / max(1, span)
            h = int(3 * (1 - t) + 1)
            x = cx + side * (2 + i)
            y = cy - 2 - int(flap * 1.6 * (1 - t))
            col = mix(P.BLOOM, P.BLOOM_DIM, t)
            c.rect(x if side > 0 else x, y, 1, h + 2, col)
    c.ellipse(cx, cy, 2.2, 3.0, P.INK2)
    c.ellipse(cx, cy - 1, 1.6, 1.8, mix(P.INK2, P.BLOOM, 0.25))
    c.set(cx - 1, cy - 2, P.GLOW)
    c.set(cx + 1, cy - 2, P.GLOW)
    c.outline(hexc("#05060c", 200))
    c.glow(cx, cy, 8, (P.BLOOM[0], P.BLOOM[1], P.BLOOM[2], 44))
    return c


def draw_stilleschreiter(phase: float) -> Canvas:
    """Stilleschreiter - schwerer Waechter, der Klang schluckt."""
    c = Canvas(22, 20)
    step = math.sin(phase)
    cx, base = 11, 19
    # Beine
    for i, s in enumerate((step, -step)):
        x = cx - 4 + i * 6 + int(s * 2)
        c.rect(x, base - 6, 3, 6, shade(P.STONE, -0.25))
        c.rect(x - 1, base - 2, 5, 2, P.STONE_LO)
    # Rumpf: gebeugte Masse
    c.ellipse(cx, base - 10, 7, 5.4, P.STONE)
    c.ellipse(cx, base - 11, 6, 4.2, P.STONE_HI)
    c.ellipse(cx + 1, base - 13, 3.4, 2.6, P.STONE)
    # Maske ohne Mund
    c.rect(cx + 2, base - 14, 5, 4, P.INK2)
    c.set(cx + 5, base - 13, P.ROT)
    c.set(cx + 5, base - 12, shade(P.ROT, -0.3))
    # Ruecken-Resonanzplatten
    for i in range(3):
        c.rect(cx - 6 + i * 3, base - 15 + i, 2, 3, mix(P.STONE_HI, P.GLOW_DIM, 0.35))
    c.shadow_pass((0, 1), -0.2)
    c.outline(hexc("#05060c", 220))
    return c


def draw_dissonanzknospe(phase: float) -> Canvas:
    """Dissonanzknospe - festgewachsen, spuckt schiefe Toene."""
    c = Canvas(16, 18)
    open_amt = max(0.0, math.sin(phase))
    cx, base = 8, 17
    c.rect(cx - 1, base - 7, 3, 7, shade(P.ROT_DIM, -0.2))
    c.rect(cx - 3, base - 1, 7, 1, P.ROT_DIM)
    petals = 5
    for i in range(petals):
        a = -math.pi / 2 + (i - (petals - 1) / 2) * (0.42 + open_amt * 0.34)
        for r in range(2, 7):
            x = cx + math.cos(a) * r
            y = base - 8 + math.sin(a) * r
            col = mix(P.ROT, P.ROT_DIM, r / 7)
            c.set(int(round(x)), int(round(y)), col)
            c.set(int(round(x)) + (1 if math.cos(a) > 0 else -1), int(round(y)), shade(col, -0.2))
    c.ellipse(cx, base - 8, 2.6, 2.6, P.INK2)
    c.ellipse(cx, base - 8, 1.4 + open_amt, 1.4 + open_amt, mix(P.ROT, P.WARM, 0.4 * open_amt))
    c.outline(hexc("#05060c", 210))
    c.glow(cx, base - 8, 7, (P.ROT[0], P.ROT[1], P.ROT[2], int(30 + 40 * open_amt)))
    return c


def draw_echoscherbe(phase: float) -> Canvas:
    """Echoscherbe - springender Kristallsplitter."""
    c = Canvas(14, 14)
    cx, cy = 7, 7
    spin = phase
    pts = []
    for i in range(6):
        a = spin + i / 6 * math.tau
        r = 5 if i % 2 == 0 else 3
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        c.line(x0, y0, x1, y1, P.GLOW)
    c.ellipse(cx, cy, 2.4, 2.4, mix(P.GLOW_DIM, P.INK2, 0.4))
    c.set(cx, cy, P.GLOW)
    c.glow(cx, cy, 8, (P.GLOW[0], P.GLOW[1], P.GLOW[2], 52))
    return c


def draw_kantor(phase: float, enraged: bool = False) -> Canvas:
    """Der Verstimmte Kantor - Boss. Orgelpfeifen wachsen ihm aus dem Ruecken."""
    c = Canvas(44, 52)
    cx, base = 22, 51
    sway = math.sin(phase) * 1.6
    accent = P.ROT if enraged else P.BLOOM

    # Schleppe / Talar
    for y in range(base - 22, base):
        t = (y - (base - 22)) / 22
        half = 5 + t * 11
        c.rect(int(cx - half + sway * (1 - t)), y, int(half * 2), 1,
               mix(P.INK2, P.STONE_LO, t * 0.7))
    c.rect(cx - 16, base - 2, 32, 2, P.INK)

    # Orgelpfeifen im Ruecken
    for i in range(7):
        h = 16 + int(abs(math.sin(phase * 0.5 + i)) * 6) + (7 - abs(i - 3)) * 3
        x = cx - 15 + i * 5
        y = base - 24 - h
        c.rect(x, y, 3, h, mix(P.STONE_HI, accent, 0.22))
        c.rect(x, y, 3, 2, mix(accent, P.WARM, 0.3))
        c.rect(x + 2, y, 1, h, shade(P.STONE_HI, -0.3))

    # Torso
    c.ellipse(cx + sway * 0.5, base - 27, 9, 8, P.STONE)
    c.ellipse(cx + sway * 0.5, base - 29, 7.6, 6, P.STONE_HI)
    # Notenkragen
    for i in range(5):
        a = -math.pi + i / 4 * math.pi
        c.set(int(cx + math.cos(a) * 9 + sway * 0.5), int(base - 30 + math.sin(a) * 5), accent)

    # Kopf: Maske mit fuenf Notenlinien
    hx, hy = int(cx - 5 + sway), base - 44
    c.rect(hx, hy, 11, 11, P.INK2)
    c.rect(hx + 1, hy + 1, 9, 9, mix(P.STONE, P.INK2, 0.5))
    for i in range(5):
        c.rect(hx + 1, hy + 2 + i * 2, 9, 1, shade(P.STONE_HI, -0.1))
    c.rect(hx + 2, hy + 4, 2, 2, accent)
    c.rect(hx + 7, hy + 4, 2, 2, accent)
    if enraged:
        c.rect(hx + 3, hy + 9, 5, 1, P.ROT)

    # Arme mit Dirigentenstab
    c.line(cx - 8, base - 30, cx - 14, base - 24 + sway, P.STONE)
    c.line(cx + 8, base - 30, cx + 15, base - 34 - sway, P.STONE)
    c.line(cx + 15, base - 34 - sway, cx + 21, base - 40 - sway, mix(P.WARM, accent, 0.4))
    c.set(int(cx + 21), int(base - 40 - sway), accent)

    c.shadow_pass((0, 1), -0.18)
    c.outline(hexc("#05060c", 225))
    c.glow(cx, base - 30, 22, (accent[0], accent[1], accent[2], 34), power=2.2)
    return c


# -------------------------------------------------------------------- Bau

def build() -> None:
    # Sieben Kerne mal zehn Fassungen: die Blaetter werden hoch. Breiter
    # packen heisst weniger hoch - und ueber 4096 Pixel Hoehe hoert bei
    # manchen Geraeten der Spass auf.
    atlas = Atlas("characters", padding=1, max_width=2048)

    for instrument in ("stimmgabel", "leier", "trommel", "floete",
                       "metronom", "glocke", "orgelpfeife"):
        for garment in GARMENTS:
            if garment == "bruch":
                continue        # der Bruch kennt keinen heilen Kern mehr
            for name, frames in hero_animations(instrument, garment).items():
                atlas.add_sequence(f"cadence_{instrument}_{garment}_{name}", frames,
                                   pivot=(0.5, 1.0), fps=_fps_for(name))

    # Der Bruch gibt es nur als ein Paar: kein Gefaess, kein heiler Kern.
    # Alle Verbindungen davon zu zeichnen waere Ausschuss - nach dem Bruch
    # ist beides weg.
    for name, frames in hero_animations("bruch", "bruch").items():
        atlas.add_sequence(f"cadence_bruch_bruch_{name}", frames,
                           pivot=(0.5, 1.0), fps=_fps_for(name))

    atlas.add_sequence("klangmotte_fly",
                       [draw_klangmotte(i / 4 * math.tau) for i in range(4)],
                       pivot=(0.5, 0.5), fps=10)
    atlas.add_sequence("stilleschreiter_walk",
                       [draw_stilleschreiter(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=7)
    atlas.add_sequence("dissonanzknospe_bloom",
                       [draw_dissonanzknospe(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("echoscherbe_spin",
                       [draw_echoscherbe(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 0.5), fps=12)
    atlas.add_sequence("kantor_idle",
                       [draw_kantor(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("kantor_rage",
                       [draw_kantor(i / 6 * math.tau, enraged=True) for i in range(6)],
                       pivot=(0.5, 1.0), fps=9)

    png, js = atlas.write(OUT)
    print(f"characters -> {png.name} ({len(atlas.frames)} Frames), {js.name}")


def _fps_for(name: str) -> int:
    return {
        "idle": 6, "run": 13, "jump": 14, "fall": 9, "land": 16,
        "dash": 18, "wall": 7, "melee": 20, "cast": 16, "hurt": 14, "rest": 5,
    }.get(name, 8)


if __name__ == "__main__":
    build()
