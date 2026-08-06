import Foundation

/// Where a sprite's origin sits inside its own frame.
public enum SpriteAnchor: Sendable, Equatable {
    case center
    case bottomCenter
    case topCenter
    /// Anchored to a specific row measured from the top of the frame — how
    /// characters stand on the floor regardless of how tall their hat is.
    case groundRow(Double)
    /// The grip anchor recorded for this weapon in the atlas manifest. The
    /// exact pixel lives with the art, so the renderer resolves it; the
    /// simulation only says "hold it by the handle".
    case weaponPivot
}

/// One thing to draw. Deliberately renderer-agnostic: it names an atlas
/// entry and a place, and says nothing about SpriteKit, textures or nodes.
public struct SpriteCommand: Sendable {
    /// Stable identity across frames, so a renderer can reuse one node per
    /// command instead of rebuilding the scene every tick.
    public var key: String
    /// Atlas sprite or animation name.
    public var sprite: String
    /// Seconds into the animation. Ignored for stills.
    public var time: Double
    public var position: Vec2
    /// Sort key. Larger draws on top.
    public var depth: Double
    public var anchor: SpriteAnchor
    /// Clockwise radians in world space (y down).
    public var rotation: Double
    public var scale: Double
    public var flipX: Bool
    public var flipY: Bool
    public var alpha: Double
    /// Colour to blend toward, and how far. Drives hit flashes and status tints.
    public var tint: (r: Double, g: Double, b: Double)?
    public var tintAmount: Double
    /// Additive blending for anything that should glow.
    public var additive: Bool

    public init(key: String, sprite: String, position: Vec2, depth: Double,
                anchor: SpriteAnchor = .center, time: Double = 0,
                rotation: Double = 0, scale: Double = 1,
                flipX: Bool = false, flipY: Bool = false, alpha: Double = 1,
                tint: (r: Double, g: Double, b: Double)? = nil,
                tintAmount: Double = 0, additive: Bool = false) {
        self.key = key
        self.sprite = sprite
        self.position = position
        self.depth = depth
        self.anchor = anchor
        self.time = time
        self.rotation = rotation
        self.scale = scale
        self.flipX = flipX
        self.flipY = flipY
        self.alpha = alpha
        self.tint = tint
        self.tintAmount = tintAmount
        self.additive = additive
    }
}

/// Turns world state into a flat list of draw commands.
///
/// This is the single source of truth for *what appears where*, shared by the
/// SpriteKit renderer and by the headless snapshot tool. Putting it in the
/// testable core is deliberate: the depth ordering that makes flat sprites
/// look like a room with height is a rule, not a rendering detail, and it is
/// worth being able to assert on.
public enum SceneSnapshot {

    /// Depth bands. Within a band, world Y decides what is in front.
    public enum Depth {
        public static let floor = -100_000.0
        public static let floorShadow = -90_000.0
        public static let world = 0.0            // + world Y
        public static let projectile = 500_000.0
        public static let effect = 600_000.0
        public static let overlay = 700_000.0
    }

    // -- static geometry ------------------------------------------------------

    /// Floor, walls, doors and scenery. Depends only on the dungeon, so a
    /// renderer can build these once per floor.
    public static func staticCommands(for dungeon: Dungeon) -> [SpriteCommand] {
        var commands: [SpriteCommand] = []
        let map = dungeon.map
        let theme = dungeon.theme
        let tile = TileMap.tileSize

        for ty in 0..<map.height {
            for tx in 0..<map.width {
                let center = map.tileCenter(tx, ty)
                switch map[tx, ty] {
                case .floor, .doorway:
                    commands.append(SpriteCommand(
                        key: "floor:\(tx),\(ty)",
                        sprite: "tile/\(theme)/floor_\(floorVariant(tx, ty))",
                        position: center, depth: Depth.floor))
                    // Wall faces cast onto the floor immediately below them.
                    if map[tx, ty - 1] == .wall {
                        commands.append(SpriteCommand(
                            key: "wallshadow:\(tx),\(ty)",
                            sprite: "tile/\(theme)/wall_shadow",
                            position: Vec2(center.x, Double(ty) * tile),
                            depth: Depth.floorShadow, anchor: .topCenter))
                    }

                case .pit:
                    commands.append(SpriteCommand(
                        key: "pit:\(tx),\(ty)", sprite: "tile/\(theme)/floor_pit",
                        position: center, depth: Depth.floor))

                case .wall:
                    // Solid rock far from any room is never on screen. Skipping
                    // it keeps a floor at a few thousand sprites, not 20,000.
                    guard isVisible(map: map, tx: tx, ty: ty) else { continue }

                    // A wall block sorts by its *bottom* edge, so an actor
                    // standing south of it draws in front and one in the room
                    // beyond draws behind. That single rule is the whole
                    // depth illusion.
                    let sortY = Double(ty + 1) * tile
                    commands.append(SpriteCommand(
                        key: "cap:\(tx),\(ty)",
                        sprite: "tile/\(theme)/cap_\(map.wallMask(tx, ty))",
                        position: center, depth: Depth.world + sortY))

                    if map.needsWallFace(tx, ty) {
                        commands.append(SpriteCommand(
                            key: "face:\(tx),\(ty)",
                            sprite: "tile/\(theme)/face_\(faceVariant(tx, ty))",
                            position: Vec2(center.x, Double(ty + 1) * tile),
                            depth: Depth.world + sortY + 1, anchor: .topCenter))
                    }
                }
            }
        }

        for (index, placement) in dungeon.props.enumerated()
        where !placement.blocking && !placement.destructible {
            commands.append(SpriteCommand(
                key: "prop:\(index)",
                sprite: "prop/\(dungeon.theme)/\(placement.name)",
                position: placement.position,
                depth: Depth.world + placement.position.y,
                anchor: .bottomCenter))
        }

        return commands
    }

