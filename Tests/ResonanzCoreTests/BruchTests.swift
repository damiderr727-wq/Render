import XCTest
@testable import ResonanzCore

/// Der Bruch: das feste Ereignis am Ende. Sie faehrt aus ihrer Fassung,
/// der Kern zerspringt, und was bleibt, ist schneller und haerter - aber
/// es haelt sie nichts mehr zusammen.
final class BruchTests: XCTestCase {

    private func spiel() throws -> GameSimulation {
        try GameSimulation.newGame(catalog: try WorldCatalog())
    }

    private func lauf(_ sim: GameSimulation, seconds: Double) {
        let dt = 1.0 / 60.0
        var t = 0.0
        while t < seconds {
            _ = sim.update(dt: dt, input: .neutral)
            t += dt
        }
    }

    func testDerBruchMachtSieAggressiverInJederHinsicht() {
        let vorher = Stats(equipment: EquipmentCatalog.mantel, kern: .leier)
        let nachher = Stats(equipment: Bruch.entfesselt, kern: .leier, gebrochen: true)

        XCTAssertGreaterThan(nachher.runSpeed, vorher.runSpeed)
        XCTAssertGreaterThan(nachher.dashSpeed, vorher.dashSpeed)
        XCTAssertGreaterThan(nachher.melee.damage, vorher.melee.damage)
        XCTAssertGreaterThan(nachher.melee.reach, vorher.melee.reach)
        XCTAssertGreaterThan(nachher.ranged.damage, vorher.ranged.damage)
        XCTAssertLessThan(nachher.ranged.cost, vorher.ranged.cost)
        XCTAssertGreaterThan(nachher.resonanceRegen, vorher.resonanceRegen)
    }

    func testNachDemBruchTraegtSieNichtsMehr() throws {
        var save = SaveState()
        save.progression.equipmentOwned.insert(EquipmentCatalog.engeFassung.id)
        let sim = try GameSimulation(catalog: try WorldCatalog(), save: save)
        var events: [GameEvent] = []

        XCTAssertTrue(sim.brich(events: &events))
        XCTAssertTrue(sim.save.progression.gebrochen)
        XCTAssertEqual(sim.save.progression.equipment.id, Bruch.entfesselt.id)

        // Es gibt kein Zurueck in die Fassung.
        sim.player.beginRest()
        XCTAssertFalse(sim.wear(EquipmentCatalog.engeFassung.id))
        XCTAssertFalse(sim.wear(EquipmentCatalog.mantel.id))
        XCTAssertEqual(sim.player.stats.equipment.id, Bruch.entfesselt.id)
    }

    func testDerBruchGeschiehtNurEinmal() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        XCTAssertTrue(sim.brich(events: &events))
        XCTAssertFalse(sim.brich(events: &events), "Ein zweites Mal gibt es nicht")
    }

    /// Ohne Gefaess zerstreut sie sich - der Bruch ist ein Wettlauf.
    func testImBruchZiehtEsIhrDasLeben() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.brich(events: &events)
        let start = sim.player.health
        lauf(sim, seconds: 4.0)
        XCTAssertLessThan(sim.player.health, start, "Sie verliert dauernd Leben")
    }

    /// Er soll draengen, nicht toeten: der letzte halbe Kristall bleibt.
    func testDerZerfallToetetSieNicht() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.brich(events: &events)
        lauf(sim, seconds: 90.0)
        XCTAssertEqual(sim.player.health, Bruch.untergrenze)
        XCTAssertFalse(sim.player.isDead, "Sterben soll sie an der Dissonanz, nicht an der Uhr")
    }

    func testOhneBruchZerfaelltNichts() throws {
        let sim = try spiel()
        let start = sim.player.health
        lauf(sim, seconds: 4.0)
        XCTAssertEqual(sim.player.health, start)
    }

    func testZumBruchGibtEsBilder() throws {
        struct Sheet: Decodable { let frames: [String: [String: Double]] }
        let sheet = try Resources.decode(Sheet.self, subdirectory: "Atlas", name: "characters")
        for zustand in ["idle", "run", "jump", "fall", "land", "dash",
                        "wall", "melee", "cast", "hurt", "rest"] {
            XCTAssertNotNil(sheet.frames["cadence_bruch_bruch_\(zustand)_0"],
                            "Es fehlt das Bild fuer den Bruch: \(zustand)")
        }
    }

    /// Das Ereignis haengt an der Geschichte, nicht am Zufall: es faellt,
    /// wenn der Kantor in den letzten Satz geht.
    func testDerBruchIstKeinFundstueck() throws {
        let catalog = try WorldCatalog()
        for room in try catalog.loadAll() {
            for pickup in room.data.pickups {
                XCTAssertNotEqual(pickup.id, Bruch.entfesselt.id,
                                  "\(room.id): der Bruch darf nicht herumliegen")
            }
        }
        XCTAssertNil(EquipmentCatalog.find(Bruch.entfesselt.id),
                     "Er steht nicht im Katalog - man kann ihn nicht anlegen")
    }
}
