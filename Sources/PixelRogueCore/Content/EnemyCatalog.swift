import Foundation

public enum EnemyRig: String, Sendable {
    /// Uses the shared humanoid rig: `char/<id>/<anim>`.
    case humanoid
    /// A single looping animation: `enemy/<id>`.
    case creature
    /// A boss sheet: `boss/<id>`.
    case boss
}

public enum EnemyBehavior: String, Sendable {
    case chaser      // straight at you, contact damage
    case shooter     // keeps distance, fires patterns
    case strafer     // circles at a preferred range while shooting
    case charger     // winds up, then dashes
    case turret      // never moves
    case bomber      // closes and detonates
    case flyer       // ignores walls, drifts
    case summoner    // spawns adds, keeps away
}

public struct EnemyDef: Sendable {
    public let id: String
    public let name: String
    public let rig: EnemyRig
    public let behavior: EnemyBehavior
    public let health: Double
    public let speed: Double
    public let radius: Double
    public let contactDamage: Double
    public let attack: AttackPattern?
    public let attackRange: Double
    public let attackCooldown: Double
    public let windUp: Double
    public let preferredRange: Double
    public let flying: Bool
    /// Spawn-budget cost. Rooms are filled to a budget rather than a count,
    /// so a room of three heavies feels as fair as a room of nine crawlers.
    public let threat: Int
    public let minFloor: Int
    public let coinValue: Int

    public var spriteBase: String {
        switch rig {
        case .humanoid: return "char/\(id)"
        case .creature: return "enemy/\(id)"
        case .boss: return "boss/\(id)"
        }
    }

    public init(id: String, name: String, rig: EnemyRig, behavior: EnemyBehavior,
                health: Double, speed: Double, radius: Double = 7,
                contactDamage: Double = 10, attack: AttackPattern? = nil,
                attackRange: Double = 220, attackCooldown: Double = 1.6,
                windUp: Double = 0.35, preferredRange: Double = 140,
                flying: Bool = false, threat: Int = 2, minFloor: Int = 1,
                coinValue: Int = 2) {
        self.id = id
        self.name = name
        self.rig = rig
        self.behavior = behavior
        self.health = health
        self.speed = speed
        self.radius = radius
        self.contactDamage = contactDamage
        self.attack = attack
        self.attackRange = attackRange
        self.attackCooldown = attackCooldown
        self.windUp = windUp
        self.preferredRange = preferredRange
        self.flying = flying
        self.threat = threat
        self.minFloor = minFloor
        self.coinValue = coinValue
    }
}