    /// Per-tile variation from a hash rather than stored state, so the floor
    /// looks the same every frame without a parallel array.
    public static func floorVariant(_ tx: Int, _ ty: Int) -> Int {
        let hash = abs((tx &* 73856093) ^ (ty &* 19349663)) % 100
        // Mostly plain: decorated tiles repeated everywhere read as wallpaper.
        if hash < 78 { return 0 }
        if hash < 88 { return 1 }
        if hash < 95 { return 2 }
        return 3
    }

    public static func faceVariant(_ tx: Int, _ ty: Int) -> Int {
        let hash = abs((tx &* 40503) ^ (ty &* 12289)) % 100
        if hash < 76 { return 0 }
        if hash < 88 { return 1 }
        if hash < 95 { return 2 }
        return 3
    }

    private static func isVisible(map: TileMap, tx: Int, ty: Int) -> Bool {
        // Two tiles of margin, not one, so a wall keeps visible thickness
        // where it meets a room.
        for dy in -2...2 {
            for dx in -2...2 where !map.isSolid(tx + dx, ty + dy) {
                return true
            }
        }
        return false
    }

    // -- moving parts ---------------------------------------------------------

    public static func dynamicCommands(for world: World) -> [SpriteCommand] {
        var commands: [SpriteCommand] = []
        commands.reserveCapacity(world.actors.count * 3 + world.projectiles.count)

        appendPickups(world, into: &commands)
        appendActors(world, into: &commands)
        appendProjectiles(world, into: &commands)
        appendDoors(world, into: &commands)
        appendExit(world, into: &commands)
        return commands
    }

    private static func appendActors(_ world: World,
                                     into commands: inout [SpriteCommand]) {
        for actor in world.actors where actor.alive || actor.isDying {
            let key = "actor:\(actor.id.raw)"
            let sortY = actor.position.y

            commands.append(SpriteCommand(
                key: "\(key):shadow", sprite: shadowSprite(for: actor),
                position: actor.position, depth: Depth.world + sortY - 1,
                alpha: actor.height > 0 ? 0.45 : 0.75))

            let body = Vec2(actor.position.x, actor.position.y - actor.height)
            var command = SpriteCommand(
                key: "\(key):body", sprite: animation(for: actor),
                position: body, depth: Depth.world + sortY,
                anchor: anchor(for: actor), time: actor.animationTime)

            // Side frames are drawn facing right and mirrored for left.
            if actor.animation.hasSuffix("_side") {
                command.flipX = actor.kind == .player
                    ? cos(actor.aimAngle) < 0
                    : actor.velocity.x < 0
            }

            if actor.hitFlashFor > 0 {
                command.tint = (1, 1, 1)
                command.tintAmount = 0.85
            } else if let status = dominantStatus(of: actor) {
                command.tint = statusTint(status)
                command.tintAmount = 0.35
            }

            if actor.isDying {
                command.alpha = max(0, actor.deathTimer / 0.5)
            } else if actor.kind == .player, actor.invulnerableFor > 0,
                      !world.player.isDodging {
                // Blink on i-frames, but never during a roll: the roll should
                // read as a roll, not as damage.
                command.alpha = sin(actor.invulnerableFor * 40) > 0 ? 0.35 : 1
            }
            commands.append(command)

            if actor.kind == .player, let weapon = world.run.loadout.activeWeapon,
               !world.player.isDodging {
                commands.append(weaponCommand(actor: actor, weapon: weapon.def,
                                              key: key))
            }
        }
    }

    private static func weaponCommand(actor: Actor, weapon: WeaponDef,
                                      key: String) -> SpriteCommand {
        let aimingLeft = cos(actor.aimAngle) < 0
        let hand = actor.position + Vec2.angle(actor.aimAngle) * 5 - Vec2(0, 9)
        var command = SpriteCommand(
            key: "\(key):weapon", sprite: weapon.sprite, position: hand,
            // In front of the body when aiming down the screen, behind when up.
            depth: Depth.world + actor.position.y + (sin(actor.aimAngle) >= 0 ? 1 : -1),
            anchor: .weaponPivot,
            rotation: actor.aimAngle + (aimingLeft ? .pi : 0))
        command.flipY = aimingLeft
        return command
    }

