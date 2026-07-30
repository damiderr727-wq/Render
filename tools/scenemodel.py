#!/usr/bin/env python3
"""
Geometriemodell des Sanatoriums, so weit es fuer Treppenfragen noetig ist.

Die Kollisions- und Bodenlogik ist 1:1 aus Game.swift uebernommen:
  hits()          Zeile 923
  groundHeight()  Zeile 939
  segments()      Zeile 205
Die Bauhelfer entsprechen wall()/wallX()/wallZ()/floorTile() aus Game.swift und
stairFlight() aus Villa.swift.

Zwei Werkzeuge benutzen dieses Modul: treppe_messen.py prueft den Ist-Zustand,
treppe_entwurf.py rechnet den Neubau durch. Beide MUESSEN dieselbe Physik
benutzen, sonst vergleicht man Aepfel mit Birnen.
"""

import math

RAD = 0.4          # Spielerradius,  Game.swift:924
EYE = 1.7          # Koerperhoehe,   Game.swift:925
DOOR_H = 2.35      # doorH,          Game.swift:220
WALL_T = 0.19      # halbe Wanddicke, Game.swift:198
MIN_HEAD = 2.00    # Kopffreiheit, Forderung aus der Uebergabe


class Box:
    """Entspricht WallBox aus Game.swift:9."""

    def __init__(self, x0, x1, z0, z1, y0=-1.0, y1=100.0,
                 blocks_player=True, blocks_camera=True, tag='', owner=''):
        self.x0, self.x1 = min(x0, x1), max(x0, x1)
        self.z0, self.z1 = min(z0, z1), max(z0, z1)
        self.y0, self.y1 = y0, y1
        self.bp, self.bc = blocks_player, blocks_camera
        self.tag = tag
        # owner = Lauf, zu dem die Sperre GEHOERT (Wange, Bruestung, Fuellung).
        # Eigene Bauteile duerfen den Lauf beruehren, fremde nicht.
        self.owner = owner


class Area:
    """Entspricht FloorArea aus Game.swift:26. y0 != y1 heisst Rampe."""

    def __init__(self, x0, x1, z0, z1, y0, y1=None, tag='', ceiling=False):
        self.x0, self.x1 = min(x0, x1), max(x0, x1)
        self.z0, self.z1 = min(z0, z1), max(z0, z1)
        self.y0 = y0
        self.y1 = y0 if y1 is None else y1
        self.tag = tag
        self.ceiling = ceiling      # Decken sind nicht begehbar, nur Hindernis

    @property
    def ramp(self):
        return self.y0 != self.y1

    def height(self, x, z):
        if self.y0 == self.y1:
            return self.y0
        t = (z - self.z0) / (self.z1 - self.z0)
        return self.y0 + (self.y1 - self.y0) * min(1.0, max(0.0, t))

    def contains(self, x, z):
        return self.x0 <= x <= self.x1 and self.z0 <= z <= self.z1


