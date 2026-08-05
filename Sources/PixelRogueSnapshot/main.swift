import Foundation
import PixelRogueCore

/// Headless snapshot tool.
///
/// The SpriteKit renderer needs macOS, which makes the visual half of the
/// game impossible to check in CI or on a Linux box. This runs the real
/// simulation, asks `SceneSnapshot` for the same draw commands the renderer
/// consumes, and writes them out as JSON. `Tools/pixelforge/render_scene.py`
/// composites that against the real atlas, so a frame of the actual game can
/// be produced and eyeballed anywhere.
struct Options {
    var seed: UInt64 = 20260805
    var frames = 240
    var character = "marshal"
    var scenario = "combat"
    var output = "scene.json"
    var width = 480
    var height = 270
}

func parseOptions() -> Options {
    var options = Options()
    var arguments = Array(CommandLine.arguments.dropFirst())

    while !arguments.isEmpty {
        let flag = arguments.removeFirst()
        func next() -> String { arguments.isEmpty ? "" : arguments.removeFirst() }
        switch flag {
        case "--seed": options.seed = seedValue(from: next())
        case "--frames": options.frames = Int(next()) ?? options.frames
        case "--character": options.character = next()
        case "--scenario": options.scenario = next()
        case "--out": options.output = next()
        case "--width": options.width = Int(next()) ?? options.width
        case "--height": options.height = Int(next()) ?? options.height
        case "--help", "-h":
            print("""
            pixel-rogue-snapshot

              --seed <value>       run seed (accepts words, e.g. GUNGEON)
              --scenario <name>    start | combat | boss | shop | treasure
              --character <id>     marshal | stray | bulwark | tinker | beak | hexe
              --frames <n>         simulation frames before capture
              --width/--height     viewport in world pixels
              --out <path>         JSON destination
            """)
            exit(0)
        default: break
        }
    }
    return options
}

// -- scenario setup -----------------------------------------------------------

func room(of kind: RoomKind, in world: World) -> Room? {
    world.dungeon.rooms.first { $0.kind == kind }
}

func place(world: World, scenario: String) {
    switch scenario {
    case "boss":
        if let target = room(of: .boss, in: world) {
            world.teleportPlayer(to: target.center + Vec2(0, 70))
        }
    case "shop":
        if let target = room(of: .shop, in: world) {
            world.teleportPlayer(to: target.center + Vec2(0, 40))
        }
    case "treasure":
        if let target = room(of: .treasure, in: world) {
            world.teleportPlayer(to: target.center + Vec2(0, 30))
        }
    case "combat":
        // The nearest combat room to the start, so the walk is short and the
        // captured frame is a real fight rather than an empty corridor.
        let combat = world.dungeon.rooms
            .filter { $0.kind == .combat }
            .min { $0.depth < $1.depth }
        if let target = combat {
            world.teleportPlayer(to: target.center)
        }
    default:
        break
    }
}

/// A crude bot: face the nearest enemy, keep some distance, and shoot.
/// Good enough to produce a frame that looks like play rather than a pose.
func scriptedInput(world: World, frame: Int) -> InputState {
    var input = InputState()
    guard let player = world.playerActor else { return input }

    let enemies = world.livingEnemies
    let target = enemies.min {
        $0.position.distanceSquared(to: player.position) <
        $1.position.distanceSquared(to: player.position)
    }

    if let target {
        input.aim = target.position
        input.firing = frame % 7 < 5
        let toTarget = target.position - player.position
        let distance = toTarget.length
        let strafe = toTarget.normalized.perpendicular
        if distance > 130 {
            input.move = (toTarget.normalized * 0.7 + strafe * 0.5).normalized
        } else if distance < 70 {
            input.move = (-toTarget.normalized * 0.6 + strafe * 0.6).normalized
        } else {
            input.move = strafe
        }
        if frame % 90 == 0 { input.dodgePressed = true }
    } else {
        let angle = Double(frame) * 0.02
        input.move = Vec2.angle(angle)
        input.aim = player.position + Vec2.angle(angle) * 120
        input.firing = frame % 40 < 6
    }
    input.interactPressed = frame % 30 == 0
    return input
}

// -- JSON emission ------------------------------------------------------------

func anchorJSON(_ anchor: SpriteAnchor) -> [String: Any] {
    switch anchor {
    case .center: return ["kind": "center"]
    case .bottomCenter: return ["kind": "bottom"]
    case .topCenter: return ["kind": "top"]
    case .groundRow(let row): return ["kind": "ground", "row": row]
    case .weaponPivot: return ["kind": "pivot"]
    }
}

