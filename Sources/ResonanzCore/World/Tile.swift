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

    public init(character: Character) {
        switch character {
        case "#": self = .solid
        case "=": self = .platform
        case "^": self = .spike
        case "D": self = .dissoWall
        default: self = .air
        }
    }

    /// Blockiert Bewegung aus allen Richtungen.
    public var isBlocking: Bool {
        self == .solid || self == .dissoWall
    }

    /// Blockiert nur von oben, wenn die Figur faellt.
    public var isOneWay: Bool {
        self == .platform
    }

    /// Kann als Boden dienen.
    public var isStandable: Bool {
        isBlocking || isOneWay
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
