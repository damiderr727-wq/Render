#!/usr/bin/env python3
"""
Vermessung des Treppenhauses x[-8,-2] z[6,14], drei Ebenen 0 / 1.8 / 3.8.

Kein Ratespiel: die Sperren (solids) und Laufflaechen (floorAreas) sind aus den
Aufrufen in Villa.swift Zeile 1695..1717 und 2224..2240 nachgebaut, und die
Begehbarkeit wird mit derselben Logik geprueft, die Game.swift benutzt
(hits() Zeile 923, groundHeight() Zeile 939).

Modelliert wird NUR der Treppenbereich - fuer die Frage "kommt man hoch?"
reicht das, weil alles andere ausserhalb liegt.
"""

RAD = 0.4          # Spielerradius, Game.swift:924
EYE = 1.7          # Koerperhoehe, Game.swift:925


class Box:
    def __init__(self, x0, x1, z0, z1, y0=-1.0, y1=100.0,
                 blocks_player=True, blocks_camera=True, tag=''):
        self.x0, self.x1, self.z0, self.z1 = x0, x1, z0, z1
        self.y0, self.y1 = y0, y1
        self.bp, self.bc = blocks_player, blocks_camera
        self.tag = tag


class Area:
    def __init__(self, x0, x1, z0, z1, y0, y1=None, tag=''):
        self.x0, self.x1, self.z0, self.z1 = x0, x1, z0, z1
        self.y0 = y0
        self.y1 = y0 if y1 is None else y1
        self.tag = tag

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


solids, areas = [], []


def wall_segments(a0, a1, gaps):
    """segments() aus Game.swift:205"""
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


def wallX(x0, x1, z, gaps=(), h=4.0, base=0.0, tag=''):
    for s0, s1 in wall_segments(x0, x1, list(gaps)):
        if s1 - s0 > 0.05:
            solids.append(Box(s0, s1, z - 0.19, z + 0.19, base, base + h,
                              tag=tag or f'wallX z={z}'))


def wallZ(z0, z1, x, gaps=(), h=4.0, base=0.0, tag=''):
    for s0, s1 in wall_segments(z0, z1, list(gaps)):
        if s1 - s0 > 0.05:
            solids.append(Box(x - 0.19, x + 0.19, s0, s1, base, base + h,
                              tag=tag or f'wallZ x={x}'))


def floor_tile(w, d, cx, cz, y=0.0, tag=''):
    areas.append(Area(cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2, y, tag=tag))


def stair_flight(x, z_start, z_end, w, y_start, y_end, tag=''):
    """stairFlight() aus Villa.swift:1433 - Rampe plus Kamerasperren."""
    fw = w
    up_north = z_end > z_start
    areas.append(Area(x - fw / 2, x + fw / 2, min(z_start, z_end), max(z_start, z_end),
                      y_start if up_north else y_end,
                      y_end if up_north else y_start, tag=tag))
    for k in range(5):
        t0, t1 = k / 5, (k + 1) / 5
        za, zb = z_start + (z_end - z_start) * t0, z_start + (z_end - z_start) * t1
        ya, yb = y_start + (y_end - y_start) * t0, y_start + (y_end - y_start) * t1
        solids.append(Box(x - fw / 2, x + fw / 2, min(za, zb), max(za, zb),
                          min(ya, yb) - 0.9, max(ya, yb),
                          blocks_player=False, tag=f'{tag} Kamerasperre'))
    # Trittstufen sind 6 cm breiter als der Lauf - fuer die Kollision ohne
    # Belang, aber entscheidend fuer die Frage, ob sie in einer Wand stecken.
    return (x - (fw + 0.06) / 2, x + (fw + 0.06) / 2)


# ------------------------------------------------------- Erdgeschoss
floor_tile(16, 14, 0, 7, 0.0, tag='Boden EG')

# Waende um und im Treppenhaus (Villa.swift:1576..1642)
wallZ(0, 14, -8.0, gaps=[(3.5, 2.4)], h=6, tag='Westwand x=-8')
wallX(-8, 8, 14.0, h=6, tag='Suedwand z=14')
wallZ(0, 14, -2.0, gaps=[(10.0, 1.8)], h=6, tag='Wand x=-2')
wallX(-8, -2, 6.0, gaps=[(-4.0, 4.0)], h=6, tag='Nordabschluss z=6')
wallZ(6, 14, -4.0, gaps=[(12.5, 1.6)], h=6, tag='Trennwand x=-4')

# ------------------------------------------------------- Treppe (Villa.swift:1695..1711)
A_tread = stair_flight(-6.8, 13.4, 10.4, 1.8, 0.0, 1.8, tag='Lauf A')

# Podest
areas.append(Area(-7.7, -4.1, 9.2, 10.4, 1.8, tag='Podest'))
solids.append(Box(-7.7, -4.1, 9.1, 9.3, 1.8, 3.0, tag='Bruestung Podestnordkante'))
solids.append(Box(-7.7, -4.1, 9.2, 10.4, 0.0, 1.8,
                  blocks_camera=False, tag='Fuellung unter Podest'))

