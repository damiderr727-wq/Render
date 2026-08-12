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


def _treppenfrei(hoehen: dict[int, int], x0: int, x1: int) -> dict[int, int]:
    """
    Begradigt ein Deckenprofil, damit daraus eine Linie werden kann.

    Zwei Bedingungen, beide notwendig, damit `Room.deckenglaetten` an
    einer Stufe ueberhaupt ein Paar Schraegkacheln setzen darf: der
    Sprung zwischen zwei Spalten ist hoechstens eine Kachel, und links
    wie rechts der Stufe steht ein Lauf von mindestens zwei Spalten auf
    gleicher Hoehe. Wird das vorher nicht erzwungen, bleibt jede zweite
    Stufe stehen - und eine halb geglaettete Decke sieht schlechter aus
    als eine ehrliche Treppe.

    Begradigt wird ausschliesslich nach oben (kleinere Werte gewinnen).
    Das Ergebnis ist die untere Huellkurve des Rohprofils: sie liegt
    nirgends tiefer als das Original, also nimmt die Glaettung nirgends
    Kopfhoehe weg. Was sie kostet, ist etwas Fels - das ist zu
    verschmerzen.
    """
    d = dict(hoehen)
    for x in range(x0 + 1, x1):                     # von links
        d[x] = min(d[x], d[x - 1] + 1)
    for x in range(x1 - 2, x0 - 1, -1):             # und zurueck
        d[x] = min(d[x], d[x + 1] + 1)

    # Und dann in Stufen von zwei Spalten legen.
    #
    # Ein Schraegenpaar braucht links und rechts je zwei gleiche Spalten,
    # sonst passt es nicht. Eine Decke, die Spalte fuer Spalte um eine
    # Kachel faellt, hat aber ueberall Laeufe der Laenge eins - und blieb
    # deshalb eine Treppe, obwohl kein einziger Sprung groesser als eine
    # Kachel war. Das war der Rest, der nach der Begradigung stehen blieb.
    #
    # Die Decke darf jetzt hoechstens eine Kachel pro *zwei* Spalten
    # fallen. Das ist genau die Steigung, die ein Schraegenpaar darstellt,
    # und damit ist jede Stufe im Raum eine, die sich glaetten laesst.
    paare = [(k, min(d[k], d[k + 1] if k + 1 < x1 else d[k]))
             for k in range(x0, x1, 2)]
    for i in range(1, len(paare)):
        k, h = paare[i]
        paare[i] = (k, min(h, paare[i - 1][1] + 1))
    for i in range(len(paare) - 2, -1, -1):
        k, h = paare[i]
        paare[i] = (k, min(h, paare[i + 1][1] + 1))
    for k, h in paare:
        d[k] = h
        if k + 1 < x1:
            d[k + 1] = h

    # Einzelne Spalten auf eigener Hoehe verbreitern, wieder nach oben.
    # Eine Spalte, die allein steht, ist ein Lauf der Laenge eins - und an
    # so einem Lauf kann die Glaettung kein Schraegenpaar setzen, weil
    # links und rechts davon je zwei gleiche Spalten stehen muessen. Also
    # weg damit, in beide Richtungen: eine einzelne Kerbe wird verbreitert,
    # ein einzelner Zapfen abgetragen.
    for _ in range(4):
        ruhig = True
        for x in range(x0 + 1, x1 - 1):
            if d[x] < d[x - 1] and d[x] < d[x + 1]:
                d[x - 1 if d[x - 1] <= d[x + 1] else x + 1] = d[x]
                ruhig = False
            elif d[x] > d[x - 1] and d[x] > d[x + 1]:
                d[x] = max(d[x - 1], d[x + 1])
                ruhig = False
        if ruhig:
            break
    return d


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
        # Wo `hoehle` die Decke hingelegt hat, Spalte fuer Spalte: die
        # oberste Luftzeile. Die Glaettung braucht das, weil sie die
        # Deckenlinie sonst aus dem fertigen Gitter zurueckrechnen muesste
        # - und dann haelt sie jeden Tropfstein fuer die Decke.
        self.deckenprofil: dict[int, int] = {}
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

    def schacht(self, x: int, y: int, w: int, h: int, seed: int = 0,
                wand: int = 2) -> "Room":
        """
        Ein senkrechter Aufstieg mit gewachsenen Waenden.

        `carve` schneidet ein Rechteck. Ein Rechteck ist genau das, was
        man einem Raum ansieht: zwei kerzengerade Waende ueber zwanzig
        Kacheln, links und rechts gleich weit weg. Hier wird stattdessen
        gefasst und dann wieder eingebeult - die Breite atmet ueber die
        Hoehe, links und rechts unabhaengig voneinander.

        Die schmalste Stelle bleibt breit genug zum Springen; eingebeult
        wird nur, wo Platz dafuer ist.
        """
        self.fill(x - wand, y, w + wand * 2, h)
        self.carve(x, y, w, h)
        for j in range(y, y + h):
            t = (j - y) / max(1, h - 1)
            for seite in (0, 1):
                # Zwei Wellen ungleicher Laenge: die Wand darf nirgends
                # eine Weile geradeaus laufen.
                tiefe = (math.sin(t * 7.0 + seed + seite * 2.1) * 0.5 + 0.5) \
                    * (math.sin(t * 2.3 + seed * 0.7 + seite) * 0.5 + 0.7)
                d = int(tiefe * min(3, (w - 5) / 2))
                if d <= 0:
                    continue
                self.fill(x + (0 if seite == 0 else w - d), j, d, 1)
        return self

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

    def simse_formen(self, seed: int = 0) -> "Room":
        """
        Freistehende Simse verlieren ihre Rechteckform.

        `soften` fasst nur gewachsenen Boden an - eine Saeule, die bis
        zum unteren Rand durchsteht. Alles, was in der Luft steht, blieb
        deshalb genau das, was `ledge()` gesetzt hat: ein Rechteck. Und
        ein Rechteck in einer gewachsenen Landschaft sticht sofort
        heraus, egal wie fein Boden und Decke ringsum verlaufen.

        Zwei Griffe, beide billig:

          Die Enden der Oberkante werden angerampt. Damit laeuft der
          Sims aus, statt abzubrechen - und man kann von der Seite
          heraufgehen statt heraufzuspringen.

          Die unteren Ecken werden weggenommen. Das aendert am Laufen
          nichts (dort steht ohnehin niemand), bricht aber die zweite
          gerade Kante, an der man den Block erkennt.

        Nicht jeder Sims bekommt beides: gleiche Behandlung an allen
        Simsen ergibt wieder ein Muster, nur ein anderes.
        """
        for y in range(1, self.h - 2):
            x = 0
            while x < self.w:
                if self.grid[y][x] != SOLID or self.grid[y - 1][x] != AIR:
                    x += 1
                    continue
                start = x
                while (x < self.w and self.grid[y][x] == SOLID
                       and self.grid[y - 1][x] == AIR):
                    x += 1
                laenge = x - start

                # Gewachsener Boden gehoert `soften`, nicht hierher.
                gewachsen = all(self.grid[j][start] == SOLID
                                for j in range(y, self.h))
                if gewachsen or laenge < 4:
                    continue

                if hash01(start * 3, seed + 1) < 0.82:
                    self.set(start, y, SLOPE_UP)
                if hash01(x * 5, seed + 2) < 0.82:
                    self.set(x - 1, y, SLOPE_DOWN)

                # Untere Ecken abtragen, wo darunter Luft steht.
                for ex, wuerfel in ((start, 7), (x - 1, 11)):
                    if hash01(ex, seed + wuerfel) < 0.7:
                        continue
                    for j in range(y + 1, min(self.h - 1, y + 3)):
                        if self.grid[j][ex] == SOLID and self.grid[j + 1][ex] == AIR:
                            self.set(ex, j, AIR)
                            break
        return self

    def kamin(self, x: int, w: int, y_oben: int, y_unten: int,
              seed: int = 0, tuer_x: int | None = None,
              abstand: int = 3) -> "Room":
        """
        Ein Kamin: senkrechter Schacht mit Sprossen darin.

        Fuenf Raeume hintereinander hatten denselben Fehler - eine Tuer
        in der Decke und darunter Absaetze, die irgendwo im Fels steckten
        oder zu weit auseinander lagen. Das ist keine Frage des
        Geschmacks, sondern eine Rechnung: die Figur braucht drei Kacheln
        Kopffreiheit zum Stehen und schafft vier Kacheln Hoehe pro Sprung.
        Wer das jedes Mal von Hand hinschreibt, macht es jedes Mal anders
        falsch.

        Der Schacht bekommt eingebeulte Waende (kein Rechteck), die
        Sprossen sitzen abwechselnd links und rechts, und die oberste
        liegt genau unter der Oeffnung - nur dort steht die Figur mit
        genug Luft ueber dem Kopf.
        """
        # Nur aushoehlen, nicht einfassen. `schacht` legt Fels um seinen
        # Gang - richtig fuer einen Aufstieg durch gewachsenes Gestein,
        # falsch fuer einen Kamin, der in einer Kammer steht: dort steht
        # danach eine Wand quer im Raum, und alles dahinter ist
        # abgeschnitten. Ueber der Kammerdecke ist ohnehin Fels; wer dort
        # aushoehlt, bekommt seine Waende geschenkt.
        self.carve(x, y_oben, w, y_unten - y_oben)
        # Beulen in den Waenden - aber einzeln, hoechstens eine Kachel
        # tief, und nur im oberen Teil.
        #
        # Ein Zwischenstand hat sie ueber zwei Kacheln Tiefe und ohne
        # Luecken gesetzt. Aus den Beulen wurde eine durchgehende Wand,
        # und die stand ausgerechnet unten, wo der Kamin zum Raum hin
        # offen sein muss: der Aufstieg war zugemauert, und man kam
        # nicht einmal an die unterste Sprosse.
        for j in range(y_oben, y_unten):
            t = (j - y_oben) / max(1, y_unten - y_oben - 1)
            if t < 0.35:
                continue
            for seite in (0, 1):
                if hash01(j * 3 + seite * 7, seed + 11) < 0.55:
                    continue
                self.fill(x + (0 if seite == 0 else w - 1), j, 1, 1)

        tuer_x = x + (w - 4) // 2 if tuer_x is None else tuer_x
        breite = max(4, min(6, w - 4))

        # Die Sprossen werden gleichmaessig ueber die Hoehe verteilt,
        # nicht von unten abgezaehlt. Zaehlt man ab, bleibt oben ein
        # Rest - und wenn der groesser ist als ein Sprung, endet der
        # Kamin drei Kacheln unter seiner eigenen Tuer.
        # Die oberste Sprosse liegt dicht unter der Oeffnung. Bleibt
        # dort ein voller Sprung Abstand, kommt man ohne Faehigkeit
        # nicht hindurch - und eine Kammer, in die man faellt, waere
        # damit eine Falle statt eines Endes.
        oberste = y_oben + 1
        spanne = y_unten - oberste
        if spanne <= 0:
            return self
        anzahl = max(1, int(math.ceil(spanne / abstand)))
        for k in range(1, anzahl + 1):
            y = int(round(y_unten - spanne * k / anzahl))
            if k == anzahl:
                self.platform(tuer_x, y, min(breite, 4))
            else:
                sx = x + 1 if k % 2 else x + w - breite - 1
                self.platform(sx, y, breite)
        return self

    def nische(self, x: int, y: int, w: int, h: int, seed: int = 0) -> "Room":
        """
        Eine Nische im Fels: ausgehoehlt, mit gerundeten Ecken.

        Bisher gab es genau zwei Arten, Fels wegzunehmen - `carve`
        schneidet ein Rechteck, `schacht` einen Gang. Beides sind
        Durchgaenge. Eine Nische ist etwas anderes: eine Ausbuchtung, die
        nirgendwohin fuehrt, und genau davon lebt ein Gebiet, das
        gewachsen aussehen soll. Dort steht dann eine Bank, ein Kristall,
        eine Inschrift - oder nichts, und man geht daran vorbei und
        merkt nur, dass die Wand nicht gerade ist.
        """
        for j in range(h):
            v = j / max(1, h - 1)
            # Oben und unten schmaler, in der Mitte am weitesten.
            einzug = int(round((1 - math.sin(math.pi * v) ** 0.6) * (w / 3)))
            einzug += 1 if hash01(j, seed) > 0.72 else 0
            breite = w - einzug * 2
            if breite <= 0:
                continue
            self.carve(x + einzug, y + j, breite, 1)
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
            # Wo `hoehle` gebaut hat, steht die Deckenlinie schon fest.
            # Sie aus dem Gitter zurueckzurechnen ginge auch - nur haelt
            # so eine Suche jeden Tropfstein fuer die Decke und zerlegt
            # den Lauf, an dem die Schraege sitzen soll.
            if x in self.deckenprofil:
                d = self.deckenprofil[x]
                if 0 < d <= self.h - 2 and self.grid[d - 1][x] == SOLID:
                    unter[x] = d - 1
                continue
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
            # `unter` ist ein Zeilenindex, und Zeilen zaehlen nach unten:
            # ein *groesserer* Wert heisst, die Decke haengt tiefer. Hier
            # stand das Gegenteil, und deshalb bekam jede Stufe das Paar
            # der Gegenrichtung - die Schraegen liefen andersherum als die
            # Decke, an der sie sassen.
            #
            # Die Schraege sitzt immer in der *unteren* der beiden Zeilen;
            # darueber steht Fels.
            if hb > ha:                              # Decke faellt nach rechts
                ty, paar = hb, (CEIL_DOWN_HIGH, CEIL_DOWN_LOW)
            else:                                    # Decke steigt nach rechts
                ty, paar = ha, (CEIL_UP_LOW, CEIL_UP_HIGH)
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

        Die Decke wird dabei **treppenfrei gebaut, nicht treppenfrei
        verkleidet.**

        Vorher stand hier das Gegenteil: eine gerundete Kurve wird beim
        Runden auf ganze Kacheln zur Treppe, und an jede Stufe wurde ein
        Zapfen gehaengt, der genau so lang war wie der Sprung. Das war
        Kosmetik ueber einem Baufehler, und es hat auch nicht
        funktioniert - was man sah, waren senkrechte Bloecke in
        verschiedenen Laengen nebeneinander, also erst recht ein Regal.

        Jetzt wird das Deckenprofil vor dem Setzen begradigt: hoechstens
        eine Kachel Unterschied von Spalte zu Spalte, und keine Hoehe
        steht allein. Damit findet `deckenglaetten` an jeder Stufe ein
        Paar Schraegkacheln, das dort hinpasst, und aus der Treppe wird
        eine durchgehende Linie. Begradigt wird ausserdem immer *nach
        oben* - die Decke geht hoch, nie herunter, sonst nimmt eine
        Glaettung irgendwo die Kopfhoehe weg, die der Raum braucht.
        """
        b_roh: dict[int, int] = {}
        d_roh: dict[int, int] = {}
        for x in range(x0, x1):
            b = max(2, min(self.h - 1, int(round(boden(x)))))
            b_roh[x] = b
            d_roh[x] = max(1, int(round(b - max(3, kopfhoehe(x)))))

        decke = _treppenfrei(d_roh, x0, x1)

        hoehen: dict[int, tuple[int, int]] = {}
        for x in range(x0, x1):
            b, d = b_roh[x], decke[x]
            hoehen[x] = (b, d)
            self.deckenprofil[x] = d
            self.fill(x, b, 1, self.h - b)
            self.fill(x, 0, 1, d)

        for x in range(x0, x1):
            b, d = hoehen[x]
            luft = b - d

            # Tropfsteine bleiben - aber als Form, nicht als Fuellung
            # einer Luecke. Zwei Kacheln breit oben, eine unten: eine
            # einzelne Kachelsaeule ist kein Fels, sondern ein Strich.
            #
            # Nur wo die Decke ueber vier Spalten hinweg flach liegt.
            #
            # Zwei Gruende. Erstens bekommt eine Spalte an einer Stufe
            # Luft ueber sich und damit vom Kachelsatz eine Oberkante mit
            # Gras - Gras, das unter der Decke nach oben waechst.
            # Zweitens, und wichtiger: ein Tropfstein an einer Stufe
            # blockiert die Glaettung. Sie sieht dann nicht mehr die
            # Decke, sondern den Zapfen, der Lauf reisst an dieser Spalte
            # auseinander, und die Stufe daneben bleibt eine Stufe. So
            # blieb die halbe Decke eine Treppe, obwohl das Profil laengst
            # begradigt war.
            flach = all(hoehen.get(x + k, (0, -1))[1] == d
                        for k in (-1, 1, 2))
            if zacken and luft >= 11 and flach and hash01(x, seed) < zacken:
                laenge = min(2 + int(hash01(x, seed + 1) * 3), luft - 7)
                if laenge >= 2:
                    self.fill(x, d, 2, laenge - 1)
                    self.fill(x, d + laenge - 1, 1, 1)

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
    # Das Loch in der Mulde. Im ersten Raum ein Loch in den Boden zu
    # setzen ist Absicht: man tritt hinein, bevor man weiss, dass es
    # eines gibt, und lernt in einem Zug, dass die Welt nach unten
    # weitergeht und dass man von unten wieder heraufkommt.
    r.shaft_door("D", 27, 4, "down", "A11", "N")
    r.spawn_on("D", 33, 20, -1)
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

    # Mehr Stuetzpunkte, kleinere Abstaende: dazwischen wird weich
    # interpoliert, also ergibt jeder zusaetzliche Punkt eine Welle statt
    # einer Ecke. Mit sechs Punkten auf zweiundsiebzig Kacheln war der
    # Boden ueber weite Strecken schlicht eben.
    boden = r.profil([(0, 25), (7, 26), (14, 27), (21, 26), (27, 28),
                      (34, 29), (40, 27), (46, 27), (52, 25), (58, 26),
                      (64, 24), (71, 25)], rauheit=0.7, seed=11)
    kopf = r.profil([(0, 10), (7, 12), (12, 13), (19, 16), (26, 18),
                     (33, 17), (40, 16), (48, 10), (54, 16), (60, 22),
                     (71, 24)], rauheit=0.45, seed=13)
    r.hoehle(1, 71, boden, kopf, seed=17, zacken=0.10)

    # Der Kamin nach oben rechts. Gefasst und wieder eingebeult - als
    # ausgeschnittenes Rechteck war er die auffaelligste gerade Linie im
    # ganzen Hain.
    r.schacht(46, 3, 22, 22, seed=5, wand=2)

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
    r.kamin(7, 11, 2, 16, seed=17, tuer_x=10)
    r.shaft_door("U", 10, 4, "up", "A16", "N", requires="fluegelschlag")
    # Nicht bei x=14: dort liegt die Dornengrube dieses Raums,
    # und ein Ankunftspunkt gehoert nie neben Dornen.
    r.spawn_on("U", 11, 16, 1)
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
    r.shaft_door("D", 8, 4, "down", "A13", "U")
    r.spawn_on("D", 14, 15, 1)
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
    r.side_door("L", "left", "A14", "R", hint=6)

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
    r.shaft_door("D", 38, 4, "down", "A12", "N")
    r.spawn_on("D", 35, 15, -1)

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
    r.side_door("R", "right", "A13", "L", hint=26)
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


# ---------------------------------------------------------------------
#  Der Hain, zweiter Ausbau
#
#  Bis hierher bestand das Gebiet aus zwei Ketten: oben A1-A2-A3-A4-A10,
#  unten A5-A6-A7-A8-A9, verbunden an genau zwei Stellen. Zwei Ketten
#  sind kein Gebiet, sondern zwei Gaenge. Was in den Vorbildern ein
#  Gebiet ausmacht, ist die **Schleife**: man laeuft irgendwo hinaus,
#  kommt woanders wieder heraus und weiss ploetzlich, wie alles
#  zusammenhaengt.
#
#  Die sechs Raeume hier schliessen drei davon:
#
#    Westen   A1 faellt nach A11, von dort ueber A14 nach A5 und die
#             Oberkette wieder hinauf. Wer im ersten Raum ins Loch
#             tritt, steht nicht in einer Sackgasse.
#    Osten    A8 fuehrt nach A13 und dort hinauf nach A4 - der kurze
#             Weg zurueck zum Tempel, der sich erst mit dem
#             Fluegelschlag oeffnet.
#    Tiefe    A15 unter A11 und A12 unter A6: zwei Kammern, die
#             nirgendwohin fuehren. Ein Gebiet braucht auch Enden.
#
#  Und A16 steht senkrecht ueber A3: ein hohler Stamm, den man von
#  aussen sieht, lange bevor man hineinkommt.
# ---------------------------------------------------------------------

def room_A11() -> Room:
    """
    Die gesunkene Lichtung: das Loch, in das man im ersten Raum tritt.

    Sie ist der Beweis dafuer, dass der Hain unter sich weitergeht. Oben
    steht das Loch, durch das man gefallen ist, und durch dasselbe Loch
    faellt Licht - der einzige helle Fleck. Der Rest liegt im Schatten
    des eingesunkenen Daches.
    """
    r = Room("A11", "DIE GESUNKENE LICHTUNG", "hain", 54, 26)
    r.border()

    boden = r.profil([(0, 19), (8, 20), (16, 21), (24, 20), (32, 22),
                      (40, 21), (47, 19), (53, 19)], rauheit=0.6, seed=311)
    kopf = r.profil([(0, 8), (9, 12), (17, 14), (25, 10), (33, 13),
                     (41, 15), (53, 11)], rauheit=0.45, seed=313)
    r.hoehle(1, 53, boden, kopf, seed=317, zacken=0.12)

    r.dark = 0.12

    # Der eingesunkene Trichter unter dem Loch. Hier faellt man herein,
    # also darf hier nichts stehen - und der Weg hinaus fuehrt ueber die
    # Stufen an seinem Rand.
    r.kamin(8, 12, 2, 19, seed=3, tuer_x=12)
    r.ledge(24, 17, 6, 2)

    r.shaft_door("N", 12, 4, "up", "A1", "D", requires="fluegelschlag")
    r.spawn_on("N", 17, 16, 1)
    r.side_door("R", "right", "A14", "L", hint=18)
    r.shaft_door("D", 36, 4, "down", "A15", "N")
    r.spawn_on("D", 41, 20, -1)

    r.pickup_on("siegel", "wurzelmark", 27, 20)

    r.enemy_on("gabelmaus", 33, 20, patrol=5)
    r.enemy_on("stilleschreiter", 46, 18, patrol=4)

    r.crystal_on(6, 18, 2)
    r.crystal_on(30, 20, 1)
    r.scatter_decor(19, 13)

    r.note_on(21, 20, "DAS DACH IST NICHT GEFALLEN. "
                      "ES HAT AUFGEHOERT, SICH ZU HALTEN.")
    return r


def room_A14() -> Room:
    """
    Der Farngrund: Weg, sonst nichts - und deshalb wichtig.

    Zwischen zwei Raeumen, in denen etwas passiert, muss Strecke liegen.
    Sonst reiht sich alles aneinander wie Perlen auf einer Schnur, und
    ein Gebiet, das so gebaut ist, fuehlt sich klein an, egal wie viele
    Raeume es hat.
    """
    r = Room("A14", "DER FARNGRUND", "hain", 46, 20)
    r.border()

    boden = r.profil([(0, 15), (9, 16), (18, 15), (27, 16), (36, 14),
                      (45, 15)], rauheit=0.55, seed=331)
    kopf = r.profil([(0, 8), (10, 6), (20, 9), (30, 6), (40, 8), (45, 7)],
                    rauheit=0.4, seed=337)
    r.hoehle(1, 45, boden, kopf, seed=347, zacken=0.18)

    r.dark = 0.14

    r.ledge(20, 12, 6, 2)
    r.platform(30, 11, 5)

    r.side_door("L", "left", "A11", "R", hint=6)
    r.side_door("R", "right", "A5", "L", hint=6)

    r.enemy_on("dissonanzknospe", 24, 14)
    r.enemy_on("gabelmaus", 38, 14, patrol=6)

    r.crystal_on(7, 14, 1)
    r.scatter_decor(29, 14)

    r.note_on(13, 14, "HIER WAECHST NICHTS, WAS KLINGT. "
                      "DARUM WAECHST HIER UEBERHAUPT ETWAS.")
    return r


def room_A15() -> Room:
    """
    Kammer der ersten Stimme: klein, tief, und ein Ende.

    Nicht jeder Gang muss weitergehen. Ein Gebiet, in dem jeder Weg
    irgendwohin fuehrt, ist ein Schaltplan; erst die Sackgassen machen
    daraus eine Gegend, durch die man sucht.
    """
    r = Room("A15", "KAMMER DER ERSTEN STIMME", "hain", 38, 24)
    r.border()

    boden = r.profil([(0, 19), (12, 20), (24, 19), (37, 19)],
                     rauheit=0.4, seed=353)
    kopf = r.profil([(0, 8), (10, 11), (20, 9), (37, 7)], rauheit=0.4, seed=359)
    r.hoehle(1, 37, boden, kopf, seed=367, zacken=0.16)

    r.dark = 0.22

    # Der Weg zurueck hinauf, ohne Faehigkeit zu schaffen. Wer hier
    # herunterfaellt, kommt auch wieder heraus - eine Kammer ist ein
    # Ende, keine Falle.
    #
    # Der Raum ist dafuer hoeher als noetig: ein Kamin braucht Sprossen,
    # Sprossen brauchen Abstand, und in einem Raum von achtzehn Kacheln
    # frisst der Kamin den Boden auf, auf dem man landet.
    r.kamin(4, 12, 2, 19, seed=7, tuer_x=8)

    r.shaft_door("N", 8, 4, "up", "A11", "D")
    r.spawn_on("N", 20, 18, 1)

    r.pickup_on("equipment", "lauschband", 30, 18)

    r.crystal_on(26, 18, 2)
    r.scatter_decor(7, 18)

    r.note_on(22, 18, "DIE ERSTE STIMME WAR NICHT LAUT. "
                      "SIE WAR NUR ALLEIN.")
    return r


def room_A12() -> Room:
    """
    Die Horchkammer unter dem Tropfsteingang.

    Ein Ort zum Sitzen, mehr will er nicht sein. Baenke stehen in den
    Vorbildern nie am Weg, sondern immer ein Stueck daneben - man muss
    sie suchen, und genau deshalb merkt man sie sich.
    """
    r = Room("A12", "DIE HORCHKAMMER", "hain", 36, 18)
    r.border()

    boden = r.profil([(0, 13), (12, 14), (24, 13), (35, 13)],
                     rauheit=0.35, seed=373)
    kopf = r.profil([(0, 6), (12, 8), (24, 7), (35, 6)], rauheit=0.4, seed=379)
    r.hoehle(1, 35, boden, kopf, seed=383, zacken=0.1)

    r.dark = 0.18

    r.kamin(5, 11, 2, 13, seed=9, tuer_x=8)

    r.shaft_door("N", 8, 4, "up", "A6", "D")
    r.spawn_on("N", 15, 12, 1)

    r.bench_on(27, 12)

    r.crystal_on(22, 12, 1)
    r.scatter_decor(11, 12)

    r.note_on(19, 12, "SETZ DICH. DIE STILLE HIER IST DIE EINZIGE, "
                      "DIE NICHT VON DER DISSONANZ KOMMT.")
    return r


def room_A13() -> Room:
    """
    Der Splitterhang: der kurze Weg zurueck, wenn man fliegen kann.

    Von unten links nach oben rechts, ueber Absaetze und an Dornen
    vorbei. Er verbindet das Mottennest wieder mit der Kanzel - und
    damit laeuft man nach dem Tempel nicht denselben Weg zurueck, den
    man gekommen ist.
    """
    r = Room("A13", "DER SPLITTERHANG", "hain", 40, 38)
    r.border()

    boden = r.profil([(0, 31), (10, 32), (20, 30), (30, 31), (39, 30)],
                     rauheit=0.55, seed=389)
    kopf = r.profil([(0, 20), (12, 24), (22, 21), (32, 12), (39, 6)],
                    rauheit=0.5, seed=397)
    r.hoehle(1, 39, boden, kopf, seed=401, zacken=0.12)

    # Der Aufstieg. Die unteren Stufen gehen ohne alles, ab der Mitte
    # braucht es den Fluegelschlag - so ist der Raum von unten ein
    # Ausblick und von oben eine Abkuerzung.
    r.ledge(6, 27, 7, 2)
    r.platform(16, 24, 6)
    r.ledge(26, 22, 7, 2)
    r.platform(14, 18, 6)
    r.ledge(24, 14, 7, 2)
    r.kamin(20, 12, 2, 14, seed=13, tuer_x=24)

    r.dornengrube(16, 5, 3, boden)
    r.deckendornen(30, 4)

    r.side_door("L", "left", "A8", "R", hint=30)
    r.shaft_door("U", 24, 4, "up", "A4", "D", requires="fluegelschlag")
    r.spawn_on("U", 27, 5, -1)

    r.enemy_on("stilleschreiter", 9, 26, patrol=4)
    r.enemy("klangmotte", 20, 20)
    r.enemy("klangmotte", 34, 18)

    r.crystal_on(34, 30, 2)
    r.scatter_decor(41, 30)

    r.note_on(5, 30, "DER HANG IST AUS DEM GEBROCHEN, "
                     "WAS EINMAL DIE KANZEL GETRAGEN HAT.")
    return r


def room_A16() -> Room:
    """
    Der hohle Stamm: ein senkrechter Raum ueber dem Wurzelgang.

    Man sieht ihn von unten, lange bevor man hineinkommt - das ist der
    ganze Zweck. Ein Gebiet, in dem man nur sieht, wo man gerade steht,
    hat keine Ferne.
    """
    r = Room("A16", "DER HOHLE STAMM", "hain", 26, 42)
    r.border()

    boden = r.profil([(0, 35), (12, 36), (25, 35)], rauheit=0.4, seed=409)
    kopf = r.profil([(0, 30), (8, 32), (16, 31), (25, 30)],
                    rauheit=0.35, seed=419)
    r.hoehle(1, 25, boden, kopf, seed=421, zacken=0.1)

    r.dark = 0.2

    # Der Stamm selbst: ein Schacht mit eingebeulten Waenden, in dem
    # abwechselnd links und rechts Absaetze stehen.
    r.schacht(6, 2, 14, 30, seed=11, wand=2)
    for k, y in enumerate(range(28, 4, -4)):
        if k % 2 == 0:
            r.platform(7, y, 5)
        else:
            r.platform(14, y, 5)

    r.shaft_door("N", 10, 4, "down", "A3", "U")
    r.spawn_on("N", 16, 33, -1)

    r.pickup_on("siegel", "stammklang", 12, 6)

    r.enemy("klangmotte", 12, 20)
    r.enemy("klangmotte", 15, 11)

    r.crystal_on(4, 34, 1)
    r.scatter_decor(23, 34)

    r.note_on(20, 34, "DER STAMM IST HOHL, WEIL DER TON IN IHM "
                      "IRGENDWANN AUFGEHOERT HAT ZU KREISEN.")
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
    r.shaft_door("D", 6, 4, "down", "B7", "N")
    r.spawn_on("D", 12, 40, 1)
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
    # Der Weg hinauf in den Triforiengang. Der Pfeiler bei x=30 steht
    # dort schon - der Kamin wird durch ihn hindurchgeschlagen.
    r.kamin(28, 10, 1, 28, seed=31, tuer_x=30)
    r.shaft_door("U", 30, 4, "up", "B5", "N", requires="fluegelschlag")
    r.spawn_on("U", 34, 18, 1)
    r.shaft_door("D", 60, 4, "down", "B8", "U")
    r.spawn_on("D", 56, 18, -1)
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
    r.kamin(12, 10, 1, 21, seed=37, tuer_x=14)
    r.shaft_door("U", 14, 4, "up", "B6", "D", requires="fluegelschlag")
    r.spawn_on("U", 19, 18, 1)
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


# ---------------------------------------------------------------------
#  Die Kathedrale, zweiter Ausbau
#
#  Vier Raeume waren eine Reihe mit einem Abzweig. Eine Kathedrale ist
#  aber gerade das Gegenteil einer Reihe: sie hat ein Schiff, darueber
#  einen Umgang, darunter eine Krypta, und man kann auf drei Hoehen
#  durch denselben Raum gehen. Genau diese Schichtung fehlte.
#
#    oben    B5 Triforiengang, B6 Glockenstube
#    Mitte   B1 Vorhalle, B3 Kreuzgang, B4 Herzkammer  (wie bisher)
#    unten   B7 Krypta, B8 Verschuetteter Chor
#
#  Damit laufen zwei Schleifen durch das Gebiet: eine oben herum
#  (B3-B5-B6-B4) und eine unten herum (B1-B7-B8-B3).
# ---------------------------------------------------------------------

def room_B5() -> Room:
    """
    Der Triforiengang: der schmale Umgang ueber dem Kreuzgang.

    Er laeuft in der Wandstaerke, also ist er eng, und man sieht durch
    seine Oeffnungen hinunter in den Raum, durch den man vorhin
    gelaufen ist. Das ist der Zweck eines Umgangs - nicht ein Weg,
    sondern ein zweiter Blick auf einen bekannten.
    """
    r = Room("B5", "DER TRIFORIENGANG", "kathedrale", 64, 20)
    r.border()
    r.ground(1, 63, lambda x: 15 - 1.5 * math.sin(x * 0.09))
    r.ceiling(1, 63, lambda x: 5 + 1.2 * math.sin(x * 0.15 + 1))

    # Die Arkadenoeffnungen. Sie haengen von der Decke herunter und
    # reichen *nicht* bis zum Boden - ein Pfeiler, der durchsteht, ist
    # in einem Gang von zehn Kacheln Hoehe keine Gliederung, sondern
    # eine Wand, und der Umgang war damit an vier Stellen zugemauert.
    for x in range(8, 60, 13):
        r.fill(x, 5, 2, 6)

    r.platform(20, 11, 6)
    r.platform(40, 11, 6)

    r.shaft_door("N", 30, 4, "down", "B3", "U")
    r.spawn_on("N", 36, 13, 1)
    r.side_door("R", "right", "B6", "L", hint=6)

    r.enemy_on("stilleschreiter", 16, 14, patrol=5)
    r.enemy("echoscherbe", 46, 10)

    r.crystal_on(6, 14, 1)
    r.scatter_decor(131, 10, kinds=("crystal",))
    r.note_on(52, 14, "VON HIER OBEN SIEHT DER KREUZGANG AUS "
                      "WIE EIN NOTENBLATT, AUF DEM JEMAND STEHT.")
    return r


def room_B6() -> Room:
    """
    Die Glockenstube: hoch, leer, und einmal war hier alles voll Klang.

    Sie haengt ueber der Herzkammer, und der Weg hinunter fuehrt durch
    das Loch, durch das frueher das Seil lief.
    """
    r = Room("B6", "DIE GLOCKENSTUBE", "kathedrale", 38, 34)
    r.border()
    r.ground(1, 37, lambda x: 28 - 1.5 * math.sin(x * 0.11))
    r.ceiling(1, 37, lambda x: 3)

    # Die Balkenlage, auf der die Glocken hingen: drei Ebenen, versetzt.
    r.ledge(4, 22, 9, 2)
    r.platform(18, 19, 7)
    r.ledge(26, 15, 9, 2)
    r.platform(10, 11, 7)
    r.ledge(20, 7, 10, 2)

    r.side_door("L", "left", "B5", "R", hint=27)
    r.shaft_door("D", 14, 4, "down", "B4", "U")
    r.spawn_on("D", 20, 27, -1)

    r.pickup("siegel", "glockenmund", 24, 6)

    r.enemy("echoscherbe", 16, 16)
    r.enemy_on("dissonanzknospe", 32, 27)

    r.crystal_on(6, 27, 2)
    r.scatter_decor(137, 12, kinds=("crystal",))
    r.note_on(9, 27, "DIE GLOCKEN SIND NICHT FORT. "
                     "SIE HAENGEN NUR NICHT MEHR HIER.")
    return r


def room_B7() -> Room:
    """
    Die Krypta unter der Vorhalle: niedrig, breit, voller Pfeiler.

    Was oben Halle heisst, heisst hier unten Keller - und der Keller
    traegt die Halle. Man geht zwischen den Pfeilern hindurch, die man
    von oben als Boden kennt.
    """
    r = Room("B7", "DIE KRYPTA DER STIMMEN", "kathedrale", 58, 22)
    r.border()
    r.ground(1, 57, lambda x: 17 - 1.2 * math.sin(x * 0.1))
    r.ceiling(1, 57, lambda x: 7 + 1.5 * math.sin(x * 0.2))
    r.dark = 0.2

    for x in range(10, 54, 11):
        r.fill(x, 7, 3, 10)

    r.shaft_door("N", 6, 4, "up", "B1", "D", requires="fluegelschlag")
    r.spawn_on("N", 14, 15, 1)
    r.side_door("R", "right", "B8", "L", hint=6)

    r.kamin(4, 9, 2, 17, seed=23, tuer_x=6)

    r.enemy_on("stilleschreiter", 26, 16, patrol=6)
    r.enemy_on("dissonanzknospe", 47, 15)

    r.crystal_on(20, 16, 1)
    r.scatter_decor(139, 10, kinds=("crystal",))
    r.note_on(36, 16, "SIE HABEN DIE STIMMEN HIER UNTEN GELASSEN, "
                      "DAMIT SIE DAS GEWOELBE HALTEN.")
    return r


def room_B8() -> Room:
    """
    Der verschuettete Chor: die Decke ist herunter, der Raum steigt an.

    Von hier fuehrt ein Schacht wieder hinauf in den Kreuzgang - der
    Beweis dafuer, dass die Kathedrale nicht flach ist, sondern
    uebereinander liegt.
    """
    r = Room("B8", "DER VERSCHUETTETE CHOR", "kathedrale", 52, 30)
    r.border()
    r.ground(1, 51, lambda x: 24 - x * 0.22)
    r.ceiling(1, 51, lambda x: 6 + 6 * math.sin(x * 0.06))
    r.dark = 0.14

    r.ledge(12, 20, 8, 2)
    r.platform(24, 17, 7)
    r.ledge(34, 15, 8, 2)

    r.side_door("L", "left", "B7", "R", hint=22)
    r.shaft_door("U", 42, 4, "up", "B3", "D", requires="klangschritt")
    r.spawn_on("U", 46, 12, -1)
    r.kamin(38, 10, 2, 13, seed=29, tuer_x=42)

    r.enemy("echoscherbe", 20, 18)
    r.enemy_on("stilleschreiter", 30, 14, patrol=4)

    r.crystal_on(8, 22, 2)
    r.scatter_decor(149, 10, kinds=("crystal",))
    r.note_on(16, 20, "DER CHOR HAT WEITERGESUNGEN, ALS DAS GEWOELBE KAM. "
                      "MAN HOERT IHN NOCH, WENN MAN STILLSTEHT.")
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
    r.shaft_door("D", 78, 4, "down", "C4", "N")
    r.spawn_on("D", 74, 22, -1)
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
    r.shaft_door("D", 24, 4, "down", "C5", "U")
    r.spawn_on("D", 20, 34, -1)

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
    # Nicht ganz links: dort kommt man aus dem Schlund herein, und ein
    # Kamin genau im Eingang laesst den Ankommenden im Fels stehen.
    r.kamin(32, 10, 1, 21, seed=47, tuer_x=34)
    r.shaft_door("U", 34, 4, "up", "C6", "N", requires="fluegelschlag")
    r.spawn_on("U", 40, 21, -1)

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


# ---------------------------------------------------------------------
#  Die Resonanzkavernen, zweiter Ausbau
#
#  Drei Raeume in einer Reihe waren ein Gang mit Kristallen an der Wand.
#  Eine Hoehle ist aber nie eine Reihe: sie hat ein Niveau, unter dem
#  noch eines liegt, und Wasser sammelt sich immer unten. Genau das
#  fehlte - der Unterschied zwischen "weiter rechts" und "weiter unten".
#
#    oben    C1 Kristallgrotten, C2 Schlund, C3 Verstimmte Adern
#    unten   C4 Spiegelbecken, C5 Nadelkammer
#    hoch    C6 Der taube Gang, ueber den Adern
# ---------------------------------------------------------------------

def room_C4() -> Room:
    """
    Das Spiegelbecken: das tiefste Stueck der Kavernen, und das hellste.

    Unten steht Wasser, und darauf steht der Fels auf dem Kopf. Es ist
    der einzige Ort im Spiel, an dem etwas *heller* ist als der Weg
    dorthin - deshalb sieht man den Eingang schon von oben.
    """
    r = Room("C4", "DAS SPIEGELBECKEN", "grotten", 62, 26)
    r.border()
    r.ground(1, 61, lambda x: 20 - 2.5 * math.sin(x * 0.07))
    r.ceiling(1, 61, lambda x: 5 + 2.5 * math.sin(x * 0.11 + 2))

    r.ledge(10, 16, 8, 2)
    r.platform(24, 13, 7)
    r.ledge(38, 15, 9, 2)
    r.platform(50, 12, 6)

    r.shaft_door("N", 8, 4, "up", "C1", "D", requires="fluegelschlag")
    r.spawn_on("N", 15, 19, 1)
    r.kamin(6, 10, 2, 19, seed=41, tuer_x=8)
    r.side_door("R", "right", "C5", "L", hint=6)

    r.pickup("siegel", "spiegelgrund", 44, 14)

    r.enemy_on("dissonanzknospe", 30, 19)
    r.enemy("echoscherbe", 36, 12)
    r.enemy_on("stilleschreiter", 54, 19, patrol=4)

    r.crystal_on(20, 19, 2)
    r.crystal_on(46, 19, 2)
    r.scatter_decor(151, 12, kinds=("crystal",))
    r.note_on(26, 19, "DAS WASSER GIBT DEN TON ZURUECK, DEN ES BEKOMMT. "
                      "MEHR HAT NIE JEMAND VERLANGT.")
    return r


def room_C5() -> Room:
    """
    Die Nadelkammer: alles hier ist spitz, und alles zeigt zur Mitte.

    Der Aufstieg zurueck in den Schlund fuehrt zwischen den Nadeln
    hindurch - der Raum ist die Probe darauf, ob man springen kann,
    ohne zu haengen.
    """
    r = Room("C5", "DIE NADELKAMMER", "grotten", 48, 34)
    r.border()
    r.ground(1, 47, lambda x: 28 - 1.5 * math.sin(x * 0.13))
    r.ceiling(1, 47, lambda x: 4 + 3 * math.sin(x * 0.09))
    r.dark = 0.1

    r.ledge(6, 24, 8, 2)
    r.platform(18, 21, 6)
    r.ledge(28, 19, 8, 2)
    r.platform(16, 15, 6)
    r.ledge(26, 11, 8, 2)

    r.spikes(15, 27, 8)
    r.deckendornen(20, 5)
    r.wanddornen(40, 14, 8, nach=-1)

    r.side_door("L", "left", "C4", "R", hint=27)
    r.shaft_door("U", 28, 4, "up", "C2", "D", requires="klangschritt")
    r.spawn_on("U", 33, 10, -1)
    r.kamin(26, 10, 2, 11, seed=43, tuer_x=28)

    r.enemy("echoscherbe", 22, 24)
    r.enemy_on("dissonanzknospe", 38, 27)

    r.crystal_on(8, 27, 1)
    r.scatter_decor(157, 10, kinds=("crystal",))
    r.note_on(11, 27, "WER HIER STEHENBLEIBT, HAT ZEIT, DIE NADELN ZU ZAEHLEN. "
                      "ES SIND MEHR, ALS MAN DENKT.")
    return r


def room_C6() -> Room:
    """
    Der taube Gang: eine Kammer ueber den Adern, in der nichts klingt.

    Ein Ende, aber eines mit einem Grund - hier liegt das Siegel, das
    Stille zu etwas macht, das man tragen kann.
    """
    r = Room("C6", "DER TAUBE GANG", "grotten", 40, 20)
    r.border()
    r.ground(1, 39, lambda x: 15 - 1.2 * math.sin(x * 0.12))
    r.ceiling(1, 39, lambda x: 4 + 1.5 * math.sin(x * 0.18))
    r.dark = 0.24

    r.ledge(8, 12, 7, 2)
    r.platform(20, 10, 6)

    r.shaft_door("N", 6, 4, "down", "C3", "U")
    r.spawn_on("N", 13, 14, 1)

    r.pickup("siegel", "taubwerk", 32, 13)

    r.enemy("echoscherbe", 26, 9)

    r.crystal_on(18, 14, 1)
    r.scatter_decor(163, 8, kinds=("crystal",))
    r.note_on(24, 14, "HIER HOERT MAN NICHTS. NICHT, WEIL ES STILL IST - "
                      "SONDERN WEIL DER GANG NICHTS DURCHLAESST.")
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
    room_A11, room_A12, room_A13, room_A14, room_A15, room_A16,
    room_B1, room_B2, room_B3, room_B4,
    room_B5, room_B6, room_B7, room_B8,
    room_C1, room_C2, room_C3, room_C4, room_C5, room_C6,
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
        r.simse_formen(seed=sum(map(ord, r.id)))
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
