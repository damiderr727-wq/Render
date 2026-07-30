# Sanatorium Nachtschatten — Übergabe an Claude Code

## Was das ist

Survival-Horror-Spiel für iPad, gebaut in **Swift Playgrounds** mit **SwiftUI + SceneKit**.
Vorbilder: Resident Evil 1 (Kameraführung, Räume als Bühnen) und **Silent Hill 2 Remake**
(Lichtstimmung: düster, aber mit klaren hellen Inseln — kein gleichmäßiges Grau).

Alles ist prozedural im Code gebaut, es gibt **keine 3D-Modelldateien**. Texturen werden
von einem Python-Skript erzeugt und als PNG mitgeliefert.

Sprache im Projekt: **Deutsch**. Kommentare, Toasts, Raumnamen, UI. Swift-Strings bitte
ASCII-only (keine Umlaute) — Playgrounds hat sich daran verschluckt. Also "Taefelung",
nicht "Täfelung".

Antworte mir auf **Deutsch**, direkt und ohne Beschönigen. Wenn du einen Fehler machst,
sag es. Wenn du etwas nicht weißt, rate nicht — messe oder frag.

---

## Dateien

| Datei | Inhalt |
|---|---|
| `MyApp.swift` | `@main`, minimal. **Nur eine Datei darf `@main` haben.** |
| `ContentView.swift` | Gesamte UI: Joystick, Aktionsknopf, Inventar, Papierkarte, Journal, Debug-Panel, Möbel-Editor, Wand-Editor, Free-Cam-Panel |
| `Game.swift` | `GameController` (SceneKit-Delegate): Kamerazonen, Kollision, Licht, Interaktion, Gegner-Update, Editor-Zustand, freie Kamera |
| `Villa.swift` | ~2700 Zeilen Gebäudebau. Alle Räume, Wände, Treppen, Fenster, Lichtschächte, Wasserflächen |
| `Furniture.swift` | **Datengetriebene Möbel und Wände** + Editor-Logik + Speichern/Laden |
| `PlayerModel.swift` | Spielerfigur (zwei Stile), Gegner „Der Schläfer" |
| `Textures.swift` | Textur-Registry mit Fallbacks |
| `Interaction.swift` | `ItemKind`, `Door`, `Pickup`, `RoomInfo` für die Karte |
| `Audio.swift` | Echtzeit-synthetisierter Regen, Grundrauschen, ferner Donner (keine Audiodateien) |

Dazu ein Python-Texturgenerator (`make_textures.py`, ~1200 Zeilen, PIL + numpy) der
68 PNGs erzeugt. Den solltest du mit übernehmen — er ist die Quelle für alle Texturen.

---

## KRITISCHE Technik-Erkenntnisse

Diese haben jeweils mehrere Runden gekostet. Bitte nicht neu entdecken.

### 1. Dreieckswicklung
SceneKit cullt im Uhrzeigersinn gewickelte Flächen. Bänder zwischen zwei Ringen müssen
`(A_i, B_j, B_i)` + `(A_i, A_j, B_j)` sein — gegen den Uhrzeiger von außen gesehen.
Falsch gewickelt sieht man **von vorn die Innenseite der Rückwand**. Das war lange der
Grund, warum die Spielerfigur „invertiert" aussah.

### 2. SceneKit-Lichtskala ist 1000, nicht 1
`intensity = 240` sind 24 % Normalhelligkeit, nicht „hell". Ich habe wochenlang mit
Werten unter 1000 hantiert und mich gefragt, warum alles dunkel bleibt.
Aktuell: Grundlicht 1650, Richtlicht 780, Belichtung 1,05.

### 3. Helligkeit = Albedo × Licht
Die Innentexturen hatten Mittelwerte um 55/255 (21 % Albedo). Eine solche Fläche wird
**nie** hell, egal wie stark die Lampen sind. Der Texturgenerator hebt sie jetzt per
Gamma an (`LIFT`-Tabelle in `make_textures.py`). Wenn etwas zu dunkel wirkt: erst die
Textur messen, dann am Licht drehen.

### 4. Emission beleuchtet nichts
Ein Material mit Emission ist selbst hell, wirft aber **kein Licht** in die Umgebung.
Leuchtende Fenster brauchen zusätzlich echte Lampen, sonst hat man strahlende Panele in
einem dunklen Raum.

