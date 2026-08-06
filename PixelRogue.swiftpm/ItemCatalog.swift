import Foundation

public enum ItemTag: String, Sendable, CaseIterable {
    case damage, firerate, projectile, defence, mobility, economy
    case fire, ice, poison, shock, arcane, explosive, holy, void, blood
    case cursed
}

public struct ItemDef: Sendable {
    public let id: String
    public let name: String
    public let flavor: String
    /// Shown in the pause screen; written as what the item *does*, not as
    /// numbers the player would have to trust.
    public let effect: String
    public let rarity: Int          // 1 common, 2 uncommon, 3 rare
    public let tags: Set<ItemTag>
    public let price: Int
    /// Folded into the run's StatBlock when the item is picked up.
    public let apply: @Sendable (inout StatBlock) -> Void

    public var sprite: String { "item/\(id)" }

    public init(id: String, name: String, flavor: String, effect: String,
                rarity: Int = 1, tags: Set<ItemTag> = [], price: Int = 25,
                apply: @escaping @Sendable (inout StatBlock) -> Void) {
        self.id = id
        self.name = name
        self.flavor = flavor
        self.effect = effect
        self.rarity = rarity
        self.tags = tags
        self.price = price
        self.apply = apply
    }
}

/// The thirty-two passives.
public enum ItemCatalog {
    public static let all: [ItemDef] = [
        // -- raw offence ----------------------------------------------------
        ItemDef(id: "bloodstone", name: "Bloodstone",
                flavor: "Warm, and getting warmer.",
                effect: "+22% damage", rarity: 1, tags: [.damage, .blood],
                price: 30) { $0.damageMultiplier *= 1.22 },

        ItemDef(id: "quickpowder", name: "Quickpowder",
                flavor: "Burns hot, burns first.",
                effect: "+25% fire rate", rarity: 1, tags: [.firerate, .fire],
                price: 30) { $0.fireRateMultiplier *= 1.25 },

        ItemDef(id: "long_lens", name: "Long Lens",
                flavor: "Everything is closer than it appears.",
                effect: "Tighter spread, longer range", rarity: 1,
                tags: [.projectile], price: 25) {
                    $0.spreadMultiplier *= 0.62
                    $0.projectileRangeMultiplier *= 1.35
                },

        ItemDef(id: "heavy_slug", name: "Heavy Slug",
                flavor: "Fewer, larger opinions.",
                effect: "+45% damage and knockback, -15% fire rate",
                rarity: 2, tags: [.damage], price: 45) {
                    $0.damageMultiplier *= 1.45
                    $0.knockbackMultiplier *= 1.6
                    $0.fireRateMultiplier *= 0.85
                },

        ItemDef(id: "split_shot", name: "Split Shot",
                flavor: "Why choose a direction.",
                effect: "+1 projectile, wider spread", rarity: 2,
                tags: [.projectile], price: 55) {
                    $0.extraProjectiles += 1
                    $0.spreadMultiplier *= 1.3
                    $0.damageMultiplier *= 0.9
                },

        ItemDef(id: "ricochet_ring", name: "Ricochet Ring",
                flavor: "The walls are on your side.",
                effect: "Shots bounce twice", rarity: 2,
                tags: [.projectile], price: 50) { $0.bounces += 2 },

        ItemDef(id: "piercing_tip", name: "Piercing Tip",
                flavor: "Line them up.",
                effect: "Shots pierce one extra enemy", rarity: 2,
                tags: [.projectile], price: 45) { $0.pierce += 1 },

        ItemDef(id: "homing_chip", name: "Homing Chip",
                flavor: "It has opinions about your aim.",
                effect: "Shots curve toward enemies", rarity: 2,
                tags: [.projectile], price: 50) { $0.homingStrength += 3.2 },

        ItemDef(id: "bandolier", name: "Bandolier",
                flavor: "Wear the whole shop.",
                effect: "+60% reserve ammo, faster reloads", rarity: 1,
                tags: [.economy], price: 30) {
                    $0.ammoMultiplier *= 1.6
                    $0.reloadSpeedMultiplier *= 1.2
                },

        ItemDef(id: "serpent_eye", name: "Serpent Eye",
                flavor: "It never blinks first.",
                effect: "+20% crit chance, +0.5x crit damage", rarity: 2,
                tags: [.damage], price: 55) {
                    $0.critChance += 0.20
                    $0.critMultiplier += 0.5
                },

        ItemDef(id: "echo_bell", name: "Echo Bell",
                flavor: "Everything twice, quietly.",
                effect: "+1 projectile, -12% damage", rarity: 2,
                tags: [.projectile, .arcane], price: 50) {
                    $0.extraProjectiles += 1
                    $0.damageMultiplier *= 0.88
                },

        // -- elemental ------------------------------------------------------
        ItemDef(id: "ember_core", name: "Ember Core",
                flavor: "Kept in glass for everyone's sake.",
                effect: "Shots can set enemies alight", rarity: 2,
                tags: [.fire], price: 45) {
                    $0.addStatusChance(.burn, 0.35)
                    $0.addStatusDamageBonus(.burn, 0.25)
                },

        ItemDef(id: "frost_core", name: "Frost Core",
                flavor: "Slow is smooth.",
                effect: "Shots chill enemies", rarity: 2,
                tags: [.ice], price: 45) {
                    $0.addStatusChance(.chill, 0.4)
                    $0.addStatusDamageBonus(.chill, 0.2)
                },

        ItemDef(id: "venom_vial", name: "Venom Vial",
                flavor: "Patience in a bottle.",
                effect: "Shots poison; poison ignores armour", rarity: 2,
                tags: [.poison], price: 45) {
                    $0.addStatusChance(.poison, 0.35)
                    $0.addStatusDamageBonus(.poison, 0.3)
                },

        ItemDef(id: "tesla_capacitor", name: "Tesla Capacitor",
                flavor: "Grounding is a luxury.",
                effect: "Shots can shock and chain", rarity: 2,
                tags: [.shock], price: 50) {
                    $0.addStatusChance(.shock, 0.3)
                },

        ItemDef(id: "void_prism", name: "Void Prism",
                flavor: "Light goes in. Something else comes out.",
                effect: "+30% damage, -1 max heart", rarity: 3,
                tags: [.void, .damage, .cursed], price: 70) {
                    $0.damageMultiplier *= 1.3
                    $0.maxHealthBonus -= 20
                },

        ItemDef(id: "sun_medal", name: "Sun Medal",
                flavor: "Awarded for excessive brightness.",
                effect: "+15% damage, heal on some kills", rarity: 2,
                tags: [.holy], price: 55) {
                    $0.damageMultiplier *= 1.15
                    $0.healOnKillChance += 0.08
                },

        ItemDef(id: "gunpowder_keg", name: "Gunpowder Keg",
                flavor: "Do not shake. Do shake.",
                effect: "Shots explode on impact", rarity: 3,
                tags: [.explosive], price: 75) {
                    $0.explosiveShots = true
                    $0.explosionRadiusBonus += 10
                },

        // -- defence --------------------------------------------------------
        ItemDef(id: "iron_heart", name: "Iron Heart",
                flavor: "Beats regardless.",
                effect: "+2 max hearts, +1 armour", rarity: 1,
                tags: [.defence], price: 40) {
                    $0.maxHealthBonus += 40
                    $0.startingArmor += 1
                },

        ItemDef(id: "feather_boots", name: "Feather Boots",
                flavor: "Ankle-deep in nothing.",
                effect: "+18% move speed, longer dodge", rarity: 1,
                tags: [.mobility], price: 35) {
                    $0.moveSpeedMultiplier *= 1.18
                    $0.dodgeDistanceMultiplier *= 1.2
                },

        ItemDef(id: "phase_cloak", name: "Phase Cloak",
                flavor: "Briefly elsewhere.",
                effect: "+1 dodge charge, longer invulnerability", rarity: 3,
                tags: [.mobility, .arcane], price: 70) {
                    $0.dodgeCooldownMultiplier *= 0.6
                    $0.invulnBonus += 0.15
                },

        ItemDef(id: "thorn_mail", name: "Thorn Mail",
                flavor: "Hugs discouraged.",
                effect: "Damages enemies that touch you", rarity: 2,
                tags: [.defence], price: 45) {
                    $0.contactDamage += 14
                    $0.startingArmor += 1
                },

        ItemDef(id: "vampire_fang", name: "Vampire Fang",
                flavor: "A small, reasonable arrangement.",
                effect: "Kills sometimes restore health", rarity: 2,
                tags: [.blood], price: 55) { $0.lifestealOnKill += 1.6 },

        ItemDef(id: "mirror_shard", name: "Mirror Shard",
                flavor: "Their problem now.",
                effect: "Chance to reflect enemy shots", rarity: 3,
                tags: [.defence, .arcane, .ice], price: 65) { $0.reflectChance += 0.22 },

        ItemDef(id: "clock_spring", name: "Clock Spring",
                flavor: "Tick. Tiiiick.",
                effect: "Taking a hit briefly slows time", rarity: 3,
                tags: [.defence], price: 65) {
                    $0.timeSlowOnHit += 0.9
                    $0.invulnBonus += 0.1
                },

        // -- economy --------------------------------------------------------
        ItemDef(id: "lucky_coin", name: "Lucky Coin",
                flavor: "Lands on its edge more than it should.",
                effect: "+luck, +25% coins", rarity: 1,
                tags: [.economy], price: 30) {
                    $0.luck += 1.0
                    $0.coinMultiplier *= 1.25
                },

        ItemDef(id: "magnet_core", name: "Magnet Core",
                flavor: "Pickups come to you.",
                effect: "Much larger pickup range", rarity: 1,
                tags: [.economy, .shock], price: 25) { $0.pickupRadiusBonus += 70 },

        ItemDef(id: "ammo_belt", name: "Ammo Belt",
                flavor: "Weight you are happy to carry.",
                effect: "+90% reserve ammo", rarity: 1,
                tags: [.economy], price: 30) { $0.ammoMultiplier *= 1.9 },

        ItemDef(id: "speed_loader", name: "Speed Loader",
                flavor: "Muscle memory in brass.",
                effect: "+70% reload speed", rarity: 1,
                tags: [.firerate], price: 35) { $0.reloadSpeedMultiplier *= 1.7 },

        ItemDef(id: "glass_cannon", name: "Glass Cannon",
                flavor: "Beautiful while it lasts.",
                effect: "+80% damage, halves your max health", rarity: 3,
                tags: [.damage, .cursed], price: 60) {
                    $0.damageMultiplier *= 1.8
                    $0.maxHealthBonus -= 40
                },

        ItemDef(id: "hex_tome", name: "Hex Tome",
                flavor: "The margins argue with the text.",
                effect: "Shots curse enemies to take more damage", rarity: 3,
                tags: [.arcane], price: 65) {
                    $0.addStatusChance(.curse, 0.3)
                    $0.addStatusDamageBonus(.curse, 0.35)
                },

        ItemDef(id: "orbital_shard", name: "Orbital Shard",
                flavor: "It stays close. It always stays close.",
                effect: "A shard orbits you and damages enemies", rarity: 3,
                tags: [.arcane, .defence], price: 70) { $0.orbitals += 1 },
    ]

    private static var byID: [String: ItemDef] {
        Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0) })
    }

    public static func item(_ id: String) -> ItemDef? { byID[id] }

    public static func randomDrop(rng: inout RNG, luck: Double,
                                  excluding owned: Set<String>) -> ItemDef? {
        let pool = all.filter { !owned.contains($0.id) }
        guard !pool.isEmpty else { return nil }
        let weights = pool.map { def -> (value: ItemDef, weight: Double) in
            let base = [4.0, 2.0, 0.9][min(2, max(0, def.rarity - 1))]
            let luckBoost = def.rarity >= 2 ? 1 + luck * 0.35 : 1
            return (def, base * luckBoost)
        }
        return rng.weighted(weights)
    }
}
