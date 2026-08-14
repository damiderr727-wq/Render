#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Die Anzeige: Notenherzen, Resonanzbogen, aktives Kern, Hinweise.
/// Sie haengt an der Kamera und bewegt sich deshalb nicht mit der Welt.
public final class HUDNode: SKNode {

    private let hearts = SKNode()
    private let resonanceBar = SKShapeNode()
    private let resonanceFill = SKShapeNode()
    private let kernLabel = SKLabelNode()
    private let equipmentLabel = SKLabelNode()
    private let promptLabel = SKLabelNode()
    private let hintLabel = SKLabelNode()
    private let loreBox = SKNode()
    private let loreLabel = SKLabelNode()
    private let titleLabel = SKLabelNode()
    private let subtitleLabel = SKLabelNode()
    private let bossBar = SKShapeNode()
    private let bossFill = SKShapeNode()
    private let bossLabel = SKLabelNode()

    private let kerben = SKNode()
    private let siegelLabel = SKLabelNode()
    // Der gefuehrte Kern als Bild seines Pulses - kein Text. Was man
    // schiesst, sieht man; wozu es einen Namen vorlesen.
    private let kernIcon = SKSpriteNode()
    private let kernRing = SKShapeNode()
    private var lastKern = ""
    private var heartNodes: [SKShapeNode] = []

    // Die Klangkette. Sie war bisher unsichtbar - und eine Kampffunktion,
    // die der Spieler nicht sieht, gibt es fuer ihn nicht.
    private let taktRing = SKShapeNode()
    private let taktKern = SKShapeNode()
    private let kettenGlieder = SKNode()
    private var gliedNodes: [SKShapeNode] = []
    private var letzteGlieder = -1
    private var lastKerbenBelegt = -1
    private var lastKerbenTotal = -1
    private var lastHealth = -1
    private var lastMaxHealth = -1

    private let font = "Menlo-Bold"
    private let glow = SKColor(red: 0.50, green: 0.91, blue: 0.85, alpha: 1)
    private let bloom = SKColor(red: 0.90, green: 0.70, blue: 1.00, alpha: 1)
    private let rot = SKColor(red: 0.76, green: 0.25, blue: 0.37, alpha: 1)

