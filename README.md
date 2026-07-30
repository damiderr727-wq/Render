# Sanatorium Nachtschatten

Survival-Horror fuer iPad, gebaut in Swift Playgrounds mit SwiftUI + SceneKit.
Alles prozedural im Code - keine 3D-Modelldateien. Vorbilder: Resident Evil 1
(Kamerazonen, Raeume als Buehnen) und Silent Hill 2 Remake (Lichtstimmung).

## Aufbau

| Pfad | Inhalt |
|---|---|
| `Sources/MyApp.swift` | `@main`. Nur eine Datei im Projekt darf das haben. |
| `Sources/ContentView.swift` | Gesamte UI: Joystick, Aktionsknopf, Inventar, Karte, Journal, Debug-Panel, Moebel- und Wand-Editor, Free-Cam |
| `Sources/Game.swift` | `GameController`: Kamerazonen, Kollision, Licht, Interaktion, Render-Loop |
| `Sources/Villa.swift` | Gebaeudebau - alle Raeume, Waende, Treppen, Fenster, Lichtschaechte, Wasser |
| `Sources/Furniture.swift` | Datengetriebene Moebel und Waende, Editor-Logik, Speichern/Laden |
| `Sources/PlayerModel.swift` | Spielerfigur (zwei Stile), Gegner "Der Schlaefer" |
| `Sources/Textures.swift` | Textur-Registry mit prozeduralen Fallbacks |
| `Sources/Interaction.swift` | `ItemKind`, `Door`, `Pickup`, `RoomInfo` |
| `Sources/Audio.swift` | Echtzeit-synthetisierter Regen, Grundrauschen, Donner |
| `docs/UEBERGABE_Claude_Code.md` | Uebergabeprotokoll mit allen Technik-Erkenntnissen |
| `tools/pruefsuite.py` | Statische Pruefungen, die ein Compiler nicht macht |
| `tools/treppe_messen.py` | Vermessung des Treppenhauses |

Sprache im Projekt: Deutsch. Swift-Strings ASCII-only - Playgrounds verschluckt
sich an Umlauten. Also "Taefelung", nicht "Taefelung" mit ae statt ä.

## Pruefen

```
python3 tools/pruefsuite.py Sources
python3 tools/treppe_messen.py
```

Die Pruefsuite deckt neun Fehlerklassen ab, jede aus einem tatsaechlich
passierten Fehler entstanden: Klammernbilanz, fehlende Texturen, doppelte
Funktionsnamen (scope-bewusst), unbekannte Argumentlabels, Labelreihenfolge,
Float/CGFloat-Verwechslungen, `self.` auf freie Funktionen,
Kamerazonen-Ueberlappung und Editor-Arten ohne `case`-Zweig.

Jede Pruefung ist gegen absichtlich eingebaute Fehler gegengeprueft - eine
Suite, die nicht anschlagen kann, ist wertlos.

Sie ersetzt keinen Compiler. Was sie NICHT findet: Typfehler, fehlende
Rueckgaben, falsche Optionals - alles, was `swiftc` in einer Sekunde sieht.
Wer eine Toolchain hat, sollte zuerst kompilieren.
