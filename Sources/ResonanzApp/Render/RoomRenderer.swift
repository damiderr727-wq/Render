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

    /// Wie lange der Raum schon steht. Nur die Wolken brauchen sie: sie
    /// laufen von selbst und nicht, weil die Kamera laeuft.
    private var zeit: Double = 0

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
        buildSockel(room: room)
        buildTerrain(room: room)
        scatterEdgeProps(room: room)
        scatterHangProps(room: room)
        buildDecor(room: room)
        buildAtmosphere(room: room)
    }

    // MARK: - Hintergrund

    private func buildBackdrop(room: Room) {
        // Die Kulisse darf von der Region abweichen - siehe RoomData.
        let region = room.data.backdrop ?? room.region.rawValue

        // Eine Himmelsflaeche hinter allem. Die Schichten selbst sind genau
        // bildschirmhoch und werden nur waagerecht gekachelt - senkrecht
        // wiederholt gaebe der Verlauf eine sichtbare Naht.
        // Und zwar als *Verlauf*, nicht als Flaeche: ein schmaler Streifen
        // aus dem Atlas, ueber die ganze Raumhoehe gezogen. Vorher stand
        // hier eine einzige Farbe, und die traf den Verlauf der Kulisse
        // nur an einem Ende - am anderen lief eine waagerechte Kante
        // quer durchs Bild.
        let himmelGroesse = CGSize(width: Double(room.width) * tileSize + 512,
                                   height: Double(room.height) * tileSize + 512)
        let sky: SKSpriteNode
        if let streifen = atlas.frame("\(region)_himmel") {
            sky = SKSpriteNode(texture: streifen.texture, size: himmelGroesse)
        } else {
            sky = SKSpriteNode(color: skyColor(for: region, fallback: room.region),
                               size: himmelGroesse)
        }
        sky.anchorPoint = CGPoint(x: 0, y: 1)
        sky.position = CGPoint(x: -256, y: 256)
        sky.zPosition = -10
        layers.backdrop.addChild(sky)

        // Vier Schichten, nicht drei. Die unterste traegt nur noch Werte
        // ohne Form - der Hintergrund des Hintergrunds. Ohne sie sitzen
        // die erkennbaren Silhouetten direkt auf dem Himmel.
        for layer in 0..<4 {
            let name = "\(region)_bg\(layer)"
            guard let info = atlas.frame(name) else { continue }
            let factor = atlas.parallaxFactors[name] ?? [0.0, 0.06, 0.14, 0.27][layer]

            // Genug Kacheln, um den ganzen Raum abzudecken.
            let container = SKNode()
            container.zPosition = CGFloat(layer)
            let columns = Int(ceil(Double(room.width) * tileSize / Double(info.size.width))) + 2

            // In Raeumen, die hoeher sind als ein Bildschirm, bleibt oben
            // Himmel stehen. Das ist gewollt: die Schichten sind in ihren
            // obersten Reihen durchsichtig gezeichnet (`in_dunst` in
            // gen_backdrops.py) und gehen ohne Kante in ihn ueber, statt
            // irgendwo in der Luft aufzuhoeren.
            // Schicht 0 ist Luft und haengt oben im Raum, alle anderen
            // stehen unten auf dem Boden. Bodenbuendig gehaengt landete
            // der Mond in einem hohen Raum auf halber Hoehe zwischen den
            // Plattformen - ein Mond gehoert nach oben.
            let unterkante = layer == 0
                ? -Double(info.size.height)
                : -Double(room.height) * tileSize

            for column in 0..<columns {
                let sprite = SKSpriteNode(texture: info.texture, size: info.size)
                sprite.anchorPoint = CGPoint(x: 0, y: 0)
                sprite.position = CGPoint(x: CGFloat(column) * info.size.width,
                                          y: unterkante)
                // Deckend. Die Staffelung nach hinten steckt in der Farbe
                // der Schicht selbst (`in_ferne` in gen_backdrops.py), nicht
                // in ihrer Deckkraft. Halbdurchsichtig hiess: man sah den
                // Mond durch den Baumstamm.
                sprite.alpha = 1.0

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

        buildWolken(room: room, region: region)
    }

    /// Wolken. Sie gibt es nur ueber der Bruecke - dem einzigen Gebiet
    /// unter freiem Himmel.
    ///
    /// Sie sind keine gewoehnliche Kulissenschicht: eine Kulisse laeuft
    /// nur, weil die Kamera laeuft, und ein Himmel, der still steht,
    /// waehrend man hundert Schritte ueber ein Tal geht, ist eine
    /// Tapete. Also traegt jedes Band zusaetzlich einen Eigenlauf in
    /// Pixeln je Sekunde (`drift` im Atlas), und der wird in
    /// `updateParallax` aufaddiert.
    private func buildWolken(room: Room, region: String) {
        for stufe in 0..<2 {
            let name = "\(region)_wolken\(stufe)"
            guard let info = atlas.frame(name) else { continue }
            let breite = Double(info.size.width)
            let container = SKNode()
            // Zwischen Luft (0) und Ferne (1): hinter den Bergen, vor
            // der Sonne.
            container.zPosition = 0.3 + CGFloat(stufe) * 0.3

            // Zwei Kacheln mehr, und zwei davon links vom Nullpunkt. Das
            // Band wandert nach links aus dem Bild; ohne den Vorlauf
            // rechts risse rechts eine Luecke auf.
            let spalten = Int(ceil((Double(room.width) * tileSize) / breite)) + 4
            for spalte in 0..<spalten {
                let sprite = SKSpriteNode(texture: info.texture, size: info.size)
                sprite.anchorPoint = CGPoint(x: 0, y: 0)
                sprite.position = CGPoint(x: (Double(spalte) - 2) * breite,
                                          y: -Double(info.size.height))
                container.addChild(sprite)
            }
            container.userData = [
                "parallax": atlas.parallaxFactors[name] ?? 0.03,
                "drift": atlas.driftFactors[name] ?? 0,
                "breite": breite,
            ]
            layers.backdrop.addChild(container)
        }
    }

    /// Verschiebt Hinter- und Vordergrund gegenlaeufig zur Kamera.
    /// Ein Faktor ueber 1 laesst die Schicht schneller laufen als die Welt -
    /// so entsteht der Eindruck, dicht davor zu stehen.
    public func updateParallax(cameraPosition: CGPoint, dt: Double = 0) {
        zeit += dt
        for container in layers.backdrop.children + layers.foreground.children {
            guard let factor = container.userData?["parallax"] as? Double else { continue }
            // Durchgehend in Double gerechnet und erst am Ende gesetzt.
            // Gemischt mit CGFloat haengt es an der impliziten Umwandlung,
            // welchen Typ der Ausdruck bekommt - und die faellt auf jeder
            // Plattform anders aus als hier gedacht.
            var x = Double(cameraPosition.x) * (1 - factor)
            // Eigenlauf, auf eine Bandbreite zurueckgefaltet: sonst
            // waechst der Versatz ueber eine lange Sitzung ins
            // Unermessliche und das Band schiebt sich aus dem Raum.
            if let drift = container.userData?["drift"] as? Double, drift != 0,
               let breite = container.userData?["breite"] as? Double, breite > 0 {
                x += (drift * zeit).truncatingRemainder(dividingBy: breite)
            }
            container.position = CGPoint(
                x: x, y: Double(cameraPosition.y) * (1 - factor) * 0.5)
        }
    }

    /// Der Unterbau der Plattformen.
    ///
    /// In den Vorbildern schwebt keine Plattform - jede sitzt auf einer
    /// Konsole, und dahinter liegt eine abgeschattete Ebene. Unsere waren
    /// Bretter in der Luft. Der Sockel haengt unter der Plattform heraus
    /// und liegt hinter dem Gelaende.
    private func buildSockel(room: Room) {
        let region = room.region.rawValue
        for ty in 0..<room.height {
            var tx = 0
            while tx < room.width {
                guard room.tile(tx, ty) == .platform else { tx += 1; continue }
                let start = tx
                while tx < room.width, room.tile(tx, ty) == .platform { tx += 1 }

                // Ein einziger Sockel in der Mitte reichte nur fuer kurze
                // Plattformen. Ueber zwanzig Kacheln hinweg sass darunter
                // ein handbreiter Klumpen und links und rechts davon
                // schwebte das Brett weiter. Also alle drei Kacheln einer -
                // sie ueberlappen sich und ergeben eine durchgehende Masse.
                let breite = tx - start
                let anzahl = max(1, Int((Double(breite) / 3.0).rounded()))
                for k in 0..<anzahl {
                    let mitte = Double(start)
                        + Double(breite) * (Double(k) + 0.5) / Double(anzahl)
                    let node = atlas.sprite(
                        "sockel_\(region)_\(variante(Int(mitte), ty, 3, salz: 6 &+ k))")
                    node.anchorPoint = CGPoint(x: 0.5, y: 1.0)
                    node.position = CGPoint(x: mitte * tileSize,
                                            y: -Double(ty) * tileSize - 4)
                    node.zPosition = -1
                    layers.terrain.addChild(node)
                }
            }
        }
    }

    /// Welche Variante einer Kachel an dieser Stelle steht.
    ///
    /// Vorher stand hier `(tx * 31 + ty * 17) % n`. Das ist keine
    /// Streuung, sondern eine Rechnung: geht man eine Kachel nach
    /// rechts, steigt der Wert um genau eins, also laufen dieselben
    /// Varianten in schnurgeraden Diagonalen durch den ganzen Raum. Man
    /// sieht es erst, wenn die Kacheln selbst Zeichnung haben - dann
    /// aber sofort, als schraeges Streifenmuster ueber dem Boden.
    ///
    /// Eine Hashfunktion streut stattdessen: benachbarte Kacheln
    /// bekommen unzusammenhaengende Werte, und das Auge findet keine
    /// Periode mehr.
    private func variante(_ tx: Int, _ ty: Int, _ anzahl: Int, salz: Int = 0) -> Int {
        var h = UInt32(truncatingIfNeeded: tx &* 73_856_093)
        h ^= UInt32(truncatingIfNeeded: ty &* 19_349_663)
        h ^= UInt32(truncatingIfNeeded: salz &* 83_492_791)
        h ^= h >> 13
        h = h &* 2_654_435_761
        h ^= h >> 16
        return Int(h % UInt32(anzahl))
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
                                        + "\(variante(tx, ty, 6))")
                case .platform:
                    // Enden einer Plattform laufen aus, statt abgeschnitten
                    // zu sein - erst dadurch wird sie Teil der Landschaft.
                    var cap = ""
                    if room.tile(tx - 1, ty) != .platform { cap += "l" }
                    if room.tile(tx + 1, ty) != .platform { cap += "r" }
                    node = atlas.sprite("\(region)_platform_\(cap.isEmpty ? "mid" : cap)_"
                                        + "\(variante(tx, ty, 4, salz: 1))")
                case .balken:
                    var bcap = ""
                    if room.tile(tx - 1, ty) != .balken { bcap += "l" }
                    if room.tile(tx + 1, ty) != .balken { bcap += "r" }
                    node = atlas.sprite("\(region)_balken_\(bcap.isEmpty ? "mid" : bcap)_"
                                        + "\(variante(tx, ty, 3, salz: 4))")
                case .spike, .spikeDown, .spikeLeft, .spikeRight:
                    node = atlas.sprite("\(region)_spike\(tile.hazardSuffix)")
                case .ceilDownHigh, .ceilDownLow, .ceilUpLow, .ceilUpHigh:
                    node = atlas.sprite("\(region)_ceil_\(tile.ceilingSuffix)_"
                                        + "\(variante(tx, ty, 4, salz: 2))")
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
                    node = atlas.sprite("\(region)_slope_\(kind)_\(variante(tx, ty, 4, salz: 3))")
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
        // Raeume mit eigener Kulisse bekommen keine Regionsrequisiten. Im
        // Schattentempel wuchs sonst Gras auf den Bodenplatten - er hat
        // seinen Kachelsatz vom Hain geerbt, nicht dessen Vegetation.
        guard room.data.backdrop == nil else { return }
        let region = room.region.rawValue
        func isSurface(_ tx: Int, _ ty: Int) -> Bool {
            ty > 0 && room.tile(tx, ty) == .solid && room.tile(tx, ty - 1) == .air
        }
        for ty in 1..<room.height {
            for tx in 1..<room.width {
                guard isSurface(tx, ty), isSurface(tx - 1, ty) else { continue }
                let roll = abs((tx &* 2654435761) &+ (ty &* 40503)) % 100
                guard roll < 34 else { continue }
                let name = "edge_\(region)_\(variante(tx, ty, 6, salz: 4))"
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
    /// Dasselbe an der Decke.
    ///
    /// Der Boden sieht gut aus, weil Requisiten quer ueber seinen Kacheln
    /// liegen. Die Decke hatte nichts davon und blieb deshalb eine Treppe
    /// aus Rechtecken, egal wie fein das Hoehenprofil war. An jeder Stufe
    /// haengt jetzt etwas darueber - genau dort, wo die Waagerechte
    /// sichtbar waere.
    private func scatterHangProps(room: Room) {
        guard room.data.backdrop == nil else { return }
        let region = room.region.rawValue

        func isCeiling(_ tx: Int, _ ty: Int) -> Bool {
            room.tile(tx, ty) == .solid && room.tile(tx, ty + 1) == .air
        }

        for ty in 0..<(room.height - 1) {
            for tx in 1..<room.width where isCeiling(tx, ty) {
                let step = !isCeiling(tx - 1, ty) || !isCeiling(tx + 1, ty)
                if !step, (tx &* 2654435761 &+ ty &* 40503) % 100 >= 22 { continue }
                let node = atlas.sprite("hang_\(region)_\(variante(tx, ty, 6, salz: 5))")
                node.anchorPoint = CGPoint(x: 0.5, y: 1.0)
                node.position = CGPoint(x: Double(tx) * tileSize + tileSize / 2,
                                        y: -Double(ty + 1) * tileSize + 2)
                node.zPosition = 2
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
        // Ueber der Schlucht steht ein Aufwind. Als einziges Gebiet
        // unter freiem Himmel traegt sie ihren Staub nach oben davon.
        case .bruecke: steigt = 0.8
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
    /// Die Farbe hinter allen Schichten. Kulissen, die keine Region sind,
    /// bringen ihre eigene mit - der Tempel hat gar keinen Himmel.
    private func skyColor(for kulisse: String, fallback: Region) -> SKColor {
        if kulisse == "tempel" {
            return SKColor(red: 0.055, green: 0.06, blue: 0.085, alpha: 1)
        }
        return skyColor(for: Region(rawValue: kulisse) ?? fallback)
    }

    /// Die Farbe hinter allen Schichten.
    ///
    /// Sie muss dem *unteren* Ende des Himmelsverlaufs entsprechen, den
    /// `gen_backdrops.py` in Schicht 0 zeichnet. Schicht 0 haengt oben im
    /// Raum; was darunter noch frei bleibt, fuellt diese Farbe, und jede
    /// Abweichung liefe dort als waagerechte Kante quer durchs Bild.
    private func skyColor(for region: Region) -> SKColor {
        switch region {
        case .hain: return SKColor(red: 0.208, green: 0.196, blue: 0.176, alpha: 1)
        case .kathedrale: return SKColor(red: 0.188, green: 0.153, blue: 0.192, alpha: 1)
        case .grotten: return SKColor(red: 0.137, green: 0.180, blue: 0.243, alpha: 1)
        case .dissonanz: return SKColor(red: 0.125, green: 0.078, blue: 0.098, alpha: 1)
        // Das untere Ende des Tageshimmels aus `gen_backdrops.py`
        // (#eef3ec). Hier ist es hell - als Einziges im Spiel.
        case .bruecke: return SKColor(red: 0.933, green: 0.953, blue: 0.925, alpha: 1)
        }
    }

    private func tint(for region: Region) -> SKColor {
        switch region {
        case .hain: return SKColor(red: 0.50, green: 0.91, blue: 0.85, alpha: 1)
        case .kathedrale: return SKColor(red: 0.90, green: 0.70, blue: 1.00, alpha: 1)
        case .grotten: return SKColor(red: 0.56, green: 0.84, blue: 1.00, alpha: 1)
        case .dissonanz: return SKColor(red: 0.76, green: 0.25, blue: 0.37, alpha: 1)
        case .bruecke: return SKColor(red: 1.00, green: 0.85, blue: 0.63, alpha: 1)
        }
    }
}
#endif
