#if canImport(SpriteKit)
import Foundation
import SpriteKit

/// Draws a floor and keeps its nodes in step with the simulation.
///
/// The depth illusion is all in the sort order. Floor tiles sit on a flat
/// layer; *everything else* — wall caps, wall faces, props, actors, pickups —
/// shares one layer sorted by world Y. A wall block sorts by its bottom edge,
/// so an actor standing south of a wall draws in front of it and an actor in
/// the room beyond draws behind it. That single rule is what turns flat
/// sprites into a room with height.
final class WorldRenderer {
    /// World Y is the sort key; these offsets keep classes of thing apart
    /// without breaking the per-Y ordering inside each class.
    private enum Depth {
        static let floor: CGFloat = -10_000
        static let floorDecal: CGFloat = -9_000
        static let shadow: CGFloat = -8_000
        static let sorted: CGFloat = 0          // + world Y
        static let projectile: CGFloat = 60_000 // bullets always readable
        static let effect: CGFloat = 70_000
        static let overlay: CGFloat = 90_000
    }

    let atlas: Atlas
    let root = SKNode()

    private let floorLayer = SKNode()
    private let sortedLayer = SKNode()
    private let effectLayer = SKNode()

    private var actorNodes: [Int: ActorNode] = [:]
    private var projectileNodes: [Int: SKSpriteNode] = [:]
    private var pickupNodes: [Int: PickupNode] = [:]
    private var doorNodes: [Int: SKSpriteNode] = [:]
    private var beamNode: SKSpriteNode?
    private var theme: String = "keep"

    /// A character plus the shadow and gun that travel with it.
    private final class ActorNode {
        let body: SKSpriteNode
        let shadow: SKSpriteNode
        var weapon: SKSpriteNode?
        var lastAnimation: String = ""

        init(body: SKSpriteNode, shadow: SKSpriteNode) {
            self.body = body
            self.shadow = shadow
        }

        func removeFromParent() {
            body.removeFromParent()
            shadow.removeFromParent()
            weapon?.removeFromParent()
        }
    }

    private final class PickupNode {
        let sprite: SKSpriteNode
        let shadow: SKSpriteNode
        var price: SKNode?

        init(sprite: SKSpriteNode, shadow: SKSpriteNode) {
            self.sprite = sprite
            self.shadow = shadow
        }

        func removeFromParent() {
            sprite.removeFromParent()
            shadow.removeFromParent()
            price?.removeFromParent()
        }
    }

    init(atlas: Atlas) {
        self.atlas = atlas
        floorLayer.zPosition = Depth.floor
        effectLayer.zPosition = Depth.effect
        root.addChild(floorLayer)
        root.addChild(sortedLayer)
        root.addChild(effectLayer)
    }

    // -- coordinate conversion ------------------------------------------------

    /// World space is y-down (matching the art); SpriteKit is y-up.
    static func scenePoint(_ position: Vec2) -> CGPoint {
        CGPoint(x: CGFloat(position.x), y: -CGFloat(position.y))
    }

    // -- static geometry ------------------------------------------------------

