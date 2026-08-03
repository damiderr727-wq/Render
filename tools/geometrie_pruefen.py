#!/usr/bin/env python3
"""
Findet Baufehler, die man erst im Spiel sieht:

  1. Waende, die ineinander stecken (Z-Fighting, flackernde Texturen)
  2. Boden- und Deckenplatten, die deckungsgleich uebereinander liegen
  3. Wandstuecke, die frei im Raum enden - Reste alter Grundrisse
  4. Raumhoehen: welche Decke haengt tatsaechlich ueber welchem Raum

Gelesen werden die Aufrufe von wall(), wallX(), wallZ(), floorTile() und
ceiling() aus Villa.swift und Stairwell.swift. Aufrufe mit nicht auswertbaren
Argumenten werden gezaehlt und am Ende gemeldet - sie fehlen dann in der
Pruefung, und das muss man wissen.

    python3 tools/geometrie_pruefen.py
"""

import math
import os
import re
import sys
from collections import defaultdict

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HIER, 'Sources')
DATEIEN = ['Villa.swift', 'Stairwell.swift']

WALL_T = 0.19          # halbe Wanddicke, wall() in Game.swift
MIN_UEBERLAPP = 0.05   # ab wieviel Metern Ueberschneidung gemeldet wird


def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('//', i):
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        out.append(src[i])
        i += 1
    return ''.join(out)


def zahl(tok, konst):
    """Wertet ein Argument aus, wenn es rein numerisch ist."""
    t = tok.strip()
    t = re.sub(r'\b(?:CGFloat|Float|Double)\s*\(', '(', t)
    t = t.replace('Float.pi', str(math.pi)).replace('.pi', str(math.pi))
    for k, v in konst.items():
        t = re.sub(r'(?<![\w.])' + re.escape(k) + r'(?![\w])', repr(v), t)
    if not re.fullmatch(r'[-+*/(). \d]+', t):
        return None
    try:
        return float(eval(t, {'__builtins__': {}}, {}))
    except Exception:
        return None


def args_von(src, start):
    """Argumentliste eines Aufrufs, auf oberster Ebene getrennt."""
    d, k = 0, start
    while k < len(src):
        if src[k] == '(':
            d += 1
        elif src[k] == ')':
            d -= 1
            if d == 0:
                break
        k += 1
    inner = src[start + 1:k]
    teile, d2, cur = [], 0, []
    for ch in inner:
        if ch in '([':
            d2 += 1
        elif ch in ')]':
            d2 -= 1
        if ch == ',' and d2 == 0:
            teile.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    teile.append(''.join(cur))
    return teile, k


def konstanten(src):
    """private let NAME: Typ = Zahl  - fuer Stairwell.swift"""
    k = {}
    for m in re.finditer(r'(?:private\s+)?let\s+(\w+)\s*:\s*\w+\s*=\s*([^/\n]+)', src):
        v = zahl(m.group(2), dict(k))
        if v is not None:
            k[m.group(1)] = v
    return k


def segmente(a0, a1, gaps):
    segs = [(a0, a1)]
    for c, w in gaps:
        ga, gb = c - w / 2, c + w / 2
        out = []
        for s0, s1 in segs:
            if gb <= s0 or ga >= s1:
                out.append((s0, s1))
                continue
            if ga > s0:
                out.append((s0, ga))
            if gb < s1:
                out.append((gb, s1))
        segs = out
    return segs


def gaps_von(text, konst):
    """gaps: [(Mitte, Breite), ...] aus dem Argumenttext."""
    out = []
    for m in re.finditer(r'\(([^(),]+),([^(),]+)\)', text):
        a, b = zahl(m.group(1), konst), zahl(m.group(2), konst)
        if a is not None and b is not None:
            out.append((a, b))
    return out


