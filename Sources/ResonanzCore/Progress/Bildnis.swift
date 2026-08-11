import Foundation

/// Wie Cadence dargestellt wird - die Namen der Bildreihen an einem Ort.
///
/// Sie wird in Schichten gezeichnet, und zwar in dieser Reihenfolge:
///
///     Nadeln  ->  Fassung  ->  Flamme  ->  Kern
///
/// Gebacken werden die Schichten trotzdem zu fertigen Bildern, eine Reihe
/// je Kombination aus Kern und Fassung. Das ist Absicht: die Darstellung
/// setzt dann pro Bild genau einen Sprite, ohne Gelenkpunkte, ohne
/// Reihenfolge, ohne Versatz, der bei jeder Pose neu stimmen muesste.
/// Der Preis ist Platz im Atlas - und Platz ist das Billigste, was wir
/// haben, solange die Bilder aus einem Programm fallen und nicht aus einer
/// Hand.
///
/// Eine Reihe faellt aus dem Schema: **ohne**. Das ist sie selbst, ohne
/// Fassung und ohne alles - der Bogen fuers Inventar, an dem man sieht,
/// wie weit sie schon ist.
public enum Bildnis {
    /// Die Bildreihe fuer den Spielraum.
    public static func sprite(kern: Kern, fassung: String, zustand: String) -> String {
        "cadence_\(kern.rawValue)_\(fassung)_\(zustand)"
    }

    /// Sie ohne alles - fuer das Inventar. Nur die Nadeln, die Flamme und
    /// der Kern, der gerade in ihr steckt.
    public static let ohneFassung = "ohne"

    public static func nackt(kern: Kern, zustand: String = "idle") -> String {
        sprite(kern: kern, fassung: ohneFassung, zustand: zustand)
    }

    /// Alle Zustaende, zu denen es Bilder geben muss.
    public static let zustaende = [
        "idle", "run", "jump", "fall", "land", "dash",
        "wall", "melee", "cast", "hurt", "rest",
    ]
}
