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

Drei Anläufe waren daneben, und alle drei aus demselben Grund: Ich habe
Formen variiert, ohne dass eine Idee dahinterstand. Ein Mädchen im Umhang
wurde bei zwanzig Pixeln zu Matsch. Eine bleiche Maske mit einem Auge war
zu nah an Bekanntem. Eine Glockenform mit Zinken las sich als Tierkopf.
Danach ein Musterbogen mit zwanzig Silhouetten — der half auch nicht, weil
alle zwanzig dieselbe falsche Voraussetzung teilten.

Die Voraussetzung war: eine Heldin in einer Welt aus Klang sieht aus wie
jemand, der Klang *benutzt*. Falsch. **Sie ist selbst welcher.**

Cadence hat keinen Körper, sie hat eine Gestalt: eine flammenartige,
traumhafte Masse, die oben ausfranst und den Boden kaum berührt. Kein
Gesicht, keine Glieder — nur eine dunkle Kerbe dort, wo sie am dichtesten
ist, damit der Blick einen Halt hat.

Darin steckt der einzige harte Gegenstand an ihr: eine **Stimmgabel, halb
im Körper versenkt**. Der Steg liegt tief genug, dass die Masse ihn
umschließt, nach unten verliert sich der Stiel in ihr, und die Gestalt
läuft oberhalb zwischen den Zinken weiter. Sie ist das, was Cadence
zusammenhält — und das Einzige an ihr, das eine Kante hat.

Zwei Dinge folgen daraus von selbst:

**Das Instrument verformt sie.** Die Leier zieht sie lang, die Trommel
drückt sie breit und schwer, die Flöte spitzt sie zu. Man sieht an der
Silhouette, womit sie gerade spielt — statt an einem Gegenstand in einer
Hand.

**Die Animation wird frei.** Weil keine Gliedmaßen zueinander passen
müssen, ist jede Bewegung eine Verformung der ganzen Masse: der Sprung
dehnt sie, der Herzschlag verwischt sie waagerecht und reißt sie in
Bänder, ein Treffer lässt sie fast zerfallen. Die späteren
Resonanz-Fähigkeiten ziehen sie im Kampf kurz auseinander — dafür ist der
Parameter schon da.

## Die Fassungen

Cadence würde sich ohne Kleidung zerstreuen. Deshalb ist ihre Ausrüstung
kein Kostüm, sondern ein **Gefäß** — und daraus fällt die ganze Mechanik
von selbst heraus, statt aus einer Liste von Zahlen:

> Sie ist Klang unter Druck. Wo die Fassung Öffnungen hat, entweicht der
> Ton — und je weniger Öffnungen, desto höher der Druck an den
> verbliebenen.

| Fassung | Öffnungen | was sie tut |
| --- | --- | --- |
| Schlichter Mantel | 4 | hält sie zusammen, sonst nichts |
| Enge Fassung | 1 | Fernklang trägt weit und hart, sie wird träge |
| Offene Fassung | 9 | Nahklang weit und billig, Fernklang verpufft |
| Schlagfassung | 2 | Basston und Trommel reißen, sie springt niedrig |
| Gerissenes Gewand | 14 | schnell und weit, hält aber fast nichts aus |

Der Mantel ist die Standardausrüstung und verschiebt nichts. Er gibt ihr
nichts — er nimmt ihr nur das Vergehen. Ohne gültige Fassung fällt sie
auf ihn zurück.

Technisch hängt alles an einer Stelle: `Stats` multipliziert die
Grundwerte aus `Tuning` mit den Faktoren der getragenen Fassung, und der
Spieler fragt nur noch `Stats` — nie mehr `Tuning` direkt. Eine neue
Fassung wirkt dadurch überall zugleich: Lauf, Sprung, Sprint,
Reichweite, Wucht, Zusammenhalt. Reichweite steckt dabei nicht in einem
eigenen Feld, sondern in Tempo und Lebensdauer des Geschosses — sonst
gäbe es zwei Wahrheiten über dasselbe.

Eine Feinheit, die beim Testen auffiel: ganzzahliger Schaden verschluckt
kleine Aufschläge beim Runden. Ein Ton mit Schaden 1 blieb auch mit
vierzig Prozent mehr Druck bei 1 — die Fassung versprach etwas, das man
nie zu spüren bekam. Ab einem deutlichen Aufschlag kommt jetzt mindestens
ein Punkt an.

Gewechselt wird nur an der Stimmgabel. Sich mitten im Kampf neu zu fassen
wäre kein Kleiderwechsel, sondern ein Umbau.

### Der Stoff darf nicht steif sein

Die Kleidung bekommt kein eigenes Skelett. Sie läuft über dasselbe
Rückgrat wie die Gestalt, nur **verzögert**: unten am Saum hängt sie am
weitesten hinterher, oben am Kragen sitzt sie fast auf. Dadurch folgt sie
jeder Bewegung, ohne dass eine einzige Pose von Hand gesetzt wäre — beim
Lauf weht der Saum nach hinten aus, beim Stehenbleiben schwingt er nach,
bei der Landung schlägt er hoch.

Zwei Entscheidungen halten sie bei zweiundzwanzig Pixeln lesbar:

- **Die Öffnungen sind Kerben im Rand, kein fehlendes Stück.** Ein echtes
  Loch im Stoff gab die helle Masse dahinter frei, und die Silhouette
  zerfiel. Jetzt weicht der Stoff an der Öffnung zurück, und in der Kerbe
  steht ihr Licht.
