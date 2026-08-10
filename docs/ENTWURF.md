# RESONANZ — Entwurf

Was hier steht, sind die Entscheidungen hinter dem Spiel und die Gründe
dafür. Zahlen stehen in `Sources/ResonanzCore/Combat/Tuning.swift`, nicht
hier — dieses Dokument soll nicht veralten.

## Die Welt

Eine Welt, die sich selbst gesungen hat. Kein Chor, kein Publikum: Klang war
der Stoffwechsel. Kristalle wuchsen dort, wo ein Ton lange genug gehalten
wurde. Kreaturen verständigten sich in Intervallen. Der Boden trug Adern aus
erstarrtem Klang.

Dann geriet sie in Dissonanz. Nicht in Stille — das wäre erträglich. In
Dissonanz: alles klingt weiter, aber nichts mehr zueinander.

Die Regionen sind vier Zustände dieses Zerfalls:

**Der schlafende Hain** — noch fast heil, nur leise. Warme Teiltöne, offene
Räume, weiche Böden. Hier lernt man, dass Klang etwas bewirkt.

**Kathedrale der Fugen** — Ordnung, die überlebt hat, weil sie streng war.
Senkrechte Räume, Orgelpfeifen, Hall. Vier Stimmen gingen hier im Kreis;
eine blieb stehen, seitdem stolpern alle.

**Resonanzkavernen** — Kristall, Weite, Kälte. Die Klüfte sind zu breit für
Beine. Hier braucht man einen geliehenen Herzschlag.

**Herz der Dissonanz** — dunkel, rot, verstimmt. Das Präludium aus dem Hain
kehrt wieder, nur kippt jede vierte Note einen Halbton weg.

## Cadence

Eine kleine Figur mit langen Gliedern und einem kleinen Kopf — die
Silhouette entscheidet, nicht das Gesicht. Der Umhang hat einen leuchtenden
Saum, damit man sie im Dunkeln findet.

Sie wird parametrisch gezeichnet: eine Pose ist eine Handvoll Zahlen
(Neigung, Wippen, Beinphase, Haarschwung, Armwinkel). Das war keine
Bequemlichkeit, sondern eine Entscheidung — 127 Bilder aus drei
Instrumenten mal elf Bewegungen hätte niemand von Hand nachgezogen, wenn
sich die Silhouette noch einmal ändert.

## Der Kampf

Die Waffe ist der Schall. Das Instrument gibt ihm nur die Form. Deshalb
gibt es keine Waffenliste, die länger wird, sondern drei Handschriften:

- **Leier** — ausgewogen. Weiter Bogen, drei Töne in die Ferne.
- **Trommel** — Wucht und Rückstoß, kurze Reichweite, lange Erholung.
- **Flöte** — schnell und spitz, wenig Schaden, wenig Kosten.

Der Kreislauf hält die Figur in Bewegung: Fernkampf kostet Resonanz,
Nahkampftreffer geben sie zurück. Wer auf Abstand bleibt, verhungert. Wer
nur zuschlägt, hat für die Kluft keine Antwort.

Der Schlag nach unten prallt ab — von Kreaturen wie von Dornen. Dornen
sind dadurch nicht nur Strafe, sondern Gelände.

Damit kein Treffer falsch klingt, laufen alle Angriffsklänge über eine
äolische Leiter auf D. Eine Angriffsserie steigt dabei die Leiter hinauf und
fängt nach einer Pause von vorn an — Kämpfen ist eine Phrase.

## Der Fortschritt

Vier Fähigkeiten, jede der Rest von etwas Lebendigem. Sie sind keine
Werkzeuge, sondern Fundstücke einer Welt, die nicht mehr da ist.

| Fähigkeit | Öffnet |
|---|---|
| Flügelschlag | Schächte — Sprossen über der einfachen Sprunghöhe |
| Klangschritt | Kamine — schmale Schächte ohne Absätze |
| Herzschlag | Klüfte — Lücken jenseits der Sprungweite |
| Basston | verstimmte Sperren — Akkorde, die sich weigern aufzulösen |

Die Reihenfolge steht nicht im Code, sie ergibt sich aus der Geometrie. Ein
Test prüft, dass sie überhaupt eine ist: Flügelschlag → Klangschritt →
Herzschlag → Basston, jeder Raum erreichbar, keine Fähigkeit hinter sich
selbst.

## Der Verstimmte Kantor

