import Foundation

public enum FireMode: String, Sendable {
    case projectile   // ordinary bullets
    case burst        // n shots in quick succession per trigger pull
    case beam         // continuous hitscan while held
    case arc          // lobbed, explodes on landing
    case boomerang    // returns to the shooter
    case charge       // hold to charge, release for a big shot
    case orbit        // spawns motes that circle before striking
}

public enum WeaponTag: String, Sendable, CaseIterable {
    case kinetic, fire, ice, poison, shock, arcane, explosive
    case shotgun, automatic, precision, heavy, beam, holy, void
}

/// Static description of a gun. Copied and mutated per run by synergies, so
/// this is a value type on purpose.
public struct WeaponDef: Sendable {
    public var id: String
    public var name: String
    public var flavor: String
    public var sprite: String

    public var damage: Double = 8
    public var fireInterval: Double = 0.25
    public var projectileSpeed: Double = 420
    public var projectileSprite: String = "proj/bolt_player"
    public var projectileRadius: Double = 3
    public var projectileLife: Double = 1.4
    public var pellets: Int = 1
    public var spread: Double = 0
    public var magazine: Int = 12
    public var reserve: Int = 180        // -1 means infinite
    public var reloadTime: Double = 1.1
    public var knockback: Double = 60
    public var recoil: Double = 2
    public var mode: FireMode = .projectile
    public var burstCount: Int = 3
    public var burstInterval: Double = 0.06
    public var pierce: Int = 0
    public var bounces: Int = 0
    public var homing: Double = 0
    public var explodeRadius: Double = 0
    public var status: StatusKind? = nil
    public var statusChance: Double = 0
    public var chain: Int = 0
    public var chargeTime: Double = 0
    public var shake: Double = 1.5
    public var muzzleFX: String = "fx/muzzle_flash"
    public var impactFX: String = "fx/impact_spark"
    public var arcGravity: Double = 0
    public var curve: Double = 0          // sine weave amplitude
    public var beamRange: Double = 320
    public var rarity: Int = 1
    public var tags: Set<WeaponTag> = [.kinetic]

    public init(id: String, name: String, flavor: String, sprite: String? = nil) {
        self.id = id
        self.name = name
        self.flavor = flavor
        self.sprite = sprite ?? "weapon/\(id)"
    }

    public var isInfiniteAmmo: Bool { reserve < 0 }
}

/// Per-run mutable state for one carried gun.
public struct WeaponInstance: Sendable {
    public var def: WeaponDef
    public var ammoInMagazine: Int
    public var reserveAmmo: Int
    public var cooldown: Double = 0
    public var reloadRemaining: Double = 0
    public var burstRemaining: Int = 0
    public var burstTimer: Double = 0
    public var chargeHeld: Double = 0
    public var beamActive: Bool = false

    public init(def: WeaponDef) {
        self.def = def
        self.ammoInMagazine = def.magazine
        self.reserveAmmo = def.isInfiniteAmmo ? Int.max : def.reserve
    }

    public var isReloading: Bool { reloadRemaining > 0 }
    public var isEmpty: Bool { ammoInMagazine <= 0 }
    public var canRefill: Bool { def.isInfiniteAmmo || reserveAmmo > 0 }

    public var ammoText: String {
        def.isInfiniteAmmo ? "\(ammoInMagazine)/∞" : "\(ammoInMagazine)/\(reserveAmmo)"
    }

    public mutating func beginReload(speedMultiplier: Double) {
        guard !isReloading, ammoInMagazine < def.magazine, canRefill else { return }
        reloadRemaining = def.reloadTime / max(0.2, speedMultiplier)
        burstRemaining = 0
    }

    public mutating func finishReload() {
        let needed = def.magazine - ammoInMagazine
        if def.isInfiniteAmmo {
            ammoInMagazine = def.magazine
        } else {
            let taken = min(needed, reserveAmmo)
            ammoInMagazine += taken
            reserveAmmo -= taken
        }
        reloadRemaining = 0
    }

    public mutating func addAmmo(_ amount: Int) {
        guard !def.isInfiniteAmmo else { return }
        reserveAmmo = min(def.reserve, reserveAmmo + amount)
    }
}

/// One resolved shot request: the sim turns this into projectiles.
public struct ShotRequest: Sendable {
    public var origin: Vec2
    public var direction: Vec2
    public var def: WeaponDef
    public var stats: StatBlock
    public var faction: Faction
    public var owner: ActorID?
}

public enum WeaponMath {
    /// Effective interval between shots after fire-rate modifiers.
    public static func interval(_ def: WeaponDef, _ stats: StatBlock) -> Double {
        max(0.02, def.fireInterval / max(0.1, stats.fireRateMultiplier))
    }

    /// Total pellets after `extraProjectiles`. Shotguns get the bonus per
    /// trigger pull rather than per pellet, or +2 projectiles would double a
    /// six-pellet spread and trivialise the game.
    public static func pelletCount(_ def: WeaponDef, _ stats: StatBlock) -> Int {
        max(1, def.pellets + stats.extraProjectiles)
    }

    public static func damage(_ def: WeaponDef, _ stats: StatBlock) -> Double {
        def.damage * stats.damageMultiplier
    }

    /// Angles for one trigger pull, symmetric around the aim direction.
    public static func spreadAngles(count: Int, spread: Double,
                                    rng: inout RNG) -> [Double] {
        guard count > 1 else {
            return spread > 0 ? [rng.double(-spread, spread) * 0.5] : [0]
        }
        var angles: [Double] = []
        let step = spread / Double(count - 1)
        for i in 0..<count {
            let base = -spread / 2 + step * Double(i)
            angles.append(base + rng.double(-step, step) * 0.12)
        }
        return angles
    }
}
