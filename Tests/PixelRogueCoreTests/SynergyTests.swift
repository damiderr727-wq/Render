import XCTest
@testable import PixelRogueCore

/// The synergy system is the reason the item pool is interesting, so it gets
/// its own suite: a synergy that silently stops firing is invisible in play
/// but ruins a build.
final class SynergyTests: XCTestCase {

    func testSynergyActivatesWhenRequirementsAreMet() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.scattergun)
        XCTAssertFalse(loadout.activeSynergies.contains("dragons_breath"))

        let gained = loadout.add(item: "ember_core")
        XCTAssertTrue(loadout.activeSynergies.contains("dragons_breath"))
        XCTAssertTrue(gained.contains { $0.id == "dragons_breath" },
                      "picking up the completing item did not announce it")
    }

    func testSynergyDoesNotActivateWithoutTheWeapon() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.peacemaker)
        loadout.add(item: "ember_core")
        XCTAssertFalse(loadout.activeSynergies.contains("dragons_breath"))
    }

    func testSynergyModifiesTheWeaponItNames() {
        var plain = Loadout(startingWeapon: WeaponCatalog.scattergun)
        let basePellets = plain.weapons[0].def.pellets

        plain.add(item: "ember_core")
        let synergised = plain.weapons[0].def
        XCTAssertGreaterThan(synergised.pellets, basePellets,
                             "Dragon's Breath did not add pellets")
        XCTAssertEqual(synergised.status, .burn)
        XCTAssertTrue(synergised.tags.contains(.fire))
    }

    func testSynergyDeactivatesWhenTheWeaponIsSwappedAway() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.scattergun)
        loadout.add(item: "ember_core")
        XCTAssertTrue(loadout.activeSynergies.contains("dragons_breath"))

        // Fill the remaining slots, then swap the scattergun itself out —
        // a full loadout replaces whichever weapon is currently equipped.
        for weapon in [WeaponCatalog.ripper, WeaponCatalog.longarm,
                       WeaponCatalog.hexbolt] {
            _ = loadout.add(weapon: weapon)
        }
        loadout.selectWeapon(0)
        XCTAssertEqual(loadout.activeWeapon?.def.id, "scattergun")
        let result = loadout.add(weapon: WeaponCatalog.thumper)
        XCTAssertEqual(result.dropped?.id, "scattergun")
        XCTAssertFalse(loadout.weapons.contains { $0.def.id == "scattergun" })
        XCTAssertFalse(loadout.activeSynergies.contains("dragons_breath"),
                       "synergy stayed active after its weapon was dropped")
    }

    func testWeaponModsDoNotCompoundOnRecompute() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.scattergun)
        loadout.add(item: "ember_core")
        let afterFirst = loadout.weapons[0].def.pellets

        // Any inventory change re-runs the whole derivation.
        loadout.add(item: "lucky_coin")
        loadout.add(item: "magnet_core")
        XCTAssertEqual(loadout.weapons[0].def.pellets, afterFirst,
                       "synergy stacked onto its own output")
    }

    func testTagSynergyNeedsEnoughTaggedItems() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.peacemaker)
        loadout.add(item: "ember_core")          // one .fire item
        XCTAssertFalse(loadout.activeSynergies.contains("pyroclasm"))
        loadout.add(item: "quickpowder")         // two .fire items
        XCTAssertTrue(loadout.activeSynergies.contains("pyroclasm"))
    }

    func testItemStatsAccumulate() {
        var loadout = Loadout()
        let base = loadout.stats.damageMultiplier
        loadout.add(item: "bloodstone")
        let one = loadout.stats.damageMultiplier
        loadout.add(item: "heavy_slug")
        let two = loadout.stats.damageMultiplier
        XCTAssertGreaterThan(one, base)
        XCTAssertGreaterThan(two, one)
    }

    func testSynergyPreviewPredictsThePickup() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.scattergun)
        let preview = loadout.synergyPreview(forItem: "ember_core")
        XCTAssertTrue(preview.contains { $0.id == "dragons_breath" })

        loadout.add(item: "ember_core")
        XCTAssertTrue(loadout.synergyPreview(forItem: "ember_core").isEmpty,
                      "already-owned item still previews a synergy")
    }

    func testWeaponPreviewPredictsThePickup() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.peacemaker)
        loadout.add(item: "ember_core")
        let preview = loadout.synergyPreview(forWeapon: WeaponCatalog.scattergun)
        XCTAssertTrue(preview.contains { $0.id == "dragons_breath" })
    }

    func testDuplicateWeaponRefillsInsteadOfTakingASlot() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.ripper)
        loadout.updateActiveWeapon { $0.reserveAmmo = 10 }
        let before = loadout.weapons.count
        _ = loadout.add(weapon: WeaponCatalog.ripper)
        XCTAssertEqual(loadout.weapons.count, before)
        XCTAssertGreaterThan(loadout.weapons[0].reserveAmmo, 10)
    }

    func testFullSlotsDropTheActiveWeapon() {
        var loadout = Loadout(startingWeapon: WeaponCatalog.peacemaker)
        for weapon in [WeaponCatalog.ripper, WeaponCatalog.longarm,
                       WeaponCatalog.hexbolt] {
            let result = loadout.add(weapon: weapon)
            XCTAssertNil(result.dropped)
        }
        XCTAssertEqual(loadout.weapons.count, loadout.maxWeapons)
        let result = loadout.add(weapon: WeaponCatalog.thumper)
        XCTAssertNotNil(result.dropped, "a full loadout swallowed a weapon")
        XCTAssertEqual(loadout.weapons.count, loadout.maxWeapons)
    }

    func testEverySynergyIsReachable() {
        // A synergy nobody can ever assemble is dead content. Each one must
        // name items and weapons that actually exist.
        for synergy in SynergyCatalog.all {
            for item in synergy.items {
                XCTAssertNotNil(ItemCatalog.item(item),
                                "\(synergy.id) requires unknown item \(item)")
            }
            for weapon in synergy.weapons {
                XCTAssertNotNil(WeaponCatalog.weapon(weapon),
                                "\(synergy.id) requires unknown weapon \(weapon)")
            }
            for (tag, count) in synergy.itemTagCounts {
                let available = ItemCatalog.all.filter { $0.tags.contains(tag) }.count
                XCTAssertGreaterThanOrEqual(
                    available, count,
                    "\(synergy.id) needs \(count) '\(tag)' items but only \(available) exist")
            }
        }
    }

    func testNoSynergyIsAlwaysOn() {
        let bare = Loadout()
        for synergy in SynergyCatalog.all {
            XCTAssertFalse(
                synergy.isActive(items: [], weapons: bare.weapons.map(\.def)),
                "\(synergy.id) is active with an empty inventory")
        }
    }

    func testSynergyIDsAreUnique() {
        let ids = SynergyCatalog.all.map(\.id)
        XCTAssertEqual(Set(ids).count, ids.count, "duplicate synergy id")
    }

    func testMaxHealthItemsDoNotKill() {
        var run = RunState(seed: 1)
        run.loadout.add(item: "glass_cannon")   // halves max health
        run.loadout.add(item: "void_prism")     // and takes another heart
        run.refreshDerivedHealth()
        XCTAssertGreaterThan(run.health, 0)
        XCTAssertLessThanOrEqual(run.health, run.maxHealth)
        XCTAssertGreaterThanOrEqual(run.maxHealth, 20)
    }
}
