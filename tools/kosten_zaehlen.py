#!/usr/bin/env python3
"""
Zaehlt, was die Szene den Renderer kostet: Lichter, Schattenwerfer,
Partikelsysteme, transparente Zusatzflaechen.

Warum statisch und nicht im Spiel gemessen: dafuer braeuchte man ein iPad.
Der Quelltext reicht, weil fast alles in Schleifen ueber Literal-Listen oder
Zahlenbereiche steht - die lassen sich aufmultiplizieren.

Vorgehen: erst je Funktion zaehlen, was sie SELBST erzeugt, dann den
Aufrufgraphen von den Bauwurzeln aus aufloesen (buildVilla, buildStairwell,
spawnPlacement, buildScene). Ohne diesen Schritt zaehlt man die Lichter, die
in candelabra() oder sconce() stehen, einmal zu oft.

Nicht aufloesbare Schleifen (Umfang haengt an einer Variablen) gehen als
Faktor 1 ein. Die echten Zahlen liegen also eher hoeher als hier steht.

    python3 tools/kosten_zaehlen.py
"""

import os
import re
import sys
from collections import defaultdict

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HIER, 'Sources')

# Was ist ein "Kostenposten"? Primitive, die der Renderer teuer bezahlt.
PRIMITIVE = {
    'lichter':      ['addOmni', 'addSpot'],
    'partikel':     ['addDust'],
    'transparent':  ['floorPool', 'lightShaft', 'wallGlow', 'contactShadow'],
    'wasser':       ['waterSurface'],
    'flackern':     ['registerFlicker'],
}
ALLE_PRIM = [p for gruppe in PRIMITIVE.values() for p in gruppe]

# Wurzeln des Szenenaufbaus
# NUR buildScene: es ruft buildVilla auf, das buildStairwell aufruft.
# Alle drei als Wurzel zu zaehlen haette buildVilla doppelt und
# buildStairwell dreifach gezaehlt.
WURZELN = ['buildScene']

RANGE_RE = re.compile(
    r'for\s+[\w(),\s]+?\s+in\s+'
    r'(?:stride\(from:\s*(-?[\d.]+),\s*to:\s*(-?[\d.]+),\s*by:\s*(-?[\d.]+)\)'
    r'|(-?\d+)\s*\.\.<\s*(-?\d+)'
    r'|\[([^\]]*)\])')


def strip_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('//', i):
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if src.startswith('/*', i):
            while i < n and not src.startswith('*/', i):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            i += 2
            out.append('  ')
            continue
        out.append(src[i])
        i += 1
    return ''.join(out)


def loop_factor(text):
    m = RANGE_RE.search(text)
    if not m:
        return None
    if m.group(1) is not None:
        a, b, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return max(1, int(round((b - a) / s)))
    if m.group(4) is not None:
        return max(1, int(m.group(5)) - int(m.group(4)))
    inner = m.group(6)
    if not inner.strip():
        return 1
    depth, teile = 0, 1
    for ch in inner:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            teile += 1
    return teile


def funktionen(src):
    """{Name: Rumpf} fuer alle func-Deklarationen."""
    out = {}
    for m in re.finditer(r'\bfunc\s+(\w+)\s*(?:<[^>]*>)?\s*\(', src):
        name = m.group(1)
        j = src.find('{', m.end())
        if j < 0:
            continue
        d, k = 0, j
        while k < len(src):
            if src[k] == '{':
                d += 1
            elif src[k] == '}':
                d -= 1
                if d == 0:
                    break
            k += 1
        out.setdefault(name, src[j:k])
    return out


def direkt(body, ziele):
    """Zaehlt Aufrufe in einem Rumpf, mit Schleifenfaktoren."""
    treffer = defaultdict(int)
    unsicher = 0
    stapel = []
    for ln in body.split('\n'):
        if not ln.strip():
            continue
        ind = len(ln) - len(ln.lstrip())
        while stapel and ind <= stapel[-1][0]:
            stapel.pop()

        zeilen_mult, offene, rest = 1, 0, ln
        while True:
            m = RANGE_RE.search(rest)
            if not m:
                break
            f = loop_factor(rest[m.start():])
            zeilen_mult *= (f or 1)
            offene += 1
            rest = rest[m.end():]
        roh = len(re.findall(r'\bfor\b[^\n]*?\bin\b', ln))
        if roh > offene:
            unsicher += roh - offene

        mult = zeilen_mult
        for _, k in stapel:
            mult *= k
        for name in ziele:
            for m in re.finditer(r'(?<![\w.])' + re.escape(name) + r'\s*\(', ln):
                if ln[:m.start()].rstrip().endswith('func'):
                    continue
                treffer[name] += mult
        if roh and ln.count('{') - ln.count('}') > 0:
            stapel.append((ind, zeilen_mult if offene else 1))
    return treffer, unsicher


