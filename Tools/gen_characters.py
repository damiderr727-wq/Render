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

HERO_W, HERO_H = 22, 30
GROUND = HERO_H - 1  # unterste Pixelzeile = Fussboden


# ------------------------------------------------------------------ Heldin

def draw_heroine(
    *,
    lean: float = 0.0,        # Oberkoerperneigung in Pixeln
    bob: float = 0.0,         # vertikales Wippen
    leg_phase: float | None = None,   # None = Stand
    leg_spread: float = 0.0,  # Sprung/Fall-Haltung
    arm_front: float = 0.0,   # vorderer Arm: -1 unten .. +1 oben
    arm_back: float = 0.0,
    hair_sway: float = 0.0,   # Schwingen der Zinken
    cloak_sway: float = 0.0,
    cloak_lift: float = 0.0,
    instrument: str | None = "leier",
    aim: float = 0.0,
    crouch: float = 0.0,
    glow: float = 0.35,
    alpha_body: int = 255,
) -> Canvas:
    """
    Zeichnet Cadence nach rechts blickend.

    Sie ist bewusst keine Person. Bei zwanzig Pixeln verliert ein Gesicht
    jede Wirkung - eine Form nicht.

    Zwei Anlaeufe waren daneben. Eine runde bleiche Maske mit einem grossen
    Auge ist woanders schon vergeben, und ein gleichschenkliger Umhang
    darunter ergab eine Tuete mit Kopf. Deshalb jetzt: eine Maske in Form
    eines Glockenkorpus mit einem Resonanzschlitz statt eines Auges, ein
    asymmetrischer Umhang, der vorn geschlitzt ist und ein Bein zeigt, ein
    kantiger Kragen - und ein wehendes Notenband, das in jedem Bild die
    Dreiecksform aufbricht. Darueber die Zinken einer Stimmgabel.
    """
    c = Canvas(HERO_W, HERO_H)

    cx = HERO_W // 2
    base = GROUND - int(round(bob)) - int(round(crouch))
    lean_i = int(round(lean))
    sway = cloak_sway

    hem_y = base
    shoulder_y = base - 15
    mask_cy = base - 20
    fork_base = mask_cy - 5

    # --- Umhang -----------------------------------------------------------
    #
    # Der erste Entwurf war ein gleichschenkliges Dreieck - eine Tuete mit
    # Kopf. Silhouetten leben von Asymmetrie: der Saum haengt hinten lang
    # und ist vorn hochgeschlagen, sodass ein Bein sichtbar bleibt, und
    # ueber der Schulter liegt ein kantiger Kragen statt einer Rundung.
    for y in range(shoulder_y, hem_y + 1):
        t = (y - shoulder_y) / max(1, hem_y - shoulder_y)
        back = 2.4 + (t ** 1.15) * 5.4 + cloak_lift * t * 0.8
        front = 2.2 + (t ** 1.9) * 3.0
        off = lean_i * (1 - t) * 0.7 + sway * (t ** 1.4)
        # Vorn frueher aufhoeren: der Saum ist geschlitzt.
        if t > 0.72:
            front *= 1 - (t - 0.72) / 0.28 * 0.75
        col = mix(P.CLOAK_HI, P.CLOAK_LO, min(1.0, t * 1.3))
        x0 = int(round(cx - back + off))
        x1 = int(round(cx + front + off))
        c.rect(x0, y, max(1, x1 - x0), 1, col)

    # Zerfranster Saum hinten.
    hem_half = 2.4 + 5.4 + cloak_lift * 0.8
    for i in range(int(hem_half)):
        x = int(round(cx - hem_half + sway)) + i
        notch = int(hash01(x * 7, 3) * 2.4)
        for k in range(notch):
            c.set(x, hem_y - k, None)

    # --- Bein und Stiefel auf der Vorderseite -----------------------------
    step = math.sin(leg_phase) if leg_phase is not None else 0.0
    lx = cx + 2 + int(round(step * 2.2)) + lean_i // 2
    ly = hem_y - max(0, int(round(step * 2.0)))
    c.rect(lx, hem_y - 5, 2, 5 - max(0, int(round(step * 2.0))), shade(P.CLOAK_LO, -0.1))
    c.rect(lx - 1, ly - 2, 4, 2, P.CLOAK_LO)
    c.set(lx + 2, ly - 1, mix(P.AMBER, P.CLOAK_LO, 0.6))
    if leg_phase is not None:
        # Das hintere Bein blitzt gegenlaeufig unter dem Saum auf.
        bx = cx - 3 - int(round(step * 2.0))
        c.rect(bx, hem_y - 3, 2, 3 + int(round(step * 1.5)), P.CLOAK_LO)

    # --- Kragen -----------------------------------------------------------
    c.rect(cx - 4 + lean_i, shoulder_y, 8, 2, P.CLOAK_HI)
    c.rect(cx - 5 + lean_i, shoulder_y + 1, 10, 1, P.CLOAK_HI)
    c.rect(cx - 5 + lean_i, shoulder_y + 2, 10, 1, shade(P.CLOAK, -0.1))
    c.set(cx - 5 + lean_i, shoulder_y, None)      # Ecken kappen: kantig,
    c.set(cx + 4 + lean_i, shoulder_y, None)      # nicht rund

    # --- Notenband --------------------------------------------------------
    #
    # Ein langes Band weht hinter ihr her - eine einzelne Notenlinie. Es
    # bricht in jedem Bild die Dreiecksform auf und traegt die Bewegung.
    ribbon_len = 13 + int(abs(sway) * 1.6 + cloak_lift * 1.2)
    rx, ry = cx - 4 + lean_i, shoulder_y + 1
    for i in range(ribbon_len):
        u = i / ribbon_len
        wave = math.sin(u * 3.4 + sway * 0.7 + cloak_lift * 0.5) * (2.2 + u * 3.4)
        px = rx - u * (7 + abs(sway) * 1.4) - abs(sway) * 0.6
        py = ry + wave * 0.55 + u * 2.2 - cloak_lift * 0.7
        c.set(int(px), int(py), mix(P.CLOAK_HI, P.BONE_LO, u * 0.5))
        if i % 5 == 0:
            c.set(int(px), int(py) + 1, P.CLOAK_LO)
    c.set(int(rx - (7 + abs(sway) * 1.4)), int(ry + 2.2 - cloak_lift * 0.7), P.AMBER)

    # --- Arme: zwei kurze dunkle Striche ----------------------------------
    def arm(x: int, raise_amt: float, col) -> tuple[int, int]:
        length = 5.0
        ex = x + int(round(length * 0.5 * max(raise_amt, -0.3) + 1.5))
        ey = shoulder_y + 3 + int(round(length * (1 - abs(raise_amt) * 0.8)))
        c.line(x, shoulder_y + 3, ex, ey, col)
        return ex, ey

    arm(cx - 3 + lean_i, arm_back, P.CLOAK_LO)
    fex, fey = arm(cx + 3 + lean_i, arm_front, P.CLOAK)

    # --- Maske ------------------------------------------------------------
    #
    # Keine runde Scheibe mit zwei Augen - das ist woanders schon vergeben.
    # Diese Maske hat die Form eines Glockenkorpus und statt eines Auges
    # einen Resonanzschlitz, wie ihn Streichinstrumente tragen.
    mx = cx + lean_i
    mask_top = mask_cy - 3
    mask_bot = mask_cy + 4
    # Oben breit, zum Kinn hin schmal - ein Schild, keine Schnauze. Die
    # umgekehrte Verjuengung las sich zusammen mit den Zinken als Tierkopf.
    for y in range(mask_top, mask_bot + 1):
        t = (y - mask_top) / max(1, mask_bot - mask_top)
        half = 2.9 - (t ** 1.4) * 1.7
        c.rect(int(round(mx - half)), y, max(1, int(round(half * 2))), 1,
               mix(P.BONE, P.BONE_SH, t * 0.5))
    # Schattenseite links.
    for y in range(mask_top + 1, mask_bot + 1):
        t = (y - mask_top) / max(1, mask_bot - mask_top)
        c.set(int(round(mx - (2.9 - (t ** 1.4) * 1.7))), y, P.BONE_SH)
    # Flache Stirnkante.
    c.rect(mx - 3, mask_top, 6, 1, P.BONE)
    c.rect(mx - 2, mask_bot, 4, 1, shade(P.BONE_SH, -0.2))

    # Resonanzschlitz: senkrecht, mit Kerbe oben und unten.
    sx = mx + 1
    sy = mask_cy - 2 - (1 if aim > 0.5 else 0)
    c.rect(sx, sy, 2, 4, P.EYE)
    c.set(sx - 1, sy, P.EYE)          # Kerbe oben links
    c.set(sx + 2, sy + 3, P.EYE)      # Kerbe unten rechts
    c.set(sx + 2, sy, mix(P.EYE, P.BONE, 0.45))

    # Feiner Riss ueber der Wange.
    c.set(mx - 2, mask_cy - 1, P.BONE_LO)
    c.set(mx - 2, mask_cy, P.BONE_LO)

    # --- Stimmgabel-Krone -------------------------------------------------
    #
    # Das Zeichen der Welt sitzt ihr auf dem Kopf. Der Querbalken liegt auf
    # der Stirn, die Zinken stehen leicht nach aussen - senkrecht und dicht
    # beieinander lesen sie sich als Ohren.
    swing = hair_sway * 0.5
    # Ein schmaler Steg auf der Stirn, aus dem zwei duenne Zinken in einem
    # V nach oben laufen. Kurz und dick sassen sie wie Ohren auf dem Kopf -
    # lang, duenn und auseinanderlaufend lesen sie sich als Gabel.
    c.rect(mx - 1, fork_base, 3, 2, P.BONE_SH)
    c.rect(mx - 1, fork_base, 3, 1, P.BONE)
    for side in (-1, 1):
        bx = mx + side
        tip_x = bx + side * 3 + int(round(swing * (1 if side > 0 else 0.6)))
        c.line(bx, fork_base, tip_x, 1, P.BONE_SH)
        c.set(tip_x, 1, P.AMBER)
        c.set(tip_x, 2, mix(P.AMBER, P.BONE_SH, 0.4))

    if instrument:
        draw_instrument(c, instrument, fex, fey, glow)

    # Harte Kontur: die Figur muss sich gegen jeden Hintergrund abheben.
    c.outline(hexc("#04050a", 255), diagonal=False)

    if glow > 0:
        for side in (-1, 1):
            c.glow(mx + side * 4 + swing, 2, 5,
                   (P.AMBER[0], P.AMBER[1], P.AMBER[2], int(80 * glow)), power=2.0)

    if alpha_body < 255:
        for i in range(len(c.px)):
            c.px[i][3] = int(c.px[i][3] * alpha_body / 255)
    return c


