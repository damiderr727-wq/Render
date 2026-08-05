import XCTest
@testable import PixelRogueCore

/// End-to-end checks that the simulation runs, stays deterministic and never
/// drifts into an unplayable state.
final class SimulationTests: XCTestCase {

    private func makeWorld(seed: UInt64 = 12345, depth: Int = 1) -> World {
        var run = RunState(seed: seed)
        run.depth = depth
        return World(run: run)
    }

    // -- determinism ---------------------------------------------------------

    func testSameSeedProducesSameFloor() {
        let a = DungeonGenerator().generate(floor: 2, theme: "crypt", seed: 999)
        let b = DungeonGenerator().generate(floor: 2, theme: "crypt", seed: 999)
        XCTAssertEqual(a.rooms.count, b.rooms.count)
        XCTAssertEqual(a.startRoom, b.startRoom)
        XCTAssertEqual(a.bossRoom, b.bossRoom)
        for (roomA, roomB) in zip(a.rooms, b.rooms) {
            XCTAssertEqual(roomA.floorRect, roomB.floorRect)
            XCTAssertEqual(roomA.kind, roomB.kind)
        }
    }

    func testDifferentSeedsProduceDifferentFloors() {
        let a = DungeonGenerator().generate(floor: 1, theme: "keep", seed: 1)
        let b = DungeonGenerator().generate(floor: 1, theme: "keep", seed: 2)
        let sameLayout = a.rooms.count == b.rooms.count &&
            zip(a.rooms, b.rooms).allSatisfy { $0.floorRect == $1.floorRect }
        XCTAssertFalse(sameLayout, "two seeds produced an identical floor")
    }

    func testRNGStreamIsStable() {
        var rng = RNG(seed: 42)
        let first = (0..<5).map { _ in rng.int(0, 999) }
        var again = RNG(seed: 42)
        let second = (0..<5).map { _ in again.int(0, 999) }
        XCTAssertEqual(first, second)
    }

    // -- floor structure -----------------------------------------------------

    func testEveryFloorHasStartAndBoss() {
        for seed in UInt64(1)...30 {
            for floor in 1...4 {
                let dungeon = DungeonGenerator().generate(
                    floor: floor, theme: "keep", seed: seed &* 77 &+ UInt64(floor))
                XCTAssertEqual(dungeon.rooms.filter { $0.kind == .start }.count, 1,
                               "seed \(seed) floor \(floor) start rooms")
                XCTAssertGreaterThanOrEqual(
                    dungeon.rooms.filter { $0.kind == .boss }.count, 1,
                    "seed \(seed) floor \(floor) has no boss room")
            }
        }
    }

    func testAllRoomsReachableFromStart() {
        for seed in UInt64(1)...25 {
            let dungeon = DungeonGenerator().generate(floor: 3, theme: "keep",
                                                      seed: seed &* 131)
            var adjacency = [Int: Set<Int>]()
            for door in dungeon.doors {
                adjacency[door.roomA, default: []].insert(door.roomB)
                adjacency[door.roomB, default: []].insert(door.roomA)
            }
            var seen: Set<Int> = [dungeon.startRoom]
            var stack = [dungeon.startRoom]
            while let current = stack.popLast() {
                for next in adjacency[current] ?? [] where !seen.contains(next) {
                    seen.insert(next)
                    stack.append(next)
                }
            }
            XCTAssertEqual(seen.count, dungeon.rooms.count,
                           "seed \(seed): \(dungeon.rooms.count - seen.count) rooms unreachable")
        }
    }

    func testRoomFloorsAreWalkable() {
        let dungeon = DungeonGenerator().generate(floor: 1, theme: "keep", seed: 7)
        for room in dungeon.rooms {
            XCTAssertTrue(dungeon.map.isWalkable(room.center),
                          "room \(room.index) centre is solid")
            XCTAssertEqual(dungeon.map.room(at: room.center), room.index)
        }
    }

    func testPlayerStartsInsideTheStartRoom() {
        let world = makeWorld()
        let player = world.playerActor
        XCTAssertNotNil(player)
        XCTAssertEqual(world.currentRoom, world.dungeon.startRoom)
        XCTAssertTrue(world.dungeon.map.isWalkable(player!.position))
    }

    // -- movement and collision ----------------------------------------------

