import SceneKit
import UIKit
import simd
import Combine

// Villa Nachtschatten - Kern: Kamera-Zonen, Kollision, Bewegung.
// Der Villa-Aufbau steckt in Villa.swift.

struct WallBox {
    let x0: Float; let x1: Float; let z0: Float; let z1: Float
    /// Hoehenbereich. Eine Wand im ersten Stock darf im Erdgeschoss nicht sperren.
    var y0: Float = -1.0
    var y1: Float = 100.0
    /// Tuersperren werden umgeschaltet statt entfernt - der Index bleibt gueltig.
    var on: Bool = true
    /// Nur Waende und Tuerblaetter draengen die Kamera zurueck. Moebel nicht -
    /// sonst schwenkt sie an jedem Stuhl und Tisch herum.
    var blocksCamera: Bool = true
    /// Treppenlaeufe sollen die KAMERA stoppen, aber den Spieler durchlassen -
    /// er laeuft ja darauf. Ohne das gleitet die Kamera durch die Stufen.
    var blocksPlayer: Bool = true
}

/// Begehbare Flaeche. Ist y0 == y1, ist sie eben, sonst eine Rampe (Treppe).
/// Der Spieler bekommt seine Hoehe aus der Flaeche unter ihm.
struct FloorArea {
    let x0: Float, x1: Float, z0: Float, z1: Float
    let y0: Float, y1: Float
    let alongZ: Bool
    /// Rampen haben Vorrang vor ebenen Flaechen. Ohne das gewinnt der Boden
    /// unter der Treppe immer, weil er zur aktuellen Hoehe den Abstand 0 hat -
    /// der Spieler steigt dann nie.
    var isRamp: Bool { y0 != y1 }

    func height(_ x: Float, _ z: Float) -> Float {
        if y0 == y1 { return y0 }
        let t = alongZ ? (z - z0) / (z1 - z0) : (x - x0) / (x1 - x0)
        return y0 + (y1 - y0) * min(1, max(0, t))
    }
    func contains(_ x: Float, _ z: Float) -> Bool {
        x >= x0 && x <= x1 && z >= z0 && z <= z1
    }
}

// Feste Kamera pro Raumbereich. straight = achsenparallel (Raeume),
// schraege Winkel nur in den Fluren.
struct CamZone {
    let x0: Float, x1: Float, z0: Float, z1: Float
    let pos: SCNVector3
    let look: SCNVector3
    let fov: CGFloat          // pro Raum eigener Bildwinkel
    let follow: Bool          // true = Standort haengt am Spieler
    let track: Float          // 0 = starrer Blickpunkt, 1 = blickt direkt auf den Spieler
    let margin: Float         // wie weit die mitlaufende Kamera vom Zonenrand wegbleibt
    let yLo: Float            // ab welcher Spielerhoehe diese Zone gilt
    let yHi: Float            // bis zu welcher
    /// Blickrichtung der Zone. Der Kameraversatz wird darum gedreht - beim
    /// Betreten dreht sich die Kamera so, dass der Raum "von vorn" steht.
    let yaw: Float
}

class GameController: NSObject, ObservableObject, SCNSceneRendererDelegate {
    let scene = SCNScene()
    let player = SCNNode()
    var rig: PlayerRig!
    let cameraNode = SCNNode()
    var move = CGVector.zero
    var solids: [WallBox] = []
    var camZones: [CamZone] = []
    @Published var equipped: ItemKind? = nil
    @Published var floorIdx = 0            // 0 = Erdgeschoss, 1 = Obergeschoss
    var attackCooldown: Float = 0
    var dodgeT: Float = -1
    var dodgeDirX: Float = 0
    var dodgeDirZ: Float = 0
    var dodgeCooldown: Float = 0
    /// Unverwundbarkeits-Fenster - vorbereitet fuer das Kampfsystem.
    var invulnT: Float = 0
    /// Laterne: haengt am Spieler und leuchtet mit, wenn sie ausgeruestet ist.
    private let lanternNode = SCNNode()
    @Published var lanternOn = false
    /// Lichtschaft-Flaechen samt Normalen - werden gegen den Blick ausgeblendet.
    var shaftPlanes: [(SCNNode, SIMD3<Float>)] = []
    /// Alle Lichter, die Schatten werfen. Jedes davon rendert die sichtbare
    /// Geometrie ein zusaetzliches Mal - aus grosser Hoehe ist das die ganze
    /// Villa auf einmal, und genau dort bricht es weg.
    var shadowLights: [SCNNode] = []
    var sleepers: [Sleeper] = []
    /// Moebel-Editor: je ein Gruppenknoten pro Eintrag in furnitureList.
    var furnitureNodes: [SCNNode] = []
    /// Bauposition je Stueck - der Drehpunkt bleibt dort stehen.
    var furnitureBase: [(Float, Float)] = []
    var wallNodes: [SCNNode] = []
    var wallBase: [(Float, Float)] = []
    @Published var selectedWall: Int? = nil
    @Published var wallMode = false
    @Published var editMode = false
    /// Freie Kamera zum Begutachten - loest sich vom Spieler.
    @Published var freeCam = false
    var fcPos = SCNVector3(0, 3, 8)
    var fcYaw: Float = 0
    var fcPitch: Float = -0.25
    var fcLift: Float = 0
    private var shadowsOff = false
    @Published var selectedFurniture: Int? = nil
    private let selMarker = SCNNode()
    let audio = AudioController()
    var floorAreas: [FloorArea] = []
    /// Wasserflaechen: Material plus Fliessgeschwindigkeit in UV pro Sekunde.
    var waterLayers: [(mat: SCNMaterial, sx: Float, sy: Float, rep: Float)] = []
    /// Flackerlichter: Knoten, Grundhelligkeit und ein Phasenversatz.
    var flickerLights: [(node: SCNNode, base: CGFloat, seed: Float)] = []
    private var animTime: Float = 0

    // --- Spielzustand fuer die Oberflaeche ---
    @Published var prompt: String? = nil        // Text am Aktionsknopf
    @Published var inventory: [ItemKind] = []
    @Published var toast: String? = nil         // kurze Einblendung
    @Published var mapOpen = false
    @Published var journalOpen = false
    @Published var debugOn = false
    /// Helligkeitsregler fuers Testen. 1.0 = wie ausgeliefert.
    @Published var brightness: Float = 1.0
    /// Figurenstil. Umschalten baut die Figur neu auf.
    @Published var cartoon = false
    private var ambientNode: SCNNode?
    private var keyNode: SCNNode?
    private let ambientBase: CGFloat = 1650
    private let keyBase: CGFloat = 780
    private let exposureBase: CGFloat = 1.05
    @Published var debugText = ""
    @Published var rooms: [RoomInfo] = MapData.rooms
    @Published var currentRoom: String = ""
    /// Position fuer die Karte, wird nur gelegentlich nachgefuehrt
    @Published var mapX: Float = 0
    @Published var mapZ: Float = 0

