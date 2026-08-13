import XCTest
@testable import ResonanzCore

/// Das Dorf: was es kostet, was es gibt - und was es *nicht* gibt.
final class LadenTests: XCTestCase {

    func testOhneStimmenGibtEsNichts() {
        var save = SaveState()
        let ware = Laden.waren[0]
        XCTAssertFalse(Laden.kaufbar(ware, in: save))
        XCTAssertFalse(Laden.kaufe(ware, save: &save))
        XCTAssertTrue(save.gekauft.isEmpty)
    }

    func testKaufenZiehtAbUndLiefert() {
        var save = SaveState()
        let ware = Laden.waren[0]
        save.stimmen = ware.preis + 7
        XCTAssertTrue(Laden.kaufe(ware, save: &save))
        XCTAssertEqual(save.stimmen, 7)
        XCTAssertTrue(save.gekauft.contains(ware.id))
        if case .siegel(let id) = ware.inhalt {
            XCTAssertTrue(save.progression.siegelOwned.contains(id))
        }
    }

    /// Jede Ware liegt genau einmal da - auch wenn man wiederkommt.
    func testZweimalKaufenGehtNicht() {
        var save = SaveState()
        let ware = Laden.waren[0]
        save.stimmen = ware.preis * 3
        XCTAssertTrue(Laden.kaufe(ware, save: &save))
        let rest = save.stimmen
        XCTAssertFalse(Laden.kaufe(ware, save: &save))
        XCTAssertEqual(save.stimmen, rest, "beim zweiten Mal darf nichts abgehen")
    }

    /// Kerne gibt es hier nicht. Ein Kern ist das, womit sie klingt - den
    /// findet man, oder man findet ihn nicht.
    func testKerneStehenNichtImLaden() {
        for ware in Laden.waren {
            switch ware.inhalt {
            case .siegel, .equipment: break
            }
        }
        // Und keine Ware traegt den Namen eines Kerns.
        let kernNamen = Set(Kern.allCases.map { $0.rawValue })
        for ware in Laden.waren {
            XCTAssertFalse(kernNamen.contains(ware.id))
        }
    }

    /// Was im Laden liegt, liegt sonst nirgends: sonst ist der Laden eine
    /// Strafgebuehr fuer schlechtes Suchen.
    func testLadenwareLiegtNichtInDerWelt() throws {
        let catalog = try WorldCatalog()
        var inDerWelt: Set<String> = []
        for room in try catalog.loadAll() {
            for p in room.data.pickups { inDerWelt.insert(p.id) }
        }
        for ware in Laden.waren {
            switch ware.inhalt {
            case .siegel(let id), .equipment(let id):
                XCTAssertFalse(inDerWelt.contains(id),
                               "\(id) liegt sowohl im Laden als auch in der Welt")
            }
        }
    }

    /// Die Preise steigen in Stufen: die erste Ware nach dem ersten
    /// Gebiet, die letzte erst nach einer Weile.
    func testDiePreiseSteigen() {
        let preise = Laden.waren.map { $0.preis }
        XCTAssertEqual(preise, preise.sorted())
        XCTAssertGreaterThan(preise.last ?? 0, (preise.first ?? 0) * 2)
    }

    func testJedeWareGibtEsWirklich() {
        for ware in Laden.waren {
            switch ware.inhalt {
            case .siegel(let id):
                XCTAssertNotNil(SiegelKatalog.find(id), "Siegel \(id) fehlt")
            case .equipment(let id):
                XCTAssertNotNil(EquipmentCatalog.find(id), "Fassung \(id) fehlt")
            }
        }
    }
}