def main():
    quellen = {}
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.swift'):
            quellen[f] = strip_comments(open(os.path.join(SRC, f),
                                             encoding='utf-8').read())
    alle_funcs = {}
    for f, src in quellen.items():
        for n, b in funktionen(src).items():
            alle_funcs.setdefault(n, b)

    # set(): addOmni & Co. sind SELBST Funktionen im Quelltext. Standen sie
    # doppelt in der Liste, zaehlte die innere Schleife jeden Treffer zweimal.
    ziele = sorted(set(ALLE_PRIM) | set(alle_funcs))
    eigen, unsicher = {}, 0
    for n, b in alle_funcs.items():
        t, u = direkt(b, ziele)
        eigen[n] = t
        unsicher += u

    # Transitiv aufloesen: was kostet EIN Aufruf dieser Funktion?
    kosten = {}

    def aufloesen(name, pfad=()):
        if name in kosten:
            return kosten[name]
        if name in pfad or name not in eigen:
            return defaultdict(int)
        summe = defaultdict(int)
        for k, v in eigen[name].items():
            if k in ALLE_PRIM:
                summe[k] += v
            elif k in eigen:
                for kk, vv in aufloesen(k, pfad + (name,)).items():
                    summe[kk] += vv * v
        kosten[name] = summe
        return summe

    for n in alle_funcs:
        aufloesen(n)

    # Szene = Wurzeln + Moebel (spawnPlacement je Eintrag in furnitureList)
    gesamt = defaultdict(int)
    for w in WURZELN:
        for k, v in kosten.get(w, {}).items():
            gesamt[k] += v
    furn = quellen.get('Furniture.swift', '')
    n_moebel = len(re.findall(r'Placement\(kind:', furn))
    # spawnPlacement ist ein switch - im Schnitt greift ein Zweig. Der teuerste
    # Zweig (candle/lamp) hat ein Licht, die meisten haben keines.
    lampen = len(re.findall(r'Placement\(kind:\s*"(?:candle|lamp)"', furn))

    print("SZENENKOSTEN, aus dem Quelltext aufaddiert")
    print(f"  {n_moebel} Moebelstuecke, davon {lampen} mit eigener Lampe\n")

    print("  LICHTER")
    licht = gesamt['addOmni'] + gesamt['addSpot'] + lampen
    print(f"    addOmni                {gesamt['addOmni']:>4}")
    print(f"    addSpot                {gesamt['addSpot']:>4}")
    print(f"    aus Moebeln            {lampen:>4}")
    print(f"    Grundlicht + Richtlicht + Laterne   3")
    print(f"    ---------------------------------------")
    print(f"    SUMME                  {licht + 3:>4}")

    print("\n  PARTIKELSYSTEME")
    print(f"    addDust                {gesamt['addDust']:>4}"
          f"   (Lebensdauer 12 s, additiv, je Emitter rund birthRate x 12 Teilchen)")

    print("\n  TRANSPARENTE ZUSATZFLAECHEN (additiv, ohne Tiefenschreiben)")
    flaechen = 0
    for k in PRIMITIVE['transparent']:
        je = 2 if k == 'lightShaft' else 1
        n = gesamt[k] * je
        flaechen += n
        zusatz = f"  ({gesamt[k]} x {je} Flaechen)" if je > 1 else ""
        print(f"    {k:<22}{n:>4}{zusatz}")
    flaechen += gesamt['waterSurface'] * 2
    print(f"    waterSurface           {gesamt['waterSurface']*2:>4}"
          f"  ({gesamt['waterSurface']} x 2 Flaechen)")
    print(f"    ---------------------------------------")
    print(f"    SUMME                  {flaechen:>4}  Flaechen mit Ueberzeichnung")

    print("\n  JE BILD NEU GESETZT")
    print(f"    registerFlicker        {gesamt['registerFlicker']:>4}")

    # Schattenwerfer
    sh = 0
    for f, src in quellen.items():
        sh += len(re.findall(r'shadow:\s*true', src))
    print(f"\n  SCHATTENWERFER (shadow: true)   {sh}"
          f"   + Laterne = {sh + 1}")
    print("    Jeder rendert die sichtbare Geometrie ein zusaetzliches Mal.")

    if unsicher:
        print(f"\n  ({unsicher} Schleifen nicht aufloesbar, als Faktor 1 gezaehlt -")
        print("   die echten Zahlen liegen eher hoeher als hier)")


if __name__ == '__main__':
    main()
