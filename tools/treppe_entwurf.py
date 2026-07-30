#!/usr/bin/env python3
"""
Entwurf des neuen Treppenhauses - zweilaeufig gegenlaeufig, zweimal gestapelt.

Form (nach der Vorgabe des Nutzers):
    Lauf steigt in EINE Richtung  ->  Zwischenpodest (der "Mini-Flur")
    ->  naechster Lauf in die GEGENrichtung  ->  naechste Etage
    ->  dort beginnt dasselbe wieder.

Der entscheidende Trick fuer die Stapelung: beide Geschosse bekommen denselben
Grundriss. Dazu muessen die Laeufe gleich LANG sein, obwohl die Geschosshoehen
verschieden sind (3.80 m und 2.80 m). Also unterschiedliche Stufenzahl bei
gleichem Lauf: 11 Stufen a 17.27 cm bzw. 10 Stufen a 14.00 cm. Dadurch liegt
Lauf C exakt ueber Lauf A und der lichte Abstand ist an jeder Stelle gleich -
genau daran ist die alte Fassung gescheitert, weil dort 3.13 m auf 2.24 m
Lauflaenge trafen und sich die Podeste in die Laeufe geschoben haben.

Zweiter Punkt: das Podest liegt am SUEDende an der Wand, und beide Laeufe teilen
sich denselben z-Bereich. Dadurch kommt der obere Lauf im Norden an, wo Platz
zum Austreten ist. Lag das Podest im Norden, endete der obere Lauf 21 cm vor
der Suedwand - man haette nicht aussteigen koennen.

    python3 tools/treppe_entwurf.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenemodel import (Scene, Box, Area, pruef_steigungen, pruef_freiraum,
                        pruef_kopffreiheit, begehbar, WALL_T, MIN_HEAD)

# ==================================================================== Entwurf

# --- Schacht ---
XW, XE = -8.0, -4.0            # Wandachsen West / Ost
ZN, ZS = 6.0, 14.0             # Wandachsen Nord / Sued
XWI, XEI = XW + WALL_T, XE - WALL_T      # -7.81 / -4.19  Innenflaechen
ZNI, ZSI = ZN + WALL_T, ZS - WALL_T      # +6.19 / +13.81

# --- Laeufe ---
W = 1.40                       # Laufbreite
XA = -6.90                     # Laufachse West
XB = -5.10                     # Laufachse Ost
RAIL = W / 2 + 0.09            # Handlaufversatz von der Laufachse

# --- Podest am Suedende ---
D_LANDING = 1.70
Z_LAND_S = ZSI                 # Podest liegt an der Suedwand
Z_LAND_N = Z_LAND_S - D_LANDING

# --- Geschosse: (Name, y unten, y oben, Stufen je Lauf) ---
LEVELS = [('EG->OG', 0.00, 3.80, 11),
          ('OG->BH', 3.80, 6.60, 10)]

RUN = 3.135                    # Lauflaenge, fuer BEIDE Geschosse gleich
Z_FOOT = Z_LAND_N - RUN        # Antritt Lauf A / Austritt Lauf B


def geschoss(i):
    """Liefert die Kennzahlen eines Geschosses."""
    name, y0, y1, n = LEVELS[i]
    y_mid = (y0 + y1) / 2
    rise = (y_mid - y0) / n
    going = RUN / n
    return dict(name=name, y0=y0, y1=y1, y_mid=y_mid, n=n, rise=rise, going=going)


def bauen():
    sc = Scene("Entwurf: zweilaeufig gegenlaeufig, zwei Geschosse gestapelt")

    # ---------------- Schachtwaende, volle Hoehe bis unter die Badehausdecke
    sc.wall_z(ZN, ZS, XW, h=9.3, tag='Westwand x=-8')
    sc.wall_z(ZN, ZS, XE, h=9.3, tag='Ostwand x=-4')
    sc.wall_x(XW, XE, ZS, h=9.3, tag='Suedwand z=14')
    # Nordwand: im EG mit Sturz (Tuerhoehe reicht), im OG VOLLE Hoehe, damit man
    # nicht durch einen Sturz laeuft. Ueber dem OG traegt die Badehausplatte.
    sc.wall_x(XW, XE, ZN, gaps=[(-5.0, 2.0)], h=3.8, base=0.0,
              tag='Nordwand z=6 EG')
    sc.wall_x(XW, XE, ZN, gaps=[(-5.0, 2.0)], h=2.2, base=3.8,
              tag='Nordwand z=6 OG', lintel=False)

    # ---------------- Boeden ausserhalb des Schachts (nur was angrenzt)
    sc.floor(XW, XE, 0.0, ZN, 0.0, tag='Flur EG (nordlich)')
    sc.floor(XW, XE, ZN, ZSI, 0.0, tag='Boden EG im Schacht')
    sc.floor(XW, XE, 0.0, ZN, 3.80, tag='Galerie OG (nordlich)')
    sc.floor(XW, XE, 0.0, ZN, 6.60, tag='Vorraum BH (nordlich)')

    # ---------------- Geschossplatten IM Schacht: Band im Norden, Schacht offen
    for g in (geschoss(0), geschoss(1)):
        sc.floor(XW, XE, ZN, Z_FOOT, g['y1'],
                 tag=f"Band {g['name'].split('->')[1]} z {ZN:.2f}..{Z_FOOT:.3f}")
    # Decke ueber dem OG-Band (normale Raumhoehe), NICHT ueber dem Schacht
    sc.ceil(XW, XE, ZN, Z_FOOT, 6.0, tag='Decke ueber OG-Band')
    # Decke ueber dem ganzen Schacht erst auf Badehausniveau + 2.7
    sc.ceil(XW, XE, ZN, ZSI, 9.3, tag='Schachtdecke y=9.3')

    # ---------------- Laeufe, Podeste, Fuellungen
    for k, g in enumerate((geschoss(0), geschoss(1))):
        suf = 'AB' if k == 0 else 'CD'
        # Lauf 1: Westspur, steigt nach SUEDEN (+z)
        sc.stair_run(XA, Z_FOOT, Z_LAND_N, W, g['y0'], g['y_mid'], g['n'],
                     rails=(True, True), rail_off=RAIL, tag=f'Lauf {suf[0]}')
        # Podest an der Suedwand
        sc.floor(XWI, XEI, Z_LAND_N, Z_LAND_S, g['y_mid'],
                 tag=f'Podest {k + 1}')
        # Lauf 2: Ostspur, steigt nach NORDEN (-z), kommt am Band an
        sc.stair_run(XB, Z_LAND_N, Z_FOOT, W, g['y_mid'], g['y1'], g['n'],
                     rails=(True, True), rail_off=RAIL, tag=f'Lauf {suf[1]}')

        # KEINE Bruestung quer ueber Podestkante oder Bandkante.
        # Beide Kanten sind vollstaendig von den zwei Laeufen belegt: am Podest
        # kommt Lauf 1 an und Lauf 2 setzt an, am Band tritt Lauf 2 aus und
        # Lauf 1 des naechsten Geschosses setzt an. Eine durchgehende Bruestung
        # dort war genau der Fehler, der die alte Treppe unpassierbar gemacht
        # hat. Gesichert wird stattdessen durch die Wangen der Laeufe (siehe
        # stair_run) - sie laufen mit der Steigung und lassen Antritt und
        # Austritt frei.
        pass

    # ---------------- Fuellung unter der untersten Treppe
    # Nur im Erdgeschoss noetig: unter Lauf C/D liegt der offene Schacht, dort
    # kann niemand stehen. Die Oberkante folgt der Rampe minus 30 cm, damit sie
    # den Laeufer NIEMALS erreicht - hits() blendet eine Sperre erst aus, wenn
    # y1 < y + 0.15 ist.
    g0 = geschoss(0)
    segs = 8
    for k in range(segs):
        t0, t1 = k / segs, (k + 1) / segs
        za = Z_FOOT + RUN * t0
        zb = Z_FOOT + RUN * t1
        ya = g0['y0'] + (g0['y_mid'] - g0['y0']) * t0        # Westspur steigt mit z
        top = ya - 0.30
        if top > 0.25:
            sc.solids.append(Box(XA - W / 2 - 0.04, XA + W / 2 + 0.04, za, zb,
                                 0.0, top, blocks_camera=False,
                                 tag='Fuellung unter Lauf A'))
        # Ostspur: Lauf B faellt mit z, also Hoehe am SUEDende am kleinsten
        yb_ost = g0['y_mid'] + (g0['y1'] - g0['y_mid']) * (1 - t1)
        top_o = yb_ost - 0.30
        if top_o > 0.25 and yb_ost < 2.0 + 0.30:
            sc.solids.append(Box(XB - W / 2 - 0.04, XB + W / 2 + 0.04, za, zb,
                                 0.0, top_o, blocks_camera=False,
                                 tag='Fuellung unter Lauf B'))
    # Unter dem Podest 1: geschlossener Raum, Oberkante 1.60
    sc.solids.append(Box(XWI, XEI, Z_LAND_N + 0.05, ZSI, 0.0,
                         g0['y_mid'] - 0.30, blocks_camera=False,
                         tag='Kammer unter Podest 1'))
    return sc


# ==================================================================== Ausgabe

def zwischenraum(sc):
    """Lichter Abstand zwischen den gestapelten Geschossen."""
    print("  LICHTER ABSTAND ZWISCHEN DEN GESCHOSSEN")
    paare = [('Lauf A', 'Lauf C'), ('Lauf B', 'Lauf D'),
             ('Podest 1', 'Podest 2')]
    ok = True
    byname = {}
    for a in sc.areas:
        byname[a.tag] = a
    for lo, hi in paare:
        if lo not in byname or hi not in byname:
            continue
        a, b = byname[lo], byname[hi]
        worst = 99.0
        for i in range(41):
            t = i / 40
            z = max(a.z0, b.z0) + (min(a.z1, b.z1) - max(a.z0, b.z0)) * t
            x = (max(a.x0, b.x0) + min(a.x1, b.x1)) / 2
            if not (a.contains(x, z) and b.contains(x, z)):
                continue
            worst = min(worst, b.height(x, z) - a.height(x, z))
        mark = 'ok' if worst >= MIN_HEAD else 'ZU NIEDRIG'
        print(f"    {lo} unter {hi}: mindestens {worst:.2f} m   [{mark}]")
        if worst < MIN_HEAD:
            ok = False
    print()
    return ok


def swift_zahlen():
    print("=" * 74)
    print("ZAHLEN FUER DEN SWIFT-CODE")
    print("=" * 74)
    print(f"  Schacht innen      x {XWI:+.2f} .. {XEI:+.2f}   "
          f"z {ZNI:+.2f} .. {ZSI:+.2f}")
    print(f"  Laufbreite         {W:.2f} m")
    print(f"  Laufachsen         West x {XA:+.2f}   Ost x {XB:+.2f}")
    print(f"  Handlaufversatz    {RAIL:.3f} m von der Laufachse")
    print(f"  Treppenauge        {(XB - W/2 - 0.03) - (XA + W/2 + 0.03):.2f} m "
          f"zwischen den Tritten")
    print(f"  Lauflaenge         {RUN:.3f} m (beide Geschosse gleich)")
    print(f"  Antritt / Austritt z {Z_FOOT:+.3f}")
    print(f"  Podest             z {Z_LAND_N:+.3f} .. {Z_LAND_S:+.3f}  "
          f"(Tiefe {D_LANDING:.2f} m)")
    print(f"  Schachtoeffnung    x {XW:+.2f} .. {XE:+.2f}   "
          f"z {Z_FOOT:+.3f} .. {ZSI:+.2f}")
    print(f"  Bodenband          x {XW:+.2f} .. {XE:+.2f}   "
          f"z {ZN:+.2f} .. {Z_FOOT:+.3f}")
    print()
    for i in range(len(LEVELS)):
        g = geschoss(i)
        suf = 'AB' if i == 0 else 'CD'
        print(f"  {g['name']}:  {g['n']} Stufen je Lauf, "
              f"Steigung {g['rise']*100:.3f} cm, Auftritt {g['going']*100:.3f} cm")
        print(f"     Lauf {suf[0]} (West)  x {XA:+.2f}  "
              f"z {Z_FOOT:+.3f} -> {Z_LAND_N:+.3f}   "
              f"y {g['y0']:.2f} -> {g['y_mid']:.2f}")
        print(f"     Podest         z {Z_LAND_N:+.3f} .. {Z_LAND_S:+.2f}   "
              f"y {g['y_mid']:.2f}")
        print(f"     Lauf {suf[1]} (Ost)   x {XB:+.2f}  "
              f"z {Z_LAND_N:+.3f} -> {Z_FOOT:+.3f}   "
              f"y {g['y_mid']:.2f} -> {g['y1']:.2f}")
    print()


if __name__ == '__main__':
    sc = bauen()
    print("=" * 74)
    print(sc.name)
    print("=" * 74)
    print(f"  {len(sc.solids)} Sperren, {len(sc.areas)} Flaechen\n")
    ok = True
    ok &= pruef_steigungen(sc)
    ok &= pruef_freiraum(sc)
    ok &= zwischenraum(sc)
    ok &= pruef_kopffreiheit(sc)

    # Weg: aus dem Flur in den Schacht, hoch bis ins Badehaus
    weg = [(-5.0, 4.0),                        # Flur, noerdlich des Schachts
           (-5.0, 7.4),                        # durch die Nordwandluecke
           (XA, 8.6), (XA, Z_FOOT + 0.2),      # an den Antritt von Lauf A
           (XA, Z_LAND_N - 0.1),               # Lauf A hoch
           (XA, Z_LAND_S - 0.5),               # aufs Podest
           (XB, Z_LAND_S - 0.5),               # Wende auf dem Podest
           (XB, Z_LAND_N + 0.1),               # an den Antritt von Lauf B
           (XB, Z_FOOT + 0.1),                 # Lauf B hoch -> OG
           (XB, Z_FOOT - 0.8),                 # aufs OG-Band austreten
           (XA, Z_FOOT - 0.8),                 # zum Antritt von Lauf C
           (XA, Z_FOOT + 0.2), (XA, Z_LAND_N - 0.1),
           (XA, Z_LAND_S - 0.5), (XB, Z_LAND_S - 0.5),
           (XB, Z_LAND_N + 0.1), (XB, Z_FOOT + 0.1),
           (XB, Z_FOOT - 0.8)]                 # Badehaus
    ok &= begehbar(sc, weg, "Flur EG -> Obergeschoss -> Badehaus")
    print()
    print(f"  ENTWURF: {'alle Pruefungen bestanden' if ok else 'FEHLER, siehe oben'}\n")
    swift_zahlen()
