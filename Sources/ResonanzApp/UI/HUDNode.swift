#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Die Anzeige: Notenherzen, Resonanzbogen, aktives Instrument, Hinweise.
/// Sie haengt an der Kamera und bewegt sich deshalb nicht mit der Welt.
public final class HUDNode: SKNode {

    private let hearts = SKNode()
    private let resonanceBar = SKShapeNode()
    private let resonanceFill = SKShapeNode()
    private let instrumentLabel = SKLabelNode()
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

    private var heartNodes: [SKShapeNode] = []
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

        resonanceBar.path = CGPath(roundedRect: CGRect(x: 0, y: 0, width: 64, height: 4),
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

        style(instrumentLabel, size: 8, color: glow)
        instrumentLabel.horizontalAlignmentMode = .left
        instrumentLabel.position = CGPoint(x: left + 10, y: top - 42)
        addChild(instrumentLabel)

        style(equipmentLabel, size: 6, color: SKColor(white: 0.62, alpha: 1))
        equipmentLabel.horizontalAlignmentMode = .left
        equipmentLabel.position = CGPoint(x: left + 10, y: top - 52)
        addChild(equipmentLabel)

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
                                                        width: max(0, 62 * fraction), height: 2),
                                    cornerWidth: 1, cornerHeight: 1, transform: nil)
        resonanceFill.fillColor = fraction < 0.2 ? rot : glow

        instrumentLabel.text = sim.player.instrument.displayName
        let fassung = sim.save.progression.equipment
        equipmentLabel.text = "\(fassung.name)  \(fassung.openings) OEFFNUNGEN"

        // An der Stimmgabel darf sie sich neu fassen - nur dort.
        if sim.player.isResting {
            promptLabel.text = sim.save.progression.ownedEquipment.count > 1
                ? "[F] AUFBRECHEN     [,] [.] FASSUNG WECHSELN"
                : "[F] AUFBRECHEN"
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
            }
        }

        if let boss = sim.boss, boss.alive, boss.action != .entrance {
            bossBar.alpha = 1
            bossFill.alpha = 1
            bossLabel.alpha = 1
            bossLabel.text = "DER VERSTIMMTE KANTOR - SATZ \(boss.phase.rawValue)"
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

    private func updateHearts(health: Int, max maxHealth: Int) {
        guard health != lastHealth || maxHealth != lastMaxHealth else { return }
        let verloren = health < lastHealth
        lastHealth = health
        lastMaxHealth = maxHealth

        if heartNodes.count != maxHealth {
            hearts.removeAllChildren()
            heartNodes = (0..<maxHealth).map { index in
                // Ein Notenkopf als Lebenszeichen.
                let node = SKShapeNode(ellipseOf: CGSize(width: 7, height: 5))
                node.position = CGPoint(x: CGFloat(index) * 10, y: 0)
                node.lineWidth = 1
                hearts.addChild(node)
                return node
            }
        }

        for (index, node) in heartNodes.enumerated() {
            let voll = index < health
            node.fillColor = voll ? SKColor(white: 0.95, alpha: 1) : SKColor(white: 1, alpha: 0.08)
            node.strokeColor = voll ? glow : SKColor(white: 1, alpha: 0.25)
            if verloren && index == health {
                node.run(.sequence([.scale(to: 1.8, duration: 0.08),
                                    .scale(to: 1.0, duration: 0.18)]))
            }
        }
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

    public func flashInstrument() {
        instrumentLabel.removeAllActions()
        instrumentLabel.run(.sequence([
            .scale(to: 1.4, duration: 0.07),
            .scale(to: 1.0, duration: 0.14),
        ]))
    }
}
#endif
