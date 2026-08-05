import Foundation

public struct CharacterDef: Sendable {
    public let id: String
    public let name: String
    public let blurb: String
    public let maxHealth: Double
    public let armor: Int
    public let moveSpeed: Double
    public let startingWeapon: String
    public let startingItem: String?
    public let startingBlanks: Int
    public let startingCoins: Int
    /// Applied on top of items, before synergies.
    public let passive: @Sendable (inout StatBlock) -> Void
    public let passiveText: String

    public var portrait: String { "portrait/\(id)" }
    public var spriteBase: String { "char/\(id)" }
}

public enum CharacterCatalog {
    public static let all: [CharacterDef] = [
        CharacterDef(
            id: "marshal", name: "The Marshal",
            blurb: "Came down here on purpose. Regrets it professionally.",
            maxHealth: 60, armor: 1, moveSpeed: 96,
            startingWeapon: "peacemaker", startingItem: nil,
            startingBlanks: 2, startingCoins: 20,
            passive: { $0.critChance += 0.08 },
            passiveText: "Steady hands: +8% critical chance"),

        CharacterDef(
            id: "stray", name: "The Stray",
            blurb: "Knows every shortcut, owns none of them.",
            maxHealth: 40, armor: 0, moveSpeed: 112,
            startingWeapon: "ripper", startingItem: "feather_boots",
            startingBlanks: 3, startingCoins: 35,
            passive: {
                $0.dodgeCooldownMultiplier *= 0.75
                $0.luck += 0.5
            },
            passiveText: "Light-footed: faster dodges, luckier drops"),

        CharacterDef(
            id: "bulwark", name: "The Bulwark",
            blurb: "Moves like a door. Hits like one too.",
            maxHealth: 100, armor: 3, moveSpeed: 78,
            startingWeapon: "hand_cannon", startingItem: "iron_heart",
            startingBlanks: 1, startingCoins: 10,
            passive: {
                $0.knockbackMultiplier *= 1.4
                $0.moveSpeedMultiplier *= 0.94
            },
            passiveText: "Immovable: more armour, heavier knockback"),

        CharacterDef(
            id: "tinker", name: "The Tinker",
            blurb: "Every gun is a suggestion.",
            maxHealth: 50, armor: 1, moveSpeed: 94,
            startingWeapon: "nail_driver", startingItem: "speed_loader",
            startingBlanks: 2, startingCoins: 60,
            passive: {
                $0.ammoMultiplier *= 1.4
                $0.reloadSpeedMultiplier *= 1.25
                $0.shopDiscount += 0.15
            },
            passiveText: "Resourceful: more ammo, cheaper shops"),

        CharacterDef(
            id: "beak", name: "The Beak",
            blurb: "Small. Fast. Extremely rude.",
            maxHealth: 40, armor: 0, moveSpeed: 118,
            startingWeapon: "scattergun", startingItem: "lucky_coin",
            startingBlanks: 2, startingCoins: 45,
            passive: {
                $0.coinMultiplier *= 1.5
                $0.pickupRadiusBonus += 40
            },
            passiveText: "Hoarder: far more coins, wide pickup range"),

        CharacterDef(
            id: "hexe", name: "The Hexe",
            blurb: "Traded something important for something interesting.",
            maxHealth: 50, armor: 0, moveSpeed: 92,
            startingWeapon: "hexbolt", startingItem: "hex_tome",
            startingBlanks: 3, startingCoins: 25,
            passive: {
                $0.addStatusChance(.curse, 0.2)
                $0.damageMultiplier *= 1.1
            },
            passiveText: "Ill-omened: shots curse, +10% damage"),
    ]

    public static func character(_ id: String) -> CharacterDef? {
        all.first { $0.id == id }
    }

    public static var `default`: CharacterDef { all[0] }
}

/// Everything that persists across rooms and floors within one run.
public struct RunState: Sendable {
    public var seed: UInt64
    public var character: CharacterDef
    public var depth: Int = 1
    public var loadout: Loadout

    public var health: Double
    public var maxHealth: Double
    public var armor: Int
    public var coins: Int
    public var keys: Int
    public var blanks: Int

    public var kills: Int = 0
    public var roomsCleared: Int = 0
    public var elapsed: Double = 0
    public var damageTaken: Double = 0
    public var bossesFelled: [String] = []

    public static let maxDepth = 4
    public static let themeOrder = ["keep", "crypt", "foundry", "sanctum"]

    public init(seed: UInt64, character: CharacterDef = CharacterCatalog.default) {
        self.seed = seed
        self.character = character
        let weapon = WeaponCatalog.weapon(character.startingWeapon)
            ?? WeaponCatalog.starter
        var loadout = Loadout(startingWeapon: weapon)
        if let item = character.startingItem {
            loadout.add(item: item)
        }
        self.loadout = loadout
        self.maxHealth = character.maxHealth
        self.health = character.maxHealth
        self.armor = character.armor
        self.coins = character.startingCoins
        self.keys = 1
        self.blanks = character.startingBlanks
        refreshDerivedHealth()
    }

    /// Character passive folds in on top of item stats.
    public var stats: StatBlock {
        var block = loadout.stats
        character.passive(&block)
        return block
    }

    public var theme: String {
        Self.themeOrder[min(Self.themeOrder.count - 1, max(0, depth - 1))]
    }

    public var floorSeed: UInt64 { seed &+ UInt64(depth) &* 0x9E3779B9 }

    public var isFinalFloor: Bool { depth >= Self.maxDepth }

    public var moveSpeed: Double {
        character.moveSpeed * stats.moveSpeedMultiplier
    }

    /// Recomputes max health after an item changed it, keeping current health
    /// proportional so a +max-health item does not read as a heal and a
    /// -max-health item cannot instantly kill.
    public mutating func refreshDerivedHealth() {
        let fraction = maxHealth > 0 ? health / maxHealth : 1
        let newMax = max(20, character.maxHealth + stats.maxHealthBonus)
        maxHealth = newMax
        health = min(newMax, max(1, fraction * newMax))
    }

    public mutating func heal(_ amount: Double) {
        health = min(maxHealth, health + amount)
    }

    public mutating func addCoins(_ amount: Int) {
        coins += max(0, Int(Double(amount) * stats.coinMultiplier))
    }

    public func price(_ base: Int) -> Int {
        max(1, Int(Double(base) * (1 - stats.shopDiscount)))
    }

    public var summaryLines: [String] {
        [
            "Depth \(depth)",
            "Kills \(kills)",
            "Rooms \(roomsCleared)",
            "Time \(Int(elapsed / 60))m \(Int(elapsed.truncatingRemainder(dividingBy: 60)))s",
        ]
    }
}