    var doors: [Door] = []
    var pickups: [Pickup] = []
    private var nearDoor: Door?
    private var nearPickup: Pickup?
    private var scanTick = 0
    private var toastID = 0
    private var smoothPos = SCNVector3Zero
    private var smoothAim = SCNVector3Zero
    private var currentZone = -1
    private var lastTime: TimeInterval = 0
    private var vx: Float = 0
    private var vz: Float = 0
    private var faceAngle: Float = 0
    private var useFx: Float = 0
    private var useFz: Float = -1
    private var useRx: Float = 1
    private var useRz: Float = 0

    let wallMat: SCNMaterial = {
        let m = SCNMaterial()
        m.lightingModel = .lambert
        m.diffuse.contents = UIColor(red: 0.46, green: 0.45, blue: 0.41, alpha: 1)
        return m
    }()

    lazy var wainscotMat: SCNMaterial = texMat(Tex.wainscot, 5, 1)
    lazy var frameMat: SCNMaterial = texMat(Tex.wainscot, 1, 1)
    lazy var ceilMat: SCNMaterial = {
        let m = texMat(Tex.plaster, 6, 6)
        m.isDoubleSided = false   // von oben unsichtbar, von unten normal
        return m
    }()

    override init() {
        super.init()
        buildScene()
    }

    // --- Wandsegment ---
    func wall(_ width: CGFloat, _ pos: SCNVector3, _ rotY: Float, _ mat: SCNMaterial? = nil,
              wainscot: Bool = true, h: CGFloat = 4, base: Float = 0) {
        let box = SCNBox(width: width, height: h, length: 0.3, chamferRadius: 0)
        box.firstMaterial = mat ?? wallMat
        let n = SCNNode(geometry: box)
        n.position = SCNVector3(pos.x, base + Float(h / 2), pos.z)
        n.eulerAngles.y = rotY
        scene.rootNode.addChildNode(n)

        if wainscot {
            let wb = SCNBox(width: width, height: 0.95, length: 0.38, chamferRadius: 0)
            wb.firstMaterial = wainscotMat
            let wn = SCNNode(geometry: wb)
            wn.position = SCNVector3(pos.x, base + 0.475, pos.z)
            wn.eulerAngles.y = rotY
            scene.rootNode.addChildNode(wn)
        }

        let w = Float(width)
        let wy0 = base, wy1 = base + Float(h)
        if abs(rotY) < 0.01 {
            solids.append(WallBox(x0: pos.x - w/2, x1: pos.x + w/2, z0: pos.z - 0.19, z1: pos.z + 0.19, y0: wy0, y1: wy1))
        } else {
            solids.append(WallBox(x0: pos.x - 0.19, x1: pos.x + 0.19, z0: pos.z - w/2, z1: pos.z + w/2, y0: wy0, y1: wy1))
        }
    }

    // schneidet Oeffnungen aus einer Spanne heraus
    private func segments(_ a0: Float, _ a1: Float, _ gaps: [(Float, Float)]) -> [(Float, Float)] {
        var segs: [(Float, Float)] = [(a0, a1)]
        for g in gaps {
            let ga = g.0 - g.1 / 2, gb = g.0 + g.1 / 2
            var out: [(Float, Float)] = []
            for s in segs {
                if gb <= s.0 || ga >= s.1 { out.append(s); continue }
                if ga > s.0 { out.append((s.0, ga)) }
                if gb < s.1 { out.append((gb, s.1)) }
            }
            segs = out
        }
        return segs
    }

    private let doorH: Float = 2.35

    // Sturz + Zarge ueber/neben einer Oeffnung
    private func opening(_ center: SCNVector3, _ width: Float, _ rotY: Float, _ mat: SCNMaterial, _ h: CGFloat) {
        let base = center.y
        // Sturz
        let lh = Float(h) - doorH
        if lh > 0.05 {
            let b = SCNBox(width: CGFloat(width), height: CGFloat(lh), length: 0.3, chamferRadius: 0)
            b.firstMaterial = mat
            let n = SCNNode(geometry: b)
            n.position = SCNVector3(center.x, base + doorH + lh / 2, center.z)
            n.eulerAngles.y = rotY
            scene.rootNode.addChildNode(n)
        }
        // Zarge: zwei Pfosten + Balken
        let along: SCNVector3 = abs(rotY) < 0.01 ? SCNVector3(1, 0, 0) : SCNVector3(0, 0, 1)
        for s in [-1, 1] {
            let b = SCNBox(width: 0.14, height: CGFloat(doorH), length: 0.42, chamferRadius: 0)
            b.firstMaterial = frameMat
            let n = SCNNode(geometry: b)
            let d = (width / 2 - 0.07) * Float(s)
            n.position = SCNVector3(center.x + along.x * d, base + doorH / 2, center.z + along.z * d)
            n.eulerAngles.y = rotY
            scene.rootNode.addChildNode(n)
        }
        let top = SCNBox(width: CGFloat(width + 0.1), height: 0.16, length: 0.44, chamferRadius: 0)
        top.firstMaterial = frameMat
        let tn = SCNNode(geometry: top)
        tn.position = SCNVector3(center.x, base + doorH + 0.08, center.z)
        tn.eulerAngles.y = rotY
        scene.rootNode.addChildNode(tn)
    }

    // Wand entlang x bei festem z. gaps = [(Mitte, Breite)]
    func wallX(_ x0: Float, _ x1: Float, _ z: Float, _ mat: SCNMaterial,
               gaps: [(Float, Float)] = [], h: CGFloat = 4, wainscot: Bool = true,
               base: Float = 0) {
        for s in segments(x0, x1, gaps) where s.1 - s.0 > 0.05 {
            wall(CGFloat(s.1 - s.0), SCNVector3((s.0 + s.1) / 2, 0, z), 0, mat,
                 wainscot: wainscot, h: h, base: base)
        }
        for g in gaps { opening(SCNVector3(g.0, base, z), g.1, 0, mat, h) }
    }

    // Wand entlang z bei festem x
    func wallZ(_ z0: Float, _ z1: Float, _ x: Float, _ mat: SCNMaterial,
               gaps: [(Float, Float)] = [], h: CGFloat = 4, wainscot: Bool = true,
               base: Float = 0) {
        for s in segments(z0, z1, gaps) where s.1 - s.0 > 0.05 {
            wall(CGFloat(s.1 - s.0), SCNVector3(x, 0, (s.0 + s.1) / 2), Float.pi / 2, mat,
                 wainscot: wainscot, h: h, base: base)
        }
        for g in gaps { opening(SCNVector3(x, base, g.0), g.1, Float.pi / 2, mat, h) }
    }

