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


def _draw_schwung(c: Canvas, *, cx: int, base: float, height: float,
                  schwung: float, lean: float) -> None:
    """
    Der Schlag: die Klinge verlaesst den Ruecken und faehrt einen Bogen.

    Der erste Fehler war, dass die Klinge waehrend des Schlags *auf ihrem
    Ruecken liegen blieb*. Sie hat sich nach vorn geneigt und ein wenig
    geleuchtet, und die Waffe hat nichts getan.

    Der zweite Fehler war der Nachzieher: fuenf blassere Kopien der
    Klinge auf frueheren Winkeln. Das liest sich nicht als Bewegung,
    sondern als Faecher aus Stoecken. Eine Klinge, die durch die Luft
    faehrt, hinterlaesst keine Klingen - sie hinterlaesst eine
    **gewischte Flaeche**, und die wird hier zwischen zwei Winkeln
    gefuellt, aussen hell und nach innen auslaufend.

    Dazu ist die Klinge im Schlag kuerzer als auf dem Ruecken. Sie fuehrt
    sie mit ausgestrecktem Arm, nicht ueber dem Kopf - eine Fechterin,
    keine Holzfaellerin.

    Der dritte Fehler war der Massstab. Die Figur ist knapp vierzig Pixel
    hoch; auf dieser Groesse *kann* eine Klinge keinen Schlag erzaehlen -
    sie ist zwei Pixel breit und dreht sich um wenige Grad pro Bild. Was
    man sieht, ist immer nur der **Bogen**. Beim Vorbild ist der Nagel
    kaum zu erkennen, die weisse Sichel dagegen fuellt den halben
    Bildschirm, und genau deshalb liest man den Schlag sofort.

    Also andersherum gebaut als vorher: zuerst der Bogen, gross, mit
    gleichmaessiger Dicke und einer hellen Vorderkante; die Klinge liegt
    danach auf seiner Vorderkante und ist nur noch die Begruendung. Der
    Bogen beginnt weit hinter der Klinge und endet an ihr - vorne hell
    und geschlossen, hinten duenn und offen. Er startet ausserdem
    ausserhalb ihrer Silhouette: ein Bogen, der durch die Figur laeuft,
    sieht aus wie ein Strich quer durchs Bild.

    `schwung` 0 = ausgeholt, 1 = durchgezogen.
    """
    S = HERO_SCALE
    rosa = mix(hexc("#ff7ad0"), P.CLOAK, 0.14)
    rosa_hi = mix(rosa, P.BONE, 0.55)
    rosa_lo = mix(rosa, P.CLOAK, 0.5)

    # Der Drehpunkt ist die Schulter, nicht die Hand: von dort geht der
    # Bogen aus, und nur deshalb liegt sein Mittelpunkt ruhig, waehrend
    # sich alles andere bewegt.
    dreh_x = cx + 0.6 * S + lean * 0.4
    dreh_y = base - height * 0.60

    # Von schraeg oben hinten nach vorn unten. In Leinwandkoordinaten
    # zeigt +y nach unten, also ist -1.85 rad oben-hinten und +0.42
    # vorn-leicht-unten.
    a0, a1 = -2.15, 0.78
    t = schwung ** 0.78
    winkel = a0 + (a1 - a0) * t

    # Der Arm streckt sich erst im Durchzug. Bei voller Reichweite schon
    # im Ausholen stand die Spitze ueber dem oberen Bildrand und wurde
    # abgeschnitten - und ein angeschnittener Schlag liest sich nicht.
    reichweite = height * (0.46 + 0.18 * t)

    # --- Der Bogen.
    # Zum Schluss klingt er ab: im letzten Bild soll die ausgestreckte
    # Klinge stehen, nicht noch einmal dieselbe Sichel.
    verblassen = 1.0 if t < 0.93 else 1.0 - (t - 0.93) / 0.07 * 0.55
    if t > 0.06:
        # Er zieht einen festen Winkelbetrag hinter sich her, statt bis
        # zum Anfang zurueckzureichen: sonst steht im letzten Bild ein
        # halber Kreis um sie herum.
        # Eine Sichel, keine Schleifspur.
        #
        # Der Unterschied steckt im Querschnitt. Eine Spur ist hinten
        # duenn und vorn dick, laeuft also in eine stumpfe Kante aus.
        # Eine Sichel ist in der Mitte am breitesten und laeuft nach
        # *beiden* Seiten spitz zu - das ist die Form, die man von der
        # Klinge im Vorbild kennt, und sie ist der ganze Grund, warum man
        # dort einen Schlag sieht und keinen Wisch. Der Aussenradius
        # bleibt darum fest; nur der Innenradius wandert.
        schleppe = min(t, 0.78)
        r_innen, r_aussen = reichweite * 0.60, reichweite * 1.00
        schritte = 56

        # Erst sammeln, dann setzen. Wird beim Abtasten direkt gemischt,
        # trifft die Bahn manche Pixel zweimal und andere einmal, und die
        # Sichel bekommt ein Schachbrettmuster. Pro Pixel zaehlt nur der
        # hoechste Wert, den die Bahn dort erreicht.
        flaeche: dict[tuple[int, int], tuple[tuple, int]] = {}

        def auftragen(px: float, py: float, col, deckung: int) -> None:
            schluessel = (int(px), int(py))
            vorher = flaeche.get(schluessel)
            if vorher is None or deckung > vorher[1]:
                flaeche[schluessel] = (col, deckung)

        for k in range(schritte):
            u = k / (schritte - 1)          # 0 = hintere Spitze, 1 = Klinge
            a = a0 + (a1 - a0) * (t - schleppe * (1 - u))
            ax, ay = math.cos(a), math.sin(a)
            # Linse: null an den Enden, am dicksten kurz vor der Klinge.
            # Im Ausholen ist sie zusaetzlich flacher - eine Sichel in
            # voller Dicke ueber einem Viertel Bogen ist ein Klumpen.
            dicke = math.sin(math.pi * min(1.0, u ** 0.72)) ** 0.55
            dicke *= 0.45 + 0.55 * t
            r0 = r_aussen - (r_aussen - r_innen) * dicke
            deckung = int((90 + 150 * u ** 1.1) * verblassen)
            i = r0
            while i <= r_aussen:
                v = (i - r0) / max(1.0, r_aussen - r0)
                # Aussen heller: die Vorderkante der Sichel traegt das Licht.
                auftragen(dreh_x + ax * i, dreh_y + ay * i,
                          mix(rosa, P.BONE, 0.10 + v * 0.55 + u * 0.25), deckung)
                i += 0.4
            # Die Aussenkante durchgehend, deckend - sie ist die Linie,
            # an der das Auge den Schlag festmacht, und sie laeuft ueber
            # die ganze Sichel, nicht nur ueber ihr vorderes Drittel.
            if dicke > 0.06 and verblassen > 0.7:
                for r in (r_aussen, r_aussen - 0.5):
                    auftragen(dreh_x + ax * r, dreh_y + ay * r,
                              mix(P.BONE, rosa_hi, 0.25 + (1 - u) * 0.35), 255)

        for (px, py), (col, deckung) in flaeche.items():
            c.blend(px, py, (col[0], col[1], col[2], deckung))

    # --- Die Klinge, auf der Vorderkante des Bogens.
    ax, ay = math.cos(winkel), math.sin(winkel)
    hand = reichweite * 0.24
    for i in range(int(hand), int(reichweite)):
        v = max(0.0, (i - hand) / (reichweite - hand))
        w = (1.9 - 1.5 * v ** 0.8) * S
        px, py = dreh_x + ax * i, dreh_y + ay * i
        for dq in range(-int(w), int(w) + 1):
            qx, qy = px - ay * dq, py + ax * dq
            c.set(int(qx), int(qy),
                  (rosa_hi if dq >= int(w) else rosa) if dq > 0 else rosa_lo)

    # Faust, Parierstueck, Knauf - drei Punkte, mehr traegt die Groesse nicht.
    fx, fy = dreh_x + ax * hand, dreh_y + ay * hand
    c.ellipse(fx, fy, 1.6 * S, 1.6 * S, P.BONE_SH)
    for k in (-2, -1, 1, 2):
        c.set(int(fx - ay * k), int(fy + ax * k), rosa_lo)
    for i in range(int(2.5 * S)):
        c.set(int(fx - ax * (i + 1)), int(fy - ay * (i + 1)),
              mix(rosa_lo, P.CLOAK, 0.35))

    spitze = (dreh_x + ax * reichweite, dreh_y + ay * reichweite)
    c.set(int(spitze[0]), int(spitze[1]), mix(rosa_hi, P.BONE, 0.7))
    c.glow(spitze[0], spitze[1], 5 * S, (rosa[0], rosa[1], rosa[2], 55))


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
               phase: float, lean: float, glow: float, mid,
               signatur: float = 1.0) -> None:
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
            c.blend(xi, yi, (licht[0], licht[1], licht[2],
                             max(0, min(255, int(a * signatur)))))

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
               (licht[0], licht[1], licht[2],
                int((70 + 60 * p) * glow * (0.45 + 0.55 * signatur))))


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
    # Der Schlag selbst: 0 ausgeholt, 1 durchgezogen. `None` heisst, die
    # Klinge bleibt auf dem Ruecken.
    schwung: float | None = None,
    settle: float = 0.0,      # Absinken (Rast, Landung)
    aim: float = 0.0,
    glow: float = 1.0,
    # Wie laut der Kern gerade klingt. Beim Gehen fast still, beim Zaubern
    # voll aufgedreht - sonst ist die Silhouette dauernd von Ringen und
    # Strahlen zugestellt, und man sieht nicht mehr, was gerade passiert.
    signatur: float = 0.35,
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

    # Die Klinge liegt auf ihrem Ruecken, also hinter allem anderen -
    # ausser sie schlaegt gerade zu. Dann kommt sie ganz zum Schluss
    # nach vorn (siehe unten).
    if schwung is None:
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
               phase=phase, lean=lean, glow=glow, mid=mid, signatur=signatur)

    if glow > 0:
        c.glow(cx, base - height * 0.45, 11,
               (P.TRIM[0], P.TRIM[1], P.TRIM[2], int(38 * glow)), power=2.2)

    if alpha_body < 255:
        for i in range(len(c.px)):
            c.px[i][3] = int(c.px[i][3] * alpha_body / 255)
    if schwung is not None:
        _draw_schwung(c, cx=cx, base=base, height=height,
                      schwung=schwung, lean=lean)

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

    def laut(name: str) -> float:
        return SIGNATUR.get(name, 0.35)

    def frames(count: int, **kw) -> list[Canvas]:
        out = []
        for i in range(count):
            p = i / count * math.tau
            out.append(draw_heroine(instrument=instrument, garment=garment,
                                    phase=p, sway=math.sin(p) * 0.6, **kw))
        return out

    # Ruhe: sie flackert und atmet.
    anims["idle"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("idle"), phase=i / 10 * math.tau,
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
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("run"), phase=i / 8 * math.tau * 2,
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
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("jump"), phase=0.6,
                     lean=1.6, stretch=1.30, smear=0.08, sway=-1.7,
                     leg_phase=1.2, leg_spread=0.6, crouch=1.4),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("jump"), phase=1.5,
                     lean=1.3, stretch=1.22, smear=0.04, sway=-1.1,
                     leg_phase=1.9, leg_spread=0.3, crouch=0.8),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("jump"), phase=2.4,
                     lean=1.0, stretch=1.12, sway=-0.5, glow=1.1,
                     leg_phase=2.6, crouch=0.3),
    ]

    # Fall: sie zieht sich lang, das Tuch steht nach oben weg und flattert.
    anims["fall"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("fall"), phase=i * 1.4,
                     lean=0.6, stretch=0.86 + i * 0.02, smear=0.18,
                     leg_phase=3.4 + i * 0.4, leg_spread=0.8,
                     sway=1.5 + math.sin(i * 1.9) * 0.5)
        for i in range(4)
    ]

    # Landung: erst staucht es sie zusammen, dann federt sie zurueck.
    anims["land"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("land"), phase=1.1,
                     stretch=0.68, settle=3, smear=0.36, sway=2.1,
                     leg_spread=1.4, crouch=2.6),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("land"), phase=1.8,
                     stretch=0.84, settle=1, smear=0.18, sway=1.2,
                     leg_spread=0.7, crouch=1.2),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("land"), phase=2.5,
                     stretch=1.04, smear=0.05, sway=0.4),
    ]

    # Herzschlag: die Gestalt zerreisst waagerecht und zieht nach.
    anims["dash"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("dash"), phase=i * 1.7, lean=4.0 - i,
                     stretch=0.82, smear=0.9 - i * 0.2, split=0.5 - i * 0.15,
                     glow=1.4, alpha_body=235 - i * 30)
        for i in range(3)
    ]

    anims["wall"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("wall"), phase=i * 1.6,
                     lean=-1.8, stretch=1.10 - i * 0.02, smear=0.1,
                     sway=-0.7 - i * 0.25)
        for i in range(3)
    ]

    # Nahkampf: eine Welle laeuft durch sie hindurch.
    #
    # Drei Bilder waren zu wenig fuer den Schlag, den man am haeufigsten
    # sieht. Ein Schlag hat vier Teile, und jeder muss ein eigenes Bild
    # haben, sonst fehlt ihm das Gewicht:
    #
    #   ausholen   - sie zieht sich zurueck, gegen die Richtung
    #   schlagen   - der Umschlag, mit Schmier und ganz gestreckt
    #   durchziehen- die Klinge ist schon durch, der Koerper folgt
    #   nachgeben  - sie faengt sich, die Kette schwingt aus
    anims["melee"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("melee"), phase=0.1, lean=-2.4, whip=-0.55,
                     stretch=1.10, settle=-1, glow=0.9, schwung=0.0),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("melee"), phase=0.9, lean=1.2, whip=0.35,
                     stretch=1.02, smear=0.5, glow=1.4, schwung=0.30),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("melee"), phase=1.7, lean=3.8, whip=0.95,
                     stretch=0.90, smear=0.85, glow=1.8, schwung=0.66),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("melee"), phase=2.4, lean=2.6, whip=0.55,
                     stretch=0.96, smear=0.25, glow=1.3, schwung=0.88),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("melee"), phase=3.0, lean=1.0, whip=0.15,
                     stretch=1.02, glow=1.1, schwung=1.0),
    ]

    # Fernkampf: sie zieht sich zusammen und stoesst den Ton aus.
    # Auch hier ein Bild mehr - das Zusammenziehen davor ist die Ansage.
    anims["cast"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("cast"), phase=0.2, stretch=0.86,
                     lean=-1.4, settle=1, glow=0.9),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("cast"), phase=1.0, stretch=0.94,
                     lean=-0.4, glow=1.2),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("cast"), phase=1.8, stretch=1.18,
                     lean=1.4, split=0.32, glow=1.9),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("cast"), phase=2.9, stretch=1.04,
                     lean=0.4, split=0.10, glow=1.3),
    ]

    # Treffer: sie zerfaellt fast.
    anims["hurt"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("hurt"), phase=1.9, lean=-3.4,
                     stretch=0.84, split=0.85, smear=0.45, sway=-2.2,
                     glow=0.4, alpha_body=195),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("hurt"), phase=2.9, lean=-2.2,
                     stretch=0.90, split=0.45, smear=0.25, sway=-1.2,
                     glow=0.6, alpha_body=220),
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("hurt"), phase=3.9, lean=-1.0,
                     stretch=0.97, split=0.15, sway=-0.4,
                     glow=0.85, alpha_body=240),
    ]

    # Rast: sie sinkt zu einer Lache zusammen.
    anims["rest"] = [
        draw_heroine(instrument=instrument, garment=garment,
                     signatur=laut("rest"), phase=i / 5 * math.tau,
                     stretch=0.58, settle=4, glow=1.2,
                     sway=math.sin(i / 5 * math.tau) * 0.35)
        for i in range(5)
    ]

    return anims


