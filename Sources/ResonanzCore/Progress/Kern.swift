import Foundation

/// Das Ding, das in ihr steckt.
///
/// Cadence ist formlos - der Kern ist der einzige harte Gegenstand an ihr,
/// und er ist der Grund, warum sie ueberhaupt eine Gestalt hat. Er bestimmt
/// zweierlei:
///
///   - **Den Magiestil.** Wie ihr Klang in die Ferne geht: als Dreiklang,
///     als Druckkugel, als Stich.
///   - **Ihre Anlage.** Ein schwerer Kern zieht sie breit und macht sie
///     zaeh, ein spitzer macht sie schnell und duenn.
///
/// Er ist austauschbar. Die Stimmgabel ist nur der erste, den sie findet -
/// alles Weitere ist eine Frage dessen, was noch in der Welt liegt.
public enum Kern: String, Codable, Sendable, CaseIterable {
    /// Der Anfang. Zwei Zinken, ein sauberer Ton, nichts Besonderes.
    case stimmgabel
    /// Ausgewogen: ein Dreiklang in die Ferne.
    case leier
    /// Schwer: eine Druckkugel, die durchschlaegt.
    case trommel
    /// Schnell und spitz: sticht und durchschlaegt.
    case floete
    /// Der Takt selbst. Kein grosser Ton, sondern lauter kleine, in Reihe.
    case metronom
    /// Schwer und weit. Ein Schlag, der nachhallt, statt zu treffen.
    case glocke
    /// Ein einziger gerader Ton, der durch alles hindurchgeht.
    case orgelpfeife

    public var displayName: String {
        switch self {
        case .stimmgabel: return "STIMMGABEL"
        case .leier: return "LEIER"
        case .trommel: return "TROMMEL"
        case .floete: return "FLOETE"
        case .metronom: return "METRONOM"
        case .glocke: return "GLOCKE"
        case .orgelpfeife: return "ORGELPFEIFE"
        }
    }

    public var summary: String {
        switch self {
        case .stimmgabel: return "EIN SAUBERER TON, ZWEIMAL"
        case .leier: return "DREIKLANG - WEIT UND BREIT"
        case .trommel: return "DRUCKKUGEL - LANGSAM, ABER SIE REISST"
        case .floete: return "STICH - SCHNELL UND DURCHSCHLAGEND"
        case .metronom: return "TICKEN - VIELE KLEINE, BILLIGE STOESSE"
        case .glocke: return "SCHLAG - LANGSAM, SCHWER, HALLT NACH"
        case .orgelpfeife: return "LANZE - EIN GERADER TON DURCH ALLES"
        }
    }

    public var loreLine: String {
        switch self {
        case .stimmgabel:
            return "SIE STECKT IN DIR, SEIT DU AUFGEWACHT BIST. "
                 + "OHNE SIE WAERST DU NUR EIN GERAEUSCH."
        case .leier:
            return "DREI TOENE ZUGLEICH. KEINER DAVON ALLEIN WAERE ETWAS WERT."
        case .trommel:
            return "DER GRUNDTON SCHLAEGT NICHT AN, ER SCHLAEGT DURCH."
        case .floete:
            return "EIN EINZIGER TON, SO SCHMAL, DASS ER DURCH ALLES PASST."
        case .metronom:
            return "ER MISST NICHTS MEHR. ER HAELT NUR NOCH DURCH."
        case .glocke:
            return "SIE WURDE EINMAL ANGESCHLAGEN. DAS WAR VOR SEHR LANGER ZEIT."
        case .orgelpfeife:
            return "AUS DEM REGISTER GEBROCHEN. SIE KENNT WEITER NUR IHREN TON."
        }
    }

    /// Wie der Kern die Gestalt formt. Reine Werte, keine Waffe.
    public var modifiers: Modifiers {
        switch self {
        case .stimmgabel:
            return .neutral
        case .leier:
            return Modifiers(rangedRange: 1.10, resonanceRegen: 1.10)
        case .trommel:
            // Ein schwerer Kern zieht sie nach unten und haelt sie zusammen.
            return Modifiers(moveSpeed: 0.94, jumpPower: 0.95,
                             cohesion: 1.2, blastForce: 1.25)
        case .floete:
            // Ein spitzer Kern macht sie schnell und duenn.
            return Modifiers(moveSpeed: 1.10, dashDistance: 1.10,
                             rangedCost: 0.85, cohesion: 0.9)
        case .metronom:
            // Er haelt den Takt, also auch ihren: sie fuellt sich schneller.
            return Modifiers(moveSpeed: 1.03, rangedDamage: 0.9,
                             resonanceRegen: 1.35)
        case .glocke:
            // Schwer wie ein Kessel. Sie steht fester und springt kuerzer.
            return Modifiers(moveSpeed: 0.90, jumpPower: 0.92,
                             cohesion: 1.25, blastForce: 1.30)
        case .orgelpfeife:
            // Lang und hohl: sie traegt weit und haelt wenig.
            return Modifiers(jumpPower: 1.05, rangedRange: 1.20, cohesion: 0.9)
        }
    }
}