    func testPlayerCannotWalkThroughWalls() {
        let world = makeWorld()
        var input = InputState()
        input.move = Vec2(-1, 0)   // straight into the west wall
        for _ in 0..<600 {
            world.step(dt: 1.0 / 60.0, input: input)
        }
        let player = world.playerActor!
        XCTAssertTrue(world.dungeon.map.isWalkable(player.position),
                      "player ended up inside geometry at \(player.position)")
    }

    func testDodgeGrantsInvulnerability() {
        let world = makeWorld()
        var input = InputState()
        input.move = Vec2(1, 0)
        input.dodgePressed = true
        world.step(dt: 1.0 / 60.0, input: input)
        XCTAssertTrue(world.player.isDodging)
        XCTAssertGreaterThan(world.playerActor!.invulnerableFor, 0)
    }

    func testDodgeHasCooldown() {
        let world = makeWorld()
        var input = InputState()
        input.move = Vec2(1, 0)
        input.dodgePressed = true
        world.step(dt: 1.0 / 60.0, input: input)

        input.dodgePressed = false
        for _ in 0..<24 { world.step(dt: 1.0 / 60.0, input: input) }
        XCTAssertFalse(world.player.isDodging)
        XCTAssertGreaterThan(world.player.dodgeCooldown, 0)
    }

    // -- shooting ------------------------------------------------------------

    func testFiringSpawnsProjectiles() {
        let world = makeWorld()
        var input = InputState()
        input.aim = world.playerActor!.position + Vec2(100, 0)
        input.firing = true
        world.step(dt: 1.0 / 60.0, input: input)
        XCTAssertFalse(world.projectiles.isEmpty, "trigger pull produced no bullets")
        XCTAssertEqual(world.projectiles.first?.faction, .player)
    }

    func testFireRateIsRespected() {
        let world = makeWorld()
        var input = InputState()
        input.aim = world.playerActor!.position + Vec2(100, 0)
        input.firing = true
        // Peacemaker fires every 0.28s, so one second of holding is ~4 shots.
        var shots = 0
        for _ in 0..<60 {
            let before = world.projectiles.count
            world.step(dt: 1.0 / 60.0, input: input)
            if world.projectiles.count > before { shots += 1 }
        }
        XCTAssertGreaterThan(shots, 1)
        XCTAssertLessThan(shots, 8, "fire rate ignored: \(shots) shots in a second")
    }

    func testShotgunFiresMultiplePellets() {
        var run = RunState(seed: 5)
        _ = run.loadout.add(weapon: WeaponCatalog.scattergun)
        let world = World(run: run)
        var input = InputState()
        input.aim = world.playerActor!.position + Vec2(100, 0)
        input.firing = true
        world.step(dt: 1.0 / 60.0, input: input)
        XCTAssertGreaterThanOrEqual(world.projectiles.count, 5)
    }

    func testAmmoDepletes() {
        var run = RunState(seed: 5)
        _ = run.loadout.add(weapon: WeaponCatalog.scattergun)
        let world = World(run: run)
        var input = InputState()
        input.aim = world.playerActor!.position + Vec2(100, 0)
        input.firing = true
        for _ in 0..<300 { world.step(dt: 1.0 / 60.0, input: input) }
        let weapon = world.run.loadout.activeWeapon!
        XCTAssertLessThan(weapon.reserveAmmo, weapon.def.reserve,
                          "reserve ammo never went down")
    }

    // -- damage and death ----------------------------------------------------

    func testEnemyTakesDamageAndDies() {
        let world = makeWorld()
        let def = EnemyCatalog.enemy("crawler")!
        let position = world.playerActor!.position + Vec2(40, 0)
        let id = world.spawnEnemy(def, at: position, room: world.currentRoom)
        XCTAssertNotNil(world.actor(id))

        var input = InputState()
        input.aim = position
        input.firing = true
        for _ in 0..<600 {
            world.step(dt: 1.0 / 60.0, input: input)
            if world.actor(id) == nil { break }
        }
        XCTAssertNil(world.actor(id), "enemy survived 10 seconds of point-blank fire")
        XCTAssertGreaterThan(world.run.kills, 0)
    }

    func testPlayerTakesDamageFromEnemyBullets() {
        // The Stray carries no armour, so a hit lands on health directly.
        let run = RunState(seed: 1, character: CharacterCatalog.character("stray")!)
        let world = World(run: run)
        let start = world.playerActor!.health
        world.fire(def: WeaponCatalog.peacemaker,
                   from: world.playerActor!.position + Vec2(60, 0),
                   angle: .pi, stats: StatBlock(), faction: .enemy,
                   owner: .none)
        for _ in 0..<60 { world.step(dt: 1.0 / 60.0, input: InputState()) }
        XCTAssertLessThan(world.playerActor!.health, start)
    }

