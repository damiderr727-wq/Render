# Arbeitsweise in diesem Projekt

## Berichten

**Am Ende jeder Antwort kurz auflisten, welche Dateien sich geaendert haben** -
getrennt nach geaendert / neu / geloescht, mit einem Halbsatz wozu.

Antworten auf Deutsch, direkt, ohne Beschoenigen. Fehler benennen. Nicht raten -
messen oder fragen.

## Vor jeder Aenderung

In dieser Umgebung gibt es **kein swiftc**. Die Pruefwerkzeuge sind der einzige
Ersatz, also nach jeder Aenderung laufen lassen:

```
python3 tools/pruefsuite.py Sources     # neun statische Fehlerklassen
python3 tools/treppe_messen.py          # Treppenhaus begehbar?
python3 tools/kamera_zonen.py           # klemmen Kamerazonen?
python3 tools/kosten_zaehlen.py         # Lichter, Flaechen, Partikel
```

Jedes Werkzeug ist gegen absichtlich eingebaute Fehler gegengeprueft. Wer ein
Werkzeug erweitert, prueft die neue Regel genauso gegen - eine Pruefung, die
nicht scheitern kann, ist wertlos.

Ehrlich dazusagen, dass nicht kompiliert wurde.

## Code

- Swift-Strings **ASCII-only**, keine Umlaute - Swift Playgrounds verschluckt
  sich daran. Also "Taefelung", nicht "Täfelung".
- Kommentare, Toasts, Raumnamen, UI auf Deutsch.
- Kleine, exakt verankerte Aenderungen. In diesem Projekt wurden schon dreimal
  Funktionen zerstoert, weil ueber Blockgrenzen hinweg ersetzt wurde.
- Keine zwei konkurrierenden Bauer fuer dieselbe Sache stehen lassen. Genau so
  entstand das kaputte Treppenhaus.

## Die teuren Fallen

Ausfuehrlich in `docs/UEBERGABE_Claude_Code.md`. Die drei, die am meisten
Zeit gekostet haben:

1. **SceneKit-Lichtskala ist 1000**, nicht 1. `intensity = 240` sind 24 %.
2. **Helligkeit = Albedo x Licht.** Eine Textur mit 21 % Mittelwert wird nie
   hell, egal wie stark die Lampe ist. Erst die Textur messen, dann am Licht
   drehen.
3. **`hits()` blendet eine Sperre erst aus, wenn `y1 < y + 0.15`.** Ein
   Fuellkoerper, der bis zur Trittflaeche reicht, sperrt den Lauf, auf dem man
   steht. Daran war das Treppenhaus zweimal unpassierbar.
