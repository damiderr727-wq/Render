import Foundation

/// Rohdaten eines Raums, so wie `Tools/gen_levels.py` sie schreibt.
///
/// Koordinaten sind Kacheleinheiten: `x` ist die Mitte einer Figur,
/// `y` ihre Fusslinie.
public struct RoomData: Codable, Sendable {
    public struct Door: Codable, Sendable {
        public let id: String
        public let x: Int
        public let y: Int
        public let w: Int
        public let h: Int
        public let target: String
        public let targetDoor: String
        /// Faehigkeit, ohne die dieser Weg geschlossen bleibt (nur Hinweis-Text;
        /// die eigentliche Sperre ist die Geometrie).
        public let requires: String?
    }

    public struct SpawnPoint: Codable, Sendable {
        public let x: Double
        public let y: Double
        public let facing: Int
    }

    public struct Placement: Codable, Sendable {
        public let x: Double
        public let y: Double
    }

    public struct EnemySpawn: Codable, Sendable {
        public let type: String
        public let x: Double
        public let y: Double
        public let patrol: Double?
    }

    public struct PickupSpawn: Codable, Sendable {
        public let kind: String
        public let id: String
        public let x: Double
        public let y: Double
    }

    public struct DecorSpawn: Codable, Sendable {
        public let kind: String
        public let size: Int?
        public let x: Double
        public let y: Double
    }

    public struct LoreSpawn: Codable, Sendable {
        public let x: Double
        public let y: Double
        public let text: String
    }

    public struct BossSpawn: Codable, Sendable {
        public struct Arena: Codable, Sendable {
            public let x: Int
            public let y: Int
            public let w: Int
            public let h: Int
        }
        public let type: String
        public let x: Double
        public let y: Double
        public let arena: Arena
    }

    public let id: String
    public let name: String
    public let region: Region
    public let music: String
    public let width: Int
    public let height: Int
    public let darkness: Double
    /// Welche Kulisse hinter dem Raum steht, falls nicht die der Region.
    ///
    /// Der Schattentempel liegt im Hain, soll aber nicht wie der Hain
    /// aussehen: er ist gebaut, nicht gewachsen. Kachelsatz und Musik
    /// bleiben beim Gebiet - nur die Schichten dahinter wechseln.
    ///
    /// Bewusst ein Name und keine Region: eine Kulisse ist Bildwerk und
    /// muss kein Gebiet sein. Der Tempel hat eine eigene, die es als
    /// Region gar nicht gibt.
    public let backdrop: String?

    /// Fehlt das Feld in aelteren Raumdaten, gilt die Region.
    public init(id: String, name: String, region: Region, music: String,
                width: Int, height: Int, darkness: Double,
                backdrop: String? = nil, tiles: [String], doors: [Door],
                spawns: [String: SpawnPoint], benches: [Placement],
                enemies: [EnemySpawn], pickups: [PickupSpawn],
                decor: [DecorSpawn], lore: [LoreSpawn], boss: BossSpawn?) {
        self.id = id
        self.name = name
        self.region = region
        self.music = music
        self.width = width
        self.height = height
        self.darkness = darkness
        self.backdrop = backdrop
        self.tiles = tiles
        self.doors = doors
        self.spawns = spawns
        self.benches = benches
        self.enemies = enemies
        self.pickups = pickups
        self.decor = decor
        self.lore = lore
        self.boss = boss
    }
    public let tiles: [String]
    public let doors: [Door]
    public let spawns: [String: SpawnPoint]
    public let benches: [Placement]
    public let enemies: [EnemySpawn]
    public let pickups: [PickupSpawn]
    public let decor: [DecorSpawn]
    public let lore: [LoreSpawn]
    public let boss: BossSpawn?
}

/// Der Weltindex: alle Raeume, Startpunkt, Verbindungen.
public struct WorldIndex: Codable, Sendable {
    public struct Entry: Codable, Sendable {
        public struct Connection: Codable, Sendable {
            public let door: String
            public let to: String
        }
        public let id: String
        public let name: String
        public let region: Region
        public let music: String
        public let width: Int
        public let height: Int
        public let connections: [Connection]
    }

    public let startRoom: String
    public let startSpawn: String
    public let rooms: [Entry]
}
