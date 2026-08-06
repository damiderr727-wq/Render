import Foundation

/// Everything the player is carrying, plus the derived numbers the sim reads.
///
/// `recompute()` rebuilds stats and weapon definitions from scratch every time
/// the inventory changes. Rebuilding rather than incrementally patching means
/// a synergy that stops being satisfied — say, after swapping a gun away —
/// correctly stops applying, which incremental updates get wrong constantly.
public struct Loadout: Sendable {
    public private(set) var items: [String] = []
    public private(set) var weapons: [WeaponInstance] = []
    public private(set) var stats = StatBlock()
    public private(set) var activeSynergies: [String] = []

    public var activeWeaponIndex: Int = 0
    public let maxWeapons = 4

    public init(startingWeapon: WeaponDef = WeaponCatalog.starter) {
        weapons = [WeaponInstance(def: startingWeapon)]
        recompute()
    }

    public var activeWeapon: WeaponInstance? {
        weapons.indices.contains(activeWeaponIndex) ? weapons[activeWeaponIndex] : nil
    }

    public var ownedItemIDs: Set<String> { Set(items) }

    public var itemDefs: [ItemDef] { items.compactMap { ItemCatalog.item($0) } }

    public var synergyDefs: [SynergyDef] {
        activeSynergies.compactMap { SynergyCatalog.synergy($0) }
    }

    // -- mutation -----------------------------------------------------------

    /// Adds an item. Returns the synergies that just came online, so the
    /// caller can announce them.
    @discardableResult
    public mutating func add(item id: String) -> [SynergyDef] {
        guard ItemCatalog.item(id) != nil else { return [] }
        let before = Set(activeSynergies)
        items.append(id)
        recompute()
        return activeSynergies.filter { !before.contains($0) }
            .compactMap { SynergyCatalog.synergy($0) }
    }

    /// Picks up a gun. When all slots are full the active one is dropped,
    /// which is returned so the world can put it back on the floor.
    @discardableResult
    public mutating func add(weapon def: WeaponDef) -> (dropped: WeaponDef?,
                                                        gained: [SynergyDef]) {
        let before = Set(activeSynergies)
        var dropped: WeaponDef?

        if let existing = weapons.firstIndex(where: { $0.def.id == def.id }) {
            // Duplicate gun tops up its ammo instead of eating a slot.
            weapons[existing].addAmmo(def.magazine * 3)
            recompute()
            return (nil, [])
        }

        if weapons.count >= maxWeapons {
            dropped = weapons[activeWeaponIndex].def
            weapons[activeWeaponIndex] = WeaponInstance(def: def)
        } else {
            weapons.append(WeaponInstance(def: def))
            activeWeaponIndex = weapons.count - 1
        }
        recompute()
        let gained = activeSynergies.filter { !before.contains($0) }
            .compactMap { SynergyCatalog.synergy($0) }
        return (dropped, gained)
    }

    public mutating func cycleWeapon(by delta: Int) {
        guard weapons.count > 1 else { return }
        let count = weapons.count
        activeWeaponIndex = ((activeWeaponIndex + delta) % count + count) % count
    }

    public mutating func selectWeapon(_ index: Int) {
        guard weapons.indices.contains(index) else { return }
        activeWeaponIndex = index
    }

    public mutating func updateActiveWeapon(_ body: (inout WeaponInstance) -> Void) {
        guard weapons.indices.contains(activeWeaponIndex) else { return }
        body(&weapons[activeWeaponIndex])
    }

    public mutating func refillAmmo(fraction: Double = 0.4) {
        for i in weapons.indices {
            let amount = Int(Double(weapons[i].def.reserve) * fraction)
            weapons[i].addAmmo(max(1, amount))
        }
    }

    // -- derivation ---------------------------------------------------------

    public mutating func recompute() {
        var block = StatBlock()
        for def in itemDefs { def.apply(&block) }

        // Base defs first: a synergy must never stack onto the mutated copy
        // it produced last frame.
        var baseDefs: [WeaponDef] = weapons.map {
            WeaponCatalog.weapon($0.def.id) ?? $0.def
        }

        let owned = ownedItemIDs
        let synergies = SynergyCatalog.active(items: owned, weapons: baseDefs)
        activeSynergies = synergies.map(\.id)

        for synergy in synergies {
            synergy.stats(&block)
            for i in baseDefs.indices where synergy.appliesTo(baseDefs[i]) {
                synergy.weaponMod(&baseDefs[i])
            }
        }

        // Ammo capacity scales with the item pool, so a fresh gun found late
        // in a run arrives with the reserve the build has earned.
        for i in baseDefs.indices where !baseDefs[i].isInfiniteAmmo {
            baseDefs[i].reserve = Int(Double(baseDefs[i].reserve) * block.ammoMultiplier)
        }

        for i in weapons.indices {
            let previousMagazine = weapons[i].ammoInMagazine
            let previousReserve = weapons[i].reserveAmmo
            weapons[i].def = baseDefs[i]
            weapons[i].ammoInMagazine = min(previousMagazine, baseDefs[i].magazine)
            weapons[i].reserveAmmo = baseDefs[i].isInfiniteAmmo
                ? Int.max
                : min(previousReserve, baseDefs[i].reserve)
        }

        stats = block
    }

    /// Would picking this up light anything up? Used for the pickup prompt.
    public func synergyPreview(forItem id: String) -> [SynergyDef] {
        SynergyCatalog.potential(from: id, owned: ownedItemIDs,
                                 weapons: weapons.map(\.def))
    }

    public func synergyPreview(forWeapon def: WeaponDef) -> [SynergyDef] {
        SynergyCatalog.potential(fromWeapon: def, owned: ownedItemIDs,
                                 weapons: weapons.map(\.def))
    }
}
