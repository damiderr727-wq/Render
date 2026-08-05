#if canImport(SpriteKit)
import Foundation
import SpriteKit
import PixelRogueCore

/// The heads-up display: health, ammo, consumables, weapon slots, minimap,
/// boss bar and the transient banners.
///
/// It lives under the camera, so it is drawn in screen space and never
/// scrolls. Everything is laid out from the screen corners rather than from
/// the centre, so a resized window rearranges instead of clipping.
final class HUD {
    let root = SKNode()

    private let atlas: Atlas
    private let font: BitmapFont

    private let healthRow = SKNode()
    private let consumableRow = SKNode()
    private let weaponPanel = SKNode()
    private let itemRow = SKNode()
    private let minimap = SKNode()
    private let bossBar = SKNode()
    private let bannerLayer = SKNode()

    private let ammoText: TextNode
    private let weaponName: TextNode
    private let coinText: TextNode
    private let keyText: TextNode
    private let blankText: TextNode
    private let depthText: TextNode
    private let interactPrompt: TextNode
    private var bossFill: SKSpriteNode?
    private var bossName: TextNode?

    private var heartNodes: [SKSpriteNode] = []
    private var armorNodes: [SKSpriteNode] = []
    private var itemNodes: [String: SKSpriteNode] = [:]
    private var minimapCells: [Int: SKSpriteNode] = [:]
    private var size: CGSize = .zero

    private var reloadBar: SKSpriteNode?
    private var reloadFrame: SKSpriteNode?
    /// Which weapons the slot row was last built for. Rebuilding it every
    /// frame would churn a dozen nodes for a row that changes once a minute.
    private var weaponSignature = ""

    static let gold = SKColor(red: 1.0, green: 0.85, blue: 0.36, alpha: 1)
    static let pale = SKColor(red: 0.86, green: 0.87, blue: 0.94, alpha: 1)
    static let danger = SKColor(red: 1.0, green: 0.42, blue: 0.38, alpha: 1)

    init(atlas: Atlas, font: BitmapFont) {
        self.atlas = atlas
        self.font = font
        ammoText = TextNode(font: font, color: Self.gold, align: .right)
        weaponName = TextNode(font: font, color: Self.pale, align: .right)
        coinText = TextNode(font: font, color: Self.gold)
        keyText = TextNode(font: font, color: Self.pale)
        blankText = TextNode(font: font, color: Self.pale)
        depthText = TextNode(font: font, color: Self.pale, align: .center)
        interactPrompt = TextNode(font: font, color: Self.gold, align: .center)

        for node in [healthRow, consumableRow, weaponPanel, itemRow, minimap,
                     bossBar, bannerLayer] {
            root.addChild(node)
        }
        weaponPanel.addChild(ammoText)
        weaponPanel.addChild(weaponName)
        consumableRow.addChild(coinText)
        consumableRow.addChild(keyText)
        consumableRow.addChild(blankText)
        root.addChild(depthText)
        root.addChild(interactPrompt)
        root.zPosition = 100_000
        bossBar.isHidden = true
    }

    // -- layout ---------------------------------------------------------------

    func layout(for size: CGSize) {
        guard size != self.size else { return }
        self.size = size
        let left = -size.width / 2
        let right = size.width / 2
        let top = size.height / 2
        let bottom = -size.height / 2
        let margin: CGFloat = 14

        healthRow.position = CGPoint(x: left + margin, y: top - margin - 12)
        consumableRow.position = CGPoint(x: left + margin, y: top - margin - 42)
        itemRow.position = CGPoint(x: left + margin, y: bottom + margin + 10)
        weaponPanel.position = CGPoint(x: right - margin, y: bottom + margin + 46)
        minimap.position = CGPoint(x: right - margin - 70, y: top - margin - 60)
        bossBar.position = CGPoint(x: 0, y: top - margin - 20)
        bannerLayer.position = CGPoint(x: 0, y: 60)
        depthText.position = CGPoint(x: 0, y: top - margin - 12)
        interactPrompt.position = CGPoint(x: 0, y: bottom + 120)

        ammoText.position = CGPoint(x: 0, y: 0)
        weaponName.position = CGPoint(x: 0, y: 16)
        coinText.position = CGPoint(x: 20, y: 0)
        keyText.position = CGPoint(x: 90, y: 0)
        blankText.position = CGPoint(x: 150, y: 0)
    }

