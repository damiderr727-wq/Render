import Foundation

/// Was eine Ausruestung an den Werten der Figur verschiebt.
///
/// Alles sind Faktoren um 1.0 - so bleibt der Grundwert in `Tuning` die
/// einzige Wahrheit, und eine Ausruestung sagt nur, wie weit sie davon
/// abweicht. Ein Wert unter 1 ist ein Preis, keine Strafe: jede Fassung
/// nimmt etwas, damit sie etwas anderes geben kann.
public struct Modifiers: Codable, Sendable, Equatable {
    public var moveSpeed: Double
    public var jumpPower: Double
    public var dashDistance: Double
    public var meleeReach: Double
    public var meleeDamage: Double
    public var rangedRange: Double
    public var rangedDamage: Double
    public var rangedCost: Double
    public var resonanceRegen: Double
    /// Zusammenhalt: wie viel Zerstreuung sie vertraegt, bevor sie vergeht.
    public var cohesion: Double
    /// Wucht von Basston und Trommelstoss.
    public var blastForce: Double

    public init(moveSpeed: Double = 1, jumpPower: Double = 1, dashDistance: Double = 1,
                meleeReach: Double = 1, meleeDamage: Double = 1,
                rangedRange: Double = 1, rangedDamage: Double = 1, rangedCost: Double = 1,
                resonanceRegen: Double = 1, cohesion: Double = 1, blastForce: Double = 1) {
        self.moveSpeed = moveSpeed
        self.jumpPower = jumpPower
        self.dashDistance = dashDistance
        self.meleeReach = meleeReach
        self.meleeDamage = meleeDamage
        self.rangedRange = rangedRange
        self.rangedDamage = rangedDamage
        self.rangedCost = rangedCost
        self.resonanceRegen = resonanceRegen
        self.cohesion = cohesion
        self.blastForce = blastForce
    }

    public static let neutral = Modifiers()

    /// Zwei Quellen zusammenlegen. Faktoren multiplizieren sich - so bleibt
    /// jede Quelle fuer sich verstaendlich, und keine kann eine andere
    /// aufheben, indem sie einen Wert einfach ueberschreibt.
    public static func * (a: Modifiers, b: Modifiers) -> Modifiers {
        Modifiers(moveSpeed: a.moveSpeed * b.moveSpeed,
                  jumpPower: a.jumpPower * b.jumpPower,
                  dashDistance: a.dashDistance * b.dashDistance,
                  meleeReach: a.meleeReach * b.meleeReach,
                  meleeDamage: a.meleeDamage * b.meleeDamage,
                  rangedRange: a.rangedRange * b.rangedRange,
                  rangedDamage: a.rangedDamage * b.rangedDamage,
                  rangedCost: a.rangedCost * b.rangedCost,
                  resonanceRegen: a.resonanceRegen * b.resonanceRegen,
                  cohesion: a.cohesion * b.cohesion,
                  blastForce: a.blastForce * b.blastForce)
    }
}

/// Ein Kleidungsstueck oder Harnisch.
///
/// Cadence ist Klang unter Druck. Eine Fassung ist ein Gefaess: wo sie
/// Oeffnungen hat, entweicht der Ton - und je weniger Oeffnungen, desto
/// hoeher der Druck an den verbliebenen. Daraus folgt die ganze Mechanik
/// von selbst. Eine geschlossene Fassung traegt weit und schlaegt hart,
/// nimmt ihr aber die Beweglichkeit; eine offene laesst sie schnell und
/// nah kaempfen, verpufft aber in die Ferne.
public struct Equipment: Codable, Sendable, Equatable, Identifiable {
    public let id: String
    public let name: String
    /// Wie viele Oeffnungen das Gefaess hat. 0 gibt es nicht - dann klingt
    /// sie gar nicht mehr.
    public let openings: Int
    /// Wie sie in dieser Fassung zuschlaegt. Nicht die Klinge entscheidet
    /// das, sondern das, was ihr Platz laesst.
    public let stil: Kampfstil
    public let summary: String
    public let flavour: String
    public let modifiers: Modifiers

