import Foundation

/// The sixteen guns.
///
/// Balance intent: every weapon should have a range band where it is clearly
/// the best thing you own and a band where it is clearly the worst, so
/// swapping weapons mid-fight is a real decision rather than an upgrade
/// ladder.
public enum WeaponCatalog {
    public static let all: [WeaponDef] = [
        peacemaker, scattergun, ripper, longarm, hexbolt, thumper, arcCoil,
        flamer, cryoLance, nailDriver, boneSaw, starCaller, handCannon,
        plagueCenser, voidNeedle, sunburst,
    ]

    private static var byID: [String: WeaponDef] {
        Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0) })
    }

    public static func weapon(_ id: String) -> WeaponDef? { byID[id] }

    public static let starter = peacemaker

    /// Drop pool weighted by rarity, biased upward by luck.
    public static func randomDrop(rng: inout RNG, luck: Double = 0,
                                  excluding owned: Set<String> = []) -> WeaponDef {
        let pool = all.filter { !owned.contains($0.id) && $0.id != peacemaker.id }
        let candidates = pool.isEmpty ? all : pool
        let weights = candidates.map { def -> (value: WeaponDef, weight: Double) in
            let base = [3.0, 2.0, 1.0][min(2, max(0, def.rarity - 1))]
            let luckBoost = def.rarity >= 2 ? 1 + luck * 0.5 : 1
            return (def, base * luckBoost)
        }
        return rng.weighted(weights) ?? peacemaker
    }

    // -- definitions --------------------------------------------------------

    public static var peacemaker: WeaponDef {
        var w = WeaponDef(id: "peacemaker", name: "Peacemaker",
                          flavor: "Six shots, six problems.")
        w.damage = 11
        w.fireInterval = 0.28
        w.projectileSpeed = 460
        w.magazine = 6
        w.reserve = -1                 // starter gun never runs dry
        w.reloadTime = 0.9
        w.knockback = 70
        w.tags = [.kinetic, .precision]
        return w
    }

    public static var scattergun: WeaponDef {
        var w = WeaponDef(id: "scattergun", name: "Scattergun",
                          flavor: "Answers most questions at once.")
        w.damage = 5.5
        w.pellets = 7
        w.spread = 0.55
        w.fireInterval = 0.62
        w.projectileSpeed = 400
        w.projectileLife = 0.42        // short life is the range limiter
        w.projectileSprite = "proj/pellet_player"
        w.projectileRadius = 2.5
        w.magazine = 2
        w.reserve = 40
        w.reloadTime = 1.3
        w.knockback = 130
        w.recoil = 6
        w.shake = 3.5
        w.rarity = 1
        w.tags = [.kinetic, .shotgun]
        return w
    }

    public static var ripper: WeaponDef {
        var w = WeaponDef(id: "ripper", name: "Ripper",
                          flavor: "Trigger discipline optional.")
        w.damage = 3.4
        w.fireInterval = 0.075
        w.spread = 0.16
        w.projectileSpeed = 520
        w.projectileRadius = 2.5
        w.magazine = 40
        w.reserve = 400
        w.reloadTime = 1.4
        w.knockback = 24
        w.recoil = 1
        w.shake = 0.8
        w.tags = [.kinetic, .automatic]
        return w
    }

    public static var longarm: WeaponDef {
        var w = WeaponDef(id: "longarm", name: "Longarm",
                          flavor: "One number, very large.")
        w.damage = 42
        w.fireInterval = 0.95
        w.projectileSpeed = 900
        w.projectileSprite = "proj/bolt_heavy"
        w.projectileRadius = 4
        w.projectileLife = 1.6
        w.pierce = 2
        w.magazine = 4
        w.reserve = 48
        w.reloadTime = 1.6
        w.knockback = 150
        w.recoil = 7
        w.shake = 4
        w.rarity = 2
        w.tags = [.kinetic, .precision, .heavy]
        return w
    }

    public static var hexbolt: WeaponDef {
        var w = WeaponDef(id: "hexbolt", name: "Hexbolt Wand",
                          flavor: "It knows where you meant to point it.")
        w.damage = 9
        w.fireInterval = 0.34
        w.projectileSpeed = 300
        w.projectileSprite = "proj/bolt_arcane"
        w.projectileRadius = 3.5
        w.projectileLife = 2.2
        w.homing = 2.6
        w.magazine = 10
        w.reserve = 120
        w.reloadTime = 1.2
        w.status = .curse
        w.statusChance = 0.25
        w.rarity = 2
        w.tags = [.arcane]
        return w
    }

    public static var thumper: WeaponDef {
        var w = WeaponDef(id: "thumper", name: "Thumper",
                          flavor: "Lob first, apologise later.")
        w.damage = 26
        w.fireInterval = 0.85
        w.projectileSpeed = 260
        w.projectileSprite = "proj/grenade"
        w.projectileRadius = 5
        w.projectileLife = 1.1
        w.mode = .arc
        w.arcGravity = 210
        w.explodeRadius = 56
        w.magazine = 4
        w.reserve = 36
        w.reloadTime = 1.7
        w.knockback = 160
        w.shake = 5
        w.impactFX = "fx/explosion"
        w.rarity = 2
        w.tags = [.explosive, .heavy]
        return w
    }

    public static var arcCoil: WeaponDef {
        var w = WeaponDef(id: "arc_coil", name: "Arc Coil",
                          flavor: "Conducts enthusiasm between strangers.")
        w.damage = 7
        w.fireInterval = 0.3
        w.projectileSpeed = 640
        w.projectileSprite = "proj/pellet_small"
        w.projectileRadius = 3
        w.projectileLife = 0.9
        w.chain = 3
        w.status = .shock
        w.statusChance = 0.6
        w.magazine = 16
        w.reserve = 160
        w.reloadTime = 1.3
        w.impactFX = "fx/lightning_arc"
        w.rarity = 2
        w.tags = [.shock]
        return w
    }

    public static var flamer: WeaponDef {
        var w = WeaponDef(id: "flamer", name: "Flamer",
                          flavor: "Short conversations only.")
        w.damage = 2.6
        w.fireInterval = 0.045
        w.projectileSpeed = 220
        w.projectileSprite = "proj/flame_puff"
        w.projectileRadius = 6
        w.projectileLife = 0.36
        w.spread = 0.34
        w.status = .burn
        w.statusChance = 0.5
        w.magazine = 120
        w.reserve = 600
        w.reloadTime = 1.6
        w.knockback = 8
        w.recoil = 0
        w.shake = 0.4
        w.muzzleFX = "fx/flame_puff"
        w.impactFX = "fx/flame_puff"
        w.rarity = 2
        w.tags = [.fire, .automatic]
        return w
    }

    public static var cryoLance: WeaponDef {
        var w = WeaponDef(id: "cryo_lance", name: "Cryo Lance",
                          flavor: "Hold still. Now hold stiller.")
        w.damage = 22          // per second while the beam is on target
        w.fireInterval = 0.1
        w.mode = .beam
        w.beamRange = 300
        w.projectileSprite = "proj/beam_seg_ice"
        w.status = .chill
        w.statusChance = 1.0
        w.magazine = 100
        w.reserve = 400
        w.reloadTime = 1.5
        w.knockback = 0
        w.shake = 0.6
        w.impactFX = "fx/freeze_shatter"
        w.rarity = 3
        w.tags = [.ice, .beam]
        return w
    }

    public static var nailDriver: WeaponDef {
        var w = WeaponDef(id: "nail_driver", name: "Nail Driver",
                          flavor: "Fastening solutions.")
        w.damage = 6
        w.fireInterval = 0.12
        w.projectileSpeed = 700
        w.projectileSprite = "proj/nail"
        w.projectileRadius = 2.5
        w.projectileLife = 0.8
        w.pierce = 1
        w.magazine = 30
        w.reserve = 300
        w.reloadTime = 1.2
        w.knockback = 30
        w.tags = [.kinetic, .automatic]
        return w
    }

    public static var boneSaw: WeaponDef {
        var w = WeaponDef(id: "bone_saw", name: "Bone Saw",
                          flavor: "It always comes home.")
        w.damage = 16
        w.fireInterval = 0.55
        w.projectileSpeed = 380
        w.projectileSprite = "proj/saw"
        w.projectileRadius = 8
        w.projectileLife = 1.5
        w.mode = .boomerang
        w.pierce = 99
        w.magazine = 1
        w.reserve = -1
        w.reloadTime = 0.5
        w.knockback = 40
        w.rarity = 2
        w.tags = [.kinetic, .heavy]
        return w
    }

    public static var starCaller: WeaponDef {
        var w = WeaponDef(id: "star_caller", name: "Star Caller",
                          flavor: "Patience, then violence.")
        w.damage = 14
        w.fireInterval = 0.5
        w.projectileSpeed = 200
        w.projectileSprite = "proj/pellet_player"
        w.projectileRadius = 4
        w.projectileLife = 3.0
        w.mode = .orbit
        w.homing = 4.0
        w.pellets = 3
        w.magazine = 9
        w.reserve = 90
        w.reloadTime = 1.5
        w.rarity = 3
        w.tags = [.holy, .arcane]
        return w
    }

    public static var handCannon: WeaponDef {
        var w = WeaponDef(id: "hand_cannon", name: "Hand Cannon",
                          flavor: "Recoil is a mobility option.")
        w.damage = 55
        w.fireInterval = 1.1
        w.projectileSpeed = 620
        w.projectileSprite = "proj/bolt_heavy"
        w.projectileRadius = 5
        w.projectileLife = 1.2
        w.explodeRadius = 34
        w.magazine = 2
        w.reserve = 24
        w.reloadTime = 1.8
        w.knockback = 260
        w.recoil = 14          // shoves the player, which is the point
        w.shake = 7
        w.impactFX = "fx/explosion"
        w.rarity = 3
        w.tags = [.kinetic, .explosive, .heavy]
        return w
    }

    public static var plagueCenser: WeaponDef {
        var w = WeaponDef(id: "plague_censer", name: "Plague Censer",
                          flavor: "Area denial, liturgical edition.")
        w.damage = 8
        w.fireInterval = 0.7
        w.projectileSpeed = 240
        w.projectileSprite = "proj/bolt_toxic"
        w.projectileRadius = 5
        w.projectileLife = 1.4
        w.explodeRadius = 44
        w.status = .poison
        w.statusChance = 1.0
        w.magazine = 6
        w.reserve = 60
        w.reloadTime = 1.4
        w.impactFX = "fx/poison_cloud"
        w.rarity = 2
        w.tags = [.poison]
        return w
    }

    public static var voidNeedle: WeaponDef {
        var w = WeaponDef(id: "void_needle", name: "Void Needle",
                          flavor: "A line drawn through everything.")
        w.damage = 30
        w.fireInterval = 0.8
        w.mode = .beam
        w.beamRange = 460
        w.projectileSprite = "proj/beam_seg_void"
        w.magazine = 6
        w.reserve = 60
        w.reloadTime = 1.6
        w.shake = 3
        w.impactFX = "fx/impact_spark"
        w.rarity = 3
        w.tags = [.void, .beam, .precision]
        return w
    }

    public static var sunburst: WeaponDef {
        var w = WeaponDef(id: "sunburst", name: "Sunburst",
                          flavor: "Hold. Hold. There.")
        w.damage = 12
        w.fireInterval = 0.4
        w.mode = .charge
        w.chargeTime = 0.75
        w.pellets = 12          // released as a full ring
        w.spread = .pi * 2
        w.projectileSpeed = 340
        w.projectileSprite = "proj/pellet_player"
        w.projectileRadius = 3.5
        w.projectileLife = 1.1
        w.magazine = 5
        w.reserve = 50
        w.reloadTime = 1.5
        w.shake = 4
        w.rarity = 3
        w.tags = [.holy, .explosive]
        return w
    }
}