    func build(dungeon: Dungeon) {
        floorLayer.removeAllChildren()
        sortedLayer.removeAllChildren()
        effectLayer.removeAllChildren()
        actorNodes.removeAll()
        projectileNodes.removeAll()
        pickupNodes.removeAll()
        doorNodes.removeAll()
        theme = dungeon.theme

        let map = dungeon.map
        let tile = atlas.tileSize

        for ty in 0..<map.height {
            for tx in 0..<map.width {
                let kind = map[tx, ty]
                let origin = CGPoint(x: CGFloat(tx) * tile + tile / 2,
                                     y: -(CGFloat(ty) * tile + tile / 2))

                switch kind {
                case .floor, .doorway:
                    let variant = Self.floorVariant(tx: tx, ty: ty)
                    let sprite = SKSpriteNode(
                        frame: atlas.frame("tile/\(theme)/floor_\(variant)"))
                    sprite.position = origin
                    floorLayer.addChild(sprite)

                    // Contact shadow on the floor beneath a wall face.
                    if map[tx, ty - 1] == .wall {
                        let shadow = SKSpriteNode(
                            frame: atlas.frame("tile/\(theme)/wall_shadow"))
                        shadow.anchorPoint = CGPoint(x: 0.5, y: 1)
                        shadow.position = CGPoint(x: origin.x, y: origin.y + tile / 2)
                        shadow.zPosition = Depth.shadow - Depth.floor
                        floorLayer.addChild(shadow)
                    }

                case .pit:
                    let sprite = SKSpriteNode(frame: atlas.frame("tile/\(theme)/floor_pit"))
                    sprite.position = origin
                    floorLayer.addChild(sprite)

                case .wall:
                    // Solid rock far from any room is never seen; skipping it
                    // keeps a floor at a few thousand nodes instead of 20,000.
                    guard Self.isWallVisible(map: map, tx: tx, ty: ty) else { continue }

                    let cap = SKSpriteNode(
                        frame: atlas.frame("tile/\(theme)/cap_\(map.wallMask(tx, ty))"))
                    cap.position = origin
                    // Sort by the block's bottom edge, so anything standing
                    // south of it is in front and anything north is behind.
                    cap.zPosition = Depth.sorted + CGFloat(ty + 1) * tile
                    sortedLayer.addChild(cap)

                    if map.needsWallFace(tx, ty) {
                        let variant = Self.faceVariant(tx: tx, ty: ty)
                        let face = SKSpriteNode(
                            frame: atlas.frame("tile/\(theme)/face_\(variant)"))
                        face.anchorPoint = CGPoint(x: 0.5, y: 1)
                        face.position = CGPoint(x: origin.x, y: origin.y - tile / 2)
                        face.zPosition = Depth.sorted + CGFloat(ty + 1) * tile + 1
                        sortedLayer.addChild(face)
                    }
                }
            }
        }

        for placement in dungeon.props where !placement.blocking && !placement.destructible {
            addStaticProp(placement)
        }
        for (index, door) in dungeon.doors.enumerated() {
            addDoor(index: index, door: door)
        }
    }

    /// Deterministic per-tile variation: hashing the coordinates avoids
    /// storing a variant per tile and keeps the floor stable across frames.
    private static func floorVariant(tx: Int, ty: Int) -> Int {
        let hash = (tx &* 73856093) ^ (ty &* 19349663)
        let value = abs(hash) % 100
        // Mostly plain tiles — decorated ones tile into visible wallpaper.
        if value < 78 { return 0 }
        if value < 88 { return 1 }
        if value < 95 { return 2 }
        return 3
    }

    private static func faceVariant(tx: Int, ty: Int) -> Int {
        let hash = (tx &* 40503) ^ (ty &* 12289)
        let value = abs(hash) % 100
        if value < 76 { return 0 }
        if value < 88 { return 1 }
        if value < 95 { return 2 }
        return 3
    }

    private static func isWallVisible(map: TileMap, tx: Int, ty: Int) -> Bool {
        // Visible if any tile within two steps is walkable — two, not one, so
        // the wall still has thickness where it meets a room.
        for dy in -2...2 {
            for dx in -2...2 {
                if !map.isSolid(tx + dx, ty + dy) { return true }
            }
        }
        return false
    }

    private func addStaticProp(_ placement: PropPlacement) {
        let name = "prop/\(theme)/\(placement.name)"
        let node = SKSpriteNode(frame: atlas.frame(name))
        node.anchorPoint = CGPoint(x: 0.5, y: 0)
        node.position = Self.scenePoint(placement.position)
        node.zPosition = Depth.sorted + CGFloat(placement.position.y)
        sortedLayer.addChild(node)

        if let info = atlas.animationInfo(name), info.frames.count > 1 {
            let textures = atlas.animation(name).map(\.texture)
            let action = SKAction.animate(with: textures,
                                          timePerFrame: 1.0 / info.fps,
                                          resize: false, restore: false)
            node.run(.repeatForever(action))
        }
    }

    private func addDoor(index: Int, door: Door) {
        let state = door.isBossDoor ? "boss" : (door.locked ? "locked" : "closed")
        let node = SKSpriteNode(frame: atlas.frame(
            "tile/\(theme)/door_\(state)_\(door.axis)"))
        let center = Vec2((Double(door.tileX) + 1) * TileMap.tileSize,
                          (Double(door.tileY) + 1) * TileMap.tileSize)
        node.position = Self.scenePoint(center)
        node.zPosition = Depth.sorted + CGFloat(center.y) + 2
        node.alpha = 0
        doorNodes[index] = node
        sortedLayer.addChild(node)
    }