func commandJSON(_ command: SpriteCommand) -> [String: Any] {
    var object: [String: Any] = [
        "sprite": command.sprite,
        "x": command.position.x,
        "y": command.position.y,
        "depth": command.depth,
        "time": command.time,
        "rotation": command.rotation,
        "scale": command.scale,
        "flipX": command.flipX,
        "flipY": command.flipY,
        "alpha": command.alpha,
        "anchor": anchorJSON(command.anchor),
        "additive": command.additive,
    ]
    if let tint = command.tint {
        object["tint"] = [tint.r, tint.g, tint.b]
        object["tintAmount"] = command.tintAmount
    }
    return object
}

func hudJSON(_ world: World) -> [String: Any] {
    let run = world.run
    let weapon = run.loadout.activeWeapon
    let minimap = world.dungeon.rooms.filter(\.discovered).map { room -> [String: Any] in
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
        return ["x": room.cells[0].x, "y": room.cells[0].y, "kind": key,
                "current": room.index == world.currentRoom]
    }

    return [
        "health": run.health,
        "maxHealth": run.maxHealth,
        "armor": run.armor,
        "coins": run.coins,
        "keys": run.keys,
        "blanks": run.blanks,
        "depth": run.depth,
        "theme": run.theme,
        "weapon": weapon?.def.name ?? "",
        "ammo": weapon?.ammoText ?? "",
        "weapons": run.loadout.weapons.map { $0.def.sprite },
        "activeWeapon": run.loadout.activeWeaponIndex,
        "items": run.loadout.items.map { "item/\($0)" },
        "synergies": run.loadout.synergyDefs.map(\.name),
        "minimap": minimap,
        "currentCell": ["x": world.dungeon.rooms[world.currentRoom].cells[0].x,
                        "y": world.dungeon.rooms[world.currentRoom].cells[0].y],
        "boss": world.activeBoss.map { boss -> [String: Any] in
            var name = "BOSS"
            if case let .boss(id) = boss.kind,
               let def = BossCatalog.boss(id) { name = def.name }
            return ["name": name, "fraction": boss.healthFraction]
        } as Any,
    ]
}

// -- main ---------------------------------------------------------------------

let options = parseOptions()
guard let character = CharacterCatalog.character(options.character) else {
    FileHandle.standardError.write(
        Data("unknown character '\(options.character)'\n".utf8))
    exit(1)
}

var run = RunState(seed: options.seed, character: character)
if options.scenario == "boss" { run.depth = 1 }
let world = World(run: run)

// A few items so the snapshot exercises the HUD and the synergy display.
if options.scenario != "start" {
    for id in ["ember_core", "bloodstone", "feather_boots"] {
        _ = world.run.loadout.add(item: id)
    }
    _ = world.run.loadout.add(weapon: WeaponCatalog.scattergun)
}

place(world: world, scenario: options.scenario)

var input = InputState()
for frame in 0..<options.frames {
    input = scriptedInput(world: world, frame: frame)
    world.step(dt: 1.0 / 60.0, input: input)
    _ = world.drainEvents()
    if world.playerDead { break }
}

let staticCommands = SceneSnapshot.staticCommands(for: world.dungeon)
let dynamicCommands = SceneSnapshot.dynamicCommands(for: world)
let camera = world.playerActor?.position ?? world.dungeon.rooms[0].center

let payload: [String: Any] = [
    "camera": ["x": camera.x, "y": camera.y],
    "viewport": ["width": options.width, "height": options.height],
    "theme": world.dungeon.theme,
    "seed": seedText(options.seed),
    "scenario": options.scenario,
    "frames": options.frames,
    "sprites": (staticCommands + dynamicCommands)
        .sorted { $0.depth < $1.depth }
        .map(commandJSON),
    "hud": hudJSON(world),
]

let data = try JSONSerialization.data(withJSONObject: payload,
                                      options: [.sortedKeys])
try data.write(to: URL(fileURLWithPath: options.output))

print("wrote \(options.output): \(staticCommands.count) static + "
      + "\(dynamicCommands.count) dynamic sprites, "
      + "\(world.livingEnemies.count) enemies alive, "
      + "player \(Int(world.run.health))/\(Int(world.run.maxHealth)) hp")
