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

/// Alles, was dauerhaft am Fortschritt haengt.
public struct Progression: Codable, Sendable, Equatable {
    /// Was sie kann. Faehigkeiten sind dauerhaft und liegen abseits des Wegs -
    /// sie werden nie getauscht, nur gefunden.
    public var abilities: Set<Ability>
    /// Gefundene Kerne und der eingesetzte.
    public var kerne: Set<Kern>
    public var kernWorn: Kern
    /// Lebenskristalle. Gerechnet wird intern in Haelften.
    public var crystals: Int
    public var maxResonance: Double
    /// Gelesene Inschriften, damit sie nicht erneut aufpoppen.
    public var readLore: Set<String>
    /// Gefundene Fassungen und die getragene.
    public var equipmentOwned: Set<String>
    public var equipmentWorn: String
    /// Gefundene Klingen und die gefuehrte. Rein aeusserlich.
    public var klingenOwned: Set<String>
    public var klingeWorn: String
    /// Siegel: gefunden, angelegt, und wie viele Kerben zur Verfuegung stehen.
    public var siegelOwned: Set<String>
    public var siegelWorn: [String]
    public var kerbenTotal: Int
    /// Der Bruch. Ein festes Ereignis am Ende, keine Wahl - und nicht
    /// rueckgaengig zu machen.
    public var gebrochen: Bool

    public init(abilities: Set<Ability> = [],
                kerne: Set<Kern> = [.stimmgabel],
                kernWorn: Kern = .stimmgabel,
                crystals: Int = 5,
                maxResonance: Double = 100,
                readLore: Set<String> = [],
                equipmentOwned: Set<String> = [EquipmentCatalog.ohne.id],
                equipmentWorn: String = EquipmentCatalog.ohne.id,
                klingenOwned: Set<String> = [KlingenKatalog.schlicht.id],
                klingeWorn: String = KlingenKatalog.schlicht.id,
                siegelOwned: Set<String> = [],
                siegelWorn: [String] = [],
                kerbenTotal: Int = 3,
                gebrochen: Bool = false) {
        self.abilities = abilities
        self.kerne = kerne
        self.kernWorn = kernWorn
        self.crystals = crystals
        self.maxResonance = maxResonance
        self.readLore = readLore
        self.equipmentOwned = equipmentOwned
        self.equipmentWorn = equipmentWorn
        self.klingenOwned = klingenOwned
        self.klingeWorn = klingeWorn
        self.siegelOwned = siegelOwned
        self.siegelWorn = siegelWorn
        self.kerbenTotal = kerbenTotal
        self.gebrochen = gebrochen
    }

    /// Die getragene Fassung. Ohne eine gueltige steht sie da, wie sie
    /// aufgewacht ist: ohne alles.
    public var equipment: Equipment {
        // Nach dem Bruch traegt sie nichts mehr. Es gibt kein Zurueck in
        // die Fassung - das ist der Punkt des Ereignisses.
        if gebrochen { return Bruch.entfesselt }
        guard equipmentOwned.contains(equipmentWorn),
              let found = EquipmentCatalog.find(equipmentWorn) else {
            return EquipmentCatalog.ohne
        }
        return found
    }

    /// Die gefuehrte Klinge. Rein aeusserlich - alle schlagen gleich.
    public var klinge: Klinge {
        guard klingenOwned.contains(klingeWorn),
              let found = KlingenKatalog.find(klingeWorn) else {
            return KlingenKatalog.schlicht
        }
        return found
    }

    /// Die angelegten Siegel, in der Reihenfolge, in der sie stecken.
    public var siegel: [Siegel] {
        siegelWorn.compactMap(SiegelKatalog.find)
    }

    public var kerbenBelegt: Int { siegel.reduce(0) { $0 + $1.kerben } }
    public var kerbenFrei: Int { kerbenTotal - kerbenBelegt }

    public var stats: Stats {
        Stats(equipment: equipment, kern: kernWorn, siegel: siegel,
              gebrochen: gebrochen)
    }

    public var ownedEquipment: [Equipment] {
        EquipmentCatalog.all.filter { equipmentOwned.contains($0.id) }
    }

    public var ownedKlingen: [Klinge] {
        KlingenKatalog.all.filter { klingenOwned.contains($0.id) }
    }

    public var ownedSiegel: [Siegel] {
        SiegelKatalog.all.filter { siegelOwned.contains($0.id) }
    }

    public func has(_ ability: Ability) -> Bool { abilities.contains(ability) }
    public func has(_ kern: Kern) -> Bool { kerne.contains(kern) }

    /// Reihenfolge fuer den Kernwechsel - immer stabil sortiert.
    public var orderedKerne: [Kern] {
        Kern.allCases.filter { kerne.contains($0) }
    }

