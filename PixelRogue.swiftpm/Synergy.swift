import Foundation

/// A named combination that changes how a build plays.
///
/// Synergies are the reason to pick up an item you would otherwise skip.
/// They are deliberately *legible*: each one names two or three specific
/// things you are carrying, so a player can see the combination coming
/// rather than discovering it in a wiki.
public struct SynergyDef: Sendable {
    public let id: String
    public let name: String
    public let summary: String

    /// Every listed item must be owned.
    public let items: [String]
    /// Every listed weapon must be carried.
    public let weapons: [String]
    /// Minimum number of owned items carrying each tag, e.g. `[.fire: 3]`.
    public let itemTagCounts: [ItemTag: Int]
    /// At least one carried weapon must have each of these tags.
    public let weaponTags: [WeaponTag]

    public let stats: @Sendable (inout StatBlock) -> Void
    /// Applied to every carried weapon that passes `appliesTo`.
    public let weaponMod: @Sendable (inout WeaponDef) -> Void
    public let appliesTo: @Sendable (WeaponDef) -> Bool

    public init(id: String, name: String, summary: String,
                items: [String] = [], weapons: [String] = [],
                itemTagCounts: [ItemTag: Int] = [:],
                weaponTags: [WeaponTag] = [],
                stats: @escaping @Sendable (inout StatBlock) -> Void = { _ in },
                appliesTo: @escaping @Sendable (WeaponDef) -> Bool = { _ in false },
                weaponMod: @escaping @Sendable (inout WeaponDef) -> Void = { _ in }) {
        self.id = id
        self.name = name
        self.summary = summary
        self.items = items
        self.weapons = weapons
        self.itemTagCounts = itemTagCounts
        self.weaponTags = weaponTags
        self.stats = stats
        self.appliesTo = appliesTo
        self.weaponMod = weaponMod
    }

    public func isActive(items owned: Set<String>,
                         weapons carried: [WeaponDef]) -> Bool {
        for required in items where !owned.contains(required) { return false }

        let weaponIDs = Set(carried.map(\.id))
        for required in weapons where !weaponIDs.contains(required) { return false }

        if !itemTagCounts.isEmpty {
            var counts: [ItemTag: Int] = [:]
            for id in owned {
                guard let def = ItemCatalog.item(id) else { continue }
                for tag in def.tags { counts[tag, default: 0] += 1 }
            }
            for (tag, needed) in itemTagCounts where counts[tag, default: 0] < needed {
                return false
            }
        }

        if !weaponTags.isEmpty {
            let allTags = carried.reduce(into: Set<WeaponTag>()) { $0.formUnion($1.tags) }
            for tag in weaponTags where !allTags.contains(tag) { return false }
        }

        // A synergy with no requirements at all would be permanently on.
        return !(items.isEmpty && weapons.isEmpty &&
                 itemTagCounts.isEmpty && weaponTags.isEmpty)
    }
}