public enum EnemyCatalog {
    public static let all: [EnemyDef] = [
        // -- floor 1 ---------------------------------------------------------
        EnemyDef(id: "brigand", name: "Brigand", rig: .humanoid,
                 behavior: .shooter, health: 30, speed: 62,
                 contactDamage: 8,
                 attack: .aimed(count: 1, spread: 0.1, speed: 220, damage: 8,
                                sprite: "proj/bolt_enemy"),
                 attackRange: 240, attackCooldown: 1.5, preferredRange: 150,
                 threat: 2, minFloor: 1, coinValue: 2),

        EnemyDef(id: "crawler", name: "Crawler", rig: .creature,
                 behavior: .chaser, health: 22, speed: 96, radius: 8,
                 contactDamage: 12, attack: nil,
                 threat: 1, minFloor: 1, coinValue: 1),

        EnemyDef(id: "blob_green", name: "Ooze", rig: .creature,
                 behavior: .chaser, health: 34, speed: 44, radius: 9,
                 contactDamage: 10,
                 attack: .radial(count: 6, speed: 130, damage: 6,
                                 sprite: "proj/pellet_enemy",
                                 offsetByPhase: true),
                 attackRange: 130, attackCooldown: 2.4,
                 threat: 2, minFloor: 1, coinValue: 2),

        EnemyDef(id: "mothling", name: "Mothling", rig: .creature,
                 behavior: .flyer, health: 16, speed: 108, radius: 7,
                 contactDamage: 8, attack: nil,
                 flying: true, threat: 1, minFloor: 1, coinValue: 1),

        EnemyDef(id: "cultist", name: "Cultist", rig: .humanoid,
                 behavior: .strafer, health: 34, speed: 58,
                 contactDamage: 8,
                 attack: .wave(count: 5, arc: 0.9, speed: 165, speedStep: 22,
                               damage: 7, sprite: "proj/bolt_arcane"),
                 attackRange: 260, attackCooldown: 2.2, windUp: 0.5,
                 preferredRange: 175, threat: 3, minFloor: 1, coinValue: 3),

        // -- floor 2 ---------------------------------------------------------
        EnemyDef(id: "skelly", name: "Rattler", rig: .humanoid,
                 behavior: .charger, health: 26, speed: 74, radius: 6,
                 contactDamage: 14,
                 attack: .dash(speed: 320, duration: 0.45),
                 attackRange: 190, attackCooldown: 2.0, windUp: 0.55,
                 threat: 2, minFloor: 2, coinValue: 2),

        EnemyDef(id: "blob_red", name: "Clot", rig: .creature,
                 behavior: .chaser, health: 26, speed: 66, radius: 8,
                 contactDamage: 14,
                 attack: .serpent(count: 3, spread: 0.7, speed: 150,
                                  curve: 34, damage: 7,
                                  sprite: "proj/pellet_enemy"),
                 attackRange: 160, attackCooldown: 2.0,
                 threat: 2, minFloor: 2, coinValue: 2),

        EnemyDef(id: "turret", name: "Wall Gun", rig: .creature,
                 behavior: .turret, health: 46, speed: 0, radius: 8,
                 contactDamage: 0,
                 attack: .spiral(arms: 3, speed: 145, damage: 7,
                                 sprite: "proj/pellet_enemy",
                                 turnPerVolley: 0.55),
                 attackRange: 320, attackCooldown: 0.62, windUp: 0.2,
                 threat: 3, minFloor: 2, coinValue: 3),

        EnemyDef(id: "imp", name: "Fuse Imp", rig: .creature,
                 behavior: .bomber, health: 18, speed: 118, radius: 7,
                 contactDamage: 0,
                 attack: .detonate(radius: 66, damage: 26),
                 attackRange: 34, attackCooldown: 0.1, windUp: 0.7,
                 threat: 2, minFloor: 2, coinValue: 2),

        EnemyDef(id: "gunner", name: "Gunner", rig: .humanoid,
                 behavior: .strafer, health: 40, speed: 66,
                 contactDamage: 8,
                 attack: .aimed(count: 3, spread: 0.28, speed: 250, damage: 7,
                                sprite: "proj/bolt_enemy"),
                 attackRange: 280, attackCooldown: 1.7, windUp: 0.4,
                 preferredRange: 190, threat: 3, minFloor: 2, coinValue: 3),

        // -- floor 3 ---------------------------------------------------------
        EnemyDef(id: "watcher", name: "Watcher", rig: .creature,
                 behavior: .flyer, health: 32, speed: 58, radius: 8,
                 contactDamage: 10,
                 attack: .seekers(count: 3, speed: 95, homing: 1.6, damage: 9,
                                  sprite: "proj/orb_enemy"),
                 attackRange: 300, attackCooldown: 2.8, windUp: 0.6,
                 flying: true, threat: 3, minFloor: 3, coinValue: 3),

        EnemyDef(id: "zealot", name: "Zealot", rig: .humanoid,
                 behavior: .shooter, health: 48, speed: 60,
                 contactDamage: 12,
                 attack: .ringGap(count: 14, gapWidth: 1.1, speed: 150,
                                  damage: 8, sprite: "proj/pellet_enemy"),
                 attackRange: 280, attackCooldown: 2.6, windUp: 0.6,
                 preferredRange: 160, threat: 4, minFloor: 3, coinValue: 4),

        EnemyDef(id: "warden", name: "Warden", rig: .humanoid,
                 behavior: .charger, health: 90, speed: 52, radius: 9,
                 contactDamage: 18,
                 attack: .dash(speed: 300, duration: 0.6),
                 attackRange: 230, attackCooldown: 2.4, windUp: 0.75,
                 threat: 5, minFloor: 3, coinValue: 6),

        EnemyDef(id: "sentry", name: "Sentry", rig: .creature,
                 behavior: .strafer, health: 44, speed: 78, radius: 8,
                 contactDamage: 8,
                 attack: .cross(perArm: 3, spacing: 16, speed: 165, damage: 7,
                                sprite: "proj/pellet_small"),
                 attackRange: 280, attackCooldown: 2.2, windUp: 0.45,
                 preferredRange: 175, flying: true, threat: 4, minFloor: 3,
                 coinValue: 4),

        // -- floor 4 ---------------------------------------------------------
        EnemyDef(id: "hexer", name: "Hexer", rig: .humanoid,
                 behavior: .summoner, health: 56, speed: 54,
                 contactDamage: 8,
                 attack: .summon(kind: "mothling", count: 2),
                 attackRange: 320, attackCooldown: 4.5, windUp: 0.9,
                 preferredRange: 210, threat: 5, minFloor: 4, coinValue: 6),

        EnemyDef(id: "blob_ice", name: "Rime", rig: .creature,
                 behavior: .chaser, health: 54, speed: 40, radius: 10,
                 contactDamage: 14,
                 attack: .flower(petals: 4, perPetal: 3, petalSpread: 0.4,
                                 speed: 140, damage: 8,
                                 sprite: "proj/shard_ice"),
                 attackRange: 200, attackCooldown: 2.6,
                 threat: 4, minFloor: 4, coinValue: 4),

        EnemyDef(id: "marauder", name: "Marauder", rig: .humanoid,
                 behavior: .chaser, health: 78, speed: 84, radius: 9,
                 contactDamage: 20, attack: nil,
                 threat: 4, minFloor: 4, coinValue: 5),

        EnemyDef(id: "crawler_steel", name: "Iron Crawler", rig: .creature,
                 behavior: .chaser, health: 46, speed: 118, radius: 8,
                 contactDamage: 16, attack: nil,
                 threat: 3, minFloor: 4, coinValue: 3),

        EnemyDef(id: "watcher_void", name: "Void Watcher", rig: .creature,
                 behavior: .flyer, health: 60, speed: 62, radius: 9,
                 contactDamage: 14,
                 attack: .flower(petals: 5, perPetal: 4, petalSpread: 0.45,
                                 speed: 155, damage: 9,
                                 sprite: "proj/orb_void"),
                 attackRange: 340, attackCooldown: 3.0, windUp: 0.7,
                 flying: true, threat: 6, minFloor: 5, coinValue: 7),

        EnemyDef(id: "mothling_ember", name: "Ember Moth", rig: .creature,
                 behavior: .flyer, health: 26, speed: 128, radius: 7,
                 contactDamage: 12,
                 attack: .aimed(count: 1, spread: 0, speed: 200, damage: 8,
                                sprite: "proj/bolt_toxic"),
                 attackRange: 200, attackCooldown: 2.0,
                 flying: true, threat: 2, minFloor: 5, coinValue: 2),
    ]

    private static var byID: [String: EnemyDef] {
        Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0) })
    }

    public static func enemy(_ id: String) -> EnemyDef? { byID[id] }

    public static func available(onFloor floor: Int) -> [EnemyDef] {
        let pool = all.filter { $0.minFloor <= floor }
        return pool.isEmpty ? all : pool
    }

    /// Fills a room to a threat budget. Weighting toward newer enemies keeps
    /// later floors from feeling like floor one with more hit points.
    public static func roll(budget: Int, floor: Int, rng: inout RNG) -> [EnemyDef] {
        var remaining = budget
        var picked: [EnemyDef] = []
        let pool = available(onFloor: floor)
        var attempts = 0

        while remaining > 0 && attempts < 60 {
            attempts += 1
            let affordable = pool.filter { $0.threat <= remaining }
            guard !affordable.isEmpty else { break }
            let weights = affordable.map { def -> (value: EnemyDef, weight: Double) in
                let freshness = 1.0 + Double(def.minFloor) * 0.35
                return (def, freshness)
            }
            guard let choice = rng.weighted(weights) else { break }
            picked.append(choice)
            remaining -= choice.threat
        }
        return picked
    }
}
