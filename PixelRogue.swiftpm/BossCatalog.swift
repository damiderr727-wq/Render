import Foundation

/// One attack a boss can choose, with its own timing.
public struct BossMove: Sendable {
    public let name: String
    public let pattern: AttackPattern
    /// Repeats of the pattern inside one move, e.g. a five-volley spiral.
    public let volleys: Int
    public let volleyInterval: Double
    public let windUp: Double
    public let recover: Double
    public let weight: Double
    /// Movement while executing: bosses that stand still are free damage.
    public let drift: BossDrift

    public init(name: String, pattern: AttackPattern, volleys: Int = 1,
                volleyInterval: Double = 0.18, windUp: Double = 0.6,
                recover: Double = 0.7, weight: Double = 1,
                drift: BossDrift = .hold) {
        self.name = name
        self.pattern = pattern
        self.volleys = volleys
        self.volleyInterval = volleyInterval
        self.windUp = windUp
        self.recover = recover
        self.weight = weight
        self.drift = drift
    }
}

public enum BossDrift: String, Sendable {
    case hold        // stay put
    case approach    // close on the player
    case retreat     // back away
    case circle      // strafe around the player
    case reposition  // dart to a new anchor point
}

public struct BossPhase: Sendable {
    /// Phase begins when health drops below this fraction.
    public let healthThreshold: Double
    public let moves: [BossMove]
    public let speedMultiplier: Double
    public let announcement: String

    public init(healthThreshold: Double, moves: [BossMove],
                speedMultiplier: Double = 1, announcement: String = "") {
        self.healthThreshold = healthThreshold
        self.moves = moves
        self.speedMultiplier = speedMultiplier
        self.announcement = announcement
    }
}

public struct BossDef: Sendable {
    public let id: String
    public let name: String
    public let title: String
    public let health: Double
    public let radius: Double
    public let speed: Double
    public let contactDamage: Double
    public let phases: [BossPhase]
    public let floor: Int

    public var spriteBase: String { "boss/\(id)" }

    /// Index of the phase that matches a health fraction. Phases are listed
    /// from full health downward.
    public func phaseIndex(forHealthFraction fraction: Double) -> Int {
        var index = 0
        for (i, phase) in phases.enumerated() where fraction <= phase.healthThreshold {
            index = i
        }
        return index
    }
}

public enum BossCatalog {
    public static let all: [BossDef] = [colossus, hiveMother, clockworkChoir,
                                        voidSovereign]

    public static func boss(forFloor floor: Int) -> BossDef {
        all.first { $0.floor == floor } ?? all[min(all.count - 1, max(0, floor - 1))]
    }

    public static func boss(_ id: String) -> BossDef? {
        all.first { $0.id == id }
    }

    // -- floor 1 -------------------------------------------------------------

    public static let colossus = BossDef(
        id: "colossus", name: "The Colossus", title: "Warden of the First Gate",
        health: 620, radius: 22, speed: 46, contactDamage: 22,
        phases: [
            BossPhase(healthThreshold: 1.0, moves: [
                BossMove(name: "Siege Volley",
                         pattern: .aimed(count: 5, spread: 0.55, speed: 190,
                                         damage: 9, sprite: "proj/bolt_enemy"),
                         volleys: 3, volleyInterval: 0.22, windUp: 0.65,
                         weight: 2, drift: .approach),
                BossMove(name: "Ground Slam",
                         pattern: .radial(count: 18, speed: 165, damage: 10,
                                          sprite: "proj/pellet_enemy",
                                          offsetByPhase: true),
                         windUp: 0.9, recover: 0.9, weight: 1.4, drift: .hold),
                BossMove(name: "Charge",
                         pattern: .dash(speed: 340, duration: 0.7),
                         windUp: 0.8, recover: 0.8, weight: 1, drift: .hold),
            ], announcement: "THE COLOSSUS AWAKENS"),

            BossPhase(healthThreshold: 0.55, moves: [
                BossMove(name: "Sweeping Fire",
                         pattern: .spiral(arms: 4, speed: 175, damage: 9,
                                          sprite: "proj/pellet_enemy",
                                          turnPerVolley: 0.42),
                         volleys: 9, volleyInterval: 0.11, windUp: 0.55,
                         weight: 2, drift: .circle),
                BossMove(name: "Shrapnel Ring",
                         pattern: .ringGap(count: 20, gapWidth: 0.9, speed: 185,
                                           damage: 10,
                                           sprite: "proj/pellet_enemy"),
                         volleys: 3, volleyInterval: 0.42, windUp: 0.7,
                         weight: 1.6, drift: .hold),
                BossMove(name: "Charge",
                         pattern: .dash(speed: 400, duration: 0.75),
                         windUp: 0.6, recover: 0.6, weight: 1.2, drift: .hold),
            ], speedMultiplier: 1.25, announcement: "ARMOUR BREACHED"),

            BossPhase(healthThreshold: 0.25, moves: [
                BossMove(name: "Last Stand",
                         pattern: .flower(petals: 6, perPetal: 4,
                                          petalSpread: 0.42, speed: 195,
                                          damage: 11,
                                          sprite: "proj/bolt_enemy"),
                         volleys: 4, volleyInterval: 0.3, windUp: 0.5,
                         weight: 2, drift: .reposition),
                BossMove(name: "Guardians",
                         pattern: .summon(kind: "turret", count: 2),
                         windUp: 1.0, recover: 1.0, weight: 1, drift: .hold),
            ], speedMultiplier: 1.5, announcement: "CORE EXPOSED"),
        ],
        floor: 1)