def draw_instrument(c: Canvas, kind: str, hx: int, hy: int, glow: float) -> None:
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

def hero_animations(instrument: str) -> dict[str, list[Canvas]]:
    anims: dict[str, list[Canvas]] = {}

    # Ruhe: Atem, Haar und Umhang schwingen leicht nach.
    idle = []
    for i in range(6):
        p = i / 6 * math.tau
        idle.append(draw_heroine(
            bob=math.sin(p) * 0.9,
            hair_sway=math.sin(p - 0.7) * 0.8,
            cloak_sway=math.sin(p - 1.2) * 0.7,
            arm_front=-0.15 + math.sin(p) * 0.08,
            arm_back=-0.3,
            instrument=instrument,
            glow=0.3 + 0.12 * (0.5 + 0.5 * math.sin(p)),
        ))
    anims["idle"] = idle

    # Lauf: acht Phasen, Oberkoerper nach vorn.
    run = []
    for i in range(8):
        p = i / 8 * math.tau
        run.append(draw_heroine(
            lean=1.4,
            bob=abs(math.sin(p * 2)) * 1.3,
            leg_phase=p,
            hair_sway=-1.4 - math.sin(p) * 0.7,
            cloak_sway=-2.0 - math.sin(p * 2) * 0.8,
            cloak_lift=0.7,
            arm_front=-0.35 + math.sin(p) * 0.3,
            arm_back=-0.35 + math.sin(p + math.pi) * 0.3,
            instrument=instrument,
        ))
    anims["run"] = run

    anims["jump"] = [draw_heroine(
        lean=1.0, leg_spread=1.6, cloak_lift=1.6, cloak_sway=-2.4,
        hair_sway=-2.0, arm_front=0.35, arm_back=-0.5, instrument=instrument,
    )]
    anims["fall"] = [draw_heroine(
        lean=0.4, leg_spread=0.8, cloak_lift=2.4, cloak_sway=-1.4,
        hair_sway=-2.6, arm_front=0.15, arm_back=0.35, instrument=instrument,
    )]
    anims["land"] = [draw_heroine(
        crouch=3, lean=0.6, leg_spread=2.2, cloak_lift=-0.6, cloak_sway=0.6,
        hair_sway=0.9, arm_front=-0.6, arm_back=-0.6, instrument=instrument,
    )]

    # Dash: gestreckt, halbtransparent - der Herzschlag traegt sie.
    dash = []
    for i in range(2):
        dash.append(draw_heroine(
            lean=3.0 + i, bob=1.0, leg_spread=2.6 - i, cloak_lift=2.2,
            cloak_sway=-4.0, hair_sway=-3.4, arm_front=0.6, arm_back=0.7,
            instrument=instrument, glow=0.9, alpha_body=245 - i * 25,
        ))
    anims["dash"] = dash

    # Wandhaftung: an die Wand gedrueckt, Blick zurueck.
    anims["wall"] = [draw_heroine(
        lean=-1.6, leg_spread=0.6, cloak_sway=2.6, hair_sway=2.2,
        arm_front=0.8, arm_back=0.2, instrument=instrument,
    )]

    # Nahkampf: Ausholen, Schlag, Nachschwingen.
    swing = []
    for i, (af, ln, cr) in enumerate([(0.9, -1.0, 0), (-0.2, 2.6, 1), (-0.7, 1.4, 0)]):
        swing.append(draw_heroine(
            lean=ln, crouch=cr, arm_front=af, arm_back=-0.4 + i * 0.2,
            hair_sway=-1.2 + i, cloak_sway=-1.6 + i * 1.2, cloak_lift=0.8,
            instrument=instrument, glow=0.5 + i * 0.2,
        ))
    anims["melee"] = swing

    # Fernkampf: Standfest, Instrument vorgestreckt.
    cast = []
    for i, af in enumerate([0.25, 0.55, 0.35]):
        cast.append(draw_heroine(
            lean=-0.8 + i * 0.6, arm_front=af, arm_back=-0.5,
            hair_sway=0.8 - i * 0.6, cloak_sway=1.2 - i * 0.8,
            instrument=instrument, glow=0.55 + i * 0.25,
        ))
    anims["cast"] = cast

    anims["hurt"] = [draw_heroine(
        lean=-2.6, crouch=1, leg_spread=1.2, arm_front=0.5, arm_back=0.6,
        hair_sway=2.6, cloak_sway=3.0, instrument=instrument, glow=0.15,
    )]

    # Ausatmen an der Stimmgabel (Rast).
    rest = []
    for i in range(4):
        p = i / 4 * math.tau
        rest.append(draw_heroine(
            crouch=4, bob=math.sin(p) * 0.6, leg_spread=1.0,
            arm_front=-0.75, arm_back=-0.75, hair_sway=math.sin(p) * 0.6,
            cloak_sway=math.sin(p - 1) * 0.5, instrument=None, glow=0.6,
        ))
    anims["rest"] = rest

    return anims


# ---------------------------------------------------------------- Kreaturen

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
        for name, frames in hero_animations(instrument).items():
            atlas.add_sequence(f"cadence_{instrument}_{name}", frames,
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