    /// Legt ein Siegel an, wenn noch Kerben frei sind. Meldet den Erfolg.
    @discardableResult
    public mutating func anlegen(_ siegelID: String) -> Bool {
        guard siegelOwned.contains(siegelID),
              !siegelWorn.contains(siegelID),
              let s = SiegelKatalog.find(siegelID),
              s.kerben <= kerbenFrei
        else { return false }
        siegelWorn.append(siegelID)
        return true
    }

    @discardableResult
    public mutating func ablegen(_ siegelID: String) -> Bool {
        guard let index = siegelWorn.firstIndex(of: siegelID) else { return false }
        siegelWorn.remove(at: index)
        return true
    }
}

/// Der gespeicherte Spielstand. Gespeichert wird nur an einer Stimmgabel.
public struct SaveState: Codable, Sendable, Equatable {
    public static let currentVersion = 1

    public var version: Int
    public var roomID: String
    public var spawnName: String
    public var progression: Progression
    public var kern: Kern
    /// Zerschlagene Sperren, damit sie zerschlagen bleiben.
    public var brokenWalls: [String: [Int]]
    /// Bereits eingesammelte Fundstuecke ("A3/fluegelschlag").
    public var collected: Set<String>
    /// Wie oft welche Kreatur erlegt wurde. Traegt das Bestiarium: ein
    /// Eintrag oeffnet sich erst, wenn man oft genug mit ihr zu tun hatte.
    public var erlegt: [String: Int]
    /// Wem man ueberhaupt schon begegnet ist - auch ohne sie zu erlegen.
    public var gesehen: Set<String>
    /// Stimmen: was eine gefallene Kreatur zurücklaesst.
    ///
    /// Die Welt hat sich selbst gesungen, und was davon uebrig ist,
    /// steckt in ihren Bewohnern. Wer eine erlegt, bekommt den Rest -
    /// und im Dorf nimmt man das als Zahlung, weil es das Einzige ist,
    /// was dort noch jemand braucht.
    public var stimmen: Int
    /// Was im Dorf schon gekauft wurde. Jede Ware liegt genau einmal da.
    public var gekauft: Set<String>
    public var playTime: Double

    public init(roomID: String = "A1",
                spawnName: String = "start",
                progression: Progression = Progression(),
                kern: Kern = .leier,
                brokenWalls: [String: [Int]] = [:],
                collected: Set<String> = [],
                erlegt: [String: Int] = [:],
                gesehen: Set<String> = [],
                stimmen: Int = 0,
                gekauft: Set<String> = [],
                playTime: Double = 0) {
        self.version = Self.currentVersion
        self.roomID = roomID
        self.spawnName = spawnName
        self.progression = progression
        self.kern = kern
        self.brokenWalls = brokenWalls
        self.collected = collected
        self.erlegt = erlegt
        self.gesehen = gesehen
        self.stimmen = stimmen
        self.gekauft = gekauft
        self.playTime = playTime
    }

    /// Fehlende Felder werden nachgesehen, nicht bemaengelt.
    ///
    /// Ein Spielstand aus einer aelteren Fassung kennt das Bestiarium
    /// nicht. Ohne diesen Umweg wuerde das Laden daran scheitern - und
    /// jemand verloere seinen Spielstand, weil eine Liste dazugekommen
    /// ist. Neue Felder gehoeren darum immer mit Rueckfallwert gelesen.
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        version = try c.decodeIfPresent(Int.self, forKey: .version) ?? Self.currentVersion
        roomID = try c.decodeIfPresent(String.self, forKey: .roomID) ?? "A1"
        spawnName = try c.decodeIfPresent(String.self, forKey: .spawnName) ?? "start"
        progression = try c.decodeIfPresent(Progression.self, forKey: .progression)
            ?? Progression()
        kern = try c.decodeIfPresent(Kern.self, forKey: .kern) ?? .leier
        brokenWalls = try c.decodeIfPresent([String: [Int]].self, forKey: .brokenWalls) ?? [:]
        collected = try c.decodeIfPresent(Set<String>.self, forKey: .collected) ?? []
        erlegt = try c.decodeIfPresent([String: Int].self, forKey: .erlegt) ?? [:]
        gesehen = try c.decodeIfPresent(Set<String>.self, forKey: .gesehen) ?? []
        stimmen = try c.decodeIfPresent(Int.self, forKey: .stimmen) ?? 0
        gekauft = try c.decodeIfPresent(Set<String>.self, forKey: .gekauft) ?? []
        playTime = try c.decodeIfPresent(Double.self, forKey: .playTime) ?? 0
    }
}