class Scene:
    def __init__(self, name):
        self.name = name
        self.solids = []
        self.areas = []
        self.flights = []      # dicts: tag,x,w,z0,z1,y0,y1,n,rise,going

    # ---------------- Bauhelfer ----------------

    @staticmethod
    def segments(a0, a1, gaps):
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

    def wall_x(self, x0, x1, z, gaps=(), h=4.0, base=0.0, tag='', lintel=True):
        """lintel=False bedeutet volle Durchgangshoehe - fuer Treppenschaechte."""
        for s0, s1 in self.segments(x0, x1, list(gaps)):
            if s1 - s0 > 0.05:
                self.solids.append(Box(s0, s1, z - WALL_T, z + WALL_T,
                                       base, base + h, tag=tag))
        if lintel:
            for c, w in gaps:
                if base + h - (base + DOOR_H) > 0.05:
                    self.areas.append(Area(c - w / 2, c + w / 2, z - WALL_T, z + WALL_T,
                                           base + DOOR_H,
                                           tag=f'{tag} Sturzunterkante', ceiling=True))

    def wall_z(self, z0, z1, x, gaps=(), h=4.0, base=0.0, tag='', lintel=True):
        for s0, s1 in self.segments(z0, z1, list(gaps)):
            if s1 - s0 > 0.05:
                self.solids.append(Box(x - WALL_T, x + WALL_T, s0, s1,
                                       base, base + h, tag=tag))
        if lintel:
            for c, w in gaps:
                if base + h - (base + DOOR_H) > 0.05:
                    self.areas.append(Area(x - WALL_T, x + WALL_T, c - w / 2, c + w / 2,
                                           base + DOOR_H,
                                           tag=f'{tag} Sturzunterkante', ceiling=True))

    def floor(self, x0, x1, z0, z1, y, tag=''):
        self.areas.append(Area(x0, x1, z0, z1, y, tag=tag))

    def floor_tile(self, w, d, cx, cz, y=0.0, tag=''):
        """floorTile() aus Game.swift:277 - Mitte plus Masse."""
        self.floor(cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2, y, tag)

    def ceil(self, x0, x1, z0, z1, y, tag=''):
        self.areas.append(Area(x0, x1, z0, z1, y, tag=tag, ceiling=True))

    def old_stair_flight(self, x, z_start, z_end, w, y_start, y_end, tag=''):
        """stairFlight() aus Villa.swift:1433 - immer 11 Stufen, Rampe plus
        Kamerasperren, Handlauf beidseitig bei x +- (w/2 + 0.10)."""
        up_north = z_end > z_start
        self.areas.append(Area(x - w / 2, x + w / 2,
                               min(z_start, z_end), max(z_start, z_end),
                               y_start if up_north else y_end,
                               y_end if up_north else y_start, tag=tag))
        for k in range(5):
            t0, t1 = k / 5, (k + 1) / 5
            za = z_start + (z_end - z_start) * t0
            zb = z_start + (z_end - z_start) * t1
            ya = y_start + (y_end - y_start) * t0
            yb = y_start + (y_end - y_start) * t1
            self.solids.append(Box(x - w / 2, x + w / 2, za, zb,
                                   min(ya, yb) - 0.9, max(ya, yb),
                                   blocks_player=False, tag=f'{tag} Kamerasperre'))
        n = 11
        self.flights.append(dict(tag=tag, x=x, w=w, z0=z_start, z1=z_end,
                                 y0=y_start, y1=y_end, n=n,
                                 rise=abs(y_end - y_start) / n,
                                 going=abs(z_end - z_start) / n,
                                 rails=(True, True), rail_off=w / 2 + 0.10))

    def stair_run(self, x, z_start, z_end, w, y_start, y_end, n,
                  rails=(True, True), rail_off=None, tag='',
                  cam_blocks_player=False, wange_lo=-0.10, wange_hi=1.10):
        """Neuer Lauf: Stufenzahl wird uebergeben, Handlaeufe seitenweise.

        cam_blocks_player / wange_lo / wange_hi kommen beim Vermessen aus dem
        Swift-Quelltext, damit das Modell nicht seine eigene Nachbildung prueft.
        """
        if rail_off is None:
            rail_off = w / 2 + 0.09
        up_north = z_end > z_start
        self.areas.append(Area(x - w / 2, x + w / 2,
                               min(z_start, z_end), max(z_start, z_end),
                               y_start if up_north else y_end,
                               y_end if up_north else y_start, tag=tag))
        # Kamerasperre: haelt die Kamera ueber den Stufen, laesst den Spieler
        # durch. blocks_player MUSS false bleiben - genau das war der alte Fehler.
        for k in range(6):
            t0, t1 = k / 6, (k + 1) / 6
            za = z_start + (z_end - z_start) * t0
            zb = z_start + (z_end - z_start) * t1
            ya = y_start + (y_end - y_start) * t0
            yb = y_start + (y_end - y_start) * t1
            self.solids.append(Box(x - w / 2, x + w / 2, za, zb,
                                   min(ya, yb) - 0.85, max(ya, yb),
                                   blocks_player=cam_blocks_player,
                                   tag=f'{tag} Kamerasperre', owner=tag))
            # Wangen links und rechts: sie halten den Spieler AUF dem Lauf.
            # Ohne sie laeuft er seitlich in das Treppenauge und faellt durch,
            # weil dort keine Laufflaeche liegt. Der Hoehenbereich haengt an der
            # Rampe, damit die Wange unten niemanden stoert.
            for sgn, has in zip((-1, 1), rails):
                if not has:
                    continue
                c = x + sgn * rail_off
                self.solids.append(Box(c - 0.07, c + 0.07, za, zb,
                                       min(ya, yb) + wange_lo,
                                       max(ya, yb) + wange_hi,
                                       blocks_camera=False,
                                       tag=f"{tag} Wange {'W' if sgn < 0 else 'O'}",
                                       owner=tag))
        self.flights.append(dict(tag=tag, x=x, w=w, z0=z_start, z1=z_end,
                                 y0=y_start, y1=y_end, n=n,
                                 rise=abs(y_end - y_start) / n,
                                 going=abs(z_end - z_start) / n,
                                 rails=rails, rail_off=rail_off))

    # ---------------- Logik aus Game.swift ----------------

    def hits(self, x, z, y):
        head = y + EYE
        for s in self.solids:
            if not s.bp:
                continue
            if s.y1 < y + 0.15 or s.y0 > head:
                continue
            cx = max(s.x0, min(x, s.x1))
            cz = max(s.z0, min(z, s.z1))
            dx, dz = x - cx, z - cz
            if dx * dx + dz * dz < RAD * RAD:
                return s
        return None

    def ground_height(self, x, z, cur):
        walk = [a for a in self.areas if not a.ceiling]
        best, best_d = None, 1.1
        for a in walk:
            if a.ramp and a.contains(x, z):
                h = a.height(x, z)
                if abs(h - cur) < best_d:
                    best_d, best = abs(h - cur), h
        if best is not None:
            return best
        best_d = 1.6
        for a in walk:
            if not a.ramp and a.contains(x, z):
                h = a.height(x, z)
                if abs(h - cur) < best_d:
                    best_d, best = abs(h - cur), h
        return cur if best is None else best


