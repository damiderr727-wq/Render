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
HERO_W, HERO_H = 28, 30
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
    else:
        a, low, high = 9.4, 0.38, 0.60     # ausgewogen
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
    # Der Schnitt bestimmt die Silhouette, die Oeffnungen den Spielwert.
    #
    #   mantel   - lose, faellt weit, laeuft dem Koerper hinterher
    #   harnisch - starr, geschlossen, laesst nur den Kopf frei
    #   cape     - haengt nur an der Schulter und schwirrt umher
    "mantel": dict(
        openings=4, cut="mantel", deckung=0.64,
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



def _draw_garment(c: Canvas, *, garment: str, kind: str, cx: int, base: float,
                  height: float, phase: float, lean: float, smear: float,
                  split: float, sway: float, hinter: bool) -> None:
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

    # Ein Cape haengt hinter ihr, ein Mantel liegt auf ihr. Deshalb wird das
    # eine vor der Gestalt gezeichnet und das andere danach.
    if (cut == "cape") != hinter:
        return

    if cut == "cape":
        _draw_cape(c, kind=kind, cx=cx, base=base, height=height, phase=phase,
                   lean=lean, smear=smear, sway=sway, coverage=coverage,
                   slits=slits, stoff=stoff, stoff_hi=stoff_hi, licht=saum_licht)
        return

    starr = cut == "harnisch"
    rows = max(2, int(height * coverage))

    for i in range(rows + 1):
        u = i / rows                      # 0 Saum, 1 Kragen
        t = u * coverage                  # in den Einheiten der Gestalt
        y = base - t * height
        hang = (1 - u) ** 2               # wie frei der Stoff haengt

        if starr:
            # Metall haengt nicht. Es sitzt auf ihr und folgt nur der Neigung.
            sx = cx + lean * t
            sx += math.sin(t * 2.6 + phase) * (0.6 + t * 0.9) * 0.5
            # Enger Sitz: die Schienen liegen dicht ueber der Gestalt, unten
            # laeuft der Beintaschen-Rand ein Stueck aus.
            w = _profile(t, kind) * 0.98 + 0.9 + 0.9 * hang
        else:
            # Lose: der Saum haengt weit hinterher und schwingt nach.
            sx = cx + lean * t * (1 - 0.42 * hang)
            sx += math.sin(t * 2.6 + phase - 1.1 * hang) * (0.9 + t * 1.7) * 0.85
            sx += (-lean * 0.75 - smear * 5.5) * hang
            sx += math.sin(phase * 1.3 + sway * 3.0 + u * 2.2) * hang * (1.5 + sway * 2.8)
            # Weit geschnitten: er faellt ueber den Bauch der Gestalt hinaus.
            w = _profile(t, kind) * 0.88 + 1.4 + 4.2 * hang
        w *= 1 + smear * 0.20
        if split > 0:
            sx += math.sin(t * 9.0 + phase * 2) * split * 3.0

        # Eine Oeffnung ist eine Kerbe im Rand, kein fehlendes Stueck: der
        # Stoff weicht dort zurueck, und in der Kerbe steht ihr Licht.
        def kerbe(seite: int) -> float:
            for su, s_, laenge in slits:
                if s_ == seite and abs(u - su) < laenge / 2:
                    tief = 1 - abs(u - su) / (laenge / 2)
                    return (1.8 + 1.8 * tief) * min(1.0, w / 4)
            return 0.0

        links = int(sx - w + kerbe(-1))
        rechts = int(sx + w - kerbe(1))
        # Waagerechte Schienen: alle drei Reihen eine Fuge, darueber ein
        # heller Grat. Daran erkennt man Metall auf den ersten Blick.
        schiene = starr and i % 3 == 0
        for x in range(links, rechts + 1):
            rand = x <= links or x >= rechts
            if not starr and u < 0.14 and hash01(x, int(y) + int(phase * 4)) < 0.45:
                continue
            # Ihr Licht sitzt hinter dem Stoff, also glueht der Rand - ein
            # dunkler Umriss verschwaende vor dem dunklen Grund.
            if rand:
                col = mix(stoff, saum_licht, 0.42)
            elif schiene:
                col = shade(stoff, -0.42)
            elif starr and i % 3 == 1:
                col = stoff_hi
            elif abs(x - int(sx)) <= 1:
                col = mix(stoff, saum_licht, 0.18)
            else:
                col = stoff
            if not starr:
                falte = int(sx) + int(math.sin(u * 2.4 + phase * 0.6 + sway) * 2) - 2
                if x == falte and not rand:
                    col = shade(stoff, -0.35)
            c.set(x, int(y), col)

        for seite, kante in ((-1, links), (1, rechts)):
            if kerbe(seite) > 0:
                c.set(kante, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 225))
                c.blend(kante + seite, int(y),
                        (saum_licht[0], saum_licht[1], saum_licht[2], 60))

        # Der Kragen haelt sie zusammen. Beim Harnisch steht er als Kehle
        # hoch und laesst genau den Kopf frei.
        if u > 0.90:
            c.set(links, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 170))
            c.set(rechts, int(y), (saum_licht[0], saum_licht[1], saum_licht[2], 170))
            if starr:
                for x in range(links + 1, rechts):
                    c.set(x, int(y - 1), stoff_hi)
                c.set(links, int(y - 1), mix(stoff, saum_licht, 0.5))
                c.set(rechts, int(y - 1), mix(stoff, saum_licht, 0.5))


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
    height = (20.0 + (2.0 if kind == "floete" else 0.0)) * stretch - settle * 0.6
    top_y = base - height

    core = mix(P.BONE, hexc("#dffaf2"), 0.55)
    mid = mix(P.TRIM, P.BONE, 0.35)
    rim = mix(P.TRIM, P.CLOAK, 0.45)

    # Was hinter ihr haengt, kommt zuerst - sonst laege das Cape vor ihr.
    _draw_garment(c, garment=garment, kind=kind, cx=cx, base=base, height=height,
                  phase=phase, lean=lean, smear=smear, split=split, sway=sway,
                  hinter=True)

    # --- Die Gestalt ------------------------------------------------------
    steps = int(height) + 1
    for i in range(steps):
        t = i / max(1, steps - 1)
        y = base - t * height

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
            if d < 0.34:
                col = core
            elif d < 0.68:
                col = mid
            else:
                col = rim
            c.set(int(sx) + dx, int(y), col)

    # Unten loest sie sich auf, statt auf dem Boden aufzusetzen.
    for k in range(3):
        y = base - k
        for dx in range(-4, 5):
            if hash01(cx + dx, int(y) + int(phase * 5)) < 0.35 + k * 0.2:
                c.set(cx + dx + int(lean * 0.2), int(y), None)
    c.rect(cx - 3, GROUND, 7, 1, mix(P.TRIM, P.CLOAK_LO, 0.65))

    # Funken steigen auf.
    for k in range(5):
        u = (k / 5 + phase * 0.35) % 1.0
        fy = base - height * (0.75 + u * 0.5)
        fx = cx + lean * 0.8 + math.sin(u * 7 + phase * 3) * (3 + u * 5)
        if hash01(k, int(phase * 8)) > 0.35:
            c.set(int(fx), int(fy), mix(mid, P.AMBER, 0.35))

    _draw_garment(c, garment=garment, kind=kind, cx=cx, base=base, height=height,
                  phase=phase, lean=lean, smear=smear, split=split, sway=sway,
                  hinter=False)

    # --- Der Resonanzschlitz ----------------------------------------------
    # Kein Gesicht - nur eine dunkle Kerbe, dort wo die Gestalt am dichtesten
    # ist. Sie gibt dem Blick einen Halt, ohne Zuege zu behaupten.
    slot_t = 0.70
    slot_y = int(base - slot_t * height)
    slot_x = int(cx + lean * slot_t + math.sin(slot_t * 2.6 + phase) * 1.6)
    c.rect(slot_x, slot_y - (3 if aim > 0.5 else 2), 2, 5, P.EYE)
    c.set(slot_x - 1, slot_y - 2, P.EYE)
    c.set(slot_x + 2, slot_y + 2, P.EYE)

    # --- Die Stimmgabel ---------------------------------------------------
    #
    # Sie steckt in ihr, sie sitzt nicht obenauf. Der Steg liegt tief genug,
    # dass die Masse ihn umschliesst; nach unten laeuft der Stiel weiter und
    # verliert sich in ihr. Nur die beiden Zinken stehen frei - und die
    # Gestalt franst oberhalb davon weiter aus, sodass sie hinter den Zinken
    # noch weitergeht.
    fork_t = 0.52
    fy = base - fork_t * height
    fx = cx + lean * fork_t + math.sin(fork_t * 2.6 + phase) * 1.2
    tilt = 0.16 + lean * 0.02

    # Stiel nach unten, verschwindet in der Masse.
    for i in range(8):
        col = P.BONE_SH if i < 3 else mix(P.BONE_LO, mid, min(1.0, (i - 3) / 5))
        c.set(int(fx + tilt * i), int(fy + i), col)

    # Steg - er liegt in der Gestalt, deshalb schmal und gedeckt.
    c.rect(int(fx) - 2, int(fy - 1), 5, 2, P.BONE_SH)
    c.rect(int(fx) - 2, int(fy - 1), 5, 1, P.BONE)

    for side in (-1, 1):
        bx = fx + side * 1.5
        for i in range(9):
            c.set(int(bx + side * i * 0.34), int(fy - 2 - i), P.BONE)
            if i > 1:
                c.set(int(bx + side * i * 0.34) + side, int(fy - 2 - i), P.BONE_SH)
        tipx, tipy = int(bx + side * 8 * 0.34), int(fy - 11)
        c.set(tipx, tipy, P.AMBER)
        c.set(tipx, tipy + 1, mix(P.AMBER, P.BONE, 0.5))
        if glow > 0:
            c.glow(tipx, tipy, 5,
                   (P.AMBER[0], P.AMBER[1], P.AMBER[2], int(95 * glow)), power=2.0)

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
        draw_heroine(instrument=instrument, garment=garment, phase=i / 8 * math.tau,
                     stretch=1.0 + math.sin(i / 8 * math.tau) * 0.04,
                     sway=math.sin(i / 8 * math.tau) * 0.5,
                     glow=0.85 + 0.25 * (0.5 + 0.5 * math.sin(i / 8 * math.tau)))
        for i in range(8)
    ]

    # Lauf: sie neigt sich und zieht einen Schweif hinter sich her.
    anims["run"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i / 8 * math.tau * 2,
                     lean=2.4 + math.sin(i / 8 * math.tau) * 0.8,
                     stretch=0.94 + abs(math.sin(i / 8 * math.tau)) * 0.10,
                     smear=0.16, sway=math.sin(i / 8 * math.tau + 1.1) * 1.3)
        for i in range(8)
    ]

    anims["jump"] = [draw_heroine(instrument=instrument, garment=garment, phase=0.6,
                                  lean=1.4, stretch=1.24, smear=0.05, sway=-0.9)]
    anims["fall"] = [draw_heroine(instrument=instrument, garment=garment, phase=2.2,
                                  lean=0.6, stretch=0.88, smear=0.18, sway=1.4)]
    anims["land"] = [draw_heroine(instrument=instrument, garment=garment, phase=1.1,
                                  stretch=0.72, settle=2, smear=0.34, sway=1.8)]

    # Herzschlag: die Gestalt zerreisst waagerecht und zieht nach.
    anims["dash"] = [
        draw_heroine(instrument=instrument, garment=garment, phase=i * 1.7, lean=4.0 - i,
                     stretch=0.82, smear=0.9 - i * 0.2, split=0.5 - i * 0.15,
                     glow=1.4, alpha_body=235 - i * 30)
        for i in range(3)
    ]

    anims["wall"] = [draw_heroine(instrument=instrument, garment=garment, phase=0.4,
                                  lean=-1.8, stretch=1.10, smear=0.1)]

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
    anims["hurt"] = [draw_heroine(instrument=instrument, garment=garment, phase=1.9, lean=-3.0,
                                  stretch=0.86, split=0.7, smear=0.4,
                                  glow=0.5, alpha_body=210)]

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
    atlas = Atlas("characters", padding=1, max_width=512)

    for instrument in ("leier", "trommel", "floete"):
        for garment in GARMENTS:
            for name, frames in hero_animations(instrument, garment).items():
                atlas.add_sequence(f"cadence_{instrument}_{garment}_{name}", frames,
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
        "idle": 7, "run": 13, "jump": 1, "fall": 1, "land": 1,
        "dash": 18, "wall": 1, "melee": 20, "cast": 16, "hurt": 1, "rest": 5,
    }.get(name, 8)


if __name__ == "__main__":
    build()
