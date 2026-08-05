import XCTest
@testable import PixelRogueCore

/// The depth ordering that makes flat sprites read as a room with height is a
/// rule, not a rendering detail — so it is asserted here rather than left to
/// be noticed in a screenshot.
final class SceneSnapshotTests: XCTestCase {

    private func makeWorld(seed: UInt64 = 4242) -> World {
        World(run: RunState(seed: seed))
    }

    func testStaticCommandsCoverEveryFloorTile() {
        let dungeon = DungeonGenerator().generate(floor: 1, theme: "keep", seed: 11)
        let commands = SceneSnapshot.staticCommands(for: dungeon)
        let floorKeys = Set(commands.filter { $0.key.hasPrefix("floor:") }.map(\.key))

        var expected = 0
        for y in 0..<dungeon.map.height {
            for x in 0..<dungeon.map.width where !dungeon.map[x, y].blocksMovement {
                expected += 1
                XCTAssertTrue(floorKeys.contains("floor:\(x),\(y)"),
                              "walkable tile \(x),\(y) has no floor sprite")
            }
        }
        XCTAssertEqual(floorKeys.count, expected)
    }

    func testCommandKeysAreUnique() {
        // Keys drive node reuse in the renderer; a duplicate silently makes
        // two things share one node.
        let world = makeWorld()
        let commands = SceneSnapshot.staticCommands(for: world.dungeon)
            + SceneSnapshot.dynamicCommands(for: world)
        let keys = commands.map(\.key)
        XCTAssertEqual(Set(keys).count, keys.count, "duplicate sprite key")
    }

    func testFloorAlwaysSortsBelowEverythingElse() {
        let world = makeWorld()
        let commands = SceneSnapshot.staticCommands(for: world.dungeon)
            + SceneSnapshot.dynamicCommands(for: world)
        let floorDepth = commands.filter { $0.key.hasPrefix("floor:") }
            .map(\.depth).max() ?? 0
        let othersMin = commands.filter { !$0.key.hasPrefix("floor:")
            && !$0.key.hasPrefix("pit:") }.map(\.depth).min() ?? 0
        XCTAssertLessThan(floorDepth, othersMin)
    }

    func testActorSouthOfAWallDrawsInFrontOfIt() {
        let world = makeWorld()
        guard let player = world.playerActor else { return XCTFail("no player") }
        let commands = SceneSnapshot.staticCommands(for: world.dungeon)
        let (px, py) = world.dungeon.map.tileCoord(player.position)

        // Find the nearest wall block north of the player in the same column.
        var wallY: Int?
        for y in stride(from: py - 1, through: max(0, py - 6), by: -1)
        where world.dungeon.map[px, y] == .wall {
            wallY = y
            break
        }
        guard let wallY else { return }   // player not below a wall on this seed

        guard let cap = commands.first(where: { $0.key == "cap:\(px),\(wallY)" })
        else { return XCTFail("wall at \(px),\(wallY) has no cap sprite") }

        let playerDepth = SceneSnapshot.Depth.world + player.position.y
        XCTAssertGreaterThan(playerDepth, cap.depth,
                             "player standing south of a wall sorts behind it")
    }

    func testActorNorthOfAWallDrawsBehindIt() {
        let world = makeWorld()
        let commands = SceneSnapshot.staticCommands(for: world.dungeon)
        guard let cap = commands.first(where: { $0.key.hasPrefix("cap:") })
        else { return XCTFail("no walls generated") }

        // Anything a tile further up the screen must sort behind the block.
        let aboveDepth = SceneSnapshot.Depth.world + cap.position.y - TileMap.tileSize
        XCTAssertLessThan(aboveDepth, cap.depth)
    }

    func testProjectilesSortAboveActors() {
        let world = makeWorld()
        var input = InputState()
        input.aim = (world.playerActor?.position ?? .zero) + Vec2(80, 0)
        input.firing = true
        world.step(dt: 1.0 / 60.0, input: input)

        let commands = SceneSnapshot.dynamicCommands(for: world)
        let bullets = commands.filter { $0.key.hasPrefix("proj:") }
        let actors = commands.filter { $0.key.hasPrefix("actor:") }
        XCTAssertFalse(bullets.isEmpty)
        XCTAssertFalse(actors.isEmpty)
        // In a bullet hell the player must never lose a bullet behind a body.
        XCTAssertGreaterThan(bullets.map(\.depth).min()!, actors.map(\.depth).max()!)
    }

    func testWeaponIsHeldByItsGrip() {
        let world = makeWorld()
        let commands = SceneSnapshot.dynamicCommands(for: world)
        guard let weapon = commands.first(where: { $0.key.hasSuffix(":weapon") })
        else { return XCTFail("player is not holding anything") }
        XCTAssertEqual(weapon.anchor, .weaponPivot)
        XCTAssertTrue(weapon.sprite.hasPrefix("weapon/"))
    }

    func testDyingActorsFadeOut() {
        let world = makeWorld()
        let def = EnemyCatalog.enemy("crawler")!
        let position = (world.playerActor?.position ?? .zero) + Vec2(30, 0)
        let id = world.spawnEnemy(def, at: position, room: world.currentRoom)

        var input = InputState()
        input.aim = position
        input.firing = true
        for _ in 0..<600 {
            world.step(dt: 1.0 / 60.0, input: input)
            guard let actor = world.actors.first(where: { $0.id == id }),
                  actor.isDying else { continue }

            // The fade starts at full opacity on the frame of death, so the
            // check is that it *progresses*, not that it has already begun.
            var commands = SceneSnapshot.dynamicCommands(for: world)
            let first = commands.first { $0.key == "actor:\(id.raw):body" }
            XCTAssertNotNil(first, "a dying enemy stopped being drawn")

            for _ in 0..<8 { world.step(dt: 1.0 / 60.0, input: InputState()) }
            commands = SceneSnapshot.dynamicCommands(for: world)
            if let later = commands.first(where: { $0.key == "actor:\(id.raw):body" }) {
                XCTAssertLessThan(later.alpha, first!.alpha,
                                  "death fade never progressed")
            }
            return
        }
    }

    func testEveryCommandNamesSomethingThatCouldExist() {
        // Cheap guard against a formatting slip in a sprite name; the atlas
        // contract test proves the names actually resolve.
        let world = makeWorld()
        let commands = SceneSnapshot.staticCommands(for: world.dungeon)
            + SceneSnapshot.dynamicCommands(for: world)
        for command in commands {
            XCTAssertFalse(command.sprite.isEmpty, "empty sprite for \(command.key)")
            XCTAssertFalse(command.sprite.contains("//"),
                           "malformed sprite name '\(command.sprite)'")
            XCTAssertFalse(command.sprite.hasSuffix("/"),
                           "truncated sprite name '\(command.sprite)'")
        }
    }
}
