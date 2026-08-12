import Foundation

/// Die Einkehr an der Stimmgabel.
///
/// Bisher war eine Bank ein Knopf: man drueckte, war gerettet, drueckte
/// wieder und lief weiter. Dazwischen sass die Figur da und wartete. Das
/// ist der Moment, in dem man im Spiel am laengsten stillsteht, und
/// ausgerechnet der hatte nichts.
///
/// Jetzt ist es ein Vorgang mit drei Abschnitten:
///
///   **Aufsteigen** - sie loest sich in ihre Flamme auf und steigt ueber
///   die Gabel. Solange das laeuft, ist noch nichts entschieden; man
///   sieht nur, dass etwas passiert.
///
///   **Flamme** - sie schwebt ueber der Gabel und *ist* wieder das, was
///   sie vor allem war: ein Klang ohne Gefaess. Nur in diesem Zustand
///   laesst sich die Ausruestung aendern. Das ist keine Menuebedingung,
///   sondern der Grund, warum es ueberhaupt geht - ohne Gefaess kann man
///   das Gefaess wechseln.
///
///   **Aussteigen** - sie faellt in ihre Gestalt zurueck. Ausgeloest wird
///   das durch den Sprung, nicht durch dieselbe Taste, mit der man
///   hereinkam: man geht aus einer Einkehr heraus, indem man sich
///   abstoesst.
///
/// Der ganze Ablauf steht hier und nicht in der Simulation, weil er
/// genau eine Sache tut und sich damit einzeln pruefen laesst.
public struct Einkehr: Sendable, Equatable {

    public enum Zustand: Sendable, Equatable {
        /// Nicht an der Gabel.
        case fort
        /// Loest sich auf. Der Wert laeuft von 0 nach 1.
        case aufsteigen(Double)
        /// Schwebt als Flamme. Hier darf gewechselt werden.
        case flamme
        /// Faellt zurueck in die Gestalt. Der Wert laeuft von 0 nach 1.
        case aussteigen(Double)
    }

    /// Wie lange das Aufloesen dauert. Lang genug, dass man es sieht,
    /// kurz genug, dass es beim zehnten Mal nicht nervt.
    public static let aufstieg: Double = 0.55
    /// Der Rueckweg ist schneller: hinein geht man langsam, hinaus schnell.
    public static let abstieg: Double = 0.32

    public private(set) var zustand: Zustand = .fort

    public init() {}

    public var aktiv: Bool { zustand != .fort }

    /// Nur als Flamme laesst sich die Ausruestung aendern.
    public var darfWechseln: Bool { zustand == .flamme }

    /// Wie weit die Figur schon Flamme ist: 0 Gestalt, 1 ganz Flamme.
    /// Die Darstellung blendet daran beides ineinander.
    public var flammenanteil: Double {
        switch zustand {
        case .fort: return 0
        case .aufsteigen(let t): return glatt(t)
        case .flamme: return 1
        case .aussteigen(let t): return glatt(1 - t)
        }
    }

    /// Wie hoch sie ueber der Gabel steht, als Anteil der vollen Hoehe.
    /// Sie steigt beim Aufloesen und sinkt beim Zurueckfallen - dieselbe
    /// Kurve wie der Flammenanteil, damit beides zusammengehoert.
    public var schwebe: Double { flammenanteil }

    public mutating func beginne() {
        guard zustand == .fort else { return }
        zustand = .aufsteigen(0)
    }

    /// Der Sprung loest das Aussteigen aus - aber erst, wenn sie ganz
    /// Flamme ist. Wer mitten im Aufloesen springt, wuerde sonst in einem
    /// halb aufgeloesten Zustand herausfallen.
    public mutating func verlasse() {
        guard zustand == .flamme else { return }
        zustand = .aussteigen(0)
    }

    /// Bricht alles sofort ab - fuer Raumwechsel und Tod.
    public mutating func abbrechen() {
        zustand = .fort
    }

    /// Gibt zurueck, ob der Vorgang in diesem Bild fertig geworden ist.
    @discardableResult
    public mutating func tick(_ dt: Double) -> Bool {
        switch zustand {
        case .fort, .flamme:
            return false
        case .aufsteigen(let t):
            let neu = t + dt / Self.aufstieg
            if neu >= 1 {
                zustand = .flamme
                return true
            }
            zustand = .aufsteigen(neu)
            return false
        case .aussteigen(let t):
            let neu = t + dt / Self.abstieg
            if neu >= 1 {
                zustand = .fort
                return true
            }
            zustand = .aussteigen(neu)
            return false
        }
    }

    /// Weich anlaufen, weich enden. Eine gerade Rampe sieht bei einem
    /// Uebergang immer nach Schalter aus.
    private func glatt(_ t: Double) -> Double {
        let x = max(0, min(1, t))
        return x * x * (3 - 2 * x)
    }
}