    public func build(in size: CGSize) {
        zPosition = 1000
        // Die Kamera sitzt in der Mitte; die Anzeige rechnet von dort aus.
        let left = -size.width / 2
        let top = size.height / 2

        hearts.position = CGPoint(x: left + 10, y: top - 14)
        addChild(hearts)

        resonanceBar.path = CGPath(roundedRect: CGRect(x: 0, y: 0, width: 64, height: 5),
                                   cornerWidth: 2, cornerHeight: 2, transform: nil)
        resonanceBar.strokeColor = SKColor(white: 1, alpha: 0.25)
        resonanceBar.fillColor = SKColor(white: 0, alpha: 0.35)
        resonanceBar.lineWidth = 1
        resonanceBar.position = CGPoint(x: left + 10, y: top - 28)
        addChild(resonanceBar)

        resonanceFill.fillColor = glow
        resonanceFill.strokeColor = .clear
        resonanceFill.position = resonanceBar.position
        addChild(resonanceFill)

        // Der Taktgeber. Ein Ring, in dem ein Kern auf jeden Schlag
        // aufblitzt - man muss ihn nicht ansehen, um ihn wahrzunehmen,
        // und genau so soll er wirken: als Puls im Augenwinkel.
        taktRing.path = CGPath(ellipseIn: CGRect(x: -7, y: -7, width: 14, height: 14),
                               transform: nil)
        taktRing.strokeColor = SKColor(white: 1, alpha: 0.22)
        taktRing.fillColor = .clear
        taktRing.lineWidth = 1
        taktRing.position = CGPoint(x: left + 84, y: top - 26)
        addChild(taktRing)

        taktKern.path = CGPath(ellipseIn: CGRect(x: -4, y: -4, width: 8, height: 8),
                               transform: nil)
        taktKern.strokeColor = .clear
        taktKern.fillColor = glow
        taktKern.position = taktRing.position
        addChild(taktKern)

        // Vier Glieder daneben. Sie fuellen sich, sie leeren sich - mehr
        // muss die Kette nicht erzaehlen.
        kettenGlieder.position = CGPoint(x: left + 98, y: top - 26)
        addChild(kettenGlieder)
        for i in 0..<4 {
            let glied = SKShapeNode(rectOf: CGSize(width: 4, height: 4), cornerRadius: 1)
            glied.position = CGPoint(x: CGFloat(i) * 7, y: 0)
            glied.strokeColor = SKColor(white: 1, alpha: 0.22)
            glied.fillColor = .clear
            glied.lineWidth = 1
            kettenGlieder.addChild(glied)
            gliedNodes.append(glied)
        }

        // Der Kern: ein Ring, darin das Bild seines Pulses.
        kernRing.path = CGPath(ellipseIn: CGRect(x: -9, y: -9, width: 18, height: 18),
                               transform: nil)
        kernRing.strokeColor = SKColor(white: 1, alpha: 0.28)
        kernRing.fillColor = SKColor(white: 0, alpha: 0.30)
        kernRing.lineWidth = 1
        kernRing.position = CGPoint(x: left + 19, y: top - 47)
        addChild(kernRing)
        kernIcon.position = kernRing.position
        addChild(kernIcon)

        // Die Kerbenpunkte daneben, auf derselben Zeile.
        kerben.position = CGPoint(x: left + 36, y: top - 47)
        addChild(kerben)

        // Nur im Bruch traegt das HUD noch ein Wort.
        style(kernLabel, size: 8, color: rot)
        kernLabel.horizontalAlignmentMode = .left
        kernLabel.position = CGPoint(x: left + 36, y: top - 47)
        kernLabel.alpha = 0
        addChild(kernLabel)

        // Fassung und Siegel mit Namen: nur an der Stimmgabel, wo man
        // sie wechseln kann. Im Spiel sind sie Daueranzeige gewesen -
        // zwei Zeilen Text, die niemand liest und jeder sieht.
        style(equipmentLabel, size: 6, color: SKColor(white: 0.62, alpha: 1))
        equipmentLabel.horizontalAlignmentMode = .left
        equipmentLabel.position = CGPoint(x: left + 10, y: top - 64)
        equipmentLabel.alpha = 0
        addChild(equipmentLabel)

        style(siegelLabel, size: 5, color: bloom)
        siegelLabel.horizontalAlignmentMode = .left
        siegelLabel.position = CGPoint(x: left + 10, y: top - 74)
        siegelLabel.alpha = 0
        addChild(siegelLabel)

        style(promptLabel, size: 7, color: SKColor(white: 0.85, alpha: 1))
        promptLabel.position = CGPoint(x: 0, y: -size.height / 2 + 28)
        addChild(promptLabel)

        style(hintLabel, size: 8, color: bloom)
        hintLabel.position = CGPoint(x: 0, y: -size.height / 2 + 46)
        hintLabel.alpha = 0
        addChild(hintLabel)

        // Inschriften
        let backdrop = SKShapeNode(rectOf: CGSize(width: size.width - 60, height: 46),
                                   cornerRadius: 3)
        backdrop.fillColor = SKColor(white: 0.02, alpha: 0.82)
        backdrop.strokeColor = SKColor(white: 1, alpha: 0.14)
        backdrop.lineWidth = 1
        loreBox.addChild(backdrop)
        style(loreLabel, size: 7, color: SKColor(white: 0.82, alpha: 1))
        loreLabel.numberOfLines = 3
        loreLabel.preferredMaxLayoutWidth = size.width - 76
        loreLabel.verticalAlignmentMode = .center
        loreBox.addChild(loreLabel)
        loreBox.position = CGPoint(x: 0, y: -size.height / 2 + 62)
        loreBox.alpha = 0
        addChild(loreBox)

        style(titleLabel, size: 14, color: SKColor(white: 0.95, alpha: 1))
        titleLabel.position = CGPoint(x: 0, y: 18)
        titleLabel.alpha = 0
        addChild(titleLabel)

        style(subtitleLabel, size: 7, color: glow)
        subtitleLabel.position = CGPoint(x: 0, y: 2)
        subtitleLabel.alpha = 0
        addChild(subtitleLabel)

        // Bossleiste
        bossBar.path = CGPath(rect: CGRect(x: -110, y: 0, width: 220, height: 3), transform: nil)
        bossBar.strokeColor = SKColor(white: 1, alpha: 0.3)
        bossBar.fillColor = SKColor(white: 0, alpha: 0.4)
        bossBar.lineWidth = 1
        bossBar.position = CGPoint(x: 0, y: -size.height / 2 + 16)
        bossBar.alpha = 0
        addChild(bossBar)

        bossFill.fillColor = rot
        bossFill.strokeColor = .clear
        bossFill.position = bossBar.position
        bossFill.alpha = 0
        addChild(bossFill)

        style(bossLabel, size: 7, color: rot)
        bossLabel.position = CGPoint(x: 0, y: -size.height / 2 + 24)
        bossLabel.alpha = 0
        addChild(bossLabel)
    }

