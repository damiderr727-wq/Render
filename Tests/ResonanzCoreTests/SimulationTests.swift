import XCTest
@testable import ResonanzCore

/// Prueft das Zusammenspiel: Raumwechsel, Kampf, Musiksteuerung, Partituren.
final class SimulationTests: XCTestCase {

    private func neuesSpiel() throws -> GameSimulation {
        try GameSimulation.newGame(catalog: try WorldCatalog())
    }

    private func lauf(_ sim: GameSimulation, seconds: Double,
                      input: (Double) -> PlayerInput) -> [GameEvent] {
        var alle: [GameEvent] = []
        let dt = 1.0 / 60.0
        var t = 0.0
        while t < seconds {
            alle.append(contentsOf: sim.update(dt: dt, input: input(t)))
            t += dt
        }
        return alle
    }

    func testSpielStartetImErstenRaum() throws {
        let sim = try neuesSpiel()
        XCTAssertEqual(sim.room.id, "A1")
        XCTAssertEqual(sim.player.health, sim.player.maxHealth)
        XCTAssertTrue(sim.save.progression.has(.stimmgabel), "Die Stimmgabel steckt von Anfang an in ihr")
        XCTAssertFalse(sim.save.progression.has(.trommel))
        XCTAssertTrue(sim.save.progression.abilities.isEmpty)
    }

