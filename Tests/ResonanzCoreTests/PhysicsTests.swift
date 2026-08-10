import XCTest
@testable import ResonanzCore

/// Prueft das Bewegungsgefuehl in Zahlen: Sprunghoehe, Landung, Wandhaftung.
final class PhysicsTests: XCTestCase {

    /// Ein Testraum: ebener Boden, optional Hindernisse.
    private func flatRoom(width: Int = 40, height: Int = 20, floor: Int = 15) -> Room {
        var rows: [String] = []
        for y in 0..<height {
            if y == 0 || y >= floor {
                rows.append(String(repeating: "#", count: width))
            } else {
                rows.append("#" + String(repeating: ".", count: width - 2) + "#")
            }
        }
        return room(from: rows)
    }

    private func room(from rows: [String]) -> Room {
        let data = RoomData(
            id: "TEST", name: "TEST", region: .hain, music: "hain",
            width: rows[0].count, height: rows.count, darkness: 0,
            tiles: rows, doors: [], spawns: [:], benches: [], enemies: [],
            pickups: [], decor: [], lore: [], boss: nil)
        return Room(data: data)
    }

    private func makePlayer(in room: Room, at tile: Vec2,
                            abilities: Set<Ability> = []) -> Player {
        let progression = Progression(abilities: abilities)
        let player = Player(position: Vec2.tiles(tile.x, tile.y),
                            progression: progression, instrument: .leier)
        player.placeAt(Vec2.tiles(tile.x, tile.y), facing: 1)
        return player
    }

    private func simulate(_ player: Player, in room: Room, seconds: Double,
                          input: (Double) -> PlayerInput) {
        var events: [GameEvent] = []
        let dt = 1.0 / 60.0
        var t = 0.0
        while t < seconds {
            player.update(dt: dt, input: input(t), room: room, events: &events)
            events.removeAll(keepingCapacity: true)
            t += dt
        }
    }

    // MARK: - Landung

    /// Nach einem Sprung muss die Figur genau auf der Kachelkante stehen.
    /// Bleibt sie darueber haengen, sind alle Bodenpruefungen daneben.
    func testLandetBuendigAufDemBoden() {
        let room = flatRoom()
        let player = makePlayer(in: room, at: Vec2(10, 15))
        simulate(player, in: room, seconds: 1.5) { t in
            PlayerInput(jumpHeld: t < 0.4, jumpPressed: t < 0.001)
        }
        XCTAssertTrue(player.onGround, "Figur sollte gelandet sein")
        XCTAssertEqual(player.position.y, 15 * tileSize, accuracy: 0.1,
                       "Fusslinie muss auf der Kachelkante liegen")
    }

    func testFaelltAufDenBodenUndBleibtLiegen() {
        let room = flatRoom()
        let player = makePlayer(in: room, at: Vec2(10, 4))
        simulate(player, in: room, seconds: 2.0) { _ in .neutral }
        XCTAssertEqual(player.position.y, 15 * tileSize, accuracy: 0.1)
        XCTAssertEqual(player.velocity.y, 0, accuracy: 0.01)
    }

    // MARK: - Sprunghoehe

    func testSprunghoeheEntsprichtDerAuslegung() {
        let room = flatRoom(height: 30, floor: 25)
        let player = makePlayer(in: room, at: Vec2(10, 25))
        var hoechster = player.position.y
        var events: [GameEvent] = []
        var t = 0.0
        while t < 1.2 {
            player.update(dt: 1.0 / 60.0,
                          input: PlayerInput(jumpHeld: true, jumpPressed: t < 0.001),
                          room: room, events: &events)
            events.removeAll(keepingCapacity: true)
            hoechster = min(hoechster, player.position.y)
            t += 1.0 / 60.0
        }
        let hoehe = (25 * tileSize - hoechster) / tileSize
        // Rechnerisch v^2 / (2 * g * riseScale) = 400^2 / (2 * 1290) = 62 px = 3,9 Kacheln.
        XCTAssertGreaterThan(hoehe, 3.0, "Sprung zu niedrig: \(hoehe) Kacheln")
        XCTAssertLessThan(hoehe, 4.5, "Sprung zu hoch: \(hoehe) Kacheln")
    }