    public init(id: String, name: String, openings: Int, stil: Kampfstil,
                summary: String, flavour: String, modifiers: Modifiers) {
        self.id = id
        self.name = name
        self.openings = openings
        self.stil = stil
        self.summary = summary
        self.flavour = flavour
        self.modifiers = modifiers
    }
}

/// Alle Fassungen, die es gibt.
public enum EquipmentCatalog {

    /// So faengt sie an: ohne alles.
    ///
    /// Kein Gefaess, also nichts, was sie zusammenhaelt - sie traegt einen
    /// Kristall weniger als mit dem schlichten Mantel. Dafuer haengt ihr
    /// auch nichts im Weg. Das ist der Ausgangspunkt, an dem alles andere
    /// gemessen wird, und der Grund, warum der erste Fund im Spiel kein
    /// Schwert ist, sondern etwas zum Anziehen.
    public static let ohne = Equipment(
        id: "ohne",
        name: "OHNE ALLES",
        openings: 0,
        stil: .bogen,
        summary: "NICHTS HAELT SIE - DAFUER HAENGT IHR AUCH NICHTS IM WEG",
        flavour: "SO IST SIE AUFGEWACHT. EIN KLANG, EINE STIMMGABEL, "
               + "ZWEI SPITZEN, AUF DENEN SIE STEHT.",
        modifiers: Modifiers(moveSpeed: 1.06, dashDistance: 1.05, cohesion: 0.8))

    /// Das erste Fundstueck. Er tut nichts, ausser sie zusammenzuhalten -
    /// und genau das ist ihr Zweck.
    public static let mantel = Equipment(
        id: "mantel",
        name: "SCHLICHTER MANTEL",
        openings: 4,
        stil: .bogen,
        summary: "HAELT SIE ZUSAMMEN. SONST NICHTS.",
        flavour: "OHNE IHN ZERSTREUT SIE SICH IM ERSTEN WIND. "
               + "ER GIBT IHR NICHTS - ER NIMMT IHR NUR DAS VERGEHEN.",
        modifiers: .neutral)

    /// Eine Oeffnung nach vorn: der ganze Druck geht in die Ferne.
    public static let engeFassung = Equipment(
        id: "enge_fassung",
        name: "ENGE FASSUNG",
        openings: 1,
        stil: .stich,
        summary: "FERNKLANG TRAEGT WEIT UND HART - DAFUER IST SIE TRAEGE",
        flavour: "EIN HARNISCH MIT EINER EINZIGEN OEFFNUNG. "
               + "WAS DA HERAUSKOMMT, KOMMT MIT ALLEM HERAUS.",
        modifiers: Modifiers(moveSpeed: 0.82, jumpPower: 0.94, dashDistance: 0.85,
                             rangedRange: 1.75, rangedDamage: 1.4,
                             rangedCost: 1.25, resonanceRegen: 0.8))

    /// Viele Oeffnungen: sie klingt ueberall, aber nirgends weit.
    public static let offeneFassung = Equipment(
        id: "offene_fassung",
        name: "OFFENE FASSUNG",
        openings: 9,
        stil: .wirbel,
        summary: "NAHKLANG WEIT UND BILLIG - FERNKLANG VERPUFFT",
        flavour: "NEUN OEFFNUNGEN. SIE KLINGT NACH ALLEN SEITEN ZUGLEICH, "
               + "UND NICHTS DAVON KOMMT WEIT.",
        modifiers: Modifiers(moveSpeed: 1.08, meleeDamage: 1.2,
                             rangedRange: 0.6, rangedDamage: 0.75, rangedCost: 0.7,
                             resonanceRegen: 1.5))