    /// Legt eine Bodenplatte und meldet sie zugleich als begehbare Flaeche an.
    func floorTile(_ w: CGFloat, _ d: CGFloat, _ cx: Float, _ cz: Float, _ mat: SCNMaterial,
                   y: Float = 0) {
        addFloorArea(cx - Float(w)/2, cx + Float(w)/2, cz - Float(d)/2, cz + Float(d)/2, y)
        let plane = SCNPlane(width: w, height: d)
        plane.firstMaterial = mat
        plane.firstMaterial?.isDoubleSided = true
        let n = SCNNode(geometry: plane)
        n.eulerAngles.x = -Float.pi / 2
        n.position = SCNVector3(cx, y, cz)
        scene.rootNode.addChildNode(n)
    }

    func ceiling(_ w: CGFloat, _ d: CGFloat, _ cx: Float, _ cz: Float, _ h: Float = 4) {
        let plane = SCNPlane(width: w, height: d)
        plane.firstMaterial = ceilMat
        let n = SCNNode(geometry: plane)
        n.eulerAngles.x = Float.pi / 2
        n.position = SCNVector3(cx, h, cz)
        scene.rootNode.addChildNode(n)
    }

    /// Gibt den Knoten zurueck, damit Aufrufer ihn z.B. bei registerFlicker
    /// eintragen koennen. @discardableResult, weil das meist nicht gebraucht wird.
    @discardableResult
    func addOmni(_ pos: SCNVector3, _ intensity: CGFloat, _ color: UIColor, range: CGFloat = 16) -> SCNNode {
        let n = SCNNode()
        n.light = SCNLight()
        n.light?.type = .omni
        n.light?.intensity = intensity * 2.6
        n.light?.color = color
        n.light?.attenuationStartDistance = range * 0.25
        n.light?.attenuationEndDistance = range
        n.position = pos
        scene.rootNode.addChildNode(n)
        return n
    }

    /// Feste Kamera: pos und look sind Weltkoordinaten.
    /// Verfolgerkamera (follow: true): pos und look sind Versatz zum Spieler,
    /// nur die y-Werte gelten absolut. Die Blickrichtung bleibt konstant, damit
    /// die Laufrichtung beim Mitziehen nicht wandert.
    /// Kegelfoermige Lichtquelle. Gibt anders als ein Omni einen erkennbaren
    /// Lichtfleck an Wand und Boden - das ist der eigentliche Grund, warum
    /// vorher alles gleichmaessig hell aussah.
    @discardableResult
    func addSpot(_ pos: SCNVector3, _ target: SCNVector3, _ intensity: CGFloat, _ color: UIColor,
                 inner: CGFloat = 18, outer: CGFloat = 58, range: CGFloat = 14,
                 shadow: Bool = false) -> SCNNode {
        let n = SCNNode()
        let l = SCNLight()
        l.type = .spot
        l.intensity = intensity * 2.6
        l.color = color
        l.spotInnerAngle = inner
        l.spotOuterAngle = outer
        l.attenuationStartDistance = range * 0.20
        l.attenuationEndDistance = range
        if shadow {
            // Nur wenige Lichter werfen Schatten - jeder Schattenwerfer kostet
            // einen zusaetzlichen Renderdurchgang.
            l.castsShadow = true
            l.shadowMode = .deferred
            l.shadowMapSize = CGSize(width: 512, height: 512)
            l.shadowSampleCount = 1
            l.shadowRadius = 3
            // 0.32 statt 0.58: mit Schatten AUS (beim Ueberfliegen) sah die
            // Helligkeit genau richtig aus - die Schatten haben also das Licht
            // gefressen. Jetzt bleiben sie sichtbar, verschlucken aber weniger.
            l.shadowColor = UIColor(white: 0, alpha: 0.32)
            l.zNear = 0.5
            l.zFar = range + 6
        }
        n.light = l
        n.position = pos
        if shadow { shadowLights.append(n) }
        scene.rootNode.addChildNode(n)
        aimNode(n, pos, target)
        return n
    }

    /// Schwebender Staub. Kostet fast nichts und macht die Lichtstrahlen
    /// ueberhaupt erst glaubhaft, weil sich etwas darin bewegt.
    func addDust(_ cx: Float, _ cy: Float, _ cz: Float,
                 _ w: CGFloat, _ h: CGFloat, _ d: CGFloat, _ rate: CGFloat) {
        let ps = SCNParticleSystem()
        ps.birthRate = rate
        ps.particleLifeSpan = 12
        ps.particleLifeSpanVariation = 5
        ps.particleSize = 0.013
        ps.particleSizeVariation = 0.009
        ps.particleColor = UIColor(white: 1.0, alpha: 0.42)
        ps.particleColorVariation = SCNVector4(0, 0, 0.12, 0.30)
        ps.particleImage = Tex.dust
        ps.blendMode = .additive
        ps.isLightingEnabled = false
        ps.emitterShape = SCNBox(width: w, height: h, length: d, chamferRadius: 0)
        ps.birthLocation = .volume
        ps.birthDirection = .random
        ps.particleVelocity = 0.040
        ps.particleVelocityVariation = 0.045
        ps.acceleration = SCNVector3(0, -0.005, 0)
        ps.warmupDuration = 6
        ps.loops = true
        let n = SCNNode()
        n.position = SCNVector3(cx, cy, cz)
        n.addParticleSystem(ps)
        scene.rootNode.addChildNode(n)
    }

    func registerWater(_ m: SCNMaterial, _ sx: Float, _ sy: Float, _ rep: Float) {
        waterLayers.append((m, sx, sy, rep))
    }
    func registerFlicker(_ n: SCNNode, _ base: CGFloat) {
        // Gleiche Skala wie addOmni/addSpot, sonst dimmt das Flackern zurueck
        flickerLights.append((n, base * 2.6, Float.random(in: 0...6.28)))
    }

    /// Legt einen Gegenstand in die Welt. Er schwebt leicht und dreht sich,
    /// damit man ihn im Halbdunkel ueberhaupt findet.
    func addPickup(_ kind: ItemKind, _ x: Float, _ y: Float, _ z: Float, _ build: (SCNNode) -> Void) {
        let holder = SCNNode()
        holder.position = SCNVector3(x, y, z)
        build(holder)
        holder.runAction(.repeatForever(.rotateBy(x: 0, y: .pi * 2, z: 0, duration: 6)))
        // schwacher Schein, damit der Gegenstand auffaellt
        let g = SCNPlane(width: 0.55, height: 0.55)
        let m = SCNMaterial()
        m.lightingModel = .constant
        m.diffuse.contents = Tex.pool
        m.multiply.contents = UIColor(red: 1.0, green: 0.90, blue: 0.62, alpha: 1)
        m.blendMode = .add
        m.transparency = 0.38
        m.writesToDepthBuffer = false
        m.isDoubleSided = true
        g.firstMaterial = m
        let gn = SCNNode(geometry: g)
        gn.eulerAngles.x = -Float.pi / 2
        gn.position = SCNVector3(0, -y + 0.03, 0)
        gn.renderingOrder = 19
        holder.addChildNode(gn)
        scene.rootNode.addChildNode(holder)
        pickups.append(Pickup(node: holder, kind: kind, x: x, z: z))
    }