def einlesen():
    waende, platten, unklar = [], [], 0
    for datei in DATEIEN:
        pfad = os.path.join(SRC, datei)
        if not os.path.exists(pfad):
            continue
        src = strip_comments(open(pfad, encoding='utf-8').read())
        konst = konstanten(src)
        for m in re.finditer(r'(?<![\w.])(wallX|wallZ|floorTile|ceiling)\s*\(', src):
            name = m.group(1)
            teile, ende = args_von(src, m.end() - 1)
            ln = src.count('\n', 0, m.start()) + 1
            pos = [t for t in teile if ':' not in t.split('(')[0]]
            benannt = {}
            for t in teile:
                if ':' in t.split('(')[0]:
                    a, b = t.split(':', 1)
                    benannt[a.strip()] = b
            v = [zahl(t, konst) for t in pos]
            # wallX/wallZ: (a0, a1, fix, material) - das Material ist eine
            # Variable und nie auswertbar, also nur die ersten DREI fordern.
            noetig = 3 if name in ('wallX', 'wallZ') else 4
            if len(v) < noetig or any(x is None for x in v[:noetig]):
                unklar += 1
                continue
            if name in ('wallX', 'wallZ'):
                h = zahl(benannt.get('h', '4'), konst)
                base = zahl(benannt.get('base', '0'), konst)
                if h is None or base is None:
                    unklar += 1
                    continue
                g = gaps_von(benannt.get('gaps', ''), konst)
                a0, a1, fix = v[0], v[1], v[2]
                for s0, s1 in segmente(min(a0, a1), max(a0, a1), g):
                    if s1 - s0 <= 0.05:
                        continue
                    if name == 'wallX':
                        waende.append(dict(datei=datei, zeile=ln,
                                           x0=s0, x1=s1,
                                           z0=fix - WALL_T, z1=fix + WALL_T,
                                           y0=base, y1=base + h))
                    else:
                        waende.append(dict(datei=datei, zeile=ln,
                                           x0=fix - WALL_T, x1=fix + WALL_T,
                                           z0=s0, z1=s1,
                                           y0=base, y1=base + h))
            elif name == 'floorTile':
                y = zahl(benannt.get('y', '0'), konst)
                if y is None:
                    unklar += 1
                    continue
                w, d, cx, cz = v[0], v[1], v[2], v[3]
                platten.append(dict(datei=datei, zeile=ln, art='Boden',
                                    x0=cx - w / 2, x1=cx + w / 2,
                                    z0=cz - d / 2, z1=cz + d / 2, y=y))
            else:  # ceiling
                w, d, cx, cz = v[0], v[1], v[2], v[3]
                h = v[4] if len(v) > 4 and v[4] is not None else 4.0
                platten.append(dict(datei=datei, zeile=ln, art='Decke',
                                    x0=cx - w / 2, x1=cx + w / 2,
                                    z0=cz - d / 2, z1=cz + d / 2, y=h))
    return waende, platten, unklar