    /// Unten geschlossen bis auf einen Schlitz: die Wucht geht nach unten.
    public static let schlagfassung = Equipment(
        id: "schlagfassung",
        name: "SCHLAGFASSUNG",
        openings: 2,
        stil: .sturz,
        summary: "BASSTON UND TROMMEL REISSEN - DAFUER SPRINGT SIE NIEDRIG",
        flavour: "WIE EIN KESSEL, DER NUR NACH UNTEN ATMET. "
               + "MAN HOERT SIE DURCH DEN BODEN, BEVOR MAN SIE SIEHT.",
        modifiers: Modifiers(moveSpeed: 0.9, jumpPower: 0.85, dashDistance: 0.9,
                             meleeDamage: 1.15, rangedRange: 0.9,
                             cohesion: 1.2, blastForce: 2.0))

    /// Zerrissen: sie haelt kaum noch, dafuer ist sie schnell.
    public static let gerissenesGewand = Equipment(
        id: "gerissenes_gewand",
        name: "GERISSENES GEWAND",
        openings: 14,
        stil: .hetze,
        summary: "SCHNELL UND WEIT - ABER SIE HAELT FAST NICHTS AUS",
        flavour: "MEHR RISS ALS STOFF. WER SO WENIG BEISAMMEN IST, "
               + "KOMMT SCHNELLER VORAN - UND VERGEHT SCHNELLER.",
        modifiers: Modifiers(moveSpeed: 1.28, jumpPower: 1.10, dashDistance: 1.35,
                             rangedCost: 0.85, resonanceRegen: 1.25, cohesion: 0.6))

    /// Nur ein Tuch an der Schulter. Es haelt kaum etwas zusammen, aber es
    /// haengt ihr auch nirgends im Weg.
    public static let cape = Equipment(
        id: "cape",
        name: "WEHENDES CAPE",
        openings: 6,
        stil: .hetze,
        summary: "SPRINGT HOEHER UND SETZT SCHNELLER NACH",
        flavour: "ES DECKT NICHTS. ES FAENGT NUR DIE BEWEGUNG - "
               + "UND GIBT SIE EINEN LIDSCHLAG SPAETER ZURUECK.",
        modifiers: Modifiers(moveSpeed: 1.06, jumpPower: 1.16, dashDistance: 1.18,
                             meleeReach: 0.9, cohesion: 0.9))

    /// Drei Oeffnungen, gleichmaessig verteilt: nichts ragt heraus, nichts
    /// faellt aus. Der Panzer fuer die, die nicht sterben wollen.
    public static let chorpanzer = Equipment(
        id: "chorpanzer",
        name: "CHORPANZER",
        openings: 3,
        stil: .bogen,
        summary: "HAELT VIEL AUS - DAFUER IST SIE SCHWERFAELLIG",
        flavour: "VIER STIMMEN, DIE EINANDER TRAGEN. EINZELN WAERE JEDE "
               + "ZU SCHWACH, ZUSAMMEN HALTEN SIE ALLES.",
        modifiers: Modifiers(moveSpeed: 0.86, jumpPower: 0.92, dashDistance: 0.88,
                             resonanceRegen: 0.9, cohesion: 1.45))

    /// Eine Oeffnung, aber nach vorn gezogen wie ein Rohr: der Schlag geht
    /// weit hinaus, statt hart zu werden.
    public static let pfeifenharnisch = Equipment(
        id: "pfeifenharnisch",
        name: "PFEIFENHARNISCH",
        openings: 1,
        stil: .peitsche,
        summary: "SIE TRIFFT, WAS WEIT WEG STEHT - ABER NUR GENAU DAVOR",
        flavour: "AUS DEM REGISTER GESCHNITTEN UND UM SIE GEBOGEN. "
               + "WAS HERAUSKOMMT, KOMMT LANG HERAUS.",
        modifiers: Modifiers(moveSpeed: 0.94, meleeDamage: 0.9,
                             rangedRange: 1.25, rangedCost: 1.1))