    // --- Interaktion ---

    /// Wird vom Aktionsknopf aufgerufen.
    /// Bretter loesen - vom Aktionsknopf und vom Brecheisenschlag benutzt.
    func pry(_ d: Door) {
        d.boarded = false
        for b in d.boards {
            b.runAction(.sequence([.fadeOut(duration: 0.35), .removeFromParentNode()]))
        }
        say("Die Bretter geben nach.")
    }

    /// Figur im anderen Stil neu aufbauen. Der Spielerknoten bleibt, nur das
    /// Modell darunter wird ersetzt - Position und Kamera bleiben also erhalten.
    func setCartoon(_ on: Bool) {
        guard on != cartoon else { return }
        cartoon = on
        cartoonStyle = on
        rig.root.removeFromParentNode()
        rig = makePlayerRig()
        player.addChildNode(rig.root)
        rig.setCrowbar(visible: equipped == .crowbar)
        rig.setLantern(visible: lanternOn)
        say(on ? "Cartoon-Figur." : "Realistische Figur.")
    }

    /// Helligkeit zur Laufzeit. Skaliert Grundlicht, Richtlicht und Belichtung
    /// gemeinsam - so bleibt das Verhaeltnis von Licht und Schatten erhalten.
    func setBrightness(_ v: Float) {
        let b = max(0.4, min(2.2, v))
        brightness = b
        ambientNode?.light?.intensity = ambientBase * CGFloat(b)
        keyNode?.light?.intensity = keyBase * CGFloat(b)
        cameraNode.camera?.exposureOffset = exposureBase + CGFloat((b - 1) * 0.55)
    }

    /// Ist der Gegenstand gerade in Benutzung? Brecheisen ausgeruestet oder
    /// Laterne brennend - beides wird im Inventar golden hervorgehoben.
    func isActive(_ k: ItemKind) -> Bool {
        k == .lantern ? lanternOn : equipped == k
    }

    /// Gegenstand an- oder ablegen. Brecheisen zum Schlagen, Laterne zum Sehen.
    func toggleEquip(_ k: ItemKind) {
        guard inventory.contains(k) else { return }
        if k == .lantern {
            lanternOn.toggle()
            lanternNode.light?.intensity = lanternOn ? 2400 : 0
            rig.setLantern(visible: lanternOn)
            say(lanternOn ? "Die Laterne brennt." : "Laterne geloescht.")
            return
        }
        guard k == .crowbar else { return }
        equipped = (equipped == k) ? nil : k
        rig.setCrowbar(visible: equipped == .crowbar)
    }

    /// Ausweichrolle: kurzer Schub in Bewegungsrichtung (oder rueckwaerts),
    /// waehrend invulnT laeuft, wird der Spieler spaeter keinen Schaden nehmen.
    func dodge() {
        guard dodgeT < 0, dodgeCooldown <= 0 else { return }
        let l = (vx * vx + vz * vz).squareRoot()
        if l > 0.2 { dodgeDirX = vx / l; dodgeDirZ = vz / l }
        else {
            dodgeDirX = -sin(player.eulerAngles.y)
            dodgeDirZ = -cos(player.eulerAngles.y)
        }
        dodgeT = 0
        dodgeCooldown = 0.9
        invulnT = 0.45
    }

