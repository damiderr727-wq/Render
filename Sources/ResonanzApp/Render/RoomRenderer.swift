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
        scatterEdgeProps(room: room)
        buildDecor(room: room)
        buildAtmosphere(room: room)
    }

    // MARK: - Hintergrund

    private func buildBackdrop(room: Room) {
        let region = room.region.rawValue

        // Eine Himmelsflaeche hinter allem. Die Schichten selbst sind genau
        // bildschirmhoch und werden nur waagerecht gekachelt - senkrecht
        // wiederholt gaebe der Verlauf eine sichtbare Naht.
        let sky = SKSpriteNode(color: skyColor(for: room.region),
                               size: CGSize(width: Double(room.width) * tileSize + 512,
                                            height: Double(room.height) * tileSize + 512))
        sky.anchorPoint = CGPoint(x: 0, y: 1)
        sky.position = CGPoint(x: -256, y: 256)
        sky.zPosition = -10
        layers.backdrop.addChild(sky)

        for layer in 0..<3 {
            let name = "\(region)_bg\(layer)"
            guard let info = atlas.frame(name) else { continue }
            let factor = atlas.parallaxFactors[name] ?? [0.15, 0.35, 0.6][layer]

            // Genug Kacheln, um den ganzen Raum abzudecken.
            let container = SKNode()
            container.zPosition = CGFloat(layer)
            let columns = Int(ceil(Double(room.width) * tileSize / Double(info.size.width))) + 2

            // In Raeumen, die hoeher sind als ein Bildschirm, bleibt oben
            // Himmel stehen. Das ist gewollt: die Schichten sind in ihren
            // obersten Reihen durchsichtig gezeichnet (`in_dunst` in
            // gen_backdrops.py) und gehen ohne Kante in ihn ueber, statt
            // irgendwo in der Luft aufzuhoeren.
            for column in 0..<columns {
                let sprite = SKSpriteNode(texture: info.texture, size: info.size)
                sprite.anchorPoint = CGPoint(x: 0, y: 0)
                sprite.position = CGPoint(x: CGFloat(column) * info.size.width,
                                          y: -Double(room.height) * tileSize)
                sprite.alpha = [0.55, 0.7, 0.85][layer]

                // Jede zweite Kachel gespiegelt. Aneinandergereiht stiess
                // sonst die rechte Kante der Schicht auf ihre eigene linke,
                // und in breiten Raeumen lief alle 512 Pixel eine harte
                // senkrechte Naht durchs Bild. Gespiegelt trifft jede Kante
                // auf sich selbst, und die Naht verschwindet.
                //
                // Der Preis: auf den gespiegelten Kacheln kommt das Licht
                // von links statt von rechts. In dieser Entfernung, hinter
                // zwei Schleiern, faellt das nicht auf - eine Naht schon.
                if column % 2 == 1 {
                    sprite.xScale = -1
                    sprite.position.x += info.size.width
                }
                container.addChild(sprite)
            }
            container.userData = ["parallax": factor]
            layers.backdrop.addChild(container)
        }
    }

    /// Verschiebt Hinter- und Vordergrund gegenlaeufig zur Kamera.
    /// Ein Faktor ueber 1 laesst die Schicht schneller laufen als die Welt -
    /// so entsteht der Eindruck, dicht davor zu stehen.
    public func updateParallax(cameraPosition: CGPoint) {
        for container in layers.backdrop.children + layers.foreground.children {
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
                                        + "\((tx &* 31 &+ ty &* 17) % 6)")
                case .platform:
                    // Enden einer Plattform laufen aus, statt abgeschnitten
                    // zu sein - erst dadurch wird sie Teil der Landschaft.
                    var cap = ""
                    if room.tile(tx - 1, ty) != .platform { cap += "l" }
                    if room.tile(tx + 1, ty) != .platform { cap += "r" }
                    node = atlas.sprite("\(region)_platform_\(cap.isEmpty ? "mid" : cap)_"
                                        + "\((tx &* 13 &+ ty &* 7) % 4)")
                case .spike:
                    node = atlas.sprite("\(region)_spike")
                case .slopeUp, .slopeDown, .slopeUpLow, .slopeUpHigh,
                     .slopeDownHigh, .slopeDownLow:
                    let kind: String
                    switch tile {
                    case .slopeUp: kind = "up"
                    case .slopeDown: kind = "down"
                    case .slopeUpLow: kind = "uplow"
                    case .slopeUpHigh: kind = "uphigh"
                    case .slopeDownHigh: kind = "downhigh"
                    default: kind = "downlow"
                    }
                    node = atlas.sprite("\(region)_slope_\(kind)_\((tx &* 17 &+ ty &* 5) % 4)")
                case .dissoWall:
                    node = atlas.sprite("dissowall_0")
                    if let loop = atlas.loop("dissowall") { node.run(loop) }
                case .air:
                    continue
                }

                // Bodenkacheln ragen oben ueber ihr Raster hinaus (Gras,
                // Moos, Wurzeln). Ihr Ursprung steht im Atlas - er darf
                // hier nicht ueberschrieben werden.
                if tile != .solid && tile != .platform && !tile.isSlope {
                    node.anchorPoint = CGPoint(x: 0, y: 1)
                }
                node.position = WorldSpace.sceneTile(tx, ty)
                layers.terrain.addChild(node)

                if tile == .dissoWall {
                    breakableNodes[ty * room.width + tx] = node
                }
            }
        }
    }

    /// Requisiten auf die Kachelnaehte setzen: Steine, Wurzeln, Reisig.
    ///
    /// Das ist der Griff, der handgezeichnete Karten von Kachelkarten
    /// unterscheidet - nicht das Kachelbild selbst, sondern die Dinge, die
    /// quer ueber den Fugen liegen.
    private func scatterEdgeProps(room: Room) {
        let region = room.region.rawValue
        func isSurface(_ tx: Int, _ ty: Int) -> Bool {
            ty > 0 && room.tile(tx, ty) == .solid && room.tile(tx, ty - 1) == .air
        }
        for ty in 1..<room.height {
            for tx in 1..<room.width {
                guard isSurface(tx, ty), isSurface(tx - 1, ty) else { continue }
                let roll = abs((tx &* 2654435761) &+ (ty &* 40503)) % 100
                guard roll < 34 else { continue }
                let name = "edge_\(region)_\((tx &* 7 &+ ty &* 3) % 6)"
                let node = atlas.sprite(name)
                node.position = CGPoint(x: Double(tx) * tileSize,
                                        y: -Double(ty) * tileSize + 2)
                node.zPosition = 2
                // Jede Requisite wiegt sich, aber nicht im Gleichschritt -
                // sonst atmet der ganze Boden wie ein einziges Wesen.
                if let loop = atlas.loop(name) {
                    let versatz = Double((tx &* 13 &+ ty &* 7) % 100) / 100.0
                    node.run(.sequence([.wait(forDuration: versatz), loop]))
                }
                layers.decor.addChild(node)
            }
        }
    }

    /// Staub, der durch den Raum treibt.
    ///
    /// Ein Raum, in dem sich nichts bewegt, wirkt tot - und zwar auch dann,
    /// wenn jede Kachel liebevoll gezeichnet ist. Ein paar Funken, die
    /// langsam quer durchs Bild ziehen, kosten fast nichts und aendern
    /// alles. Sie fliegen nicht zufaellig: jede Region hat ihre Richtung.
    private func buildAmbient(room: Room) {
        let breite = Double(room.width) * tileSize
        let hoehe = Double(room.height) * tileSize
        // Im Hain sinkt der Staub, in den Grotten steigt er auf.
        let steigt: Double
        switch room.region {
        case .hain: steigt = -1
        case .kathedrale: steigt = -0.4
        case .grotten: steigt = 1
        case .dissonanz: steigt = 0.3
        }

        let anzahl = min(48, max(12, room.width * room.height / 90))
        for i in 0..<anzahl {
            let node = atlas.sprite("mote_0")
            if let loop = atlas.loop("mote", speed: 0.5) { node.run(loop) }
            let x = Double((i &* 7919) % 1000) / 1000 * breite
            let y = -Double((i &* 4241) % 1000) / 1000 * hoehe
            node.position = CGPoint(x: x, y: y)
            node.alpha = 0.16 + Double((i &* 37) % 40) / 100
            node.zPosition = 3
            node.setScale(0.6 + Double((i &* 13) % 60) / 100)

            // Eine lange, langsame Schleife. Sie muss nicht aufgehen -
            // niemand schaut einem einzelnen Funken so lange zu.
            let dauer = 9.0 + Double((i &* 29) % 70) / 10
            let weite = 26.0 + Double((i &* 17) % 40)
            node.run(.repeatForever(.sequence([
                .group([.moveBy(x: weite, y: steigt * 34, duration: dauer),
                        .fadeAlpha(to: 0.05, duration: dauer)]),
                .group([.moveBy(x: -weite, y: -steigt * 34, duration: dauer),
                        .fadeAlpha(to: 0.34, duration: dauer)]),
            ])))
            layers.decor.addChild(node)
        }
    }

    /// Welche Seiten der Kachel liegen frei? Daraus waehlt sich die Kante.
    private func edgeKey(room: Room, tx: Int, ty: Int) -> String {
        var key = ""
        if !room.tile(tx, ty - 1).isBlocking { key += "t" }
        if !room.tile(tx - 1, ty).isBlocking { key += "l" }
        if !room.tile(tx + 1, ty).isBlocking { key += "r" }
        if !room.tile(tx, ty + 1).isBlocking { key += "b" }
        // Der Generator liefert alle sechzehn Nachbarschaften - ein
        // Rueckfall auf "Mitte" liesse Felswaende ohne Kante stehen.
        return key.isEmpty ? "mid" : key
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

        buildAmbient(room: room)

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

        // Vorderste Schicht: fast schwarze Massen, laufen schneller als
        // die Kamera und schliessen den Blick nach unten ab.
        if let info = atlas.frame("\(room.region.rawValue)_fg") {
            let container = SKNode()
            container.zPosition = 1
            let columns = Int(ceil(Double(room.width) * tileSize / Double(info.size.width))) + 2
            for column in 0..<columns {
                let sprite = SKSpriteNode(texture: info.texture, size: info.size)
                sprite.anchorPoint = CGPoint(x: 0, y: 0)
                sprite.position = CGPoint(x: CGFloat(column) * info.size.width,
                                          y: -Double(room.height) * tileSize)
                // Wie hinten: gespiegelt gekachelt, sonst steht in breiten
                // Raeumen alle 512 Pixel eine schwarze Kante im Vordergrund.
                if column % 2 == 1 {
                    sprite.xScale = -1
                    sprite.position.x += info.size.width
                }
                container.addChild(sprite)
            }
            container.userData = ["parallax": atlas.parallaxFactors["\(room.region.rawValue)_fg"] ?? 1.3]
            layers.foreground.addChild(container)
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

    /// Der hellste Wert der Region - er steht hinter allem.
    private func skyColor(for region: Region) -> SKColor {
        switch region {
        case .hain: return SKColor(red: 0.49, green: 0.55, blue: 0.58, alpha: 1)
        case .kathedrale: return SKColor(red: 0.56, green: 0.55, blue: 0.63, alpha: 1)
        case .grotten: return SKColor(red: 0.56, green: 0.64, blue: 0.71, alpha: 1)
        case .dissonanz: return SKColor(red: 0.43, green: 0.32, blue: 0.35, alpha: 1)
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
