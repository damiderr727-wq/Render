import Foundation

/// Die Bausteine eines Raums. Die Zeichen stammen aus den Level-JSONs,
/// die der Python-Generator schreibt.
public enum Tile: UInt8, Sendable, CaseIterable {
    case air = 0
    case solid
    /// Von unten durchlaessig, von oben begehbar.
    case platform
    /// Dissonanzdornen - verletzen bei Beruehrung.
    case spike
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

    public init(character: Character) {
        switch character {
        case "#": self = .solid
        case "=": self = .platform
        case "^": self = .spike
        case "D": self = .dissoWall
        case "/": self = .slopeUp
        case "\\": self = .slopeDown
        case "1": self = .slopeUpLow
        case "2": self = .slopeUpHigh
        case "3": self = .slopeDownHigh
        case "4": self = .slopeDownLow
        default: self = .air
        }
    }

    /// Blockiert Bewegung aus allen Richtungen.
    ///
    /// Schraegen blockieren waagerecht nicht - sonst liefe man gegen ihre
    /// Kachelkante wie gegen eine Wand. Ihre Oberflaeche wird stattdessen
    /// beim senkrechten Aufsetzen berechnet.
    public var isBlocking: Bool {
        self == .solid || self == .dissoWall
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
        self == .spike
    }
}

/// Regionen bestimmen Farbwelt, Kachelsatz und Musik.
public enum Region: String, Codable, Sendable, CaseIterable {
    case hain
    case kathedrale
    case grotten
    case dissonanz

    public var displayName: String {
        switch self {
        case .hain: return "DER SCHLAFENDE HAIN"
        case .kathedrale: return "KATHEDRALE DER FUGEN"
        case .grotten: return "RESONANZKAVERNEN"
        case .dissonanz: return "HERZ DER DISSONANZ"
        }
    }
}
