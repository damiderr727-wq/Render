#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Baut die sichtbare Fassung eines Raums: Hintergrundschichten, Kacheln,
/// Kristalle, Baenke.
///
/// Die Logik rechnet mit y nach unten, SpriteKit mit y nach oben. Alle
/// Umrechnungen laufen ueber `scenePoint` - sonst schleicht sich das
/// Vorzeichen ueberall ein.
public enum WorldSpace {
    public static func scenePoint(_ v: Vec2) -> CGPoint {
        CGPoint(x: v.x, y: -v.y)
    }

    public static func sceneTile(_ tx: Int, _ ty: Int) -> CGPoint {
        CGPoint(x: Double(tx) * tileSize, y: -Double(ty) * tileSize)
    }
}

public final class RoomRenderer {
    private let atlas = AtlasStore.shared

    public struct Layers {
        public let backdrop = SKNode()
        public let terrain = SKNode()
        public let decor = SKNode()
        public let entities = SKNode()
        public let effects = SKNode()
        public let foreground = SKNode()
    }

    public let layers = Layers()
    public let root = SKNode()

    /// Kacheln, die zur Laufzeit verschwinden koennen (verstimmte Sperren).
    private var breakableNodes: [Int: SKNode] = [:]

    public init() {
        layers.backdrop.zPosition = -100
        layers.terrain.zPosition = 0
        layers.decor.zPosition = 10
        layers.entities.zPosition = 20
        layers.effects.zPosition = 30
        layers.foreground.zPosition = 40
        for node in [layers.backdrop, layers.terrain, layers.decor,
                     layers.entities, layers.effects, layers.foreground] {
            root.addChild(node)
        }
    }

    public func build(room: Room) {
        layers.backdrop.removeAllChildren()
        layers.terrain.removeAllChildren()
        layers.decor.removeAllChildren()
        layers.foreground.removeAllChildren()
        breakableNodes.removeAll()

        buildBackdrop(room: room)
        buildTerrain(room: room)
        buildDecor(room: room)
        buildAtmosphere(room: room)
    }

    // MARK: - Hintergrund

    private func buildBackdrop(room: Room) {
        let region = room.region.rawValue
        for layer in 0..<3 {
            let name = "\(region)_bg\(layer)"
            guard let info = atlas.frame(name) else { continue }
            let factor = atlas.parallaxFactors[name] ?? [0.15, 0.35, 0.6][layer]

            // Genug Kacheln, um den ganzen Raum abzudecken.
            let container = SKNode()
            container.zPosition = CGFloat(layer)
            let columns = Int(ceil(Double(room.width) * tileSize / Double(info.size.width))) + 2
            let rows = Int(ceil(Double(room.height) * tileSize / Double(info.size.height))) + 1
            for column in 0..<columns {
                for row in 0..<rows {
                    let sprite = SKSpriteNode(texture: info.texture, size: info.size)
                    sprite.anchorPoint = CGPoint(x: 0, y: 0)
                    sprite.position = CGPoint(
                        x: CGFloat(column) * info.size.width,
                        y: -Double(room.height) * tileSize + CGFloat(row) * info.size.height)
                    sprite.alpha = [0.55, 0.7, 0.85][layer]
                    container.addChild(sprite)
                }
            }
            container.userData = ["parallax": factor]
            layers.backdrop.addChild(container)
        }
    }

    /// Verschiebt die Hintergrundschichten gegenlaeufig zur Kamera.
    public func updateParallax(cameraPosition: CGPoint) {
        for container in layers.backdrop.children {
            guard let factor = container.userData?["parallax"] as? Double else { continue }
            container.position = CGPoint(x: cameraPosition.x * (1 - factor),
                                         y: cameraPosition.y * (1 - factor) * 0.5)
        }
    }

    // MARK: - Gelaende

    private func buildTerrain(room: Room) {
        let region = room.region.rawValue
        for ty in 0..<room.height {
            for tx in 0..<room.width {
                let tile = room.tile(tx, ty)
                guard tile != .air else { continue }
                let node: SKSpriteNode

                switch tile {
                case .solid:
                    node = atlas.sprite("\(region)_solid_\(edgeKey(room: room, tx: tx, ty: ty))_"
                                        + "\((tx &* 31 &+ ty &* 17) % 4)")
                case .platform:
                    node = atlas.sprite("\(region)_platform")
                case .spike:
                    node = atlas.sprite("\(region)_spike")
                case .dissoWall:
                    node = atlas.sprite("dissowall_0")
                    if let loop = atlas.loop("dissowall") { node.run(loop) }
                case .air:
                    continue
                }

                node.anchorPoint = CGPoint(x: 0, y: 1)
                node.position = WorldSpace.sceneTile(tx, ty)
                layers.terrain.addChild(node)

                if tile == .dissoWall {
                    breakableNodes[ty * room.width + tx] = node
                }
            }
        }
    }