- **Der Rand glüht, statt dunkel zu sein.** Ihr Licht sitzt hinter dem
  Stoff — ein dunkler Umriss verschwindet vor dem dunklen Grund, ein
  hinterleuchteter Rand nicht.

Die Zahl der Öffnungen im Bild ist dieselbe wie im Spielwert. Das Siegel
des Fundstücks zeigt denselben Querschnitt: so viele Lücken wie
Öffnungen, und aus jeder fährt der Druck heraus — wenige Lücken, lange
Strahlen. Ein Test prüft, dass es zu jeder Fassung im Katalog auch Bilder
gibt, sonst driften Zahlen und Zeichnung auseinander.

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

**Plattformen brauchen einen Grund — aber keine Verzierung.** Ein dünnes
Brett, das zwei Kacheln über ebenem Boden schwebt, sieht aus wie eine
Spielmechanik. Der erste Reflex war, das mit Material zu beheben: doppelte
Dicke, Rinde, herabhängendes Wurzelwerk. Das war der falsche Hebel. Bei
sieben Pixeln Höhe wird jedes zusätzliche Detail zu Rauschen, und die
klare Silhouette ging dabei verloren — die schlichtere Fassung mit Moos,
unregelmäßigem Kamm und auslaufenden Enden trägt weiter.

Das Problem lag ohnehin nicht am Material, sondern am **Ort**. Eine
Plattform bekommt ihren Sinn aus dem, was sie erschließt. A1 hat deshalb
jetzt eine Form statt einer Streuung: eine Terrasse zum Ankommen, eine
Mulde in der Mitte, und rechts ein vier Kacheln hoher Absatz zur Tür. Ohne
die drei Plattformen kommt man da nicht hinauf — damit haben sie einen
Grund, dort zu liegen. Der frei schwebende Felsblock, den nichts hielt,
ist weg.

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

## Warum Kachelkarten nach Kacheln aussehen

Die Vorbilder — Hollow Knight, Silksong, Blasphemous, Rain World, Celeste,
Dead Cells — zeigen alle kein Raster, obwohl mehrere davon eines benutzen.
Drei Gründe, in der Reihenfolge ihrer Wirkung:

**Die Bodenlinie hat keine Wiederholungseinheit.** Ein Kamm, der innerhalb
einer Kachel variiert und an ihren Rändern festgenagelt ist, ergibt über
zehn Kacheln trotzdem eine gerade Linie. Die Unruhe muss aus der
Geländeform selbst kommen, nicht aus der Kachel.

**Schrägen sind flach.** 45 Grad wirken wie eine Rutsche. Zwei zu eins —
also zwei Kacheln Länge je Kachel Höhe — sieht nach gewachsenem Hang aus.
Deshalb gibt es die Schrägen in beiden Fassungen, und im Gelände steht fast
immer die sanfte.

**Requisiten liegen auf den Nähten.** Das ist der eigentliche Griff. Nicht
das Kachelbild verrät das Raster, sondern die ununterbrochene Fuge. Steine,
Wurzelknäuel und Reisig werden deshalb gezielt über die Kachelgrenzen
gesetzt, nicht in die Kachelmitte — dort, wo die Linie sonst sichtbar wäre.

### Stufen werden Hänge

Ein Höhenprofil aus `ground()` wird beim Runden zur Treppe: jede Kachel
liegt ganz oben oder ganz unten. Statt in jedem Raum von Hand Rampen zu
setzen, läuft am Ende ein Durchgang über den fertigen Boden und ersetzt
jede Stufe von genau einer Kachel durch ein Rampenpaar — zwei Kacheln
lang, eine hoch.

Drei Regeln halten den Durchgang davon ab, die Karte einzuebnen:

- **Nur gewachsener Boden.** Eine Säule, die bis zum unteren Rand
  durchsteht. Schwebende Simse behalten ihre Kante, sonst verschwimmt der
  Unterschied zwischen Boden und Vorsprung.
- **Nur einzelne Stufen.** Zwei Kacheln Unterschied bleiben stehen: eine
  Klippe ist eine Absicht, keine Panne.
- **Nur zwischen langen Läufen.** Ein Absatz von einer Kachel Breite wird
  nicht zur Rampe umgebaut, sondern bleibt Absatz.

Das Ergebnis: siebzig Rampenkacheln in fünf Räumen, ohne eine einzige von
Hand gesetzt. Die Kathedrale bleibt unberührt — gemauerter Boden ist
flach, und das soll er auch sein.

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
- Gesperrte Ziele wurden von der Prüfung gar nicht geprüft, sondern nur
  übersprungen. Ein zweiter Durchgang mit allem Können läuft jetzt darüber,
  und der Bericht unterscheidet "später erreichbar" von "nie erreichbar".

## Was fehlt

- Eine Karte. Zwölf Räume kommen ohne aus, mehr nicht.
- Mehr Kreaturen je Region; im Moment teilen sich alle vier Regionen vier
  Arten.
- Zwischenbosse. Der Kantor steht allein.
- Erweiterungen der Instrumente — der Rahmen dafür steht, es fehlt das
  Material.
- Das Erproben auf einem Gerät: `ResonanzApp` ist hier nie gelaufen.