B_tread = stair_flight(-5.0, 9.2, 6.2, 1.8, 1.8, 3.8, tag='Lauf B')

# ------------------------------------------------------- Obergeschoss (Villa.swift:2224..2240)
F = 3.8
floor_tile(6.0, 5.7, -5.0, 3.35, F, tag='OG noerdlich')
floor_tile(6.0, 4.4, -5.0, 11.8, F, tag='OG suedlich')
floor_tile(1.8, 3.4, -7.1, 7.9, F, tag='OG westlich')
floor_tile(2.0, 3.4, -3.0, 7.9, F, tag='OG oestlich')
solids.append(Box(-6.3, -6.1, 6.2, 9.6, F, F + 1.2, tag='Schachtgelaender West'))
solids.append(Box(-4.1, -3.9, 6.2, 9.6, F, F + 1.2, tag='Schachtgelaender Ost'))
solids.append(Box(-6.2, -4.0, 9.5, 9.7, F, F + 1.2, tag='Schachtgelaender Sued'))
solids.append(Box(-2.1, -1.9, 0.5, 12.0, F, F + 1.2, tag='Galeriebruestung'))


# ------------------------------------------------------- Logik aus Game.swift

def hits(x, z, y):
    """hits() Game.swift:923"""
    head = y + EYE
    for s in solids:
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


def ground_height(x, z, cur):
    """groundHeight() Game.swift:939 - Rampen haben Vorrang."""
    best, best_d = None, 1.1
    for a in areas:
        if a.ramp and a.contains(x, z):
            h = a.height(x, z)
            if abs(h - cur) < best_d:
                best_d, best = abs(h - cur), h
    if best is not None:
        return best
    best_d = 1.6
    for a in areas:
        if not a.ramp and a.contains(x, z):
            h = a.height(x, z)
            if abs(h - cur) < best_d:
                best_d, best = abs(h - cur), h
    return cur if best is None else best


# ------------------------------------------------------- Messungen

def steigung():
    print("STEIGUNGEN (11 Stufen je Lauf, stairFlight n=11)")
    for tag, z0, z1, y0, y1 in [('Lauf A', 13.4, 10.4, 0.0, 1.8),
                                ('Lauf B', 9.2, 6.2, 1.8, 3.8)]:
        n = 11
        rise = abs(y1 - y0) / n
        going = abs(z1 - z0) / n
        import math
        ang = math.degrees(math.atan2(abs(y1 - y0), abs(z1 - z0)))
        print(f"  {tag}: Steigung {rise*100:5.2f} cm   Auftritt {going*100:5.2f} cm"
              f"   2S+A = {(2*rise+going)*100:5.1f} cm   {ang:4.1f} Grad")
    print("  Schrittmassregel: 2S+A soll 59..65 cm sein, S soll GLEICH sein.")
    print()


def stufen_in_wand():
    print("STUFEN IN DER WAND (Trittbreite = Laufbreite + 6 cm, Villa.swift:1447)")
    for tag, (tx0, tx1), z0, z1, y0, y1 in [('Lauf A', A_tread, 10.4, 13.4, 0.0, 1.8),
                                            ('Lauf B', B_tread, 6.2, 9.2, 1.8, 3.8)]:
        print(f"  {tag}: Tritte x {tx0:+.2f} .. {tx1:+.2f}")
        for s in solids:
            if not s.bc or s.tag.endswith('Kamerasperre'):
                continue
            ox = min(tx1, s.x1) - max(tx0, s.x0)
            oz = min(z1, s.z1) - max(z0, s.z0)
            oy = min(y1, s.y1) - max(y0, s.y0)
            if ox > 0.001 and oz > 0.001 and oy > 0.001:
                print(f"        steckt {ox*100:5.1f} cm in '{s.tag}' "
                      f"(x {s.x0:+.2f}..{s.x1:+.2f}) ueber {oz:.2f} m Lauflaenge")
        # Handlauf sitzt bei x +- (w/2 + 0.10), Villa.swift:1478
        mid = (tx0 + tx1) / 2
        for sgn in (-1, 1):
            hx = mid + sgn * (0.9 + 0.10)
            for s in solids:
                if not s.bc or s.tag.endswith('Kamerasperre'):
                    continue
                if s.x0 - 0.05 <= hx <= s.x1 + 0.05 and \
                        min(z1, s.z1) - max(z0, s.z0) > 0.001:
                    print(f"        Handlauf bei x {hx:+.2f} liegt in '{s.tag}'")
    print()


