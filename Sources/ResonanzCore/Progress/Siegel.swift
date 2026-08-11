import Foundation

/// Ein Siegel.
///
/// Kleine, dauerhafte Verschiebungen, die man selbst zusammenstellt. Jedes
/// kostet Kerben, und Kerben sind knapp - man traegt nie alles, was man
/// hat. Genau darin liegt der Reiz: nicht im Sammeln, sondern im Weglassen.
///
/// Siegel sind Splitter von Toenen, die einmal jemandem gehoert haben. Sie
/// tun nichts von selbst - sie haengen sich an ihren Klang und faerben ihn.
public struct Siegel: Codable, Sendable, Equatable, Identifiable {
    public let id: String
    public let name: String
    /// Wie viele Kerben es belegt.
    public let kerben: Int
    public let summary: String
    public let flavour: String
    public let modifiers: Modifiers
    /// Manche Siegel aendern nicht die Werte, sondern den Schlag selbst.
    /// Das sind die teuersten - und die einzigen, die eine Fassung
    /// ueberstimmen duerfen.
    public let stil: Kampfstil?

    public init(id: String, name: String, kerben: Int,
                summary: String, flavour: String, modifiers: Modifiers,
                stil: Kampfstil? = nil) {
        self.id = id
        self.name = name
        self.kerben = kerben
        self.summary = summary
        self.flavour = flavour
        self.modifiers = modifiers
        self.stil = stil
    }
}

public enum SiegelKatalog {

    public static let nachhall = Siegel(
        id: "nachhall", name: "NACHHALL", kerben: 1,
        summary: "FERNKLANG TRAEGT WEITER",
        flavour: "EIN RAUM, DER NICHT LOSLASSEN WOLLTE. "
               + "JETZT LAESST ER DEINEN TON NICHT LOS.",
        modifiers: Modifiers(rangedRange: 1.28))

    public static let dauerton = Siegel(
        id: "dauerton", name: "DAUERTON", kerben: 2,
        summary: "RESONANZ KEHRT SCHNELLER ZURUECK",
        flavour: "JEMAND HAT HIER EINEN TON GEHALTEN, BIS IHM DIE LUFT AUSGING. "
               + "DER TON HAELT IMMER NOCH.",
        modifiers: Modifiers(resonanceRegen: 1.6))

    public static let bruchstein = Siegel(
        id: "bruchstein", name: "BRUCHSTEIN", kerben: 2,
        summary: "NAHKAMPF SCHLAEGT HAERTER - DAFUER LANGSAMER",
        flavour: "EIN STUECK MAUER, DAS DEN SCHLAG BEHALTEN HAT, "
               + "DER ES ZERBROCHEN HAT.",
        modifiers: Modifiers(moveSpeed: 0.94, meleeDamage: 1.3))

    public static let federstaub = Siegel(
        id: "federstaub", name: "FEDERSTAUB", kerben: 1,
        summary: "SIE SPRINGT HOEHER",
        flavour: "WAS VOM FLUEGELSCHLAG UEBRIG BLIEB, NACHDEM ER VERKLUNGEN WAR.",
        modifiers: Modifiers(jumpPower: 1.12))

    public static let windschliff = Siegel(
        id: "windschliff", name: "WINDSCHLIFF", kerben: 3,
        summary: "SCHNELL UND WEIT - ABER SIE HAELT WENIGER AUS",
        flavour: "SO LANGE GESCHLIFFEN, BIS NICHTS MEHR IM WEG WAR. "
               + "AUCH NICHTS, WAS GESCHUETZT HAETTE.",
        modifiers: Modifiers(moveSpeed: 1.18, dashDistance: 1.22, cohesion: 0.85))

    public static let hohlklang = Siegel(
        id: "hohlklang", name: "HOHLKLANG", kerben: 2,
        summary: "MEHR ZUSAMMENHALT - DAFUER DUENNERER FERNKLANG",
        flavour: "EIN LEERER RAUM KLINGT LAENGER ALS EIN VOLLER. "
               + "ER HAELT AUCH LAENGER.",
        modifiers: Modifiers(rangedDamage: 0.8, cohesion: 1.4))