### 5. Decken brauchen Öffnungen
Ein durchgehender `floorTile` über einem Treppenhaus lässt die Treppe von unten in die
Deckenplatte laufen — „Stufen in der Decke", Etage nicht erreichbar. Deckenplatten
müssen als mehrere Teile **um die Schachtöffnung herum** gebaut werden.

### 6. `WallBox` hat zwei Flags
- `blocksCamera` — Möbel dürfen die Kamera nicht wegdrängen, sonst schwenkt sie an jedem
  Stuhl herum. Wände ja, Möbel nein.
- `blocksPlayer` — Treppenläufe sollen die **Kamera** stoppen (damit sie nicht durch die
  Stufen gleitet), den **Spieler** aber durchlassen (er läuft ja darauf).

Außerdem braucht jede Sperre einen **Höhenbereich**. Ohne den blockierte das
Schwimmbecken im Dachgeschoss einen Gang im Erdgeschoss.

### 7. Möbel verschieben: Drehpunkt bleibt stehen
SceneKit rechnet `Welt = Position · Drehung · Drehpunkt⁻¹`. Setzt man beim Verschieben
Drehpunkt **und** Position auf denselben neuen Wert, kürzen sie sich weg — nichts bewegt
sich. Der Drehpunkt muss auf der **Bauposition** bleiben (`furnitureBase`).

### 8. `simd_normalize` eines Nullvektors → NaN → Absturz
Steht die Kamera exakt auf einem Lichtschacht, ist der Differenzvektor null lang.
`opacity = NaN` bringt SceneKit zum Absturz. Immer Länge prüfen und `isFinite` testen.

### 9. Knotenzahl ist der Engpass
`glassRun` hat pro Fassade Bucht für Bucht gebaut: 102 Einzelkörper in der Schwimmhalle.
Das hat den Raum zum Absturz gebracht. Jetzt eine durchgehende Leuchtplatte je Fassade
(28 Körper). **Bei Absturzverdacht immer erst Knoten und Lichter zählen.**

### 10. Schattenwerfer sind teuer
Jedes schattenwerfende Licht rendert die sichtbare Geometrie ein zusätzliches Mal. Aus
der Vogelperspektive sieht man das halbe Gebäude — das war der Absturz beim Hochfliegen.
Sie werden jetzt über 6,5 m Kamerahöhe abgeschaltet (`shadowLights`, `shadowsOff`).

### 11. Fensterscheiben: Versatz POSITIV
Die Wandnormale `n` zeigt in den Raum. Die Scheibe muss mit **positivem** Versatz
gesetzt werden (`+0.03`), dann liegt sie in jeder Wandrichtung im Raum. Mit `-D` lag sie
32 cm hinter dem Anker, also mitten in der 30 cm dicken Wand — unsichtbar.

### 12. Kein Compiler im alten Setup
Ich hatte kein `swiftc` und habe deshalb eine **Python-Prüfsuite** gebaut. Du hast einen
Compiler — nutze ihn. Behalte die Suite trotzdem für die semantischen Prüfungen, die
der Compiler nicht macht (siehe unten).

---

## Prüfsuite (Python, gegen alle .swift-Dateien)

Acht Fehlerklassen, jede aus einem tatsächlich passierten Fehler gewachsen:

1. **Klammernbilanz** `{} () []`, Kommentare und Strings vorher gestrippt
2. **Fehlende Texturen**: `Tex.X` gegen `static let X` in Textures.swift
3. **Doppelte Funktionsnamen**
4. **Unbekannte Argumentlabels** gegen Signaturen
5. **Reihenfolge der Argumentlabels** — Swift verlangt Deklarationsreihenfolge
6. **Float/CGFloat-Konflikte** (nur bei eindeutigen Namen ab 4 Zeichen, sonst nur Rauschen)
7. **`self.X()` auf freie Funktionen** — freie Funktionen stehen auf Spalte 0, Member sind eingerückt
8. **Kamerazonen-Überlappung** unter Berücksichtigung der Höhenbereiche
9. **SwiftUI-Panels**: jede `some View`-Property muss genau **einen** Container auf oberster Ebene zurückgeben