def ov(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def pruef_waende(waende):
    print("  WAENDE, DIE INEINANDER STECKEN")
    n = 0
    for i in range(len(waende)):
        for j in range(i + 1, len(waende)):
            a, b = waende[i], waende[j]
            dx = ov(a['x0'], a['x1'], b['x0'], b['x1'])
            dz = ov(a['z0'], a['z1'], b['z0'], b['z1'])
            dy = ov(a['y0'], a['y1'], b['y0'], b['y1'])
            if dx <= MIN_UEBERLAPP or dz <= MIN_UEBERLAPP or dy <= MIN_UEBERLAPP:
                continue
            # Kreuzende Waende sind normal: dann ist die Ueberschneidung auf
            # BEIDEN Achsen hoechstens eine Wanddicke.
            if dx <= 2 * WALL_T + 0.02 and dz <= 2 * WALL_T + 0.02:
                continue
            n += 1
            if n <= 12:
                print(f"    {a['datei']}:{a['zeile']} und {b['datei']}:{b['zeile']}  "
                      f"{dx:.2f} x {dz:.2f} m, Hoehe {dy:.2f} m")
    if n > 12:
        print(f"    ... und {n - 12} weitere")
    if n == 0:
        print("    keine")
    print()
    return n


def pruef_platten(platten):
    print("  PLATTEN AUF GLEICHER HOEHE, DIE SICH UEBERLAPPEN (Z-Fighting)")
    n = 0
    for i in range(len(platten)):
        for j in range(i + 1, len(platten)):
            a, b = platten[i], platten[j]
            if abs(a['y'] - b['y']) > 0.02:
                continue
            dx = ov(a['x0'], a['x1'], b['x0'], b['x1'])
            dz = ov(a['z0'], a['z1'], b['z0'], b['z1'])
            if dx <= MIN_UEBERLAPP or dz <= MIN_UEBERLAPP:
                continue
            n += 1
            if n <= 12:
                print(f"    {a['art']} {a['datei']}:{a['zeile']} und "
                      f"{b['art']} {b['datei']}:{b['zeile']}  auf y {a['y']:.2f}  "
                      f"ueberlappen {dx:.1f} x {dz:.1f} m")
    if n > 12:
        print(f"    ... und {n - 12} weitere")
    if n == 0:
        print("    keine")
    print()
    return n


def pruef_freie_enden(waende):
    """Ein Wandende, an dem keine andere Wand ansetzt und das nicht an einer
    Ecke liegt, ist meist ein Rest eines alten Grundrisses."""
    print("  WANDSTUECKE MIT FREIEM ENDE - NUR HINWEIS, kein Fehler")
    print("    Jede Tuerluecke erzeugt zwei solche Enden. Die Liste ist damit")
    print("    zu laut, um sie abzuarbeiten; sie taugt zum Nachschlagen, wenn")
    print("    im Spiel irgendwo ein Wandstumpf auffaellt.")
    n = 0
    for i, a in enumerate(waende):
        laengs_x = (a['x1'] - a['x0']) > (a['z1'] - a['z0'])
        enden = ([(a['x0'], (a['z0'] + a['z1']) / 2), (a['x1'], (a['z0'] + a['z1']) / 2)]
                 if laengs_x else
                 [((a['x0'] + a['x1']) / 2, a['z0']), ((a['x0'] + a['x1']) / 2, a['z1'])])
        for (ex, ez) in enden:
            treffer = False
            for j, b in enumerate(waende):
                if i == j:
                    continue
                if ov(a['y0'], a['y1'], b['y0'], b['y1']) <= 0.1:
                    continue
                if (b['x0'] - 0.45 <= ex <= b['x1'] + 0.45
                        and b['z0'] - 0.45 <= ez <= b['z1'] + 0.45):
                    treffer = True
                    break
            if not treffer:
                n += 1
                if n <= 10:
                    print(f"    {a['datei']}:{a['zeile']}  Ende bei "
                          f"x {ex:+.2f}  z {ez:+.2f}  (y {a['y0']:.1f}..{a['y1']:.1f})")
    if n > 10:
        print(f"    ... und {n - 10} weitere")
    if n == 0:
        print("    keine")
    print()
    return n


def raumhoehen(platten):
    """Welche Decke haengt ueber welchem Raum - und wie hoch ist sie?"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("  RAUMHOEHEN (niedrigste Decke ueber der Raummitte)")
    # Raeume aus Interaction.swift
    inter = os.path.join(SRC, 'Interaction.swift')
    raeume = []
    if os.path.exists(inter):
        s = strip_comments(open(inter, encoding='utf-8').read())
        for m in re.finditer(r'RoomInfo\(name:\s*"([^"]+)".*?x0:\s*(-?[\d.]+),\s*'
                             r'x1:\s*(-?[\d.]+),\s*z0:\s*(-?[\d.]+),\s*z1:\s*(-?[\d.]+)'
                             r'(?:.*?floor:\s*(\d+))?', s):
            raeume.append((m.group(1), float(m.group(2)), float(m.group(3)),
                           float(m.group(4)), float(m.group(5)),
                           int(m.group(6) or 0)))
    basis = {0: 0.0, 1: 3.8, 2: 6.6}
    for name, x0, x1, z0, z1, fl in raeume:
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        boden = basis.get(fl, 0.0)
        best, wo = None, ''
        for p in platten:
            if p['x0'] <= cx <= p['x1'] and p['z0'] <= cz <= p['z1'] \
                    and p['y'] > boden + 1.6:
                if best is None or p['y'] < best:
                    best, wo = p['y'], f"{p['art']} {p['datei']}:{p['zeile']}"
        if best is None:
            print(f"    {name:<20} KEINE DECKE gefunden")
        else:
            print(f"    {name:<20} {best - boden:5.2f} m   ({wo})")
    print()


def pruef_fenster():
    """Fensterteile duerfen seit dem Loch-Umbau in der LAIBUNG sitzen
    (Versatz bis -0.30, dem Anker-Abstand zur Aussenkante der Wand), aber
    nicht weiter draussen - dort ragten frueher Scheibe, Rahmen und Laibung
    unsichtbar ins Mauerwerk (Erkenntnis 11 der Uebergabe, zweimal passiert).
    """
    print("  FENSTERTEILE JENSEITS DER AUSSENKANTE (Versatz < -0.30)")
    pfad = os.path.join(SRC, 'Villa.swift')
    src = strip_comments(open(pfad, encoding='utf-8').read())
    i = src.find('func stormWindow')
    if i < 0:
        print("    stormWindow nicht gefunden")
        print()
        return 0
    j = src.index('{', i)
    d, k = 0, j
    while k < len(src):
        if src[k] == '{':
            d += 1
        elif src[k] == '}':
            d -= 1
            if d == 0:
                break
        k += 1
    body = src[j:k]
    n = 0
    # box(a, u, d, pa, pu, pd, mat) - pd ist der Versatz in den Raum.
    # -0.30 ist die Aussenkante: Anker 0.14 vor der Wandachse, Wanddicke 0.30,
    # also Achse -0.15 und Aussenflaeche bei -0.29.
    for m in re.finditer(r'(?<![\w.])box\(', body):
        teile, _ = args_von(body, m.end() - 1)
        if len(teile) < 6:
            continue
        pd = zahl(teile[5], {'D': 0.32, 'dRev': 0.06, 'dMid': -0.07})
        if pd is None or pd >= -0.30:
            continue
        n += 1
        print(f"    Villa.swift (stormWindow): Teil mit Versatz {pd:+.3f} - "
              f"ragt hinter die Aussenkante der Wand")
    if n == 0:
        print("    keine - alle Teile liegen zwischen Aussenkante und Raum")
    print()
    return n


def pruef_fensterloecher(waende):
    """Jedes stormWindow braucht seit dem Umbau ein LOCH in seiner Wand.

    Ohne Loch schaut das Fenster auf massives Mauerwerk: Glas und Backplate
    sind unsichtbar, uebrig bleibt ein Rahmen um eine Wandflaeche. Geprueft
    werden alle Aufrufe mit auswertbaren Argumenten; Aufrufe in Schleifen
    (Variablen) werden gezaehlt und gemeldet, denn sie fehlen in der Pruefung.
    """
    print("  STORMWINDOW OHNE PASSENDES WANDLOCH")
    # Loecher einsammeln: holes: [(Mitte, Breite, Bruestung, Hoehe)]
    loecher = []          # (achse 'x'/'z', fix, mitte, breite, base+sill, base+sill+hh)
    unklar = 0
    n_offen = 0
    for datei in DATEIEN:
        pfad = os.path.join(SRC, datei)
        if not os.path.exists(pfad):
            continue
        src = strip_comments(open(pfad, encoding='utf-8').read())
        konst = konstanten(src)
        for m in re.finditer(r'(?<![\w.])(wallX|wallZ)\s*\(', src):
            teile, _ = args_von(src, m.end() - 1)
            benannt = {}
            for t in teile:
                if ':' in t.split('(')[0]:
                    a, b = t.split(':', 1)
                    benannt[a.strip()] = b
            if 'holes' not in benannt:
                continue
            pos = [t for t in teile if ':' not in t.split('(')[0]]
            v = [zahl(t, konst) for t in pos[:3]]
            base = zahl(benannt.get('base', '0'), konst)
            if any(x is None for x in v) or base is None:
                unklar += 1
                continue
            fix = v[2]
            achse = 'x' if m.group(1) == 'wallX' else 'z'
            for hm in re.finditer(r'\(([^()]+)\)', benannt['holes']):
                hv = [zahl(t, konst) for t in hm.group(1).split(',')]
                if len(hv) != 4 or any(x is None for x in hv):
                    unklar += 1
                    continue
                loecher.append((achse, fix, hv[0], hv[1],
                                base + hv[2], base + hv[2] + hv[3]))
        # stormWindow-Aufrufe pruefen (Definition ueberspringen)
        fenster = []
        for m in re.finditer(r'(?<![\w.])stormWindow\s*\(', src):
            if src.rfind('func', max(0, m.start() - 6), m.start()) >= 0:
                continue
            teile, _ = args_von(src, m.end() - 1)
            ln = src.count('\n', 0, m.start()) + 1
            v = [zahl(t, konst) for t in teile[:7]]
            if any(x is None for x in v):
                unklar += 1
                continue
            fenster.append((ln, v))
        for ln, v in fenster:
            wx, wy, wz, ww, wh, nx, nz = v
            # Wandachse liegt 0.14 hinter dem Anker, entlang der Normalen
            if abs(nx) > 0.5:
                achse, fix, mitte = 'z', wx - 0.14 * nx, wz
            else:
                achse, fix, mitte = 'x', wz - 0.14 * nz, wx
            lo, hi = wy - wh / 2, wy + wh / 2
            ok = False
            for (la, lf, lc, lw, ly0, ly1) in loecher:
                if la != achse or abs(lf - fix) > 0.25:
                    continue
                if abs(lc - mitte) > 0.30 or lw < ww - 0.02:
                    continue
                if ly0 > lo + 0.06 or ly1 < hi - 0.06:
                    continue
                ok = True
                break
            if not ok:
                n_offen += 1
                print(f"    {datei}:{ln}  Fenster bei ({wx:+.2f},{wz:+.2f}) "
                      f"hat kein passendes Loch in der Wand")
    if unklar:
        print(f"    ({unklar} Aufrufe mit Variablen nicht pruefbar - "
              f"Schleifenfenster fehlen in dieser Pruefung)")
    if n_offen == 0:
        print("    alle auswertbaren Fenster sitzen in einem Loch")
    print()
    return n_offen


def pruef_treppendeckel(platten):
    """Grosse Platten, die ueber einem Treppenlauf liegen.

    ZWEIMAL passiert, beide Male derselbe Griff: ein Loch im Boden gelassen,
    die Platte darueber vergessen.
      - Schwimmhalle: eine durchgehende Bodenplatte lag ueber dem fertig
        gebauten Becken. "Beim Poolraum existiert nicht mal ein Pool."
      - Tiefkeller: die Deckenuntersicht lag ueber dem Treppenloch.
        "Bei der Treppe versperrt eine Holzplatte alles nach unten."

    Geprueft wird der Kopfraum ueber jedem stairRun: von 30 cm ueber der
    tiefsten Stufe bis 2 m ueber der hoechsten. Nur GROSSE Platten (ueber
    6 m2) - die Trittstufen und Podeste sind selbst prop-Platten und gehoeren
    natuerlich dorthin.
    """
    print("  PLATTEN UEBER EINEM TREPPENLAUF")
    laeufe = []
    unklar = 0
    # Flache prop()-Koerper zaehlen hier als Platte - die Deckenuntersicht des
    # Tiefkellers war genau so eine und stand in keiner der beiden Listen, die
    # einlesen() fuehrt. Sie kommen NUR in diese Pruefung, nicht in die
    # Z-Fighting-Pruefung: dort waere jede Tischplatte ein Fehlalarm.
    alle = list(platten)
    for datei in DATEIEN:
        pfad = os.path.join(SRC, datei)
        if not os.path.exists(pfad):
            continue
        src = strip_comments(open(pfad, encoding='utf-8').read())
        konst = konstanten(src)
        for m in re.finditer(r'(?<![\w.])prop\s*\(', src):
            teile, _ = args_von(src, m.end() - 1)
            pos = [t for t in teile if ':' not in t.split('(')[0]]
            v = [zahl(t, konst) for t in pos[:6]]
            if len(v) < 6 or any(x is None for x in v):
                continue
            w, h, d, px, py, pz = v
            if h > 0.25:            # nur flache Koerper sind Platten
                continue
            alle.append(dict(datei=datei, zeile=src.count('\n', 0, m.start()) + 1,
                             art='Platte', x0=px - w / 2, x1=px + w / 2,
                             z0=pz - d / 2, z1=pz + d / 2, y=py))
    for datei in DATEIEN:
        pfad = os.path.join(SRC, datei)
        if not os.path.exists(pfad):
            continue
        src = strip_comments(open(pfad, encoding='utf-8').read())
        konst = konstanten(src)
        for m in re.finditer(r'(?<![\w.])stairRun\s*\(', src):
            if src.rfind('func', max(0, m.start() - 6), m.start()) >= 0:
                continue
            teile, _ = args_von(src, m.end() - 1)
            ln = src.count('\n', 0, m.start()) + 1
            v = [zahl(t, konst) for t in teile[:6]]
            if any(x is None for x in v):
                unklar += 1
                continue
            x, zf, zt, w, yf, yt = v
            laeufe.append(dict(datei=datei, zeile=ln,
                               x0=x - w / 2, x1=x + w / 2,
                               z0=min(zf, zt), z1=max(zf, zt),
                               ylo=min(yf, yt), yhi=max(yf, yt)))
    n = 0
    for L in laeufe:
        for p in alle:
            flaeche = (p['x1'] - p['x0']) * (p['z1'] - p['z0'])
            if flaeche < 6.0:
                continue
            dx = ov(L['x0'], L['x1'], p['x0'], p['x1'])
            dz = ov(L['z0'], L['z1'], p['z0'], p['z1'])
            if dx <= MIN_UEBERLAPP or dz <= MIN_UEBERLAPP:
                continue
            if not (L['ylo'] + 0.30 <= p['y'] <= L['yhi'] + 2.0):
                continue
            n += 1
            print(f"    {p['art']} {p['datei']}:{p['zeile']} auf y {p['y']:.2f} "
                  f"liegt ueber der Treppe {L['datei']}:{L['zeile']} "
                  f"(y {L['ylo']:.2f}..{L['yhi']:.2f}), "
                  f"Ueberdeckung {dx:.1f} x {dz:.1f} m")
    print(f"    ({len(laeufe)} Laeufe geprueft"
          + (f", {unklar} nicht auswertbar" if unklar else "") + ")")
    if n == 0:
        print("    keine - alle Laeufe haben freien Kopfraum")
    print()
    return n


def main():
    waende, platten, unklar = einlesen()
    print("GEOMETRIEPRUEFUNG")
    print(f"  {len(waende)} Wandstuecke, {len(platten)} Platten eingelesen")
    if unklar:
        print(f"  {unklar} Aufrufe mit nicht auswertbaren Argumenten - "
              f"die fehlen in der Pruefung")
    print()
    a = pruef_waende(waende)
    b = pruef_platten(platten)
    c = pruef_freie_enden(waende)
    f = pruef_fenster()
    g = pruef_fensterloecher(waende)
    t = pruef_treppendeckel(platten)
    raumhoehen(platten)
    print(f"  {a} Wandueberschneidungen, {b} Plattenueberlappungen, "
          f"{f} Fensterteile hinter der Aussenkante, {g} Fenster ohne Loch, "
          f"{t} Platten ueber Treppen")
    print(f"  ({c} freie Wandenden - nur Hinweis, siehe oben)")


if __name__ == '__main__':
    main()