# ------------------------------------------------------------- Kreaturen
#
# Die Bewohner sind aus demselben Stoff wie Cadence - und genau daran
# erkennt man, was ihnen fehlt.
#
# Sie hat eine Scherbe in sich, die leuchtet. Die Kreaturen haben an
# derselben Stelle **ein Loch**: einen hellen Rand um nichts. Das ist die
# eine Regel, die alle teilen, und sie wird auch gezeichnet - eine dunkle
# Mulde mit heller Kante, in der kein Licht steht. Darum sind sie boese
# und darum sind sie zu bedauern; beides in derselben Form.
#
# Zwei Regeln kommen dazu, damit die Silhouetten nicht ineinanderlaufen:
#
# 2. **Jede Kreatur hat genau eine harte Kante.** Bei der Maus die
#    Gabelohren, beim Schreiter die Platte, bei der Knospe die
#    aufgesprungene Schale. Alles andere an ihr ist weich oder Dunst.
# 3. **Die Farbe sagt, wie weit sie fort ist.** Was noch klingt, hat
#    Fluegellicht (BLOOM/GLOW); was verstummt ist, ist Stein; was falsch
#    klingt, ist rot.

def _flaeche(c: Canvas, punkte, farbe, kante=None) -> None:
    """
    Fuellt ein Vieleck.

    Der erste Anlauf zeichnete die Kreaturen aus Linien, und aus Linien
    wird bei zwanzig Pixeln Matsch: man sieht ein Gekritzel, keine
    Gestalt. Eine Kreatur braucht zuerst eine geschlossene Flaeche, und
    erst danach Kanten darauf.
    """
    if len(punkte) < 3:
        return
    ymin = int(math.floor(min(p[1] for p in punkte)))
    ymax = int(math.ceil(max(p[1] for p in punkte)))
    for y in range(ymin, ymax + 1):
        schnitte = []
        for i in range(len(punkte)):
            x0, y0 = punkte[i]
            x1, y1 = punkte[(i + 1) % len(punkte)]
            if (y0 <= y < y1) or (y1 <= y < y0):
                schnitte.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
        schnitte.sort()
        for k in range(0, len(schnitte) - 1, 2):
            a, b = int(round(schnitte[k])), int(round(schnitte[k + 1]))
            for x in range(a, b + 1):
                c.set(x, y, farbe)
    if kante is not None:
        for i in range(len(punkte)):
            c.line(*punkte[i], *punkte[(i + 1) % len(punkte)], kante)


