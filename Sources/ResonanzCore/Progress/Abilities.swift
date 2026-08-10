import Foundation

/// Die Welt gibt nichts her, was sie nicht verloren hat. Jede Faehigkeit ist
/// ein Rest von etwas Lebendigem, das hier einmal geklungen hat.
public enum Ability: String, Codable, Sendable, CaseIterable {
    /// Der Fluegelschlag eines Vogels, der laengst fort ist: Doppelsprung.
    case fluegelschlag
    /// Klang, der in der Wand haengengeblieben ist: Wandhaftung und Wandsprung.
    case klangschritt
    /// Der Herzschlag einer schlafenden Kreatur: Sprint durch die Luft.
    case herzschlag
    /// Der Ton, den niemand singt: Bruchschlag nach unten.
    case basston

    public var displayName: String {
        switch self {
        case .fluegelschlag: return "FLUEGELSCHLAG"
        case .klangschritt: return "KLANGSCHRITT"
        case .herzschlag: return "HERZSCHLAG"
        case .basston: return "BASSTON"
        }
    }

    public var summary: String {
        switch self {
        case .fluegelschlag: return "EIN ZWEITER SPRUNG IN DER LUFT"
        case .klangschritt: return "AN WAENDEN HAFTEN UND ABSPRINGEN"
        case .herzschlag: return "EIN STOSS NACH VORN, UNVERWUNDBAR"
        case .basston: return "IM FALL NACH UNTEN SCHLAGEN"
        }
    }

    public var loreLine: String {
        switch self {
        case .fluegelschlag:
            return "DER VOGEL IST FORT. SEIN SCHLAG HAENGT NOCH IN DER LUFT."
        case .klangschritt:
            return "DER STEIN HAT ZUGEHOERT. JETZT TRAEGT ER DICH."
        case .herzschlag:
            return "ETWAS GROSSES SCHLAEFT HIER. LEIH DIR SEINEN TAKT."
        case .basston:
            return "MANCHE AKKORDE LOESEN SICH NICHT AUF. MAN MUSS SIE SCHLAGEN."
        }
    }
}

/// Die drei Startinstrumente. Die Waffe ist immer der Schall selbst -
/// das Instrument bestimmt nur seine Form.
public enum Instrument: String, Codable, Sendable, CaseIterable {
    /// Ausgewogen: weiter Bogen im Nahkampf, Dreiklang in die Ferne.
    case leier
    /// Schwer: kurze Reichweite, dafuer Wucht und Rueckstoss.
    case trommel
    /// Schnell und spitz: sticht, durchschlaegt, kostet wenig.
    case floete

    public var displayName: String {
        switch self {
        case .leier: return "LEIER"
        case .trommel: return "TROMMEL"
        case .floete: return "FLOETE"
        }
    }

    public var summary: String {
        switch self {
        case .leier: return "AUSGEWOGEN - BOGEN UND DREIKLANG"
        case .trommel: return "WUCHT - STOSSWELLE UND DRUCKKUGEL"
        case .floete: return "SCHNELL - STICH UND DURCHSCHLAG"
        }
    }
}

/// Alles, was dauerhaft am Fortschritt haengt.
public struct Progression: Codable, Sendable, Equatable {
    public var abilities: Set<Ability>
    public var instruments: Set<Instrument>
    public var maxHealth: Int
    public var maxResonance: Double
    /// Gelesene Inschriften, damit sie nicht erneut aufpoppen.
    public var readLore: Set<String>

    public init(abilities: Set<Ability> = [],
                instruments: Set<Instrument> = [.leier],
                maxHealth: Int = 5,
                maxResonance: Double = 100,
                readLore: Set<String> = []) {
        self.abilities = abilities
        self.instruments = instruments
        self.maxHealth = maxHealth
        self.maxResonance = maxResonance
        self.readLore = readLore
    }

    public func has(_ ability: Ability) -> Bool { abilities.contains(ability) }
    public func has(_ instrument: Instrument) -> Bool { instruments.contains(instrument) }

    /// Reihenfolge fuer den Instrumentenwechsel - immer stabil sortiert.
    public var orderedInstruments: [Instrument] {
        Instrument.allCases.filter { instruments.contains($0) }
    }
}

/// Der gespeicherte Spielstand. Gespeichert wird nur an einer Stimmgabel.
public struct SaveState: Codable, Sendable, Equatable {
    public static let currentVersion = 1

    public var version: Int
    public var roomID: String
    public var spawnName: String
    public var progression: Progression
    public var instrument: Instrument
    /// Zerschlagene Sperren, damit sie zerschlagen bleiben.
    public var brokenWalls: [String: [Int]]
    /// Bereits eingesammelte Fundstuecke ("A3/fluegelschlag").
    public var collected: Set<String>
    public var playTime: Double

    public init(roomID: String = "A1",
                spawnName: String = "start",
                progression: Progression = Progression(),
                instrument: Instrument = .leier,
                brokenWalls: [String: [Int]] = [:],
                collected: Set<String> = [],
                playTime: Double = 0) {
        self.version = Self.currentVersion
        self.roomID = roomID
        self.spawnName = spawnName
        self.progression = progression
        self.instrument = instrument
        self.brokenWalls = brokenWalls
        self.collected = collected
        self.playTime = playTime
    }
}
