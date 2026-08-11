import XCTest
@testable import ResonanzCore

/// Leben zaehlt in halben Kristallen. Ein voller Kristall sind zwei
/// Haelften, und mancher Schlag nimmt anderthalb - drei.
final class HealthTests: XCTestCase {

    private func spiel() throws -> GameSimulation {
        try GameSimulation.newGame(catalog: try WorldCatalog())
    }

    func testFuenfKristalleSindZehnHaelften() throws {
        let sim = try spiel()
        XCTAssertEqual(sim.save.progression.crystals, 5)
        XCTAssertEqual(sim.player.maxHealth, 10)
        XCTAssertEqual(sim.player.health, 10)
        XCTAssertEqual(sim.player.crystalsFull, 5)
        XCTAssertFalse(sim.player.hasHalfCrystal)
    }

    func testAnderthalbSchadenLaesstEinenHalbenKristallStehen() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.player.takeDamage(3, from: Vec2(0, 0), events: &events)

        XCTAssertEqual(sim.player.health, 7, "Zehn minus drei Haelften")
        XCTAssertEqual(sim.player.crystalsFull, 3)
        XCTAssertTrue(sim.player.hasHalfCrystal, "Ein halber haengt noch dran")
    }

    /// Auf einem halben Kristall ueberlebt sie keinen Treffer mehr - egal
    /// wie klein er ist.
    func testAufEinemHalbenKristallUeberlebtSieNichts() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.player.takeDamage(9, from: Vec2(0, 0), events: &events)
        XCTAssertEqual(sim.player.health, 1)
        XCTAssertFalse(sim.player.isDead)

        // Der naechste Treffer, auch der kleinstmoegliche, ist der letzte.
        sim.player.dropInvulnerability()
        events.removeAll()
        sim.player.takeDamage(1, from: Vec2(0, 0), events: &events)
        XCTAssertTrue(sim.player.isDead)
        XCTAssertEqual(sim.player.health, 0)
    }

    func testDornenNehmenEinenGanzenKristall() throws {
        XCTAssertEqual(Tuning.spikeDamage, 2)
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.player.takeDamage(Tuning.spikeDamage, from: Vec2(0, 0), events: &events)
        XCTAssertEqual(sim.player.crystalsFull, 4)
        XCTAssertFalse(sim.player.hasHalfCrystal)
    }

    func testDerKantorNimmtAnderthalb() {
        // Der Grundwert der Bossangriffe steht in halben Kristallen.
        let hazard = BossHazard(rect: Rect(x: 0, y: 0, width: 10, height: 10),
                                warmup: 0.2, active: 0.2, kind: "test")
        XCTAssertEqual(hazard.damage, 3)
    }

    func testKreaturenNehmenGanzeUndHalbeKristalle() {
        XCTAssertEqual(EnemyKind.klangmotte.contactDamage, 2, "Ein ganzer Kristall")
        XCTAssertEqual(EnemyKind.stilleschreiter.contactDamage, 3, "Anderthalb")
        for kind in EnemyKind.allCases {
            XCTAssertGreaterThanOrEqual(kind.contactDamage, 1)
            XCTAssertLessThanOrEqual(kind.contactDamage, 4)
        }
    }

    /// Der Zusammenhalt der Fassung rechnet auf Haelften, nicht auf ganze
    /// Kristalle - sonst waere jede Verschiebung gleich ein ganzes Herz.
    func testZusammenhaltRechnetInHaelften() {
        let mantel = Stats(equipment: EquipmentCatalog.mantel)
        let riss = Stats(equipment: EquipmentCatalog.gerissenesGewand)   // 0.6
        let schlag = Stats(equipment: EquipmentCatalog.schlagfassung)    // 1.2

        XCTAssertEqual(mantel.maxHealth(crystals: 5), 10)
        XCTAssertEqual(riss.maxHealth(crystals: 5), 6, "Drei Kristalle")
        XCTAssertEqual(schlag.maxHealth(crystals: 5), 12, "Sechs Kristalle")
    }

    func testHeilenAnDerStimmgabelFuelltAlleKristalle() throws {
        let sim = try spiel()
        var events: [GameEvent] = []
        sim.player.takeDamage(5, from: Vec2(0, 0), events: &events)
        XCTAssertEqual(sim.player.health, 5)
        sim.player.restore()
        XCTAssertEqual(sim.player.health, sim.player.maxHealth)
    }
}
