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


def hash01(x: int, y: int = 0) -> float:
    """Derselbe deterministische Wert wie im Zeichenwerkzeug."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) & 0xFFFFFFFF
    return ((h * 1274126177) & 0xFFFFFFFF) / 0xFFFFFFFF

OUT = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources" / "Levels"

AIR, SOLID, PLATFORM, SPIKE, DWALL = ".", "#", "=", "^", "D"
# Dornen zeigen in vier Richtungen. Wer sie alle als "^" schreibt,
# bekommt an der Decke Dornen, die nach oben wachsen.
SPIKE_DOWN, SPIKE_LEFT, SPIKE_RIGHT = "v", "<", ">"
# Deckenschraegen, sanft (zwei Kacheln je Hoehenkachel).
CEIL_DOWN_HIGH, CEIL_DOWN_LOW = "q", "w"
CEIL_UP_LOW, CEIL_UP_HIGH = "e", "r"
SLOPE_UP, SLOPE_DOWN = "/", "\\"
UP_LOW, UP_HIGH, DOWN_HIGH, DOWN_LOW = "1", "2", "3", "4"


class Room:
    def __init__(self, rid: str, name: str, region: str, w: int, h: int, music: str | None = None):
        self.id = rid
        self.name = name
        self.region = region
        self.w = w
        self.h = h
        self.music = music or region
        # Die Kulisse ist normalerweise die der Region. Der Schattentempel
        # bricht damit: er liegt im Hain und sieht aus wie gebaut.
        self.backdrop: str | None = None
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

    def slope(self, x: int, y: int, length: int, direction: int = 1) -> "Room":
        """
        Ein schraeger Weg. `direction` 1 steigt nach rechts, -1 faellt.

        `y` ist die Reihe der ersten Kachel, und ihre *anschliessende* Kante
        liegt auf deren Oberkante: eine fallende Rampe beginnt also in
        derselben Reihe wie der Boden davor, eine steigende in derselben
        Reihe wie der Boden dahinter. Um eins daneben, und die Rampe erzeugt
        genau die Stufe, die sie beseitigen soll.

        Unter jeder Kachel wird bis zum Raumboden aufgefuellt - sonst haengt
        die Rampe in der Luft.
        """
        for i in range(length):
            tx = x + i
            ty = y - i * direction
            self.set(tx, ty, SLOPE_UP if direction > 0 else SLOPE_DOWN)
            self.fill(tx, ty + 1, 1, self.h - ty - 1, SOLID)
        return self

    def ramp(self, x: int, y: int, steps: int, direction: int = 1) -> "Room":
        """
        Ein sanfter Hang: je Hoehenkachel zwei Kacheln Laenge.

        45 Grad wirken im Gelaende wie eine Rutsche. Zwei zu eins sieht nach
        gewachsenem Boden aus - und ist der Grund, warum die Kachelsaetze der
        Vorbilder fast nie steiler werden.
        """
        pair = (UP_LOW, UP_HIGH) if direction > 0 else (DOWN_HIGH, DOWN_LOW)
        for i in range(steps):
            ty = y - i * direction
            for k, ch in enumerate(pair):
                tx = x + i * 2 + k
                self.set(tx, ty, ch)
                self.fill(tx, ty + 1, 1, self.h - ty - 1, SOLID)
        return self

    def soften(self, min_run: int = 2) -> "Room":
        """
        Wandelt einzelne Bodenstufen in sanfte Haenge.

        Ein Hoehenprofil aus `ground()` wird beim Runden zur Treppe: jede
        Kachel liegt ganz oben oder ganz unten, und die Karte bekommt genau
        die harten Absaetze, an denen man ein Kachelspiel erkennt. Statt in
        jedem Raum von Hand Rampen zu setzen, laeuft dieser Durchgang am
        Ende ueber den fertigen Boden und ersetzt jede Stufe von genau
        einer Kachel durch ein Rampenpaar (zwei Kacheln Laenge, eine hoch).

        Angefasst wird nur gewachsener Boden - eine Saeule, die bis zum
        unteren Rand durchsteht. Schwebende Simse behalten ihre Kante,
        sonst zerfliesst der Unterschied zwischen "Boden" und "Vorsprung".
        Stufen von zwei oder mehr Kacheln bleiben ebenfalls stehen: eine
        Klippe ist eine Absicht, keine Panne.
        """
        surf: list[int | None] = [None] * self.w

        for x in range(1, self.w - 1):
            for y in range(1, self.h):
                # Freiliegende Oberkante gesucht. Deckenkacheln und alles,
                # worueber Dornen oder eine Sperre sitzen, fallen durch.
                if self.grid[y][x] != SOLID or self.grid[y - 1][x] != AIR:
                    continue
                # Nur gewachsener Boden: die Saeule steht bis nach unten durch.
                # Ein schwebender Sims wird uebersprungen, nicht abgebrochen -
                # darunter liegt ja noch der eigentliche Boden.
                if not all(self.grid[j][x] == SOLID for j in range(y, self.h)):
                    continue
                # Kopffreiheit, sonst schiebt die Rampe die Figur in den Fels.
                if all(self.grid[y - k][x] == AIR for k in range(1, 4)):
                    surf[x] = y
                break

        # Laeufe gleicher Hoehe. Nur zwischen zwei ausreichend langen
        # Laeufen darf eine Rampe stehen - sonst frisst sie einen schmalen
        # Absatz ganz auf.
        laeufe: list[tuple[int, int, int]] = []   # (start, ende, hoehe)
        x = 1
        while x < self.w - 1:
            if surf[x] is None:
                x += 1
                continue
            start, hoehe = x, surf[x]
            while x + 1 < self.w - 1 and surf[x + 1] == hoehe:
                x += 1
            laeufe.append((start, x, hoehe))
            x += 1

        for (a0, a1, ha), (b0, b1, hb) in zip(laeufe, laeufe[1:]):
            if b0 != a1 + 1 or abs(ha - hb) != 1:
                continue
            if a1 - a0 + 1 < min_run or b1 - b0 + 1 < min_run:
                continue
            if hb < ha:                                   # steigt nach rechts
                ty, pair = hb, (UP_LOW, UP_HIGH)
            else:                                         # faellt nach rechts
                ty, pair = ha, (DOWN_HIGH, DOWN_LOW)
            for k, ch in enumerate(pair):
                tx = a1 + k
                self.set(tx, ty, ch)
                self.fill(tx, ty + 1, 1, self.h - ty - 1, SOLID)
        return self

    def deckenglaetten(self, min_run: int = 2) -> "Room":
        """
        Macht aus Deckenstufen sanfte Schraegen - das Gegenstueck zu `soften`.

        Der Boden hatte das laengst: ein gerundetes Hoehenprofil wird zur
        Treppe, und jede Einzelstufe wird nachtraeglich durch ein
        Rampenpaar ersetzt. Nach oben ging das nicht, weil es keine
        Schraegkacheln gab - deshalb blieb die Decke ein Regal, egal wie
        fein das Profil war. Der Ausweg war bisher, die Stufen mit
        Tropfsteinen zu verdecken. Das ist Kosmetik; das hier ist die
        Sache selbst.

        Angefasst wird nur gewachsener Fels: eine Saeule, die bis zum
        oberen Rand durchsteht. Ein freischwebender Block behaelt seine
        Kante, und eine Stufe von zwei oder mehr Kacheln bleibt stehen -
        eine Kliffkante ist eine Absicht, keine Panne.
        """
        unter: list[int | None] = [None] * self.w

        for x in range(1, self.w - 1):
            for y in range(self.h - 2, 0, -1):
                if self.grid[y][x] != SOLID or self.grid[y + 1][x] != AIR:
                    continue
                if not all(self.grid[j][x] == SOLID for j in range(0, y + 1)):
                    continue
                unter[x] = y
                break

        laeufe: list[tuple[int, int, int]] = []
        x = 1
        while x < self.w - 1:
            if unter[x] is None:
                x += 1
                continue
            start, hoehe = x, unter[x]
            while x + 1 < self.w - 1 and unter[x + 1] == hoehe:
                x += 1
            laeufe.append((start, x, hoehe))
            x += 1

        for (a0, a1, ha), (b0, b1, hb) in zip(laeufe, laeufe[1:]):
            if b0 != a1 + 1 or abs(ha - hb) != 1:
                continue
            if a1 - a0 + 1 < min_run or b1 - b0 + 1 < min_run:
                continue
            if hb > ha:                              # Decke steigt nach rechts
                ty, paar = ha, (CEIL_UP_LOW, CEIL_UP_HIGH)
            else:                                    # Decke faellt nach rechts
                ty, paar = hb, (CEIL_DOWN_HIGH, CEIL_DOWN_LOW)
            for k, ch in enumerate(paar):
                tx = a1 + k
                self.set(tx, ty, ch)
                self.fill(tx, 0, 1, ty)
        return self

    def stairs(self, x: int, y: int, steps: int, dx: int = 1, dy: int = -1, w: int = 3) -> "Room":
        for i in range(steps):
            self.ledge(x + i * dx * w, y + i * dy, w, 2)
        return self

    # ---- Hoehlenbau
    #
    # Boden und Decke waren bisher zwei unabhaengige Sinuskurven. Das ist
    # der Grund, warum die Raeume unnatuerlich aussehen: eine Sinuskurve
    # hat keine Absicht, und zwei davon haben keinen Bezug zueinander.
    # Ein echter Gang wird eng und weit, eine Halle hat Hoehe, ein Spalt
    # hat keine - die Decke gehoert zum Boden, nicht neben ihn.
    #
    # Darum wird jetzt zweierlei gesetzt: der Bodenverlauf, und darueber
    # die *Kopfhoehe*. Beides als Stuetzpunkte, zwischen denen weich
    # interpoliert wird. So steht in jedem Raum lesbar da, was er tut.

    # Fuer Deckenprofile bleibt die Rauheit klein. Beim Runden auf ganze
    # Kacheln wird aus jeder Zehntelkachel eine ganze Stufe, und eine Decke
    # aus Stufen sieht aus wie eine Treppe. Der Boden vertraegt mehr, weil
    # `soften()` seine Einzelstufen nachtraeglich zu Rampen macht - fuer
    # die Decke gibt es keine solchen Kacheln.
    @staticmethod
    def profil(punkte: list[tuple[float, float]], rauheit: float = 0.0,
               seed: int = 0):
        """
        Eine Kurve durch gesetzte Stuetzpunkte.

        Zwischen zwei Punkten wird weich geblendet (Smoothstep), nicht
        gerade gezogen: eine Gerade zwischen zwei Hoehen sieht aus wie
        eine Rampe, eine geblendete wie gewachsener Fels. `rauheit`
        streut zusaetzlich ein paar Zehntel Kachel darauf, damit die
        Kurve nicht mathematisch glatt bleibt.
        """
        punkte = sorted(punkte)

        def f(x: float) -> float:
            if x <= punkte[0][0]:
                y = punkte[0][1]
            elif x >= punkte[-1][0]:
                y = punkte[-1][1]
            else:
                y = punkte[-1][1]
                for (x0, y0), (x1, y1) in zip(punkte, punkte[1:]):
                    if x0 <= x <= x1:
                        t = (x - x0) / max(1e-6, x1 - x0)
                        t = t * t * (3 - 2 * t)
                        y = y0 + (y1 - y0) * t
                        break
            if rauheit:
                n = (math.sin(x * 0.7 + seed) * 0.5
                     + math.sin(x * 1.9 + seed * 2.3) * 0.3
                     + math.sin(x * 4.1 + seed * 5.7) * 0.2)
                y += n * rauheit
            return y

        return f

    def hoehle(self, x0: int, x1: int, boden, kopfhoehe, seed: int = 0,
               zacken: float = 0.0, saeulen: float = 0.0) -> "Room":
        """
        Boden und Decke in einem Zug - die Decke folgt dem Boden.

        `kopfhoehe(x)` sagt, wie viel Luft ueber dem Boden bleibt. Vier
        Kacheln sind ein Kriechgang, acht ein Weg, sechzehn eine Halle.
        Damit ist die Decke keine eigene Erfindung mehr, sondern eine
        Aussage ueber den Ort.

        Die Decke bekommt ausserdem eine Behandlung, die der Boden schon
        hatte: **an jeder Stufe haengt Fels.**

        Eine gerundete Kurve wird beim Runden auf ganze Kacheln zur
        Treppe, und eine Treppe quer ueber das Bild sieht aus wie ein
        Regal. Der Boden loest das mit Rampen (`soften`); nach oben gibt
        es keine Rampenkacheln. Also wird die Stufe stattdessen
        *verdeckt*: wo die Decke springt, waechst ein Zapfen herunter,
        der genau so lang ist wie der Sprung, plus ein wenig. Damit ist
        die waagerechte Kante weg - was bleibt, liest sich als Fels.
        """
        hoehen: dict[int, tuple[int, int]] = {}
        for x in range(x0, x1):
            b = max(2, min(self.h - 1, int(round(boden(x)))))
            d = max(1, int(round(b - max(3, kopfhoehe(x)))))
            hoehen[x] = (b, d)
            self.fill(x, b, 1, self.h - b)
            self.fill(x, 0, 1, d)

        for x in range(x0, x1):
            b, d = hoehen[x]
            luft = b - d

            # Der Zapfen an der Stufe: so lang wie der Hoehensprung zum
            # Nachbarn, damit die Kante darin verschwindet.
            stufe = max(abs(d - hoehen[x - 1][1]) if x - 1 in hoehen else 0,
                        abs(d - hoehen[x + 1][1]) if x + 1 in hoehen else 0)
            laenge = 0
            if stufe and luft >= 6:
                laenge = stufe + 1 + int(hash01(x, seed + 3) * 2)
            elif zacken and luft >= 10 and hash01(x, seed) < zacken:
                laenge = 1 + int(hash01(x, seed + 1) * 2.6)
            if laenge:
                self.fill(x, d, 1, min(laenge, max(0, luft - 5)))

            if saeulen and luft >= 10 and hash01(x, seed + 9) < saeulen:
                # Eine Saeule, die durchsteht, sperrt den Gang - und weil
                # sie an zufaelliger Stelle steht, sperrt sie ihn an
                # zufaelliger Stelle. Also waechst sie von oben und von
                # unten aufeinander zu und trifft sich nicht ganz.
                oben, unten = int(luft * 0.34), int(luft * 0.24)
                for k in range(2):
                    self.fill(x + k, d, 1, oben)
                    self.fill(x + k, b - unten, 1, unten)
        return self

    def dornengrube(self, x: int, w: int, tiefe: int, boden) -> "Room":
        """
        Eine Grube mit Dornen darin, in den gewachsenen Boden geschnitten.

        Dornen auf ebener Flaeche sind eine Steuer, keine Aufgabe: man
        laeuft daneben vorbei. In einer Grube sind sie eine Frage - drueber
        springen oder einen Weg daneben suchen -, und genau das macht aus
        Laufen ein Spiel.
        """
        oben = int(round(min(boden(x + i) for i in range(w))))
        self.carve(x, oben, w, tiefe)
        self.fill(x, oben + tiefe, w, self.h - oben - tiefe, SOLID)
        self.spikes(x, oben + tiefe - 1, w)
        return self

    def deckendornen(self, x: int, w: int) -> "Room":
        """
        Dornen, die von der Decke haengen - sie begrenzen die Sprunghoehe.

        Sie bekommen die gedrehte Kachel: nach unten zeigend. Vorher stand
        hier dieselbe Kachel wie am Boden, und das sah aus wie Gras, das
        von der Decke waechst.
        """
        for i in range(x, x + w):
            for y in range(1, self.h - 1):
                if self.grid[y][i] == SOLID and self.grid[y + 1][i] == AIR:
                    self.set(i, y + 1, SPIKE_DOWN)
                    break
        return self

    def wanddornen(self, x: int, y: int, h: int, nach: int = 1) -> "Room":
        """Dornen an einer senkrechten Wand. `nach` 1 zeigt nach rechts."""
        ch = SPIKE_RIGHT if nach > 0 else SPIKE_LEFT
        for j in range(y, y + h):
            self.set(x, j, ch)
        return self

    # ---- Bodensuche
    #
    # Konvention: Entitaets-Koordinaten sind Kacheleinheiten, `x` ist die
    # Mitte, `y` die Fusslinie. Steht eine Figur auf Kachelreihe 15, ist
    # ihr y also genau 15.0 - die Oberkante dieser Reihe.

    def floor_at(self, x: float, hint: float = 0) -> int:
        """
        Erste begehbare Oberflaeche ab `hint` abwaerts (Fels mit Luft darueber).

        Der Hinweis dient dazu, ein Sims zu ueberspringen und den Boden
        darunter zu treffen. Liegt er versehentlich *unter* dem Boden,
        findet die Suche nichts mehr - und lieferte frueher die unterste
        Raumzeile zurueck, also mitten im Fels. Beim Ausbau des Hains
        passierte das gleich siebenmal.

        Ein unerfuellbarer Hinweis ist immer ein Versehen. Also wird er in
        dem Fall verworfen und von oben gesucht, statt etwas an eine
        Stelle zu setzen, die nachweislich falsch ist.
        """
        # Schraegen zaehlen mit: auf einer Rampe steht man genauso wie auf
        # Fels, und wer das vergisst, setzt Gegner ueber Rampen ins Leere.
        begehbar = (SOLID, PLATFORM, SLOPE_UP, SLOPE_DOWN,
                    UP_LOW, UP_HIGH, DOWN_HIGH, DOWN_LOW)
        xi = max(0, min(self.w - 1, int(x)))

        def frei(y: int, kopf: int) -> bool:
            return all(self.grid[y - k][xi] == AIR
                       for k in range(1, kopf + 1) if y - k >= 0)

        # Erst mit Kopffreiheit suchen, dann ohne. Eine Flaeche, ueber der
        # kein Platz zum Stehen ist, ist keine Standflaeche - da nuetzt es
        # nichts, dass Fels und Luft aufeinandertreffen.
        for kopf in (3, 1):
            for start in (max(1, int(hint)), 1):
                for y in range(start, self.h):
                    if self.grid[y][xi] in begehbar and frei(y, kopf):
                        return y
        return self.h - 1

    def pickup_on(self, kind: str, pid: str, x: float, hint: float = 0) -> "Room":
        """Ein Fundstueck auf dem Boden - eine Kachel ueber der Standflaeche."""
        return self.pickup(kind, pid, x, self.floor_at(x, hint))

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
            "backdrop": self.backdrop,
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
    """
    Der erste Raum: eine Terrasse, eine Mulde, ein Aufstieg.

    Drei Abschnitte, jeder mit einer Aufgabe. Oben links kommt man an -
    flach, hell, mit der Bank; hier lernt man Laufen und Springen. In der
    Mulde liegt der erste Fund unter dem Weg, man muss also hinunter. Und
    rechts steigt es zur Tuer, mit der ersten Stelle, an der ein Sprung
    nicht optional ist.
    """
    r = Room("A1", "DER ERSTE TON", "hain", 60, 24)
    r.border()

    boden = r.profil([(0, 16), (17, 16), (23, 20), (34, 20), (39, 17),
                      (43, 14), (59, 14)], rauheit=0.55, seed=3)
    # Kopfhoehe: die Terrasse ist offen, die Mulde ist ein Kessel, der
    # Aufstieg zur Tuer wird eng. Der Raum atmet, statt gleich hoch zu sein.
    kopf = r.profil([(0, 11), (14, 12), (24, 15), (33, 14), (41, 8),
                     (52, 9), (59, 10)], rauheit=0.45, seed=7)
    r.hoehle(1, 59, boden, kopf, seed=5, zacken=0.10)

    r.ramp(17, 17, 3, 1)
    r.ramp(35, 19, 4, -1)

    # Der einzige Absatz, den man nicht umgehen kann - dafuer liegt die
    # Plattform da.
    r.platform(39, 12, 4)

    r.side_door("R", "right", "A2", "L", hint=6)
    r.spawn_on("start", 8, 6, 1)
    r.bench_on(11, 6)

    r.pickup_on("kern", "leier", 29, 14)
    r.pickup_on("equipment", "mantel", 15, 10)

    # Ein Gegner im ersten Raum, unten in der Mulde. Mehr braucht es
    # nicht: hier lernt man, dass es Gegner gibt.
    r.enemy_on("gabelmaus", 28, 15, patrol=4)

    r.crystal_on(24, 6, 2)
    r.crystal_on(50, 6, 1)
    r.scatter_decor(11, 15)

    r.note_on(16, 6, "HIER SANG DIE WELT SICH SELBST. "
                     "JETZT HAELT SIE NUR NOCH DEN ATEM AN.")
    r.note_on(46, 6, "DREI INSTRUMENTE LAGEN IM HAIN. "
                     "NUR EINES WAR NOCH GESTIMMT.")
    return r


def room_A2() -> Room:
    """
    Die Lichtung: der Knotenpunkt des Hains.

    Vier Wege gehen ab, also muss der Raum uebersichtlich bleiben. Der
    Boden ist eine lange, sanfte Senke, die Decke oeffnet sich ueber der
    Mitte zur Halle und schliesst sich nach rechts zum Kamin.
    """
    r = Room("A2", "LICHTUNG DER STUMMEN VOEGEL", "hain", 72, 34)
    r.border()

    boden = r.profil([(0, 25), (14, 27), (30, 28), (46, 27), (58, 26),
                      (71, 25)], rauheit=0.6, seed=11)
    kopf = r.profil([(0, 10), (12, 13), (26, 18), (40, 16), (48, 10),
                     (60, 22), (71, 24)], rauheit=0.45, seed=13)
    r.hoehle(1, 71, boden, kopf, seed=17, zacken=0.10)

    # Der Kamin nach oben rechts wird freigeraeumt und gefasst.
    r.carve(46, 3, 22, 22)
    r.fill(44, 3, 2, 22)
    r.fill(68, 3, 3, 22)

    # Links: zwei Simse als Aussicht ueber die Lichtung.
    r.ledge(8, 23, 7, 2)
    r.platform(17, 20, 5)

    # Rechts: die Sprossen des Kamins. Drei Kacheln Abstand, solange sie
    # noch nichts kann - der Weg nach oben selbst braucht den Fluegelschlag.
    r.ledge(47, 22, 8, 2)
    r.platform(56, 19, 6)
    r.platform(48, 15, 6)
    r.platform(57, 11, 6)
    r.platform(49, 7, 6)

    # Und eine Stelle, an der man springen muss statt zu laufen.
    r.dornengrube(33, 6, 3, boden)

    r.side_door("L", "left", "A1", "R", hint=6)
    r.side_door("R", "right", "A3", "L", hint=6)
    r.shaft_door("U", 51, 5, "up", "B1", "N", requires="fluegelschlag")
    r.spawn_on("U", 53, 5, 1)
    r.shaft_door("D", 20, 4, "down", "A5", "N")
    r.spawn_on("D", 25, 14, 1)

    r.pickup("kern", "trommel", 12, 21)
    r.pickup("equipment", "cape", 20, 18)

    r.enemy_on("stilleschreiter", 40, 14, patrol=6)
    r.enemy("klangmotte", 28, 20)
    r.enemy_on("gabelmaus", 60, 14, patrol=5)

    r.crystal_on(6, 14, 2)
    r.crystal_on(38, 14, 1)
    r.scatter_decor(24, 14)

    r.note_on(10, 14, "WER SICH WEIT OEFFNET, KLINGT NACH ALLEN SEITEN - "
                      "UND NICHTS DAVON KOMMT AN.")
    r.note(20, 18, "DIE TROMMEL SCHLAEGT DEN GRUNDTON. "
                   "WAS DEN GRUNDTON HAELT, HAELT DIE WELT.")
    r.note(50, 22, "OBEN LIEGT DIE KATHEDRALE. "
                   "OHNE FLUEGEL KOMMST DU NICHT HINAUF.")
    return r


def room_A3() -> Room:
    """
    Der Wurzelgang: eine Treppe abwaerts und wieder hinauf.

    Der Raum hat genau eine Form - ein V - und alles darin dient ihr.
    Unten am Grund ist das Loch in den Untergrund, oben rechts liegt der
    Fluegelschlag. Man muss also durch die Senke hindurch.
    """
    r = Room("A3", "WURZELGANG DER ECHOS", "hain", 64, 28)
    r.border()

    boden = r.profil([(0, 15), (10, 16), (20, 21), (30, 23), (40, 22),
                      (48, 18), (56, 15), (63, 14)], rauheit=0.7, seed=23)
    kopf = r.profil([(0, 9), (12, 12), (26, 15), (38, 13), (50, 9),
                     (63, 8)], rauheit=0.45, seed=29)
    r.hoehle(1, 63, boden, kopf, seed=31, zacken=0.12)

    # Der Weg hinauf nach rechts: drei Absaetze, jeder in Sprungweite.
    r.ledge(43, 19, 6, 2)
    r.platform(50, 16, 5)
    r.ledge(54, 13, 8, 2)

    # Und zwei Dornengruben im Abstieg - die erste ist schmal, die zweite
    # verlangt den Absatz darueber.
    r.dornengrube(14, 4, 3, boden)
    r.dornengrube(35, 6, 3, boden)
    r.platform(35, 18, 5)

    r.side_door("L", "left", "A2", "R", hint=6)
    r.side_door("R", "right", "A4", "L", hint=6)
    r.shaft_door("T", 25, 3, "down", "A7", "N")
    r.spawn_on("T", 22, 16, 1)

    r.pickup_on("kern", "floete", 30, 16)
    r.pickup("ability", "fluegelschlag", 58, 12)

    r.enemy_on("gabelmaus", 18, 12, patrol=5)
    r.enemy_on("dissonanzknospe", 44, 14)
    r.enemy("klangmotte", 48, 12)

    r.crystal_on(8, 8, 1)
    r.crystal_on(46, 10, 2)
    r.scatter_decor(31, 16)

    r.note_on(10, 8, "DIE FLOETE TRAEGT DEN REINEN TON. "
                     "SIE STICHT, WO DIE LEIER STREICHELT.")
    r.note(58, 12, "EIN FLUEGELSCHLAG BLIEB IN DER LUFT HAENGEN, "
                   "ALS DER VOGEL SCHON LANGE FORT WAR.")
    return r


def room_A4() -> Room:
    """
    Der stille Raum vor dem Tempel.

    Ein Gebiet, in dem jeder Gang irgendwohin fuehrt, fuehlt sich an wie
    ein Schaltplan. Hier ist nichts los: eine Bank, ein Fund, und ganz
    hinten ein Loch im Boden, aus dem kalte Luft kommt. Erst dahinter
    faengt der Tempel an.
    """
    r = Room("A4", "DIE STILLE KANZEL", "hain", 40, 22)
    r.border()

    boden = r.profil([(0, 15), (12, 15), (20, 14), (28, 12), (39, 11)],
                     rauheit=0.4, seed=37)
    # Nach hinten wird es niedriger und enger: der Raum zieht sich
    # zusammen, statt einfach aufzuhoeren.
    kopf = r.profil([(0, 10), (14, 11), (26, 8), (39, 5)], rauheit=0.45, seed=41)
    r.hoehle(1, 39, boden, kopf, seed=43, zacken=0.14)

    r.ramp(19, 14, 3, 1)
    r.ramp(25, 12, 3, 1)

    r.side_door("L", "left", "A3", "R", hint=6)
    r.bench_on(9, 6)

    r.pickup_on("siegel", "scherbenherz", 34, 6)
    # Hinter der Kanzel geht der Gang weiter - in den Tempel.
    r.side_door("R", "right", "A10", "L", hint=6)

    r.crystal_on(6, 6, 2)
    r.crystal_on(16, 6, 1)
    r.scatter_decor(13, 8)

    r.note_on(13, 8, "HIER SETZTE SICH JEMAND HIN UND HOERTE ZU, "
                     "BIS NICHTS MEHR KAM.")
    r.note(34, 10, "EIN HERZ AUS SCHERBEN SCHLAEGT NICHT LEISER. "
                   "ES SCHLAEGT NUR AN MEHR STELLEN.")
    return r


def room_A10() -> Room:
    """
    DER SCHATTENTEMPEL - die Arena des ersten Bosses.

    Er gehoert zum Hain und sieht doch nicht danach aus: kein Himmel,
    kein Gras, keine Baeume. Statt gewachsenem Fels stehen hier gesetzte
    Saeulen, der Boden ist eben, die Decke gerade - jemand hat das
    gebaut, und zwar lange bevor der Hain schlief.

    Eine Arena muss lesbar sein. Es gibt darum genau eine Ebene, zwei
    Saeulen zum Ausweichen und keinen einzigen Dorn: was hier wehtut,
    kommt vom Boss, und nichts soll davon ablenken.
    """
    r = Room("A10", "DER SCHATTENTEMPEL", "hain", 52, 24)
    r.border(2)
    r.fill(2, 19, 48, 5)                    # eine ebene Flaeche, sonst nichts
    r.fill(2, 2, 48, 4)
    # Dunkel, aber lesbar: in einer Arena muss man sehen, was auf einen
    # zukommt. Finsternis gehoert vor den Kampf, nicht hinein.
    r.dark = 0.16
    # Gebaut, nicht gewachsen - und ohne Himmel. Der Tempel hat eine
    # eigene Kulisse, die es als Gebiet gar nicht gibt: hinten steht eine
    # Wand, nicht die Ferne. Kachelsatz und Musik bleiben beim Hain.
    r.backdrop = "tempel"

    # Zwei Saeulenpaare. Sie stehen im Weg, nicht auf dem Weg: man kann
    # dazwischen hindurch, aber ein Schlag geht daran vorbei.
    for x in (14, 36):
        r.fill(x, 6, 2, 5)
        r.fill(x - 1, 5, 4, 1)
        r.fill(x - 1, 11, 4, 1)

    # Der Eingang liegt auf derselben Ebene wie die Arena. Ein Schacht
    # waere hier falsch: aus einer Arena muss man jederzeit
    # herauslaufen koennen, ohne erst klettern zu muessen.
    r.side_door("L", "left", "A4", "R", hint=8)
    r.bench_on(46, 8)

    r.set_boss("auftakt", 34, 19, (4, 6, 44, 13))

    r.crystal_on(20, 8, 1)
    r.crystal_on(30, 8, 1)

    r.note_on(12, 8, "GEBAUT, ALS DER HAIN NOCH SANG. "
                     "WOFUER, STEHT NIRGENDS.")
    r.note_on(44, 8, "EINER MUSSTE DEN TAKT HALTEN, "
                     "DAMIT DIE ANDEREN SPIELEN KONNTEN.")
    return r


def room_A5() -> Room:
    """
    Unter der Lichtung: niedrig, dunkel, voller Wurzeln.

    Der Hain war bisher ein Gang mit Aussicht. Ein Gebiet wird aber erst
    gross, wenn es unter sich noch etwas hat - und wenn dieses Etwas
    anders aussieht. Hier ist die Kopfhoehe die halbe: man geht gebueckt,
    und das sieht man dem Raum an.
    """
    r = Room("A5", "UNTER DEN WURZELN", "hain", 56, 20)
    r.border()

    boden = r.profil([(0, 15), (12, 14), (24, 16), (36, 15), (55, 14)],
                     rauheit=0.5, seed=47)
    kopf = r.profil([(0, 11), (8, 6), (18, 5), (26, 9), (34, 5), (44, 5),
                     (55, 8)], rauheit=0.45, seed=53)
    r.hoehle(1, 55, boden, kopf, seed=59, zacken=0.16)

    r.dark = 0.16

    # Der Schacht aus der Lichtung schlaegt einen Alkoven in die niedrige
    # Decke - das Loch, durch das man gefallen ist, und das Einzige hier
    # unten, wo Licht hereinkommt. Der Aufstieg findet ganz darin statt:
    # der uebrige Raum ist zu niedrig fuer eine Treppe, und Sprossen
    # buendig unter der Decke sind keine.
    r.carve(15, 1, 12, 14)
    r.platform(15, 11, 6)
    r.platform(20, 7, 6)
    # Die oberste Sprosse liegt genau unter der Oeffnung: nur dort hat die
    # Figur die drei Kacheln Kopffreiheit, die sie zum Stehen braucht.
    r.platform(20, 3, 4)

    r.shaft_door("N", 20, 4, "up", "A2", "D", requires="fluegelschlag")
    r.spawn_on("N", 24, 6, 1)
    r.side_door("R", "right", "A6", "L", hint=6)

    r.pickup_on("siegel", "federstaub", 44, 10)

    r.enemy_on("stilleschreiter", 32, 12, patrol=5)
    r.enemy_on("gabelmaus", 46, 12, patrol=6)

    r.crystal_on(6, 12, 1)
    r.crystal_on(28, 12, 2)
    r.scatter_decor(38, 12)

    r.note_on(9, 12, "WAS OBEN LICHTUNG HEISST, HEISST HIER UNTEN DECKE.")
    r.note_on(50, 12, "DIE WURZELN HABEN DEN TON BEHALTEN. "
                      "SIE GEBEN IHN NUR NICHT MEHR HERAUS.")
    return r


def room_A6() -> Room:
    """
    Der Tropfsteingang: ein Weg, mehr nicht - und genau darum wichtig.

    Zwischen zwei Ereignissen muss Weg liegen, sonst reiht sich alles
    aneinander wie Perlen. Dieser hier ist eng, tropft, und hat in der
    Mitte die erste Stelle im Spiel, an der man von oben und von unten
    zugleich aufpassen muss.
    """
    r = Room("A6", "DER TROPFSTEINGANG", "hain", 48, 22)
    r.border()

    boden = r.profil([(0, 16), (10, 17), (20, 16), (30, 17), (40, 15),
                      (47, 15)], rauheit=0.5, seed=61)
    kopf = r.profil([(0, 9), (8, 7), (16, 12), (24, 6), (32, 11), (40, 7),
                     (47, 9)], rauheit=0.45, seed=67)
    r.hoehle(1, 47, boden, kopf, seed=71, zacken=0.20)

    r.dark = 0.10

    # Die Stelle: eine Grube mit Dornen, darueber Dornen an der Decke.
    # Also nicht zu hoch springen und nicht zu kurz - der einzige Ort im
    # Hain, an dem die Sprunghoehe selbst zaehlt.
    r.dornengrube(20, 7, 3, boden)
    r.platform(22, 13, 4)
    r.deckendornen(24, 3)

    r.dornengrube(36, 4, 3, boden)

    r.side_door("L", "left", "A5", "R", hint=6)
    r.side_door("R", "right", "A7", "L", hint=6)

    r.pickup_on("equipment", "offene_fassung", 42, 10)

    r.enemy_on("dissonanzknospe", 14, 14)
    r.enemy_on("gabelmaus", 31, 14, patrol=4)

    r.crystal_on(6, 14, 1)
    r.crystal_on(44, 14, 2)
    r.scatter_decor(12, 14)

    r.note_on(9, 14, "TROPFEN SIND DER LANGSAMSTE TAKT, DEN ES GIBT. "
                     "UND DER EINZIGE, DER NIE AUSSETZT.")
    return r


def room_A7() -> Room:
    """
    Der gefallene Stamm: der Knoten des ganzen Gebiets.

    Vier Wege treffen sich hier. Der Aufstieg ist bewusst ohne jede
    Faehigkeit begehbar - er ist der einzige freie Weg aus dem Untergrund
    heraus, und ohne ihn waere das Loch in A3 eine Falle statt einer
    Abkuerzung. Die Sprossen liegen darum durchgehend unter vier Kacheln.
    """
    r = Room("A7", "DER GEFALLENE STAMM", "hain", 36, 44)
    r.border()

    boden = r.profil([(0, 40), (12, 41), (24, 40), (35, 41)], rauheit=0.4, seed=73)
    kopf = r.profil([(0, 36), (18, 38), (35, 36)], rauheit=0.45, seed=79)
    r.hoehle(1, 35, boden, kopf, seed=83)
    # Der Schacht selbst: ein hoher Hohlraum ueber dem Grund.
    r.carve(2, 3, 32, 34)

    for i, (x, y, w) in enumerate([(3, 36, 10), (16, 33, 9), (5, 29, 9),
                                   (18, 26, 8), (6, 22, 8), (17, 18, 9),
                                   (4, 14, 8), (16, 10, 10), (17, 6, 8)]):
        if i % 3 == 2:
            r.platform(x, y, w)
        else:
            r.ledge(x, y, w, 2)

    # Wer faellt, faellt weit - also liegt unten etwas, das wehtut. Aber
    # nicht unter dem Aufstieg und nicht vor einer Tuer: der erste Versuch
    # legte sie genau auf den Ankunftspunkt aus dem Tropfsteingang.
    r.spikes(14, 39, 6)

    r.shaft_door("N", 18, 3, "up", "A3", "T")
    r.spawn_on("N", 20, 6, 1)
    r.side_door("L", "left", "A6", "R", hint=36)
    r.side_door("R", "right", "A8", "L", hint=36)
    r.bench_on(10, 36)

    r.pickup("siegel", "pilgerstab", 8, 21)

    r.enemy("klangmotte", 20, 30)
    r.enemy_on("stilleschreiter", 8, 28, patrol=3)
    r.enemy("echoscherbe", 21, 15)

    r.crystal_on(22, 36, 2)
    r.scatter_decor(15, 36)

    r.note_on(14, 36, "ER FIEL, ALS DER LETZTE TON AUSGING. "
                      "SEITDEM LIEGT ER DA UND TRAEGT DEN WEG.")
    r.note(20, 10, "OBEN IST DER WURZELGANG. "
                   "DER STAMM TRAEGT DICH HIN, WENN DU IHM FOLGST.")
    return r


def room_A8() -> Room:
    """
    Weit, offen, voller Motten - der Gegenentwurf zum Tropfsteingang.

    Ein Gebiet braucht auch einmal Platz. Hier ist der Boden fast eben,
    die Decke hoch, und die Gefahr kommt aus der Luft statt aus dem Weg.
    """
    r = Room("A8", "NEST DER KLANGMOTTEN", "hain", 80, 32)
    r.border()

    boden = r.profil([(0, 26), (18, 27), (36, 26), (54, 27), (79, 26)],
                     rauheit=0.5, seed=89)
    kopf = r.profil([(0, 12), (16, 20), (34, 22), (50, 21), (64, 17),
                     (79, 12)], rauheit=0.45, seed=97)
    r.hoehle(1, 79, boden, kopf, seed=101, zacken=0.10)

    r.ledge(14, 22, 7, 2)
    r.platform(28, 19, 6)
    r.ledge(40, 21, 8, 2)
    r.ledge(64, 22, 8, 2)

    # Der Aufstieg zum Schacht - erst mit dem Fluegelschlag zu schaffen,
    # aber lange vorher zu sehen.
    r.ledge(50, 20, 8, 2)
    r.platform(52, 15, 12)
    r.ledge(46, 10, 8, 2)

    r.dornengrube(22, 6, 3, boden)
    r.dornengrube(68, 5, 3, boden)

    r.side_door("L", "left", "A7", "R", hint=6)
    r.shaft_door("U", 54, 3, "up", "A9", "N", requires="fluegelschlag")
    r.platform(54, 5, 3)
    r.spawn_on("U", 55, 4, 1)

    r.pickup_on("klinge", "gezackt", 44, 14)

    r.enemy("klangmotte", 20, 14)
    r.enemy("klangmotte", 34, 11)
    r.enemy("klangmotte", 50, 9)
    r.enemy_on("gabelmaus", 32, 20, patrol=8)
    r.enemy_on("stilleschreiter", 70, 20, patrol=6)

    r.crystal_on(10, 20, 2)
    r.crystal_on(38, 20, 1)
    r.crystal_on(74, 20, 2)
    r.scatter_decor(46, 20)

    r.note_on(12, 20, "SIE FLIEGEN NOCH IMMER ZUM LICHT. "
                      "ES IST NUR KEINES MEHR DA.")
    r.note(44, 20, "EINE KLINGE AUS SCHALL SCHNEIDET NICHT. "
                   "SIE BRINGT ZUM KLINGEN, BIS ETWAS BRICHT.")
    return r


def room_A9() -> Room:
    """
    Klein, hoch oben, nur mit Fluegelschlag zu erreichen.

    Der Lohn dafuer, dass man mit einer neuen Faehigkeit zurueckkommt und
    nachsieht, wo sie etwas oeffnet.
    """
    r = Room("A9", "DIE VERGESSENE BANK", "hain", 28, 16)
    r.border()

    boden = r.profil([(0, 11), (14, 11), (27, 11)], rauheit=0.35, seed=103)
    kopf = r.profil([(0, 5), (10, 8), (20, 7), (27, 5)], rauheit=0.45, seed=107)
    r.hoehle(1, 27, boden, kopf, seed=109, zacken=0.14)

    r.shaft_door("N", 12, 3, "down", "A8", "U")
    r.spawn_on("N", 9, 6, 1)
    r.bench_on(20, 6)

    r.pickup_on("kern", "metronom", 5, 6)

    r.crystal_on(23, 6, 2)
    r.scatter_decor(8, 6)

    r.note_on(17, 6, "WER HIERHER FINDET, HAT SCHON GELERNT ZU FLIEGEN. "
                     "SETZ DICH TROTZDEM.")
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

    r.pickup("siegel", "nachhall", 34, 31)

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
    # Ganz oben kehrt der Aufstieg um: eine Stufe zurueck unter die Pfeifen.
    r.platform(40, 7, 4)

    r.spikes(15, 29, 5)
    r.spikes(31, 29, 5)

    r.shaft_door("N", 2, 4, "down", "B1", "U")
    r.spawn_on("N", 9, 26, 1)

    r.pickup("ability", "klangschritt", 42, 9)
    r.pickup("equipment", "enge_fassung", 41, 6)
    r.pickup("siegel", "stille", 6, 26)
    r.pickup("equipment", "pfeifenharnisch", 22, 19)
    r.pickup("kern", "orgelpfeife", 46, 12)

    r.enemy("echoscherbe", 16, 22)
    r.enemy("echoscherbe", 33, 14)
    r.enemy_on("dissonanzknospe", 25, 26)
    r.enemy("klangmotte", 42, 8)

    r.scatter_decor(55, 10, kinds=("crystal",))
    r.note_on(20, 26, "JEDE PFEIFE KENNT NUR EINEN TON. "
                      "ZUSAMMEN KENNEN SIE ALLE.")
    r.note(42, 12, "WER DEN KLANG IN DER WAND HOERT, "
                   "KANN AUF IHM STEHEN.")
    r.note(43, 6, "EINE PFEIFE MIT EINER EINZIGEN OEFFNUNG "
                  "TRAEGT WEITER ALS EIN GANZER CHOR.")
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

    r.pickup("siegel", "bruchstein", 74, 15)
    r.pickup("equipment", "chorpanzer", 12, 27)

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
    r.pickup("siegel", "dauerton", 12, 17)
    r.pickup("siegel", "bleisiegel", 36, 15)

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

    r.pickup("equipment", "schlagfassung", 48, 10)
    r.pickup("siegel", "hohlklang", 6, 11)
    r.pickup("kern", "glocke", 34, 14)
    r.pickup("siegel", "kreiselsiegel", 56, 14)

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

    r.pickup("klinge", "glas", 38, 8)
    r.pickup("siegel", "taubes_ohr", 12, 32)

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

    r.pickup("equipment", "gerissenes_gewand", 55, 17)
    r.pickup("siegel", "windschliff", 46, 10)
    r.pickup("equipment", "flimmerhemd", 20, 11)
    r.pickup("siegel", "nadelsiegel", 68, 21)

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
    r.note_on(58, 7, "WER NUR NOCH IN FETZEN ZUSAMMENHAENGT, "
                     "IST SCHNELL. UND KURZ.")
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
    room_A1, room_A2, room_A3, room_A4, room_A5,
    room_A6, room_A7, room_A8, room_A9, room_A10,
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
        # Zum Schluss, wenn Tueren, Simse und Deko stehen: Boden und Decke
        # werden von ihren Treppenstufen befreit.
        r.soften()
        r.deckenglaetten()
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