    // -- per-frame ------------------------------------------------------------

    func update(world: World) {
        let run = world.run
        updateHealth(run: run)
        updateConsumables(run: run)
        updateWeapon(world: world)
        updateItems(run: run)
        updateMinimap(world: world)
        updateBoss(world: world)

        depthText.text = "DEPTH \(run.depth)  -  \(themeName(run.theme))"

        if let target = world.player.interactTarget,
           let pickup = world.pickups.first(where: { $0.id == target }) {
            interactPrompt.text = pickup.price > 0
                ? "[E]  BUY \(pickup.label.uppercased())  -  \(pickup.price)"
                : "[E]  TAKE \(pickup.label.uppercased())"
            interactPrompt.isHidden = false
        } else {
            interactPrompt.isHidden = true
        }
    }

    private func themeName(_ theme: String) -> String {
        switch theme {
        case "keep": return "THE UNDERKEEP"
        case "crypt": return "THE BONE CRYPT"
        case "foundry": return "THE FOUNDRY"
        default: return "THE SANCTUM"
        }
    }

    private func updateHealth(run: RunState) {
        // Hearts are worth 20 health, matching the pickup value, so a heart
        // pickup visibly fills exactly one heart.
        let perHeart = 20.0
        let total = Int(ceil(run.maxHealth / perHeart))

        while heartNodes.count < total {
            let node = SKSpriteNode(frame: atlas.frame("ui/heart_full"))
            node.anchorPoint = CGPoint(x: 0, y: 0.5)
            node.position = CGPoint(x: CGFloat(heartNodes.count) * 16, y: 0)
            healthRow.addChild(node)
            heartNodes.append(node)
        }
        while heartNodes.count > total {
            heartNodes.removeLast().removeFromParent()
        }

        for (index, node) in heartNodes.enumerated() {
            let filled = run.health - Double(index) * perHeart
            let name = filled >= perHeart * 0.75 ? "ui/heart_full"
                : (filled > 0 ? "ui/heart_half" : "ui/heart_empty")
            node.apply(atlas.frame(name))
        }

        while armorNodes.count < run.armor {
            let node = SKSpriteNode(frame: atlas.frame("ui/armor_ui"))
            node.anchorPoint = CGPoint(x: 0, y: 0.5)
            armorNodes.append(node)
            healthRow.addChild(node)
        }
        while armorNodes.count > max(0, run.armor) {
            armorNodes.removeLast().removeFromParent()
        }
        for (index, node) in armorNodes.enumerated() {
            node.position = CGPoint(x: CGFloat(total) * 16 + 8 + CGFloat(index) * 15,
                                    y: 0)
        }
    }

    private func updateConsumables(run: RunState) {
        if consumableRow.childNode(withName: "coinIcon") == nil {
            for (name, x) in [("coin_icon", CGFloat(4)), ("key_icon", 74),
                              ("blank_icon", 134)] {
                let icon = SKSpriteNode(frame: atlas.frame("ui/\(name)"))
                icon.name = name == "coin_icon" ? "coinIcon" : name
                icon.position = CGPoint(x: x, y: 0)
                consumableRow.addChild(icon)
            }
        }
        coinText.text = "\(run.coins)"
        keyText.text = "\(run.keys)"
        blankText.text = "\(run.blanks)"
    }

