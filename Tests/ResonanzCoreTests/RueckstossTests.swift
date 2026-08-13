import XCTest
@testable import ResonanzCore

/// Der Schlag stoesst auch die, die ihn fuehrt - aber nur in der Luft.
final class RueckstossTests: XCTestCase {

    private func heldin(inDerLuft: Bool) -> Player {
        let spieler = Player(position: Vec2(100, 100),
                             progression: Progression(abilities: [.fluegelschlag]),
                             kern: .leier)
        spieler.placeAt(Vec2(100, 100), facing: 1)
        // Frisch gesetzt hat sie noch keinen Boden unter sich - genau
        // der Zustand, um den es hier geht. Fuer den Bodenfall wird sie
        // einen Schritt lang auf festen Grund gestellt.
        if !inDerLuft { spieler.setzeAufBodenZumTesten() }
        return spieler
    }

    func testInDerLuftWirftDerSchlagSieZurueck() {
        let s = heldin(inDerLuft: true)
        s.meleeRecoil(from: 1)
        XCTAssertLessThan(s.velocity.x, 0, "Schlag nach rechts stoesst nach links")
        XCTAssertEqual(abs(s.velocity.x), Tuning.meleeRecoil, accuracy: 0.001)
    }

    func testNachLinksGeschlagenStoesstNachRechts() {
        let s = heldin(inDerLuft: true)
        s.meleeRecoil(from: -1)
        XCTAssertGreaterThan(s.velocity.x, 0)
    }

    /// Am Boden nicht: sonst schiebt der eigene Schlag sie vom Gegner
    /// weg, und man kaeme nie zum zweiten.
    func testAmBodenStehtSieFest() {
        let s = heldin(inDerLuft: false)
        let vorher = s.velocity.x
        s.meleeRecoil(from: 1)
        XCTAssertEqual(s.velocity.x, vorher, accuracy: 0.001)
    }

    /// Der Stoss muss die Steuerung kurz sperren - sonst schiebt ein
    /// gehaltener Laufknopf ihn im selben Bild wieder weg.
    func testDerStossSperrtDieSteuerungKurz() {
        let s = heldin(inDerLuft: true)
        s.meleeRecoil(from: 1)
        XCTAssertGreaterThanOrEqual(s.controlLock, Tuning.meleeRecoilLock - 0.0001)
    }

    /// Er soll den Schlag spuerbar machen, nicht die Bewegung uebernehmen.
    func testErIstDeutlichSchwaecherAlsDerAbprallerNachUnten() {
        XCTAssertLessThan(Tuning.meleeRecoil, abs(Tuning.pogoVelocity))
    }
}