    // -- floor 2 -------------------------------------------------------------

    public static let hiveMother = BossDef(
        id: "hive_mother", name: "The Hive Mother", title: "She Who Divides",
        health: 780, radius: 24, speed: 38, contactDamage: 20,
        phases: [
            BossPhase(healthThreshold: 1.0, moves: [
                BossMove(name: "Spawn Brood",
                         pattern: .summon(kind: "crawler", count: 3),
                         windUp: 1.0, recover: 0.8, weight: 1.4, drift: .retreat),
                BossMove(name: "Bile Wave",
                         pattern: .wave(count: 9, arc: 1.5, speed: 150,
                                        speedStep: 18, damage: 9,
                                        sprite: "proj/bolt_toxic"),
                         volleys: 2, volleyInterval: 0.35, windUp: 0.7,
                         weight: 2, drift: .hold),
                BossMove(name: "Creeping Spores",
                         pattern: .seekers(count: 5, speed: 80, homing: 1.2,
                                           damage: 8, sprite: "proj/orb_enemy"),
                         windUp: 0.8, weight: 1.5, drift: .circle),
            ], announcement: "THE HIVE STIRS"),

            BossPhase(healthThreshold: 0.6, moves: [
                BossMove(name: "Rupture",
                         pattern: .radial(count: 24, speed: 160, damage: 9,
                                          sprite: "proj/pellet_enemy",
                                          offsetByPhase: true),
                         volleys: 4, volleyInterval: 0.28, windUp: 0.6,
                         weight: 2, drift: .hold),
                BossMove(name: "Spawn Brood",
                         pattern: .summon(kind: "blob_red", count: 3),
                         windUp: 0.9, weight: 1.6, drift: .retreat),
                BossMove(name: "Braided Bile",
                         pattern: .serpent(count: 6, spread: 1.2, speed: 165,
                                           curve: 42, damage: 9,
                                           sprite: "proj/bolt_toxic"),
                         volleys: 3, volleyInterval: 0.3, windUp: 0.6,
                         weight: 1.8, drift: .approach),
            ], speedMultiplier: 1.2, announcement: "THE SAC SPLITS"),

            BossPhase(healthThreshold: 0.28, moves: [
                BossMove(name: "Final Clutch",
                         pattern: .summon(kind: "imp", count: 4),
                         windUp: 0.9, weight: 1.4, drift: .reposition),
                BossMove(name: "Death Bloom",
                         pattern: .flower(petals: 7, perPetal: 5,
                                          petalSpread: 0.5, speed: 175,
                                          damage: 10, sprite: "proj/bolt_toxic"),
                         volleys: 5, volleyInterval: 0.24, windUp: 0.5,
                         weight: 2.4, drift: .hold),
            ], speedMultiplier: 1.35, announcement: "SHE WILL NOT STOP"),
        ],
        floor: 2)

    // -- floor 3 -------------------------------------------------------------