    private func updateWeapon(world: World) {
        let loadout = world.run.loadout
        guard let active = loadout.activeWeapon else { return }
        weaponName.text = active.def.name.uppercased()
        ammoText.text = active.ammoText

        // Weapon slots, rebuilt only when the carried set changes.
        let signature = loadout.weapons.map(\.def.id).joined(separator: ",")
            + "|\(loadout.activeWeaponIndex)"
        if weaponSignature != signature {
            weaponSignature = signature
            weaponPanel.children
                .filter { $0.name == "slot" }
                .forEach { $0.removeFromParent() }

            for (index, weapon) in loadout.weapons.enumerated() {
                let slot = SKSpriteNode(frame: atlas.frame(
                    index == loadout.activeWeaponIndex ? "ui/slot_active" : "ui/slot"))
                slot.name = "slot"
                slot.position = CGPoint(
                    x: -CGFloat(loadout.weapons.count - index - 1) * 26 - 12, y: 42)
                weaponPanel.addChild(slot)

                let icon = SKSpriteNode(frame: atlas.frame(weapon.def.sprite))
                icon.setScale(0.62)
                icon.position = .zero
                slot.addChild(icon)
            }
        }

        // Reload progress under the ammo counter.
        if active.isReloading {
            if reloadFrame == nil {
                let frameNode = SKSpriteNode(frame: atlas.frame("ui/bar_frame"))
                frameNode.anchorPoint = CGPoint(x: 1, y: 0.5)
                frameNode.position = CGPoint(x: 0, y: -14)
                weaponPanel.addChild(frameNode)
                reloadFrame = frameNode

                let fill = SKSpriteNode(frame: atlas.frame("ui/bar_fill_charge"))
                fill.anchorPoint = CGPoint(x: 0, y: 0.5)
                fill.position = CGPoint(x: -60, y: -14)
                weaponPanel.addChild(fill)
                reloadBar = fill
            }
            let progress = 1 - (active.reloadRemaining /
                                max(0.05, active.def.reloadTime))
            reloadBar?.xScale = max(0.02, CGFloat(progress))
            reloadFrame?.isHidden = false
            reloadBar?.isHidden = false
        } else {
            reloadFrame?.isHidden = true
            reloadBar?.isHidden = true
        }
    }

    private func updateItems(run: RunState) {
        let owned = run.loadout.items
        for (index, id) in owned.enumerated() {
            if itemNodes[id] == nil {
                let node = SKSpriteNode(frame: atlas.frame("item/\(id)"))
                node.setScale(0.75)
                itemRow.addChild(node)
                itemNodes[id] = node
            }
            itemNodes[id]?.position = CGPoint(x: CGFloat(index % 14) * 16 + 8,
                                              y: CGFloat(index / 14) * 16)
        }
        for (id, node) in itemNodes where !owned.contains(id) {
            node.removeFromParent()
            itemNodes.removeValue(forKey: id)
        }
    }

    private func updateMinimap(world: World) {
        let cell = CGSize(width: 13, height: 11)
        // Centre the map on the room you are in, so it never wanders off the
        // panel on a wide floor.
        let current = world.dungeon.rooms[world.currentRoom].cells[0]

        for room in world.dungeon.rooms {
            guard room.discovered else {
                minimapCells[room.index]?.isHidden = true
                continue
            }
            let node: SKSpriteNode
            if let existing = minimapCells[room.index] {
                node = existing
            } else {
                node = SKSpriteNode(frame: atlas.frame("ui/minimap_normal"))
                minimap.addChild(node)
                minimapCells[room.index] = node
            }
            node.isHidden = false

            let key: String
            if room.index == world.currentRoom {
                key = "current"
            } else if !room.visited {
                key = room.kind == .combat ? "unknown" : room.kind.minimapKey
            } else if room.cleared && room.kind == .combat {
                key = "cleared"
            } else {
                key = room.kind.minimapKey
            }
            node.apply(atlas.frame("ui/minimap_\(key)"))
            node.position = CGPoint(
                x: CGFloat(room.cells[0].x - current.x) * cell.width,
                y: -CGFloat(room.cells[0].y - current.y) * cell.height)
            node.alpha = room.visited ? 1 : 0.55
        }
    }