    func testDoppelsprungKommtHoeher() {
        let room = flatRoom(height: 30, floor: 25)

        func gipfel(abilities: Set<Ability>, zweiterSprung: Bool) -> Double {
            let player = makePlayer(in: room, at: Vec2(10, 25), abilities: abilities)
            var hoechster = player.position.y
            var events: [GameEvent] = []
            var t = 0.0
            while t < 1.5 {
                let second = zweiterSprung && t >= 0.30 && t < 0.32
                player.update(dt: 1.0 / 60.0,
                              input: PlayerInput(jumpHeld: true,
                                                 jumpPressed: t < 0.001 || second),
                              room: room, events: &events)
                events.removeAll(keepingCapacity: true)
                hoechster = min(hoechster, player.position.y)
                t += 1.0 / 60.0
            }
            return (25 * tileSize - hoechster) / tileSize
        }

        let einfach = gipfel(abilities: [], zweiterSprung: true)
        let doppelt = gipfel(abilities: [.fluegelschlag], zweiterSprung: true)
        XCTAssertGreaterThan(doppelt, einfach + 1.5,
                             "Fluegelschlag muss deutlich hoeher tragen")
        XCTAssertGreaterThan(doppelt, 5.5)
    }

    func testOhneFluegelschlagKeinZweiterSprung() {
        let room = flatRoom(height: 30, floor: 25)
        let ohne = makePlayer(in: room, at: Vec2(10, 25))
        var hoechsterOhne = ohne.position.y
        var events: [GameEvent] = []
        var t = 0.0
        while t < 1.2 {
            let second = t >= 0.30 && t < 0.32
            ohne.update(dt: 1.0 / 60.0,
                        input: PlayerInput(jumpHeld: true, jumpPressed: t < 0.001 || second),
                        room: room, events: &events)
            events.removeAll(keepingCapacity: true)
            hoechsterOhne = min(hoechsterOhne, ohne.position.y)
            t += 1.0 / 60.0
        }
        XCTAssertLessThan((25 * tileSize - hoechsterOhne) / tileSize, 4.5)
    }

    // MARK: - Einwegplattformen

    func testPlattformTraegtVonObenUndLaesstVonUntenDurch() {
        var rows = (0..<20).map { y -> String in
            y == 0 || y >= 15 ? String(repeating: "#", count: 30)
                              : "#" + String(repeating: ".", count: 28) + "#"
        }
        // Plattform auf Hoehe 10.
        var row = Array(rows[10])
        for x in 8..<16 { row[x] = "=" }
        rows[10] = String(row)
        let room = self.room(from: rows)

        // Von unten hindurch: der Sprung darf nicht abprallen.
        let hoch = makePlayer(in: room, at: Vec2(11, 15), abilities: [.fluegelschlag])
        simulate(hoch, in: room, seconds: 1.0) { t in
            PlayerInput(jumpHeld: true, jumpPressed: t < 0.001 || (t >= 0.25 && t < 0.27))
        }
        XCTAssertLessThanOrEqual(hoch.position.y, 10 * tileSize + 0.5,
                                 "Figur muss die Plattform von unten durchqueren")

        // Von oben: sie muss tragen.
        let drauf = makePlayer(in: room, at: Vec2(11, 6))
        simulate(drauf, in: room, seconds: 2.0) { _ in .neutral }
        XCTAssertEqual(drauf.position.y, 10 * tileSize, accuracy: 0.1,
                       "Plattform muss von oben tragen")
    }

    // MARK: - Wand

