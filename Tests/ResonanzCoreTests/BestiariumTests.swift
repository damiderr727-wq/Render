import XCTest
@testable import ResonanzCore

/// Das Bestiarium ist das Einzige im Spiel, das sich beim Spielen selbst
/// schreibt. Diese Tests halten drei Dinge fest: dass jede Kreatur einen
/// Eintrag hat, dass er sich nicht zu frueh oeffnet, und dass ein alter
/// Spielstand ihn nicht mitbringen muss.
final class BestiariumTests: XCTestCase {

    func testJedeKreaturHatEinenEintrag() {
        for art in EnemyKind.allCases {
            XCTAssertNotNil(Bestiarium.eintrag(fuer: art),
                            "Ohne Eintrag taucht \(art.rawValue) im Bestiarium nie auf")
        }
    }

    func testEintraegeBeginnenUnbekannt() {
        let save = SaveState()
        for art in EnemyKind.allCases {
            XCTAssertEqual(Bestiarium.stand(fuer: art, in: save), .unbekannt)
        }
        XCTAssertEqual(Bestiarium.verstanden(in: save), 0)
    }

    func testSehenReichtNichtZumVerstehen() {
        var save = SaveState()
        save.gesehen.insert(EnemyKind.gabelmaus.rawValue)
        XCTAssertEqual(Bestiarium.stand(fuer: .gabelmaus, in: save), .gesehen)
        XCTAssertEqual(Bestiarium.verstanden(in: save), 0)
    }

    func testDerEintragOeffnetSichGenauAnDerSchwelle() throws {
        let eintrag = try XCTUnwrap(Bestiarium.eintrag(fuer: .gabelmaus))
        var save = SaveState()

        save.erlegt[EnemyKind.gabelmaus.rawValue] = eintrag.schwelle - 1
        XCTAssertEqual(Bestiarium.stand(fuer: .gabelmaus, in: save), .gesehen,
                       "Eine unter der Schwelle ist noch nicht verstanden")

        save.erlegt[EnemyKind.gabelmaus.rawValue] = eintrag.schwelle
        XCTAssertEqual(Bestiarium.stand(fuer: .gabelmaus, in: save), .verstanden)
        XCTAssertEqual(Bestiarium.verstanden(in: save), 1)
    }

    /// Die Zahlen im Eintrag muessen die des Spiels sein - sonst steht im
    /// Bestiarium etwas anderes als in der Welt.
    func testZahlenKommenAusDemSpiel() throws {
        let eintrag = try XCTUnwrap(Bestiarium.eintrag(fuer: .stilleschreiter))
        XCTAssertEqual(eintrag.maxHealth, EnemyKind.stilleschreiter.maxHealth)
        XCTAssertEqual(eintrag.contactDamage, EnemyKind.stilleschreiter.contactDamage)
        // Anderthalb Kristalle - der einzige krumme Wert im Spiel.
        XCTAssertEqual(eintrag.schadenText, "1,5 Kristall")
    }

    /// Ein Spielstand von vor dem Bestiarium darf nicht am Laden scheitern.
    ///
    /// Der alte Stand wird nicht von Hand geschrieben, sondern aus einem
    /// echten erzeugt, dem die neuen Felder wieder entfernt werden. Von
    /// Hand geschrieben trifft man die Form der eingebetteten Typen nie
    /// genau - der erste Versuch scheiterte prompt an einem Feld, das
    /// mit dem Bestiarium gar nichts zu tun hat.
    func testAlterSpielstandLaedtOhneBestiarium() throws {
        var frisch = SaveState(roomID: "A2", spawnName: "L")
        frisch.erlegt = ["gabelmaus": 9]
        frisch.gesehen = ["gabelmaus"]

        var roh = try XCTUnwrap(try JSONSerialization.jsonObject(
            with: JSONEncoder().encode(frisch)) as? [String: Any])
        roh.removeValue(forKey: "erlegt")
        roh.removeValue(forKey: "gesehen")

        let alt = try JSONSerialization.data(withJSONObject: roh)
        let save = try JSONDecoder().decode(SaveState.self, from: alt)

        XCTAssertEqual(save.roomID, "A2")
        XCTAssertTrue(save.erlegt.isEmpty, "Fehlende Felder werden nachgesehen")
        XCTAssertTrue(save.gesehen.isEmpty)
    }
}