def kopffreiheit():
    print("KOPFFREIHEIT (Deckenplatten und Podeste ueber dem Laufweg)")
    decken = [(a, a.y0) for a in areas if not a.ramp and a.y0 > 0.01]
    for tag, x, z0, z1, y0, y1 in [('Lauf A', -6.8, 13.4, 10.4, 0.0, 1.8),
                                   ('Podest', -5.9, 10.4, 9.2, 1.8, 1.8),
                                   ('Lauf B', -5.0, 9.2, 6.2, 1.8, 3.8)]:
        worst, wz, wd = 99.0, None, ''
        for i in range(41):
            t = i / 40
            z = z0 + (z1 - z0) * t
            y = y0 + (y1 - y0) * t
            for a, ay in decken:
                if a.contains(x, z) and ay > y + 0.3:
                    if ay - y < worst:
                        worst, wz, wd = ay - y, z, a.tag
        if wz is None:
            print(f"  {tag}: nach oben offen bis zur Decke y=6.0")
        else:
            mark = 'OK' if worst >= 2.0 else 'ZU NIEDRIG'
            print(f"  {tag}: engste Stelle {worst:.2f} m bei z={wz:+.2f} "
                  f"unter '{wd}'   [{mark}]")
    print()


def sturz_pruefen():
    """Eine Wandoeffnung ist nur bis doorH = 2.35 m frei; darueber sitzt ein
    Sturz (opening(), Game.swift:223). Steht eine begehbare Flaeche hoeher als
    das, laeuft der Spieler durch massiv aussehende Geometrie.
    """
    print("WANDOEFFNUNGEN GEGEN LAUFHOEHE (Sturz ab doorH = 2.35 m)")
    DOOR_H = 2.35
    oeffnungen = [
        # (Beschreibung, Achse, Luecke von..bis, Querkoordinate, Wandhoehe, Basis)
        ('Nordabschluss z=6, Luecke x -6.0..-2.0', 'x', -6.0, -2.0, 6.0, 6.0, 0.0),
        ('Trennwand x=-4, Luecke z 11.7..13.3', 'z', 11.7, 13.3, -4.0, 6.0, 0.0),
    ]
    for name, axis, a0, a1, fixed, h, base in oeffnungen:
        frei_bis = base + DOOR_H
        treffer = []
        for a in areas:
            if a.ramp:
                continue
            if axis == 'x':
                if not (a.x0 < a1 and a.x1 > a0):
                    continue
                if not (a.z0 - 0.2 <= fixed <= a.z1 + 0.2):
                    continue
            else:
                if not (a.z0 < a1 and a.z1 > a0):
                    continue
                if not (a.x0 - 0.2 <= fixed <= a.x1 + 0.2):
                    continue
            if a.y0 > frei_bis - 0.05:
                treffer.append(a)
        if treffer:
            for a in treffer:
                print(f"  {name}")
                print(f"     Laufflaeche '{a.tag}' liegt auf y={a.y0:.2f} - "
                      f"Oeffnung ist nur bis y={frei_bis:.2f} frei, "
                      f"darueber {base+h-frei_bis:.2f} m Sturz")
        else:
            print(f"  {name}: keine Laufflaeche oberhalb des Sturzes")
    print()


def begehbar(x=-6.8, z=13.2, y_start=0.0,
             titel="Spieler laeuft von Lauf A nach oben"):
    """Der Spieler startet am angegebenen Punkt und laeuft nach Norden hoch."""
    print(f"BEGEHBARKEIT - {titel}")
    y = ground_height(x, z, y_start)
    step = 0.05
    print(f"  Start  x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
    for i in range(400):
        nz = z - step
        blocker = hits(x, nz, y)
        if blocker:
            print(f"  BLOCKIERT bei x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
            print(f"     durch '{blocker.tag}'  "
                  f"x {blocker.x0:+.2f}..{blocker.x1:+.2f}  "
                  f"z {blocker.z0:+.2f}..{blocker.z1:+.2f}  "
                  f"y {blocker.y0:.2f}..{blocker.y1:.2f}")
            # Kann man seitlich daran vorbei?
            frei = [sx for sx in [round(-7.6 + 0.1 * k, 2) for k in range(36)]
                    if not hits(sx, nz, y)]
            if frei:
                print(f"     seitlich frei bei x = {frei[0]:+.2f} .. {frei[-1]:+.2f}")
            else:
                print("     auf der ganzen Breite x -7.6 .. -4.1 kein Durchlass")
            return False
        z = nz
        gy = ground_height(x, z, y)
        y = gy
        # Am Podest muss der Spieler seitlich auf Lauf B wechseln
        if 9.2 <= z <= 10.4 and x < -5.9:
            while x < -5.0 and not hits(x + step, z, y):
                x += step
        if z <= 6.2:
            print(f"  OBEN ANGEKOMMEN  x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
            return True
    print("  Laufweg endete ohne Ergebnis")
    return False


if __name__ == '__main__':
    print(f"{len(solids)} Sperren, {len(areas)} Laufflaechen im Modell\n")
    steigung()
    stufen_in_wand()
    kopffreiheit()
    sturz_pruefen()
    ok = begehbar()
    print()
    # Zweiter Lauf: die erste Sperre uebersprungen, direkt auf dem Podest
    # starten. Sonst weiss man nicht, ob dahinter noch eine zweite steckt.
    ok2 = begehbar(-5.0, 10.2, 1.8,
                   "Spieler steht schon auf dem Podest, will auf Lauf B")
    print()
    print("ERGEBNIS: Obergeschoss ueber die Treppe erreichbar."
          if ok and ok2 else
          "ERGEBNIS: Obergeschoss ueber die Treppe NICHT erreichbar.")
