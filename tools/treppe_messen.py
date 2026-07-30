#!/usr/bin/env python3
"""
Vermessung der beiden Treppenhaeuser.

  Treppe 1  EG -> OG      x[-8,-2] z[6,14]    y 0 -> 1.8 -> 3.8
  Treppe 2  OG -> Badehaus x[-8,-4] z[8,13]   y 3.8 -> 5.2 -> 6.6

Kein Ratespiel: Sperren (solids) und Laufflaechen (floorAreas) sind aus den
Aufrufparametern in Villa.swift nachgebaut, die Begehbarkeit wird mit derselben
Logik geprueft, die Game.swift benutzt - hits() Zeile 923, groundHeight()
Zeile 939, segments() Zeile 205, stairFlight() Villa.swift Zeile 1433.

Modelliert wird nur der jeweilige Treppenbereich. Fuer die Frage "kommt man
hoch?" reicht das, weil alles andere ausserhalb der Reichweite liegt.
"""

import math

RAD = 0.4          # Spielerradius, Game.swift:924
EYE = 1.7          # Koerperhoehe, Game.swift:925
DOOR_H = 2.35      # doorH, Game.swift:220 - darueber sitzt der Sturz


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


class Scene:
    def __init__(self, name):
        self.name = name
        self.solids = []
        self.areas = []
        self.flights = []      # (tag, x, z0, z1, y0, y1, w)
        self.openings = []     # (name, achse, a0, a1, fixed, h, base)

    # ---- Bausteine, 1:1 wie in Game.swift / Villa.swift ----

    def segments(self, a0, a1, gaps):
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

    def wallX(self, x0, x1, z, gaps=(), h=4.0, base=0.0, tag=''):
        for s0, s1 in self.segments(x0, x1, list(gaps)):
            if s1 - s0 > 0.05:
                self.solids.append(Box(s0, s1, z - 0.19, z + 0.19,
                                       base, base + h, tag=tag))
        for c, w in gaps:
            self.openings.append((f'{tag}, Luecke x {c-w/2:+.1f}..{c+w/2:+.1f}',
                                  'x', c - w / 2, c + w / 2, z, h, base))

    def wallZ(self, z0, z1, x, gaps=(), h=4.0, base=0.0, tag=''):
        for s0, s1 in self.segments(z0, z1, list(gaps)):
            if s1 - s0 > 0.05:
                self.solids.append(Box(x - 0.19, x + 0.19, s0, s1,
                                       base, base + h, tag=tag))
        for c, w in gaps:
            self.openings.append((f'{tag}, Luecke z {c-w/2:+.1f}..{c+w/2:+.1f}',
                                  'z', c - w / 2, c + w / 2, x, h, base))

    def floor_tile(self, w, d, cx, cz, y=0.0, tag=''):
        self.areas.append(Area(cx - w / 2, cx + w / 2,
                               cz - d / 2, cz + d / 2, y, tag=tag))

    def stair_flight(self, x, z_start, z_end, w, y_start, y_end, tag=''):
        """stairFlight(), Villa.swift:1433"""
        up_north = z_end > z_start
        self.areas.append(Area(x - w / 2, x + w / 2,
                               min(z_start, z_end), max(z_start, z_end),
                               y_start if up_north else y_end,
                               y_end if up_north else y_start, tag=tag))
        for k in range(5):
            t0, t1 = k / 5, (k + 1) / 5
            za, zb = z_start + (z_end - z_start) * t0, z_start + (z_end - z_start) * t1
            ya, yb = y_start + (y_end - y_start) * t0, y_start + (y_end - y_start) * t1
            self.solids.append(Box(x - w / 2, x + w / 2, min(za, zb), max(za, zb),
                                   min(ya, yb) - 0.9, max(ya, yb),
                                   blocks_player=False, tag=f'{tag} Kamerasperre'))
        self.flights.append((tag, x, z_start, z_end, y_start, y_end, w))

    def switchback(self, xA, xB, z_low, z_high, w, y_bot, y_top, tag=''):
        """switchbackStairs(), Villa.swift:1493"""
        y_mid = (y_bot + y_top) / 2
        self.stair_flight(xA, z_low, z_high, w, y_bot, y_mid, tag=f'{tag} Lauf 1')
        self.stair_flight(xB, z_high, z_low, w, y_mid, y_top, tag=f'{tag} Lauf 2')
        px0 = min(xA, xB) - w / 2 - 0.1
        px1 = max(xA, xB) + w / 2 + 0.1
        pz0, pz1 = min(z_low, z_high) - 1.5, min(z_low, z_high)
        self.areas.append(Area(px0, px1, pz0, pz1, y_mid, tag=f'{tag} Podest'))
        self.solids.append(Box(px0, px1, pz0 - 0.1, pz0 + 0.1,
                               y_mid, y_mid + 1.2, tag=f'{tag} Podestbruestung'))
        # Fuellung zwischen den Laeufen - bei gleichem Laufabstand entartet sie
        self.areas.append(Area(min(xA, xB) + w / 2, max(xA, xB) - w / 2,
                               min(z_low, z_high), max(z_low, z_high), y_bot,
                               tag=f'{tag} Auge zwischen den Laeufen'))

    # ---- Logik aus Game.swift ----

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
        best, best_d = None, 1.1
        for a in self.areas:
            if a.ramp and a.contains(x, z):
                h = a.height(x, z)
                if abs(h - cur) < best_d:
                    best_d, best = abs(h - cur), h
        if best is not None:
            return best
        best_d = 1.6
        for a in self.areas:
            if not a.ramp and a.contains(x, z):
                h = a.height(x, z)
                if abs(h - cur) < best_d:
                    best_d, best = abs(h - cur), h
        return cur if best is None else best