# ==================================================================== Pruefungen

def pruef_steigungen(sc):
    print("  STEIGUNGEN")
    ok = True
    for f in sc.flights:
        r, g = f['rise'], f['going']
        ang = math.degrees(math.atan2(abs(f['y1'] - f['y0']), abs(f['z1'] - f['z0'])))
        rule = 2 * r + g
        mark = 'ok' if 0.59 <= rule <= 0.65 else 'AUSSERHALB 59..65'
        print(f"    {f['tag']:<18} {f['n']:>2} Stufen  Steigung {r*100:5.2f} cm  "
              f"Auftritt {g*100:5.2f} cm  2S+A {rule*100:5.1f} cm  "
              f"{ang:4.1f} Grad  [{mark}]")
        if not (0.59 <= rule <= 0.65):
            ok = False
    # Gleiche Steigung je Geschoss: Laeufe mit gemeinsamer Hoehenspanne
    gruppen = {}
    for f in sc.flights:
        key = round(min(f['y0'], f['y1']) / 2.0)
        gruppen.setdefault(key, []).append(f)
    for key, gruppe in sorted(gruppen.items()):
        rr = [f['rise'] for f in gruppe]
        if len(rr) > 1 and max(rr) - min(rr) > 0.002:
            print(f"    FEHLER Steigungen innerhalb eines Geschosses weichen um "
                  f"{(max(rr)-min(rr))*100:.2f} cm ab: "
                  f"{', '.join(f['tag'] for f in gruppe)}")
            ok = False
    print()
    return ok


def pruef_freiraum(sc, tol=0.02):
    """Zwei getrennte Fragen, die frueher vermischt waren:

    (a) Steckt Treppengeometrie in fremder Geometrie? Dazu wird die Rampenhoehe
        AN DER STELLE gebraucht - ein Huellkoerpervergleich meldet sonst jede
        Fuellung unter der Treppe als Treffer, obwohl sie 30 cm darunter liegt.
    (b) Sperrt eine fremde Sperre den Laufweg? Das beantwortet hits() selbst.
    """
    print("  GEOMETRIE IN FREMDEN SPERREN")
    ok = True
    for f in sc.flights:
        tx0 = f['x'] - (f['w'] + 0.06) / 2
        tx1 = f['x'] + (f['w'] + 0.06) / 2
        teile = [('Tritte', tx0, tx1)]
        for sgn, has in zip((-1, 1), f['rails']):
            if has:
                c = f['x'] + sgn * f['rail_off']
                teile.append((f"Handlauf {'W' if sgn < 0 else 'O'}",
                              c - 0.0425, c + 0.0425))
        n = 60
        treffer = {}
        for i in range(n + 1):
            t = i / n
            z = f['z0'] + (f['z1'] - f['z0']) * t
            y = f['y0'] + (f['y1'] - f['y0']) * t
            for name, a0, a1 in teile:
                for s in sc.solids:
                    if s.owner == f['tag'] or s.tag.endswith('Kamerasperre'):
                        continue
                    if not (s.z0 - 1e-9 <= z <= s.z1 + 1e-9):
                        continue
                    ox = min(a1, s.x1) - max(a0, s.x0)
                    if ox <= tol:
                        continue
                    # Der Trittkoerper reicht von der Rampe 10 cm nach unten,
                    # der Handlauf steht 1.0 m darueber.
                    lo = y - 0.10 if name == 'Tritte' else y + 0.90
                    hi = y + 0.02 if name == 'Tritte' else y + 1.05
                    if min(hi, s.y1) - max(lo, s.y0) > tol:
                        key = (f['tag'], name, s.tag)
                        treffer[key] = max(treffer.get(key, 0), ox)
        for (ft, name, st), ox in sorted(treffer.items()):
            print(f"    FEHLER {ft} {name}: bis {ox*100:.1f} cm in '{st}'")
            ok = False
    if ok:
        print("    keine Treppengeometrie steckt in fremder Geometrie")

    print("  LAUFWEG FREI? (hits() entlang der Laufachse)")
    for f in sc.flights:
        blocked = None
        n = 60
        for i in range(n + 1):
            t = i / n
            z = f['z0'] + (f['z1'] - f['z0']) * t
            y = f['y0'] + (f['y1'] - f['y0']) * t
            s = sc.hits(f['x'], z, y)
            if s is not None and s.owner != f['tag']:
                blocked = (z, y, s)
                break
        if blocked:
            z, y, s = blocked
            print(f"    FEHLER {f['tag']} bei z {z:+.2f} y {y:.2f} "
                  f"durch '{s.tag}'")
            ok = False
        else:
            print(f"    {f['tag']:<10} frei")
    print()
    return ok


