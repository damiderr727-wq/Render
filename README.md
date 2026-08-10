# RESONANZ

Ein 2D-Metroidvania in Swift. Die Welt war einmal ein Ökosystem aus Klang,
Kristall und Traum — bis sie in Dissonanz geriet. Cadence trägt drei
Instrumente; ihre Waffe ist der Schall selbst, im Nahkampf wie in der Ferne.
Die Musik stammt von Bach: durchsichtig beim Erkunden, dicht im Bosskampf.

```
Sources/
  ResonanzCore/     Spiellogik — plattformfrei, ohne Apple-SDK baubar
  ResonanzApp/      Darstellung und Klang — SpriteKit, SwiftUI, AVAudioEngine
  ResonanzCheck/    prüft die Raumgeometrie gegen die echte Spielphysik
Tools/              Python: erzeugt Grafik, Räume und Partituren
Tests/              34 Tests
```

## Bauen und starten

Die Spiellogik baut überall, auch auf Linux:

```sh
swift build
swift test
swift run -c release resonanz-check      # Raumprüfung
```

Zum Spielen wird eine Apple-Plattform gebraucht (macOS 13+, iOS 16+).
Ein minimaler App-Einstieg genügt:

```swift
import SwiftUI
import ResonanzApp

@main
struct Start: App {
    var body: some Scene {
        WindowGroup { ResonanzView() }
    }
}
```

## Steuerung

| | Tastatur | Gamepad |
|---|---|---|
| Bewegen | `A` `D` / Pfeile | Stick, Steuerkreuz |
| Zielen | `W` `S` | Stick hoch/runter |
| Springen | `Leertaste`, `Z` | A |
| Nahklang | `J`, `X` | X |
| Fernklang | `K`, `C` | Y |
| Herzschlag | `Umschalt`, `L` | R1 / R2 |
| Basston | runter + Nahklang in der Luft | runter + X |
| Instrument | `1` `2` `3`, `Q` `E` | L1 |
| Ansprechen | `F`, `Eingabe` | B |

Auf iOS erscheinen Bildschirmtasten.

## Die Welt

Zwölf Räume in vier Regionen, verbunden über einen Türgraph.

```
Der schlafende Hain      A1 → A2 → A3         Leier · Trommel · Flöte
Kathedrale der Fugen     B1 → B2 → B3 → B4
Resonanzkavernen         C1 → C2 → C3
Herz der Dissonanz       D0 → D1              Der Verstimmte Kantor
```

Vier Fähigkeiten öffnen die Welt, jede der Rest von etwas Lebendigem:

| Fähigkeit | Wirkung | Herkunft |
|---|---|---|
| **Flügelschlag** | Doppelsprung | Der Vogel ist fort. Sein Schlag hängt noch in der Luft. |
| **Klangschritt** | Wandhaftung, Wandsprung | Der Stein hat zugehört. Jetzt trägt er dich. |
| **Herzschlag** | Stoß nach vorn, unverwundbar | Etwas Großes schläft hier. Leih dir seinen Takt. |
| **Basston** | Bruchschlag nach unten | Manche Akkorde lösen sich nicht auf. Man muss sie schlagen. |

## Kampf

Die Waffe ist der Schall. Das Instrument gibt ihm nur die Form.

| | Nahklang | Fernklang |
|---|---|---|
| **Leier** | weiter Bogen, ausgewogen | Dreiklang, drei Geschosse |
| **Trommel** | Stoßwelle rundum, Wucht | schwere Druckkugel, durchschlägt |
| **Flöte** | schneller Stich | reiner Ton, durchschlägt |

Fernkampf kostet Resonanz, Nahkampftreffer geben sie zurück — wer auf
Abstand bleibt, verhungert. Ein Schlag nach unten prallt von Gegnern und
Dornen ab.

## Musik

Alles wird zur Laufzeit gerechnet; im Repository liegt kein einziges
Audio-Byte. Die Partituren sind Daten, der Synthesizer erzeugt daraus Töne.

| Stück | Ort |
|---|---|
| BWV 846, Präludium C-Dur | Der Hain — und, endlich rein, der Abspann |
| BWV 578, Fuge g-Moll | Kathedrale der Fugen |
| BWV 1068, Air | Kristallgrotten, gedehnt und gläsern |
| BWV 565, Toccata und Fuge d-Moll | Der Verstimmte Kantor |
| BWV 846, verstimmt | Das Herz der Dissonanz |

Jede Spur trägt eine Schwelle. Sie erklingt erst, wenn die Intensität sie
erreicht — die Musik verdichtet sich mit der Gefahr, statt lauter zu werden.
Im Bosskampf hängt die Intensität am Satz: Taktschlag, Fuge, Toccata.

## Assets

Es liegen keine handgemalten Dateien im Repository, nur die Generatoren:

```sh
python3 -m pip install Pillow numpy
python3 Tools/build_assets.py
```

Das schreibt nach `Sources/ResonanzCore/Resources/`:

- `Atlas/` — Figuren, Kacheln, Ausstattung, Effekte, Hintergründe
- `Levels/` — zwölf Räume mit Türgraph
- `Scores/` — sieben Stücke

Wer die Welt ändern will, ändert die Generatoren.

Räume ansehen, ohne das Spiel zu starten:

```sh
python3 Tools/preview_room.py A1 --scale 2
python3 Tools/preview_room.py --alle
```

## Die Raumprüfung

Von Hand gesetzte Plattformen liegen schnell einen halben Sprung zu weit
auseinander. `resonanz-check` simuliert deshalb einen Spieler mit genau dem
Können, das er an dieser Stelle hat — mit derselben `Player`-Klasse und
denselben `Tuning`-Werten wie das Spiel. Von jeder Standfläche fächert er
Sprungvarianten auf, verfolgt die Flugbahnen und baut daraus einen
Erreichbarkeitsgraphen.

```sh
swift run -c release resonanz-check
swift run -c release resonanz-check --map B2 --koennen fluegelschlag
swift run -c release resonanz-check --trace A3 7 17 --koennen -
```

`--map` zeichnet den Raum als ASCII-Karte (`o` erreichbar, `?` nicht),
`--trace` zeigt für eine einzelne Fläche, wohin jede Bewegungsvariante führt.

Derselbe Test läuft in `swift test`. Er hat unter anderem gefunden, dass die
Figur nach einer Landung bis zu eine Schrittweite über dem Boden hing.

## Stand

Verifiziert auf Linux mit Swift 6.0.3: `ResonanzCore`, `ResonanzCheck`,
34 Tests, die Asset-Pipeline und die Raumvorschau.

**Nicht verifiziert:** `ResonanzApp`. SpriteKit, SwiftUI und AVFoundation
gibt es auf Linux nicht, deshalb steht dieser Teil hinter
`#if canImport(SpriteKit)`. Der Compiler prüft dort die Syntax, aber keine
API-Aufrufe. Beim ersten Bauen auf einem Mac ist also mit Anpassungen zu
rechnen — die Spiellogik dahinter ist davon nicht betroffen.

## Lizenz

Code MIT. Das musikalische Material stammt aus gemeinfreien Werken von
Johann Sebastian Bach.
