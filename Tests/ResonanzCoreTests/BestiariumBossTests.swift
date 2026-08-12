import XCTest
@testable import ResonanzCore

/// Ein Boss gehoert ins Bestiarium, aber nicht nach derselben Regel wie
/// eine Kreatur. Diese Tests halten den Unterschied fest.
final class BestiariumBossTests: XCTestCase {

    func testEinBossIstUnbekanntBevorManIhmBegegnet() {
        let save = SaveState()
        XCTAssertEqual(Bestiarium.stand(fuer: Boss.Art.auftakt, in: save), .unbekannt)
    }

    /// Den Raum betreten reicht - ausweichen kann man ihm nicht.
    func testWerDenRaumBetrittHatIhnGesehen() {
        var save = SaveState()
        save.gesehen.insert("boss_auftakt")
        XCTAssertEqual(Bestiarium.stand(fuer: Boss.Art.auftakt, in: save), .gesehen)
    }

    /// Und *ein* gewonnener Kampf deckt den ganzen Eintrag auf. Bei einer
    /// Kreatur braucht das drei bis fuenf Begegnungen; einem Boss begegnet
    /// man einmal, und dieselbe Regel wuerde seinen Eintrag nie aufgehen
    /// lassen.
    func testEinGewonnenerKampfReichtZumVerstehen() {
        var save = SaveState()
        save.gesehen.insert("boss_auftakt")
        save.erlegt["boss_auftakt"] = 1
        XCTAssertEqual(Bestiarium.stand(fuer: Boss.Art.auftakt, in: save), .verstanden)
    }

    /// Der Schluessel des Bosses darf nicht mit einer gleichnamigen
    /// Kreatur kollidieren - beide leben im selben Woerterbuch.
    func testBossUndKreaturTeilenSichKeinenSchluessel() {
        var save = SaveState()
        save.erlegt["boss_auftakt"] = 1
        XCTAssertEqual(save.erlegt["auftakt"] ?? 0, 0)
        XCTAssertEqual(Bestiarium.stand(fuer: Boss.Art.auftakt, in: save), .verstanden)
    }

    func testZuJedemBossGibtEsEinenEintrag() {
        for art in [Boss.Art.auftakt, .kantor] {
            let eintrag = Bestiarium.grosser(fuer: art)
            XCTAssertNotNil(eintrag, "kein Eintrag fuer \(art.rawValue)")
            XCTAssertFalse(eintrag?.verhalten.isEmpty ?? true)
            XCTAssertFalse(eintrag?.deutung.isEmpty ?? true)
            XCTAssertEqual(eintrag?.maxHealth, art.health,
                           "Die Zahlen muessen aus dem Boss selbst kommen")
        }
    }
}
