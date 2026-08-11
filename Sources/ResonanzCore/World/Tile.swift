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
    /// Schraege, die nach rechts ansteigt.
    case slopeUp
    /// Schraege, die nach rechts abfaellt.
    case slopeDown

    public init(character: Character) {
        switch character {
        case "#": self = .solid
        case "=": self = .platform
        case "^": self = .spike
        case "D": self = .dissoWall
        case "/": self = .slopeUp
        case "\\": self = .slopeDown
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
        self == .slopeUp || self == .slopeDown
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
