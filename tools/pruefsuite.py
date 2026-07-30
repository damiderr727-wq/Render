#!/usr/bin/env python3
"""
Pruefsuite fuer Sanatorium Nachtschatten.

Ersetzt keinen Compiler. Sie prueft genau die Fehlerklassen, die in diesem
Projekt tatsaechlich mehrfach aufgetreten sind - jede Pruefung ist aus einem
echten Fehler entstanden, nicht aus einer Checkliste.

    python3 tools/pruefsuite.py [Verzeichnis]

Rueckgabe 0 = alles sauber, 1 = mindestens ein FEHLER.
Hinweise (HINWEIS) aendern den Rueckgabewert nicht.
"""

import os
import re
import sys
from collections import defaultdict

# ---------------------------------------------------------------- Textaufbereitung

def strip_code(src):
    """Ersetzt Kommentare und Stringinhalte durch Leerzeichen.

    Zeilenumbrueche bleiben erhalten, damit Zeichenpositionen und damit alle
    Zeilennummern gueltig bleiben. Ohne das melden die Klammernbilanz und die
    Labelpruefung Treffer aus Kommentaren.
    """
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            # Swift erlaubt geschachtelte Blockkommentare
            depth = 1
            out.append('  ')
            i += 2
            while i < n and depth > 0:
                if src.startswith('/*', i):
                    depth += 1
                    out.append('  ')
                    i += 2
                elif src.startswith('*/', i):
                    depth -= 1
                    out.append('  ')
                    i += 2
                else:
                    out.append('\n' if src[i] == '\n' else ' ')
                    i += 1
            continue
        if src.startswith('"""', i):
            out.append('   ')
            i += 3
            while i < n and not src.startswith('"""', i):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('   ')
            i += 3
            continue
        if c == '"':
            out.append('"')
            i += 1
            while i < n and src[i] != '"':
                if src[i] == '\\' and i + 1 < n:
                    out.append('  ')
                    i += 2
                    continue
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            if i < n:
                out.append('"')
                i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1


# ---------------------------------------------------------------- Bericht

class Report:
    def __init__(self):
        self.errors = []
        self.notes = []
        self.checks = []

    def error(self, where, msg):
        self.errors.append((where, msg))

    def note(self, where, msg):
        self.notes.append((where, msg))

    def done(self, name, count):
        self.checks.append((name, count))


# ---------------------------------------------------------------- 1 Klammernbilanz

def check_brackets(files, rep):
    pairs = {'}': '{', ')': '(', ']': '['}
    for path, clean in files.items():
        stack = []
        bad = 0
        for i, ch in enumerate(clean):
            if ch in '{([':
                stack.append((ch, i))
            elif ch in pairs:
                if not stack:
                    rep.error(f"{os.path.basename(path)}:{line_of(clean, i)}",
                              f"schliessendes '{ch}' ohne Gegenstueck")
                    bad += 1
                elif stack[-1][0] != pairs[ch]:
                    op, opos = stack[-1]
                    rep.error(f"{os.path.basename(path)}:{line_of(clean, i)}",
                              f"'{ch}' schliesst '{op}' aus Zeile {line_of(clean, opos)}")
                    bad += 1
                    stack.pop()
                else:
                    stack.pop()
        for op, opos in stack:
            rep.error(f"{os.path.basename(path)}:{line_of(clean, opos)}",
                      f"'{op}' wird nie geschlossen")
            bad += 1
    rep.done("Klammernbilanz", len(files))


# ---------------------------------------------------------------- 2 Texturen

