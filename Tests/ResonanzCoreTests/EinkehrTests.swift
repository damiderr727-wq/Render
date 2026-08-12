import XCTest
@testable import ResonanzCore

/// Die Einkehr an der Stimmgabel: aufloesen, schweben, zurueckfallen.
final class EinkehrTests: XCTestCase {

    func testSieBeginntAufgeloestUndWirdErstDannFlamme() {
        var e = Einkehr()
        XCTAssertEqual(e.zustand, .fort)
        e.beginne()
        if case .aufsteigen = e.zustand {} else { XCTFail("kein Aufstieg") }

        // Waehrend des Aufloesens darf noch nichts gewechselt werden.
        XCTAssertFalse(e.darfWechseln)
        e.tick(Einkehr.aufstieg * 0.5)
        XCTAssertFalse(e.darfWechseln)

        e.tick(Einkehr.aufstieg)
        XCTAssertEqual(e.zustand, .flamme)
        XCTAssertTrue(e.darfWechseln)
        XCTAssertEqual(e.flammenanteil, 1.0, accuracy: 0.001)
    }

    /// Der Sprung fuehrt heraus - aber erst, wenn sie ganz Flamme ist.
    /// Sonst faellt sie halb aufgeloest heraus.
    func testMittenImAufloesenLaesstSieSichNichtHerausspringen() {
        var e = Einkehr()
        e.beginne()
        e.tick(Einkehr.aufstieg * 0.4)
        e.verlasse()
        if case .aufsteigen = e.zustand {} else { XCTFail("Aufstieg abgebrochen") }
    }

    func testDerSprungFuehrtHerausUndDerVorgangEndet() {
        var e = Einkehr()
        e.beginne()
        e.tick(Einkehr.aufstieg + 0.01)
        e.verlasse()
        if case .aussteigen = e.zustand {} else { XCTFail("kein Abstieg") }
        XCTAssertFalse(e.darfWechseln, "Beim Herausfallen ist Schluss mit Wechseln")
        e.tick(Einkehr.abstieg + 0.01)
        XCTAssertEqual(e.zustand, .fort)
        XCTAssertEqual(e.flammenanteil, 0.0, accuracy: 0.001)
    }

    /// Hinein langsam, hinaus schnell.
    func testDerRueckwegIstKuerzerAlsDerHinweg() {
        XCTAssertLessThan(Einkehr.abstieg, Einkehr.aufstieg)
    }

    func testDerFlammenanteilLaeuftWeichUndBleibtImRahmen() {
        var e = Einkehr()
        e.beginne()
        var vorher = 0.0
        for _ in 0..<40 {
            e.tick(Einkehr.aufstieg / 30)
            let jetzt = e.flammenanteil
            XCTAssertGreaterThanOrEqual(jetzt, vorher - 0.0001, "faellt zwischendurch")
            XCTAssertLessThanOrEqual(jetzt, 1.0)
            vorher = jetzt
        }
        XCTAssertEqual(vorher, 1.0, accuracy: 0.001)
    }

    /// Raumwechsel und Tod brechen alles sofort ab.
    func testAbbrechenSetztAllesZurueck() {
        var e = Einkehr()
        e.beginne()
        e.tick(Einkehr.aufstieg + 0.01)
        e.abbrechen()
        XCTAssertEqual(e.zustand, .fort)
        XCTAssertFalse(e.aktiv)
    }
}