    private func style(_ label: SKLabelNode, size: CGFloat, color: SKColor) {
        label.fontName = font
        label.fontSize = size
        label.fontColor = color
        label.horizontalAlignmentMode = .center
        label.verticalAlignmentMode = .center
    }

    // MARK: - Bild pro Bild

    public func update(sim: GameSimulation, dt: Double) {
        // Der Zusammenhalt der Fassung bestimmt die Herzen, nicht der Grundwert.
        updateHearts(health: sim.player.health, max: sim.player.maxHealth)

        let fraction = sim.player.resonance / max(1, sim.save.progression.maxResonance)
        resonanceFill.path = CGPath(roundedRect: CGRect(x: 1, y: 1,
                                                        width: max(0, 62 * fraction), height: 3),
                                    cornerWidth: 1, cornerHeight: 1, transform: nil)
        resonanceFill.fillColor = fraction < 0.2 ? rot : glow

        updateTakt(sim: sim)
        updateKerben(progression: sim.save.progression)
        if sim.save.progression.gebrochen {
            // Im Bruch zaehlt nur noch eins: dass nichts mehr haelt.
            kernLabel.text = "ENTFESSELT"
            kernLabel.alpha = 1
            kernIcon.alpha = 0
            kernRing.strokeColor = rot
        } else if sim.player.kern.rawValue != lastKern {
            lastKern = sim.player.kern.rawValue
            kernLabel.alpha = 0
            if let info = AtlasStore.shared.frame("note_\(lastKern)") {
                kernIcon.texture = info.texture
                kernIcon.size = info.size
                kernIcon.alpha = 1
                kernIcon.run(.sequence([.scale(to: 1.5, duration: 0.07),
                                        .scale(to: 1.0, duration: 0.14)]))
            }
        }
        let fassung = sim.save.progression.equipment
        equipmentLabel.text = sim.save.progression.gebrochen
            ? "SIE ZERSTREUT SICH"
            : "\(fassung.name)  \(fassung.openings) OEFFNUNGEN"
        // Namen nur dort, wo man handeln kann: an der Stimmgabel.
        let zeigeText: CGFloat = sim.player.isResting ? 1 : 0
        if equipmentLabel.alpha != zeigeText {
            equipmentLabel.run(.fadeAlpha(to: zeigeText, duration: 0.25))
            siegelLabel.run(.fadeAlpha(to: zeigeText, duration: 0.25))
        }

        // An der Stimmgabel darf sie sich neu fassen - nur dort.
        if sim.player.isResting {
            var teile = ["[F] AUFBRECHEN"]
            if sim.save.progression.ownedEquipment.count > 1 {
                teile.append("[,] [.] FASSUNG")
            }
            if !sim.save.progression.ownedSiegel.isEmpty {
                teile.append("[4]-[9] SIEGEL")
            }
            promptLabel.text = teile.joined(separator: "     ")
        } else {
            switch sim.prompt {
            case .none:
                promptLabel.text = ""
            case .bench:
                promptLabel.text = "[F] AUSRUHEN UND STIMMEN"
            case .lore:
                promptLabel.text = "[F] LESEN"
            case .gate(let ability):
                promptLabel.text = "HIER FEHLT: \(ability.displayName)"
            case .npc:
                promptLabel.text = "[F] ANSPRECHEN"
            case .haendler:
                promptLabel.text = "[F] HANDELN"
            }
        }

        if let boss = sim.boss, boss.alive, boss.action != .entrance {
            bossBar.alpha = 1
            bossFill.alpha = 1
            bossLabel.alpha = 1
            bossLabel.text = boss.art.zaehltSaetze
                ? "\(boss.art.displayName) - SATZ \(boss.phase.rawValue)"
                : boss.art.displayName
            bossFill.path = CGPath(rect: CGRect(x: -109, y: 1,
                                                width: max(0, 218 * boss.healthFraction),
                                                height: 1),
                                   transform: nil)
        } else if bossBar.alpha > 0 {
            for node in [bossBar, bossFill, bossLabel] as [SKNode] {
                node.run(.fadeOut(withDuration: 0.6))
            }
        }
    }