    private func updateBoss(world: World) {
        guard let boss = world.activeBoss, case let .boss(id) = boss.kind,
              let def = BossCatalog.boss(id) else {
            bossBar.isHidden = true
            return
        }
        bossBar.isHidden = false

        if bossFill == nil {
            let frameNode = SKSpriteNode(frame: atlas.frame("ui/boss_bar_frame"))
            bossBar.addChild(frameNode)

            let fill = SKSpriteNode(frame: atlas.frame("ui/bar_fill_boss"))
            fill.anchorPoint = CGPoint(x: 0, y: 0.5)
            fill.position = CGPoint(x: -78, y: 0)
            bossBar.addChild(fill)
            bossFill = fill

            let label = TextNode(font: font, color: Self.pale, align: .center)
            label.position = CGPoint(x: 0, y: 20)
            bossBar.addChild(label)
            bossName = label
        }
        bossFill?.xScale = max(0.001, CGFloat(boss.healthFraction))
        bossName?.text = "\(def.name.uppercased())  -  \(def.title.uppercased())"
    }

    // -- banners --------------------------------------------------------------

    /// Big centred announcement: boss names, phase changes, floor titles.
    func announce(_ text: String, color: SKColor = HUD.gold) {
        let node = font.node(text.uppercased(), color: color, align: .center)
        node.setScale(2)
        node.position = CGPoint(x: 0, y: 0)
        node.alpha = 0
        bannerLayer.addChild(node)
        node.run(.sequence([
            .group([.fadeIn(withDuration: 0.15), .moveBy(x: 0, y: 12, duration: 0.4)]),
            .wait(forDuration: 1.4),
            .group([.fadeOut(withDuration: 0.4), .moveBy(x: 0, y: 10, duration: 0.4)]),
            .removeFromParent(),
        ]))
    }

    /// Synergy toast: the moment a build comes together deserves its own card.
    func announceSynergy(name: String, summary: String) {
        let card = SKNode()
        let panel = SKSpriteNode(frame: atlas.frame("ui/panel"))
        panel.centerRect = CGRect(x: 8.0 / 24, y: 8.0 / 24,
                                  width: 8.0 / 24, height: 8.0 / 24)
        panel.size = CGSize(width: 300, height: 62)
        card.addChild(panel)

        let title = font.node("SYNERGY  -  \(name.uppercased())",
                              color: SKColor(red: 1, green: 0.9, blue: 0.4, alpha: 1),
                              align: .center)
        title.position = CGPoint(x: 0, y: 18)
        card.addChild(title)

        let body = font.paragraph(summary, color: Self.pale, maxWidth: 270,
                                  align: .center)
        body.position = CGPoint(x: 0, y: 2)
        card.addChild(body)

        card.position = CGPoint(x: 0, y: -40)
        card.alpha = 0
        card.setScale(0.9)
        bannerLayer.addChild(card)
        card.run(.sequence([
            .group([.fadeIn(withDuration: 0.18),
                    .scale(to: 1, duration: 0.22),
                    .moveBy(x: 0, y: 20, duration: 0.3)]),
            .wait(forDuration: 2.6),
            .group([.fadeOut(withDuration: 0.4), .moveBy(x: 0, y: 14, duration: 0.4)]),
            .removeFromParent(),
        ]))
    }

    /// Small corner note: pickups, refusals, hints.
    func notice(_ text: String, sprite: String? = nil) {
        let row = SKNode()
        var x: CGFloat = 0
        if let sprite {
            let icon = SKSpriteNode(frame: atlas.frame(sprite))
            icon.setScale(0.8)
            icon.position = CGPoint(x: 8, y: 0)
            row.addChild(icon)
            x = 22
        }
        let label = font.node(text, color: Self.pale)
        label.position = CGPoint(x: x, y: 5)
        row.addChild(label)

        row.position = CGPoint(x: -size.width / 2 + 20, y: -size.height / 2 + 80)
        row.alpha = 0
        root.addChild(row)
        row.run(.sequence([
            .group([.fadeIn(withDuration: 0.12), .moveBy(x: 0, y: 14, duration: 0.3)]),
            .wait(forDuration: 1.5),
            .fadeOut(withDuration: 0.4),
            .removeFromParent(),
        ]))
    }
}
#endif