Zusätzlich hilfreich: Editor-Objektarten gegen die `case`-Zweige im Verteiler prüfen.

---

## Was steht

**Erdgeschoss**: Empfangshalle mit Tresen und Tresor-Rätsel, Treppenhaus, Flur,
Speisesaal, Küche (Hängerack, Tellerbord, Säcke), Lesesaal, Bäderabteilung (zwei
Wannen als Superellipsen-Netz), Apotheke, Direktion, Musiksalon mit Flügel,
Westflur (36 m, 6 Fenster), Nordflur.

**Kellergang** (y = 0): Heizungsraum mit glühendem Kessel, Kohlenkeller mit Rutsche
und Halden, Quellkammer mit Quellbecken.

**Obergeschoss** (y = 3,8): Galerie, Stationsflur, Zimmer 1–4, Schwesternzimmer,
Waschraum, **Isolierzellen** mit Wandringen, Handschellen und Kratzspuren.

**Badehaus** (y = 6,6): Vorraum, Waschsaal mit vier Schlauchständen, Schwimmhalle mit
Glasfassaden, Glasdach, Becken, acht Palmen.

**Systeme**: Papierkarte mit Etagenfilter, Journal für Lore-Dokumente (6 Stück),
Laterne (ausrüstbar, wirft Schatten, flackert), Brecheisen mit Schlag, Ausweichrolle
mit i-Frames, Gegner „Der Schläfer" (2 Instanzen), Echtzeit-Regen mit ortsabhängigem
Pegel, Möbel- und Wand-Editor mit Free Cam, Helligkeitsregler, Speichern in UserDefaults.

---

## Was kaputt ist — bitte in dieser Reihenfolge

### 1. Das Treppenhaus ist zerstört (höchste Priorität)
Siehe Screenshots: Läufe stehen schief, Geländer kreuzen sich, Podest hängt frei,
Stufen scheinen in der Wand. Ich habe es mehrfach umgebaut und dabei verschlimmert.

**Vorschlag: neu aufbauen statt weiter flicken.** Der Raum ist `x[-8,-4] z[6,14]`,
Ziel ist ein echtes Treppenhaus über drei Ebenen (0 → 3,8 → 6,6) mit:
- zwei getrennten geraden Läufen je Etage, verbunden durch ein echtes Podest
- Schachtöffnung in jeder Deckenplatte über dem oberen Lauf
- Kopffreiheit mindestens 2,0 m überall (nachrechnen!)
- Geländer an allen Schachtkanten
- Kamerazone über den ganzen Schacht (`yLo: -1, yHi: 5.4`), sonst fällt die Kamera beim
  Steigen aus der Zone und dreht nicht mit

Alle Maße vor dem Bau durchrechnen: Steigung, Kopffreiheit, Anschluss an die
Deckenöffnung, Kollision mit dem Treppenhaus der nächsten Etage.

### 2. Die Cartoon-Figur ist kaputt
`cartoonHead()` in `PlayerModel.swift`. Die Fliegerhaube und die hochgeschobene Brille
sitzen falsch. Vorlage: großer runder Kopf, Lederhaube mit Ohrenklappen, Brille auf der
Stirn, große einfache Augen. Der Umschalter (`setCartoon`) funktioniert — nur die
Geometrie stimmt nicht. Umschalten über den Knopf im Debug-Panel.

### 3. Bäderabteilung stürzt weiter ab
Die Schwimmhalle habe ich durch Reduktion der Knoten und Lichter gerettet. Die
**Bäderabteilung** (`x[-10,-3] z[-11,-4]`) stürzt noch. Erst zählen: Knoten, Lichter,
Wasserflächen, `registerWater`-Einträge. Verdacht: die Wannen-Netze plus mehrere
animierte Wasserflächen plus Schattenlichter.

### 4. Ab einer Höhe wird alles zu hell
Beim Hochfliegen mit der Free Cam wird es deutlich heller. Ursache ist wahrscheinlich
das Abschalten der Schattenwerfer über 6,5 m (`shadowsOff` in `Game.swift`) — dadurch
fällt die Verschattung weg. Entweder die Schwelle anders lösen oder die Grundhelligkeit
gegenläufig anpassen.

