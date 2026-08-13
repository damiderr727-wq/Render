import Foundation

/// Das Dorf der letzten Stimmen: was man dort bekommt und wofuer.
///
/// Zwei Regeln, und beide sind Entwurf und nicht Bilanz:
///
/// **Kerne gibt es hier nicht.** Ein Kern ist das, womit sie klingt -
/// den findet man, oder man findet ihn nicht. Waere er zu kaufen, waere
/// Erkunden eine Abkuerzung fuer Ungeduldige statt der einzige Weg.
///
/// **Was hier liegt, liegt sonst nirgends.** Ein Laden, der verkauft,
/// was ohnehin in der Welt liegt, ist eine Strafgebuehr fuer schlechtes
/// Suchen. Die drei Waren hier sind eigens fuer ihn gemacht, und wer
/// nie ins Dorf geht, bekommt sie nie.
public enum Laden {

    public struct Ware: Sendable, Equatable {
        public enum Inhalt: Sendable, Equatable {
            case siegel(String)
            case equipment(String)
        }

        public let id: String
        public let name: String
        public let preis: Int
        public let inhalt: Inhalt
        /// Was der Haendler dazu sagt. Er verkauft nichts, ohne es zu
        /// kommentieren.
        public let spruch: String
    }

    /// Der Preis steigt in Stufen, nicht linear: die erste Ware soll man
    /// nach dem ersten Gebiet haben koennen, die letzte erst, wenn man
    /// eine Weile unterwegs war.
    public static let waren: [Ware] = [
        Ware(id: "hoerrohr",
             name: "HOERROHR",
             preis: 24,
             inhalt: .siegel("hoerrohr"),
             spruch: "MAN HOERT DAMIT NICHTS BESSER. MAN HOERT NUR FRUEHER."),
        Ware(id: "flickmantel",
             name: "FLICKMANTEL",
             preis: 55,
             inhalt: .equipment("flickmantel"),
             spruch: "AUS DREI MAENTELN, DIE IHRE LEUTE NICHT MEHR BRAUCHTEN. "
                   + "ER HAELT. FRAG NICHT, WIE."),
        Ware(id: "muenzsiegel",
             name: "MUENZSIEGEL",
             preis: 90,
             inhalt: .siegel("muenzsiegel"),
             spruch: "WER ES TRAEGT, BEKOMMT MEHR FUER SEINE ARBEIT. "
                   + "ICH VERKAUFE ES TROTZDEM."),
    ]

    public static func ware(_ id: String) -> Ware? {
        waren.first { $0.id == id }
    }

    /// Ob eine Ware jetzt gekauft werden kann.
    public static func kaufbar(_ ware: Ware, in save: SaveState) -> Bool {
        !save.gekauft.contains(ware.id) && save.stimmen >= ware.preis
    }

    /// Kauft ein und gibt zurueck, ob es geklappt hat.
    ///
    /// Der Laden aendert den Spielstand selbst, statt ein Ergebnis
    /// zurueckzugeben, das jemand einbauen muss: sonst gibt es
    /// irgendwann eine Stelle, an der abgezogen wird, ohne dass etwas
    /// ankommt.
    @discardableResult
    public static func kaufe(_ ware: Ware, save: inout SaveState) -> Bool {
        guard kaufbar(ware, in: save) else { return false }
        save.stimmen -= ware.preis
        save.gekauft.insert(ware.id)
        switch ware.inhalt {
        case .siegel(let id):
            save.progression.siegelOwned.insert(id)
        case .equipment(let id):
            save.progression.equipmentOwned.insert(id)
        }
        return true
    }
}
