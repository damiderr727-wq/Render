#!/usr/bin/env python3
"""
Vermessung des GEBAUTEN Treppenhauses.

Der Unterschied zu treppe_entwurf.py: dieses Werkzeug liest die Zahlen aus
Sources/Stairwell.swift ein - die Konstanten und die Aufrufe von stairRun(),
stairLanding() und stairUnderFill(). Es prueft also, was im Code steht, nicht
was ich gemeint habe. Ein vertippter Wert faellt hier auf, im Entwurfsskript
nicht.

Die Waende und Platten rings um den Schacht stehen in Villa.swift und sind hier
von Hand nachgetragen; sie sind mit Zeilenverweis kommentiert.

    python3 tools/treppe_messen.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenemodel import (Scene, Box, pruef_steigungen, pruef_freiraum,
                        pruef_kopffreiheit, begehbar, MIN_HEAD)

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWIFT = os.path.join(HIER, 'Sources', 'Stairwell.swift')


# ------------------------------------------------------------------ einlesen

def funcbody(src, name):
    """Rumpf einer Swift-Funktion inklusive der aeusseren geschweiften Klammern."""
    i = src.index('func ' + name)
    j = src.index('{', i)
    depth, k = 0, j
    while k < len(src):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                return src[j:k + 1]
        k += 1
    raise ValueError(f'Rumpf von {name} nicht gefunden')


def lade_swift():
    src = open(SWIFT, encoding='utf-8').read()
    konst = {}
    # Rechte Seiten duerfen einfache Ausdrucke ueber schon bekannte Konstanten
    # sein - landingN und stairFoot werden im Swift abgeleitet, nicht getippt.
    for m in re.finditer(r'private let (\w+)\s*:\s*\w+\s*=\s*([^/\n]+)', src):
        name, rhs = m.group(1), m.group(2).strip()
        if not re.fullmatch(r'[\w\s+\-*/.()]+', rhs):
            continue
        try:
            konst[name] = float(eval(rhs, {'__builtins__': {}}, dict(konst)))
        except Exception:
            pass

    def wert(tok):
        tok = tok.strip()
        if ':' in tok:
            tok = tok.split(':', 1)[1].strip()
        if tok in konst:
            return konst[tok]
        return float(tok)

    # Nur der Rumpf von buildStairwell - stairRun steht auch in der eigenen
    # Deklaration und die soll nicht als Aufruf zaehlen.
    i = src.index('func buildStairwell')
    body = src[i:]

    # Die drei Zahlen, an denen die ALTE Treppe gescheitert ist, werden aus den
    # Funktionsruempfen gelesen statt in Python nachgebaut. Sonst prueft dieses
    # Werkzeug nur seine eigene Nachbildung - und genau das ist mir hier schon
    # einmal passiert: eine verdrehte Fuellungshoehe blieb unbemerkt.
    fb = funcbody(src, 'stairUnderFill')
    m = re.search(r'let top\s*=\s*min\(ya,\s*yb\)\s*([+-])\s*([\d.]+)', fb)
    konst['_fillClear'] = (1 if m.group(1) == '+' else -1) * float(m.group(2))
    m = re.search(r'if top\s*<\s*([\d.]+)\s*\{\s*continue', fb)
    konst['_fillMin'] = float(m.group(1)) if m else 0.0

    rb = funcbody(src, 'stairRun')
    # Kamerasperre: MUSS blocksPlayer: false haben. Ab der Zeile mit der 0.85
    # bis zum Ende des WallBox-Aufrufs suchen - ein Zeichenklassen-Regex bricht
    # am ersten ')' von max(ya, yb) ab und sieht das Flag nie.
    i85 = rb.find('- 0.85')
    seg = rb[i85:rb.find('))', i85) + 2] if i85 >= 0 else ''
    konst['_camBlocksPlayer'] = 0.0 if 'blocksPlayer: false' in seg else 1.0
    # Wange: Hoehenbereich relativ zur Rampe
    m = re.search(r'y0:\s*min\(ya,\s*yb\)\s*([+-])\s*([\d.]+),\s*'
                  r'y1:\s*max\(ya,\s*yb\)\s*([+-])\s*([\d.]+),\s*\n\s*blocksCamera', rb)
    konst['_wangeLo'] = (1 if m.group(1) == '+' else -1) * float(m.group(2))
    konst['_wangeHi'] = (1 if m.group(3) == '+' else -1) * float(m.group(4))

    laeufe, podeste, fuellungen = [], [], []
    for m in re.finditer(r'\bstairRun\(([^)]*)\)', body):
        a = m.group(1).split(',')
        laeufe.append(dict(x=wert(a[0]), z0=wert(a[1]), z1=wert(a[2]),
                           w=wert(a[3]), y0=wert(a[4]), y1=wert(a[5]),
                           n=int(wert(a[6]))))
    for m in re.finditer(r'\bstairLanding\(([^)]*)\)', body):
        podeste.append(wert(m.group(1).split(',')[0]))
    for m in re.finditer(r'\bstairUnderFill\(([^)]*)\)', body):
        a = m.group(1).split(',')
        fuellungen.append(dict(x=wert(a[0]), z0=wert(a[1]), z1=wert(a[2]),
                               w=wert(a[3]), y0=wert(a[4]), y1=wert(a[5])))
    return konst, laeufe, podeste, fuellungen


def bauen():
    K, laeufe, podeste, fuellungen = lade_swift()
    sc = Scene("Gebautes Treppenhaus (Zahlen aus Sources/Stairwell.swift)")

    XW, XE = K['shaftW'], K['shaftE']
    ZN, ZS = K['shaftN'], K['shaftS']
    XIW, XIE, ZIS = K['shaftIW'], K['shaftIE'], K['shaftIS']
    FOOT, LAND = K['stairFoot'], K['landingN']
    CEIL = K['shaftCeil']

    # ---- Waende aus Stairwell.swift ----
    sc.wall_z(ZN, FOOT, XE, h=6.6, tag='Ostwand am Band')
    sc.wall_z(FOOT, ZS, XE, h=CEIL, tag='Ostwand am Schacht')
    sc.wall_z(ZN, ZS, XW, h=CEIL - 6.0, base=6.0, tag='Westwand oben')
    sc.wall_x(XW, XE, ZS, h=CEIL - 6.0, base=6.0, tag='Suedwand oben')
    # ---- Waende aus Villa.swift ----
    sc.wall_z(0, 14, XW, gaps=[(3.5, 2.4)], h=6, tag='Westwand x=-8 (Villa)')
    sc.wall_x(-8, 8, 14, h=6, tag='Suedwand z=14 (Villa)')
    sc.wall_x(-8, -2, ZN, gaps=[(-4.0, 4.0)], h=3.8, tag='Nordwand EG (Villa)')
    sc.wall_x(-8, -6, ZN, h=2.2, base=3.8, lintel=False,
              tag='Nordwand OG (Villa)')

    # ---- Boeden ----
    sc.floor(-8, 8, 0, 14, 0.0, tag='Boden EG (Villa)')
    sc.floor(-8, -2, 0.5, 6.0, 3.80, tag='Galerie OG (Villa)')
    sc.floor(-8, -4, 3.0, 6.0, 6.60, tag='Vorraum BH (Villa)')
    bandD = FOOT - ZN
    sc.floor(XW, XE, ZN, FOOT, 3.80, tag='Bodenband OG')
    sc.floor(XW, XE, ZN, FOOT, 6.60, tag='Bodenband BH')
    sc.ceil(XW, XE, ZN, FOOT, 6.0, tag='Decke ueber dem Band')
    sc.ceil(XW, XE, FOOT, ZS, CEIL, tag='Schachtdecke')

    # ---- Laeufe, Podeste, Fuellungen aus dem Swift ----
    for k, f in enumerate(laeufe):
        sc.stair_run(f['x'], f['z0'], f['z1'], f['w'], f['y0'], f['y1'], f['n'],
                     rail_off=f['w'] / 2 + 0.09, tag=f'Lauf {"ABCD"[k]}',
                     cam_blocks_player=bool(K['_camBlocksPlayer']),
                     wange_lo=K['_wangeLo'], wange_hi=K['_wangeHi'])
    for k, y in enumerate(podeste):
        sc.floor(XIW, XIE, LAND, ZIS, y, tag=f'Podest {k + 1}')
    for f in fuellungen:
        segs = 8
        for k in range(segs):
            t0, t1 = k / segs, (k + 1) / segs
            za = f['z0'] + (f['z1'] - f['z0']) * t0
            zb = f['z0'] + (f['z1'] - f['z0']) * t1
            ya = f['y0'] + (f['y1'] - f['y0']) * t0
            yb = f['y0'] + (f['y1'] - f['y0']) * t1
            top = min(ya, yb) + K['_fillClear']
            if top < K['_fillMin']:
                continue
            sc.solids.append(Box(f['x'] - f['w'] / 2 - 0.04,
                                 f['x'] + f['w'] / 2 + 0.04, za, zb,
                                 0.0, top, blocks_camera=False,
                                 tag='Fuellung unter Lauf'))
    # Kammer unter dem Podest, Stairwell.swift
    sc.solids.append(Box(XIW, XIE, LAND + 0.05, ZIS, 0.0, 1.60,
                         blocks_camera=False, tag='Kammer unter Podest'))
    return sc, K, laeufe


if __name__ == '__main__':
    sc, K, laeufe = bauen()
    print("=" * 74)
    print(sc.name)
    print("=" * 74)
    print(f"  {len(laeufe)} Laeufe gelesen, {len(sc.solids)} Sperren, "
          f"{len(sc.areas)} Flaechen\n")

    ok = True
    ok &= pruef_steigungen(sc)
    ok &= pruef_freiraum(sc)
    ok &= pruef_kopffreiheit(sc)

    FOOT, LAND = K['stairFoot'], K['landingN']
    XA, XB, ZIS = K['laneWest'], K['laneEast'], K['shaftIS']
    weg = [(-5.0, 4.0), (-5.0, 7.2),
           (XA, 8.4), (XA, FOOT + 0.2), (XA, LAND - 0.1), (XA, ZIS - 0.5),
           (XB, ZIS - 0.5), (XB, LAND + 0.1), (XB, FOOT + 0.1), (XB, FOOT - 0.8),
           (XA, FOOT - 0.8),
           (XA, FOOT + 0.2), (XA, LAND - 0.1), (XA, ZIS - 0.5),
           (XB, ZIS - 0.5), (XB, LAND + 0.1), (XB, FOOT + 0.1), (XB, FOOT - 0.8)]
    ok &= begehbar(sc, weg, "Flur EG -> Obergeschoss -> Badehaus")
    print()
    print("=" * 74)
    print("ERGEBNIS: alles bestanden." if ok else "ERGEBNIS: FEHLER, siehe oben.")
    sys.exit(0 if ok else 1)
