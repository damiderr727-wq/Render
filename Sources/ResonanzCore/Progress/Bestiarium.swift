import Foundation

/// Das Bestiarium: was die Figur ueber die Bewohner der Welt weiss.
///
/// Der Text stand bisher im Zeichenwerkzeug, weil er nur fuer ein Blatt
/// gebraucht wurde. Damit gab es ihn genau einmal - und an der falschen
/// Stelle. Hier steht er jetzt, das Spiel liest ihn direkt, und das
/// Werkzeug liest ihn ebenfalls von hier. Ein Steckbrief im Spiel und
/// einer auf dem Blatt, die verschiedene Dinge behaupten, waeren
/// schlimmer als gar keiner.
///
/// Die Zahlen stehen bewusst *nicht* hier: Leben und Schaden kommen aus
/// `EnemyKind`. Sie koennen darum nicht veralten.
public struct Bestiarium: Sendable {

    /// Wie weit ein Eintrag aufgedeckt ist.
    ///
    /// Kein Eintrag ist von Anfang an da. Man bekommt ihn, indem man der
    /// Kreatur begegnet - und man versteht sie erst, wenn man oft genug
    /// mit ihr zu tun hatte. Das ist der Grund, warum das Bestiarium ein
    /// Anreiz ist und kein Nachschlagewerk.
    public enum Stand: String, Sendable {
        /// Nie begegnet. Der Eintrag existiert, aber leer.
        case unbekannt
        /// Schon gesehen: Name und Bild, sonst nichts.
        case gesehen
        /// Oft genug erlegt: der ganze Eintrag samt Zahlen.
        case verstanden
    }

    public struct Eintrag: Sendable {
        public let art: EnemyKind
        public let name: String
        /// Was sie tut - eine Beobachtung, kein Regelwerk.
        public let verhalten: [String]
        /// Was sie ist. Der Teil, den man erst nach einer Weile bekommt.
        public let deutung: [String]
        /// So oft muss man ihr begegnet sein, um sie zu verstehen.
        public let schwelle: Int

        public var maxHealth: Int { art.maxHealth }
        public var contactDamage: Int { art.contactDamage }

        /// Schaden in halben Kristallen, lesbar geschrieben.
        public var schadenText: String {
            contactDamage % 2 == 0
                ? "\(contactDamage / 2) Kristall"
                : "\(contactDamage / 2),5 Kristall"
        }
    }

    // Reihenfolge wie im Spiel: was einem zuerst begegnet, steht oben.
    public static let eintraege: [Eintrag] = [
        Eintrag(
            art: .gabelmaus,
            name: "GABELMAUS",
            verhalten: [
                "Huscht in Schueben und laeuft geradeaus an einem vorbei,",
                "statt zu verfolgen. Gefaehrlich nur, wenn man stehenbleibt.",
            ],
            deutung: [
                "Ihre Ohren sind eine Stimmgabel. Sie traegt den Ton",
                "spazieren, der mir fehlt, und weiss nichts davon.",
            ],
            schwelle: 3),
        Eintrag(
            art: .klangmotte,
            name: "KLANGMOTTE",
            verhalten: [
                "Taumelt auf einer Sinuslinie und driftet dabei heran.",
                "Fliegt. Faellt nie.",
            ],
            deutung: [
                "Ihre Fluegel sind Wellen, keine Haut. Was von ihr abfaellt,",
                "ist Staub aus Toenen, die schon verklungen sind.",
            ],
            schwelle: 4),
        Eintrag(
            art: .dissonanzknospe,
            name: "DISSONANZKNOSPE",
            verhalten: [
                "Waechst fest, bewegt sich nie, spuckt drei schiefe Toene",
                "faecherfoermig. Man kommt an ihr vorbei, wenn man wartet.",
            ],
            deutung: [
                "Keine Blume: eine Schale, die aufgesprungen ist. Innen",
                "stehen drei Linien, die nicht zueinander passen - man",
                "sieht den Missklang, bevor man ihn hoert.",
            ],
            schwelle: 4),
        Eintrag(
            art: .stilleschreiter,
            name: "STILLESCHREITER",
            verhalten: [
                "Patrouilliert und laedt auf kurze Distanz durch. Steckt",
                "mehr ein als alles andere im Hain.",
            ],
            deutung: [
                "Das Gegenstueck zu mir: ein Gefaess ohne Licht. Er traegt",
                "keine Leuchtfarbe - nur in seinen Fugen steht noch ein",
                "Rest von dem, was er geschluckt hat.",
            ],
            schwelle: 5),
        Eintrag(
            art: .echoscherbe,
            name: "ECHOSCHERBE",
            verhalten: [
                "Prallt frei umher; jede Wand dreht sie um.",
                "Sie zielt nicht. Sie ist nur im Weg.",
            ],
            deutung: [
                "Hinter ihr stehen zwei blassere Kopien aelterer Drehungen.",
                "Was man trifft, ist die scharfe vorn - die anderen sind",
                "schon vorbei.",
            ],
            schwelle: 5),
        Eintrag(
            art: .chorschatten,
            name: "CHORSCHATTEN",
            verhalten: [
                "Haengt unter der Decke und ruehrt sich nicht, bis jemand",
                "genau darunter steht. Dann laesst er los.",
            ],
            deutung: [
                "Ein Chorhemd ohne den, der darin stand. Er greift die",
                "Decke mit einem Haken - und der Haken ist das Hellste an",
                "ihm. Wer aufschaut, sieht ihn rechtzeitig.",
            ],
            schwelle: 3),
        Eintrag(
            art: .hallqualle,
            name: "HALLQUALLE",
            verhalten: [
                "Treibt in Stoessen durch den Hohlraum. Zwischen zwei",
                "Stoessen haengt sie still - dann ist sie zu treffen.",
            ],
            deutung: [
                "Sie verfolgt nicht, sie wird getragen. Das Leuchten in",
                "ihrem Schirm ist kein Drohen: in den Grotten ist sie",
                "oft das Einzige, woran man den Weg noch sieht.",
            ],
            schwelle: 4),
        Eintrag(
            art: .steinfink,
            name: "STEINFINK",
            verhalten: [
                "Hockt auf dem Gelaender, bis man nah genug ist, und",
                "stoesst dann im Bogen herab - auf die Stelle, wo man war.",
            ],
            deutung: [
                "Aus demselben Stein wie die Bruecke, auf der er sitzt.",
                "Solange er hockt, haelt man ihn fuer Zierrat. Erst die",
                "Fluegel machen aus dem Ornament ein Tier.",
            ],
            schwelle: 4),
    ]