### 5. Editor zu Sandbox ausbauen
Aktuell: Möbel und Wände anpeilen, verschieben (10 cm), drehen (15°), löschen,
hinzufügen (18 Arten), Wände verlängern und Türlücken setzen, Free Cam, Speichern.

Gewünscht: **fast freies Bauen**. Konkrete Wünsche:
- Antippen im Bild zum Auswählen (SceneKit-Hittest) statt Durchblättern
- Ziehen mit dem Finger statt Pfeiltasten
- Freie Höhe (y) einstellbar, nicht nur Bodenhöhe
- Skalierung pro Objekt
- Mehr Arten, auch Bauteile: Boden, Decke, Tür, Fenster, Treppe
- Kopieren/Einfügen, Rückgängig
- Räume als Ganzes anlegen (Boden + vier Wände + Decke in einem Schritt)

### 6. Keller unterhalb der Leitungen bauen
Neue Ebene **unter** y = 0, etwa y = −2,6. Lore: Nervenheilanstalt für „unheilbare"
Patienten, die auf dem Papier für tot erklärt wurden, um an ihnen zu experimentieren.
Zugang über die Eisentür „Zur Anstalt" im Treppenhaus (existiert, verschlossen,
braucht `ItemKind.asylumKey` — der Schlüssel ist noch nirgends platziert).

Geplant: Behandlungsflur, drei Verwahrräume, OP-Raum, Aktenkammer mit dem Beleg.
Treppe hinter dem Kessel im Heizungsraum. Braucht eine Bodenöffnung in der
Erdgeschossplatte — siehe Erkenntnis 5.

---

## Geplant, noch nicht gebaut

- **Tresor** im Empfang: enthält die erste Waffe (Pistole) plus Munition. Kombination
  aus einem Lore-Dokument, absichtlich leicht. Der Tresor steht schon da, ohne Mechanik.
- **Sturm-Phase**: Kipppunkt im Spielverlauf. Fenster werden schwarz, Poolwasser
  verschwindet, in der Schwimmhalle spawnt etwas. Vorher friedlich.
- **Gewächshaus** an der Schwimmhalle als Ruheort mit Speicherpunkt (Objekt, kein Auto-Save).
- **Rätselkette**: Tür zur Pool-Ebene und Tür zum Keller je hinter einem Rätsel im Stil
  von Resident Evil / Silent Hill (Gegenstände kombinieren, nicht Zahlenschlösser).
- **Weitere Gegner** (schematisch wie der Schläfer — das Unheimliche kommt aus falschem
  *Verhalten*, nicht aus Monsterdesign):
  - *Die Nasse Schwester* — reagiert auf Wasser, hinterlässt verblassende Fußspuren
  - *Der Wärter* — fester Rundgang, reagiert nur auf brennende Laterne
  - *Die Verlegten* — kriechend, in Laken, zu mehreren, für den Keller
  - *Der Kesselgänger* — glüht von innen, wirft einen Schatten den man vorher sieht
- **Bosskampf** später im Keller.
- Ziel: etwa **5 Stunden Inhalt** zum Start.

---

## Arbeitsweise, die sich bewährt hat

**Messen statt raten.** Fast jeder Fehler, den ich lange nicht fand, ließ sich
ausrechnen: Texturhelligkeit, Schrittlänge aus der Beinkette, Kopffreiheit einer Treppe,
Abstand einer Scheibe zur Wandfläche, Knotenzahl eines Raums. Wenn etwas komisch
aussieht — erst die Zahlen holen.

**Bildschirmfotos mit Zahlen.** Es gibt einen Käfer-Knopf, der Spielerposition,
Kameraposition, Zone, Etage und Raumnamen einblendet. Ein Screenshot davon sagt mehr
als eine Beschreibung. Bei Kameraproblemen immer danach fragen.

**Kleine, verankerte Änderungen.** Ich habe dreimal Funktionen zerstört, weil ich über
Blockgrenzen hinweg ersetzt habe. Nur exakt verankerte Ersetzungen mit Zusicherung.

**Der Nutzer findet die Ursachen mit.** „Von vorne sehe ich den Rücken" war der
Wicklungsfehler. „Nur über dem Hauptraum" waren die Schattenwerfer. „Nicht hunderte
kleine Lichter" war die Knotenzahl. Ernst nehmen, auch wenn es unfachlich klingt.