# ================================================================ Messungen

def steigung(sc):
    print("  STEIGUNGEN (stairFlight baut immer n = 11 Stufen)")
    werte = []
    for tag, x, z0, z1, y0, y1, w in sc.flights:
        rise, going = abs(y1 - y0) / 11, abs(z1 - z0) / 11
        ang = math.degrees(math.atan2(abs(y1 - y0), abs(z1 - z0)))
        werte.append(rise)
        print(f"    {tag:<16} Steigung {rise*100:5.2f} cm   Auftritt {going*100:5.2f} cm"
              f"   2S+A {(2*rise+going)*100:5.1f} cm   {ang:4.1f} Grad")
    if werte and max(werte) - min(werte) > 0.005:
        print(f"    ACHTUNG Steigungen weichen um {(max(werte)-min(werte))*100:.2f} cm "
              f"voneinander ab - in einem Treppenhaus muessen sie gleich sein")
    print()


def in_der_wand(sc):
    print("  GEOMETRIE IN WAENDEN (Tritte sind 6 cm breiter als der Lauf)")
    fund = False
    for tag, x, z0, z1, y0, y1, w in sc.flights:
        tx0, tx1 = x - (w + 0.06) / 2, x + (w + 0.06) / 2
        for s in sc.solids:
            if s.tag.endswith('Kamerasperre'):
                continue
            ox = min(tx1, s.x1) - max(tx0, s.x0)
            oz = min(max(z0, z1), s.z1) - max(min(z0, z1), s.z0)
            oy = min(max(y0, y1), s.y1) - max(min(y0, y1), s.y0)
            if ox > 0.005 and oz > 0.005 and oy > 0.005:
                print(f"    {tag}: Tritte stecken {ox*100:.0f} cm in "
                      f"'{s.tag}' ueber {oz:.2f} m Lauflaenge")
                fund = True
        for sgn in (-1, 1):
            hx = x + sgn * (w / 2 + 0.10)          # Handlauf, Villa.swift:1478
            for s in sc.solids:
                if s.tag.endswith('Kamerasperre'):
                    continue
                if s.x0 - 0.043 <= hx <= s.x1 + 0.043 and \
                        min(max(z0, z1), s.z1) - max(min(z0, z1), s.z0) > 0.005 and \
                        min(max(y0, y1), s.y1) - max(min(y0, y1), s.y0) > 0.005:
                    print(f"    {tag}: Handlauf bei x {hx:+.2f} liegt in '{s.tag}'")
                    fund = True
    if not fund:
        print("    nichts")
    print()