    // MARK: - Die Grossen
    //
    // Ein Boss gehoert ins Bestiarium, aber nicht nach derselben Regel.
    //
    // Bei den Kreaturen ist Verstehen eine Frage der Menge: man begegnet
    // einer Gabelmaus dreimal, und beim dritten Mal weiss man, was sie
    // tut. Einem Boss begegnet man einmal. Dieselbe Regel wuerde
    // bedeuten, dass sein Eintrag nie aufgeht - oder dass er nach einem
    // einzigen Kampf so vollstaendig dasteht wie der einer Motte, der
    // vier Begegnungen gekostet hat.
    //
    // Darum: **gesehen, sobald man den Raum betritt** - man weicht ihm ja
    // nicht aus - und **verstanden, sobald er liegt.** Nicht die Anzahl
    // zaehlt, sondern der Ausgang.
    public struct GrosserEintrag: Sendable {
        public let art: Boss.Art
        public let name: String
        public let titel: String
        public let verhalten: [String]
        public let deutung: [String]

        public var maxHealth: Int { art.health }
    }

    public static let grosse: [GrosserEintrag] = [
        GrosserEintrag(
            art: .auftakt,
            name: "DER GROSSE AUFTAKT",
            titel: "WAS VOR DEM ERSTEN TON KAM",
            verhalten: [
                "Haengt an vier Faeden und schlaegt seinen Schatten auf den",
                "Boden, lange nachdem er ihn angesagt hat. Wer zusieht,",
                "statt zu hetzen, kommt an ihm vorbei.",
            ],
            deutung: [
                "Ein Auftakt ist der Schlag *vor* dem ersten Ton - nichts",
                "als Vorbereitung. Dieser hier hat nie aufgehoert",
                "vorzubereiten, weil nach ihm nichts mehr kam.",
            ]),
        GrosserEintrag(
            art: .glockengeist,
            name: "DER GLOCKENGEIST",
            titel: "DER NOCH LAEUTET",
            verhalten: [
                "Schwingt zwischen den Balken und schlaegt in Wellen, die",
                "sich ausbreiten. Zwischen zwei Wellen ist Platz.",
            ],
            deutung: [
                "Der Kloeppel haengt weiter, obwohl die Glocke sprang. Er",
                "schlaegt gegen den Rand seines eigenen Koerpers - das",
                "ist alles, was er noch kann, und er kann es sehr laut.",
            ]),
        GrosserEintrag(
            art: .hallwaechter,
            name: "DER HALLWAECHTER",
            titel: "DER NICHT MEHR ZURUECKKAM",
            verhalten: [
                "Steht im Becken und schickt seine Echos voraus. Wer das",
                "Echo trifft, trifft nichts - und verliert seinen Schlag.",
            ],
            deutung: [
                "In einer Hoehle kommt jeder Ton zurueck. Dieser ist so",
                "oft zurueckgekommen, dass er stehengeblieben ist. Die",
                "Umrisse neben ihm sind aeltere Fassungen desselben Tons.",
            ]),
        GrosserEintrag(
            art: .kantor,
            name: "DER VERSTIMMTE KANTOR",
            titel: "DER DAS MASS HIELT",
            verhalten: [
                "Pfeift, ruft und schlaegt - und alles davon im Takt, den",
                "er selbst vorgibt. Wer seinen Takt trifft, trifft ihn.",
            ],
            deutung: [
                "Er hat die Welt gestimmt, solange es eine Welt gab, die",
                "sich stimmen liess. Was danach kam, hat er weiter",
                "gestimmt.",
            ]),
    ]

    public static func grosser(fuer art: Boss.Art) -> GrosserEintrag? {
        grosse.first { $0.art == art }
    }

    /// Der Stand eines Bosseintrags. Eigene Regel, siehe oben.
    public static func stand(fuer art: Boss.Art, in save: SaveState) -> Stand {
        if save.erlegt["boss_" + art.rawValue] ?? 0 > 0 { return .verstanden }
        if save.gesehen.contains("boss_" + art.rawValue) { return .gesehen }
        return .unbekannt
    }

    public static func eintrag(fuer art: EnemyKind) -> Eintrag? {
        eintraege.first { $0.art == art }
    }

    /// Der Stand eines Eintrags nach dem, was im Spielstand steht.
    public static func stand(fuer art: EnemyKind, in save: SaveState) -> Stand {
        let erlegt = save.erlegt[art.rawValue] ?? 0
        guard let eintrag = eintrag(fuer: art) else { return .unbekannt }
        if erlegt >= eintrag.schwelle { return .verstanden }
        if erlegt > 0 || save.gesehen.contains(art.rawValue) { return .gesehen }
        return .unbekannt
    }

    /// Wie viele Eintraege ganz aufgedeckt sind - fuer die Anzeige "3/5".
    public static func verstanden(in save: SaveState) -> Int {
        eintraege.filter { stand(fuer: $0.art, in: save) == .verstanden }.count
    }
}
