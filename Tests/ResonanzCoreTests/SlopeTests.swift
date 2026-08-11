import XCTest
@testable import ResonanzCore

/// Prueft die Schraegen: Hoehenfunktion, Aufsetzen, Begehbarkeit.
final class SlopeTests: XCTestCase {

    /// Ein Testraum aus Zeilen. `/` steigt nach rechts, `\` faellt.
    private func room(_ rows: [String]) -> Room {
        let data = RoomData(
            id: "SLOPE", name: "SLOPE", region: .hain, music: "hain",
            width: rows[0].count, height: rows.count, darkness: 0,
            tiles: rows, doors: [], spawns: [:], benches: [], enemies: [],
            pickups: [], decor: [], lore: [], boss: nil)
        return Room(data: data)
    }

    private func simulate(_ player: Player, in room: Room, seconds: Double,
                          input: PlayerInput) {
        var events: [GameEvent] = []
        var t = 0.0
        while t < seconds {
            player.update(dt: 1.0 / 60.0, input: input, room: room, events: &events)
            events.removeAll(keepingCapacity: true)
            t += 1.0 / 60.0
        }
    }

    func testHoehenfunktionLaeuftLinear() {
        let r = room(["....", "./..", "####"])
        // Kachel (1,1) steigt nach rechts: links unten, rechts oben.
        let left = r.slopeSurfaceY(1, 1, worldX: 1 * tileSize + 0.5)
        let right = r.slopeSurfaceY(1, 1, worldX: 2 * tileSize - 0.5)
        XCTAssertEqual(try XCTUnwrap(left), 2 * tileSize, accuracy: 1.0)
        XCTAssertEqual(try XCTUnwrap(right), 1 * tileSize, accuracy: 1.0)
        XCTAssertNil(r.slopeSurfaceY(0, 1, worldX: 4))
    }

    func testSchraegeBlockiertNichtWaagerecht() {
        let r = room(["....", "./..", "####"])
        // Sonst liefe man gegen die Kachelkante wie gegen eine Wand.
        XCTAssertFalse(r.tile(1, 1).isBlocking)
        XCTAssertTrue(r.tile(1, 1).isStandable)
    }

    /// Die Figur muss die Rampe hinauflaufen, nicht davor stehenbleiben.
    func testFigurLaeuftDieRampeHinauf() {
        // Der Boden davor liegt eine Reihe unter der ersten Rampenkachel -
        // deren linke Kante sitzt naemlich auf ihrer Unterkante.
        let rows = [
            "..............",
            "..............",
            "..............",
            "...........#..",
            "..........//..",
            ".........//#..",
            "############..",
            "##############",
        ]
        let r = room(rows)
        let player = Player(position: Vec2(3 * tileSize + 8, 6 * tileSize),
                            progression: Progression(), kern: .leier)
        player.placeAt(Vec2(3 * tileSize + 8, 6 * tileSize), facing: 1)

        let start = player.position.y
        simulate(player, in: r, seconds: 2.0, input: PlayerInput(moveX: 1))

        XCTAssertLessThan(player.position.y, start - tileSize * 1.5,
                          "Die Figur muss ueber die Rampe an Hoehe gewinnen")
        XCTAssertTrue(player.onGround, "Am Ende steht sie auf der Rampe")
    }

    /// Und wieder hinunter, ohne in der Luft zu haengen oder durchzufallen.
    func testFigurLaeuftDieRampeHinunter() {
        let rows = [
            "..............",
            "..............",
            "##\\..........",
            "###\\.........",
            "####\\........",
            "##############",
            "##############",
            "##############",
        ]
        let r = room(rows)
        let player = Player(position: Vec2(1 * tileSize + 8, 2 * tileSize),
                            progression: Progression(), kern: .leier)
        player.placeAt(Vec2(1 * tileSize + 8, 2 * tileSize), facing: 1)

        simulate(player, in: r, seconds: 2.0, input: PlayerInput(moveX: 1))

        XCTAssertGreaterThan(player.position.y, 4 * tileSize,
                             "Die Figur muss die Boeschung hinunterkommen")
        XCTAssertTrue(player.onGround)
        XCTAssertLessThanOrEqual(player.position.y, 5 * tileSize + 1,
                                 "Sie darf dabei nicht durch den Boden fallen")
    }

    func testSchraegenZaehlenAlsStandflaeche() throws {
        // In der echten Welt: A1 traegt zwei Rampen, und die Raumpruefung
        // muss sie als begehbar fuehren.
        let catalog = try WorldCatalog()
        let a1 = try catalog.room("A1")
        var slopes = 0
        for ty in 0..<a1.height {
            for tx in 0..<a1.width where a1.tile(tx, ty).isSlope { slopes += 1 }
        }
        XCTAssertGreaterThan(slopes, 0, "A1 soll Rampen haben, nicht nur Stufen")

        let probe = ReachabilityProbe(room: a1, progression: Progression())
        let result = probe.run(from: ReachabilityProbe.origins(for: a1),
                               targets: ReachabilityProbe.targets(for: a1))
        XCTAssertTrue(result.ok)
    }
}
