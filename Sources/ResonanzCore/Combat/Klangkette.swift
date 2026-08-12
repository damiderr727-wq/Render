import Foundation

/// Die Kampffunktion dieses Spiels: **im Takt treffen**.
///
/// Es gab zwei naheliegende Wege, und beide waren falsch. Der eine war,
/// aus dem Vorbild zu uebernehmen, was dort funktioniert - Seelen
/// sammeln, Seelen ausgeben. Der andere war, gar nichts zu bauen und den
/// Kampf beim Schlagen zu belassen.
///
/// Diese Welt ist aus Klang. Also gehoert ihr Kampf nicht dem, der
/// schneller drueckt, sondern dem, der **richtig** drueckt: jeder Raum
/// hat ein Stueck, jedes Stueck einen Takt, und wer auf den Schlag
/// trifft, haengt seinen Treffer an den vorigen an. Aus einzelnen
/// Schlaegen wird eine Kette, aus der Kette ein Akkord.
///
/// Drei Regeln, und keine mehr:
///
/// 1. **Ein Treffer im Fenster verlaengert die Kette.** Das Fenster ist
///    grosszuegig - es geht um Musikalitaet, nicht um Millisekunden.
/// 2. **Ein Treffer daneben setzt sie auf eins zurueck**, nicht auf
///    null. Danebenliegen kostet den Aufbau, nicht den Kampf. Wer nur
///    draufhaut, gewinnt langsamer - aber er gewinnt.
/// 3. **Beim vierten Glied klingt es aus.** Der Nachklang trifft alles
///    in der Naehe und setzt die Kette zurueck. Man baut sie also
///    absichtlich auf und gibt sie absichtlich aus.
///
/// Der erste Boss heisst nicht zufaellig DER GROSSE AUFTAKT: er gibt den
/// Takt vor, an dem man die Sache lernt.
public struct Klangkette: Sendable, Equatable {

    /// So weit vor oder hinter dem Schlag zaehlt ein Treffer noch als
    /// "im Takt". 130 Millisekunden nach beiden Seiten - das ist etwa
    /// das, was ein Mensch als "zusammen" hoert, und deutlich mehr, als
    /// ein Rhythmusspiel verlangen wuerde. Hier ist es kein Test.
    public static let fenster: Double = 0.13

    /// Laenge, ab der die Kette ausklingt.
    public static let ausklang = 4

    /// Nach so langer Pause zerfaellt die Kette von selbst.
    public static let haltbarkeit: Double = 2.2

    public private(set) var glieder: Int = 0
    /// Wann zuletzt getroffen wurde, auf der Uhr der Simulation.
    public private(set) var letzterTreffer: Double = -999

    public init() {}

    /// Der Schadensfaktor der aktuellen Kette.
    ///
    /// Bewusst flach: die Kette soll sich lohnen, aber nicht darueber
    /// entscheiden, ob man gewinnt. Wer sie nie trifft, braucht etwa ein
    /// Drittel laenger - er scheitert nicht.
    public var faktor: Double {
        switch glieder {
        case 0, 1: return 1.0
        case 2: return 1.25
        case 3: return 1.6
        default: return 2.0
        }
    }

    /// Ist die Kette abgelaufen?
    public func zerfallen(jetzt: Double) -> Bool {
        glieder > 0 && jetzt - letzterTreffer > Self.haltbarkeit
    }

    public mutating func verfallenLassen(jetzt: Double) {
        if zerfallen(jetzt: jetzt) { glieder = 0 }
    }

    /// Was ein Treffer aus der Kette macht.
    public enum Wirkung: Sendable, Equatable {
        /// Daneben - die Kette faengt von vorn an.
        case daneben
        /// Im Takt, die Kette waechst.
        case imTakt(glieder: Int)
        /// Das vierte Glied: es klingt aus, und die Kette ist verbraucht.
        case ausklang
    }

    /// Traegt einen Treffer ein. `phase` ist der Abstand zum naechsten
    /// Schlag in Sekunden, immer als Betrag.
    public mutating func treffer(jetzt: Double, abstandZumSchlag phase: Double)
        -> Wirkung {
        verfallenLassen(jetzt: jetzt)
        letzterTreffer = jetzt

        guard phase <= Self.fenster else {
            glieder = 1
            return .daneben
        }

        glieder += 1
        if glieder >= Self.ausklang {
            glieder = 0
            return .ausklang
        }
        return .imTakt(glieder: glieder)
    }
}

/// Der Takt eines Raums.
///
/// Er kommt aus dem Stueck, das gerade laeuft - nicht aus einer Zahl im
/// Kampfcode. Damit stimmt der Kampf immer mit dem ueberein, was man
/// hoert, auch wenn jemand spaeter die Musik umschreibt.
public struct Takt: Sendable, Equatable {
    public let bpm: Double
    /// Wann der erste Schlag lag, auf der Uhr der Simulation.
    public let beginn: Double

    public init(bpm: Double, beginn: Double = 0) {
        self.bpm = max(20, bpm)
        self.beginn = beginn
    }

    public var sekundenProSchlag: Double { 60 / bpm }

    /// Abstand zum naechstgelegenen Schlag, immer positiv.
    ///
    /// Gemessen wird zum *naechsten* Schlag, nicht zum letzten: wer eine
    /// Spur zu frueh drueckt, ist genauso im Takt wie einer, der eine
    /// Spur zu spaet drueckt. Alles andere waere ungerecht gegen die
    /// Haelfte aller Spieler.
    public func abstandZumSchlag(_ zeit: Double) -> Double {
        let spb = sekundenProSchlag
        let seit = (zeit - beginn).truncatingRemainder(dividingBy: spb)
        let vor = seit < 0 ? seit + spb : seit
        return min(vor, spb - vor)
    }

    /// 0 genau auf dem Schlag, 1 genau dazwischen - fuer die Anzeige.
    public func puls(_ zeit: Double) -> Double {
        abstandZumSchlag(zeit) / (sekundenProSchlag / 2)
    }
}