    func testKlangschrittHaeltAnDerWand() {
        var rows = (0..<24).map { y -> String in
            y == 0 || y >= 20 ? String(repeating: "#", count: 24)
                              : "#" + String(repeating: ".", count: 22) + "#"
        }
        // Hohe Wand in der Mitte.
        for y in 4..<20 {
            var row = Array(rows[y])
            for x in 12..<15 { row[x] = "#" }
            rows[y] = String(row)
        }
        let room = self.room(from: rows)

        let mit = makePlayer(in: room, at: Vec2(10, 20), abilities: [.klangschritt])
        simulate(mit, in: room, seconds: 0.9) { t in
            PlayerInput(moveX: 1, jumpHeld: t < 0.3, jumpPressed: t < 0.001)
        }
        XCTAssertTrue(mit.isWallSliding || mit.wallSide != 0,
                      "Mit Klangschritt muss die Wand greifen")
        XCTAssertLessThanOrEqual(mit.velocity.y, Tuning.wallSlideSpeed + 1,
                                 "Am Hang darf die Figur nicht beschleunigen")
    }

    // MARK: - Herzschlag

    func testHerzschlagTraegtWeiterAlsEinSprung() {
        let room = flatRoom(width: 60, height: 20, floor: 15)

        func weite(abilities: Set<Ability>, dash: Bool) -> Double {
            let player = makePlayer(in: room, at: Vec2(5, 15), abilities: abilities)
            simulate(player, in: room, seconds: 1.6) { t in
                PlayerInput(moveX: 1, jumpHeld: t < 0.4, jumpPressed: t < 0.001,
                            dashPressed: dash && t >= 0.2 && t < 0.22)
            }
            return player.position.x - 5 * tileSize - tileSize / 2
        }

        let ohne = weite(abilities: [], dash: false)
        let mit = weite(abilities: [.herzschlag], dash: true)
        XCTAssertGreaterThan(mit, ohne + 25, "Der Herzschlag muss spuerbar weiter tragen")
    }

    func testDashMachtKurzUnverwundbar() {
        let room = flatRoom()
        let player = makePlayer(in: room, at: Vec2(10, 15), abilities: [.herzschlag])
        var events: [GameEvent] = []
        player.update(dt: 1.0 / 60.0, input: PlayerInput(moveX: 1, dashPressed: true),
                      room: room, events: &events)
        XCTAssertTrue(player.isDashing)
        let getroffen = player.takeDamage(1, from: Vec2(0, 0), events: &events)
        XCTAssertFalse(getroffen, "Waehrend des Herzschlags darf nichts treffen")
        XCTAssertEqual(player.health, player.health)
    }

    // MARK: - Schaden

    func testTrefferKostetLebenUndStoesstZurueck() {
        let room = flatRoom()
        let player = makePlayer(in: room, at: Vec2(10, 15))
        let vorher = player.health
        var events: [GameEvent] = []
        let getroffen = player.takeDamage(1, from: Vec2(10 * tileSize + 40, 15 * tileSize),
                                          events: &events)
        XCTAssertTrue(getroffen)
        XCTAssertEqual(player.health, vorher - 1)
        XCTAssertLessThan(player.velocity.x, 0, "Rueckstoss muss von der Quelle wegfuehren")
        XCTAssertLessThan(player.velocity.y, 0, "Treffer hebt die Figur leicht an")

        // Direkt danach greifen die Unverwundbarkeitsbilder.
        let nochmal = player.takeDamage(1, from: Vec2(0, 0), events: &events)
        XCTAssertFalse(nochmal)
        XCTAssertEqual(player.health, vorher - 1)
    }

    func testFigurBleibtImRaum() {
        let room = flatRoom(width: 30)
        let player = makePlayer(in: room, at: Vec2(15, 15), abilities: Set(Ability.allCases))
        simulate(player, in: room, seconds: 4.0) { t in
            PlayerInput(moveX: t < 2 ? -1 : 1, jumpHeld: true,
                        jumpPressed: Int(t * 60) % 20 == 0,
                        dashPressed: Int(t * 60) % 37 == 0)
        }
        XCTAssertGreaterThan(player.position.x, 0)
        XCTAssertLessThan(player.position.x, 30 * tileSize)
        XCTAssertLessThan(player.position.y, 20 * tileSize)
    }
}