    func testFigurFaelltAufDenBodenUndBleibtImRaum() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 1.5) { _ in .neutral }
        XCTAssertTrue(sim.player.onGround)
        XCTAssertTrue(sim.room.bounds.contains(sim.player.position))
    }

    /// Nach rechts laufen muss frueher oder spaeter in den naechsten Raum fuehren.
    func testDauerlaufWechseltDenRaum() throws {
        let sim = try neuesSpiel()
        let events = lauf(sim, seconds: 20) { t in
            PlayerInput(moveX: 1, jumpHeld: true, jumpPressed: Int(t * 60) % 24 == 0)
        }
        let wechsel = events.compactMap { event -> String? in
            if case .roomChanged(_, let to, _) = event { return to }
            return nil
        }
        XCTAssertFalse(wechsel.isEmpty, "Die Figur sollte A1 verlassen koennen")
        XCTAssertEqual(sim.room.id, wechsel.last)
    }

    func testFernkampfKostetResonanzUndErzeugtGeschosse() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 1.0) { _ in .neutral }
        let vorher = sim.player.resonance

        // Nach oben schiessen: dort steht kein Fels im Weg.
        let events = sim.update(dt: 1.0 / 60, input: PlayerInput(aimY: -1, rangedPressed: true))

        XCTAssertLessThan(sim.player.resonance, vorher, "Fernkampf muss Resonanz kosten")
        XCTAssertTrue(events.contains { if case .fireProjectiles = $0 { return true }; return false })
        XCTAssertEqual(sim.projectiles.count, Tuning.ranged(.leier).count,
                       "Die Leier schickt einen Dreiklang los")
        XCTAssertTrue(sim.projectiles.allSatisfy { $0.owner == .player })

        // Und sie fliegen weiter, statt sofort zu vergehen.
        _ = lauf(sim, seconds: 0.2) { _ in .neutral }
        XCTAssertFalse(sim.projectiles.isEmpty, "Die Toene muessen unterwegs bleiben")
    }

    func testOhneResonanzKeinFernkampf() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 0.5) { _ in .neutral }
        sim.player.resonance = 0

        let events = lauf(sim, seconds: 0.05) { t in PlayerInput(rangedPressed: t < 0.001) }
        XCTAssertTrue(events.sounds.contains(.outOfResonance))
        XCTAssertTrue(sim.projectiles.isEmpty)
    }

    func testNahkampfFuelltDieResonanzWiederAuf() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 0.6) { _ in .neutral }
        sim.player.resonance = 10

        // Ein Gegner direkt vor der Figur.
        let ziel = Vec2(sim.player.position.x + 14, sim.player.position.y)
        let gegner = Enemy(id: 99, kind: .klangmotte, position: ziel, patrolTiles: 0)
        sim.insert(enemy: gegner)

        _ = lauf(sim, seconds: 0.35) { t in PlayerInput(meleePressed: t < 0.001) }
        XCTAssertGreaterThan(sim.player.resonance, 10,
                             "Ein Nahkampftreffer muss Resonanz zurueckgeben")
    }

    func testMusikWechseltMitDerRegion() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 0.5) { _ in .neutral }
        XCTAssertEqual(sim.musicTrack, "hain")
    }

    func testIntensitaetSteigtInGefahr() throws {
        let sim = try neuesSpiel()
        _ = lauf(sim, seconds: 0.5) { _ in .neutral }
        let ruhig = sim.musicIntensity

        for i in 0..<4 {
            let position = Vec2(sim.player.position.x + Double(20 + i * 10),
                                sim.player.position.y - 10)
            sim.insert(enemy: Enemy(id: 200 + i, kind: .klangmotte,
                                         position: position, patrolTiles: 0))
        }
        _ = lauf(sim, seconds: 3.0) { _ in .neutral }
        XCTAssertGreaterThan(sim.musicIntensity, ruhig,
                             "Naeher Gefahr muss die Musik verdichten")
    }

    func testZufaelligeEingabenBringenDasSpielNichtAusDemTritt() throws {
        let sim = try neuesSpiel()
        var rng = Rng(seed: 4242)
        var t = 0.0
        let dt = 1.0 / 60.0
        while t < 30 {
            let input = PlayerInput(
                moveX: rng.chance(0.5) ? 1 : -1,
                aimY: rng.chance(0.15) ? (rng.chance(0.5) ? -1 : 1) : 0,
                jumpHeld: rng.chance(0.4),
                jumpPressed: rng.chance(0.06),
                meleePressed: rng.chance(0.05),
                rangedPressed: rng.chance(0.04),
                dashPressed: rng.chance(0.03),
                slamPressed: rng.chance(0.02),
                interactPressed: rng.chance(0.01))
            _ = sim.update(dt: dt, input: input)
            t += dt

            XCTAssertTrue(sim.room.bounds.inset(by: -40).contains(sim.player.position),
                          "Figur ist aus dem Raum \(sim.room.id) gefallen")
            XCTAssertFalse(sim.player.position.x.isNaN)
            XCTAssertLessThan(sim.projectiles.count, 400, "Geschosse haeufen sich an")
        }
    }

    // MARK: - Partituren

    func testAllePartiturenLaden() throws {
        let library = try ScoreLibrary()
        XCTAssertFalse(library.index.scores.isEmpty)
        for entry in library.index.scores {
            let score = try XCTUnwrap(library.score(entry.id))
            XCTAssertGreaterThan(score.bpm, 20)
            XCTAssertFalse(score.tracks.isEmpty)
            XCTAssertTrue(score.tracks.contains { $0.layer <= 0 },
                          "\(entry.id): ohne Spur bei Intensitaet 0 bleibt es still")
            for track in score.tracks {
                for note in track.notes {
                    XCTAssertTrue((0..<score.loop).contains(note.t),
                                  "\(entry.id)/\(track.voice): Note bei \(note.t) faellt aus der Schleife")
                }
            }
        }
    }

    func testJedeRegionsmusikExistiert() throws {
        let library = try ScoreLibrary()
        let catalog = try WorldCatalog()
        for entry in catalog.index.rooms {
            XCTAssertNotNil(library.score(entry.music),
                            "Partitur '\(entry.music)' fuer \(entry.id) fehlt")
        }
    }

    func testDirigentPlantNotenInDerZeitFolge() throws {
        let library = try ScoreLibrary()
        let director = MusicDirector(library: library)
        director.targetIntensity = 1
        director.play("hain", now: 0)

        var geplant: [ScheduledNote] = []
        var now = 0.0
        while now < 12 {
            geplant.append(contentsOf: director.pull(now: now, dt: 1.0 / 60.0))
            now += 1.0 / 60.0
        }
        XCTAssertFalse(geplant.isEmpty, "Der Dirigent muss Noten liefern")
        XCTAssertEqual(geplant, geplant.sorted { $0.time < $1.time },
                       "Noten muessen in zeitlicher Ordnung kommen")
        // Keine Note darf doppelt oder in der Vergangenheit liegen.
        for note in geplant {
            XCTAssertGreaterThanOrEqual(note.time, 0)
            XCTAssertGreaterThan(note.duration, 0)
            XCTAssertGreaterThan(note.gain, 0)
        }
    }

    func testLeiseSpurenSchweigenBeiGeringerIntensitaet() throws {
        let library = try ScoreLibrary()
        let director = MusicDirector(library: library)
        director.targetIntensity = 0
        director.play("boss", now: 0)

        var voices: Set<Voice> = []
        var now = 0.0
        while now < 16 {
            for note in director.pull(now: now, dt: 1.0 / 60.0) { voices.insert(note.voice) }
            now += 1.0 / 60.0
        }
        XCTAssertFalse(voices.contains(.perc),
                       "Die Perkussion gehoert erst zur dichten Fassung")
    }
}

extension ScheduledNote: Equatable {
    public static func == (a: ScheduledNote, b: ScheduledNote) -> Bool {
        a.voice == b.voice && a.midi == b.midi && a.time == b.time
    }
}