    // -- per-frame sync -------------------------------------------------------

    func sync(world: World, font: BitmapFont) {
        syncActors(world: world)
        syncProjectiles(world: world)
        syncPickups(world: world, font: font)
        syncDoors(world: world)
        syncBeam(world: world)
    }

    private func syncActors(world: World) {
        var live: Set<Int> = []

        for actor in world.actors {
            guard actor.alive || actor.isDying else { continue }
            live.insert(actor.id.raw)

            let node = actorNodes[actor.id.raw] ?? makeActorNode(for: actor)
            let point = Self.scenePoint(actor.position)

            node.shadow.position = CGPoint(x: point.x, y: point.y - CGFloat(actor.height))
            node.shadow.zPosition = Depth.sorted + CGFloat(actor.position.y) - 1
            node.shadow.alpha = actor.height > 0 ? 0.45 : 0.75

            node.body.position = CGPoint(x: point.x, y: point.y + CGFloat(actor.height))
            node.body.zPosition = Depth.sorted + CGFloat(actor.position.y)

            // Side animations are drawn facing right and mirrored for left.
            if actor.animation.hasSuffix("_side") {
                let facingLeft = actor.kind == .player
                    ? cos(actor.aimAngle) < 0
                    : actor.velocity.x < 0
                node.body.xScale = facingLeft ? -1 : 1
            } else {
                node.body.xScale = 1
            }

            let animation = animationName(for: actor)
            node.body.apply(atlas.frame(of: animation, at: actor.animationTime))

            // Hit flash: blend the sprite toward white for a few frames.
            if actor.hitFlashFor > 0 {
                node.body.color = .white
                node.body.colorBlendFactor = 0.85
            } else if actor.has(.burn) {
                node.body.color = SKColor(red: 1, green: 0.45, blue: 0.15, alpha: 1)
                node.body.colorBlendFactor = 0.35
            } else if actor.has(.chill) {
                node.body.color = SKColor(red: 0.5, green: 0.85, blue: 1, alpha: 1)
                node.body.colorBlendFactor = 0.4
            } else if actor.has(.poison) {
                node.body.color = SKColor(red: 0.45, green: 1, blue: 0.35, alpha: 1)
                node.body.colorBlendFactor = 0.3
            } else if actor.has(.curse) {
                node.body.color = SKColor(red: 0.75, green: 0.4, blue: 1, alpha: 1)
                node.body.colorBlendFactor = 0.3
            } else {
                node.body.colorBlendFactor = 0
            }

            // Invulnerability blink, skipped while dodging so the roll reads
            // as a roll rather than as damage.
            if actor.kind == .player {
                let blinking = actor.invulnerableFor > 0 && !world.player.isDodging
                node.body.alpha = blinking
                    ? (sin(actor.invulnerableFor * 40) > 0 ? 0.35 : 1)
                    : 1
            } else if actor.isDying {
                node.body.alpha = CGFloat(max(0, actor.deathTimer / 0.5))
            }

            if actor.kind == .player {
                syncHeldWeapon(node: node, actor: actor, world: world)
            }
        }

        for (id, node) in actorNodes where !live.contains(id) {
            node.removeFromParent()
            actorNodes.removeValue(forKey: id)
        }
    }

    private func animationName(for actor: Actor) -> String {
        switch actor.kind {
        case .player:
            return "\(actor.spriteBase)/\(actor.animation)"
        case .enemy:
            if actor.enemy?.rig == .humanoid {
                let name = actor.animation.isEmpty ? "idle_front" : actor.animation
                return "\(actor.spriteBase)/\(name)"
            }
            return actor.spriteBase
        case .boss:
            return actor.spriteBase
        case .prop, .orbital:
            return actor.spriteBase
        }
    }

    private func makeActorNode(for actor: Actor) -> ActorNode {
        let animation = animationName(for: actor)
        let frame = atlas.frame(of: animation, at: 0)

        let groundY: CGFloat
        switch actor.kind {
        case .player:
            groundY = 21          // the character rig's ground row
        case .enemy where actor.enemy?.rig == .humanoid:
            groundY = 21
        default:
            groundY = frame.size.height - 2
        }

        let body = SKSpriteNode(frame: frame, groundY: groundY)
        body.zPosition = Depth.sorted
        sortedLayer.addChild(body)

        let shadowSize = shadowName(for: actor)
        let shadow = SKSpriteNode(frame: atlas.frame(shadowSize))
        shadow.alpha = 0.7
        sortedLayer.addChild(shadow)

        let node = ActorNode(body: body, shadow: shadow)
        actorNodes[actor.id.raw] = node
        return node
    }