    /// Zwoelf feine Schlitze: sie klingt ununterbrochen, aber leise.
    public static let flimmerhemd = Equipment(
        id: "flimmerhemd",
        name: "FLIMMERHEMD",
        openings: 12,
        stil: .flirren,
        summary: "SEHR SCHNELLE, SEHR KLEINE TREFFER - UND SIE HAELT WENIG AUS",
        flavour: "SO DUENN, DASS MAN DEN TON DURCH DEN STOFF SIEHT. "
               + "ER HOERT NIE AUF, ER WIRD NUR NIE LAUT.",
        modifiers: Modifiers(moveSpeed: 1.14, dashDistance: 1.1,
                             rangedDamage: 0.85, resonanceRegen: 1.4,
                             cohesion: 0.85))

    /// Aus der Kammer der ersten Stimme. Kein Panzer, kein Gewand -
    /// nur ein Band, das den Klang beisammenhaelt, damit man ihn hoert,
    /// statt ihn zu tragen.
    public static let lauschband = Equipment(
        id: "lauschband",
        name: "LAUSCHBAND",
        openings: 2,
        stil: .bogen,
        summary: "WENIGE OEFFNUNGEN, DAFUER KEHRT DER KLANG SCHNELL ZURUECK",
        flavour: "JEMAND HAT ES SICH UM DEN KOPF GEBUNDEN, UM BESSER ZU "
               + "HOEREN. ES HAT NICHTS GENUETZT - ABER ES HAELT.",
        modifiers: Modifiers(resonanceRegen: 1.35, cohesion: 1.05))

    /// Der Flickmantel: aus drei Maenteln, die ihre Leute nicht mehr
    /// brauchten. Nur im Dorf zu haben.
    public static let flickmantel = Equipment(
        id: "flickmantel",
        name: "FLICKMANTEL",
        openings: 6,
        stil: .bogen,
        summary: "MEHR OEFFNUNGEN ALS DER SCHLICHTE MANTEL, UND ER HAELT MEHR AUS",
        flavour: "AUS DREI MAENTELN ZUSAMMENGESETZT, DIE NIEMAND MEHR "
               + "GEBRAUCHT HAT. ER HAELT. FRAG NICHT, WIE.",
        modifiers: Modifiers(moveSpeed: 0.97, cohesion: 1.15))

    public static let all: [Equipment] = [
        ohne, mantel, cape, chorpanzer, pfeifenharnisch, flimmerhemd, engeFassung, offeneFassung, schlagfassung, gerissenesGewand,
        lauschband, flickmantel,
    ]

    public static func find(_ id: String) -> Equipment? {
        all.first { $0.id == id }
    }
}

/// Die abgeleiteten Werte der Figur.
///
/// Drei Quellen verschieben die Grundwerte aus `Tuning`, und sie
/// multiplizieren sich: die getragene **Fassung**, der **Kern** in ihr und
/// die angelegten **Siegel**. Der Spieler fragt nie mehr direkt `Tuning`,
/// sondern immer diese Tabelle - dadurch wirkt jede neue Fassung, jeder
/// neue Kern und jedes Siegel ueberall zugleich, ohne dass man die Stellen
/// einzeln nachziehen muesste.
///
/// Was aus welcher Quelle kommt, ist bewusst getrennt:
///
///   Fassung  - der Kampfstil und der Zusammenhalt
///   Kern     - der Magiestil und ihre Anlage
///   Siegel   - alles, was man selbst dazuwaehlt
public struct Stats: Sendable {
    public let equipment: Equipment
    public let kern: Kern
    public let siegel: [Siegel]
    /// Nach dem Bruch ist der Kern zersprungen - er klingt lauter, weil ihn
    /// nichts mehr haelt.
    public let gebrochen: Bool
    private let m: Modifiers