def pruef_kopffreiheit(sc, schritt=0.10):
    """Fuer jede begehbare Flaeche: was haengt darueber und wie hoch.

    Punkte, an denen der Spieler ohnehin nicht stehen kann - weil eine Sperre
    dort greift oder eine hoehere Flaeche naeher liegt - zaehlen nicht. Sonst
    meldet der Raum unter einer Treppe immer zu wenig Kopffreiheit, obwohl er
    zugemauert ist.
    """
    print(f"  KOPFFREIHEIT (Soll >= {MIN_HEAD:.2f} m, nur erreichbare Punkte)")
    walk = [a for a in sc.areas if not a.ceiling]
    ok = True
    for a in walk:
        worst, wp, wt = 99.0, None, ''
        nx = max(2, int((a.x1 - a.x0) / schritt) + 1)
        nz = max(2, int((a.z1 - a.z0) / schritt) + 1)
        for i in range(nx):
            x = a.x0 + (a.x1 - a.x0) * i / (nx - 1)
            for j in range(nz):
                z = a.z0 + (a.z1 - a.z0) * j / (nz - 1)
                y = a.height(x, z)
                if sc.hits(x, z, y) is not None:
                    continue                      # dort steht niemand
                if abs(sc.ground_height(x, z, y) - y) > 0.01:
                    continue                      # eine andere Flaeche gewinnt
                for b in sc.areas:
                    if b is a or not b.contains(x, z):
                        continue
                    by = b.height(x, z)
                    if by - y > 0.25 and by - y < worst:
                        worst, wp, wt = by - y, (x, z), b.tag
        if wp is None:
            print(f"    {a.tag:<26} nach oben offen")
        else:
            mark = 'ok' if worst >= MIN_HEAD - 1e-6 else 'ZU NIEDRIG'
            if worst < MIN_HEAD - 1e-6:
                ok = False
            print(f"    {a.tag:<26} {worst:.2f} m bei x {wp[0]:+.2f} z {wp[1]:+.2f} "
                  f"unter '{wt}'   [{mark}]")
    print()
    return ok


def begehbar(sc, weg, titel):
    """weg = Liste von (x, z) Wegpunkten. Laeuft sie in 5-cm-Schritten ab."""
    print(f"  BEGEHBARKEIT - {titel}")
    x, z = weg[0]
    y = sc.ground_height(x, z, weg[0][1] and 0.0 or 0.0)
    y = sc.ground_height(x, z, y)
    print(f"    Start   x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
    for tx, tz in weg[1:]:
        for _ in range(4000):
            dx, dz = tx - x, tz - z
            d = math.hypot(dx, dz)
            if d < 0.05:
                break
            nx = x + dx / d * 0.05
            nz = z + dz / d * 0.05
            # Achsenweise wie im Render-Loop (Game.swift:1015)
            moved = False
            if not sc.hits(nx, z, y):
                x, moved = nx, True
            if not sc.hits(x, nz, y):
                z, moved = nz, True
            if not moved:
                b = sc.hits(nx, nz, y)
                print(f"    BLOCKIERT bei x {x:+.2f} z {z:+.2f} y {y:.2f} "
                      f"auf dem Weg nach x {tx:+.2f} z {tz:+.2f}")
                if b:
                    print(f"       durch '{b.tag}'  x {b.x0:+.2f}..{b.x1:+.2f}  "
                          f"z {b.z0:+.2f}..{b.z1:+.2f}  y {b.y0:.2f}..{b.y1:.2f}")
                return False
            y = sc.ground_height(x, z, y)
        else:
            print(f"    kommt bei x {tx:+.2f} z {tz:+.2f} nicht an")
            return False
        print(f"    erreicht x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
    return True
