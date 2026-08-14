#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Das Bestiarium, aufgeschlagen.
///
/// Links die Liste der Kreaturen, rechts die aufgeschlagene Seite. Was
/// man noch nie gesehen hat, steht als Strich in der Liste; was man
/// gesehen, aber nicht oft genug erlegt hat, zeigt Bild und Namen und
/// sonst nichts. Erst wer oft genug mit einer Kreatur zu tun hatte,
/// bekommt den ganzen Text und die Zahlen.
///
/// Der Text kommt aus `Bestiarium` in der Kern-Bibliothek, die Zahlen
/// aus `EnemyKind`. Hier steht nichts, was anderswo auch stehen koennte -
/// diese Datei ordnet nur an.
public final class BestiariumNode: SKNode {
    private let atlas = AtlasStore.shared

    private var groesse: CGSize = .zero
    private var auswahl = 0
    private let liste = SKNode()
    private let seite = SKNode()

    /// Sichtbar? Solange das Bestiarium offen ist, laeuft das Spiel nicht.
    public private(set) var offen = false

    private static let bilder: [EnemyKind: String] = [
        .gabelmaus: "gabelmaus_husch_2",
        .klangmotte: "klangmotte_fly_1",
        .stilleschreiter: "stilleschreiter_walk_2",
        .dissonanzknospe: "dissonanzknospe_bloom_3",
        .echoscherbe: "echoscherbe_spin_1",
        .chorschatten: "chorschatten_haengt_2",
        .hallqualle: "hallqualle_treibt_2",
        .steinfink: "steinfink_hockt_2",
        .zerrmaul: "zerrmaul_schnappt_2",
        .taumler: "taumler_taumelt_2",
    ]

    public func build(in size: CGSize) {
        groesse = size
        zPosition = 900
        isHidden = true

        let schleier = SKSpriteNode(color: SKColor(white: 0.02, alpha: 0.94), size: size)
        schleier.zPosition = 0
        addChild(schleier)

        let titel = beschriftung("DIE BEWOHNER DER VERSTIMMTEN WELT", groesse: 9,
                                 farbe: SKColor(red: 0.91, green: 0.89, blue: 0.82, alpha: 1))
        titel.position = CGPoint(x: 0, y: size.height / 2 - 22)
        titel.zPosition = 2
        addChild(titel)

        liste.zPosition = 2
        liste.position = CGPoint(x: -size.width / 2 + 26, y: size.height / 2 - 52)
        addChild(liste)

        seite.zPosition = 2
        seite.position = CGPoint(x: -30, y: size.height / 2 - 52)
        addChild(seite)

        let fuss = beschriftung("W/S blaettern    B schliesst", groesse: 7,
                                farbe: SKColor(white: 0.55, alpha: 1))
        fuss.position = CGPoint(x: 0, y: -size.height / 2 + 16)
        fuss.zPosition = 2
        addChild(fuss)
    }

    // MARK: - Bedienung

    public func toggle(save: SaveState) {
        offen.toggle()
        isHidden = !offen
        if offen { zeichne(save: save) }
    }

    public func close() {
        offen = false
        isHidden = true
    }

    /// Wie viele Zeilen die Liste hat: Kreaturen, dann die Grossen.
    ///
    /// Beide stehen in derselben Liste und werden mit demselben Index
    /// durchgeblaettert - ein zweites Menue fuer zwei Eintraege waere
    /// mehr Bedienung als Inhalt. Was sie unterscheidet, ist die Regel,
    /// nach der sie aufgehen, und die steht im Bestiarium selbst.
    private var zeilen: Int { Bestiarium.eintraege.count + Bestiarium.grosse.count }

    /// Blaettern. Gibt zurueck, ob sich etwas geaendert hat.
    @discardableResult
    public func blaettern(_ richtung: Int, save: SaveState) -> Bool {
        guard offen, richtung != 0 else { return false }
        let anzahl = zeilen
        let neu = (auswahl + richtung + anzahl) % anzahl
        guard neu != auswahl else { return false }
        auswahl = neu
        zeichne(save: save)
        return true
    }

    // MARK: - Aufbau der Seite