    /// Lebenskristalle. Gerechnet wird in Haelften, gezeigt werden ganze
    /// Kristalle - jeder kann voll, halb oder leer sein. Ein halber ist
    /// nicht bloss Zierde: mancher Schlag nimmt anderthalb, und auf einem
    /// halben Kristall ueberlebt sie nichts mehr.
    /// Puls und Kette.
    ///
    /// Der Kern im Ring ist genau auf dem Schlag am groessten und am
    /// hellsten und faellt dazwischen ab - kein Blinken, sondern ein
    /// Atmen. Ein hartes An/Aus liest sich als Fehler, ein Verlauf als
    /// Rhythmus.
    private func updateTakt(sim: GameSimulation) {
        // `puls` ist 0 auf dem Schlag und 1 genau dazwischen.
        let naehe = 1 - sim.takt.puls(sim.elapsed)
        let staerke = pow(max(0, naehe), 2.6)
        taktKern.setScale(0.45 + staerke * 0.75)
        taktKern.alpha = 0.25 + staerke * 0.75

        // Voll aufgebaut faerbt sich der Puls um: man sieht am Rand des
        // Blicks, dass man oben ist.
        let farbe = sim.kette.voll ? bloom : glow
        taktKern.fillColor = farbe
        taktRing.strokeColor = SKColor(white: 1, alpha: sim.kette.voll ? 0.45 : 0.22)

        guard sim.kette.glieder != letzteGlieder else { return }
        letzteGlieder = sim.kette.glieder
        for (i, glied) in gliedNodes.enumerated() {
            let an = i < sim.kette.glieder
            glied.fillColor = an ? farbe : .clear
            glied.strokeColor = an ? farbe : SKColor(white: 1, alpha: 0.22)
            if an {
                // Jedes neue Glied setzt sich kurz durch, statt einfach
                // da zu sein.
                glied.removeAllActions()
                glied.run(.sequence([.scale(to: 1.6, duration: 0.06),
                                     .scale(to: 1.0, duration: 0.12)]))
            }
        }
    }

