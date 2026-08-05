import XCTest
@testable import PixelRogueCore

/// Contract tests between the Python art pipeline and the Swift content.
///
/// Sprite names are plain strings on both sides, so a rename in a generator
/// or a typo in a catalog produces an invisible missing sprite at runtime
/// rather than a compile error. These tests turn that into a build failure.
final class ContentIntegrityTests: XCTestCase {

    private static let manifest: [String: Any]? = {
        // Walk up from this file to the repository root.
        var url = URL(fileURLWithPath: #filePath)
        for _ in 0..<3 { url.deleteLastPathComponent() }
        let path = url.appendingPathComponent("Assets/generated/game.json")
        guard let data = try? Data(contentsOf: path),
              let object = try? JSONSerialization.jsonObject(with: data),
              let dictionary = object as? [String: Any] else { return nil }
        return dictionary
    }()

    private var sprites: Set<String> {
        guard let table = Self.manifest?["sprites"] as? [String: Any] else { return [] }
        return Set(table.keys)
    }

    private var animations: Set<String> {
        guard let table = Self.manifest?["animations"] as? [String: Any] else { return [] }
        return Set(table.keys)
    }

    private func assertSprite(_ name: String, _ context: String,
                              file: StaticString = #filePath,
                              line: UInt = #line) {
        // Animated entries are addressed by base name; still frames by key.
        let exists = sprites.contains(name) || animations.contains(name)
            || sprites.contains("\(name)/0")
        XCTAssertTrue(exists, "\(context): missing sprite '\(name)'",
                      file: file, line: line)
    }

    func testManifestIsPresent() throws {
        try XCTSkipIf(Self.manifest == nil,
                      "Assets/generated/game.json not built — run Tools/pixelforge/build_assets.py")
        XCTAssertFalse(sprites.isEmpty)
        XCTAssertFalse(animations.isEmpty)
    }

    func testWeaponSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for def in WeaponCatalog.all {
            assertSprite(def.sprite, "weapon \(def.id)")
            assertSprite(def.projectileSprite, "weapon \(def.id) projectile")
            assertSprite(def.muzzleFX, "weapon \(def.id) muzzle")
            assertSprite(def.impactFX, "weapon \(def.id) impact")
        }
    }

