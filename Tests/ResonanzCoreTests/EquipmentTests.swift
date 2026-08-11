import XCTest
@testable import ResonanzCore

/// Prueft die Fassungen: der Mantel darf nichts verschieben, jede andere
/// Fassung muss ihren Preis wirklich kosten - und die Werte muessen bis in
/// die Physik durchschlagen, nicht nur in der Tabelle stehen.
final class EquipmentTests: XCTestCase {

    /// Ein Spielstand, der die genannte Fassung besitzt und traegt.
    private func stand(_ equipmentID: String,
                       worn: Bool = true) -> SaveState {
        var save = SaveState()
        save.progression.equipmentOwned.insert(equipmentID)
        if worn { save.progression.equipmentWorn = equipmentID }
        return save
    }

    /// Wie weit ein Ton fliegt, bevor er vergeht.
    private func reichweite(_ stats: Stats, _ instrument: Instrument = .leier) -> Double {
        let p = stats.ranged(instrument)
        return p.speed * p.lifetime
    }

    // MARK: - Der Mantel

    func testDerMantelVerschiebtNichts() {
        let stats = Stats(equipment: EquipmentCatalog.mantel)
        XCTAssertEqual(stats.runSpeed, Tuning.runSpeed, accuracy: 0.0001)
        XCTAssertEqual(stats.jumpVelocity, Tuning.jumpVelocity, accuracy: 0.0001)
        XCTAssertEqual(stats.dashSpeed, Tuning.dashSpeed, accuracy: 0.0001)
        XCTAssertEqual(stats.resonanceRegen, Tuning.resonanceRegen, accuracy: 0.0001)
        XCTAssertEqual(stats.maxHealth(base: 5), 5)
        for instrument in Instrument.allCases {
            XCTAssertEqual(stats.melee(instrument).reach,
                           Tuning.melee(instrument).reach, accuracy: 0.0001)
            XCTAssertEqual(stats.melee(instrument).damage,
                           Tuning.melee(instrument).damage)
            XCTAssertEqual(stats.ranged(instrument).damage,
                           Tuning.ranged(instrument).damage)
            XCTAssertEqual(reichweite(stats, instrument),
                           Tuning.ranged(instrument).speed * Tuning.ranged(instrument).lifetime,
                           accuracy: 0.0001)
        }
    }

    func testOhneGueltigeFassungTraegtSieDenMantel() {
        var progression = Progression()
        XCTAssertEqual(progression.equipment.id, EquipmentCatalog.mantel.id)
        progression.equipmentWorn = "gibt_es_nicht"
        XCTAssertEqual(progression.equipment.id, EquipmentCatalog.mantel.id,
                       "Ganz ohne Gefaess wuerde sie sich aufloesen")
    }

    // MARK: - Druck und Oeffnungen

    /// Eine Oeffnung: der ganze Druck geht nach vorn.
    func testEngeFassungTraegtWeitUndSchlaegtKurz() {
        let mantel = Stats(equipment: EquipmentCatalog.mantel)
        let eng = Stats(equipment: EquipmentCatalog.engeFassung)

        XCTAssertGreaterThan(reichweite(eng), reichweite(mantel) * 1.2)
        XCTAssertGreaterThan(eng.ranged(.leier).damage, mantel.ranged(.leier).damage)
        XCTAssertLessThan(eng.melee(.leier).reach, mantel.melee(.leier).reach)
        XCTAssertLessThan(eng.runSpeed, mantel.runSpeed)
        XCTAssertGreaterThan(eng.ranged(.leier).cost, mantel.ranged(.leier).cost)
    }

    /// Viele Oeffnungen: sie klingt ueberall, aber nirgends weit.
    func testOffeneFassungKehrtDasVerhaeltnisUm() {
        let mantel = Stats(equipment: EquipmentCatalog.mantel)
        let offen = Stats(equipment: EquipmentCatalog.offeneFassung)

        XCTAssertGreaterThan(offen.melee(.leier).reach, mantel.melee(.leier).reach)
        XCTAssertLessThan(reichweite(offen), reichweite(mantel))
        XCTAssertLessThan(offen.ranged(.leier).cost, mantel.ranged(.leier).cost)
        XCTAssertGreaterThan(offen.resonanceRegen, mantel.resonanceRegen)
    }

    func testSchlagfassungGibtWuchtUndNimmtSprunghoehe() {
        let mantel = Stats(equipment: EquipmentCatalog.mantel)
        let schlag = Stats(equipment: EquipmentCatalog.schlagfassung)

        XCTAssertGreaterThan(schlag.slamRadius, mantel.slamRadius)
        XCTAssertGreaterThan(schlag.slamDamage, mantel.slamDamage)
        XCTAssertGreaterThan(schlag.melee(.trommel).knockback, mantel.melee(.trommel).knockback)
        // Nach oben faellt der Sprung kuerzer aus - jumpVelocity ist negativ.
        XCTAssertGreaterThan(schlag.jumpVelocity, mantel.jumpVelocity)
    }

    func testGerissenesGewandIstSchnellUndZerbrechlich() {
        let mantel = Stats(equipment: EquipmentCatalog.mantel)
        let riss = Stats(equipment: EquipmentCatalog.gerissenesGewand)

        XCTAssertGreaterThan(riss.runSpeed, mantel.runSpeed)
        XCTAssertGreaterThan(riss.dashSpeed, mantel.dashSpeed)
        XCTAssertLessThan(riss.maxHealth(base: 5), mantel.maxHealth(base: 5))
        XCTAssertGreaterThanOrEqual(riss.maxHealth(base: 5), 1)
    }