def _kante_licht(c: Canvas, oben, unten) -> None:
    """
    Legt Licht auf die Oberkante und Schatten unter die Unterkante.

    Innen aufgehellte Flecken sahen bei diesen Groessen aus wie
    aufgeklebte Kaesten - eine Ellipse mit drei Pixeln Radius ist eben
    ein Rechteck. Der Rand dagegen folgt immer der Form, die wirklich da
    ist, und macht aus einem flachen Klecks einen Koerper.

    Wird mitten im Zeichnen gerufen: nur was bis dahin steht, bekommt
    Licht. Beine und Ohren, die danach kommen, bleiben unberuehrt.
    """
    for x in range(c.w):
        spalte = [y for y in range(c.h) if c.get(x, y)[3] > 40]
        if not spalte:
            continue
        c.set(x, spalte[0], oben)
        if len(spalte) > 2:
            c.set(x, spalte[-1], unten)


def _hohlraum(c: Canvas, cx: float, cy: float, r: float, rand,
              puls: float = 0.0) -> None:
    """
    Das Loch, wo der Kern sein sollte.

    Nicht dunkel gefuellt - *ausgeschnitten*: der Rand leuchtet, das
    Innere ist Leere in der Farbe des Nichts. Ein Ring allein saehe aus
    wie ein Auge, also sitzt darin eine Spur Rest, die nicht ganz mittig
    steht: etwas ist herausgebrochen, und der Bruch war nicht sauber.

    Unter drei Pixeln Radius wird aus einem Kreis ein Kaestchen, und ein
    Kaestchen sieht aufgeklebt aus. Kleine Hohlraeume werden darum als
    Raute gezeichnet - die hat auch bei fuenf Pixeln noch eine Richtung.
    """
    leer = hexc("#04050a")
    saum = mix(rand, leer, 0.15 + 0.30 * puls)
    if r < 2.2:
        ix, iy = int(round(cx)), int(round(cy))
        c.set(ix, iy, leer)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            c.set(ix + dx, iy + dy, saum)
        c.set(ix, iy - 1, mix(saum, P.BONE, 0.3))
        return
    # Der Rand liegt aussen und ist hell, die Leere darin ist klein. Waere
    # es umgekehrt, saehe das Loch aus wie ein schwarzer Kasten, den
    # jemand aufs Bild gelegt hat.
    c.ellipse(cx, cy, r, r, saum)
    c.ellipse(cx, cy, r - 1.0, r - 1.0, leer)
    c.set(int(cx - r * 0.4), int(cy + r * 0.35), mix(rand, P.BONE, 0.35))
    c.set(int(cx), int(cy - r + 0.5), mix(saum, P.BONE, 0.35))