public enum SynergyCatalog {
    public static let all: [SynergyDef] = [

        SynergyDef(
            id: "dragons_breath", name: "Dragon's Breath",
            summary: "Scattergun pellets ignite. Every pellet burns.",
            items: ["ember_core"], weapons: ["scattergun"],
            stats: { $0.addStatusChance(.burn, 0.65) },
            appliesTo: { $0.id == "scattergun" },
            weaponMod: {
                $0.status = .burn
                $0.statusChance = 1.0
                $0.pellets += 3
                $0.projectileSprite = "proj/flame_puff"
                $0.tags.insert(.fire)
            }),

        SynergyDef(
            id: "glacier_lance", name: "Glacier Lance",
            summary: "The Cryo Lance freezes solid, and frozen enemies shatter.",
            items: ["frost_core"], weapons: ["cryo_lance"],
            stats: {
                $0.addStatusChance(.chill, 0.5)
                $0.addStatusDamageBonus(.chill, 0.6)
            },
            appliesTo: { $0.id == "cryo_lance" },
            weaponMod: {
                $0.damage *= 1.35
                $0.beamRange += 90
            }),

        SynergyDef(
            id: "chain_reaction", name: "Chain Reaction",
            summary: "Arc Coil bolts leap to three more targets and always shock.",
            items: ["tesla_capacitor"], weapons: ["arc_coil"],
            stats: { $0.addStatusChance(.shock, 0.4) },
            appliesTo: { $0.tags.contains(.shock) },
            weaponMod: {
                $0.chain += 3
                $0.statusChance = 1.0
                $0.damage *= 1.15
            }),

        SynergyDef(
            id: "plague_bearer", name: "Plague Bearer",
            summary: "Poison clouds linger twice as long and spread on death.",
            items: ["venom_vial"], weapons: ["plague_censer"],
            stats: {
                $0.addStatusDamageBonus(.poison, 0.5)
                $0.addStatusChance(.poison, 0.5)
            },
            appliesTo: { $0.tags.contains(.poison) },
            weaponMod: {
                $0.explodeRadius += 26
                $0.projectileLife *= 1.4
            }),

        SynergyDef(
            id: "black_powder_gospel", name: "Black Powder Gospel",
            summary: "Thumper shells split into a trio of smaller grenades.",
            items: ["gunpowder_keg"], weapons: ["thumper"],
            stats: { $0.explosionRadiusBonus += 14 },
            appliesTo: { $0.id == "thumper" },
            weaponMod: {
                $0.pellets += 2
                $0.spread = 0.34
                $0.damage *= 0.7
                $0.explodeRadius += 8
            }),

        SynergyDef(
            id: "hollow_point", name: "Hollow Point",
            summary: "The Longarm punches through everything in the line.",
            items: ["heavy_slug"], weapons: ["longarm"],
            stats: { $0.pierce += 2 },
            appliesTo: { $0.tags.contains(.precision) },
            weaponMod: {
                $0.pierce = 99
                $0.damage *= 1.25
                $0.knockback *= 1.4
            }),

        SynergyDef(
            id: "buckshot_ballet", name: "Buckshot Ballet",
            summary: "Four more pellets, and the cone tightens instead of widening.",
            items: ["split_shot"], weapons: ["scattergun"],
            stats: { $0.spreadMultiplier *= 0.7 },
            appliesTo: { $0.tags.contains(.shotgun) },
            weaponMod: {
                $0.pellets += 4
                $0.spread *= 0.75
                $0.fireInterval *= 0.85
            }),

        SynergyDef(
            id: "ricochet_rifle", name: "Ricochet Rifle",
            summary: "Bounced shots hit harder each time they land a wall.",
            items: ["ricochet_ring"], weapons: ["peacemaker"],
            stats: { $0.bounces += 2 },
            appliesTo: { $0.mode == .projectile },
            weaponMod: {
                $0.bounces += 2
                $0.projectileLife *= 1.6
            }),

        SynergyDef(
            id: "homing_swarm", name: "Homing Swarm",
            summary: "Star Caller motes multiply and hunt relentlessly.",
            items: ["homing_chip"], weapons: ["star_caller"],
            stats: { $0.homingStrength += 2.5 },
            appliesTo: { $0.mode == .orbit },
            weaponMod: {
                $0.pellets += 2
                $0.homing += 3
                $0.projectileLife += 1.0
            }),

        SynergyDef(
            id: "bullet_time", name: "Bullet Time",
            summary: "Dodging slows the world to a crawl.",
            items: ["clock_spring", "phase_cloak"],
            stats: {
                $0.timeSlowOnHit += 1.2
                $0.dodgeCooldownMultiplier *= 0.7
                $0.invulnBonus += 0.1
            }),

        SynergyDef(
            id: "sanguine_pact", name: "Sanguine Pact",
            summary: "Fragile, but every kill feeds you.",
            items: ["vampire_fang", "glass_cannon"],
            stats: {
                $0.lifestealOnKill += 3.0
                $0.healOnKillChance += 0.12
                $0.damageMultiplier *= 1.1
            }),

        SynergyDef(
            id: "voidlight", name: "Voidlight",
            summary: "The Void Needle draws its line through walls.",
            items: ["void_prism"], weapons: ["void_needle"],
            stats: { $0.damageMultiplier *= 1.15 },
            appliesTo: { $0.tags.contains(.void) },
            weaponMod: {
                $0.beamRange += 220
                $0.damage *= 1.3
                $0.fireInterval *= 0.8
            }),

        SynergyDef(
            id: "solar_flare", name: "Solar Flare",
            summary: "Sunburst charges in half the time and fires a wider ring.",
            items: ["sun_medal"], weapons: ["sunburst"],
            stats: { $0.healOnKillChance += 0.06 },
            appliesTo: { $0.mode == .charge },
            weaponMod: {
                $0.chargeTime *= 0.5
                $0.pellets += 6
                $0.projectileSpeed *= 1.2
            }),

        SynergyDef(
            id: "nail_bomb", name: "Nail Bomb",
            summary: "Nails detonate where they land.",
            items: ["gunpowder_keg"], weapons: ["nail_driver"],
            stats: { $0.explosionRadiusBonus += 6 },
            appliesTo: { $0.id == "nail_driver" },
            weaponMod: {
                $0.explodeRadius = 30
                $0.damage *= 0.85
                $0.impactFX = "fx/explosion"
                $0.tags.insert(.explosive)
            }),

        SynergyDef(
            id: "whirling_death", name: "Whirling Death",
            summary: "The Bone Saw refuses to leave, circling you instead.",
            items: ["orbital_shard"], weapons: ["bone_saw"],
            stats: { $0.orbitals += 2 },
            appliesTo: { $0.mode == .boomerang },
            weaponMod: {
                $0.projectileLife *= 1.5
                $0.damage *= 1.2
                $0.fireInterval *= 0.8
            }),

        SynergyDef(
            id: "hexed_rounds", name: "Hexed Rounds",
            summary: "Every hexbolt curses; cursed things come apart.",
            items: ["hex_tome"], weapons: ["hexbolt"],
            stats: {
                $0.addStatusChance(.curse, 0.5)
                $0.addStatusDamageBonus(.curse, 0.3)
            },
            appliesTo: { $0.tags.contains(.arcane) },
            weaponMod: {
                $0.status = .curse
                $0.statusChance = 1.0
                $0.homing += 1.5
            }),

        SynergyDef(
            id: "serpents_kiss", name: "Serpent's Kiss",
            summary: "Critical hits inject poison.",
            items: ["serpent_eye", "venom_vial"],
            stats: {
                $0.addStatusChance(.poison, 0.35)
                $0.critMultiplier += 0.4
                $0.addStatusDamageBonus(.poison, 0.25)
            }),

        SynergyDef(
            id: "mirror_barrage", name: "Mirror Barrage",
            summary: "Reflected shots come back doubled.",
            items: ["mirror_shard", "echo_bell"],
            stats: {
                $0.reflectChance += 0.25
                $0.extraProjectiles += 1
            }),

        SynergyDef(
            id: "quickdraw", name: "Quickdraw",
            summary: "Precision weapons reload the instant you crit.",
            items: ["speed_loader", "quickpowder"],
            weaponTags: [.precision],
            stats: {
                $0.reloadSpeedMultiplier *= 1.6
                $0.critChance += 0.1
            },
            appliesTo: { $0.tags.contains(.precision) },
            weaponMod: { $0.reloadTime *= 0.5 }),

        SynergyDef(
            id: "feather_trigger", name: "Feather Trigger",
            summary: "Momentum feeds the trigger finger.",
            items: ["feather_boots"], weapons: ["ripper"],
            stats: {
                $0.fireRateMultiplier *= 1.2
                $0.moveSpeedMultiplier *= 1.1
            },
            appliesTo: { $0.tags.contains(.automatic) },
            weaponMod: {
                $0.spread *= 0.7
                $0.fireInterval *= 0.9
            }),

        // -- tag-driven: reward committing to an element -----------------
        SynergyDef(
            id: "ice_nine", name: "Ice Nine",
            summary: "Three cold items: chilled enemies freeze outright.",
            itemTagCounts: [.ice: 2],
            stats: {
                $0.addStatusChance(.chill, 0.5)
                $0.addStatusDamageBonus(.chill, 0.75)
            }),

        SynergyDef(
            id: "pyroclasm", name: "Pyroclasm",
            summary: "Three burning items: things that die on fire explode.",
            itemTagCounts: [.fire: 2],
            stats: {
                $0.addStatusChance(.burn, 0.4)
                $0.addStatusDamageBonus(.burn, 0.6)
                $0.explosionRadiusBonus += 12
            }),

        SynergyDef(
            id: "storm_front", name: "Storm Front",
            summary: "Shock spreads further and stuns for longer.",
            itemTagCounts: [.shock: 2],
            stats: {
                $0.addStatusChance(.shock, 0.35)
                $0.addStatusDamageBonus(.shock, 0.4)
            },
            appliesTo: { $0.tags.contains(.shock) },
            weaponMod: { $0.chain += 2 }),

        SynergyDef(
            id: "blood_debt", name: "Blood Debt",
            summary: "Cursed items pay out: much more damage, much less margin.",
            itemTagCounts: [.cursed: 2],
            stats: {
                $0.damageMultiplier *= 1.35
                $0.critChance += 0.12
                $0.moveSpeedMultiplier *= 1.1
            }),

        SynergyDef(
            id: "high_roller", name: "High Roller",
            summary: "Luck compounds: better drops, cheaper shops.",
            itemTagCounts: [.economy: 3],
            stats: {
                $0.luck += 1.5
                $0.shopDiscount += 0.25
                $0.coinMultiplier *= 1.35
            }),
    ]

    private static var byID: [String: SynergyDef] {
        Dictionary(uniqueKeysWithValues: all.map { ($0.id, $0) })
    }

    public static func synergy(_ id: String) -> SynergyDef? { byID[id] }

    public static func active(items: Set<String>,
                              weapons: [WeaponDef]) -> [SynergyDef] {
        all.filter { $0.isActive(items: items, weapons: weapons) }
    }

    /// Synergies that a single extra item would complete. Powers the "this
    /// would combo with what you're carrying" hint on pickups and in shops.
    public static func potential(from item: String, owned: Set<String>,
                                 weapons: [WeaponDef]) -> [SynergyDef] {
        guard !owned.contains(item) else { return [] }
        let after = owned.union([item])
        let before = Set(active(items: owned, weapons: weapons).map(\.id))
        return active(items: after, weapons: weapons).filter { !before.contains($0.id) }
    }

    /// Same question for a weapon the player is standing over.
    public static func potential(fromWeapon weapon: WeaponDef, owned: Set<String>,
                                 weapons: [WeaponDef]) -> [SynergyDef] {
        let before = Set(active(items: owned, weapons: weapons).map(\.id))
        return active(items: owned, weapons: weapons + [weapon])
            .filter { !before.contains($0.id) }
    }
}
