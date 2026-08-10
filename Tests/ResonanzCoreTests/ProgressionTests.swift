import XCTest
@testable import ResonanzCore

/// Prueft, dass die Welt tatsaechlich durchspielbar ist - mit der echten
/// Physik, nicht nach Augenmass.
final class ProgressionTests: XCTestCase {

    /// Ermittelt fuer jeden Raum, welches Koennen die Figur beim ersten
    /// Betreten hat, und in welcher Reihenfolge die Faehigkeiten fallen.
    private func fortschritt(_ catalog: WorldCatalog, rooms: [String: Room])
        -> (ankunft: [String: Set<Ability>], reihenfolge: [Ability], erreicht: Set<String>) {
        var abilities: Set<Ability> = []
        var ankunft: [String: Set<Ability>] = [:]
        var reihenfolge: [Ability] = []
        var erreicht: Set<String> = []

        while true {
            var frontier = [catalog.index.startRoom]
            var gesehen: Set<String> = [catalog.index.startRoom]
            while let id = frontier.popLast() {
                if ankunft[id] == nil { ankunft[id] = abilities }
                for door in rooms[id]?.data.doors ?? [] {
                    if let requirement = door.requires,
                       let ability = Ability(rawValue: requirement),
                       !abilities.contains(ability) { continue }
                    if gesehen.insert(door.target).inserted {
                        frontier.append(door.target)
                    }
                }
            }
            erreicht = gesehen

            var neu = false
            for id in gesehen.sorted() {
                for pickup in rooms[id]?.data.pickups ?? [] where pickup.kind == "ability" {
                    if let ability = Ability(rawValue: pickup.id), abilities.insert(ability).inserted {
                        reihenfolge.append(ability)
                        neu = true
                    }
                }
            }
            if !neu { break }
        }
        return (ankunft, reihenfolge, erreicht)
    }

    func testFaehigkeitenLiegenInEinerSpielbarenReihenfolge() throws {
        let catalog = try WorldCatalog()
        let rooms = Dictionary(uniqueKeysWithValues: try catalog.loadAll().map { ($0.id, $0) })
        let (_, reihenfolge, erreicht) = fortschritt(catalog, rooms: rooms)

        XCTAssertEqual(reihenfolge, [.fluegelschlag, .klangschritt, .herzschlag, .basston],
                       "Die Faehigkeiten muessen in dieser Reihenfolge zu holen sein")
        XCTAssertEqual(erreicht.count, catalog.roomIDs.count,
                       "Jeder Raum muss erreichbar sein: fehlt \(Set(catalog.roomIDs).subtracting(erreicht))")
    }

    func testBossraumIstErreichbar() throws {
        let catalog = try WorldCatalog()
        let rooms = Dictionary(uniqueKeysWithValues: try catalog.loadAll().map { ($0.id, $0) })
        let (_, _, erreicht) = fortschritt(catalog, rooms: rooms)
        let bossRaeume = rooms.values.filter { $0.data.boss != nil }.map(\.id)
        XCTAssertFalse(bossRaeume.isEmpty, "Die Welt braucht einen Boss")
        for id in bossRaeume {
            XCTAssertTrue(erreicht.contains(id), "Bossraum \(id) ist nicht erreichbar")
        }
    }

    /// Der wichtigste Test: simuliert die Spielphysik und prueft, ob die
    /// Figur mit dem Koennen, das sie zu diesem Zeitpunkt hat, wirklich
    /// alles im Raum erreicht.
    func testJederRaumIstMitDemVorhandenenKoennenBegehbar() throws {
        let catalog = try WorldCatalog()
        let rooms = Dictionary(uniqueKeysWithValues: try catalog.loadAll().map { ($0.id, $0) })
        let (ankunft, _, _) = fortschritt(catalog, rooms: rooms)

        for id in catalog.roomIDs {
            guard let room = rooms[id] else { continue }
            let koennen = ankunft[id] ?? []
            let progression = Progression(abilities: koennen,
                                          instruments: Set(Instrument.allCases))

            // Gesperrte Tueren zaehlen erst, wenn das Koennen dafuer da ist.
            let ziele = ReachabilityProbe.targets(for: room).filter { ziel in
                guard ziel.kind == .door,
                      let door = room.data.doors.first(where: {
                          ziel.name == "door:\($0.id)->\($0.target)"
                      }),
                      let requirement = door.requires,
                      let ability = Ability(rawValue: requirement)
                else { return true }
                return koennen.contains(ability)
            }

            let probe = ReachabilityProbe(room: room, progression: progression)
            let ergebnis = probe.run(from: ReachabilityProbe.origins(for: room), targets: ziele)

            XCTAssertTrue(ergebnis.ok,
                          "\(id) (\(room.name)): nicht erreichbar - "
                          + ergebnis.unreached.map(\.name).joined(separator: ", "))
        }
    }

    func testSpielstandUeberlebtEinenSpeicherdurchlauf() throws {
        var save = SaveState(roomID: "B4", spawnName: "L")
        save.progression.abilities = [.fluegelschlag, .klangschritt]
        save.progression.instruments = [.leier, .trommel]
        save.instrument = .trommel
        save.collected = ["A3/fluegelschlag", "A2/trommel"]
        save.brokenWalls = ["C3": [28, 14, 28, 15]]
        save.playTime = 1234.5

        let daten = try JSONEncoder().encode(save)
        let zurueck = try JSONDecoder().decode(SaveState.self, from: daten)
        XCTAssertEqual(save, zurueck)
    }

    func testInstrumentenreihenfolgeIstStabil() {
        var progression = Progression(instruments: [.floete, .leier])
        XCTAssertEqual(progression.orderedInstruments, [.leier, .floete])
        progression.instruments.insert(.trommel)
        XCTAssertEqual(progression.orderedInstruments, [.leier, .trommel, .floete])
    }
}