def draw_gabelmaus(phase: float) -> Canvas:
    """
    Gabelmaus - das erste, was einem im Hain begegnet.

    Sie ist der Entwurf, der als Heldin nicht taugte: rundlicher Flaum,
    zwei symmetrische Zinken mit leuchtenden Spitzen, alles putzig. Als
    Tier stimmt genau das - die Zinken sind hier Ohren, und dass sie
    aussehen wie eine Stimmgabel, ist der ganze Witz der Kreatur: sie
    hat den Ton, der Cadence fehlt, und traegt ihn spazieren.

    Sie huscht in Schueben. Der Zyklus ist darum ungleich verteilt: vier
    schnelle Bilder Lauf, zwei in denen sie fast steht und die Ohren
    zucken.
    """
    c = Canvas(24, 20)
    base = 19

    sitz = max(0.0, math.cos(phase)) ** 2   # 1 = sitzt, 0 = rennt
    lauf = 1 - sitz
    takt = math.sin(phase * 2)
    hop = max(0.0, takt) * 1.7 * lauf
    by = base - 6.4 - hop                   # Ruecken-/Bauchmitte
    duck = sitz * 0.8                       # im Sitzen richtet sie sich auf

    # Sie muss sich vom Hain abheben, und der Hain ist dunkelgruen. Ein zu
    # dunkles Fell verschwindet darin - der erste Gegner des Spiels darf
    # aber nie uebersehen werden.
    fell = mix(P.CLOAK, P.STONE, 0.85)
    fell_hi = mix(fell, P.BONE, 0.34)
    fell_lo = shade(fell, -0.38)
    ader = mix(P.TRIM, P.BONE, 0.5)

    # Zwei Kreise machen ein Tier: ein grosser Rumpf hinten, ein kleiner
    # Kopf vorn, halb ineinander. Der Versuch, den Leib in einem Zug als
    # Tropfen zu ziehen, ergab einen Keil - zwei Formen lesen sich bei
    # dieser Groesse einfach besser als eine kluge.
    rx, ry = 8.6, by                     # Rumpfmitte
    kx, ky = 15.4, by - 1.7 - duck       # Kopfmitte

    c.ellipse(rx, ry, 4.4, 3.8, fell)
    c.ellipse(kx, ky, 2.8, 2.6, fell)
    # Der Hals: nur so viel Masse, dass Kopf und Rumpf zusammenhaengen.
    # Zu viel davon, und aus zwei Formen wird wieder ein Laib.
    _flaeche(c, [(rx + 3.0, ry - 1.6), (kx - 1.8, ky - 1.0),
                 (kx - 1.4, ky + 1.8), (rx + 3.0, ry + 2.2)], fell)
    # Schnauze: ein kurzer Keil nach vorn, sonst endet der Kopf stumpf.
    _flaeche(c, [(kx + 1.2, ky - 1.4), (kx + 4.4, ky + 0.6),
                 (kx + 1.2, ky + 1.8)], fell)
    _kante_licht(c, fell_hi, fell_lo)

    # Flaum: der Umriss franst aus, sonst ist sie ein Stein mit Ohren.
    for i in range(20):
        a = i / 20 * math.tau
        if hash01(i, int(phase * 4)) > 0.5:
            c.set(int(round(rx + math.cos(a) * 5.0)),
                  int(round(ry + math.sin(a) * 4.4)), shade(fell, -0.08))

    # Schwanz: duenn, lang, schwingt gegenlaeufig - und endet in einer
    # kleinen Gabel, damit auch von hinten klar ist, was sie ist.
    schwung = math.sin(phase * 2 + 1.3) * 2.8
    sp = [(rx - 3.6, ry + 1.4), (rx - 6.4, ry - 0.6 + schwung * 0.4),
          (rx - 8.6, ry - 2.6 + schwung)]
    for i in range(len(sp) - 1):
        c.line(*sp[i], *sp[i + 1], fell_lo)
    ex, ey = sp[-1]
    for k in (-1, 1):
        c.line(ex, ey, ex - 1.4, ey + k * 1.4, mix(fell, ader, 0.35))

    # Vier Nadelbeine, paarweise gegenlaeufig. Dieselben Spitzen, auf
    # denen auch Cadence steht - nur kuerzer und zu viert.
    for ox, ph in ((-2.6, 0.0), (-1.0, math.pi), (4.6, math.pi), (6.2, 0.0)):
        s = math.sin(phase * 2 + ph) * lauf
        hx = rx + ox
        fx = hx + s * 1.8
        fy = base - max(0.0, s) * 2.0 - hop
        c.line(hx, ry + 2.2, fx, fy, fell_lo)
        c.line(hx, ry + 2.2, hx + (fx - hx) * 0.4, ry + 2.2 + (fy - ry - 2.2) * 0.4,
               shade(fell, -0.18))
        c.set(int(round(fx)), int(round(fy)), mix(fell, ader, 0.3))

    # Die Gabelohren. Zwei Zinken auf einem Steg - erst der Steg macht
    # aus zwei Ohren eine Stimmgabel.
    oy = ky - 2.4
    zuck = sitz * math.sin(phase * 7) * 0.26
    c.line(kx - 1.4, oy, kx + 1.4, oy, mix(fell_hi, ader, 0.4))
    for seite in (-1, 1):
        a = -math.pi / 2 + seite * (0.24 + zuck)
        n = 5
        for i in range(n + 1):
            x = kx + seite * 1.4 + math.cos(a) * i
            y = oy + math.sin(a) * i
            c.set(int(round(x)), int(round(y)), mix(fell_hi, ader, i / n * 0.7))
        sx = int(round(kx + seite * 1.4 + math.cos(a) * n))
        sy = int(round(oy + math.sin(a) * n))
        c.set(sx, sy, mix(ader, P.BONE, 0.55))
        c.glow(sx, sy, 2.5, (ader[0], ader[1], ader[2], 52))

    # Augen: zwei warme Punkte uebereinander am Kopf, das obere hell.
    # Rosa gehoert Cadence allein.
    c.set(int(kx + 1), int(round(ky - 0.2)), P.AMBER)
    c.set(int(kx + 1), int(round(ky + 0.8)), shade(P.AMBER, -0.45))

    # Und die Regel: in der Flanke fehlt ihr etwas. Klein, dunkel und weit
    # hinten - sonst liest es sich als Auge, und Augen hat sie schon.
    _hohlraum(c, rx - 2.2, ry + 1.0, 1.2,
              mix(ader, P.CLOAK, 0.35), puls=abs(takt))

    c.shadow_pass((0, 1), -0.2)
    c.outline(hexc("#05060c", 210))
    return c


def draw_klangmotte(phase: float) -> Canvas:
    """
    Klangmotte - taumelnder Falter aus verklungenen Toenen.

    Ihre Fluegel sind keine Fluegel, sondern Wellen: drei Boegen
    uebereinander, die beim Schlag zusammenlaufen und beim Oeffnen
    auseinanderdriften. Was von ihr abfaellt, ist Staub aus alten Toenen.
    """
    c = Canvas(26, 22)
    cx, cy = 13, 11
    flap = math.sin(phase)
    taumel = math.cos(phase * 1.3) * 0.9
    my = cy + taumel * 0.5

    fluegel = mix(P.BLOOM_DIM, P.INK2, 0.35)
    fluegel_hi = mix(P.BLOOM, P.BONE, 0.15)

    for seite in (-1, 1):
        # Zwei Fluegel je Seite - ein grosser oben, ein deutlich kleinerer
        # unten. Gleich grosse Fluegel ergeben ein Kreuz; erst das
        # Missverhaeltnis liest sich als Falter. Der Schlag dreht sie um
        # die Schulter, statt sie zu strecken: gestreckte Fluegel sehen
        # aus wie Bretter.
        for gross in (True, False):
            w = 10.2 if gross else 5.0
            h = 4.6 if gross else 2.4
            dreh = (-0.40 if gross else 0.62) + flap * (0.34 if gross else 0.24)
            sx, sy = cx + seite * 1.6, my - (1.6 if gross else -1.8)
            ecken = []
            for ex, ey in ((0.1, -0.2), (0.55, -1.0), (1.0, -0.15),
                           (0.85, 0.75), (0.3, 0.6)):
                px, py = ex * w, ey * h
                ecken.append((sx + seite * (px * math.cos(dreh) - py * math.sin(dreh)),
                              sy + px * math.sin(dreh) + py * math.cos(dreh)))
            _flaeche(c, ecken, fluegel)
            # Die Adern sind Wellen: drei Boegen ueber den Fluegel, so
            # dass man sieht, dass er aus Klang besteht und nicht aus Haut.
            for k in range(3):
                t = 0.3 + k * 0.26
                a0 = (sx + seite * ((0.15 * w) * math.cos(dreh) - (t * 2 - 1) * h * 0.5 * math.sin(dreh)),
                      sy + (0.15 * w) * math.sin(dreh) + (t * 2 - 1) * h * 0.5 * math.cos(dreh))
                a1 = (sx + seite * ((0.95 * w) * math.cos(dreh) - (t * 2 - 1) * h * 0.4 * math.sin(dreh)),
                      sy + (0.95 * w) * math.sin(dreh) + (t * 2 - 1) * h * 0.4 * math.cos(dreh))
                c.line(*a0, *a1, mix(fluegel, fluegel_hi, 0.45 - k * 0.1))

    # Leib: eine Spindel, deutlich dunkler als die Fluegel. Sie muss
    # breit genug sein, um zwischen den Fluegeln zu bestehen - sonst
    # sieht der Falter aus wie vier Blaetter ohne Mitte.
    c.ellipse(cx, my, 2.4, 4.2, hexc("#0b0f1c"))
    c.ellipse(cx, my - 3.0, 2.0, 1.8, P.INK2)          # Kopf
    for y in range(int(my - 4), int(my + 5)):
        c.set(cx - 2, y, mix(P.INK2, P.BLOOM, 0.30))   # Lichtkante links
    # Der Hinterleib ist geringelt - drei Striche genuegen dafuer.
    for i in range(3):
        c.rect(cx - 1, int(my + 1 + i * 1.4), 3, 1, mix(P.INK2, P.BLOOM_DIM, 0.45))

    # Fuehler: zwei gefiederte Boegen, nach aussen gekruemmt.
    for seite in (-1, 1):
        for i in range(6):
            t = i / 5
            x = cx + seite * (1.4 + t * 3.8)
            y = my - 4.4 - t * 3.4
            c.set(int(round(x)), int(round(y)), mix(P.BLOOM, P.BONE, 0.25 + t * 0.45))
            if i and i % 2 == 0:
                c.set(int(round(x)) + seite, int(round(y)) + 1, P.BLOOM_DIM)

    _hohlraum(c, cx, my + 0.4, 1.5, P.BLOOM, puls=abs(flap))

    # Tonstaub faellt von ihr ab - das Einzige an ihr, das nach unten will.
    for i in range(3):
        t = (phase / math.tau + i / 3) % 1.0
        c.set(int(cx + math.sin(phase + i * 2) * 3.5), int(my + 5 + t * 6),
              (P.BLOOM[0], P.BLOOM[1], P.BLOOM[2], int(170 * (1 - t))))

    c.outline(hexc("#05060c", 200))
    c.glow(cx, my, 10, (P.BLOOM[0], P.BLOOM[1], P.BLOOM[2], 34))
    return c