def kopffreiheit(sc):
    print("  KOPFFREIHEIT (Deckenplatten ueber dem Laufweg, Soll >= 2.00 m)")
    decken = [a for a in sc.areas if not a.ramp]
    for tag, x, z0, z1, y0, y1, w in sc.flights:
        worst, wz, wd = 99.0, None, ''
        for i in range(41):
            t = i / 40
            z, y = z0 + (z1 - z0) * t, y0 + (y1 - y0) * t
            for a in decken:
                if a.contains(x, z) and a.y0 > y + 0.3 and a.y0 - y < worst:
                    worst, wz, wd = a.y0 - y, z, a.tag
        if wz is None:
            print(f"    {tag:<16} nach oben offen")
        else:
            mark = 'OK' if worst >= 2.005 else 'ZU NIEDRIG'
            print(f"    {tag:<16} engste Stelle {worst:.2f} m bei z {wz:+.2f} "
                  f"unter '{wd}'   [{mark}]")
    print()


def stuerze(sc):
    print("  WANDOEFFNUNGEN GEGEN LAUFHOEHE (frei nur bis doorH = 2.35 m)")
    fund = False
    for name, axis, a0, a1, fixed, h, base in sc.openings:
        frei_bis = base + DOOR_H
        for a in sc.areas:
            if a.ramp or a.y0 <= frei_bis - 0.05:
                continue
            if axis == 'x':
                treffer = a.x0 < a1 and a.x1 > a0 and a.z0 - 0.2 <= fixed <= a.z1 + 0.2
            else:
                treffer = a.z0 < a1 and a.z1 > a0 and a.x0 - 0.2 <= fixed <= a.x1 + 0.2
            if treffer:
                print(f"    '{name}'")
                print(f"       Laufflaeche '{a.tag}' liegt auf y {a.y0:.2f} - "
                      f"Oeffnung endet bei y {frei_bis:.2f}, darueber "
                      f"{base+h-frei_bis:.2f} m Sturz zum Durchlaufen")
                fund = True
    if not fund:
        print("    keine Laufflaeche oberhalb eines Sturzes")
    print()