Er gab den Takt. Niemand hat ihm gesagt, wann er aufhören soll — also
dirigiert er weiter, gegen eine Welt, die längst nicht mehr mitspielt.

Drei Sätze, die den musikalischen Aufbau spiegeln:

1. **Taktschlag** — einzelne Akkorde, weite Pausen. Man lernt sein Metrum.
2. **Fuge** — mehrere Stimmen zugleich: er ruft, was von seinem Chor übrig
   ist, und die Angriffe überlagern sich.
3. **Toccata** — Orgelpfeifen brechen aus dem Boden, dichter und schneller.

Jede Gefahrenzone leuchtet erst und trifft dann. Eine der Pfeifen zielt auf
den Spieler, die übrigen streuen — Ausweichen bleibt immer möglich, aber es
verlangt eine Entscheidung.

## Die Musik

Bach, weil dieses Material genau das kann, was die Welt braucht: es hält
sich zusammen, auch wenn man Stimmen wegnimmt.

Eine Partitur besteht aus Spuren mit je einer Schwelle. Steigt die
Intensität, kommen Stimmen dazu — sie wird nicht lauter, sie wird dichter.
Beim Erkunden hört man die Figuration und einen Pad; kommen Kreaturen
näher, tritt der Bass ein, dann die Glocken. Im Bosskampf hängt die
Intensität am Satz.

Der Dirigent im Kern erzeugt keinen Ton. Er sagt nur, welche Note wann
fällig wäre. Deshalb ist die Musik testbar: ein Test prüft, dass Noten in
zeitlicher Ordnung kommen und dass die Perkussion bei Intensität 0 schweigt.

## Der Aufbau

Die Trennung zwischen `ResonanzCore` und `ResonanzApp` ist die wichtigste
Entscheidung im Projekt.

`ResonanzCore` kennt keinen Bildschirm und keinen Lautsprecher. Es nimmt
`PlayerInput` entgegen und liefert `GameEvent` zurück — „hier wäre ein
Sprunggeräusch", „hier bräche eine Wand". Damit läuft das ganze Spiel ohne
Apple-SDK, und das hat sich ausgezahlt: 34 Tests, eine simulierte
Raumprüfung und eine Zufallseingaben-Probe über 30 Sekunden laufen auf einer
Linux-Maschine ohne Fenster.

`ResonanzApp` übersetzt: Ereignis zu Klang, Zustand zu Sprite. Es trifft
keine Spielentscheidungen.

## Die Raumprüfung

Der Teil, der am meisten gebracht hat.

Plattformen setzt man nach Augenmaß, und Augenmaß irrt sich um einen halben
Sprung. Statt das im Spiel zu merken, simuliert `ReachabilityProbe` einen
Spieler mit einem gegebenen Können: Von jeder begehbaren Fläche fächert sie
Bewegungsvarianten auf — gehen, tippen, voll springen, doppelt springen zu
drei Zeitpunkten, stoßen, an der Wand klettern —, verfolgt die Flugbahnen
und baut daraus einen Graphen.

Weil sie dieselbe `Player`-Klasse benutzt wie das Spiel, können Physik und
Levelbau nicht auseinanderlaufen. Ändert jemand die Sprunghöhe, meldet die
Prüfung sofort, welcher Aufstieg dadurch unmöglich wurde.

Gefunden hat sie unter anderem:

- Nach einer Landung blieb bis zu eine Schrittweite Luft unter den Füßen.
  Die Bodenprüfung lag danach jedes Mal daneben — im Spiel hätte sich das
  als schwammige Kollision gezeigt, ohne dass man den Grund gesehen hätte.
- Türen wuchsen im Gelände zu, weil ihre Höhe von Hand gesetzt war und das
  Gelände danach gezeichnet wurde.
- Mehrere Aufstiege hatten Sprossen außerhalb der Sprungweite.
- Der Fernkampf meldete den Schuss, erzeugte aber nie Geschosse.

## Was fehlt

- Eine Karte. Zwölf Räume kommen ohne aus, mehr nicht.
- Mehr Kreaturen je Region; im Moment teilen sich alle vier Regionen vier
  Arten.
- Zwischenbosse. Der Kantor steht allein.
- Erweiterungen der Instrumente — der Rahmen dafür steht, es fehlt das
  Material.
- Das Erproben auf einem Gerät: `ResonanzApp` ist hier nie gelaufen.