def draw_stilleschreiter(phase: float, sturm: float = 0.0) -> Canvas:
    """
    Stilleschreiter - schwerer Waechter, der Klang schluckt.

    Er ist das Gegenstueck zu Cadence: sie ist Licht in einem Gefaess, er
    ist ein Gefaess ohne Licht. Also bekommt er als Einziger im Spiel
    ueberhaupt keine Leuchtfarbe - nur Stein, und in den Fugen zwischen
    seinen Platten steht ein kalter Rest, der beim Schritt aufblitzt.
    Sein Kopf ist eine heruntergezogene Haube ueber nichts.
    """
    c = Canvas(30, 28)
    cx, base = 15, 27
    step = math.sin(phase)
    heben = abs(step) * 1.1
    # Beim Ansturm geht er in die Hocke und nach vorn - erst dadurch
    # sieht man ihm an, dass gleich etwas passiert. Ein Gegner ohne
    # Ansage ist kein Gegner, sondern eine Falle.
    ky = base - 15 - heben + sturm * 3.0

    stein = P.STONE
    stein_hi = P.STONE_HI
    stein_lo = P.STONE_LO
    fuge = mix(P.GLOW_DIM, P.STONE, 0.55)

    # Zwei schwere Beine. Keine Spitzen - er steht auf Flaechen, und man
    # soll ihn stehen hoeren.
    for i, s in enumerate((step, -step)):
        x = cx - 6 + i * 8 + s * 2.2
        _flaeche(c, [(cx - 3 + i * 6, ky + 5), (cx - 0.5 + i * 6, ky + 5),
                     (x + 3.4, base - 3), (x, base - 3)], shade(stein, -0.30))
        c.rect(int(x) - 1, base - 3, 6, 2, shade(stein, -0.38))
        c.rect(int(x) - 2, base - 1, 8, 1, stein_lo)

    # Der Rumpf haengt vornueber: eine Masse, die zu schwer fuer sich
    # selbst ist. Ein aufrechter Rumpf saehe aus wie eine Ruestung.
    v = sturm * 3.5
    _flaeche(c, [(cx - 8.5 + v, ky - 3), (cx + 5.0 + v, ky - 5.5),
                 (cx + 8.0 + v, ky + 1), (cx + 5.5 + v, ky + 6),
                 (cx - 6.0 + v, ky + 6.5), (cx - 9.5 + v, ky + 2)],
             stein)
    _kante_licht(c, stein_hi, stein_lo)

    # Ruecken: drei Platten wie Deckel auf einem Kessel. In den Fugen
    # dazwischen steht der Rest Klang, den er noch nicht geschluckt hat -
    # und der blitzt beim Schritt auf.
    for i in range(3):
        px, py = cx - 9 + i * 4.4, ky - 5.5 + i * 1.1
        _flaeche(c, [(px, py), (px + 4.2, py - 0.8), (px + 4.6, py + 4.4),
                     (px + 0.4, py + 5.0)], mix(stein_hi, P.INK2, 0.35))
        c.line(px, py, px + 4.2, py - 0.8, stein_hi)
        c.line(px + 4.4, py - 0.4, px + 4.8, py + 4.6,
               mix(fuge, stein, 0.5 - 0.35 * abs(math.sin(phase * 2 + i))))

    # Haube: faellt vorn ueber den Kopf und laesst nur Schatten frei.
    #
    # Ein schwarzes Rechteck als Gesicht sah aus wie ein Loch im Bild,
    # nicht wie eine Oeffnung an ihm. Der Schatten hat darum jetzt die
    # Form der Haube - er laeuft nach unten breiter, wie die Oeffnung
    # selbst - und darunter liegt die Lippe des Stoffs im Licht.
    hx, hy = cx + 3.5 + sturm * 4.5, ky - 7.5
    _flaeche(c, [(hx - 1.6, hy), (hx + 1.8, hy + 0.4), (hx + 4.2, hy + 6.5),
                 (hx - 3.4, hy + 6.0)], mix(stein, P.INK2, 0.30))
    c.line(hx - 1.6, hy, hx + 1.8, hy + 0.4, stein_hi)
    _flaeche(c, [(hx - 1.8, hy + 3.0), (hx + 2.2, hy + 3.2),
                 (hx + 3.0, hy + 6.2), (hx - 2.4, hy + 6.0)], hexc("#04050a"))
    c.line(hx - 1.8, hy + 3.0, hx + 2.2, hy + 3.2, mix(stein, P.INK2, 0.55))
    c.line(hx - 2.4, hy + 6.0, hx + 3.0, hy + 6.2, mix(stein_lo, stein, 0.45))

    # Auch er hat das Loch. Bei ihm sitzt es tief in der Brust, halb von
    # der Haube verdeckt: dass ihm etwas fehlt, sieht man erst genau hin.
    _hohlraum(c, cx + 3, ky + 2.5, 2.4, fuge, puls=abs(step) * 0.5)

    c.shadow_pass((0, 1), -0.22)
    c.outline(hexc("#05060c", 225))
    return c