def check_textures(files, rep):
    declared = set()
    for path, clean in files.items():
        if os.path.basename(path) != 'Textures.swift':
            continue
        m = re.search(r'\benum\s+Tex\s*\{', clean)
        if not m:
            continue
        depth, i = 0, m.end() - 1
        start = i
        while i < len(clean):
            if clean[i] == '{':
                depth += 1
            elif clean[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = clean[start:i]
        declared |= set(re.findall(r'static\s+(?:let|var)\s+(\w+)', body))

    used = defaultdict(list)
    for path, clean in files.items():
        for m in re.finditer(r'\bTex\.(\w+)', clean):
            used[m.group(1)].append((path, line_of(clean, m.start())))

    for name, spots in sorted(used.items()):
        if name not in declared:
            path, ln = spots[0]
            rep.error(f"{os.path.basename(path)}:{ln}",
                      f"Tex.{name} ist in Textures.swift nicht deklariert"
                      f" ({len(spots)} Verwendungen)")
    unused = sorted(declared - set(used))
    if unused:
        rep.note("Textures.swift", "nie benutzt: " + ", ".join(unused))
    rep.done("Texturen", len(used))


# ---------------------------------------------------------------- Signaturen

FUNC_RE = re.compile(r'(^[ \t]*)(?:@discardableResult\s+)?'
                     r'(?:(?:public|private|fileprivate|internal|final|static|class|override|mutating)\s+)*'
                     r'func\s+(\w+)\s*(?:<[^>]*>)?\s*\(', re.M)


def split_top(text):
    """Teilt eine Parameter- oder Argumentliste auf oberster Ebene."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch in '([{<':
            depth += 1
        elif ch in ')]}>':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    if ''.join(cur).strip():
        parts.append(''.join(cur))
    return parts


def matching_paren(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] in '([{':
            depth += 1
        elif text[i] in ')]}':
            depth -= 1
            if depth == 0:
                return i
    return -1


class Signature:
    __slots__ = ('name', 'labels', 'types', 'path', 'line', 'free', 'scope')

    def __init__(self, name, labels, types, path, line, free, scope):
        self.name = name
        self.labels = labels     # '_' fuer unbenannt
        self.types = types
        self.path = path
        self.line = line
        self.free = free
        self.scope = scope       # Typname, 'global' oder 'local'


TYPE_RE = re.compile(r'\b(?:class|struct|enum|extension|protocol|actor)\s+(\w+)')
FUNCHEAD_RE = re.compile(r'\bfunc\s+\w+')


def scope_stack(clean):
    """Liefert je '{' den Kontext, in dem es steht.

    Ohne das meldete die Duplikatpruefung FloorArea.contains gegen
    RoomInfo.contains und jede lokale Hilfsfunktion pt() gegen sich selbst -
    lauter Fehler, die es nicht gibt.
    """
    events = []      # (open_pos, close_pos, kind, name)
    stack = []
    for i, ch in enumerate(clean):
        if ch == '{':
            head = clean[max(0, i - 240):i]
            tm = None
            for tm in TYPE_RE.finditer(head):
                pass
            fm = None
            for fm in FUNCHEAD_RE.finditer(head):
                pass
            # Was steht naeher am '{' - eine Typdeklaration oder ein func?
            if tm and (not fm or tm.start() > fm.start()):
                kind, name = 'type', tm.group(1)
            elif fm:
                kind, name = 'func', ''
            else:
                kind, name = 'block', ''
            stack.append([i, kind, name])
        elif ch == '}' and stack:
            op, kind, name = stack.pop()
            events.append((op, i, kind, name))
    for op, kind, name in stack:
        events.append((op, len(clean), kind, name))
    return events


def context_at(events, pos):
    """Innerster Kontext um pos: Typname, 'local' (in einem func-Koerper)
    oder 'global'."""
    inner = [e for e in events if e[0] < pos < e[1]]
    inner.sort(key=lambda e: e[0], reverse=True)
    for op, close, kind, name in inner:
        if kind == 'func':
            return 'local'
        if kind == 'type':
            return name
    return 'global'


def collect_signatures(files):
    sigs = defaultdict(list)
    for path, clean in files.items():
        events = scope_stack(clean)
        for m in FUNC_RE.finditer(clean):
            indent, name = m.group(1), m.group(2)
            close = matching_paren(clean, m.end() - 1)
            if close < 0:
                continue
            params = split_top(clean[m.end():close])
            labels, types = [], []
            for p in params:
                p = p.strip()
                if not p:
                    continue
                head = p.split(':', 1)
                names = head[0].strip().split()
                labels.append(names[0] if names else '_')
                types.append(head[1].strip() if len(head) > 1 else '')
            sigs[name].append(Signature(name, labels, types, path,
                                        line_of(clean, m.start()),
                                        len(indent) == 0,
                                        context_at(events, m.start())))
    return sigs


# ---------------------------------------------------------------- 3 doppelte Namen

def check_duplicates(sigs, rep):
    for name, group in sorted(sigs.items()):
        seen = defaultdict(list)
        for s in group:
            if s.scope == 'local':
                continue          # lokale Hilfsfunktionen kollidieren nie
            seen[(s.scope, tuple(s.labels))].append(s)
        for (scope, labels), same in seen.items():
            if len(same) > 1:
                spots = ", ".join(f"{os.path.basename(s.path)}:{s.line}" for s in same)
                rep.error(spots, f"{scope}.{name}({', '.join(labels)}) mehrfach deklariert")
    rep.done("Doppelte Funktionsnamen", len(sigs))


# ---------------------------------------------------------------- Aufrufe

CALL_RE = re.compile(r'(?<![\w.])(\w+)\s*\(')
KEYWORDS = {'if', 'for', 'while', 'switch', 'guard', 'return', 'func', 'init',
            'catch', 'repeat', 'case', 'in', 'let', 'var', 'else', 'do', 'try',
            'defer', 'where', 'and', 'or', 'not'}
LABEL_RE = re.compile(r'^\s*(\w+)\s*:')


def call_labels(argtext):
    """Argumentlabels auf oberster Ebene. Ternaeres '?:' faellt nicht herein,
    weil dort vor dem Doppelpunkt ein Ausdruck steht, kein einzelner Name."""
    out = []
    for part in split_top(argtext):
        m = LABEL_RE.match(part)
        if m and '?' not in part.split(':', 1)[0]:
            out.append(m.group(1))
        else:
            out.append('_')
    return out


def iter_calls(files, sigs):
    for path, clean in files.items():
        for m in CALL_RE.finditer(clean):
            name = m.group(1)
            if name in KEYWORDS or name not in sigs:
                continue
            # Deklaration selbst ueberspringen
            pre = clean[max(0, m.start() - 40):m.start()]
            if re.search(r'\bfunc\s+$', pre):
                continue
            close = matching_paren(clean, m.end() - 1)
            if close < 0:
                continue
            yield path, clean, m, close, clean[m.end():close]


def check_labels(files, sigs, rep):
    n_calls = 0
    for path, clean, m, close, argtext in iter_calls(files, sigs):
        name = m.group(1)
        n_calls += 1
        given = call_labels(argtext)
        if not any(g != '_' for g in given):
            continue
        cands = sigs[name]
        ok_any = False
        for s in cands:
            named = [l for l in s.labels if l != '_']
            if all(g == '_' or g in named for g in given):
                ok_any = True
                break
        where = f"{os.path.basename(path)}:{line_of(clean, m.start())}"
        if not ok_any:
            allowed = sorted({l for s in cands for l in s.labels if l != '_'})
            unknown = [g for g in given if g != '_'
                       and g not in allowed]
            if unknown:
                rep.error(where, f"{name}(...): unbekanntes Argumentlabel "
                                 f"'{unknown[0]}' - erlaubt: {', '.join(allowed) or 'keine'}")
                continue
        # Reihenfolge: Swift verlangt Deklarationsreihenfolge
        for s in cands:
            named = [l for l in s.labels if l != '_']
            gs = [g for g in given if g != '_']
            if not all(g in named for g in gs):
                continue
            order = [named.index(g) for g in gs]
            if order != sorted(order):
                rep.error(where, f"{name}(...): Labelreihenfolge {', '.join(gs)} "
                                 f"weicht von der Deklaration ab "
                                 f"({', '.join(named)}, {os.path.basename(s.path)}:{s.line})")
            break
    rep.done("Argumentlabels", n_calls)


# ---------------------------------------------------------------- 6 Float/CGFloat

def check_float(files, sigs, rep):
    """Nur eindeutige Faelle: ein Name ab 4 Zeichen, der im ganzen Projekt
    immer denselben Typ hat, als ganzes Argument uebergeben. Alles andere
    war in der Vergangenheit nur Rauschen."""
    typed = defaultdict(set)
    decl = re.compile(r'\b(?:let|var)\s+(\w{4,})\s*:\s*(Float|CGFloat)\b')
    for path, clean in files.items():
        for m in decl.finditer(clean):
            typed[m.group(1)].add(m.group(2))
    unique = {k: v.pop() for k, v in typed.items() if len(v) == 1}

    hits = 0
    for path, clean, m, close, argtext in iter_calls(files, sigs):
        name = m.group(1)
        cands = [s for s in sigs[name]]
        if len(cands) != 1:
            continue
        s = cands[0]
        args = split_top(argtext)
        if len(args) != len(s.labels):
            continue
        for arg, ptype in zip(args, s.types):
            a = arg.strip()
            if ':' in a:
                a = a.split(':', 1)[1].strip()
            base = ptype.replace('inout', '').strip().rstrip('?')
            if base not in ('Float', 'CGFloat'):
                continue
            if a in unique and unique[a] != base:
                rep.error(f"{os.path.basename(path)}:{line_of(clean, m.start())}",
                          f"{name}(...): '{a}' ist {unique[a]}, "
                          f"Parameter erwartet {base}")
                hits += 1
    rep.done("Float/CGFloat", len(unique))


# ---------------------------------------------------------------- 7 self auf freie Funktionen

def check_self_free(files, sigs, rep):
    free = {n for n, g in sigs.items()
            if g and all(s.scope == 'global' for s in g)}
    for path, clean in files.items():
        for m in re.finditer(r'\bself\.(\w+)\s*\(', clean):
            if m.group(1) in free:
                rep.error(f"{os.path.basename(path)}:{line_of(clean, m.start())}",
                          f"self.{m.group(1)}() - {m.group(1)} ist eine freie Funktion")
    rep.done("self auf freie Funktionen", len(free))


# ---------------------------------------------------------------- 8 Kamerazonen

NUM_RE = re.compile(r'^-?\d+(?:\.\d+)?$')


def parse_num(tok):
    tok = tok.strip()
    if NUM_RE.match(tok):
        return float(tok)
    return None


def check_zones(files, raw, sigs, rep):
    zones = []
    for path, clean, m, close, argtext in iter_calls(files, sigs):
        if m.group(1) != 'zone':
            continue
        args = split_top(argtext)
        pos = [a for a in args if not LABEL_RE.match(a)]
        if len(pos) < 4:
            continue
        box = [parse_num(a) for a in pos[:4]]
        if any(b is None for b in box):
            continue
        ylo, yhi = -1.0, 2.6            # Vorgaben aus der Deklaration in Game.swift
        for a in args:
            lm = LABEL_RE.match(a)
            if not lm:
                continue
            val = parse_num(a.split(':', 1)[1])
            if val is None:
                continue
            if lm.group(1) == 'yLo':
                ylo = val
            elif lm.group(1) == 'yHi':
                yhi = val
        # Der Raumname steht als Kommentar am Ende des Aufrufs. strip_code hat
        # ihn geleert, also aus dem Rohtext holen - ohne Namen ist die Meldung
        # "Zone 2696 ueberlappt Zone 2701" praktisch unbrauchbar.
        rawlines = raw[path].split('\n')
        label = ''
        for ln in (line_of(clean, close), line_of(clean, m.start())):
            if 1 <= ln <= len(rawlines):
                cm = re.search(r'//\s*(.+?)\s*$', rawlines[ln - 1])
                if cm and not cm.group(1).startswith('-'):
                    label = cm.group(1).strip()
                    break
        zones.append({
            'line': line_of(clean, m.start()),
            'x0': box[0], 'x1': box[1], 'z0': box[2], 'z1': box[3],
            'ylo': ylo, 'yhi': yhi, 'label': label[:28],
        })

    def ov(a0, a1, b0, b1):
        return min(a1, b1) - max(a0, b0)

    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            a, b = zones[i], zones[j]
            dx = ov(a['x0'], a['x1'], b['x0'], b['x1'])
            dz = ov(a['z0'], a['z1'], b['z0'], b['z1'])
            dy = ov(a['ylo'], a['yhi'], b['ylo'], b['yhi'])
            if dx <= 0 or dz <= 0 or dy <= 0:
                continue
            what = (f"Zone Z{a['line']} ({a['label']}) und Z{b['line']} ({b['label']}) "
                    f"ueberlappen {dx:.2f} x {dz:.2f} m, Hoehe {dy:.2f} m")
            # updateCamera nimmt die ERSTE passende Zone - die spaetere verliert
            if dx > 0.05 and dz > 0.05:
                rep.error(f"Villa.swift:{b['line']}", what + " - die spaetere greift nie")
            else:
                rep.note(f"Villa.swift:{b['line']}", what + " (nur Kante)")
    rep.done("Kamerazonen", len(zones))


# ---------------------------------------------------------------- 9 SwiftUI-Panels

def check_views(files, rep):
    count = 0
    for path, clean in files.items():
        for m in re.finditer(r'\bvar\s+(\w+)\s*:\s*some\s+View\s*\{', clean):
            name = m.group(1)
            open_idx = clean.index('{', m.end() - 1)
            close = matching_paren(clean, open_idx)
            if close < 0:
                continue
            body = clean[open_idx + 1:close]
            count += 1
            # Wurzelausdruecke: Zeilen auf Tiefe 0, die mit einem Grossbuchstaben
            # oder einem Steuerwort beginnen. Modifierketten (.padding) und
            # Fortsetzungen zaehlen nicht mit.
            depth, roots = 0, 0
            for raw in body.split('\n'):
                stripped = raw.strip()
                if depth == 0 and stripped:
                    first = stripped.split('(')[0].split('{')[0].strip()
                    if (first[:1].isupper() or first.split()[0] in ('if', 'ForEach', 'Group')) \
                            and not stripped.startswith('.'):
                        roots += 1
                depth += raw.count('{') + raw.count('(') + raw.count('[')
                depth -= raw.count('}') + raw.count(')') + raw.count(']')
            if roots > 1:
                rep.note(f"{os.path.basename(path)}:{line_of(clean, m.start())}",
                         f"{name}: {roots} Wurzelausdruecke auf oberster Ebene "
                         f"- ViewBuilder erlaubt max. 10, aber die Hausregel ist einer")
    rep.done("SwiftUI-Panels", count)


# ---------------------------------------------------------------- 10 Editor-Arten

def check_kinds(files, rep):
    """Jede Art, die der Editor anbietet oder die in furnitureList steht, muss
    einen case-Zweig in spawnPlacement haben - sonst setzt man ein unsichtbares
    Objekt ab und sucht danach."""
    cases, offered, placed = set(), set(), set()
    for path, clean in files.items():
        base = os.path.basename(path)
        if base == 'Furniture.swift':
            m = re.search(r'switch\s+p\.kind\s*\{', clean)
            if m:
                close = matching_paren(clean, clean.index('{', m.end() - 1))
                body = clean[m.end():close]
                for cm in re.finditer(r'case\s+((?:"[^"]*"\s*,?\s*)+)', body):
                    cases |= set(re.findall(r'"([^"]*)"', cm.group(1)))
            placed |= set(re.findall(r'Placement\(kind:\s*"([^"]+)"', clean))
        if base == 'ContentView.swift':
            for fm in re.finditer(r'ForEach\(\[([^\]]*)\]', clean):
                block = clean[fm.end():fm.end() + 400]
                if 'addFurniture' in block:
                    offered |= set(re.findall(r'"([^"]+)"', fm.group(1)))

    # Die Namen im Editor stehen als Literale in der Textur-losen Liste; die
    # Strings wurden beim Aufbereiten geleert, deshalb aus dem Rohtext lesen.
    for kind in sorted(offered - cases):
        rep.error("Furniture.swift", f"Editor bietet '{kind}' an, "
                                     f"spawnPlacement hat keinen case dafuer")
    for kind in sorted(placed - cases):
        rep.error("Furniture.swift", f"furnitureList enthaelt '{kind}', "
                                     f"spawnPlacement hat keinen case dafuer")
    unreachable = sorted(cases - offered - placed)
    if unreachable:
        rep.note("Furniture.swift", "case ohne Verwendung: " + ", ".join(unreachable))
    rep.done("Editor-Arten", len(cases))


# ---------------------------------------------------------------- main

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'Sources'
    paths = sorted(os.path.join(root, f) for f in os.listdir(root)
                   if f.endswith('.swift'))
    if not paths:
        print(f"Keine .swift-Dateien in {root}")
        return 1

    raw = {p: open(p, encoding='utf-8').read() for p in paths}
    files = {p: strip_code(s) for p, s in raw.items()}

    rep = Report()
    check_brackets(files, rep)
    check_textures(files, rep)
    sigs = collect_signatures(files)
    check_duplicates(sigs, rep)
    check_labels(files, sigs, rep)
    check_float(files, sigs, rep)
    check_self_free(files, sigs, rep)
    check_zones(files, raw, sigs, rep)
    check_views(files, rep)
    # Arten aus dem ROHtext: die Kind-Namen sind Stringliterale
    check_kinds(raw, rep)

    print(f"{len(paths)} Dateien, {sum(s.count(chr(10)) + 1 for s in raw.values())} Zeilen\n")
    for name, cnt in rep.checks:
        print(f"  geprueft  {name:<28} {cnt}")
    print()
    if rep.notes:
        print(f"{len(rep.notes)} HINWEIS(E)")
        for where, msg in rep.notes:
            print(f"  {where:<26} {msg}")
        print()
    if rep.errors:
        print(f"{len(rep.errors)} FEHLER")
        for where, msg in rep.errors:
            print(f"  {where:<26} {msg}")
        return 1
    print("Keine Fehler.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