    private func shadowName(for actor: Actor) -> String {
        switch actor.radius {
        case ..<7: return "shadow/12x5"
        case ..<9: return "shadow/16x6"
        case ..<14: return "shadow/22x8"
        case ..<20: return "shadow/34x12"
        default: return "shadow/48x16"
        }
    }

    private func syncHeldWeapon(node: ActorNode, actor: Actor, world: World) {
        guard let weapon = world.run.loadout.activeWeapon else {
            node.weapon?.removeFromParent()
            node.weapon = nil
            return
        }
        let name = weapon.def.sprite
        let frame = atlas.frame(name)

        let sprite: SKSpriteNode
        if let existing = node.weapon {
            sprite = existing
            sprite.apply(frame)
        } else {
            sprite = SKSpriteNode(frame: frame)
            sortedLayer.addChild(sprite)
            node.weapon = sprite
        }

        // Anchor at the grip so the gun rotates around the hand, not its
        // centre — this is the difference between aiming and waving.
        if let anchors = atlas.weaponAnchors(weapon.def.id) {
            sprite.anchorPoint = CGPoint(
                x: CGFloat(anchors.pivot[0]) / frame.size.width,
                y: (frame.size.height - CGFloat(anchors.pivot[1])) / frame.size.height)
        } else {
            sprite.anchorPoint = CGPoint(x: 0.25, y: 0.35)
        }

        let aimingLeft = cos(actor.aimAngle) < 0
        // SpriteKit rotates counter-clockwise with y up; world angles are
        // clockwise with y down, hence the negation.
        sprite.zRotation = CGFloat(-actor.aimAngle) + (aimingLeft ? .pi : 0)
        sprite.yScale = aimingLeft ? -1 : 1
        sprite.isHidden = world.player.isDodging

        let hand = Vec2.angle(actor.aimAngle) * 5
        let point = Self.scenePoint(actor.position + hand)
        sprite.position = CGPoint(x: point.x, y: point.y + 9)
        // In front of the body when aiming down the screen, behind when up.
        sprite.zPosition = Depth.sorted + CGFloat(actor.position.y) +
            (sin(actor.aimAngle) >= 0 ? 1 : -1)
    }

    private func syncProjectiles(world: World) {
        var live: Set<Int> = []

        for projectile in world.projectiles where projectile.alive {
            live.insert(projectile.id)
            let node: SKSpriteNode
            if let existing = projectileNodes[projectile.id] {
                node = existing
            } else {
                node = SKSpriteNode(frame: atlas.frame(of: projectile.sprite, at: 0))
                node.zPosition = Depth.projectile
                effectLayer.addChild(node)
                projectileNodes[projectile.id] = node
            }

            node.apply(atlas.frame(of: projectile.sprite, at: projectile.age))
            let point = Self.scenePoint(projectile.position)
            node.position = CGPoint(x: point.x,
                                    y: point.y + CGFloat(projectile.height))
            node.zRotation = CGFloat(-projectile.angle) + CGFloat(projectile.rotation)
            node.setScale(CGFloat(projectile.scale))

            // A lobbed shot grows as it rises: the only cue that it is above
            // the floor rather than merely further away.
            if projectile.arcGravity > 0 {
                let lift = 1 + CGFloat(projectile.height) / 90
                node.setScale(CGFloat(projectile.scale) * lift)
            }
        }

        for (id, node) in projectileNodes where !live.contains(id) {
            node.removeFromParent()
            projectileNodes.removeValue(forKey: id)
        }
    }

