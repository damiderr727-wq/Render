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

Der erste Entwurf war ein Mädchen im Umhang mit Gesicht, Haar und Hautton.
Bei zwanzig Pixeln war das Matsch — und vor allem war es keine Marke. Man
konnte es nicht in einem Bild wiedererkennen.

Sie ist jetzt keine Person, sondern eine Form aus drei Teilen:

- eine bleiche **Maske** mit **einem** großen dunklen Auge
- darüber die zwei nach außen geneigten Zinken einer **Stimmgabel**, mit
  bernsteinfarbenen Spitzen
- darunter ein fast schwarzer **Umhang** ohne sichtbare Beine, mit
  zerfranstem Saum

Die Stimmgabel ist ohnehin schon das Zeichen dieser Welt — die Rastpunkte
sind Stimmgabeln. Sie auf den Kopf zu setzen macht die Figur zur Trägerin
des Symbols, statt ihr nur ein Instrument in die Hand zu geben.

Zwei Regeln haben den Entwurf getragen: **eine Silhouette, drei Elemente**,
und **ein Akzent** (Bernstein an den Zinken, sonst nichts Warmes an ihr).
Die Zinken standen zuerst senkrecht und dicht — da las sich die Figur als
Hase. Nach außen geneigt und dünner lesen sie sich als Gabel.

Gezeichnet wird sie parametrisch: eine Pose ist eine Handvoll Zahlen. Das
war keine Bequemlichkeit — 127 Bilder aus drei Instrumenten mal elf
Bewegungen hätte niemand von Hand nachgezogen, als die Silhouette noch
einmal komplett umgeworfen wurde.

## Die Werteordnung

Der zweite große Fehler des ersten Entwurfs: alles lag im selben
Helligkeitsbereich. Dunkelgrün auf Dunkelgrün, sauber gekachelt, und
trotzdem Matsch — weil nichts vor etwas anderem stand.

Die Welt hat jetzt eine feste Staffelung, von hell nach dunkel:

| Schicht | Rolle |
|---|---|
| Himmel | hellster Wert im Bild |
| ferne Silhouetten | Stämme, Pfeiler, hängende Formen |
| nahe Silhouetten | dieselben Formen, deutlich dunkler |
| begehbarer Fels | dunkle Masse mit **heller Lichtkante** oben |
| Vordergrund | fast schwarz, läuft schneller als die Kamera |

Der Griff, der alles zusammenhält, ist der vorletzte: der Boden ist dunkel,
sichtbar wird er über seine beleuchtete Oberkante. Dadurch braucht es
keinen Nebel, um Tiefe zu erzeugen, und die bleiche Maske der Figur hebt
sich gegen die dunkle Masse ab, wo immer sie steht.

Dazu kommt der Maßstab: die Hintergründe sind so groß wie das Sichtfeld,
Stämme spannen die volle Bildhöhe, und an Fäden hängen Zapfen, Rauchfässer
und Kristalle. Erst an solchen Dingen sieht man, wie groß eine Halle ist.

## Die Hintergründe

Sie standen zuerst in `gen_world.py` und waren gestreut: Rechteck-Stämme an
Zufallspositionen. Streuung ergibt Rauschen, kein Bild. Sie haben jetzt ein
eigenes Modul, `gen_backdrops.py`, und jede Schicht ist gesetzt — was rahmt
den Blick, was trägt den Maßstab, wo bleibt die Mitte frei für die Figur.
Der Zufall darf nur noch die Rinde körnen und Kanten ausfransen.

Drei Entscheidungen tragen das:

**Warm gegen kalt.** Der Dunst ist kühl, das Holz warm. Dieser eine
Gegensatz trägt mehr als jede zusätzliche Farbe. Die Nadeln nehmen die
Kälte des Dunstes auf, das Holz bleibt warm — dadurch trennen sich die
Schichten auch dort, wo ihre Helligkeiten sich nähern.

**Ein Blickfang je Region.** Im Hain der bleiche Mond hinter einem Stamm,
in der Kathedrale die Fensterrose, in den Grotten eine leuchtende
Kristallgruppe. Nicht mehr als einer — sonst zieht nichts.

**Gerasterte Verläufe.** Ein weicher Verlauf sieht in Pixelgrafik nach
Weichzeichner aus. Eine geordnete Rasterung (Bayer-Matrix) hält die Kante
hart und lässt dem Bild an, dass es aus Pixeln besteht.

Das Zeichnen selbst brauchte erst Werkzeug: Bezierkurven, Striche mit
Verjüngung, rekursive Äste, organische Massen aus überlappenden Beulen,
Ketten aus einzelnen Gliedern, Spitzbögen.

**Der Boden ist keine Kachel.** Die Kacheln sind acht Pixel höher als das
Raster: darüber liegt Luft, in die Gras, Moos und Wurzeln hineinwachsen.
Ohne diesen Überhang endet jeder Boden an einer geraden Linie — daran
erkennt man ein Kachelspiel sofort. Der Kamm läuft unregelmäßig, unter dem
Licht wird es sofort dunkel, Wurzeln laufen von der Kante in die Masse
hinein, und je nach Kachelvariante wächst viel, wenig oder gar nichts. Die
Kollision merkt davon nichts — sie kennt weiter nur das Raster.

Dasselbe gilt für die durchsteigbaren Plattformen — und sie bekommen
**Enden**. Eine Plattform, die an beiden Seiten abgeschnitten ist, liest
sich als hingelegtes Brett; mit auslaufenden Enden wird sie ein Stück der
Landschaft, durch die man reist.

**Sichtbare Kachelkanten.** Der Kamm variierte frei in der Höhe — und
sprang deshalb an jeder Kachelgrenze. Der Trick dagegen ist billig und
wirkt sofort: die Enden des Profils auf null festnageln. Dazwischen darf
der Kamm tun, was er will, aber zwei beliebige Kacheln treffen sich immer
bruchlos. Dasselbe Profil rauht jetzt auch die senkrechten Felswände auf.

Dabei fiel ein älterer Fehler auf: der Kachelsatz kannte nur zwölf der
sechzehn Nachbarschaften, und die vier fehlenden fielen auf „Mitte"
zurück. Genau dort blieb jede Felswand schnurgerade — sie bekam gar keine
Kante. Jetzt werden alle sechzehn erzeugt.

**Die Rosette war ein Aufkleber.** Sie schwebte als Scheibe im Dunst, weil
dahinter keine Wand stand. Eine Rose ist aber ein *Loch in einer Mauer*.
Jetzt trägt die Kathedrale eine gemauerte Chorwand mit Wandvorlagen,
Kapitellen und einem Gesims; die Rose ist mit abgestufter Laibung
hineingeschnitten, darunter stehen Lanzettfenster. Erst die Laibung gibt
der Mauer ihre Dicke — ohne sie schwebt das Fenster, egal wie fein das
Maßwerk ist.

Der lehrreichste Fehler steckt in `frond()`. Nadelzweige waren zweimal
falsch — erst als einzeln gesetzte Punkte (las sich als Fischgräte), dann
als gezeichnete Striche (als Federkiel). Beide Male wurde **entlang** der
Kurve gefüllt statt **quer** dazu. Aus der Entfernung sind Nadeln keine
Striche, sondern eine geschlossene Masse mit gezackter Kante. Mit der
Normalen an jedem Kurvenpunkt entsteht die Fläche; die Zacken kommen
hinterher an den Rand. Dieselbe Funktion zeichnet jetzt auch die Farne im
Vordergrund.

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