    public static let stille = Siegel(
        id: "stille", name: "STILLE", kerben: 1,
        summary: "FERNKLANG KOSTET WENIGER",
        flavour: "WER LEISE ANFAENGT, HAT MEHR UEBRIG.",
        modifiers: Modifiers(rangedCost: 0.7))

    // ---- Was man mit Leben bezahlt -------------------------------------

    public static let scherbenherz = Siegel(
        id: "scherbenherz", name: "SCHERBENHERZ", kerben: 2,
        summary: "SIE SCHLAEGT VIEL HAERTER - UND HAELT VIEL WENIGER AUS",
        flavour: "EIN KRISTALL, DER IN SICH GESPRUNGEN IST UND TROTZDEM "
               + "WEITERKLINGT. LAUTER ALS VORHER.",
        modifiers: Modifiers(meleeDamage: 1.35, cohesion: 0.75))

    public static let bleisiegel = Siegel(
        id: "bleisiegel", name: "BLEISIEGEL", kerben: 2,
        summary: "MEHR ZUSAMMENHALT - DAFUER SCHWER WIE STEIN",
        flavour: "MAN HAENGT ES SICH UM UND MERKT ERST BEIM ERSTEN SPRUNG, "
               + "WAS MAN GETAN HAT.",
        modifiers: Modifiers(moveSpeed: 0.88, jumpPower: 0.92, cohesion: 1.35))

    public static let taubesOhr = Siegel(
        id: "taubes_ohr", name: "TAUBES OHR", kerben: 2,
        summary: "FERNKLANG SCHLAEGT HART - ABER SIE FUELLT SICH KAUM NOCH",
        flavour: "WER NICHT MEHR HINHOERT, TRIFFT GENAUER. "
               + "ER MERKT NUR NICHT MEHR, WANN ER LEER IST.",
        modifiers: Modifiers(rangedDamage: 1.3, resonanceRegen: 0.6))

    public static let pilgerstab = Siegel(
        id: "pilgerstab", name: "PILGERSTAB", kerben: 1,
        summary: "NAHKAMPF REICHT WEITER - TRIFFT DAFUER WEICHER",
        flavour: "WER LANGE GEHT, LERNT, VON WEITER WEG ZU ZEIGEN.",
        modifiers: Modifiers(meleeReach: 1.25, meleeDamage: 0.85))

    // ---- Was den Schlag selbst umbaut ----------------------------------
    //
    // Diese beiden kosten fast alle Kerben, und das ist der Punkt: sie
    // ueberstimmen die Fassung. Wer so eines traegt, hat sich fuer einen
    // Kampfstil entschieden und gegen alles andere.

    public static let kreiselsiegel = Siegel(
        id: "kreiselsiegel", name: "KREISELSIEGEL", kerben: 3,
        summary: "SIE SCHLAEGT RUNDUM - EGAL, WAS SIE TRAEGT",
        flavour: "EIN TON, DER SICH NICHT ENTSCHEIDEN KONNTE, "
               + "IN WELCHE RICHTUNG ER GEHT. JETZT GEHT ER IN ALLE.",
        modifiers: Modifiers(meleeDamage: 0.9), stil: .wirbel)

    public static let nadelsiegel = Siegel(
        id: "nadelsiegel", name: "NADELSIEGEL", kerben: 3,
        summary: "SIE SCHLAEGT SEHR WEIT UND SEHR SCHMAL - EGAL, WAS SIE TRAEGT",
        flavour: "DUENN GENUG, UM DURCH EINE FUGE ZU PASSEN, "
               + "UND LANG GENUG, UM DAHINTER ANZUKOMMEN.",
        modifiers: Modifiers(), stil: .peitsche)

    public static let all: [Siegel] = [
        nachhall, dauerton, bruchstein, federstaub, windschliff, hohlklang, stille,
        scherbenherz, bleisiegel, taubesOhr, pilgerstab,
        kreiselsiegel, nadelsiegel,
    ]

    public static func find(_ id: String) -> Siegel? {
        all.first { $0.id == id }
    }

    /// Was diese Auswahl an Kerben kostet.
    public static func kosten(_ ids: [String]) -> Int {
        ids.compactMap(find).reduce(0) { $0 + $1.kerben }
    }
}