def draw_dissonanzknospe(phase: float, spucken: float = 0.0) -> Canvas:
    """
    Dissonanzknospe - festgewachsen, spuckt schiefe Toene.

    Keine Blume. Eine Schale, die aufgesprungen ist: vier harte Scherben
    klappen zurueck und geben ein Inneres frei, in dem drei Linien
    stehen, die nicht zueinander passen. Genau das ist ein schiefer
    Akkord - man sieht ihn, bevor man ihn hoert.
    """
    c = Canvas(24, 26)
    cx, base = 12, 25
    # Beim Spucken reisst sie weiter auf als im Atmen - und zuckt dabei
    # zusammen. Wer das einmal gesehen hat, weiss beim naechsten Mal,
    # wann der Schuss kommt.
    auf = max(0.0, math.sin(phase)) ** 0.7      # 0 zu, 1 offen
    auf = min(1.0, auf + spucken * 0.8)
    ky = base - 11.5                             # Mitte der Schale

    stiel = mix(P.ROT_DIM, P.INK2, 0.35)
    schale = mix(P.ROT_DIM, P.STONE, 0.34)
    schale_hi = mix(schale, P.BONE, 0.26)
    schale_lo = shade(schale, -0.35)

    # Stiel: steif, nicht biegsam. Sie ist eingewachsen, nicht gepflanzt -
    # also verdickt er sich nach unten und greift mit Wurzeln in den Boden.
    #
    # Er muss deutlich duenner sein als die Schale. Vorher waren beide
    # gleich breit, und daraus wurde eine Saeule mit einem Deckel - ohne
    # Taille sieht nichts gewachsen aus.
    _flaeche(c, [(cx - 0.9, ky + 2), (cx + 1.1, ky + 2),
                 (cx + 2.8, base - 1), (cx - 2.6, base - 1)], stiel)
    c.line(cx - 0.9, ky + 2, cx - 2.6, base - 1, mix(stiel, P.STONE, 0.3))
    for k in (-1, 1):
        c.line(cx + k * 2.0, base - 3, cx + k * 6.0, base - 1, shade(stiel, -0.1))
        c.line(cx + k * 1.4, base - 2, cx + k * 3.6, base - 1, shade(stiel, -0.25))
    c.rect(cx - 7, base - 1, 15, 1, shade(stiel, -0.3))

    # Vier Schalenscherben. Sie klappen auf wie etwas, das gebrochen ist -
    # deshalb bleibt jede gerade und keine biegt sich. Geschlossen bilden
    # sie ein Ei mit einem Riss darin.
    for seite in (-1, -0.42, 0.42, 1):
        a = -math.pi / 2 + seite * (0.30 + auf * 0.86)
        laenge = 9.0 - abs(seite) * 1.6
        # Geschlossen muessen die vier Scherben zusammen ein Ei ergeben,
        # also sind die aeusseren breiter als die inneren.
        breit = 1.5 + abs(seite) * 0.9
        ax, ay = math.cos(a), math.sin(a)
        _flaeche(c, [(cx - ay * breit, ky + ax * breit),
                     (cx + ax * laenge - ay * breit * 0.35,
                      ky + ay * laenge + ax * breit * 0.35),
                     (cx + ax * laenge + ay * breit * 0.35,
                      ky + ay * laenge - ax * breit * 0.35),
                     (cx + ay * breit, ky - ax * breit)], schale)
        # Aussenkante hell, Innenkante dunkel: erst dadurch wird aus dem
        # Splitter eine Schale mit Innen und Aussen.
        c.line(cx - ay * breit, ky + ax * breit,
               cx + ax * laenge - ay * breit * 0.35,
               ky + ay * laenge + ax * breit * 0.35,
               schale_hi if seite < 0 else schale_lo)
        c.set(int(round(cx + ax * laenge)), int(round(ky + ay * laenge)),
              mix(schale_hi, P.WARM, 0.35))

    # Das Innere: drei Striche in drei Winkeln, die sich nicht treffen.
    # Ein Akkord, in dem jeder Ton woanders steht - man sieht die
    # Dissonanz, bevor man sie hoert.
    if auf > 0.12:
        for i, w in enumerate((-0.95, -0.05, 0.75)):
            laenge = (2.6 + i * 1.2) * auf
            c.line(cx, ky, cx + math.cos(-math.pi / 2 + w) * laenge,
                   ky + math.sin(-math.pi / 2 + w) * laenge,
                   mix(P.ROT, P.WARM, 0.25 + 0.25 * math.sin(phase * 3 + i)))

    _hohlraum(c, cx, ky, 2.3 + spucken * 0.9, P.ROT, puls=auf)
    if spucken > 0.3:
        # Der Ton verlaesst sie sichtbar, bevor er fliegt.
        c.glow(cx, ky, 12 * spucken, (P.ROT[0], P.ROT[1], P.ROT[2],
                                      int(70 * spucken)), power=1.8)

    c.outline(hexc("#05060c", 210))
    c.glow(cx, ky, 9, (P.ROT[0], P.ROT[1], P.ROT[2], int(24 + 44 * auf)))
    return c


