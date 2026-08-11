import Foundation

/// Der Bruch.
///
/// Am Ende haelt sie es nicht mehr aus. Der Koerper wird locker, sie faehrt
/// aus ihrer Fassung heraus - und der Kern in ihr zerspringt dabei. Was
/// bleibt, ist reiner Klang ohne Gefaess: schneller, harter, weiter. Und
/// ohne Halt.
///
/// Das ist kein Fundstueck und keine Wahl. Es ist ein festes Ereignis, das
/// die Geschichte ausloest, und es laesst sich nicht rueckgaengig machen.
/// Deshalb steht es auch nicht im Katalog der Fassungen: man kann es nicht
/// anlegen, man kann nur hineingeraten.
///
/// Der Preis steht in `lebensverlust`: sie verliert dauernd Leben. Ohne
/// Gefaess zerstreut sie sich, und der Bruch ist ein Wettlauf.
public enum Bruch {

    /// Wie viele halbe Kristalle sie im Bruch pro Sekunde verliert.
    public static let lebensverlust: Double = 0.5

    /// Unter diesem Rest hoert der Verlust auf. Er soll draengen, nicht
    /// toeten - sterben soll sie an der Dissonanz, nicht an der Uhr.
    public static let untergrenze: Int = 1

    /// Das Gefaess, das keines mehr ist.
    public static let entfesselt = Equipment(
        id: "bruch",
        name: "OHNE FASSUNG",
        openings: 99,
        stil: .entfesselt,
        summary: "ALLES ZUGLEICH - UND NICHTS HAELT SIE MEHR",
        flavour: "SIE IST AUS SICH HERAUSGEFAHREN. WAS JETZT KLINGT, "
               + "KLINGT IN ALLE RICHTUNGEN, UND NICHTS DAVON KOMMT ZURUECK.",
        modifiers: Modifiers(moveSpeed: 1.35, jumpPower: 1.18, dashDistance: 1.4,
                             meleeReach: 1.35, meleeDamage: 1.6,
                             rangedRange: 1.3, rangedDamage: 1.5, rangedCost: 0.55,
                             resonanceRegen: 2.0, cohesion: 1.0, blastForce: 1.5))

    /// Der zersprungene Kern. Er klingt lauter als jeder heile - weil er
    /// nicht mehr gehalten wird.
    public static let bruchkern = Modifiers(meleeDamage: 1.2, rangedDamage: 1.25,
                                            rangedCost: 0.8)
}