    private static func appendProjectiles(_ world: World,
                                          into commands: inout [SpriteCommand]) {
        for projectile in world.projectiles where projectile.alive {
            // Lobbed shots grow as they rise: the only cue that a bullet is
            // above the floor rather than merely further away.
            let lift = projectile.arcGravity > 0 ? 1 + projectile.height / 90 : 1
            commands.append(SpriteCommand(
                key: "proj:\(projectile.id)", sprite: projectile.sprite,
                position: Vec2(projectile.position.x,
                               projectile.position.y - projectile.height),
                depth: Depth.projectile + projectile.position.y,
                time: projectile.age,
                rotation: projectile.angle + projectile.rotation,
                scale: projectile.scale * lift))
                // Deliberately not additive. Bullets are drawn as a bright
                // core inside a dark rim, and additive blending eats the rim
                // — which is the one thing that has to survive when forty of
                // them are on screen at once.
        }
    }

    private static func appendPickups(_ world: World,
                                      into commands: inout [SpriteCommand]) {
        for pickup in world.pickups {
            let bob = sin(pickup.age * 3 + pickup.bobPhase) * 2.5
            commands.append(SpriteCommand(
                key: "pickup:\(pickup.id):shadow", sprite: "shadow/12x5",
                position: pickup.position,
                depth: Depth.world + pickup.position.y - 1, alpha: 0.5))
            commands.append(SpriteCommand(
                key: "pickup:\(pickup.id)", sprite: pickup.sprite,
                position: Vec2(pickup.position.x, pickup.position.y - 8 - bob),
                depth: Depth.world + pickup.position.y))
        }
    }

    private static func appendDoors(_ world: World,
                                    into commands: inout [SpriteCommand]) {
        for (index, door) in world.dungeon.doors.enumerated() {
            let touchesCurrent = door.roomA == world.currentRoom ||
                door.roomB == world.currentRoom
            guard world.doorsLocked && touchesCurrent else { continue }
            let state = door.isBossDoor ? "boss" : (door.locked ? "locked" : "closed")
            let center = Vec2((Double(door.tileX) + 1) * TileMap.tileSize,
                              (Double(door.tileY) + 1) * TileMap.tileSize)
            commands.append(SpriteCommand(
                key: "door:\(index)",
                sprite: "tile/\(world.dungeon.theme)/door_\(state)_\(door.axis)",
                position: center, depth: Depth.world + center.y + 2))
        }
    }

    private static func appendExit(_ world: World,
                                   into commands: inout [SpriteCommand]) {
        guard let exit = world.exitPosition else { return }
        commands.append(SpriteCommand(
            key: "exit", sprite: "fx/portal", position: exit,
            depth: Depth.floorShadow + 1, time: world.time, additive: true))
    }

    // -- sprite naming --------------------------------------------------------

    public static func animation(for actor: Actor) -> String {
        switch actor.kind {
        case .player:
            return "\(actor.spriteBase)/\(actor.animation)"
        case .enemy:
            guard actor.enemy?.rig == .humanoid else { return actor.spriteBase }
            let name = actor.animation.isEmpty ? "idle_front" : actor.animation
            return "\(actor.spriteBase)/\(name)"
        case .boss, .prop, .orbital:
            return actor.spriteBase
        }
    }

    public static func anchor(for actor: Actor) -> SpriteAnchor {
        switch actor.kind {
        case .player:
            return .groundRow(21)          // the character rig's ground row
        case .enemy where actor.enemy?.rig == .humanoid:
            return .groundRow(21)
        case .prop:
            return .bottomCenter
        default:
            return .center
        }
    }

    public static func shadowSprite(for actor: Actor) -> String {
        switch actor.radius {
        case ..<7: return "shadow/12x5"
        case ..<9: return "shadow/16x6"
        case ..<14: return "shadow/22x8"
        case ..<20: return "shadow/34x12"
        default: return "shadow/48x16"
        }
    }

    private static func dominantStatus(of actor: Actor) -> StatusKind? {
        for kind in [StatusKind.burn, .chill, .poison, .curse, .shock]
        where actor.has(kind) {
            return kind
        }
        return nil
    }

    private static func statusTint(_ kind: StatusKind) -> (r: Double, g: Double,
                                                           b: Double) {
        switch kind {
        case .burn: return (1.0, 0.45, 0.15)
        case .chill: return (0.5, 0.85, 1.0)
        case .poison: return (0.45, 1.0, 0.35)
        case .curse: return (0.75, 0.4, 1.0)
        case .shock: return (0.9, 0.95, 0.4)
        }
    }
}
