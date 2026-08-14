import Foundation

/// Die Bausteine eines Raums. Die Zeichen stammen aus den Level-JSONs,
/// die der Python-Generator schreibt.
public enum Tile: UInt8, Sendable, CaseIterable {
    case air = 0
    case solid
    /// Von unten durchlaessig, von oben begehbar.
    case platform
    /// Ein gebauter Balken: so schmal wie eine Plattform, aber fest -
    /// von unten NICHT durchspringbar. Das ist der Unterschied, der
    /// Plattformen wieder zu einer Entscheidung macht: die offene
    /// laesst jeden Weg zu, der Balken versperrt einen.
    case balken
    /// Dissonanzdornen am Boden - verletzen bei Beruehrung.
    case spike
    /// Dieselben Dornen, aber an der Decke haengend.
    case spikeDown
    /// An der linken Wand, Spitzen nach rechts.
    case spikeRight
    /// An der rechten Wand, Spitzen nach links.
    case spikeLeft
    /// Verstimmte Sperre. Nur der Basston bricht sie.
    case dissoWall
    /// Schraege, die nach rechts ansteigt (45 Grad).
    case slopeUp
    /// Schraege, die nach rechts abfaellt (45 Grad).
    case slopeDown
    /// Sanfte Steigung, untere Haelfte (zwei Kacheln je Hoehenkachel).
    case slopeUpLow
    /// Sanfte Steigung, obere Haelfte.
    case slopeUpHigh
    /// Sanftes Gefaelle, obere Haelfte.
    case slopeDownHigh
    /// Sanftes Gefaelle, untere Haelfte.
    case slopeDownLow

    // Und dasselbe an der Decke. Der Boden hat seine Stufen laengst zu
    // Rampen geglaettet; die Decke blieb eine Treppe, weil es nach oben
    // keine Schraegkacheln gab. Jetzt gibt es sie.
    /// Deckenschraege, faellt nach rechts, obere Haelfte.
    case ceilDownHigh
    /// Deckenschraege, faellt nach rechts, untere Haelfte.
    case ceilDownLow
    /// Deckenschraege, steigt nach rechts, untere Haelfte.
    case ceilUpLow
    /// Deckenschraege, steigt nach rechts, obere Haelfte.
    case ceilUpHigh

    public init(character: Character) {
        switch character {
        case "#": self = .solid
        case "=": self = .platform
        case "b": self = .balken
        case "^": self = .spike
        case "v": self = .spikeDown
        case ">": self = .spikeRight
        case "<": self = .spikeLeft
        case "D": self = .dissoWall
        case "/": self = .slopeUp
        case "\\": self = .slopeDown
        case "1": self = .slopeUpLow
        case "2": self = .slopeUpHigh
        case "3": self = .slopeDownHigh
        case "4": self = .slopeDownLow
        case "q": self = .ceilDownHigh
        case "w": self = .ceilDownLow
        case "e": self = .ceilUpLow
        case "r": self = .ceilUpHigh
        default: self = .air
        }
    }

    /// Blockiert Bewegung aus allen Richtungen.
    ///
    /// Schraegen blockieren waagerecht nicht - sonst liefe man gegen ihre
    /// Kachelkante wie gegen eine Wand. Ihre Oberflaeche wird stattdessen
    /// beim senkrechten Aufsetzen berechnet.
    public var isBlocking: Bool {
        switch self {
        case .solid, .dissoWall, .balken,
             .ceilDownHigh, .ceilDownLow, .ceilUpLow, .ceilUpHigh:
            // Deckenschraegen sperren wie Fels. Ihre Schraege ist eine
            // Sache des Bildes - unter dem Kopf zaehlt die ganze Kachel,
            // und eine halbe Kachel Spielraum am Scheitel merkt niemand.
            return true
        default:
            return false
        }
    }

    /// Zeigt die Kachel nach oben ins Gestein? Dann ist sie Decke.
    public var isCeilingSlope: Bool {
        switch self {
        case .ceilDownHigh, .ceilDownLow, .ceilUpLow, .ceilUpHigh: return true
        default: return false
        }
    }

    /// Name der Bildkachel fuer Deckenschraegen.
    public var ceilingSuffix: String {
        switch self {
        case .ceilDownHigh: return "downhigh"
        case .ceilDownLow: return "downlow"
        case .ceilUpLow: return "uplow"
        case .ceilUpHigh: return "uphigh"
        default: return ""
        }
    }

    public var isSlope: Bool {
        slopeRise != nil
    }

    /// Hoehe der Oberflaeche an linker und rechter Kachelkante, gemessen von
    /// der Oberkante nach unten (0 = oben, 1 = unten).
    ///
    /// Eine 45-Grad-Rampe laeuft von 1 auf 0. Die sanfte Variante teilt
    /// dieselbe Steigung auf zwei Kacheln auf - und genau die braucht es
    /// meistens: 45 Grad wirken im Gelaende wie eine Rutsche, nicht wie ein
    /// gewachsener Hang.
    public var slopeRise: (start: Double, end: Double)? {
        switch self {
        case .slopeUp: return (1.0, 0.0)
        case .slopeDown: return (0.0, 1.0)
        case .slopeUpLow: return (1.0, 0.5)
        case .slopeUpHigh: return (0.5, 0.0)
        case .slopeDownHigh: return (0.0, 0.5)
        case .slopeDownLow: return (0.5, 1.0)
        default: return nil
        }
    }

    /// Blockiert nur von oben, wenn die Figur faellt.
    public var isOneWay: Bool {
        self == .platform
    }

    /// Kann als Boden dienen.
    public var isStandable: Bool {
        isBlocking || isOneWay || isSlope
    }

    public var isHazard: Bool {
        switch self {
        case .spike, .spikeDown, .spikeLeft, .spikeRight: return true
        default: return false
        }
    }

    /// In welche Richtung die Spitzen zeigen. Dornen an der Decke sind
    /// dieselben Dornen - sie haengen nur andersherum, und wer das nicht
    /// zeichnet, hat Gras an der Decke.
    public var hazardSuffix: String {
        switch self {
        case .spikeDown: return "_down"
        case .spikeLeft: return "_left"
        case .spikeRight: return "_right"
        default: return ""
        }
    }
}

/// Regionen bestimmen Farbwelt, Kachelsatz und Musik.
public enum Region: String, Codable, Sendable, CaseIterable {
    case hain
    case kathedrale
    case grotten
    case dissonanz
    /// Die grosse Bruecke: kein Gang zwischen zwei Gebieten, sondern
    /// eines. Sie liegt als Einziges im Freien, und man geht sie in
    /// voller Laenge ab, statt sie zu ueberqueren.
    case bruecke

    public var displayName: String {
        switch self {
        case .hain: return "DER SCHLAFENDE HAIN"
        case .kathedrale: return "KATHEDRALE DER FUGEN"
        case .grotten: return "RESONANZKAVERNEN"
        case .dissonanz: return "HERZ DER DISSONANZ"
        case .bruecke: return "DIE GROSSE BRUECKE"
        }
    }
}