    private func zeichne(save: SaveState) {
        liste.removeAllChildren()
        seite.removeAllChildren()

        let verstandenGross = Bestiarium.grosse.filter {
            Bestiarium.stand(fuer: $0.art, in: save) == .verstanden
        }.count
        let verstanden = Bestiarium.verstanden(in: save) + verstandenGross
        let zaehler = beschriftung("\(verstanden) / \(zeilen)",
                                   groesse: 7, farbe: SKColor(white: 0.5, alpha: 1),
                                   ausrichtung: .left)
        zaehler.position = CGPoint(x: 0, y: 0)
        liste.addChild(zaehler)

        for (i, eintrag) in Bestiarium.eintraege.enumerated() {
            let stand = Bestiarium.stand(fuer: eintrag.art, in: save)
            let gewaehlt = i == auswahl
            // Unbekanntes bleibt ein Strich. Man soll sehen, dass da noch
            // etwas fehlt, aber nicht, was.
            let text = stand == .unbekannt
                ? "- - - - -"
                : eintrag.name
            let farbe: SKColor
            switch stand {
            case .unbekannt: farbe = SKColor(white: 0.28, alpha: 1)
            case .gesehen: farbe = SKColor(white: 0.62, alpha: 1)
            case .verstanden: farbe = SKColor(red: 0.5, green: 0.91, blue: 0.85, alpha: 1)
            }
            let zeile = beschriftung((gewaehlt ? "> " : "  ") + text,
                                     groesse: 8, farbe: farbe, ausrichtung: .left)
            zeile.position = CGPoint(x: 0, y: -22 - CGFloat(i) * 14)
            liste.addChild(zeile)
        }

        // Die Grossen stehen unter einem Strich - sie gehen nach einer
        // anderen Regel auf, und das soll man der Liste ansehen.
        let trenner = SKSpriteNode(color: SKColor(white: 0.3, alpha: 1),
                                   size: CGSize(width: 96, height: 1))
        trenner.anchorPoint = CGPoint(x: 0, y: 0.5)
        trenner.position = CGPoint(
            x: 0, y: -24 - CGFloat(Bestiarium.eintraege.count) * 14)
        liste.addChild(trenner)

        for (k, gross) in Bestiarium.grosse.enumerated() {
            let i = Bestiarium.eintraege.count + k
            let stand = Bestiarium.stand(fuer: gross.art, in: save)
            let gewaehlt = i == auswahl
            let text = stand == .unbekannt ? "- - - - -" : gross.name
            let farbe: SKColor
            switch stand {
            case .unbekannt: farbe = SKColor(white: 0.28, alpha: 1)
            case .gesehen: farbe = SKColor(white: 0.62, alpha: 1)
            case .verstanden: farbe = SKColor(red: 0.94, green: 0.62, blue: 0.55, alpha: 1)
            }
            let zeile = beschriftung((gewaehlt ? "> " : "  ") + text,
                                     groesse: 8, farbe: farbe, ausrichtung: .left)
            zeile.position = CGPoint(x: 0, y: -30 - CGFloat(i) * 14)
            liste.addChild(zeile)
        }

        if auswahl >= Bestiarium.eintraege.count {
            zeichneGrossen(Bestiarium.grosse[auswahl - Bestiarium.eintraege.count],
                           save: save)
            return
        }

        let eintrag = Bestiarium.eintraege[auswahl]
        let stand = Bestiarium.stand(fuer: eintrag.art, in: save)
        guard stand != .unbekannt else {
            let hinweis = beschriftung("NOCH NICHT BEGEGNET", groesse: 8,
                                       farbe: SKColor(white: 0.34, alpha: 1),
                                       ausrichtung: .left)
            hinweis.position = CGPoint(x: 0, y: -60)
            seite.addChild(hinweis)
            return
        }

        if let name = Self.bilder[eintrag.art] {
            let bild = atlas.sprite(name)
            bild.setScale(2)
            bild.anchorPoint = CGPoint(x: 0, y: 1)
            bild.position = CGPoint(x: 0, y: -6)
            seite.addChild(bild)
        }

        let name = beschriftung(eintrag.name, groesse: 10,
                                farbe: SKColor(red: 0.5, green: 0.91, blue: 0.85, alpha: 1),
                                ausrichtung: .left)
        name.position = CGPoint(x: 70, y: -14)
        seite.addChild(name)

        // Zahlen erst, wenn man sie sich verdient hat.
        if stand == .verstanden {
            let werte = beschriftung(
                "Leben \(eintrag.maxHealth)     Schaden \(eintrag.schadenText)",
                groesse: 7, farbe: SKColor(white: 0.66, alpha: 1), ausrichtung: .left)
            werte.position = CGPoint(x: 70, y: -30)
            seite.addChild(werte)
        } else {
            let erlegt = save.erlegt[eintrag.art.rawValue] ?? 0
            let fehlt = beschriftung(
                "\(erlegt) von \(eintrag.schwelle) - noch nicht genug gesehen",
                groesse: 7, farbe: SKColor(white: 0.42, alpha: 1), ausrichtung: .left)
            fehlt.position = CGPoint(x: 70, y: -30)
            seite.addChild(fehlt)
        }

        var y: CGFloat = -74
        for zeile in eintrag.verhalten {
            let label = beschriftung(zeile, groesse: 7,
                                     farbe: SKColor(white: 0.74, alpha: 1),
                                     ausrichtung: .left)
            label.position = CGPoint(x: 0, y: y)
            seite.addChild(label)
            y -= 12
        }

        guard stand == .verstanden else { return }
        y -= 8
        for zeile in eintrag.deutung {
            let label = beschriftung(zeile, groesse: 7,
                                     farbe: SKColor(red: 0.78, green: 0.72, blue: 0.58,
                                                    alpha: 1),
                                     ausrichtung: .left)
            label.position = CGPoint(x: 0, y: y)
            seite.addChild(label)
            y -= 12
        }
    }

