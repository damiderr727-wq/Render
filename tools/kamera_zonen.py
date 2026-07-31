#!/usr/bin/env python3
"""
Prueft die Kamerazonen auf zwei Fragen, die man dem Code nicht ansieht:

1. Steht die Kamera ueberhaupt im Raum? Bei follow-Zonen sitzt sie auf einem
   festen Versatz zum Spieler. Ist der Versatz groesser als der Raum, landet sie
   staendig hinter einer Wand, wird von hitsWall() herangezogen und klebt dem
   Spieler im Nacken. Im Spiel sieht das aus, als drehte sie sich nie - sie
   steht ja immer gleich dicht hinter der Figur.

2. Blickt sie entlang der LANGEN Raumachse? Eine Kamera, die quer zu einem
   langen Raum steht, zeigt eine Wand statt des Raumes.

Der Kameraversatz wird um yaw gedreht (updateCamera, Game.swift):
    ox = pos.x * cos(yaw) - pos.z * sin(yaw)
    oz = pos.x * sin(yaw) + pos.z * cos(yaw)
Bei pos = (0, h, d) heisst das: yaw 0 -> Kamera im Sueden, pi/2 -> im Westen,
-pi/2 -> im Osten, pi -> im Norden.

    python3 tools/kamera_zonen.py
"""

import math
import os
import re
import sys

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VILLA = os.path.join(HIER, 'Sources', 'Villa.swift')
GAME = os.path.join(HIER, 'Sources', 'Game.swift')


def anpassung():
    """Liest die Klammerung aus zone() in Game.swift - nicht abschreiben,
    sonst weicht das Werkzeug irgendwann vom Code ab."""
    g = open(GAME, encoding='utf-8').read()
    f = re.search(r'camFitFactor:\s*Float\s*=\s*([\d.]+)', g)
    m = re.search(r'camMinDist:\s*Float\s*=\s*([\d.]+)', g)
    return (float(f.group(1)) if f else 1e9), (float(m.group(1)) if m else 0.0)

# Wieviel Prozent der Zonenflaeche muessen die Kamera noch im Raum halten,
# damit es nicht dauernd klemmt.
SCHWELLE = 50.0


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


def wert(tok, roh):
    tok = tok.strip()
    tok = tok.replace('Float.pi', str(math.pi)).replace('.pi', str(math.pi))
    try:
        return float(eval(tok, {'__builtins__': {}}, {}))
    except Exception:
        return None


def zonen():
    roh = open(VILLA, encoding='utf-8').read()
    src = strip_comments(roh)
    rohzeilen = roh.split('\n')
    out = []
    for m in re.finditer(r'(?<![\w.])zone\(', src):
        # Klammer suchen
        d, k = 0, m.end() - 1
        while k < len(src):
            if src[k] == '(':
                d += 1
            elif src[k] == ')':
                d -= 1
                if d == 0:
                    break
            k += 1
        inner = src[m.end():k]
        # auf oberster Ebene trennen
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
        pos = [t for t in teile if ':' not in t.split('(')[0]]
        if len(pos) < 6:
            continue
        box = [wert(t, roh) for t in pos[:4]]
        if any(b is None for b in box):
            continue
        vec = re.findall(r'SCNVector3\(([^)]*)\)', inner)
        if len(vec) < 2:
            continue
        cam = [wert(v, roh) for v in vec[0].split(',')]
        benannt = {}
        for t in teile:
            if ':' in t.split('(')[0]:
                nm, v = t.split(':', 1)
                benannt[nm.strip()] = v.strip()
        yaw = wert(benannt.get('yaw', '0'), roh) or 0.0
        follow = benannt.get('follow', 'false').startswith('true')
        ln = src.count('\n', 0, m.start()) + 1
        name = ''
        for j in (src.count('\n', 0, k) + 1, ln):
            if 1 <= j <= len(rohzeilen):
                cm = re.search(r'//\s*(.+?)\s*$', rohzeilen[j - 1])
                if cm and not cm.group(1).startswith('-'):
                    name = cm.group(1).strip()
                    break
        out.append(dict(line=ln, name=name[:22], x0=box[0], x1=box[1],
                        z0=box[2], z1=box[3], cam=cam, yaw=yaw, follow=follow))
    return out


def anteil_im_raum(z, fit=1e9, mind=0.0):
    """Von wieviel Prozent der Zonenflaeche steht die Kamera noch drin?"""
    cx, cz = z['cam'][0], z['cam'][2]
    # dieselbe Klammerung wie zone() in Game.swift
    alongX = abs(math.sin(z['yaw'])) > 0.707
    extent = (z['x1'] - z['x0']) if alongX else (z['z1'] - z['z0'])
    want = math.hypot(cx, cz)
    maxD = max(mind, fit * extent)
    if want > maxD and want > 0.01:
        k = maxD / want
        cx, cz = cx * k, cz * k
    ox = cx * math.cos(z['yaw']) - cz * math.sin(z['yaw'])
    oz = cx * math.sin(z['yaw']) + cz * math.cos(z['yaw'])
    w, d = z['x1'] - z['x0'], z['z1'] - z['z0']
    # Kamera drin  <=>  Spieler in (Zone verschoben um -off) geschnitten Zone
    ux = max(0.0, w - abs(ox))
    uz = max(0.0, d - abs(oz))
    return 100.0 * (ux * uz) / (w * d), ox, oz


def himmelsrichtung(ox, oz):
    if abs(oz) >= abs(ox):
        return 'Sued' if oz > 0 else 'Nord'
    return 'Ost' if ox > 0 else 'West'


def main():
    zs = zonen()
    fit, mind = anpassung()
    print(f"Klammerung aus Game.swift: Faktor {fit}, Mindestabstand {mind} m")
    print(f"{len(zs)} Zonen aus Villa.swift\n")
    print(f"{'Zeile':>5}  {'Name':<22} {'Masse':>11}  {'Kamera':>5} "
          f"{'im Raum':>8}  {'Blick':<10} {'Bewertung'}")
    schlecht, quer = [], []
    for z in zs:
        if not z['follow']:
            continue
        pct, ox, oz = anteil_im_raum(z, fit, mind)
        w, d = z['x1'] - z['x0'], z['z1'] - z['z0']
        seite = himmelsrichtung(ox, oz)
        # Blickt sie entlang der langen Achse?
        laengs_z = d >= w
        blick_z = abs(oz) >= abs(ox)
        passt = (laengs_z == blick_z)
        note = []
        if pct < SCHWELLE:
            note.append('KLEMMT')
            schlecht.append((z, pct))
        if not passt and max(w, d) / max(0.1, min(w, d)) > 1.4:
            note.append('QUER')
            quer.append(z)
        print(f"{z['line']:>5}  {z['name']:<22} {w:>5.1f}x{d:<5.1f} "
              f"{math.hypot(ox, oz):>5.1f} {pct:>7.0f}%  {seite:<10} "
              f"{' '.join(note)}")

    print(f"\n  KLEMMT = die Kamera steht von weniger als {SCHWELLE:.0f} % der")
    print("           Raumflaeche aus noch im Raum. Sie wird dann fast immer")
    print("           von hitsWall() herangezogen und klebt am Spieler -")
    print("           im Spiel: 'die Kamera dreht sich nicht'.")
    print("  QUER   = Blickrichtung steht quer zur langen Raumachse.")
    print(f"\n  {len(schlecht)} Zonen klemmen, {len(quer)} stehen quer.")


if __name__ == '__main__':
    main()
