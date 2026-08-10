import XCTest
@testable import ResonanzCore

/// Prueft, dass die vom Python-Generator erzeugte Welt in sich stimmig ist.
final class WorldTests: XCTestCase {

    func testAlleRaeumeLaden() throws {
        let catalog = try WorldCatalog()
        XCTAssertFalse(catalog.roomIDs.isEmpty)
        for room in try catalog.loadAll() {
            XCTAssertEqual(room.tiles.count, room.width * room.height,
                           "\(room.id): Rastergroesse passt nicht")
            XCTAssertFalse(room.name.isEmpty)
        }
    }

    func testRaeumeSindVonFelsUmschlossen() throws {
        let catalog = try WorldCatalog()
        for room in try catalog.loadAll() {
            // Tueroeffnungen duerfen den Rand durchbrechen, sonst nichts.
            let openings = room.data.doors.map { room.doorRect($0).inset(by: -1) }
            func istTuer(_ tx: Int, _ ty: Int) -> Bool {
                let point = Vec2(Double(tx) * tileSize + tileSize / 2,
                                 Double(ty) * tileSize + tileSize / 2)
                return openings.contains { $0.contains(point) }
            }
            for tx in 0..<room.width {
                for ty in [0, room.height - 1] where room.tile(tx, ty) == .air {
                    XCTAssertTrue(istTuer(tx, ty), "\(room.id): Loch im Rand bei (\(tx),\(ty))")
                }
            }
        }
    }

    func testTuerenSindGegenseitigVerbunden() throws {
        let catalog = try WorldCatalog()
        let rooms = try catalog.loadAll()
        let byID = Dictionary(uniqueKeysWithValues: rooms.map { ($0.id, $0) })

        for room in rooms {
            for door in room.data.doors {
                guard let target = byID[door.target] else {
                    return XCTFail("\(room.id).\(door.id): Zielraum \(door.target) fehlt")
                }
                XCTAssertNotNil(target.spawn(named: door.targetDoor),
                                "\(room.id).\(door.id): Spawnpunkt '\(door.targetDoor)' "
                                + "fehlt in \(target.id)")
                XCTAssertTrue(target.data.doors.contains { $0.target == room.id },
                              "\(room.id).\(door.id) -> \(target.id): kein Rueckweg")
            }
        }
    }

    func testSpawnpunkteStehenImFreien() throws {
        let catalog = try WorldCatalog()
        for room in try catalog.loadAll() {
            for (name, spawn) in room.data.spawns {
                let body = Rect(footAt: Vec2.entity(spawn.x, spawn.y),
                                width: Tuning.playerWidth, height: Tuning.playerHeight)
                XCTAssertFalse(room.overlapsSolid(body.inset(by: 1)),
                               "\(room.id): Spawn '\(name)' steckt im Fels")
                XCTAssertFalse(room.overlapsHazard(body),
                               "\(room.id): Spawn '\(name)' liegt in Dornen")
            }
        }
    }

    func testJedeFaehigkeitLiegtGenauEinmalInDerWelt() throws {
        let catalog = try WorldCatalog()
        var gefunden: [String: Int] = [:]
        for room in try catalog.loadAll() {
            for pickup in room.data.pickups where pickup.kind == "ability" {
                gefunden[pickup.id, default: 0] += 1
            }
        }
        for ability in Ability.allCases {
            XCTAssertEqual(gefunden[ability.rawValue], 1,
                           "\(ability.rawValue) muss genau einmal vorkommen")
        }
    }
}