    private func updateHearts(health: Int, max maxHealth: Int) {
        guard health != lastHealth || maxHealth != lastMaxHealth else { return }
        let verloren = health < lastHealth
        lastHealth = health
        lastMaxHealth = maxHealth

        let kristalle = (maxHealth + 1) / 2
        if heartNodes.count != kristalle * 2 {
            hearts.removeAllChildren()
            heartNodes = (0..<(kristalle * 2)).map { index in
                // Jeder Kristall besteht aus zwei Haelften, die nebeneinander
                // liegen - so ist der halbe Stand ohne Zahl ablesbar.
                let links = index % 2 == 0
                let path = CGMutablePath()
                let w: CGFloat = 3.4, h: CGFloat = 5.5
                if links {
                    path.move(to: CGPoint(x: w, y: h))
                    path.addLine(to: CGPoint(x: 0, y: 0))
                    path.addLine(to: CGPoint(x: w, y: -h))
                } else {
                    path.move(to: CGPoint(x: 0, y: h))
                    path.addLine(to: CGPoint(x: w, y: 0))
                    path.addLine(to: CGPoint(x: 0, y: -h))
                }
                path.closeSubpath()
                let node = SKShapeNode(path: path)
                node.position = CGPoint(x: CGFloat(index / 2) * 11
                                          + (links ? 0 : 3.9), y: 0)
                node.lineWidth = 1
                hearts.addChild(node)
                return node
            }
        }

        for (index, node) in heartNodes.enumerated() {
            let voll = index < health
            node.fillColor = voll ? SKColor(white: 0.95, alpha: 1) : SKColor(white: 1, alpha: 0.07)
            node.strokeColor = voll ? glow : SKColor(white: 1, alpha: 0.22)
            if verloren && index >= health && index < lastHealth + 3 {
                node.run(.sequence([.scale(to: 1.7, duration: 0.08),
                                    .scale(to: 1.0, duration: 0.18)]))
            }
        }
    }

    /// Die Kerbenleiste: belegte und freie Kerben, dahinter die angelegten
    /// Siegel. Man sieht auf einen Blick, was man traegt und was noch ginge.
    private func updateKerben(progression: Progression) {
        let belegt = progression.kerbenBelegt
        let gesamt = progression.kerbenTotal
        guard belegt != lastKerbenBelegt || gesamt != lastKerbenTotal else { return }
        lastKerbenBelegt = belegt
        lastKerbenTotal = gesamt

        kerben.removeAllChildren()
        for i in 0..<gesamt {
            let node = SKShapeNode(circleOfRadius: 2.2)
            node.position = CGPoint(x: CGFloat(i) * 7, y: 0)
            node.lineWidth = 1
            node.fillColor = i < belegt ? bloom : SKColor(white: 1, alpha: 0.06)
            node.strokeColor = i < belegt ? bloom : SKColor(white: 1, alpha: 0.22)
            kerben.addChild(node)
        }
        siegelLabel.text = progression.siegel.map(\.name).joined(separator: "  ")
    }

    // MARK: - Einblendungen

    public func showRoomTitle(_ name: String, region: String) {
        titleLabel.fontSize = 11
        titleLabel.text = name
        subtitleLabel.text = region
        for label in [titleLabel, subtitleLabel] {
            label.removeAllActions()
            label.alpha = 0
            label.run(.sequence([
                .fadeIn(withDuration: 0.6),
                .wait(forDuration: 1.8),
                .fadeOut(withDuration: 0.9),
            ]))
        }
    }

    public func announce(_ title: String, subtitle: String, lore: String? = nil) {
        titleLabel.fontSize = 14
        titleLabel.text = title
        subtitleLabel.text = subtitle
        for label in [titleLabel, subtitleLabel] {
            label.removeAllActions()
            label.alpha = 0
            label.run(.sequence([
                .fadeIn(withDuration: 0.4),
                .wait(forDuration: 2.6),
                .fadeOut(withDuration: 0.8),
            ]))
        }
        if let lore { showLore(lore, duration: 4.0) }
    }

    public func showLore(_ text: String, duration: Double = 5.0) {
        loreLabel.text = text
        loreBox.removeAllActions()
        loreBox.alpha = 0
        loreBox.run(.sequence([
            .fadeIn(withDuration: 0.35),
            .wait(forDuration: duration),
            .fadeOut(withDuration: 0.6),
        ]))
    }

    public func showHint(_ text: String) {
        hintLabel.text = text
        hintLabel.removeAllActions()
        hintLabel.alpha = 0
        hintLabel.run(.sequence([
            .fadeIn(withDuration: 0.25),
            .wait(forDuration: 1.6),
            .fadeOut(withDuration: 0.5),
        ]))
    }

    public func flashKern() {
        kernLabel.removeAllActions()
        kernLabel.run(.sequence([
            .scale(to: 1.4, duration: 0.07),
            .scale(to: 1.0, duration: 0.14),
        ]))
    }
}
#endif