    public init(equipment: Equipment = EquipmentCatalog.mantel,
                kern: Kern = .stimmgabel,
                siegel: [Siegel] = [],
                gebrochen: Bool = false) {
        self.equipment = equipment
        self.kern = kern
        self.siegel = siegel
        self.gebrochen = gebrochen
        var alle = equipment.modifiers * kern.modifiers
        if gebrochen { alle = alle * Bruch.bruchkern }
        self.m = siegel.reduce(alle) { $0 * $1.modifiers }
    }

    /// Alle Faktoren zusammen - fuer Anzeige und Pruefung.
    public var modifiers: Modifiers { m }

    /// Schaden ist ganzzahlig, und beim Runden verschwindet jeder kleine
    /// Aufschlag: ein Ton mit Schaden 1 bleibt auch mit vierzig Prozent
    /// mehr Druck bei 1. Ab einem deutlichen Aufschlag muss darum
    /// mindestens ein Punkt ankommen - sonst verspricht eine Fassung etwas,
    /// das man nie zu spueren bekommt.
    private func scaledDamage(_ base: Int, _ factor: Double) -> Int {
        let raw = Double(base) * factor
        if factor >= 1.25 { return Swift.max(base + 1, Int(raw.rounded())) }
        if factor < 1 { return Swift.max(1, Int(raw.rounded(.down))) }
        return Swift.max(1, Int(raw.rounded()))
    }

    public var runSpeed: Double { Tuning.runSpeed * m.moveSpeed }
    public var jumpVelocity: Double { Tuning.jumpVelocity * m.jumpPower }
    public var doubleJumpVelocity: Double { Tuning.doubleJumpVelocity * m.jumpPower }
    public var dashSpeed: Double { Tuning.dashSpeed * m.dashDistance }
    public var dashExitSpeed: Double { Tuning.dashExitSpeed * m.dashDistance }
    public var resonanceRegen: Double { Tuning.resonanceRegen * m.resonanceRegen }
    public var slamRadius: Double { 34 * m.blastForce }
    public var slamDamage: Int { scaledDamage(3, m.blastForce) }

    /// Der Zusammenhalt bestimmt, wie viel sie vertraegt - gerechnet in
    /// halben Kristallen. Ein Kristall sind zwei.
    public func maxHealth(crystals: Int) -> Int {
        Swift.max(1, Int((Double(crystals * 2) * m.cohesion).rounded()))
    }

    /// Welcher Stil tatsaechlich gilt. Normalerweise der der Fassung - es
    /// sei denn, ein Siegel ueberstimmt sie. Das duerfen nur die teuersten.
    public var stil: Kampfstil {
        siegel.compactMap(\.stil).first ?? equipment.stil
    }

    /// Der Schlag: Stil aus der Fassung (oder einem Siegel), Feinschliff
    /// aus allen Quellen.
    public var melee: MeleeProfile {
        let p = stil.melee
        return MeleeProfile(reach: p.reach * m.meleeReach,
                            halfHeight: p.halfHeight * (0.6 + 0.4 * m.meleeReach),
                            damage: scaledDamage(p.damage, m.meleeDamage),
                            cooldown: p.cooldown,
                            knockback: p.knockback * m.blastForce,
                            shape: p.shape,
                            windup: p.windup,
                            active: p.active)
    }

    /// Der Fernklang: Stil aus dem Kern.
    public var ranged: RangedProfile {
        let p = Tuning.ranged(kern)
        return RangedProfile(damage: scaledDamage(p.damage, m.rangedDamage),
                             // Reichweite steckt in Tempo und Lebensdauer.
                             speed: p.speed * (0.7 + 0.3 * m.rangedRange),
                             cost: p.cost * m.rangedCost,
                             cooldown: p.cooldown,
                             count: p.count,
                             spread: p.spread / Swift.max(0.5, m.rangedRange),
                             radius: p.radius * (0.8 + 0.2 * m.rangedDamage),
                             pierces: p.pierces + (m.rangedDamage >= 1.35 ? 1 : 0),
                             lifetime: p.lifetime * m.rangedRange,
                             gravity: p.gravity / Swift.max(0.5, m.rangedRange))
    }
}