    func testItemAndPickupSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for def in ItemCatalog.all {
            assertSprite(def.sprite, "item \(def.id)")
        }
        for name in ["heart", "heart_half", "armor", "ammo_box", "key", "coin",
                     "blank"] {
            assertSprite("pickup/\(name)", "pickup")
        }
    }

    func testEnemySpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for def in EnemyCatalog.all {
            switch def.rig {
            case .humanoid:
                for anim in ["idle_front", "walk_front", "idle_side",
                             "walk_side", "idle_back", "walk_back", "die"] {
                    assertSprite("\(def.spriteBase)/\(anim)",
                                 "enemy \(def.id) animation \(anim)")
                }
            case .creature, .boss:
                assertSprite(def.spriteBase, "enemy \(def.id)")
            }
        }
    }

    func testEnemyAttackSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for def in EnemyCatalog.all {
            guard let pattern = def.attack else { continue }
            if let sprite = Self.projectileSprite(of: pattern) {
                assertSprite(sprite, "enemy \(def.id) attack")
            }
            if case let .summon(kind, _) = pattern {
                XCTAssertNotNil(EnemyCatalog.enemy(kind),
                                "enemy \(def.id) summons unknown '\(kind)'")
            }
        }
    }

    func testBossSpritesAndMovesAreValid() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for boss in BossCatalog.all {
            assertSprite(boss.spriteBase, "boss \(boss.id)")
            XCTAssertFalse(boss.phases.isEmpty, "boss \(boss.id) has no phases")
            for phase in boss.phases {
                XCTAssertFalse(phase.moves.isEmpty,
                               "boss \(boss.id) has an empty phase")
                for move in phase.moves {
                    if let sprite = Self.projectileSprite(of: move.pattern) {
                        assertSprite(sprite, "boss \(boss.id) move \(move.name)")
                    }
                    if case let .summon(kind, _) = move.pattern {
                        XCTAssertNotNil(EnemyCatalog.enemy(kind),
                                        "boss \(boss.id) summons unknown '\(kind)'")
                    }
                }
            }
        }
    }

    func testCharacterSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for character in CharacterCatalog.all {
            assertSprite("\(character.spriteBase)/idle_front", "character")
            assertSprite("\(character.spriteBase)/roll", "character")
            assertSprite(character.portrait, "portrait")
            XCTAssertNotNil(WeaponCatalog.weapon(character.startingWeapon),
                            "\(character.id) starts with unknown weapon")
            if let item = character.startingItem {
                XCTAssertNotNil(ItemCatalog.item(item),
                                "\(character.id) starts with unknown item")
            }
        }
    }

    func testTileAndPropSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for theme in RunState.themeOrder {
            for mask in 0..<16 {
                assertSprite("tile/\(theme)/cap_\(mask)", "wall cap")
            }
            for i in 0..<4 {
                assertSprite("tile/\(theme)/floor_\(i)", "floor")
                assertSprite("tile/\(theme)/face_\(i)", "wall face")
            }
            assertSprite("tile/\(theme)/wall_shadow", "wall shadow")
            for state in ["closed", "open", "locked", "boss"] {
                for axis in ["v", "h"] {
                    assertSprite("tile/\(theme)/door_\(state)_\(axis)", "door")
                }
            }
            for prop in ["barrel", "crate", "chest_closed", "chest_rare",
                         "pillar", "statue", "shop_counter", "bone_pile",
                         "barrel_explosive", "torch"] {
                assertSprite("prop/\(theme)/\(prop)", "prop")
            }
        }
    }

    func testEffectSpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for name in ["muzzle_flash", "impact_spark", "explosion", "smoke_puff",
                     "dust_ring", "blood_splat", "heal_sparkle", "pickup_shine",
                     "portal", "shockwave", "freeze_shatter", "poison_cloud",
                     "lightning_arc", "teleport"] {
            assertSprite("fx/\(name)", "effect")
        }
    }

    func testUISpritesExist() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        for name in ["panel", "heart_full", "heart_half", "heart_empty",
                     "armor_ui", "ammo_icon", "blank_icon", "key_icon",
                     "coin_icon", "slot", "slot_active", "crosshair",
                     "boss_bar_frame", "bar_fill_boss", "vignette",
                     "damage_flash"] {
            assertSprite("ui/\(name)", "ui")
        }
        for kind in RoomKind.allCases {
            assertSprite("ui/minimap_\(kind.minimapKey)", "minimap")
        }
        assertSprite("ui/minimap_current", "minimap")
        assertSprite("ui/minimap_cleared", "minimap")
    }

    func testFontCoversTheCharactersTheGamePrints() throws {
        try XCTSkipIf(Self.manifest == nil, "atlas not built")
        guard let font = Self.manifest?["font"] as? [String: Any],
              let glyphs = font["glyphs"] as? [String: Any] else {
            return XCTFail("manifest has no font table")
        }
        var strings = ["Depth", "Kills", "Rooms", "SYNERGY"]
        strings += WeaponCatalog.all.flatMap { [$0.name, $0.flavor] }
        strings += ItemCatalog.all.flatMap { [$0.name, $0.effect, $0.flavor] }
        strings += SynergyCatalog.all.flatMap { [$0.name, $0.summary] }
        strings += CharacterCatalog.all.flatMap { [$0.name, $0.blurb, $0.passiveText] }
        strings += BossCatalog.all.flatMap { boss in
            [boss.name, boss.title] + boss.phases.map(\.announcement)
        }

        var missing: Set<Character> = []
        for text in strings {
            for character in text where glyphs[String(character.unicodeScalars.first!.value)] == nil {
                missing.insert(character)
            }
        }
        XCTAssertTrue(missing.isEmpty,
                      "font cannot render: \(missing.sorted().map(String.init).joined(separator: " "))")
    }

    // -- helpers -------------------------------------------------------------

    private static func projectileSprite(of pattern: AttackPattern) -> String? {
        switch pattern {
        case let .aimed(_, _, _, _, sprite): return sprite
        case let .radial(_, _, _, sprite, _): return sprite
        case let .ringGap(_, _, _, _, sprite): return sprite
        case let .spiral(_, _, _, sprite, _): return sprite
        case let .wave(_, _, _, _, _, sprite): return sprite
        case let .flower(_, _, _, _, _, sprite): return sprite
        case let .serpent(_, _, _, _, _, sprite): return sprite
        case let .seekers(_, _, _, _, sprite): return sprite
        case let .cross(_, _, _, _, sprite): return sprite
        case .dash, .detonate, .summon, .beamSweep: return nil
        }
    }
}