    /// Welche Seiten der Kachel liegen frei? Daraus waehlt sich die Kante.
    private func edgeKey(room: Room, tx: Int, ty: Int) -> String {
        var key = ""
        if !room.tile(tx, ty - 1).isBlocking { key += "t" }
        if !room.tile(tx - 1, ty).isBlocking { key += "l" }
        if !room.tile(tx + 1, ty).isBlocking { key += "r" }
        if !room.tile(tx, ty + 1).isBlocking { key += "b" }
        // Der Generator kennt nur eine Auswahl an Kombinationen.
        let known = ["", "t", "tl", "tr", "tlr", "l", "r", "lr", "b", "tb", "blr", "tblr"]
        return known.contains(key) ? (key.isEmpty ? "mid" : key) : "mid"
    }

    /// Laesst eine zerschlagene Sperre zerspringen.
    public func breakTile(room: Room, tx: Int, ty: Int) {
        let key = ty * room.width + tx
        guard let node = breakableNodes.removeValue(forKey: key) else { return }
        node.run(.sequence([
            .group([.fadeOut(withDuration: 0.25), .scale(to: 1.4, duration: 0.25)]),
            .removeFromParent(),
        ]))
    }

    // MARK: - Ausstattung

    private func buildDecor(room: Room) {
        let region = room.region.rawValue

        for decor in room.data.decor {
            let position = WorldSpace.scenePoint(Vec2.entity(decor.x, decor.y))
            switch decor.kind {
            case "crystal":
                let size = clamp(decor.size ?? 1, 0, 2)
                let name = "crystal_\(region)_\(size)"
                let node = atlas.sprite(name)
                node.position = position
                if let loop = atlas.loop(name, speed: 0.5) { node.run(loop) }
                layers.decor.addChild(node)
            case "reed":
                let node = atlas.sprite("reed_\(region)")
                node.position = position
                if let loop = atlas.loop("reed_\(region)", speed: 0.6) { node.run(loop) }
                layers.decor.addChild(node)
            default:
                break
            }
        }

        for bench in room.data.benches {
            let node = atlas.sprite("bench")
            node.position = WorldSpace.scenePoint(Vec2.entity(bench.x, bench.y))
            if let loop = atlas.loop("bench", speed: 0.4) { node.run(loop) }
            layers.decor.addChild(node)
        }

        for lore in room.data.lore {
            // Inschriften sind nur ein leiser Funke, bis man davorsteht.
            let node = atlas.sprite("mote_0")
            node.position = WorldSpace.scenePoint(Vec2.entity(lore.x, lore.y - 0.7))
            node.alpha = 0.7
            node.run(.repeatForever(.sequence([
                .moveBy(x: 0, y: 3, duration: 1.4),
                .moveBy(x: 0, y: -3, duration: 1.4),
            ])))
            if let loop = atlas.loop("mote", speed: 0.5) { node.run(loop) }
            layers.decor.addChild(node)
        }
    }

    /// Dunst, Staubflug und die Verdunklung tiefer Regionen.
    private func buildAtmosphere(room: Room) {
        let width = Double(room.width) * tileSize
        let height = Double(room.height) * tileSize

        // Schwebende Klangfunken.
        var rng = Rng(seed: UInt64(abs(room.id.hashValue)) | 1)
        let count = min(70, room.width * room.height / 90)
        for _ in 0..<count {
            let mote = SKSpriteNode(color: tint(for: room.region), size: CGSize(width: 1, height: 1))
            mote.position = CGPoint(x: rng.range(0, width), y: -rng.range(0, height))
            mote.alpha = rng.range(0.15, 0.5)
            let drift = rng.range(6, 22)
            let duration = rng.range(4, 11)
            mote.run(.repeatForever(.sequence([
                .moveBy(x: rng.range(-10, 10), y: drift, duration: duration),
                .moveBy(x: rng.range(-10, 10), y: -drift, duration: duration),
            ])))
            mote.run(.repeatForever(.sequence([
                .fadeAlpha(to: 0.05, duration: rng.range(1.5, 4)),
                .fadeAlpha(to: rng.range(0.3, 0.6), duration: rng.range(1.5, 4)),
            ])))
            layers.decor.addChild(mote)
        }

        if room.data.darkness > 0.01 {
            let veil = SKSpriteNode(color: .black,
                                    size: CGSize(width: width + 64, height: height + 64))
            veil.anchorPoint = CGPoint(x: 0, y: 1)
            veil.position = CGPoint(x: -32, y: 32)
            veil.alpha = CGFloat(room.data.darkness)
            veil.zPosition = 5
            veil.blendMode = .alpha
            layers.foreground.addChild(veil)
        }
    }

    private func tint(for region: Region) -> SKColor {
        switch region {
        case .hain: return SKColor(red: 0.50, green: 0.91, blue: 0.85, alpha: 1)
        case .kathedrale: return SKColor(red: 0.90, green: 0.70, blue: 1.00, alpha: 1)
        case .grotten: return SKColor(red: 0.56, green: 0.84, blue: 1.00, alpha: 1)
        case .dissonanz: return SKColor(red: 0.76, green: 0.25, blue: 0.37, alpha: 1)
        }
    }
}
#endif
