import Foundation

/// Wie sie zuschlaegt.
///
/// Die Klinge selbst entscheidet das nicht - jede Schallklinge schlaegt
/// gleich. Was den Schlag formt, ist die Fassung: ein Harnisch mit einer
/// einzigen Oeffnung laesst nur einen Stich zu, ein offenes Gewand einen
/// Wirbel um sie herum. Man wechselt also nicht die Waffe, um anders zu
/// kaempfen, sondern das, was man traegt.
public enum Kampfstil: String, Codable, Sendable, CaseIterable {
    /// Der weite Bogen. Ausgewogen, verzeiht am meisten.
    case bogen
    /// Ein langer, schmaler Stoss nach vorn.
    case stich
    /// Rundum - trifft auch, was hinter ihr steht.
    case wirbel
    /// Schwer und langsam, mit Wucht nach unten.
    case sturz
    /// Zwei schnelle Schlaege statt einem grossen.
    case hetze

    public var displayName: String {
        switch self {
        case .bogen: return "BOGEN"
        case .stich: return "STICH"
        case .wirbel: return "WIRBEL"
        case .sturz: return "STURZ"
        case .hetze: return "HETZE"
        }
    }

    public var summary: String {
        switch self {
        case .bogen: return "WEITER SCHLAG, AUSGEWOGEN"
        case .stich: return "LANG UND SCHMAL - TRIFFT NUR, WAS VORN STEHT"
        case .wirbel: return "RUNDUM - AUCH NACH HINTEN"
        case .sturz: return "SCHWER UND LANGSAM, DAFUER REISST ES"
        case .hetze: return "ZWEI SCHNELLE SCHLAEGE STATT EINEM"
        }
    }

    /// Der Grundschlag dieses Stils. Die Fassung verschiebt ihn danach noch.
    public var melee: MeleeProfile {
        switch self {
        case .bogen:
            return MeleeProfile(reach: 30, halfHeight: 15, damage: 2,
                                cooldown: 0.30, knockback: 130, shape: .arc,
                                windup: 0.045, active: 0.10)
        case .stich:
            return MeleeProfile(reach: 42, halfHeight: 7, damage: 2,
                                cooldown: 0.34, knockback: 90, shape: .thrust,
                                windup: 0.06, active: 0.08)
        case .wirbel:
            return MeleeProfile(reach: 24, halfHeight: 24, damage: 2,
                                cooldown: 0.38, knockback: 150, shape: .radial,
                                windup: 0.07, active: 0.13)
        case .sturz:
            return MeleeProfile(reach: 27, halfHeight: 20, damage: 4,
                                cooldown: 0.54, knockback: 290, shape: .radial,
                                windup: 0.09, active: 0.14)
        case .hetze:
            return MeleeProfile(reach: 26, halfHeight: 12, damage: 1,
                                cooldown: 0.15, knockback: 70, shape: .arc,
                                windup: 0.02, active: 0.07)
        }
    }
}

/// Die Waffe selbst: eine Schallklinge.
///
/// Sie ist die Standardwaffe und bleibt es. Alle Klingen funktionieren
/// gleich - was sich unterscheidet, ist allein, wie der Schlag aussieht.
/// Damit ist das Finden einer neuen Klinge nie ein Machtzuwachs, sondern
/// eine Entscheidung darueber, wie man aussehen will.
public struct Klinge: Codable, Sendable, Equatable, Identifiable {
    public let id: String
    public let name: String
    public let flavour: String
    /// Name des Schlagbogens im Atlas. Der einzige Unterschied.
    public let effect: String

    public init(id: String, name: String, flavour: String, effect: String) {
        self.id = id
        self.name = name
        self.flavour = flavour
        self.effect = effect
    }
}

public enum KlingenKatalog {
    public static let schlicht = Klinge(
        id: "schlicht",
        name: "SCHLICHTE SCHALLKLINGE",
        flavour: "EIN TON, DEN JEMAND SO LANGE GEHALTEN HAT, "
               + "BIS ER EINE SCHNEIDE BEKAM.",
        effect: "klinge_schlicht")

    public static let gezackt = Klinge(
        id: "gezackt",
        name: "GEZACKTE SCHALLKLINGE",
        flavour: "SIE SCHNEIDET NICHT SAUBERER. SIE KLINGT NUR LAUTER DABEI.",
        effect: "klinge_gezackt")

    public static let glas = Klinge(
        id: "glas",
        name: "GLASKLINGE",
        flavour: "DUENN GENUG, UM DURCH DAS LICHT ZU GEHEN. "
               + "SIE SCHLAEGT WIE JEDE ANDERE.",
        effect: "klinge_glas")

    public static let all: [Klinge] = [schlicht, gezackt, glas]

    public static func find(_ id: String) -> Klinge? {
        all.first { $0.id == id }
    }
}