    public static let clockworkChoir = BossDef(
        id: "clockwork_choir", name: "The Clockwork Choir",
        title: "Seven Voices, One Spring",
        health: 900, radius: 22, speed: 62, contactDamage: 18,
        phases: [
            BossPhase(healthThreshold: 1.0, moves: [
                BossMove(name: "Metronome",
                         pattern: .cross(perArm: 5, spacing: 18, speed: 175,
                                         damage: 9,
                                         sprite: "proj/pellet_small"),
                         volleys: 6, volleyInterval: 0.2, windUp: 0.5,
                         weight: 2, drift: .circle),
                BossMove(name: "Chorus",
                         pattern: .radial(count: 16, speed: 150, damage: 8,
                                          sprite: "proj/pellet_small",
                                          offsetByPhase: true),
                         volleys: 5, volleyInterval: 0.22, windUp: 0.5,
                         weight: 1.8, drift: .hold),
                BossMove(name: "Winding",
                         pattern: .spiral(arms: 5, speed: 165, damage: 9,
                                          sprite: "proj/pellet_enemy",
                                          turnPerVolley: 0.31),
                         volleys: 14, volleyInterval: 0.09, windUp: 0.6,
                         weight: 2, drift: .hold),
            ], announcement: "THE CHOIR TAKES A BREATH"),

            BossPhase(healthThreshold: 0.62, moves: [
                BossMove(name: "Counterpoint",
                         pattern: .spiral(arms: 6, speed: 180, damage: 9,
                                          sprite: "proj/pellet_small",
                                          turnPerVolley: -0.28),
                         volleys: 18, volleyInterval: 0.08, windUp: 0.5,
                         weight: 2.4, drift: .reposition),
                BossMove(name: "Cascade",
                         pattern: .ringGap(count: 26, gapWidth: 0.75,
                                           speed: 175, damage: 10,
                                           sprite: "proj/pellet_enemy"),
                         volleys: 4, volleyInterval: 0.36, windUp: 0.55,
                         weight: 2, drift: .hold),
            ], speedMultiplier: 1.2, announcement: "TEMPO RISING"),

            BossPhase(healthThreshold: 0.3, moves: [
                BossMove(name: "Crescendo",
                         pattern: .flower(petals: 8, perPetal: 4,
                                          petalSpread: 0.36, speed: 190,
                                          damage: 10,
                                          sprite: "proj/pellet_small"),
                         volleys: 7, volleyInterval: 0.19, windUp: 0.4,
                         weight: 2.6, drift: .circle),
                BossMove(name: "Discord",
                         pattern: .seekers(count: 7, speed: 105, homing: 2.0,
                                           damage: 9, sprite: "proj/orb_plasma"),
                         windUp: 0.6, weight: 1.6, drift: .retreat),
            ], speedMultiplier: 1.45, announcement: "ALL SEVEN AT ONCE"),
        ],
        floor: 3)

    // -- floor 4 (final) -----------------------------------------------------

    public static let voidSovereign = BossDef(
        id: "void_sovereign", name: "The Void Sovereign",
        title: "Last Thing To Look At You",
        health: 1250, radius: 24, speed: 58, contactDamage: 24,
        phases: [
            BossPhase(healthThreshold: 1.0, moves: [
                BossMove(name: "Regard",
                         pattern: .aimed(count: 7, spread: 0.95, speed: 210,
                                         damage: 10, sprite: "proj/orb_void"),
                         volleys: 3, volleyInterval: 0.24, windUp: 0.55,
                         weight: 2, drift: .reposition),
                BossMove(name: "Event Horizon",
                         pattern: .ringGap(count: 28, gapWidth: 0.85,
                                           speed: 165, damage: 11,
                                           sprite: "proj/pellet_enemy"),
                         volleys: 4, volleyInterval: 0.34, windUp: 0.6,
                         weight: 2, drift: .hold),
                BossMove(name: "Attendants",
                         pattern: .summon(kind: "watcher", count: 2),
                         windUp: 0.9, weight: 1.2, drift: .retreat),
            ], announcement: "THE SOVEREIGN LOOKS UP"),

            BossPhase(healthThreshold: 0.66, moves: [
                BossMove(name: "Collapse",
                         pattern: .spiral(arms: 7, speed: 185, damage: 10,
                                          sprite: "proj/orb_void",
                                          turnPerVolley: 0.24),
                         volleys: 20, volleyInterval: 0.075, windUp: 0.5,
                         weight: 2.4, drift: .circle),
                BossMove(name: "Starfall",
                         pattern: .flower(petals: 6, perPetal: 5,
                                          petalSpread: 0.44, speed: 185,
                                          damage: 11,
                                          sprite: "proj/pellet_enemy"),
                         volleys: 5, volleyInterval: 0.22, windUp: 0.45,
                         weight: 2.2, drift: .hold),
            ], speedMultiplier: 1.2, announcement: "THE CROWN CRACKS"),

            BossPhase(healthThreshold: 0.35, moves: [
                BossMove(name: "Unmaking",
                         pattern: .spiral(arms: 9, speed: 200, damage: 11,
                                          sprite: "proj/orb_void",
                                          turnPerVolley: -0.19),
                         volleys: 26, volleyInterval: 0.065, windUp: 0.4,
                         weight: 3, drift: .reposition),
                BossMove(name: "The Long Dark",
                         pattern: .seekers(count: 9, speed: 110, homing: 2.4,
                                           damage: 10, sprite: "proj/orb_void"),
                         windUp: 0.55, weight: 1.8, drift: .hold),
                BossMove(name: "Court of Eyes",
                         pattern: .summon(kind: "watcher_void", count: 3),
                         windUp: 0.9, weight: 1, drift: .retreat),
            ], speedMultiplier: 1.5, announcement: "NOTHING LOOKS BACK"),
        ],
        floor: 4)
}
