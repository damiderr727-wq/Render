"""
Baut die Raeume der Welt und schreibt sie als JSON nach Resources/Levels.

Die Welt ist ein zusammenhaengendes Metroidvania: jeder Raum ist von Hand
gesetzt, Verbindungen sind benannte Tueren, und der Fortschritt haengt an
vier Faehigkeiten:

    Fluegelschlag  - Doppelsprung   (oeffnet Schaechte)
    Klangschritt   - Wandhaftung    (oeffnet Kamine)
    Herzschlag     - Sprint/Dash    (oeffnet weite Luecken)
    Basston        - Bruchschlag    (oeffnet verstimmte Sperren)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Levels"

AIR, SOLID, PLATFORM, SPIKE, DWALL = ".", "#", "=", "^", "D"


class Room:
    def __init__(self, rid: str, name: str, region: str, w: int, h: int, music: str | None = None):
        self.id = rid
        self.name = name
        self.region = region
        self.w = w
        self.h = h
        self.music = music or region
        self.grid = [[AIR] * w for _ in range(h)]
        self.doors: list[dict] = []
        self.spawns: dict[str, dict] = {}
        self.benches: list[dict] = []
        self.enemies: list[dict] = []
        self.pickups: list[dict] = []
        self.decor: list[dict] = []
        self.lore: list[dict] = []
        self.boss: dict | None = None
        self.dark = 0.0

    # ---- Gelaende

    def set(self, x: int, y: int, ch: str) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = ch

    def fill(self, x: int, y: int, w: int, h: int, ch: str = SOLID) -> "Room":
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.set(i, j, ch)
        return self

    def carve(self, x: int, y: int, w: int, h: int) -> "Room":
        return self.fill(x, y, w, h, AIR)

    def border(self, thickness: int = 1) -> "Room":
        self.fill(0, 0, self.w, thickness)
        self.fill(0, self.h - thickness, self.w, thickness)
        self.fill(0, 0, thickness, self.h)
        self.fill(self.w - thickness, 0, thickness, self.h)
        return self

    def ground(self, x0: int, x1: int, profile) -> "Room":
        """Fuellt von der Hoehe `profile(x)` bis zum unteren Rand mit Fels."""
        for x in range(x0, x1):
            top = int(round(profile(x)))
            self.fill(x, top, 1, self.h - top)
        return self

    def ceiling(self, x0: int, x1: int, profile) -> "Room":
        for x in range(x0, x1):
            bot = int(round(profile(x)))
            self.fill(x, 0, 1, bot)
        return self

    def platform(self, x: int, y: int, w: int) -> "Room":
        return self.fill(x, y, w, 1, PLATFORM)

    def ledge(self, x: int, y: int, w: int, h: int = 2) -> "Room":
        return self.fill(x, y, w, h, SOLID)

    def spikes(self, x: int, y: int, w: int) -> "Room":
        return self.fill(x, y, w, 1, SPIKE)

    def dissowall(self, x: int, y: int, w: int, h: int) -> "Room":
        return self.fill(x, y, w, h, DWALL)

    def stairs(self, x: int, y: int, steps: int, dx: int = 1, dy: int = -1, w: int = 3) -> "Room":
        for i in range(steps):
            self.ledge(x + i * dx * w, y + i * dy, w, 2)
        return self

    # ---- Bodensuche
    #
    # Konvention: Entitaets-Koordinaten sind Kacheleinheiten, `x` ist die
    # Mitte, `y` die Fusslinie. Steht eine Figur auf Kachelreihe 15, ist
    # ihr y also genau 15.0 - die Oberkante dieser Reihe.

    def floor_at(self, x: float, hint: float = 0) -> int:
        """Erste begehbare Oberflaeche ab `hint` abwaerts (Fels mit Luft darueber)."""
        xi = max(0, min(self.w - 1, int(x)))
        for y in range(max(1, int(hint)), self.h):
            if self.grid[y][xi] in (SOLID, PLATFORM) and self.grid[y - 1][xi] == AIR:
                return y
        return self.h - 1

    def spawn_on(self, name: str, x: float, hint: float = 0, facing: int = 1) -> "Room":
        return self.spawn(name, x, self.floor_at(x, hint), facing)

    def bench_on(self, x: float, hint: float = 0) -> "Room":
        return self.bench(x, self.floor_at(x, hint))

    def enemy_on(self, kind: str, x: float, hint: float = 0, **opts) -> "Room":
        return self.enemy(kind, x, self.floor_at(x, hint), **opts)

    def crystal_on(self, x: float, hint: float = 0, size: int = 1) -> "Room":
        return self.crystal(x, self.floor_at(x, hint), size)

    def note_on(self, x: float, hint: float, text: str) -> "Room":
        return self.note(x, self.floor_at(x, hint), text)

    # ---- Inhalte

    def door(self, did: str, x: int, y: int, w: int, h: int, target: str, target_door: str,
             requires: str | None = None) -> "Room":
        self.carve(x, y, w, h)
        self.doors.append({
            "id": did, "x": x, "y": y, "w": w, "h": h,
            "target": target, "targetDoor": target_door,
            **({"requires": requires} if requires else {}),
        })
        return self

    def side_door(self, did: str, side: str, target: str, target_door: str,
                  requires: str | None = None, height: int = 4,
                  hint: int = 1, spawn_facing: int | None = None) -> "Room":
        """
        Tuer in der linken oder rechten Wand, buendig auf dem Boden.

        Von Hand gesetzte Tuerhoehen passen selten zum spaeter gezeichneten
        Gelaende - die Tuer haengt dann in der Wand oder ist zugewachsen.
        Hier wird stattdessen der Boden gesucht, ein kurzer Gang freigeraeumt
        und flach gelegt, und die Tuer darauf gesetzt.
        """
        inward = 4
        if side == "left":
            xs = list(range(0, inward))
            door_x, probe_x = 0, inward
            facing = 1
        else:
            xs = list(range(self.w - inward, self.w))
            door_x, probe_x = self.w - 1, self.w - inward - 1
            facing = -1

        floor = self.floor_at(probe_x, hint)
        for x in xs:
            self.fill(x, floor, 1, self.h - floor, SOLID)   # Boden auffuellen
            self.carve(x, max(0, floor - height - 1), 1, height + 1)  # Gang freiraeumen
        self.door(did, door_x, floor - height, 1, height, target, target_door, requires)
        # Jeder Raum haelt einen Spawnpunkt, der so heisst wie seine eigene Tuer.
        self.spawn(did, probe_x, floor, spawn_facing if spawn_facing is not None else facing)
        return self

    def shaft_door(self, did: str, x: int, w: int, side: str, target: str, target_door: str,
                   requires: str | None = None) -> "Room":
        """
        Tuer in Decke oder Boden. Der Schacht wird durch das gesamte Material
        gestochen, damit die Oeffnung nicht hinter einer Deckenschicht liegt.
        """
        if side == "up":
            rows = range(0, self.h)
            door_y = 0
        else:
            rows = range(self.h - 1, -1, -1)
            door_y = self.h - 1

        for x_i in range(x, x + w):
            for y in rows:
                if self.grid[y][x_i] == AIR:
                    break
                self.set(x_i, y, AIR)
        self.doors.append({
            "id": did, "x": x, "y": door_y, "w": w, "h": 1,
            "target": target, "targetDoor": target_door,
            **({"requires": requires} if requires else {}),
        })
        return self

    def spawn(self, name: str, x: float, y: float, facing: int = 1) -> "Room":
        self.spawns[name] = {"x": x, "y": y, "facing": facing}
        return self

    def bench(self, x: float, y: float) -> "Room":
        self.benches.append({"x": x, "y": y})
        return self

    def enemy(self, kind: str, x: float, y: float, **opts) -> "Room":
        self.enemies.append({"type": kind, "x": x, "y": y, **opts})
        return self

    def pickup(self, kind: str, pid: str, x: float, y: float) -> "Room":
        self.pickups.append({"kind": kind, "id": pid, "x": x, "y": y})
        return self

    def crystal(self, x: float, y: float, size: int = 1) -> "Room":
        self.decor.append({"kind": "crystal", "size": size, "x": x, "y": y})
        return self

    def reed(self, x: float, y: float) -> "Room":
        self.decor.append({"kind": "reed", "x": x, "y": y})
        return self

    def scatter_decor(self, seed: int, count: int, kinds=("crystal", "reed")) -> "Room":
        """Setzt Deko auf zufaellige, aber begehbare Bodenkanten."""
        rng = _Rng(seed)
        spots = []
        for x in range(1, self.w - 1):
            for y in range(1, self.h - 1):
                if self.grid[y][x] == SOLID and self.grid[y - 1][x] == AIR:
                    spots.append((x, y))
                    break
        if not spots:
            return self
        for _ in range(count):
            x, y = spots[rng.int(0, len(spots) - 1)]
            kind = kinds[rng.int(0, len(kinds) - 1)]
            if kind == "crystal":
                self.crystal(x, y, rng.int(0, 2))
            else:
                self.reed(x, y)
        return self

    def note(self, x: float, y: float, text: str) -> "Room":
        self.lore.append({"x": x, "y": y, "text": text})
        return self

    def set_boss(self, kind: str, x: float, y: float, arena: tuple[int, int, int, int]) -> "Room":
        self.boss = {"type": kind, "x": x, "y": y,
                     "arena": {"x": arena[0], "y": arena[1], "w": arena[2], "h": arena[3]}}
        return self

    # ---- Ausgabe

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "region": self.region, "music": self.music,
            "width": self.w, "height": self.h, "darkness": self.dark,
            "tiles": ["".join(row) for row in self.grid],
            "doors": self.doors, "spawns": self.spawns, "benches": self.benches,
            "enemies": self.enemies, "pickups": self.pickups, "decor": self.decor,
            "lore": self.lore, **({"boss": self.boss} if self.boss else {}),
        }


class _Rng:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF or 1

    def next(self) -> float:
        self.s ^= (self.s << 13) & 0xFFFFFFFF
        self.s ^= self.s >> 17
        self.s ^= (self.s << 5) & 0xFFFFFFFF
        self.s &= 0xFFFFFFFF
        return self.s / 0xFFFFFFFF

    def int(self, a: int, b: int) -> int:
        return a + int(self.next() * (b - a + 1)) % max(1, b - a + 1)


# =====================================================================
#  Region A - Der schlafende Hain
#
#  Sprungwerte aus Tuning.swift, in Kacheln gerechnet:
#    einfacher Sprung   ~3,3 hoch   /  ~4 weit
#    mit Fluegelschlag  ~6,2 hoch   /  ~6 weit
#  Sprossen liegen deshalb 3 Kacheln auseinander, solange die Figur noch
#  nichts kann, und 4 Kacheln, sobald sie den Doppelsprung hat.
# =====================================================================

def room_A1() -> Room:
    r = Room("A1", "DER ERSTE TON", "hain", 60, 22)
    r.border()
    r.ground(1, 59, lambda x: 16 - 2 * math.sin(x * 0.09) - (1 if 20 < x < 34 else 0))
    r.ceiling(1, 59, lambda x: 3 + 1.5 * math.sin(x * 0.13 + 1))

    # Plattformen sitzen dort, wo sie einen Weg oeffnen - nicht zwei
    # Kacheln ueber ebenem Boden, wo man ohnehin laufen kann.
    r.platform(22, 11, 6)
    r.ledge(32, 12, 8, 2)
    r.platform(44, 8, 5)

    r.side_door("R", "right", "A2", "L")
    r.spawn_on("start", 8, 7, 1)
    r.bench_on(11, 7)

    r.enemy("klangmotte", 28, 8)
    r.enemy("klangmotte", 46, 7)

    r.crystal_on(20, 7, 2)
    r.crystal_on(38, 7, 1)
    r.scatter_decor(11, 16)

    r.note_on(16, 7, "HIER SANG DIE WELT SICH SELBST. "
                     "JETZT HAELT SIE NUR NOCH DEN ATEM AN.")
    r.note_on(50, 7, "DREI INSTRUMENTE LAGEN IM HAIN. "
                     "NUR EINES WAR NOCH GESTIMMT.")
    return r


def room_A2() -> Room:
    r = Room("A2", "LICHTUNG DER STUMMEN VOEGEL", "hain", 72, 34)
    r.border()
    r.ground(1, 71, lambda x: 27 - 3 * math.sin(x * 0.07))
    r.ceiling(1, 44, lambda x: 14 + 2 * math.sin(x * 0.11))
    r.ceiling(44, 71, lambda x: 2)
    # Der Kamin nach oben: links und rechts von Fels gefasst.
    r.fill(44, 3, 2, 12)
    r.fill(60, 3, 11, 14)

    r.platform(8, 23, 6)
    r.platform(18, 20, 5)
    r.ledge(26, 22, 7, 2)
    r.platform(37, 19, 6)

    # Kaminboden: fuenf Kacheln ueber dem Grund - ohne Fluegelschlag zu hoch.
    r.ledge(47, 23, 9, 2)
    r.platform(46, 19, 5)
    r.platform(53, 15, 5)
    r.platform(46, 11, 5)
    r.platform(53, 7, 5)

    r.side_door("L", "left", "A1", "R")
    r.side_door("R", "right", "A3", "L", hint=17)
    r.shaft_door("U", 53, 5, "up", "B1", "N", requires="fluegelschlag")
    r.spawn_on("U", 55, 4, 1)

    r.pickup("instrument", "trommel", 30, 21)

    r.enemy("klangmotte", 16, 19)
    r.enemy_on("stilleschreiter", 27, 17, patrol=6)
    r.enemy("klangmotte", 41, 15)
    r.enemy_on("dissonanzknospe", 34, 17)
    r.enemy_on("stilleschreiter", 62, 17, patrol=5)

    r.crystal_on(12, 17, 2)
    r.crystal_on(35, 17, 1)
    r.crystal_on(58, 17, 2)
    r.scatter_decor(22, 22)

    r.note_on(24, 17, "DIE TROMMEL SCHLAEGT DEN GRUNDTON. "
                      "WAS DEN GRUNDTON HAELT, HAELT DIE WELT.")
    r.note(50, 22, "OBEN LIEGT DIE KATHEDRALE. "
                   "OHNE FLUEGEL KOMMST DU NICHT HINAUF.")
    return r


def room_A3() -> Room:
    r = Room("A3", "WURZELGANG DER ECHOS", "hain", 64, 26)
    r.border()
    r.ground(1, 63, lambda x: 20 - 4 * math.sin(x * 0.06 + 2))
    r.ceiling(1, 63, lambda x: 4 + 3 * math.sin(x * 0.09))

    # Abstieg nach rechts, dann eine Treppe zurueck nach oben.
    r.ledge(12, 17, 6, 2)
    r.platform(21, 14, 5)
    r.ledge(24, 19, 5, 2)
    r.ledge(30, 16, 8, 2)
    r.spikes(40, 23, 5)
    r.ledge(42, 21, 5, 2)
    r.ledge(48, 18, 5, 2)
    r.ledge(53, 15, 8, 2)

    r.side_door("L", "left", "A2", "R")

    r.pickup("instrument", "floete", 34, 15)
    r.pickup("ability", "fluegelschlag", 56, 13)

    r.enemy("klangmotte", 20, 11)
    r.enemy_on("dissonanzknospe", 32, 8)
    r.enemy("klangmotte", 44, 9)
    r.enemy_on("stilleschreiter", 56, 8, patrol=3)

    r.crystal_on(16, 8, 1)
    r.crystal_on(46, 8, 2)
    r.scatter_decor(33, 18)

    r.note_on(26, 8, "DIE FLOETE TRAEGT DEN REINEN TON. "
                     "SIE STICHT, WO DIE LEIER STREICHELT.")
    r.note_on(50, 8, "EIN FLUEGELSCHLAG BLIEB IN DER LUFT HAENGEN, "
                     "ALS DER VOGEL SCHON LANGE FORT WAR.")
    return r


# =====================================================================
#  Region B - Kathedrale der Fugen
# =====================================================================

def room_B1() -> Room:
    r = Room("B1", "VORHALLE DER FUGEN", "kathedrale", 44, 48)
    r.border()
    r.fill(1, 44, 42, 3)

    # Aufstieg im Zickzack: Empore links - Mittelsteg - Empore rechts.
    # Vier Reihen Abstand, drei Kacheln seitlicher Versatz.
    rungs = [(40, "left"), (36, "mid"), (32, "right"), (28, "mid"),
             (24, "left"), (20, "mid"), (16, "right"), (12, "mid"),
             (8, "left"), (4, "mid")]
    for y, side in rungs:
        if side == "left":
            r.ledge(3, y, 13, 2)
        elif side == "right":
            r.ledge(28, y, 13, 2)
        else:
            r.platform(18, y, 8)

    r.shaft_door("U", 18, 5, "up", "B2", "N", requires="fluegelschlag")
    r.shaft_door("N", 33, 5, "down", "A2", "U")
    r.spawn_on("U", 20, 5, 1)
    r.spawn_on("N", 26, 42, 1)
    r.side_door("R", "right", "B3", "L", hint=42)
    r.bench_on(9, 42)

    r.enemy("klangmotte", 22, 34)
    r.enemy("klangmotte", 20, 20)
    r.enemy_on("dissonanzknospe", 24, 42)
    r.enemy("echoscherbe", 34, 30)
    r.enemy_on("stilleschreiter", 33, 30, patrol=4)

    r.crystal_on(14, 42, 2)
    r.crystal_on(30, 42, 1)
    r.scatter_decor(44, 14, kinds=("crystal",))

    r.note_on(20, 42, "DIE FUGE IST EIN GESPRAECH, IN DEM NIEMAND "
                      "DEM ANDEREN INS WORT FAELLT.")
    return r


def room_B2() -> Room:
    r = Room("B2", "DAS ORGELREGISTER", "kathedrale", 56, 34)
    r.border()
    r.fill(1, 30, 54, 3)

    # Die Pfeifen haengen von der Decke - man geht unter ihnen hindurch.
    for i in range(6):
        r.fill(5 + i * 8, 1, 3, 4 + (i % 3) * 2)

    # Aufstieg: vier Kacheln Luecke, drei bis vier Kacheln Hoehe.
    for x, y in [(4, 27), (12, 24), (20, 20), (28, 17), (36, 13), (44, 10)]:
        r.platform(x, y, 5)

    r.spikes(15, 29, 5)
    r.spikes(31, 29, 5)

    r.shaft_door("N", 2, 4, "down", "B1", "U")
    r.spawn_on("N", 9, 26, 1)

    r.pickup("ability", "klangschritt", 42, 9)

    r.enemy("echoscherbe", 16, 22)
    r.enemy("echoscherbe", 33, 14)
    r.enemy_on("dissonanzknospe", 25, 26)
    r.enemy("klangmotte", 42, 8)

    r.scatter_decor(55, 10, kinds=("crystal",))
    r.note_on(20, 26, "JEDE PFEIFE KENNT NUR EINEN TON. "
                      "ZUSAMMEN KENNEN SIE ALLE.")
    r.note(42, 12, "WER DEN KLANG IN DER WAND HOERT, "
                   "KANN AUF IHM STEHEN.")
    return r


def room_B3() -> Room:
    r = Room("B3", "KREUZGANG DER STIMMEN", "kathedrale", 80, 32)
    r.border()
    r.fill(1, 28, 78, 3)

    # Kamine: schmale Schaechte zwischen hohen Pfeilern.
    r.fill(20, 6, 3, 22)
    r.fill(30, 0, 3, 20)
    r.fill(44, 8, 3, 20)
    r.fill(54, 0, 3, 18)
    r.spikes(23, 27, 7)
    r.spikes(47, 27, 7)
    r.platform(24, 12, 5)
    r.platform(34, 8, 8)
    r.platform(48, 14, 5)
    r.ledge(58, 18, 8, 2)
    # Die Kluft vor dem Ausgang - genau einen Herzschlag weit.
    r.carve(66, 20, 12, 11)
    r.ledge(66, 17, 3, 2)
    r.ledge(70, 16, 10, 2)

    r.side_door("L", "left", "B1", "R", hint=20)
    r.door("R", 79, 12, 1, 4, "B4", "L", requires="klangschritt")
    r.spawn_on("R", 76, 12, -1)
    r.shaft_door("N", 36, 5, "down", "C1", "U", requires="herzschlag")
    r.spawn_on("N", 42, 20, 1)

    r.enemy_on("stilleschreiter", 12, 20, patrol=7)
    r.enemy("echoscherbe", 26, 18)
    r.enemy("klangmotte", 38, 6)
    r.enemy_on("dissonanzknospe", 60, 12)
    r.enemy("echoscherbe", 60, 14)
    r.enemy_on("stilleschreiter", 62, 12, patrol=4)

    r.scatter_decor(66, 16, kinds=("crystal",))
    r.note_on(6, 20, "VIER STIMMEN GINGEN HIER IM KREIS. "
                     "EINE BLIEB STEHEN - SEITDEM STOLPERN ALLE.")
    r.note_on(67, 12, "DIE KLUFT MISST GENAU EINEN HERZSCHLAG.")
    return r


def room_B4() -> Room:
    r = Room("B4", "DIE HERZKAMMER", "kathedrale", 46, 28)
    r.border()
    r.ground(1, 45, lambda x: 22 - 2 * math.sin(x * 0.12))
    r.ceiling(1, 45, lambda x: 4)
    r.ledge(10, 18, 7, 2)
    r.ledge(26, 16, 8, 2)
    r.platform(19, 12, 8)
    r.spikes(18, 21, 7)

    r.side_door("L", "left", "B3", "R", hint=6)
    r.bench_on(6, 6)

    r.pickup("ability", "herzschlag", 30, 14)

    r.enemy_on("stilleschreiter", 24, 6, patrol=5)
    r.enemy("echoscherbe", 32, 12)
    r.enemy_on("dissonanzknospe", 38, 6)

    r.crystal_on(14, 6, 2)
    r.crystal_on(36, 6, 1)
    r.scatter_decor(77, 12, kinds=("crystal",))
    r.note_on(24, 6, "EIN HERZ SCHLUG HIER SO LAUT, "
                     "DASS DER RAUM SICH DANACH RICHTETE.")
    return r


# =====================================================================
#  Region C - Resonanzkavernen
# =====================================================================

def room_C1() -> Room:
    r = Room("C1", "DIE KRISTALLGROTTEN", "grotten", 88, 30)
    r.border()
    r.ground(1, 87, lambda x: 24 - 3 * math.sin(x * 0.05) - 2 * math.sin(x * 0.17))
    r.ceiling(1, 87, lambda x: 4 + 2 * math.sin(x * 0.08 + 3))

    # Aufstieg zurueck zur Kathedrale, links im Raum.
    for x, y in [(3, 18), (11, 15), (3, 12), (11, 9), (3, 6)]:
        r.ledge(x, y, 8, 2)

    # Weite Luecken - Gelaende fuer den Herzschlag.
    # Die Kluefte enden eine Kachel ueber dem Rand - der Raum bleibt dicht.
    r.carve(20, 18, 10, 11)
    r.carve(42, 18, 11, 11)
    r.carve(64, 18, 10, 11)
    r.ledge(30, 15, 12, 2)
    r.ledge(53, 15, 11, 2)
    r.platform(24, 12, 5)
    r.platform(46, 11, 5)
    r.spikes(21, 28, 8)
    r.spikes(43, 28, 9)
    r.spikes(65, 28, 8)

    r.shaft_door("U", 6, 5, "up", "B3", "N")
    r.spawn_on("U", 8, 8, 1)
    r.side_door("R", "right", "C2", "L", hint=8)
    r.bench_on(16, 8)

    r.enemy("echoscherbe", 26, 14)
    r.enemy("klangmotte", 36, 10)
    r.enemy_on("stilleschreiter", 35, 8, patrol=5)
    r.enemy_on("dissonanzknospe", 58, 8)
    r.enemy("echoscherbe", 70, 16)
    r.enemy("klangmotte", 78, 12)

    for x, s in ((34, 1), (56, 2), (76, 1), (82, 2)):
        r.crystal_on(x, 8, s)
    r.scatter_decor(88, 24)
    r.note_on(18, 8, "DIE KRISTALLE WACHSEN DORT, WO EIN TON "
                     "LANGE GENUG GEHALTEN WURDE.")
    return r


def room_C2() -> Room:
    r = Room("C2", "DER SCHLUND", "grotten", 52, 40)
    r.border()
    r.fill(1, 36, 50, 3)

    # Der Schlund wird im Zickzack erklommen: breite Simse aussen,
    # schmale Stege in der Mitte, immer vier Kacheln Hoehenunterschied.
    rungs = [(33, "left"), (29, "mid"), (25, "right"), (21, "mid"),
             (17, "left"), (13, "mid"), (9, "right"), (5, "mid")]
    for y, side in rungs:
        if side == "left":
            r.ledge(6, y, 14, 2)
        elif side == "right":
            r.ledge(32, y, 16, 2)
        else:
            r.platform(22, y, 8)

    r.spikes(21, 35, 10)

    r.side_door("L", "left", "C1", "R", hint=34)
    r.side_door("R", "right", "C3", "L", hint=6)

    r.pickup("ability", "basston", 26, 4)

    r.enemy("echoscherbe", 12, 28)
    r.enemy("klangmotte", 26, 24)
    r.enemy("echoscherbe", 40, 20)
    r.enemy_on("dissonanzknospe", 10, 30)
    r.enemy("klangmotte", 24, 12)

    r.crystal_on(8, 34, 2)
    r.crystal_on(44, 34, 1)
    r.scatter_decor(99, 14)
    r.note_on(14, 34, "GANZ UNTEN LIEGT DER TON, DEN NIEMAND SINGT. "
                      "MAN SCHLAEGT IHN.")
    return r


def room_C3() -> Room:
    r = Room("C3", "DIE VERSTIMMTEN ADERN", "grotten", 76, 28)
    r.border()
    r.ground(1, 75, lambda x: 22 - 2 * math.sin(x * 0.1))
    r.ceiling(1, 75, lambda x: 3 + 2 * math.sin(x * 0.14))
    r.ledge(14, 17, 8, 2)
    r.ledge(32, 15, 9, 2)
    r.ledge(52, 18, 8, 2)
    r.platform(24, 12, 6)
    r.platform(44, 11, 6)

    # Verstimmte Sperren - nur der Basston bricht sie.
    r.dissowall(28, 14, 2, 8)
    r.dissowall(48, 12, 2, 10)
    r.dissowall(64, 16, 2, 6)

    r.side_door("L", "left", "C2", "R", hint=7)
    r.side_door("R", "right", "D0", "L", hint=7, requires="basston")

    r.enemy_on("stilleschreiter", 18, 7, patrol=5)
    r.enemy_on("dissonanzknospe", 34, 7)
    r.enemy("echoscherbe", 42, 12)
    r.enemy("klangmotte", 56, 12)
    r.enemy_on("stilleschreiter", 70, 7, patrol=3)

    r.crystal_on(10, 7, 1)
    r.crystal_on(60, 7, 2)
    r.scatter_decor(111, 16)
    r.note_on(22, 7, "DIE SPERREN SIND KEIN STEIN. SIE SIND EIN AKKORD, "
                     "DER SICH WEIGERT AUFZULOESEN.")
    return r


# =====================================================================
#  Region D - Das Herz der Dissonanz
# =====================================================================

def room_D0() -> Room:
    r = Room("D0", "SCHWELLE DER STILLE", "dissonanz", 44, 22)
    r.border()
    r.fill(1, 17, 42, 5)
    r.ceiling(1, 43, lambda x: 3)
    r.ledge(16, 13, 12, 2)
    r.dark = 0.15

    r.side_door("L", "left", "C3", "R", hint=6)
    r.side_door("R", "right", "D1", "L", hint=6)
    r.bench_on(9, 6)

    r.crystal_on(22, 6, 2)
    r.note_on(13, 6, "AB HIER HOERT MAN NICHTS MEHR. "
                     "NICHT WEIL ES STILL IST - WEIL ALLES ZUGLEICH KLINGT.")
    r.note_on(34, 6, "ER WAR DER, DER DEN TAKT GAB. "
                     "NIEMAND SAGTE IHM, WANN ER AUFHOEREN SOLL.")
    return r


def room_D1() -> Room:
    r = Room("D1", "DAS HERZ DER DISSONANZ", "dissonanz", 60, 30)
    r.border()
    r.fill(1, 25, 58, 5)
    r.ceiling(1, 59, lambda x: 3)
    r.ledge(6, 18, 8, 2)
    r.ledge(46, 18, 8, 2)
    r.platform(20, 15, 8)
    r.platform(32, 15, 8)
    r.dark = 0.22

    r.side_door("L", "left", "D0", "R", hint=6)
    r.set_boss("kantor", 42, 25, (2, 4, 56, 21))
    return r


# =====================================================================

ROOMS = [
    room_A1, room_A2, room_A3,
    room_B1, room_B2, room_B3, room_B4,
    room_C1, room_C2, room_C3,
    room_D0, room_D1,
]


def validate(rooms: dict[str, Room]) -> list[str]:
    """Prueft Verbindungen, Spawnpunkte und Gelaende auf grobe Fehler."""
    problems: list[str] = []
    for r in rooms.values():
        if len(r.grid) != r.h or any(len(row) != r.w for row in r.grid):
            problems.append(f"{r.id}: Rastergroesse stimmt nicht")

        for d in r.doors:
            target = rooms.get(d["target"])
            if target is None:
                problems.append(f"{r.id}.{d['id']}: Zielraum {d['target']} fehlt")
                continue
            if d["targetDoor"] not in target.spawns:
                problems.append(
                    f"{r.id}.{d['id']} -> {d['target']}: Spawnpunkt '{d['targetDoor']}' fehlt")
            back = [x for x in target.doors if x["target"] == r.id]
            if not back and d["target"] != r.id:
                problems.append(f"{r.id}.{d['id']} -> {d['target']}: kein Rueckweg")

        # y ist die Fusslinie: der Koerper belegt die Reihen ueber y.
        def embedded(x: int, y: int, height: int = 2) -> bool:
            if not (0 <= x < r.w and 0 <= y <= r.h):
                return True
            return any(r.grid[yy][x] == SOLID
                       for yy in range(max(0, y - height), min(r.h, y)))

        for name, s in r.spawns.items():
            x, y = int(s["x"]), int(s["y"])
            if not (0 <= x < r.w and 0 <= y < r.h):
                problems.append(f"{r.id}: Spawn '{name}' ausserhalb des Raums")
                continue
            if embedded(x, y):
                problems.append(f"{r.id}: Spawn '{name}' steckt im Fels ({x},{y})")
            # Erlaubt ist ein Sturz von bis zu 16 Kacheln (Eintritt von oben).
            if not any(r.grid[yy][x] in (SOLID, PLATFORM)
                       for yy in range(y, min(r.h, y + 17))):
                problems.append(f"{r.id}: Spawn '{name}' hat keinen Boden darunter")

        for lst, label in ((r.benches, "Bank"), (r.pickups, "Fundstueck")):
            for item in lst:
                x, y = int(item["x"]), int(item["y"])
                if embedded(x, y):
                    problems.append(f"{r.id}: {label} bei ({x},{y}) steckt im Fels")

        for e in r.enemies:
            x, y = int(e["x"]), int(e["y"])
            if embedded(x, y):
                problems.append(f"{r.id}: Gegner {e['type']} bei ({x},{y}) steckt im Fels")
    return problems


def check_progression(rooms: dict[str, Room], start: str = "A1") -> list[str]:
    """
    Simuliert den Fortschritt: Welche Raeume sind mit welchen Faehigkeiten
    erreichbar? Faellt auf, wenn eine Faehigkeit hinter sich selbst liegt
    oder ein Raum nie erreichbar wird.
    """
    problems: list[str] = []
    abilities: set[str] = set()
    order: list[str] = []

    while True:
        # Erreichbare Raeume mit aktuellem Koennen bestimmen.
        seen = {start}
        frontier = [start]
        while frontier:
            rid = frontier.pop()
            for d in rooms[rid].doors:
                need = d.get("requires")
                if need and need not in abilities:
                    continue
                if d["target"] not in seen:
                    seen.add(d["target"])
                    frontier.append(d["target"])

        gained = False
        for rid in sorted(seen):
            for p in rooms[rid].pickups:
                if p["kind"] == "ability" and p["id"] not in abilities:
                    abilities.add(p["id"])
                    order.append(f"{p['id']} ({rid})")
                    gained = True
        if not gained:
            break

    unreachable = sorted(set(rooms) - seen)
    if unreachable:
        problems.append(f"nie erreichbar: {', '.join(unreachable)}")

    all_abilities = {p["id"] for r in rooms.values() for p in r.pickups if p["kind"] == "ability"}
    missing = sorted(all_abilities - abilities)
    if missing:
        problems.append(f"Faehigkeit unerreichbar: {', '.join(missing)}")

    boss_rooms = [r.id for r in rooms.values() if r.boss]
    for b in boss_rooms:
        if b not in seen:
            problems.append(f"Boss-Raum {b} nicht erreichbar")

    print("  Fortschritt: " + " -> ".join(order))
    return problems


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rooms = {}
    for factory in ROOMS:
        r = factory()
        rooms[r.id] = r

    problems = validate(rooms) + check_progression(rooms)
    for p in problems:
        print(f"  ! {p}")

    for r in rooms.values():
        (OUT / f"{r.id}.json").write_text(
            json.dumps(r.to_dict(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    index = {
        "startRoom": "A1",
        "startSpawn": "start",
        "rooms": [
            {"id": r.id, "name": r.name, "region": r.region, "music": r.music,
             "width": r.w, "height": r.h,
             "connections": [{"door": d["id"], "to": d["target"]} for d in r.doors]}
            for r in rooms.values()
        ],
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n",
                                    encoding="utf-8")
    total = sum(r.w * r.h for r in rooms.values())
    print(f"levels     -> {len(rooms)} Raeume, {total} Kacheln, "
          f"{len(problems)} Beanstandungen")


if __name__ == "__main__":
    build()