    private func syncPickups(world: World, font: BitmapFont) {
        var live: Set<Int> = []

        for pickup in world.pickups {
            live.insert(pickup.id)
            let node: PickupNode
            if let existing = pickupNodes[pickup.id] {
                node = existing
            } else {
                let sprite = SKSpriteNode(frame: atlas.frame(pickup.sprite))
                sprite.anchorPoint = CGPoint(x: 0.5, y: 0.5)
                sortedLayer.addChild(sprite)
                let shadow = SKSpriteNode(frame: atlas.frame("shadow/12x5"))
                shadow.alpha = 0.5
                sortedLayer.addChild(shadow)
                let made = PickupNode(sprite: sprite, shadow: shadow)

                if pickup.price > 0 {
                    let label = font.node("\(pickup.price)",
                                          color: SKColor(red: 1, green: 0.85,
                                                         blue: 0.35, alpha: 1),
                                          align: .center)
                    sortedLayer.addChild(label)
                    made.price = label
                }
                pickupNodes[pickup.id] = made
                node = made
            }

            let bob = sin(pickup.age * 3 + pickup.bobPhase) * 2.5
            let point = Self.scenePoint(pickup.position)
            node.sprite.position = CGPoint(x: point.x, y: point.y + 8 + CGFloat(bob))
            node.sprite.zPosition = Depth.sorted + CGFloat(pickup.position.y)
            node.shadow.position = point
            node.shadow.zPosition = Depth.sorted + CGFloat(pickup.position.y) - 1
            node.price?.position = CGPoint(x: point.x, y: point.y + 26)
            node.price?.zPosition = Depth.overlay
        }

        for (id, node) in pickupNodes where !live.contains(id) {
            node.removeFromParent()
            pickupNodes.removeValue(forKey: id)
        }
    }

    private func syncDoors(world: World) {
        for (index, node) in doorNodes {
            guard world.dungeon.doors.indices.contains(index) else { continue }
            let door = world.dungeon.doors[index]
            let touchesCurrentRoom = door.roomA == world.currentRoom ||
                door.roomB == world.currentRoom
            let shut = world.doorsLocked && touchesCurrentRoom
            let target: CGFloat = shut ? 1 : 0
            if abs(node.alpha - target) > 0.01 {
                node.removeAllActions()
                node.run(.fadeAlpha(to: target, duration: 0.18))
            }
        }
    }

    private func syncBeam(world: World) {
        guard let (start, end) = world.beamEndpoint else {
            beamNode?.isHidden = true
            return
        }
        let sprite: SKSpriteNode
        if let existing = beamNode {
            sprite = existing
        } else {
            sprite = SKSpriteNode(frame: atlas.frame("proj/beam_seg_ice"))
            sprite.anchorPoint = CGPoint(x: 0, y: 0.5)
            sprite.zPosition = Depth.projectile - 1
            sprite.blendMode = .add
            effectLayer.addChild(sprite)
            beamNode = sprite
        }
        let weaponID = world.run.loadout.activeWeapon?.def.id ?? ""
        sprite.apply(atlas.frame(weaponID == "void_needle"
                                 ? "proj/beam_seg_void" : "proj/beam_seg_ice"))
        sprite.isHidden = false
        let delta = end - start
        sprite.position = Self.scenePoint(start)
        sprite.zRotation = CGFloat(-delta.angle)
        sprite.xScale = CGFloat(delta.length) / sprite.size.width
        sprite.alpha = 0.9
    }

    // -- transient effects ----------------------------------------------------

    func play(effect: EffectRequest) {
        let name = effect.name
        let frames = atlas.animation(name)
        guard let first = frames.first else { return }

        let node = SKSpriteNode(frame: first)
        node.position = Self.scenePoint(effect.position)
        node.zRotation = CGFloat(-effect.angle)
        node.setScale(CGFloat(effect.scale))
        node.zPosition = Depth.effect
        if name.contains("explosion") || name.contains("muzzle")
            || name.contains("lightning") || name.contains("spark") {
            node.blendMode = .add
        }
        effectLayer.addChild(node)

        let fps = atlas.animationInfo(name)?.fps ?? 16
        let animate = SKAction.animate(with: frames.map(\.texture),
                                       timePerFrame: 1.0 / fps,
                                       resize: false, restore: false)
        node.run(.sequence([animate, .removeFromParent()]))
    }

    func showNumber(_ text: String, at position: Vec2, color: SKColor,
                    font: BitmapFont, scale: CGFloat = 1) {
        let node = font.node(text, color: color, align: .center)
        node.position = Self.scenePoint(position)
        node.zPosition = Depth.overlay
        node.setScale(scale)
        effectLayer.addChild(node)
        node.run(.sequence([
            .group([
                .moveBy(x: 0, y: 18, duration: 0.6),
                .sequence([.wait(forDuration: 0.35), .fadeOut(withDuration: 0.25)]),
            ]),
            .removeFromParent(),
        ]))
    }
}
#endif