    /// Keine Fassung darf einen Wert auf null oder ins Negative ziehen.
    func testJedeFassungBleibtSpielbar() {
        for equipment in EquipmentCatalog.all {
            let stats = Stats(equipment: equipment)
            XCTAssertGreaterThan(equipment.openings, 0, "\(equipment.id) klingt sonst gar nicht")
            XCTAssertGreaterThan(stats.runSpeed, 0, equipment.id)
            XCTAssertLessThan(stats.jumpVelocity, 0, equipment.id)
            XCTAssertGreaterThanOrEqual(stats.maxHealth(base: 5), 1, equipment.id)
            for instrument in Instrument.allCases {
                let melee = stats.melee(instrument)
                let ranged = stats.ranged(instrument)
                XCTAssertGreaterThan(melee.reach, 0, equipment.id)
                XCTAssertGreaterThanOrEqual(melee.damage, 1, equipment.id)
                XCTAssertGreaterThan(ranged.speed, 0, equipment.id)
                XCTAssertGreaterThan(ranged.lifetime, 0, equipment.id)
                XCTAssertGreaterThanOrEqual(ranged.damage, 1, equipment.id)
                XCTAssertGreaterThan(ranged.cost, 0, equipment.id)
            }
        }
    }

    // MARK: - Die Fassung wirkt bis in die Physik

    func testDieFassungAendertDenLauf() throws {
        let catalog = try WorldCatalog()

        func weite(_ equipmentID: String) throws -> Double {
            let sim = try GameSimulation(catalog: catalog, save: stand(equipmentID))
            _ = sim.update(dt: 1.0 / 60, input: .neutral)
            let start = sim.player.position.x
            for _ in 0..<60 {
                _ = sim.update(dt: 1.0 / 60, input: PlayerInput(moveX: 1))
            }
            return sim.player.position.x - start
        }

        let mitMantel = try weite(EquipmentCatalog.mantel.id)
        let mitRiss = try weite(EquipmentCatalog.gerissenesGewand.id)
        let mitEnge = try weite(EquipmentCatalog.engeFassung.id)

        XCTAssertGreaterThan(mitRiss, mitMantel * 1.1, "Das gerissene Gewand laeuft schneller")
        XCTAssertLessThan(mitEnge, mitMantel * 0.95, "Die enge Fassung ist traege")
    }

    func testDerZusammenhaltBestimmtDieLebenspunkte() throws {
        let catalog = try WorldCatalog()
        let mitMantel = try GameSimulation.newGame(catalog: catalog)
        let mitRiss = try GameSimulation(
            catalog: catalog, save: stand(EquipmentCatalog.gerissenesGewand.id))

        XCTAssertLessThan(mitRiss.player.maxHealth, mitMantel.player.maxHealth)
        XCTAssertGreaterThanOrEqual(mitRiss.player.maxHealth, 1)
        XCTAssertEqual(mitRiss.player.health, mitRiss.player.maxHealth,
                       "Sie startet nicht angeschlagen, nur zerbrechlicher")
    }

    // MARK: - Umziehen

    func testUmziehenNurAnDerStimmgabel() throws {
        let sim = try GameSimulation(
            catalog: try WorldCatalog(),
            save: stand(EquipmentCatalog.engeFassung.id, worn: false))
        _ = sim.update(dt: 1.0 / 60, input: .neutral)

        XCTAssertFalse(sim.wear(EquipmentCatalog.engeFassung.id),
                       "Mitten im Raum ist das kein Kleiderwechsel, sondern ein Umbau")
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.mantel.id)

        sim.player.beginRest()
        XCTAssertTrue(sim.wear(EquipmentCatalog.engeFassung.id))
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.engeFassung.id)
        XCTAssertEqual(sim.player.stats.equipment.id, EquipmentCatalog.engeFassung.id)
    }

    func testWasManNichtHatKannManNichtTragen() throws {
        let sim = try GameSimulation.newGame(catalog: try WorldCatalog())
        sim.player.beginRest()
        XCTAssertFalse(sim.wear(EquipmentCatalog.schlagfassung.id))
        XCTAssertFalse(sim.wear("gibt_es_nicht"))
        XCTAssertEqual(sim.save.progression.equipmentWorn, EquipmentCatalog.mantel.id)
    }

    // MARK: - In der Welt

    func testJedeFassungLiegtGenauEinmalInDerWelt() throws {
        let catalog = try WorldCatalog()
        var gefunden: [String: Int] = [:]
        for room in try catalog.loadAll() {
            for pickup in room.data.pickups where pickup.kind == "equipment" {
                XCTAssertNotNil(EquipmentCatalog.find(pickup.id),
                                "\(room.id): unbekannte Fassung \(pickup.id)")
                gefunden[pickup.id, default: 0] += 1
            }
        }
        for equipment in EquipmentCatalog.all where equipment.id != EquipmentCatalog.mantel.id {
            XCTAssertEqual(gefunden[equipment.id], 1,
                           "\(equipment.id) muss genau einmal in der Welt liegen")
        }
        XCTAssertNil(gefunden[EquipmentCatalog.mantel.id],
                     "Den Mantel traegt sie von Anfang an")
    }
}
