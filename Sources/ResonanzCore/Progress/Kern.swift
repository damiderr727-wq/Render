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

    public var displayName: String {
        switch self {
        case .stimmgabel: return "STIMMGABEL"
        case .leier: return "LEIER"
        case .trommel: return "TROMMEL"
        case .floete: return "FLOETE"
        }
    }

    public var summary: String {
        switch self {
        case .stimmgabel: return "EIN SAUBERER TON, ZWEIMAL"
        case .leier: return "DREIKLANG - WEIT UND BREIT"
        case .trommel: return "DRUCKKUGEL - LANGSAM, ABER SIE REISST"
        case .floete: return "STICH - SCHNELL UND DURCHSCHLAGEND"
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
        }
    }
}