    func testArmorAbsorbsAHitBeforeHealth() {
        let world = makeWorld()   // the Marshal starts with one armour
        let startHealth = world.playerActor!.health
        let startArmor = world.playerActor!.armor
        XCTAssertGreaterThan(startArmor, 0)
        world.fire(def: WeaponCatalog.peacemaker,
                   from: world.playerActor!.position + Vec2(60, 0),
                   angle: .pi, stats: StatBlock(), faction: .enemy, owner: .none)
        for _ in 0..<60 { world.step(dt: 1.0 / 60.0, input: InputState()) }
        XCTAssertEqual(world.playerActor!.armor, startArmor - 1)
        XCTAssertEqual(world.playerActor!.health, startHealth,
                       "armour did not fully absorb the hit")
    }

    func testInvulnerabilityPreventsDoubleHits() {
        let world = makeWorld()
        let position = world.playerActor!.position
        for _ in 0..<6 {
            world.fire(def: WeaponCatalog.peacemaker, from: position + Vec2(20, 0),
                       angle: .pi, stats: StatBlock(), faction: .enemy,
                       owner: .none)
        }
        let start = world.playerActor!.health
        for _ in 0..<30 { world.step(dt: 1.0 / 60.0, input: InputState()) }
        let lost = start - world.playerActor!.health
        XCTAssertLessThanOrEqual(lost, 14,
                                 "i-frames failed: took \(lost) from one volley")
    }

    // -- stability -----------------------------------------------------------

    func testLongRunWithRandomInputStaysSane() {
        let world = makeWorld(seed: 4242)
        var rng = RNG(seed: 1)
        var input = InputState()

        for frame in 0..<7200 {   // two minutes at 60Hz
            if frame % 20 == 0 {
                input.move = rng.unitVector()
                input.aim = world.playerActor.map {
                    $0.position + rng.unitVector() * 120
                } ?? .zero
                input.firing = rng.chance(0.7)
                input.dodgePressed = rng.chance(0.08)
                input.interactPressed = rng.chance(0.15)
            }
            world.step(dt: 1.0 / 60.0, input: input)
            input.clearEdges()

            if let player = world.playerActor {
                XCTAssertFalse(player.position.x.isNaN || player.position.y.isNaN,
                               "player position went NaN at frame \(frame)")
                XCTAssertTrue(world.dungeon.map.worldBounds
                    .expanded(by: 40).contains(player.position),
                              "player escaped the map at frame \(frame)")
            }
            XCTAssertLessThanOrEqual(world.projectiles.count, 1200)
            _ = world.drainEvents()
            if world.playerDead { break }
        }
    }

    func testProjectilesAreEventuallyCleanedUp() {
        let world = makeWorld()
        for i in 0..<40 {
            world.fire(def: WeaponCatalog.ripper,
                       from: world.playerActor!.position,
                       angle: Double(i) * 0.157, stats: StatBlock(),
                       faction: .player, owner: world.playerID)
        }
        XCTAssertGreaterThan(world.projectiles.count, 0)
        for _ in 0..<600 { world.step(dt: 1.0 / 60.0, input: InputState()) }
        XCTAssertEqual(world.projectiles.count, 0,
                       "bullets outlived their lifetime")
    }

    func testBossSpawnsAndFightsBack() {
        let world = makeWorld(seed: 808, depth: 1)
        let bossRoom = world.dungeon.rooms[world.dungeon.bossRoom]
        let def = BossCatalog.boss(forFloor: 1)
        _ = def
        // Drop the player into the boss room directly, then let it act.
        world.teleportPlayer(to: bossRoom.center + Vec2(0, 60))
        var input = InputState()
        // Counting distinct ids rather than the live count: a stationary
        // target eats each volley on contact, so "bullets on screen" says
        // nothing about how much the boss actually fired.
        var fired: Set<Int> = []
        for _ in 0..<900 {
            world.step(dt: 1.0 / 60.0, input: input)
            input.clearEdges()
            for projectile in world.projectiles where projectile.faction == .enemy {
                fired.insert(projectile.id)
            }
        }
        XCTAssertNotNil(world.activeBoss, "boss never spawned in the boss room")
        XCTAssertGreaterThanOrEqual(fired.count, 25,
                                    "boss fired only \(fired.count) shots in 15s")
    }
}
