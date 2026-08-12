import XCTest
@testable import ResonanzCore

/// Die Kampffunktion muss zwei Dinge zugleich sein: lohnend fuer den, der
/// sie trifft, und harmlos fuer den, der sie ignoriert. Diese Tests halten
/// beides fest.
final class KlangketteTests: XCTestCase {

    private let takt = Takt(bpm: 120)          // ein halber Schlag = 0,25 s

    func testDerTaktMisstZumNaechstenSchlag() {
        // Eine Spur zu frueh ist genauso im Takt wie eine Spur zu spaet.
        XCTAssertEqual(takt.abstandZumSchlag(0.0), 0, accuracy: 0.001)
        XCTAssertEqual(takt.abstandZumSchlag(0.05), 0.05, accuracy: 0.001)
        XCTAssertEqual(takt.abstandZumSchlag(0.45), 0.05, accuracy: 0.001)
        // Genau dazwischen ist der groesste Abstand.
        XCTAssertEqual(takt.abstandZumSchlag(0.25), 0.25, accuracy: 0.001)
    }

    func testImTaktWaechstDieKette() {
        var kette = Klangkette()
        XCTAssertEqual(kette.treffer(jetzt: 0.0, abstandZumSchlag: 0.02),
                       .imTakt(glieder: 1))
        XCTAssertEqual(kette.treffer(jetzt: 0.5, abstandZumSchlag: 0.05),
                       .imTakt(glieder: 2))
        XCTAssertEqual(kette.faktor, 1.25, accuracy: 0.001)
        XCTAssertEqual(kette.treffer(jetzt: 1.0, abstandZumSchlag: 0.01),
                       .imTakt(glieder: 3))
        XCTAssertEqual(kette.faktor, 1.6, accuracy: 0.001)
    }

    func testDasVierteGliedKlingtAusUndVerbrauchtDieKette() {
        var kette = Klangkette()
        for t in 0..<3 {
            _ = kette.treffer(jetzt: Double(t) * 0.5, abstandZumSchlag: 0.0)
        }
        XCTAssertEqual(kette.treffer(jetzt: 1.5, abstandZumSchlag: 0.0), .ausklang)
        XCTAssertEqual(kette.glieder, 0, "Der Ausklang verbraucht die Kette")
    }

    /// Der wichtigste Test: danebenliegen kostet den Aufbau, nicht den Kampf.
    func testDanebenSetztAufEinsUndNichtAufNull() {
        var kette = Klangkette()
        _ = kette.treffer(jetzt: 0.0, abstandZumSchlag: 0.0)
        _ = kette.treffer(jetzt: 0.5, abstandZumSchlag: 0.0)
        XCTAssertEqual(kette.treffer(jetzt: 0.7, abstandZumSchlag: 0.24), .daneben)
        XCTAssertEqual(kette.glieder, 1)
        XCTAssertEqual(kette.faktor, 1.0, accuracy: 0.001,
                       "Wer nur draufhaut, verliert nichts - er gewinnt langsamer")
    }

    func testDasFensterIstGrosszuegig() {
        var kette = Klangkette()
        // 120 Zaehlzeiten: der halbe Abstand zwischen zwei Schlaegen ist
        // 0,25 s. Ein Viertel davon muss noch zaehlen.
        XCTAssertEqual(kette.treffer(jetzt: 0, abstandZumSchlag: 0.12),
                       .imTakt(glieder: 1))
    }

    func testEineKetteZerfaelltVonSelbst() {
        var kette = Klangkette()
        _ = kette.treffer(jetzt: 0.0, abstandZumSchlag: 0.0)
        _ = kette.treffer(jetzt: 0.5, abstandZumSchlag: 0.0)
        XCTAssertEqual(kette.glieder, 2)

        // Nach der Haltbarkeit faengt sie von vorn an, auch wenn der
        // naechste Treffer sitzt.
        XCTAssertEqual(kette.treffer(jetzt: 0.5 + Klangkette.haltbarkeit + 0.1,
                                     abstandZumSchlag: 0.0),
                       .imTakt(glieder: 1))
    }

    /// Wer die Kette nie trifft, darf nicht scheitern - nur langsamer sein.
    func testOhneTaktIstManNichtChancenlos() {
        var mit = Klangkette()
        var ohne = Klangkette()
        var schadenMit = 0.0
        var schadenOhne = 0.0
        for i in 0..<16 {
            let t = Double(i) * 0.5
            _ = mit.treffer(jetzt: t, abstandZumSchlag: 0.0)
            schadenMit += mit.glieder == 0 ? 2.0 : mit.faktor
            _ = ohne.treffer(jetzt: t, abstandZumSchlag: 0.24)
            schadenOhne += ohne.faktor
        }
        XCTAssertGreaterThan(schadenMit, schadenOhne)
        XCTAssertLessThan(schadenMit, schadenOhne * 2.0,
                          "Die Kette soll sich lohnen, nicht entscheiden")
    }
}
