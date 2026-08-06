import Foundation

/// Status ailments a projectile can inflict.
public enum StatusKind: String, Sendable, CaseIterable {
    case burn      // damage over time, spreads on death
    case chill     // slows; stacking to full freezes
    case poison    // damage over time that ignores armour
    case shock     // brief stun, chains to a nearby target
    case curse     // takes extra damage from everything

    public var defaultDuration: Double {
        switch self {
        case .burn: return 3.0
        case .chill: return 2.5
        case .poison: return 4.0
        case .shock: return 0.8
        case .curse: return 5.0
        }
    }

    public var tickDamage: Double {
        switch self {
        case .burn: return 4
        case .poison: return 3
        default: return 0
        }
    }
}

public struct StatusEffect: Sendable {
    public var kind: StatusKind
    public var remaining: Double
    public var stacks: Int
    public var tickTimer: Double
    public var sourceDamage: Double

    public init(kind: StatusKind, duration: Double, stacks: Int = 1,
                sourceDamage: Double = 0) {
        self.kind = kind
        self.remaining = duration
        self.stacks = stacks
        self.tickTimer = 0
        self.sourceDamage = sourceDamage
    }
}

/// Everything items and synergies can change about the player.
///
/// Multipliers rather than flat adds almost everywhere, so a build stacks
/// smoothly instead of a single early item dominating the run.
public struct StatBlock: Sendable {
    public var damageMultiplier: Double = 1
    public var fireRateMultiplier: Double = 1
    public var reloadSpeedMultiplier: Double = 1
    public var projectileSpeedMultiplier: Double = 1
    public var projectileSizeMultiplier: Double = 1
    public var projectileRangeMultiplier: Double = 1
    public var extraProjectiles: Int = 0
    public var spreadMultiplier: Double = 1
    public var pierce: Int = 0
    public var bounces: Int = 0
    public var homingStrength: Double = 0
    public var critChance: Double = 0.05
    public var critMultiplier: Double = 2.0

    public var moveSpeedMultiplier: Double = 1
    public var dodgeCooldownMultiplier: Double = 1
    public var dodgeDistanceMultiplier: Double = 1
    public var maxHealthBonus: Double = 0
    public var startingArmor: Int = 0
    public var contactDamage: Double = 0
    public var reflectChance: Double = 0
    public var invulnBonus: Double = 0

    public var ammoMultiplier: Double = 1
    public var pickupRadiusBonus: Double = 0
    public var luck: Double = 0
    public var coinMultiplier: Double = 1
    public var shopDiscount: Double = 0

    public var lifestealOnKill: Double = 0
    public var healOnKillChance: Double = 0
    public var explosiveShots: Bool = false
    public var explosionRadiusBonus: Double = 0
    public var orbitals: Int = 0
    public var blankOnHit: Bool = false
    public var timeSlowOnHit: Double = 0
    public var knockbackMultiplier: Double = 1

    /// Chance to apply each status on hit.
    public var statusChance: [StatusKind: Double] = [:]
    /// Multiplier on damage dealt to targets already suffering that status.
    public var statusDamageBonus: [StatusKind: Double] = [:]

    public init() {}

    public mutating func addStatusChance(_ kind: StatusKind, _ amount: Double) {
        statusChance[kind, default: 0] += amount
    }

    public mutating func addStatusDamageBonus(_ kind: StatusKind, _ amount: Double) {
        statusDamageBonus[kind, default: 0] += amount
    }

    public func chance(for kind: StatusKind) -> Double {
        min(1.0, statusChance[kind] ?? 0)
    }
}

/// Applied to a target when something hits it.
public struct DamageInfo: Sendable {
    public var amount: Double
    public var source: Vec2
    public var knockback: Double
    public var isCrit: Bool
    public var status: StatusKind?
    public var faction: Faction

    public init(amount: Double, source: Vec2, knockback: Double = 0,
                isCrit: Bool = false, status: StatusKind? = nil,
                faction: Faction = .player) {
        self.amount = amount
        self.source = source
        self.knockback = knockback
        self.isCrit = isCrit
        self.status = status
        self.faction = faction
    }
}

public enum Faction: UInt8, Sendable {
    case player
    case enemy
    case neutral

    public func isHostile(to other: Faction) -> Bool {
        (self == .player && other == .enemy) || (self == .enemy && other == .player)
    }
}