    /// Schlag mit dem Brecheisen: Armanimation, kurz darauf der Treffer.
    func attack() {
        guard equipped == .crowbar, attackCooldown <= 0 else { return }
        attackCooldown = 0.65
        rig.startSwing()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.22) { [weak self] in
            guard let self else { return }
            let px = self.player.position.x, pz = self.player.position.z
            for d in self.doors where d.boarded && d.distance(px, pz) < 1.8 {
                self.pry(d)
                return
            }
        }
    }

    func interact() {
        if let p = nearPickup, !p.taken {
            p.taken = true
            p.node.removeAllActions()
            p.node.removeFromParentNode()
            if !inventory.contains(p.kind) { inventory.append(p.kind) }
            say(p.kind.pickupText)
            nearPickup = nil
            prompt = nil
            return
        }
        guard let d = nearDoor else { return }
        if d.boarded {
            if inventory.contains(.crowbar) {
                pry(d)
            } else {
                say("Zugenagelt. Ohne Werkzeug geht hier nichts.")
            }
            return
        }
        if let need = d.lock {
            if inventory.contains(need) {
                d.lock = nil
                say("\(need.rawValue) passt. Das Schloss springt auf.")
            } else {
                say("Verschlossen.")
                return
            }
        }
        let willOpen = !d.isOpen
        d.swing(to: willOpen)
        solids[d.solidIndex].on = !willOpen
    }

    /// Kurze Einblendung. Die Nachricht raeumt sich selbst wieder weg;
    /// toastID verhindert, dass ein alter Timer eine neue Meldung loescht.
    func say(_ text: String) {
        toastID += 1
        let mine = toastID
        toast = text
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.2) { [weak self] in
            guard let self = self, self.toastID == mine else { return }
            self.toast = nil
        }
    }

    /// Sucht die naechste Tuer bzw. den naechsten Gegenstand. Laeuft nur alle
    /// paar Bilder, das reicht voellig und spart Rechenzeit.
    /// Wichtig: die Suche selbst passiert im Render-Thread, aber jeder Zugriff
    /// auf @Published-Zustand wird auf den Hauptthread gelegt.
    private func scanInteractables() {
        let px = player.position.x, pz = player.position.z

        var bestP: Pickup? = nil
        var bestPD: Float = 1.5
        for p in pickups where !p.taken {
            let d = p.distance(px, pz)
            if d < bestPD { bestPD = d; bestP = p }
        }
        var bestD: Door? = nil
        var bestDD: Float = 2.0
        if bestP == nil {
            for d in doors {
                let dd = d.distance(px, pz)
                if dd < bestDD { bestDD = dd; bestD = d }
            }
        }

        DispatchQueue.main.async {
            self.nearPickup = bestP
            self.nearDoor = bestD

            var newPrompt: String? = nil
            if let p = bestP {
                newPrompt = "\(p.kind.rawValue) aufnehmen"
            } else if let d = bestD {
                if d.boarded {
                    newPrompt = self.inventory.contains(.crowbar) ? "Bretter aufhebeln" : "Zugenagelt"
                } else if let need = d.lock {
                    newPrompt = self.inventory.contains(need) ? "Aufschliessen" : "Verschlossen"
                } else {
                    newPrompt = d.isOpen ? "\(d.label) schliessen" : "\(d.label) oeffnen"
                }
            }
            if self.prompt != newPrompt { self.prompt = newPrompt }

            // Die Etage MUSS mitgeprueft werden: Waschsaal und Schwimmhalle
            // liegen genau ueber Empfangshalle und Treppenhalle. Ohne diesen
            // Vergleich gewinnt der zuerst eingetragene Raum - deshalb stand
            // "Waschsaal" im Erdgeschoss.
            let fl = self.floorIdx
            for (i, r) in self.rooms.enumerated() where r.floor == fl && r.contains(px, pz) {
                if !r.visited { self.rooms[i].visited = true }
                if self.currentRoom != r.name { self.currentRoom = r.name }
                break
            }
            self.mapX = px; self.mapZ = pz
        }
    }

    func zone(_ x0: Float, _ x1: Float, _ z0: Float, _ z1: Float,
              _ pos: SCNVector3, _ look: SCNVector3, _ fov: CGFloat = 70,
              follow: Bool = false, track: Float = 0.55, margin: Float = 1.6,
              yaw: Float = 0, yLo: Float = -1, yHi: Float = 2.6) {
        camZones.append(CamZone(x0: x0, x1: x1, z0: z0, z1: z1, pos: pos, look: look,
                                fov: fov, follow: follow, track: track, margin: margin,
                                yLo: yLo, yHi: yHi, yaw: yaw))
    }

    func buildScene() {
        scene.background.contents = UIColor.black
        buildVilla()
        // Gesicherten Moebelstand laden, falls vorhanden
        loadFurniture()
        buildFurniture()
        loadWalls()
        buildWalls()
        // Auswahlmarke: schwebender Ring ueber dem gewaehlten Moebelstueck
        let ring = SCNTorus(ringRadius: 0.34, pipeRadius: 0.035)
        ring.ringSegmentCount = 12; ring.pipeSegmentCount = 6
        let rm = SCNMaterial(); rm.lightingModel = .constant
        rm.diffuse.contents = UIColor(red: 1.0, green: 0.85, blue: 0.35, alpha: 1)
        rm.emission.contents = UIColor(red: 1.0, green: 0.80, blue: 0.25, alpha: 1)
        ring.firstMaterial = rm
        selMarker.addChildNode(SCNNode(geometry: ring))
        selMarker.isHidden = true
        scene.rootNode.addChildNode(selMarker)
        // Der Schlaefer: einer im Westflur, einer im Stationsflur oben.
        for (bounds, y) in [((Float(-30.2), Float(-24.8), Float(-19.0), Float(11.0)), Float(0)),
                            ((Float(-2.3), Float(2.3), Float(-19.0), Float(-1.2)), Float(3.8))] {
            let sl = makeSleeper(bounds: bounds, baseY: y)
            sl.root.position = SCNVector3((bounds.0 + bounds.1) / 2, y, (bounds.2 + bounds.3) / 2)
            scene.rootNode.addChildNode(sl.root)
            sleepers.append(sl)
        }
        audio.start()

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        // SH2-Rezept: sehr wenig Grundlicht, dafuer klare lokale Quellen.
        // 220 hat alles gleichmaessig angegraut - Finsternis gab es nie.
        ambient.light?.intensity = 1650
        ambient.light?.color = UIColor(red: 0.70, green: 0.72, blue: 0.76, alpha: 1)
        scene.rootNode.addChildNode(ambient)
        ambientNode = ambient

        // Tiefennebel: Raumenden versinken im Schwarz, Naehe bleibt lesbar.
        // Nebel deutlich weiter draussen: er soll Flurenden schlucken,
        // nicht den Raum, in dem man steht. 7/30 hat alles geschwaerzt.
        scene.fogStartDistance = 20
        scene.fogEndDistance = 80
        scene.fogDensityExponent = 1.15
        // Grauer Nebel statt schwarzem: DAS machte den Unterschied zwischen
        // "Nacht" und "draussen ist es grau bewoelkt". Ferne wird hell-truebe.
        scene.fogColor = UIColor(red: 0.055, green: 0.060, blue: 0.075, alpha: 1)

        let key = SCNNode()
        key.light = SCNLight()
        key.light?.type = .directional
        key.light?.intensity = 780
        keyNode = key
        key.light?.color = UIColor(red: 0.92, green: 0.90, blue: 0.84, alpha: 1)
        key.eulerAngles = SCNVector3(-0.9, 0.6, 0)
        scene.rootNode.addChildNode(key)

        player.position = SCNVector3(0, 0, 10)
        rig = makePlayerRig()
        player.addChildNode(rig.root)
        // Kontaktschatten unter dem Spieler: eine Textur, kein Licht. Haengt am
        // Spielerknoten und laeuft damit auch Treppen mit.
        let blobG = SCNPlane(width: 0.62, height: 0.62)
        let blobM = SCNMaterial()
        blobM.lightingModel = .constant
        blobM.diffuse.contents = Tex.shadowBlob
        blobM.writesToDepthBuffer = false
        blobG.firstMaterial = blobM
        let blob = SCNNode(geometry: blobG)
        blob.eulerAngles.x = -Float.pi / 2
        blob.position = SCNVector3(0, 0.015, 0)
        blob.renderingOrder = 6
        player.addChildNode(blob)

        // Laternenlicht - warm, kurze Reichweite, wirft Schatten. Es haengt
        // etwas vor und ueber dem Spieler, damit der Kegel nach vorn faellt.
        lanternNode.light = SCNLight()
        lanternNode.light?.type = .omni
        // SceneKit nimmt 1000 als Referenzhelligkeit. Meine bisherigen Werte
        // lagen alle darunter - deshalb war trotz "heller" alles fast schwarz.
        lanternNode.light?.intensity = 0
        lanternNode.light?.color = UIColor(red: 1.0, green: 0.86, blue: 0.62, alpha: 1)
        lanternNode.light?.attenuationStartDistance = 1.2
        lanternNode.light?.attenuationEndDistance = 12
        lanternNode.light?.castsShadow = true
        lanternNode.light?.shadowMode = .forward
        lanternNode.light?.shadowRadius = 4
        lanternNode.light?.shadowColor = UIColor(white: 0, alpha: 0.34)
        lanternNode.position = SCNVector3(0.22, 1.05, 0.20)
        player.addChildNode(lanternNode)
        scene.rootNode.addChildNode(player)

        cameraNode.camera = SCNCamera()
        let cam = cameraNode.camera!
        cam.projectionDirection = .horizontal   // FOV gilt fuer die Bildbreite
        cam.fieldOfView = 70                    // Startwert, jede Zone setzt ihren eigenen
        // Feste Kameras stehen jetzt IM Raum, nicht hinter der Wand - der alte
        // Trick funktionierte nur fuer Waende naeher als zNear.
        cam.zNear = 0.35
        // 55 statt 90: aus der Vogelperspektive lag sonst das komplette
        // Sanatorium im Bild - tausende Knoten gleichzeitig.
        cam.zFar = 55
        cam.wantsHDR = true
        cam.wantsExposureAdaptation = false
        cam.exposureOffset = 1.05
        cam.bloomIntensity = 0.55
        cam.bloomThreshold = 0.80
        cam.bloomBlurRadius = 8
        cam.vignettingIntensity = 0.48
        cam.vignettingPower = 1.1
        cam.saturation = 0.88
        cam.contrast = 0.05
        cam.colorFringeStrength = 0.12
        cam.grainIntensity = 0.10
        cam.grainScale = 2.0
        cam.grainIsColored = false
        scene.rootNode.addChildNode(cameraNode)
        updateCamera()
    }

    /// Richtet einen Knoten rollfrei auf ein Ziel aus. Gilt fuer Kameras und
    /// Spots gleichermassen - beide blicken in SceneKit entlang ihrer lokalen -z.
    /// Der Rechts-Vektor kommt aus dem Welt-Oben, dadurch bleibt der Horizont
    /// per Konstruktion waagerecht und die Szene kann nicht mehr verkippen.
    func aimNode(_ node: SCNNode, _ from: SCNVector3, _ to: SCNVector3) {
        let pos = SIMD3<Float>(from.x, from.y, from.z)
        let tgt = SIMD3<Float>(to.x, to.y, to.z)
        var back = pos - tgt
        let bl = length(back)
        if bl < 1e-5 { return }
        back /= bl
        var upRef = SIMD3<Float>(0, 1, 0)
        if abs(back.y) > 0.999 { upRef = SIMD3<Float>(0, 0, 1) }   // senkrecht nach unten
        var right = cross(upRef, back)
        let rl = length(right)
        if rl < 1e-5 { right = SIMD3<Float>(1, 0, 0) } else { right /= rl }
        let up = cross(back, right)
        var m = matrix_identity_float4x4
        m.columns.0 = SIMD4<Float>(right, 0)
        m.columns.1 = SIMD4<Float>(up, 0)
        m.columns.2 = SIMD4<Float>(back, 0)
        m.columns.3 = SIMD4<Float>(pos, 1)
        node.simdTransform = m
    }

    func aimCamera(_ from: SCNVector3, _ to: SCNVector3) {
        aimNode(cameraNode, from, to)
    }

    // --- Kamera-Zonen ---
    // Zwei Bauarten:
    //  fest    - Standort unbeweglich wie in RE. Damit der Spieler trotzdem nie
    //            aus dem Bild faellt, wandert der Blickpunkt anteilig (track) mit.
    //  follow  - Standort haengt am Spieler, Blickrichtung bleibt konstant.
    //            Fuer lange Flure und grosse Hallen.
    // Beim Zonenwechsel wird hart geschnitten, innerhalb weich nachgezogen.
    /// Freie Kamera bewegen. Der Joystick schiebt in Blickrichtung.
    func flyCamera(_ dt: Float, fwd: Float, side: Float, lift: Float) {
        let sp: Float = 6.0
        let cy = cos(fcYaw), sy = sin(fcYaw)
        fcPos.x += (-sy * fwd + cy * side) * sp * dt
        fcPos.z += (-cy * fwd - sy * side) * sp * dt
        fcPos.y += lift * sp * dt
        // In Grenzen halten: eine Kamera, die ins Unendliche fliegt, erzeugt
        // frueher oder spaeter Werte, mit denen nachgelagerte Rechnungen nicht
        // mehr umgehen koennen.
        fcPos.x = max(-60, min(35, fcPos.x))
        fcPos.y = max(-5, min(13, fcPos.y))   // knapp ueber dem hoechsten Dach
        fcPos.z = max(-30, min(22, fcPos.z))
        if !fcPos.x.isFinite || !fcPos.y.isFinite || !fcPos.z.isFinite {
            fcPos = SCNVector3(0, 4, 8)
        }
    }

    func turnCamera(_ dYaw: Float, _ dPitch: Float) {
        fcYaw += dYaw
        fcPitch = max(-1.4, min(1.4, fcPitch + dPitch))
    }

    /// Freie Kamera an die aktuelle Spielansicht setzen, damit der Wechsel
    /// nicht irgendwo im Nichts beginnt.
    func syncFreeCam() {
        fcPos = cameraNode.position
        fcYaw = cameraNode.eulerAngles.y
        fcPitch = cameraNode.eulerAngles.x
    }

    func updateCamera() {
        if freeCam {
            cameraNode.position = fcPos
            cameraNode.eulerAngles = SCNVector3(fcPitch, fcYaw, 0)
            return
        }
        let px = player.position.x, pz = player.position.z
        var found = -1
        for (i, c) in camZones.enumerated() {
            let py = player.position.y
            if px >= c.x0 && px <= c.x1 && pz >= c.z0 && pz <= c.z1
                && py >= c.yLo && py <= c.yHi { found = i; break }
        }
        if found < 0 { return }                       // ausserhalb -> alte Kamera behalten
        let c = camZones[found]
        let changed = (found != currentZone)
        if changed {
            currentZone = found
            cameraNode.camera?.fieldOfView = c.fov
        }

        var wantPos: SCNVector3
        var wantAim: SCNVector3
        if c.follow {
            // Reine Verfolgerkamera: fester Versatz zum Spieler, kein Begrenzen
            // an den Raumgrenzen. Genau das Begrenzen war die Ursache dafuer,
            // dass die Kamera am Raumrand stehenblieb und der Spieler aus dem
            // Bild lief oder hinter die Linse geriet. Lieber sieht man
            // gelegentlich durch eine Wand als gar nichts.
            let py2 = player.position.y
            // Versatz um die Zonen-Blickrichtung drehen: pro Raum steht die
            // Kamera an der "richtigen" Seite und der Raum liegt von vorn da.
            let cy2 = cos(c.yaw), sy2 = sin(c.yaw)
            var ox = c.pos.x * cy2 - c.pos.z * sy2
            var oz = c.pos.x * sy2 + c.pos.z * cy2
            var rise: Float = 0
            var sev: Float = 0

            // Kamerakollision: der gedrehte Versatz zeigt oft geradewegs in eine
            // Wand - dann rendert die Kamera aus dem Mauerwerk heraus und das
            // Bild ist schwarz. Also vom Spieler nach aussen tasten und vor dem
            // ersten Hindernis stehenbleiben.
            let full = (ox * ox + oz * oz).squareRoot()
            if full > 0.01 {
                let dirX = ox / full, dirZ = oz / full
                let camY = py2 + c.pos.y
                var reach = full
                var d: Float = 0.5
                while d <= full {
                    if hitsWall(px + dirX * d, pz + dirZ * d, camY - 0.85) {
                        reach = max(0.35, d - 0.35)
                        break
                    }
                    d += 0.25
                }
                ox = dirX * reach
                oz = dirZ * reach
                // Steht die Wand naeher als der Sollabstand, weicht die Kamera
                // nach OBEN aus und schaut steiler herab. Ein festes Minimum
                // haette sie weiter in die Wand gedrueckt - genau das war der
                // Fall in der Empfangshalle an der Nordwand.
                // Nach oben ausweichen, aber nur wenig: die Empfangshalle hat
                // ihre Decke bei 4,0 und die Kamera sitzt schon auf 3,4.
                // Mehr als einen halben Meter und sie steckt in der Decke.
                if reach < full - 0.05 {
                    rise = min(0.5, (full - reach) * 0.35)
                    // Wie stark klemmt die Kamera? 0 = frei, 1 = ganz an der Wand.
                    sev = min(1, (full - reach) / full)
                }
                // Klebt die Kamera dem Spieler im Nacken, wuerde sein Koerper
                // das ganze Bild fuellen - dann blenden wir ihn kurz aus.
                let tooClose = reach < 1.1
                if rig.root.isHidden != tooClose { rig.root.isHidden = tooClose }
            }
            wantPos = SCNVector3(px + ox, py2 + c.pos.y + rise, pz + oz)
            // Je enger die Kamera klemmt (Tuerdurchgang!), desto steiler blickt
            // sie herab - dein Vorschlag: an Tueren wie an Waenden nach oben.
            wantAim = SCNVector3(px + (c.look.x * cy2 - c.look.z * sy2),
                                 py2 + c.look.y - sev * 0.85,
                                 pz + (c.look.x * sy2 + c.look.z * cy2))
        } else {
            if rig.root.isHidden { rig.root.isHidden = false }
            wantPos = c.pos
            wantAim = SCNVector3(c.look.x + (px - c.look.x) * c.track,
                                 c.look.y,
                                 c.look.z + (pz - c.look.z) * c.track)
        }

        if changed {
            smoothPos = wantPos; smoothAim = wantAim
        } else {
            let k: Float = 0.14
            smoothPos = SCNVector3(smoothPos.x + (wantPos.x - smoothPos.x) * k,
                                   smoothPos.y + (wantPos.y - smoothPos.y) * k,
                                   smoothPos.z + (wantPos.z - smoothPos.z) * k)
            smoothAim = SCNVector3(smoothAim.x + (wantAim.x - smoothAim.x) * k,
                                   smoothAim.y + (wantAim.y - smoothAim.y) * k,
                                   smoothAim.z + (wantAim.z - smoothAim.z) * k)
        }
        aimCamera(smoothPos, smoothAim)
    }

    // --- Kollision ---
    func hits(_ x: Float, _ z: Float) -> Bool {
        hits(x, z, player.position.y)
    }

    /// y = Fusshoehe des Spielers. Eine Sperre gilt nur, wenn sie sich mit der
    /// Koerperhoehe ueberschneidet - sonst wuerde das Obergeschoss unten blockieren.
    /// Wie hits, aber nur Waende. Fuer die Kamera.
    func hitsWall(_ x: Float, _ z: Float, _ y: Float) -> Bool {
        let head = y + 1.7
        for s in solids where s.on && s.blocksCamera {
            if x > s.x0 - 0.1 && x < s.x1 + 0.1 && z > s.z0 - 0.1 && z < s.z1 + 0.1
                && head > s.y0 && y < s.y1 { return true }
        }
        return false
    }

    func hits(_ x: Float, _ z: Float, _ y: Float) -> Bool {
        let rad: Float = 0.4
        let head = y + 1.7
        for s in solids where s.on && s.blocksPlayer {
            if s.y1 < y + 0.15 || s.y0 > head { continue }
            let cx = max(s.x0, min(x, s.x1))
            let cz = max(s.z0, min(z, s.z1))
            let dx = x - cx, dz = z - cz
            if dx * dx + dz * dz < rad * rad { return true }
        }
        return false
    }

    /// Bodenhoehe unter (x,z). Bei uebereinanderliegenden Etagen gewinnt die
    /// Flaeche, die der aktuellen Hoehe am naechsten liegt - so faellt man beim
    /// Laufen ueber einer unteren Etage nicht durch.
    func groundHeight(_ x: Float, _ z: Float, near cur: Float) -> Float {
        // Erst Rampen: steht man auf einer Treppe, zaehlt die Treppe, nicht der
        // Boden darunter. Toleranz etwas grosszuegiger, damit der Uebergang
        // Boden -> erste Stufe nicht abreisst.
        var best: Float? = nil
        // 1.1 statt 2.2: Unter Lauf 2 haengt die Rampe 1.9 m ueber dem Kopf -
        // mit der alten Toleranz schnappte der Boden dorthin (Teleport nach
        // oben, sobald man unter die Treppe trat).
        var bestDist: Float = 1.1
        for a in floorAreas where a.isRamp && a.contains(x, z) {
            let d = abs(a.height(x, z) - cur)
            if d < bestDist { bestDist = d; best = a.height(x, z) }
        }
        if let b = best { return b }
        bestDist = 1.6
        for a in floorAreas where !a.isRamp && a.contains(x, z) {
            let h = a.height(x, z)
            let d = abs(h - cur)
            if d < bestDist { bestDist = d; best = h }
        }
        return best ?? cur
    }

    func addFloorArea(_ x0: Float, _ x1: Float, _ z0: Float, _ z1: Float,
                      _ y0: Float, _ y1: Float = .nan, alongZ: Bool = true) {
        floorAreas.append(FloorArea(x0: x0, x1: x1, z0: z0, z1: z1,
                                    y0: y0, y1: y1.isNaN ? y0 : y1, alongZ: alongZ))
    }

    // --- Render-Loop ---
    func renderer(_ renderer: SCNSceneRenderer, updateAtTime time: TimeInterval) {
        if lastTime == 0 { lastTime = time }
        let dt = Float(min(0.05, time - lastTime))
        lastTime = time

        updateCamera()
        animTime += dt

        // Wasser fliesst: die Texturmatrix wandert, das kostet nichts.
        for w in waterLayers {
            w.mat.diffuse.contentsTransform = SCNMatrix4Mult(
                SCNMatrix4MakeScale(w.rep, w.rep, 1),
                SCNMatrix4MakeTranslation(animTime * w.sx, animTime * w.sy, 0))
        }
        // Feuer und Kerzen zucken. Drei ueberlagerte Sinus geben ein
        // unregelmaessiges Muster, ohne dass man eine Periode heraushoert.
        for fl in flickerLights {
            let t = animTime * 7.3 + fl.seed
            let n = sin(t) * 0.5 + sin(t * 2.37 + 1.1) * 0.32 + sin(t * 5.11 + 2.6) * 0.18
            fl.node.light?.intensity = fl.base * CGFloat(0.80 + 0.20 * n)
        }

        scanTick += 1
        if scanTick % 6 == 0 { scanInteractables() }

        let f = cameraNode.simdWorldFront
        var fx = f.x, fz = f.z
        let fl = (fx * fx + fz * fz).squareRoot()
        if fl > 0.0001 { fx /= fl; fz /= fl }
        let r = cameraNode.simdWorldRight
        var rx = r.x, rz = r.z
        let rl = (rx * rx + rz * rz).squareRoot()
        if rl > 0.0001 { rx /= rl; rz /= rl }

        let jx = Float(move.dx), jy = Float(move.dy)
        let jm = (jx * jx + jy * jy).squareRoot()
        if jm < 0.12 { useFx = fx; useFz = fz; useRx = rx; useRz = rz }

        let mvx = useFx * (-jy) + useRx * jx
        let mvz = useFz * (-jy) + useRz * jx

        let speed: Float = 3.2
        let accel: Float = 9.0
        vx += (mvx * speed - vx) * min(1, accel * dt)
        vz += (mvz * speed - vz) * min(1, accel * dt)

        let nx = player.position.x + vx * dt
        if !hits(nx, player.position.z) { player.position.x = nx } else { vx = 0 }
        let nz = player.position.z + vz * dt
        if !hits(player.position.x, nz) { player.position.z = nz } else { vz = 0 }

        // Auswahlmarke ueber dem gewaehlten Stueck fuehren
        if editMode, let i = selectedFurniture, i < furnitureList.count {
            let p = furnitureList[i]
            selMarker.isHidden = false
            selMarker.position = SCNVector3(p.x, floorBase(p.floor) + 1.35 + sin(animTime * 2.4) * 0.06, p.z)
            selMarker.eulerAngles.y = animTime * 0.9
        } else if !selMarker.isHidden {
            selMarker.isHidden = true
        }
        // CGVector heisst dx/dy (width/height waere CGSize). Vorzeichen wie
        // beim Spieler weiter unten: Joystick nach unten = rueckwaerts.
        if freeCam { flyCamera(dt, fwd: -Float(move.dy), side: Float(move.dx), lift: fcLift) }
        // Aus der Hoehe sieht man fast das ganze Haus. Dann kosten die
        // Schattenwerfer je einen kompletten Zusatzdurchgang ueber alles -
        // deshalb sind sie beim Ueberfliegen aus.
        let heavyView = freeCam && cameraNode.position.y > 6.5
        if heavyView != shadowsOff {
            shadowsOff = heavyView
            for n in shadowLights { n.light?.castsShadow = !heavyView }
            lanternNode.light?.castsShadow = !heavyView
        }
        if attackCooldown > 0 { attackCooldown -= dt }
        if dodgeCooldown > 0 { dodgeCooldown -= dt }
        if invulnT > 0 { invulnT -= dt }
        if dodgeT >= 0 {
            dodgeT += dt
            let p = dodgeT / 0.30
            if p >= 1 {
                dodgeT = -1
                rig.root.eulerAngles.x = 0
            } else {
                let step = 5.2 * dt * (1 - p * 0.55)
                let nx2 = player.position.x + dodgeDirX * step
                if !hits(nx2, player.position.z) { player.position.x = nx2 }
                let nz2 = player.position.z + dodgeDirZ * step
                if !hits(player.position.x, nz2) { player.position.z = nz2 }
                rig.root.eulerAngles.x = 0.42 * sin(p * Float.pi)
            }
        }
        if lanternOn {
            // Leichtes Pumpen, damit es nach Flamme aussieht statt nach Lampe
            let f = 2400 + sin(animTime * 7.3) * 130 + sin(animTime * 17.1) * 55
            lanternNode.light?.intensity = CGFloat(f)
        }
        let pSpeed = (vx * vx + vz * vz).squareRoot()
        // Regenpegel je nach Ort: unterm Glasdach prasselt es, im Keller
        // bleibt nur ein dumpfes Rauschen durch das Mauerwerk.
        let rp: Float
        if player.position.y > 5.4 { rp = 0.95 }
        else if player.position.x > 3 && player.position.z < -11.6 && player.position.y < 2.4 { rp = 0.22 }
        else { rp = 0.55 }
        audio.setRain(rp)
        if debugOn {
            let cp = cameraNode.position
            let zn = currentZone >= 0 && currentZone < camZones.count ? currentZone : -1
            let txt = String(format: "Spieler  x %.1f  y %.1f  z %.1f\nKamera   x %.1f  y %.1f  z %.1f\nZone %d   Etage %d   %@",
                             player.position.x, player.position.y, player.position.z,
                             cp.x, cp.y, cp.z, zn, floorIdx, currentRoom)
            if txt != debugText {
                DispatchQueue.main.async { [weak self] in self?.debugText = txt }
            }
        }
        for sl in sleepers {
            sl.update(dt: dt, px: player.position.x, pz: player.position.z,
                      py: player.position.y, playerMoving: pSpeed > 0.25)
        }
        // Steht man seitlich oder im Strahl, verschwinden die Traegerflaechen,
        // statt als gekreuzte Scheiben aufzufallen - der Rest der "Kanten".
        if !shaftPlanes.isEmpty {
            let cp = cameraNode.simdWorldPosition
            for (node, nrm) in shaftPlanes {
                let v = cp - node.simdWorldPosition
                let len = simd_length(v)
                // Steht die Kamera GENAU auf dem Schacht, ist der Vektor null
                // lang - simd_normalize liefert dann NaN, und eine Deckkraft von
                // NaN bringt SceneKit zum Absturz. Genau das passierte beim
                // Hochfliegen: die Lichtschaechte haengen bei y rund 9.9.
                if len < 0.001 { node.opacity = 1.0; continue }
                let d = abs(simd_dot(nrm, v / len))
                let o = 0.18 + 0.82 * d
                node.opacity = o.isFinite ? CGFloat(o) : 1.0
            }
        }
        let fNew = player.position.y > 5.4 ? 2 : (player.position.y > 2.4 ? 1 : 0)
        if fNew != floorIdx {
            DispatchQueue.main.async { [weak self] in self?.floorIdx = fNew }
        }
        // Auf Treppen steigt der Spieler mit. Weich nachgezogen, damit die
        // einzelnen Stufen nicht als Ruckeln durchschlagen.
        let gy = groundHeight(player.position.x, player.position.z, near: player.position.y)
        player.position.y += (gy - player.position.y) * min(1, 14 * dt)

        if (vx * vx + vz * vz) > 0.02 {
            let target = Float(atan2(Double(vx), Double(vz)))
            var d = target - faceAngle
            while d > Float.pi { d -= 2 * Float.pi }
            while d < -Float.pi { d += 2 * Float.pi }
            faceAngle += d * min(1, 10 * dt)
            player.eulerAngles.y = faceAngle
        }

        rig.animate(dt: dt, speed: (vx * vx + vz * vz).squareRoot())
    }
}