def begehbar(sc, x, z, y_start, richtung, titel):
    print(f"  BEGEHBARKEIT - {titel}")
    y = sc.ground_height(x, z, y_start)
    step = 0.05
    print(f"    Start   x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
    ziel_y = max(max(f[4], f[5]) for f in sc.flights)
    for _ in range(600):
        nz = z + richtung * step
        blocker = sc.hits(x, nz, y)
        if blocker:
            print(f"    BLOCKIERT bei x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
            print(f"       durch '{blocker.tag}'   "
                  f"x {blocker.x0:+.2f}..{blocker.x1:+.2f}  "
                  f"z {blocker.z0:+.2f}..{blocker.z1:+.2f}  "
                  f"y {blocker.y0:.2f}..{blocker.y1:.2f}")
            frei = [round(-7.7 + 0.05 * k, 2) for k in range(75)
                    if not sc.hits(round(-7.7 + 0.05 * k, 2), nz, y)]
            if frei:
                print(f"       seitlich frei bei x {frei[0]:+.2f}..{frei[-1]:+.2f}")
            else:
                print("       auf der ganzen Laufbreite kein Durchlass")
            return False
        z = nz
        y = sc.ground_height(x, z, y)
        if y >= ziel_y - 0.02:
            print(f"    OBEN ANGEKOMMEN  x {x:+.2f}  z {z:+.2f}  y {y:.2f}")
            return True
    print(f"    Laufweg endete bei x {x:+.2f}  z {z:+.2f}  y {y:.2f} "
          f"(Ziel y {ziel_y:.2f})")
    return False


# ================================================================ Szenen

def treppe1():
    sc = Scene("Treppe 1  Erdgeschoss -> Obergeschoss   (Villa.swift:1695..1717)")
    sc.floor_tile(16, 14, 0, 7, 0.0, tag='Boden EG')
    sc.wallZ(0, 14, -8.0, gaps=[(3.5, 2.4)], h=6, tag='Westwand x=-8')
    sc.wallX(-8, 8, 14.0, h=6, tag='Suedwand z=14')
    sc.wallZ(0, 14, -2.0, gaps=[(10.0, 1.8)], h=6, tag='Wand x=-2')
    sc.wallX(-8, -2, 6.0, gaps=[(-4.0, 4.0)], h=6, tag='Nordabschluss z=6')
    sc.wallZ(6, 14, -4.0, gaps=[(12.5, 1.6)], h=6, tag='Trennwand x=-4')

    sc.stair_flight(-6.8, 13.4, 10.4, 1.8, 0.0, 1.8, tag='Lauf A')
    sc.areas.append(Area(-7.7, -4.1, 9.2, 10.4, 1.8, tag='Podest'))
    sc.solids.append(Box(-7.7, -4.1, 9.1, 9.3, 1.8, 3.0,
                         tag='Bruestung Podestnordkante'))
    sc.solids.append(Box(-7.7, -4.1, 9.2, 10.4, 0.0, 1.8,
                         blocks_camera=False, tag='Fuellung unter Podest'))
    sc.stair_flight(-5.0, 9.2, 6.2, 1.8, 1.8, 3.8, tag='Lauf B')

    F = 3.8
    sc.floor_tile(6.0, 5.7, -5.0, 3.35, F, tag='OG noerdlich')
    sc.floor_tile(6.0, 4.4, -5.0, 11.8, F, tag='OG suedlich')
    sc.floor_tile(1.8, 3.4, -7.1, 7.9, F, tag='OG westlich')
    sc.floor_tile(2.0, 3.4, -3.0, 7.9, F, tag='OG oestlich')
    sc.solids.append(Box(-6.3, -6.1, 6.2, 9.6, F, F + 1.2, tag='Schachtgel. West'))
    sc.solids.append(Box(-4.1, -3.9, 6.2, 9.6, F, F + 1.2, tag='Schachtgel. Ost'))
    sc.solids.append(Box(-6.2, -4.0, 9.5, 9.7, F, F + 1.2, tag='Schachtgel. Sued'))
    sc.solids.append(Box(-2.1, -1.9, 0.5, 12.0, F, F + 1.2, tag='Galeriebruestung'))
    return sc, [(-6.8, 13.2, 0.0, -1, "von unten hoch"),
                (-5.0, 10.2, 1.8, -1, "vom Podest auf Lauf B")]


def treppe2():
    sc = Scene("Treppe 2  Obergeschoss -> Badehaus   (Villa.swift:2348..2352)")
    F, F2 = 3.8, 6.6
    sc.floor_tile(6.0, 4.4, -5.0, 11.8, F, tag='OG suedlich')
    sc.floor_tile(6.0, 5.7, -5.0, 3.35, F, tag='OG noerdlich')
    sc.switchback(-6.8, -5.0, 9.8, 12.8, 1.8, F, F2, tag='T2')
    # Villa.swift:2351 - Fuellung unter Lauf 2
    sc.solids.append(Box(-5.9, -4.1, 11.2, 12.8, F, F2,
                         blocks_camera=False, tag='Fuellung unter Lauf 2'))
    sc.floor_tile(7.0, 6.8, -4.5, 6.4, F2, tag='Vorraum noerdlich')
    sc.floor_tile(1.9, 3.2, -7.05, 11.4, F2, tag='Vorraum westlich')
    sc.floor_tile(2.9, 3.2, -2.45, 11.4, F2, tag='Vorraum oestlich')
    sc.wallZ(3, 13, -8, h=2.7, base=F2, tag='Badehaus Westwand')
    sc.wallX(-8, -1, 13, h=2.7, base=F2, tag='Badehaus Suedwand')
    return sc, [(-6.8, 10.0, F, +1, "vom OG auf Lauf 1"),
                (-5.0, 12.6, 5.2, -1, "von der Wende auf Lauf 2")]


if __name__ == '__main__':
    gesamt = True
    for bauen in (treppe1, treppe2):
        sc, starts = bauen()
        print("=" * 74)
        print(sc.name)
        print("=" * 74)
        print(f"  {len(sc.solids)} Sperren, {len(sc.areas)} Laufflaechen im Modell\n")
        steigung(sc)
        in_der_wand(sc)
        kopffreiheit(sc)
        stuerze(sc)
        ok = True
        for x, z, y, r, titel in starts:
            ok &= begehbar(sc, x, z, y, r, titel)
            print()
        print(f"  ERGEBNIS: {'begehbar' if ok else 'NICHT begehbar'}\n")
        gesamt &= ok
    print("=" * 74)
    print("Beide Treppenhaeuser begehbar." if gesamt
          else "Mindestens ein Treppenhaus ist nicht begehbar.")