    /// Die Seite eines Bosses.
    ///
    /// Sie zeigt keine Zaehlung "2 von 4" - die gibt es hier nicht. Statt
    /// dessen steht da, ob er noch steht.
    private func zeichneGrossen(_ eintrag: Bestiarium.GrosserEintrag,
                                save: SaveState) {
        let stand = Bestiarium.stand(fuer: eintrag.art, in: save)
        guard stand != .unbekannt else {
            let hinweis = beschriftung("NOCH NICHT BEGEGNET", groesse: 8,
                                       farbe: SKColor(white: 0.34, alpha: 1),
                                       ausrichtung: .left)
            hinweis.position = CGPoint(x: 0, y: -60)
            seite.addChild(hinweis)
            return
        }

        let bild = atlas.sprite("\(eintrag.art.rawValue)_idle_2")
        bild.setScale(1.4)
        bild.anchorPoint = CGPoint(x: 0, y: 1)
        bild.position = CGPoint(x: 0, y: -6)
        seite.addChild(bild)

        let rot = SKColor(red: 0.94, green: 0.62, blue: 0.55, alpha: 1)
        let name = beschriftung(eintrag.name, groesse: 10, farbe: rot,
                                ausrichtung: .left)
        name.position = CGPoint(x: 92, y: -14)
        seite.addChild(name)

        let titel = beschriftung(eintrag.titel, groesse: 7,
                                 farbe: SKColor(white: 0.55, alpha: 1),
                                 ausrichtung: .left)
        titel.position = CGPoint(x: 92, y: -28)
        seite.addChild(titel)

        let zustand = stand == .verstanden
            ? "Leben \(eintrag.maxHealth)     ERLEGT"
            : "Leben \(eintrag.maxHealth)     STEHT NOCH"
        let werte = beschriftung(zustand, groesse: 7,
                                 farbe: SKColor(white: 0.66, alpha: 1),
                                 ausrichtung: .left)
        werte.position = CGPoint(x: 92, y: -44)
        seite.addChild(werte)

        var y: CGFloat = -92
        for zeile in eintrag.verhalten {
            let label = beschriftung(zeile, groesse: 7,
                                     farbe: SKColor(white: 0.74, alpha: 1),
                                     ausrichtung: .left)
            label.position = CGPoint(x: 0, y: y)
            seite.addChild(label)
            y -= 12
        }

        guard stand == .verstanden else { return }
        y -= 8
        for zeile in eintrag.deutung {
            let label = beschriftung(zeile, groesse: 7,
                                     farbe: SKColor(red: 0.78, green: 0.72, blue: 0.58,
                                                    alpha: 1),
                                     ausrichtung: .left)
            label.position = CGPoint(x: 0, y: y)
            seite.addChild(label)
            y -= 12
        }
    }

    private func beschriftung(_ text: String, groesse: CGFloat, farbe: SKColor,
                              ausrichtung: SKLabelHorizontalAlignmentMode = .center)
        -> SKLabelNode {
        let label = SKLabelNode(text: text)
        label.fontName = "Menlo"
        label.fontSize = groesse
        label.fontColor = farbe
        label.horizontalAlignmentMode = ausrichtung
        label.verticalAlignmentMode = .top
        return label
    }
}
#endif