def draw_echoscherbe(phase: float) -> Canvas:
    """
    Echoscherbe - springender Kristallsplitter.

    Sie heisst Echo, also zeichnet sie sich selbst mehrfach: hinter der
    Scherbe stehen zwei blassere Kopien in aelteren Drehungen. Was man
    trifft, ist die scharfe vorne - die anderen sind schon vorbei.
    """
    c = Canvas(20, 20)
    cx, cy = 10, 10

    def splitter(spin: float, gr: float, flaeche, kante, facette=None) -> None:
        # Vier Ecken, ungleich lang: ein Kristall ist nie regelmaessig.
        pts = []
        for i, r in enumerate((1.0, 0.62, 0.9, 0.55)):
            a = spin + i / 4 * math.tau
            pts.append((cx + math.cos(a) * gr * r, cy + math.sin(a) * gr * r))
        _flaeche(c, pts, flaeche, kante)
        if facette is not None:
            # Eine Bruchkante quer durch: erst die macht aus dem Viereck
            # einen Kristall statt eines Papierschnipsels.
            c.line(pts[0][0], pts[0][1], pts[2][0], pts[2][1], facette)
            c.line((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2,
                   cx, cy, facette)

    # Erst die Echos, dann die scharfe Scherbe darueber.
    for k in (2, 1):
        blass = (P.GLOW_DIM[0], P.GLOW_DIM[1], P.GLOW_DIM[2], 54 - k * 14)
        splitter(phase - k * 0.5, 7.0 - k * 0.7, (0, 0, 0, 0), blass)
    splitter(phase, 7.4, mix(P.GLOW_DIM, P.INK2, 0.62), P.GLOW,
             facette=mix(P.GLOW_DIM, P.GLOW, 0.5))

    _hohlraum(c, cx, cy, 2.0, P.GLOW, puls=abs(math.sin(phase * 2)))

    c.glow(cx, cy, 10, (P.GLOW[0], P.GLOW[1], P.GLOW[2], 44))
    return c


def draw_auftakt(phase: float, schlag: float = 0.0, wut: float = 0.0,
                 wurf: float = 0.0) -> Canvas:
    """
    DER GROSSE AUFTAKT - der erste Boss.

    Zwei Fehler in den Anlaeufen davor, und beide lagen nicht am Motiv.

    Der erste: er war zu gross. Eine Gestalt, die den halben Bildschirm
    fuellt, ist nicht bedrohlich, sie ist unhandlich - man sieht sie nicht
    mehr im Ganzen, und im Kampf verdeckt sie den Boden, auf dem man
    steht. Er ist jetzt knapp dreimal so hoch wie Cadence. Das reicht.

    Der zweite: er war flach. Der Stoff war eine Flaeche in einer Farbe
    mit ein paar Strichen darauf, und daran erkennt man Zeichnung, die
    nicht zu Ende gefuehrt ist. Cadence bekommt ihre Form aus einem
    Verlauf quer ueber den Koerper, aus Koernung und aus einer Lichtkante
    - er bekommt jetzt dasselbe: jede Zeile des Stoffs wird von links
    nach rechts durchgeschattet, die Falten sind weiche Taeler statt
    Striche, und wo etwas ueber etwas anderem liegt, liegt Schatten.

    `schlag` 0 = Ausholen, 1 = Schlag. `wut` faerbt ihn in der zweiten
    Haelfte um.
    """
    c = Canvas(86, 118)
    base = 112
    cx = 40

    # `wurf` hebt ihn beim Schattenwurf an den Faeden hoch: die Krone
    # zieht, der Stoff folgt spaeter. Genau das macht ihn zur Marionette
    # statt zur Figur, die sich selbst bewegt.
    schweb = math.sin(phase) * 1.7 - wurf * 5.0
    zug = math.sin(phase * 0.7 + 1.1) * 1.1 + wurf * 2.5
    # Der erste Anlauf mit Schattierung war richtig gerechnet und
    # trotzdem unbrauchbar: die Werte lagen alle drei so tief, dass die
    # Form zwar da war, aber niemand sie sah. Eine Schattierung braucht
    # Spielraum - zwischen dunkelstem und hellstem Ton muss genug liegen.
    stoff_lo = hexc("#070912")
    stoff_mid = mix(P.CLOAK, P.STONE, 0.62)
    stoff_hi = mix(stoff_mid, P.BONE, 0.34)
    bein = mix(P.BONE, P.STONE, 0.18)
    bein_lo = mix(bein, P.INK2, 0.50)
    akzent = mix(P.ROT, P.WARM, 0.30) if wut > 0.5 else P.TRIM

    def stoffton(q: float, tiefe: float = 0.0, koernung: int = 0):
        """
        Die Farbe des Stoffs an einer Stelle.

        `q` ist die Lage quer ueber die Form, -1 links bis +1 rechts.
        Das Licht kommt von rechts oben, also liegt dort ein heller Grat,
        und ganz aussen kippt es wieder ab - so wirkt eine Flaeche rund
        statt flach. `tiefe` verdunkelt zusaetzlich (Falten, Ueberlappung).
        """
        # Rund statt flach: hell bei q ~ 0.6, dunkel nach beiden Seiten.
        # Breiter Lichtgrat statt schmalem Streifen: sonst ist fast die
        # ganze Flaeche im Abfall und damit wieder eintoenig.
        licht = 0.30 + 0.70 * math.exp(-((q - 0.45) ** 2) / 0.72)
        rand = max(0.0, abs(q) - 0.86) / 0.14          # Abkippen ganz aussen
        wert = licht * (1 - rand * 0.7) - tiefe
        wert = max(0.0, min(1.0, wert))
        farbe = mix(stoff_lo, stoff_mid, min(1.0, wert * 1.55))
        if wert > 0.64:
            farbe = mix(stoff_mid, stoff_hi, (wert - 0.64) / 0.36)
        if koernung and hash01(koernung, int(q * 40)) > 0.86:
            farbe = shade(farbe, -0.09)
        return farbe

    schulter_y = base - 66
    ky = schulter_y - 30 + schweb

    # ---- Die Faeden, an denen er haengt. Sie liegen hinter allem.
    for i, (ax, sx) in enumerate(((-20, -13), (-8, -5), (8, 6), (20, 14))):
        n = int(schulter_y - ky - 3)
        for k in range(max(0, n)):
            t = k / max(1, n)
            x = cx + ax + (sx - ax) * t + zug * (1 - t) * 0.5
            if hash01(int(x), i) > 0.16:
                c.set(int(round(x)), int(ky + 9 + k), mix(bein_lo, stoff_mid, 0.5))

    # ---- Die Robe. Jede Zeile wird quer durchgeschattet, nicht gefuellt.
    falten = (-0.72, -0.34, 0.04, 0.40, 0.76)
    for y in range(schulter_y, base + 1):
        t = (y - schulter_y) / (base - schulter_y)
        halb = 8 + t ** 1.45 * 18
        neig = schweb * (1 - t) * 0.4 - t * 3
        links = cx - halb + neig
        for x in range(int(links), int(cx + halb + neig) + 1):
            q = (x - (cx + neig)) / halb
            # Falten: weiche Taeler, keine Striche. Nach unten laufen sie
            # auseinander, weil der Stoff dort weiter faellt.
            tiefe = 0.0
            for f in falten:
                d = abs(q - f * (0.6 + 0.4 * t))
                if d < 0.16:
                    tiefe = max(tiefe, (1 - d / 0.16) * 0.42)
            # Unten wird es schwerer: der Saum liegt im Eigenschatten.
            tiefe += t * 0.22
            c.set(x, y, stoffton(q, tiefe, koernung=y))
        # Lichtkante rechts, Abschluss links.
        c.set(int(cx + halb + neig), y, mix(stoff_hi, P.STONE, 0.35))
        c.set(int(links), y, stoff_lo)

    # Zerfetzter Saum: Zipfel verschiedener Laenge, im Eigenschatten.
    for x in range(cx - 26, cx + 24):
        if hash01(x, 5) > 0.32:
            for k in range(1 + int(hash01(x, 9) * 5)):
                if hash01(x, k + 13) > 0.22:
                    c.set(x - 3, base + k, mix(stoff_lo, stoff_mid, 0.35 - k * 0.06))

    # ---- Schultern: eckig, ungleich hoch, und ebenfalls durchgeschattet.
    for y in range(schulter_y - 6, schulter_y + 11):
        t = (y - (schulter_y - 6)) / 17
        halb = 15 + t * 6
        for x in range(int(cx - halb - 2), int(cx + halb)):
            q = (x - cx) / halb
            c.set(x, y, stoffton(q, 0.10 + t * 0.18, koernung=y * 3))
        c.set(int(cx + halb) - 1, y, mix(stoff_hi, P.STONE, 0.28))
        c.set(int(cx - halb - 2), y, stoff_lo)

    for i in range(6):
        t = i / 5
        x = cx - 16 + i * 6.4
        hoehe = 3 + int(abs(math.sin(t * math.pi + 0.4)) * 6)
        c.line(x, schulter_y - 5, x + (t - 0.5) * 6, schulter_y - 5 - hoehe,
               mix(bein_lo, stoff_mid, 0.3))
        c.set(int(x + (t - 0.5) * 6), schulter_y - 5 - hoehe, mix(bein, akzent, 0.35))

    # ---- Die Kapuze: leer, und man sieht hinein.
    hy = schulter_y - 8
    for y in range(hy - 11, hy + 11):
        t = (y - (hy - 11)) / 22
        halb = 3.6 + 6.6 * t ** 0.4
        neig = schweb * 0.25 * (1 - t) - t
        for x in range(int(cx - halb + neig), int(cx + halb + neig) + 1):
            q = (x - (cx + neig)) / halb
            c.set(x, y, stoffton(q, 0.06 + t * 0.10, koernung=y * 7))
        c.set(int(cx + halb + neig), y, mix(stoff_hi, P.STONE, 0.3))
        c.set(int(cx - halb + neig), y, stoff_lo)
        if t > 0.2:
            innen = (halb - 2.6) * ((t - 0.2) / 0.8) ** 0.32
            if innen > 0.8:
                c.rect(int(cx - innen + neig), y, int(innen * 2), 1, hexc("#020307"))
                c.set(int(cx - innen + neig) - 1, y, mix(stoff_hi, bein, 0.25))
    c.glow(cx - 1, hy + 4, 7, (akzent[0], akzent[1], akzent[2], int(38 + 55 * wut)))
    for k in (-2, 2):
        c.set(cx + k, hy + 3, mix(akzent, P.BONE, 0.5))

    # ---- Die Krone. Auch Knochen ist rund: die Sichel bekommt oben
    # Licht, unten Schatten, und an der Bruchkante eine harte Naht.
    for i in range(-24, 25):
        t = abs(i) / 24
        dicke = int(5 * (1 - t ** 1.5)) + 1
        y = ky + t ** 2.1 * 9 + (0 if i < 0 else 1)
        for d in range(dicke):
            v = d / max(1, dicke - 1)
            ton = mix(mix(bein, P.BONE, 0.35 * (1 - v)), bein_lo, v ** 0.7)
            if hash01(i, d) > 0.9:
                ton = shade(ton, -0.12)
            c.set(cx + i, int(y) + d, ton)
        c.set(cx + i, int(y) + dicke - 1, stoff_lo)
        if hash01(i, 3) > 0.87:
            c.set(cx + i, int(y), mix(bein_lo, stoff_mid, 0.4))
    for seite in (-1, 1):
        laenge = 8 if seite < 0 else 6
        for k in range(laenge):
            c.set(cx + seite * 24, int(ky + 9 - k), mix(bein, akzent, k / laenge * 0.55))
        c.set(cx + seite * 24, int(ky + 9 - laenge), mix(bein, P.BONE, 0.7))
        c.glow(cx + seite * 24, ky + 9 - laenge, 4,
               (akzent[0], akzent[1], akzent[2], 55))

    # Die Maske: kein Gesicht. Ein Spalt, der senkrecht hindurchgeht.
    for y in range(int(ky - 3), int(ky + 13)):
        t = (y - (ky - 3)) / 16
        halb = 4.2 - t * 1.4
        for x in range(int(cx - halb), int(cx + halb) + 1):
            q = (x - cx) / halb
            # Auch Knochen ist gewoelbt: links die Lichtseite, rechts
            # faellt es ab. Ein gleichmaessig heller Block sieht aus wie
            # Papier, das jemand aufgeklebt hat.
            ton = mix(bein_lo, mix(bein, P.BONE, 0.5),
                      max(0.0, 1.0 - abs(q + 0.30) * 1.15))
            c.set(x, y, mix(ton, bein_lo, t * 0.5))
    c.rect(cx, int(ky - 3), 1, 16, hexc("#04050a"))
    c.rect(cx + 1, int(ky - 3), 1, 16, mix(bein_lo, P.INK2, 0.35))
    for k in range(5):
        c.set(cx - 3 + k * 2, int(ky + 12), bein_lo)

    for i, x in enumerate((-17, -12, -6, 9, 14, 19)):
        laenge = 6 + (i * 5) % 9
        for k in range(laenge):
            c.set(cx + x + int(zug * 0.3 * k / laenge), int(ky + 11 + k),
                  mix(bein_lo, stoff_mid, 0.2 + k / laenge * 0.55))
        c.set(cx + x, int(ky + 11 + laenge), mix(bein_lo, akzent, 0.3))

    # ---- Arme: zu lang, zu duenn, mit zu vielen Fingern - und ebenfalls
    # gerundet statt als Strich gezogen.
    def arm(sx, sy, punkte, dick=2.4):
        vor = (sx, sy)
        for i, (px, py) in enumerate(punkte):
            n = max(2, int(math.dist(vor, (px, py))))
            for k in range(n + 1):
                tt = k / n
                x = vor[0] + (px - vor[0]) * tt
                y = vor[1] + (py - vor[1]) * tt
                w = max(1.4, dick - i * 0.35)
                for d in range(-int(w), int(w) + 1):
                    q = d / max(1.0, w)
                    c.set(int(x) + d, int(y), stoffton(-q, 0.12, koernung=int(y)))
            vor = (px, py)
        return vor

    # Beim Schattenwurf geht der Arm nicht nach vorn, sondern hoch.
    hebe = (1 - schlag) * 20 + wurf * 26
    hand = arm(cx - 19, schulter_y + 5,
               [(cx - 30, schulter_y + 9 - hebe * 0.35),
                (cx - 36, schulter_y + 24 - hebe)], dick=2.6)
    for k in range(5):
        laenge = 6 + (k * 3) % 5
        a = 0.5 + k * 0.34
        c.line(hand[0], hand[1],
               hand[0] - math.cos(a) * laenge, hand[1] + math.sin(a) * laenge,
               mix(stoff_hi, bein, 0.3 + k * 0.06))

    # ---- Der Stab mit den Glocken.
    stab_x = cx + 27
    for y in range(int(ky + 8), base + 2):
        for d in (-1, 0, 1):
            c.set(stab_x + d, y, stoffton(-d * 0.7, 0.16, koernung=y))
    arm(cx + 18, schulter_y + 5, [(stab_x - 4, schulter_y + 2), (stab_x, schulter_y + 7)])
    for i in range(4):
        gy = int(ky) + 26 + i * 19
        r = 3 + i * 1.4
        if gy > base - 8:
            break
        for k in range(int(r * 1.6)):
            t = k / (r * 1.6)
            halb = r * (0.35 + 0.75 * t ** 0.7)
            for x in range(int(stab_x - halb), int(stab_x + halb) + 1):
                q = (x - stab_x) / max(1.0, halb)
                c.set(x, gy + k, stoffton(q, 0.28 - (1 - t) * 0.14, koernung=gy + k))
            c.set(int(stab_x + halb), gy + k, mix(stoff_hi, bein, 0.35))
        c.rect(int(stab_x - r * 1.15), gy + int(r * 1.6), int(r * 2.3), 1,
               mix(stoff_hi, bein, 0.22))
        c.rect(stab_x, gy + int(r * 1.6) + 1, 1, 2, mix(bein_lo, stoff_mid, 0.4))
        c.set(stab_x, gy + int(r * 1.6) + 3, mix(akzent, bein, 0.4))

    c.outline(hexc("#05060c", 240))
    c.glow(cx, ky + 4, 30, (akzent[0], akzent[1], akzent[2], int(20 + 28 * wut)),
           power=2.6)
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

    atlas.add_sequence("gabelmaus_husch",
                       [draw_gabelmaus(i / 8 * math.tau) for i in range(8)],
                       pivot=(0.5, 1.0), fps=12)
    atlas.add_sequence("klangmotte_fly",
                       [draw_klangmotte(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 0.5), fps=10)
    atlas.add_sequence("stilleschreiter_sturm",
                       [draw_stilleschreiter(i / 6 * math.tau,
                                             sturm=min(1.0, i / 3))
                        for i in range(6)],
                       pivot=(0.5, 1.0), fps=12)
    atlas.add_sequence("dissonanzknospe_spucken",
                       [draw_dissonanzknospe(i / 5 * math.tau,
                                             spucken=min(1.0, i / 2.5))
                        for i in range(5)],
                       pivot=(0.5, 1.0), fps=11)
    atlas.add_sequence("gabelmaus_sitz",
                       [draw_gabelmaus(math.pi * 2 * 0 + i * 0.11) for i in range(5)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("stilleschreiter_walk",
                       [draw_stilleschreiter(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=7)
    atlas.add_sequence("dissonanzknospe_bloom",
                       [draw_dissonanzknospe(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("echoscherbe_spin",
                       [draw_echoscherbe(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 0.5), fps=12)
    # Der erste Boss. Ausholen ist lang, der Schlag ist kurz - genau so
    # sollen die Bilder verteilt sein, sonst liest sich der Tell nicht.
    atlas.add_sequence("auftakt_idle",
                       [draw_auftakt(i / 8 * math.tau) for i in range(8)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("auftakt_aufschwung",
                       [draw_auftakt(i / 6 * math.tau, schlag=i / 12) for i in range(6)],
                       pivot=(0.5, 1.0), fps=7)
    atlas.add_sequence("auftakt_schatten",
                       [draw_auftakt(i / 6 * math.tau, wurf=min(1.0, i / 4))
                        for i in range(6)],
                       pivot=(0.5, 1.0), fps=9)
    atlas.add_sequence("auftakt_schlag",
                       [draw_auftakt(i / 4 * math.tau, schlag=0.5 + i / 8, wut=0.7)
                        for i in range(4)],
                       pivot=(0.5, 1.0), fps=16)
    atlas.add_sequence("kantor_idle",
                       [draw_kantor(i / 6 * math.tau) for i in range(6)],
                       pivot=(0.5, 1.0), fps=6)
    atlas.add_sequence("kantor_rage",
                       [draw_kantor(i / 6 * math.tau, enraged=True) for i in range(6)],
                       pivot=(0.5, 1.0), fps=9)

    png, js = atlas.write(OUT)
    print(f"characters -> {png.name} ({len(atlas.frames)} Frames), {js.name}")


SIGNATUR = {
    # Wie laut der Kern in welchem Zustand klingt. Der Klang gehoert in den
    # Kampf; beim Herumlaufen soll die Silhouette ruhig bleiben.
    "idle": 0.30, "run": 0.22, "jump": 0.35, "fall": 0.35, "land": 0.45,
    "dash": 0.75, "wall": 0.25, "melee": 0.85, "cast": 1.00, "hurt": 0.55,
    "rest": 0.60,
}


def _fps_for(name: str) -> int:
    return {
        "idle": 6, "run": 13, "jump": 14, "fall": 9, "land": 16,
        "dash": 18, "wall": 7, "melee": 20, "cast": 16, "hurt": 14, "rest": 5,
    }.get(name, 8)


if __name__ == "__main__":
    build()
