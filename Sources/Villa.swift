import SceneKit
import UIKit
import simd

// Villa-Aufbau nach RE1-Vorbild:
// Haupthalle (doppelt hoch, Treppe) -> Speisezimmer -> Kueche
//                                   -> Bibliothek   -> Galerie
//                                   -> Nordflur     -> Bad / Lager / Arbeitszimmer

extension GameController {

    // ===================== Material-Helfer =====================

    func col(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat) -> SCNMaterial {
        let m = SCNMaterial()
        m.lightingModel = .lambert
        m.diffuse.contents = UIColor(red: r, green: g, blue: b, alpha: 1)
        m.multiply.contents = Tex.grunge
        m.multiply.wrapS = .repeat
        m.multiply.wrapT = .repeat
        m.multiply.contentsTransform = SCNMatrix4MakeScale(3, 3, 1)
        m.multiply.magnificationFilter = .nearest
        return m
    }
    func glowMat(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat) -> SCNMaterial {
        let m = SCNMaterial(); let c = UIColor(red: r, green: g, blue: b, alpha: 1)
        m.lightingModel = .constant
        m.diffuse.contents = c; m.emission.contents = c; return m
    }

    @discardableResult
    func prop(_ w: CGFloat, _ h: CGFloat, _ d: CGFloat, _ x: Float, _ y: Float, _ z: Float,
              _ mat: SCNMaterial, solid: Bool = false) -> SCNNode {
        let g = SCNBox(width: w, height: h, length: d, chamferRadius: 0.01)
        g.firstMaterial = mat
        let n = SCNNode(geometry: g); n.position = SCNVector3(x, y, z)
        scene.rootNode.addChildNode(n)
        if solid {
            let fw = Float(w), fd = Float(d), fh = Float(h)
            // Echter Hoehenbereich aus der Geometrie: ein Regal im Dachgeschoss
            // darf im Erdgeschoss nichts sperren. Und blocksCamera: false, damit
            // die Kamera nur an Waenden ausweicht, nicht an jedem Moebel.
            solids.append(WallBox(x0: x - fw/2, x1: x + fw/2, z0: z - fd/2, z1: z + fd/2,
                                  y0: y - fh/2 - 0.1, y1: y + fh/2, blocksCamera: false))
        }
        return n
    }
    func cyl(_ r: CGFloat, _ h: CGFloat, _ x: Float, _ y: Float, _ z: Float, _ mat: SCNMaterial) {
        let g = SCNCylinder(radius: r, height: h); g.firstMaterial = mat
        let n = SCNNode(geometry: g); n.position = SCNVector3(x, y, z); scene.rootNode.addChildNode(n)
    }
    func sph(_ r: CGFloat, _ x: Float, _ y: Float, _ z: Float, _ mat: SCNMaterial) {
        let g = SCNSphere(radius: r); g.firstMaterial = mat
        let n = SCNNode(geometry: g); n.position = SCNVector3(x, y, z); scene.rootNode.addChildNode(n)
    }
    /// Moebelsperre.
    /// base/height: OHNE Hoehenbereich sperrte ein Moebel im Dachgeschoss auch
    /// das Erdgeschoss - so war der Gang am Tresen vom Schwimmbecken blockiert.
    /// blocksCamera: false - die Kamera weicht nur Waenden aus, nicht Stuehlen.
    func blocker(_ x0: Float, _ x1: Float, _ z0: Float, _ z1: Float,
                 base: Float = 0, height: Float = 2.4) {
        solids.append(WallBox(x0: x0, x1: x1, z0: z0, z1: z1,
                              y0: base - 0.2, y1: base + height, blocksCamera: false))
    }



    // ===================== Licht-Bausteine =====================
    // Echte Volumenstreuung waere auf dem iPad zu teuer. Der uebliche Trick:
    // zwei gekreuzte Flaechen mit einem Helligkeitsverlauf, additiv gemischt.
    // Aus jedem Winkel bleibt ein Kegel sichtbar, Kosten praktisch null.

    func addMat(_ img: UIImage, _ tint: UIColor, _ opacity: CGFloat) -> SCNMaterial {
        let m = SCNMaterial()
        m.lightingModel = .constant
        m.diffuse.contents = img
        m.multiply.contents = tint
        m.blendMode = .add
        m.writesToDepthBuffer = false
        m.readsFromDepthBuffer = true
        m.isDoubleSided = true
        m.transparency = opacity
        return m
    }

    /// Lichtschacht von `from` (hell) nach `to` (aus).
    func lightShaft(_ from: SCNVector3, _ to: SCNVector3, _ wTop: CGFloat,
                    _ opacity: CGFloat, _ tint: UIColor) {
        let a = SIMD3<Float>(from.x, from.y, from.z)
        let b = SIMD3<Float>(to.x, to.y, to.z)
        var up = a - b                                   // +y der Flaeche zeigt zur Quelle
        let len = simd_length(up)
        if len < 0.08 { return }
        up /= len
        var right = simd_cross(up, SIMD3<Float>(0, 0, 1))
        if simd_length(right) < 1e-3 { right = simd_cross(up, SIMD3<Float>(1, 0, 0)) }
        right = simd_normalize(right)
        let fwd = simd_cross(right, up)
        let mid = (a + b) / 2
        let m = addMat(Tex.shaft, tint, opacity)
        // Zwei gekreuzte Flaechen, nach unten breiter. Vorher war es ein
        // gleichbreiter Streifen, der oben hart ansetzte wie ein Brett.
        for k in 0..<2 {
            let pl = SCNPlane(width: wTop, height: CGFloat(len))
            pl.widthSegmentCount = 1
            pl.firstMaterial = m
            let n = SCNNode(geometry: pl)
            var t = matrix_identity_float4x4
            t.columns.0 = SIMD4<Float>(k == 0 ? right : fwd, 0)
            t.columns.1 = SIMD4<Float>(up, 0)
            t.columns.2 = SIMD4<Float>(k == 0 ? fwd : -right, 0)
            t.columns.3 = SIMD4<Float>(mid, 1)
            n.simdTransform = t
            shaftPlanes.append((n, k == 0 ? fwd : -right))
            n.renderingOrder = 20
            scene.rootNode.addChildNode(n)
            registerCullable(n, mid.x, mid.y, mid.z)
        }
    }

    /// Lichtfleck auf dem Boden unter einer Lampe.
    func floorPool(_ x: Float, _ z: Float, _ rx: CGFloat, _ rz: CGFloat,
                   _ opacity: CGFloat, _ tint: UIColor) {
        let pl = SCNPlane(width: rx * 2, height: rz * 2)
        pl.firstMaterial = addMat(Tex.pool, tint, opacity)
        let n = SCNNode(geometry: pl)
        n.eulerAngles.x = -Float.pi / 2
        n.position = SCNVector3(x, 0.02, z)
        n.renderingOrder = 18
        scene.rootNode.addChildNode(n)
        registerCullable(n, x, 0.02, z)
    }

    /// Fleck an einer Wand, z.B. hinter einer Wandleuchte.
    func wallGlow(_ x: Float, _ y: Float, _ z: Float, _ r: CGFloat,
                  _ dx: Float, _ dz: Float, _ opacity: CGFloat, _ tint: UIColor) {
        let pl = SCNPlane(width: r * 2, height: r * 2.6)
        pl.firstMaterial = addMat(Tex.pool, tint, opacity)
        let n = SCNNode(geometry: pl)
        n.position = SCNVector3(x + dx * 0.05, y, z + dz * 0.05)
        n.eulerAngles.y = atan2(dx, dz)
        n.renderingOrder = 19
        scene.rootNode.addChildNode(n)
        registerCullable(n, x, y, z)
    }

    /// Fenster mit echter Tiefe. Der Unterschied zu vorher: die Scheibe sitzt
    /// 0,32 m in der Wand zurueck, davor liegt eine Laibung aus vier Platten.
    /// Dadurch bekommt das Fenster eine Leibungstiefe - eine buendige Platte mit
    /// aufgemaltem Himmel liest sich immer als Bild, egal wie gut das Bild ist.
    ///
    /// Aufbau von aussen nach innen:
    ///   Himmelsflaeche - Glas (additiv, eigene Schlieren) - Sprossen - Laibung - Sims
    ///
    /// nx/nz zeigen ins Zimmer.
    func stormWindow(_ x: Float, _ y: Float, _ z: Float, _ w: CGFloat, _ h: CGFloat,
                    _ nx: Float, _ nz: Float, _ throwDist: Float) {
        let frame = texMat(Tex.wainscot, 1, 1)
        let rev   = texMat(Tex.plaster, 1, 1)
        let alongZ = abs(nx) > 0.5
        let D: Float = 0.32                       // Leibungstiefe
        let fw = Float(w), fh = Float(h)
        // Achsen: a laeuft entlang der Wand, n zeigt in den Raum
        func P(_ along: Float, _ up: Float, _ inward: Float) -> SCNVector3 {
            alongZ ? SCNVector3(x + nx * inward, y + up, z + along)
                   : SCNVector3(x + along, y + up, z + nz * inward)
        }
        func S(_ along: CGFloat, _ up: CGFloat, _ deep: CGFloat) -> (CGFloat, CGFloat, CGFloat) {
            alongZ ? (deep, up, along) : (along, up, deep)
        }
        func box(_ a: CGFloat, _ u: CGFloat, _ d: CGFloat,
                 _ pa: Float, _ pu: Float, _ pd: Float, _ m: SCNMaterial) {
            let s3 = S(a, u, d); let p3 = P(pa, pu, pd)
            prop(s3.0, s3.1, s3.2, p3.x, p3.y, p3.z, m)
        }

        // Himmel ganz hinten, eine der vier Varianten
        let variant = Int(abs(x * 3.0 + z * 7.0)) % 4
        // Die Scheibe sass bei -D, also 32 cm HINTER dem Ankerpunkt - bei einer
        // 30 cm dicken Wand liegt sie damit komplett im Mauerwerk und war nie
        // zu sehen. Die Normale n zeigt in den Raum, ein POSITIVER Versatz
        // schiebt also in jeder Wandrichtung nach innen.
        box(w, h, 0.05, 0, 0, 0.03, windowMat(variant))

        // Glas davor: additiv, sehr durchsichtig. Der Abstand zum Himmel gibt
        // beim Vorbeilaufen einen leichten Versatz - daran erkennt man Glas.
        let gm = SCNMaterial()
        gm.lightingModel = .constant
        gm.diffuse.contents = Tex.glass
        gm.blendMode = .add
        gm.transparency = 0.30
        gm.writesToDepthBuffer = false
        gm.isDoubleSided = true
        gm.diffuse.wrapS = .repeat
        gm.diffuse.wrapT = .repeat
        registerWater(gm, 0, -0.07, 1.3)              // Regenschlieren wandern
        // Streulicht an der Laibung: zwei blasse Kanten, als fange die Wand
        // das Fensterlicht auf. Billig, aber es verankert das Fenster im Raum.
        let glowM = SCNMaterial()
        glowM.lightingModel = .constant
        glowM.diffuse.contents = UIColor(red: 0.55, green: 0.57, blue: 0.61, alpha: 1)
        glowM.emission.contents = UIColor(red: 0.26, green: 0.27, blue: 0.30, alpha: 1)
        for sg3: Float in [-1, 1] {
            // S nimmt CGFloat, fh ist Float - deshalb hier umrechnen statt
            // blind zu casten: die Streifen sollen 34 cm kuerzer sein als das
            // Fenster hoch ist, damit sie oben und unten nicht ueberstehen.
            let sSz = S(0.04, h - 0.34, 0.10)
            let sPp = P(sg3 * (Float(w) / 2 - 0.03), 0, -D * 0.55)
            prop(sSz.0, sSz.1, sSz.2, sPp.x, sPp.y, sPp.z, glowM)
        }
        box(w - 0.03, h - 0.03, 0.012, 0, 0, 0.065, gm)   // Glas vor der Scheibe

        // Laibung: vier Platten vom Glas bis zur Wandflaeche
        box(w + 0.16, 0.10, CGFloat(D), 0, fh/2 + 0.05, -D/2, rev)      // Sturz innen
        box(w + 0.16, 0.10, CGFloat(D), 0, -fh/2 - 0.05, -D/2, rev)     // Bank
        box(0.10, h + 0.20, CGFloat(D), -(fw/2 + 0.05), 0, -D/2, rev)   // Wangen
        box(0.10, h + 0.20, CGFloat(D), fw/2 + 0.05, 0, -D/2, rev)

        // Sprossenkreuz und Rahmen, buendig in der Leibung
        box(w, 0.055, 0.05, 0, 0, -D + 0.13, frame)
        box(0.055, h, 0.05, 0, 0, -D + 0.13, frame)
        box(w + 0.06, 0.075, 0.06, 0, fh/2, -D + 0.13, frame)
        box(w + 0.06, 0.075, 0.06, 0, -fh/2, -D + 0.13, frame)
        box(0.075, h + 0.15, 0.06, -(fw/2), 0, -D + 0.13, frame)
        box(0.075, h + 0.15, 0.06, fw/2, 0, -D + 0.13, frame)

        // Fensterbank ragt in den Raum
        box(w + 0.34, 0.09, 0.30, 0, -(fh/2 + 0.12), 0.09, frame)

        // Licht: der Strahl beginnt an der Scheibe INNERHALB der Leibung und
        // blendet oben ein. Vorher setzte er an der Wandflaeche hart an.
        // Tageslicht durch Wolken: fast weiss, leicht kuehl. Die Fenster sind
        // jetzt die Hauptlichtquellen der Aussenraeume.
        let moon = UIColor(red: 0.84, green: 0.86, blue: 0.90, alpha: 1)
        let sp = P(0, 0, -D + 0.14)
        let ex = x + nx * throwDist, ez = z + nz * throwDist
        lightShaft(SCNVector3(sp.x, sp.y, sp.z), SCNVector3(ex, 0.04, ez), w * 0.92, 0.22, moon)
        floorPool(ex, ez, w * 0.55, w * 0.78, 0.20, moon)
        // Streulicht in der Leibung selbst, damit die Kanten nicht schwarz absaufen
        addOmni(P(0, 0, -D + 0.20), 130, moon, range: 2.4)
        addOmni(P(0, -fh * 0.25, 0.6), 360, moon, range: 7)
    }

    /// Tuerblatt in einer Wandoeffnung. Gibt ein Door zurueck, das der Controller
    /// oeffnet und dessen Sperre er dabei abschaltet.
    /// hinge = -1 Scharnier links, +1 rechts. alongZ = die Wand laeuft entlang z.
    @discardableResult
    func doorLeaf(_ x: Float, _ z: Float, _ w: CGFloat, _ h: CGFloat,
                  _ alongZ: Bool, _ hinge: Float, _ label: String,
                  open: Bool = false, lock: ItemKind? = nil, boarded: Bool = false,
                  style: Int = 0, swing: Float = -1, base: Float = 0) -> Door {
        let leaf = SCNNode()
        let hx = alongZ ? x : x + Float(w) / 2 * hinge
        let hz = alongZ ? z + Float(w) / 2 * hinge : z
        leaf.position = SCNVector3(hx, base, hz)
        let closed = alongZ ? Float.pi / 2 : 0
        // 105 Grad, und swing bestimmt die Seite. Flurtueren schwingen in den
        // Raum hinein, nicht in den Gang - sonst stehen sie der Kamera im Bild.
        let opened = closed + 1.83 * hinge * swing
        leaf.eulerAngles.y = open ? opened : closed
        scene.rootNode.addChildNode(leaf)

        let g = SCNBox(width: w, height: h, length: 0.075, chamferRadius: 0.008)
        g.firstMaterial = texMat(Tex.doors[((style % 4) + 4) % 4], 1, Float(h / w))
        // Bei alongZ dreht die 90-Grad-Grundrotation die lokale x-Achse auf world -z.
        // Der Versatz muss deshalb das Vorzeichen wechseln, sonst addiert er sich
        // zum Scharnierversatz und das Blatt landet eine Tuerbreite daneben.
        let sgnW: Float = alongZ ? 1 : -1
        let n = SCNNode(geometry: g)
        n.position = SCNVector3(sgnW * Float(w) / 2 * hinge, Float(h) / 2, 0)
        leaf.addChildNode(n)

        let br = texMat(Tex.brass, 1, 1)
        for sgn in [-1, 1] {
            let kg = SCNSphere(radius: 0.045); kg.segmentCount = 8; kg.firstMaterial = br
            let kn = SCNNode(geometry: kg)
            kn.position = SCNVector3(sgnW * Float(w) * hinge * 0.82, 1.02, Float(sgn) * 0.06)
            leaf.addChildNode(kn)
        }
        let sg = SCNBox(width: 0.07, height: 0.16, length: 0.03, chamferRadius: 0.004)
        sg.firstMaterial = br
        let sn = SCNNode(geometry: sg)
        sn.position = SCNVector3(sgnW * Float(w) * hinge * 0.82, 1.02, 0.05)
        leaf.addChildNode(sn)

        // Vernagelte Tueren bekommen Bretter quer davor
        var boardNodes: [SCNNode] = []
        if boarded {
            let plank = texMat(Tex.plankWood, 2, 1)
            for k in 0..<3 {
                let yy = base + 0.55 + Float(k) * 0.62
                let tilt = Float(k % 2 == 0 ? 0.07 : -0.05)
                boardNodes.append(propE(w + 0.28, 0.17, 0.06,
                      alongZ ? x + 0.06 : x, yy, alongZ ? z : z + 0.06,
                      SCNVector3(0, alongZ ? Float.pi / 2 : 0, tilt), plank))
            }
        }

        // Sperre: solange die Tuer zu ist, blockiert sie den Durchgang
        let fw = Float(w)
        let sIdx = solids.count
        solids.append(WallBox(
            x0: alongZ ? x - 0.16 : x - fw / 2, x1: alongZ ? x + 0.16 : x + fw / 2,
            z0: alongZ ? z - fw / 2 : z - 0.16, z1: alongZ ? z + fw / 2 : z + 0.16,
            y0: base - 0.2, y1: base + Float(h), on: !open))

        let d = Door(hinge: leaf, solidIndex: sIdx, closedAngle: closed, openAngle: opened,
                     x: x, z: z, label: label, isOpen: open, lock: lock, boarded: boarded)
        d.boards = boardNodes
        doors.append(d)
        return d
    }

    /// Empfangstresen mit Schluesselfaechern dahinter. Das Herzstueck der
    /// Eingangshalle - ohne ihn ist ein Sanatorium nur ein grosses Haus.
    func receptionDesk(_ x: Float, _ z: Float, _ len: CGFloat) {
        contactShadow(x, z - 0.3, len + 0.3, 2.2)
        let wood = texMat(Tex.wainscot, 3, 1)
        let top = texMat(Tex.marble, 2, 1)
        let br = texMat(Tex.brass, 1, 1)
        let fl = Float(len)

        // Tresenkoerper mit Sockel, Fuellungen und Marmorplatte
        prop(len, 1.05, 0.72, x, 0.525, z, wood, solid: true)
        prop(len + 0.12, 0.08, 0.84, x, 1.09, z, top)              // Platte
        roundedEdge(x, 1.06, z + 0.42, len, 0.045, false, top)     // gerundete Vorderkante
        prop(len + 0.10, 0.10, 0.80, x, 0.055, z, wood)            // Sockel
        var px = x - fl/2 + 0.55
        while px < x + fl/2 - 0.2 {
            prop(0.92, 0.62, 0.04, px, 0.58, z + 0.37, wood)       // Fuellungen
            px += 1.10
        }
        // Rueckwand mit Schluesselfaechern
        let rz = z - 0.95
        prop(len - 0.4, 2.05, 0.16, x, 1.02, rz, wood, solid: true)
        let cols = Int((len - 0.9) / 0.19)
        for r in 0..<4 {
            for c in 0..<cols {
                let cx = x - Float(len - 0.9)/2 + Float(c) * 0.19 + 0.095
                let cy = 0.72 + Float(r) * 0.30
                prop(0.165, 0.255, 0.03, cx, cy, rz + 0.09, col(0.14, 0.10, 0.07))
                // in manchen Faechern haengt noch ein Schluessel
                if (c * 7 + r * 3) % 5 == 0 {
                    prop(0.018, 0.075, 0.012, cx, cy - 0.05, rz + 0.11, br)
                    prop(0.045, 0.030, 0.012, cx, cy - 0.10, rz + 0.11, br)
                }
            }
        }
        prop(len - 0.3, 0.10, 0.24, x, 2.10, rz + 0.05, wood)      // Kranz darueber

        // Auf dem Tresen: Gaestebuch, Klingel, Lampe, Loeschwiege
        prop(0.42, 0.055, 0.30, x - fl*0.28, 1.155, z + 0.05, col(0.32, 0.16, 0.13))
        prop(0.38, 0.010, 0.26, x - fl*0.28, 1.188, z + 0.05, col(0.80, 0.78, 0.70))
        cyl(0.075, 0.035, x + fl*0.20, 1.147, z, br)
        sph(0.058, x + fl*0.20, 1.185, z, br)                       // Klingel
        cyl(0.055, 0.30, x + fl*0.36, 1.28, z - 0.10, br)
        let shade = SCNCone(topRadius: 0.055, bottomRadius: 0.135, height: 0.16)
        shade.radialSegmentCount = 10
        shade.firstMaterial = glowMat(0.34, 0.52, 0.30)             // gruene Bankiersleuchte
        let sn = SCNNode(geometry: shade)
        sn.position = SCNVector3(x + fl*0.36, 1.50, z - 0.10)
        scene.rootNode.addChildNode(sn)
        let warm = UIColor(red: 1.0, green: 0.86, blue: 0.58, alpha: 1)
        let l = addOmni(SCNVector3(x + fl*0.36, 1.36, z - 0.10), 420, warm, range: 5)
        registerFlicker(l, 420)
        floorPool(x + fl*0.36, z + 0.5, 1.5, 1.3, 0.24, warm)
    }

    /// Gepaecktrolley aus Messing - Hotelrest, der im Sanatorium stehengeblieben ist.
    func luggageCart(_ x: Float, _ z: Float) {
        contactShadow(x, z, 1.15, 0.95)
        let br = texMat(Tex.brass, 1, 1)
        for sx in [-1, 1] {
            prop(0.05, 1.35, 0.05, x + 0.42 * Float(sx), 0.68, z - 0.30, br)
            prop(0.05, 1.35, 0.05, x + 0.42 * Float(sx), 0.68, z + 0.30, br)
        }
        prop(0.95, 0.06, 0.70, x, 0.28, z, texMat(Tex.plankWood, 1, 1), solid: true)
        prop(0.95, 0.05, 0.05, x, 1.34, z - 0.30, br)
        prop(0.95, 0.05, 0.05, x, 1.34, z + 0.30, br)
        prop(0.05, 0.05, 0.62, x - 0.42, 1.34, z, br)
        for sx in [-1, 1] { for sz in [-1, 1] {
            cyl(0.075, 0.05, x + 0.36 * Float(sx), 0.075, z + 0.26 * Float(sz), col(0.10, 0.09, 0.09))
        }}
        prop(0.55, 0.34, 0.40, x - 0.12, 0.48, z, texMat(Tex.leather, 1, 1))
        prop(0.40, 0.26, 0.32, x + 0.26, 0.44, z + 0.05, texMat(Tex.leather, 1, 1))
    }

    // ===================== Wasser =====================
    // Drei Lagen: truebe Bruehe, additive Kraeusellage die gegenlaeufig fliesst,
    // heller Randsaum. Die Bewegung laeuft ueber die Texturmatrix im Render-Loop.
    @discardableResult
    func waterSurface(_ x: Float, _ y: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat,
                      tint: UIColor = UIColor(red: 0.52, green: 0.26, blue: 0.18, alpha: 1),
                      murk: CGFloat = 0.86, rep: Float = 1.0, flow: Float = 0.012) -> SCNNode {
        let holder = SCNNode()
        holder.position = SCNVector3(x, y, z)
        scene.rootNode.addChildNode(holder)
        let base = SCNPlane(width: w, height: d)
        let bm = SCNMaterial()
        bm.lightingModel = .lambert
        bm.diffuse.contents = Tex.waterFoul
        bm.diffuse.wrapS = .repeat; bm.diffuse.wrapT = .repeat
        bm.multiply.contents = tint
        bm.transparency = murk
        bm.isDoubleSided = true
        bm.locksAmbientWithDiffuse = true
        base.firstMaterial = bm
        let bn = SCNNode(geometry: base); bn.eulerAngles.x = -Float.pi / 2
        holder.addChildNode(bn)
        registerWater(bm, flow, flow * 0.6, rep)
        let top = SCNPlane(width: w * 0.98, height: d * 0.98)
        let tm = SCNMaterial()
        tm.lightingModel = .constant
        tm.diffuse.contents = Tex.waterFoul
        tm.diffuse.wrapS = .repeat; tm.diffuse.wrapT = .repeat
        tm.multiply.contents = UIColor(red: 0.44, green: 0.40, blue: 0.34, alpha: 1)
        tm.blendMode = .add
        tm.transparency = 0.24
        tm.writesToDepthBuffer = false
        tm.isDoubleSided = true
        top.firstMaterial = tm
        let tn = SCNNode(geometry: top)
        tn.eulerAngles.x = -Float.pi / 2
        tn.position = SCNVector3(0, 0.006, 0)
        tn.renderingOrder = 12
        holder.addChildNode(tn)
        registerWater(tm, -flow * 1.7, flow * 1.1, rep * 1.6)
        return holder
    }

    /// Einfarbiges Lambert-Material.
    func mat2(_ c: UIColor) -> SCNMaterial {
        let m = SCNMaterial(); m.lightingModel = .lambert; m.diffuse.contents = c
        return m
    }

    /// Kontaktschatten als Textur - keine Lichtberechnung. Ein dunkler Fleck
    /// unter jedem Moebel erdet es im Raum; genau das haben die schattenlosen
    /// gelben Lichter vermissen lassen. Skaliert auf das ganze Sanatorium.
    func contactShadow(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat,
                       y: Float = 0.012) {
        let m = SCNMaterial()
        m.lightingModel = .constant
        m.diffuse.contents = Tex.shadowBlob
        m.writesToDepthBuffer = false
        m.locksAmbientWithDiffuse = true
        let pl = SCNPlane(width: w, height: d)
        pl.firstMaterial = m
        let n = SCNNode(geometry: pl)
        n.eulerAngles.x = -Float.pi / 2
        n.position = SCNVector3(x, y, z)
        n.renderingOrder = 5
        scene.rootNode.addChildNode(n)
        registerCullable(n, x, y, z)
    }

    /// Glasfassade: Bruestung, Eisensprossen, dazwischen leuchtende Wolken-
    /// scheiben. Jede Bucht bekommt eine eigene Variante, damit nichts kachelt.
    func glassRun(_ a0: Float, _ a1: Float, _ fixed: Float, alongX: Bool,
                  _ base: Float, _ h: CGFloat) {
        // EINE durchgehende Leuchtplatte statt einer Scheibe je Bucht.
        // Vorher entstanden hier pro Fassade ueber dreissig Einzelkoerper mit
        // eigenem Material - mal drei Fassaden in einem Raum. Genau daran ist
        // die Schwimmhalle erstickt.
        let iron = texMat(Tex.iron, 2, 1)
        let len = CGFloat(a1 - a0)
        let mid = (a0 + a1) / 2
        let pane = windowMat(0)
        pane.emission.intensity = 0.95
        pane.transparency = 0.92                 // milchig, kein greller Block

        if alongX {
            prop(len, 0.45, 0.16, mid, base + 0.225, fixed, texMat(Tex.wainscot, 2, 1))
            prop(len, h, 0.05, mid, base + 0.45 + Float(h) / 2, fixed, pane)
            prop(len + 0.2, 0.14, 0.14, mid, base + 0.45 + Float(h) + 0.07, fixed, iron)
        } else {
            prop(0.16, 0.45, len, fixed, base + 0.225, mid, texMat(Tex.wainscot, 2, 1))
            prop(0.05, h, len, fixed, base + 0.45 + Float(h) / 2, mid, pane)
            prop(0.14, 0.14, len + 0.2, fixed, base + 0.45 + Float(h) + 0.07, mid, iron)
        }
        // Sprossen nur alle 3.2 m statt alle 1.6 m - halbiert die Koerperzahl
        var p = a0
        while p <= a1 + 0.01 {
            if alongX { prop(0.09, h + 0.5, 0.09, p, base + Float(h + 0.5) / 2, fixed, iron) }
            else      { prop(0.09, h + 0.5, 0.09, fixed, base + Float(h + 0.5) / 2, p, iron) }
            p += 3.2
        }
        // EINE ruhige Lampe je Fassade
        let dayL = UIColor(red: 0.86, green: 0.89, blue: 0.93, alpha: 1)
        let lp = alongX ? SCNVector3(mid, base + 1.9, fixed) : SCNVector3(fixed, base + 1.9, mid)
        addOmni(lp, 240, dayL, range: 18)

        if alongX {
            solids.append(WallBox(x0: a0, x1: a1, z0: fixed - 0.1, z1: fixed + 0.1,
                                  y0: base, y1: base + Float(h) + 0.6))
        } else {
            solids.append(WallBox(x0: fixed - 0.1, x1: fixed + 0.1, z0: a0, z1: a1,
                                  y0: base, y1: base + Float(h) + 0.6))
        }
    }

    /// Topfpalme. leaning kippt den ganzen Topf - fuer die umgestuerzten.
    func palmAt(_ x: Float, _ z: Float, _ base: Float, leaning: Bool = false) {
        let holder = SCNNode()
        holder.position = SCNVector3(x, base, z)
        if leaning { holder.eulerAngles.z = 0.9; holder.position.y = base + 0.12 }
        scene.rootNode.addChildNode(holder)
        let pot = SCNCylinder(radius: 0.30, height: 0.42)
        pot.radialSegmentCount = 9
        pot.firstMaterial = texMat(Tex.brick, 2, 1)
        let pn = SCNNode(geometry: pot); pn.position = SCNVector3(0, 0.21, 0)
        holder.addChildNode(pn)
        let soil = SCNCylinder(radius: 0.26, height: 0.05)
        soil.radialSegmentCount = 9
        soil.firstMaterial = col(0.16, 0.12, 0.08)
        let sn2 = SCNNode(geometry: soil); sn2.position = SCNVector3(0, 0.43, 0)
        holder.addChildNode(sn2)
        let trunkM = col(0.35, 0.27, 0.16)
        for (ty, tilt) in [(Float(0.75), Float(0.06)), (1.25, 0.14)] {
            let tg = SCNCylinder(radius: 0.045, height: 0.62)
            tg.radialSegmentCount = 6; tg.firstMaterial = trunkM
            let tn = SCNNode(geometry: tg)
            tn.position = SCNVector3(sin(tilt) * ty * 0.4, ty, 0)
            tn.eulerAngles.z = tilt
            holder.addChildNode(tn)
        }
        // Blattkranz aus langen Dreiecken, beidseitig
        let leafM = SCNMaterial(); leafM.lightingModel = .lambert
        leafM.diffuse.contents = UIColor(red: 0.18, green: 0.34, blue: 0.16, alpha: 1)
        leafM.isDoubleSided = true
        var lt: [(SCNVector3, SCNVector3, SCNVector3)] = []
        for k in 0..<8 {
            let a2 = Float(k) / 8 * 2 * Float.pi
            let dx = sin(a2), dz = cos(a2)
            let droop: Float = 0.28 + Float(k % 3) * 0.10
            let tip = SCNVector3(dx * 1.05, 1.62 - droop, dz * 1.05)
            let b1 = SCNVector3(dx * 0.06 - dz * 0.09, 1.60, dz * 0.06 + dx * 0.09)
            let b2 = SCNVector3(dx * 0.06 + dz * 0.09, 1.60, dz * 0.06 - dx * 0.09)
            lt.append((b1, tip, b2))
        }
        let leaves = flatDoubleMesh(lt, leafM)
        holder.addChildNode(leaves)
        contactShadow(x, z, 0.9, 0.9, y: base + 0.012)
        if !leaning { blocker(x - 0.34, x + 0.34, z - 0.34, z + 0.34, base: base) }
    }

    /// Beidseitiges Dreiecksnetz fuer Blattwerk.
    func flatDoubleMesh(_ tris: [(SCNVector3, SCNVector3, SCNVector3)],
                        _ m: SCNMaterial) -> SCNNode {
        var all = tris
        for t in tris { all.append((t.0, t.2, t.1)) }
        var verts: [SCNVector3] = []; var idx: [Int32] = []
        for t in all {
            for p in [t.0, t.1, t.2] { verts.append(p); idx.append(Int32(verts.count - 1)) }
        }
        let geo = SCNGeometry(sources: [SCNGeometrySource(vertices: verts)],
                              elements: [SCNGeometryElement(indices: idx, primitiveType: .triangles)])
        geo.firstMaterial = m
        return SCNNode(geometry: geo)
    }

    /// Schlauchstand des Waschsaals: Ventilrad an der Wand, Schlauch haengt
    /// in zwei Boegen herab, Messingduese am Ende.
    func hoseStation(_ x: Float, _ z: Float, _ base: Float) {
        let br = texMat(Tex.brass, 1, 1)
        let rubber = col(0.12, 0.11, 0.10)
        prop(0.30, 0.30, 0.06, x, base + 1.55, z, texMat(Tex.iron, 1, 1))
        let wheel = SCNTorus(ringRadius: 0.085, pipeRadius: 0.018)
        wheel.ringSegmentCount = 10; wheel.pipeSegmentCount = 5; wheel.firstMaterial = br
        let wn = SCNNode(geometry: wheel)
        wn.position = SCNVector3(x, base + 1.55, z + 0.09)
        wn.eulerAngles.x = Float.pi / 2
        scene.rootNode.addChildNode(wn)
        cylE(0.030, 0.35, x, base + 1.30, z + 0.05, SCNVector3(0.5, 0, 0), br)
        cylE(0.026, 0.55, x - 0.10, base + 0.92, z + 0.16, SCNVector3(0.25, 0, 0.35), rubber)
        cylE(0.026, 0.50, x - 0.28, base + 0.52, z + 0.24, SCNVector3(-0.15, 0, 0.55), rubber)
        cylE(0.024, 0.42, x - 0.34, base + 0.20, z + 0.30, SCNVector3(0.9, 0, 0.1), rubber)
        cylE(0.020, 0.14, x - 0.34, base + 0.06, z + 0.48, SCNVector3(1.3, 0, 0), br)
    }

    // ===================== Bauteile fuer Flure =====================

    /// Durchscheinende Gardine aus vier gegeneinander gedrehten Bahnen.
    func sheerCurtain(_ x: Float, _ z: Float, _ w: CGFloat, _ h: CGFloat,
                      _ alongZ: Bool, _ billow: Float, _ inward: Float) {
        let m = SCNMaterial()
        m.lightingModel = .lambert
        m.diffuse.contents = Tex.sheer
        m.diffuse.wrapS = .repeat; m.diffuse.wrapT = .repeat
        m.transparency = 0.52
        m.isDoubleSided = true
        m.writesToDepthBuffer = false
        m.locksAmbientWithDiffuse = true
        // Zwei seitliche Bahnen mit FESTER Breite, aussen an den Kanten. Die
        // alte Fassung hing als geschlossener Vorhang vor der Scheibe - man sah
        // Gardine und Licht, nie das Glas. Feste Breite statt Anteil, damit die
        // freie Mitte nicht mit der Gardinenbreite mitwaechst.
        let panelW: CGFloat = 0.45
        let sw = panelW
        for k in [0, 1] {
            let t: Float = k == 0 ? 0.18 : 0.82
            let bulge = sin(t * Float.pi) * billow
            let pl = SCNPlane(width: sw * 1.06, height: h)
            pl.firstMaterial = m
            let n = SCNNode(geometry: pl)
            let off = (k == 0 ? -1 : 1) * Float(w / 2 - panelW / 2)
            // Alle Bahnen bleiben parallel zur Wand. Die frueheren Einzel-
            // drehungen haben die Gardine im Gegenlicht zickzackfoermig zerrissen.
            if alongZ {
                n.position = SCNVector3(x + inward * (0.05 + bulge), Float(h) / 2 + 0.05, z + off)
                n.eulerAngles = SCNVector3(0, Float.pi / 2, 0)
            } else {
                n.position = SCNVector3(x + off, Float(h) / 2 + 0.05, z + inward * (0.05 + bulge))
            }
            n.renderingOrder = 14
            scene.rootNode.addChildNode(n)
        }
        let rod = texMat(Tex.brass, 1, 1)
        if alongZ { cylE(0.022, w + 0.3, x + inward * 0.10, Float(h) + 0.10, z, SCNVector3(Float.pi/2, 0, 0), rod) }
        else      { cylE(0.022, w + 0.3, x, Float(h) + 0.10, z + inward * 0.10, SCNVector3(0, 0, Float.pi/2), rod) }
    }

    /// Pendelleuchte mit drei Milchglaskelchen.
    func pendantLamp(_ x: Float, _ z: Float, _ ceilY: Float, _ drop: Float, _ intensity: CGFloat,
                     shadow: Bool = false) {
        let br = texMat(Tex.brass, 1, 1)
        let y = ceilY - drop
        cyl(0.010, CGFloat(drop), x, y + drop / 2, z, col(0.10, 0.09, 0.08))
        cyl(0.070, 0.045, x, ceilY - 0.03, z, br)
        cyl(0.048, 0.07, x, y + 0.05, z, br)
        for k in 0..<3 {
            let a = Double(k) / 3.0 * Double.pi * 2.0
            let px = x + Float(cos(a)) * 0.085, pz = z + Float(sin(a)) * 0.085
            let g = SCNCone(topRadius: 0.026, bottomRadius: 0.058, height: 0.095)
            g.radialSegmentCount = 8
            g.firstMaterial = glowMat(1.0, 0.92, 0.74)
            let n = SCNNode(geometry: g)
            n.position = SCNVector3(px, y - 0.05, pz)
            scene.rootNode.addChildNode(n)
        }
        let warm = UIColor(red: 1.0, green: 0.86, blue: 0.62, alpha: 1)
        let l = addSpot(SCNVector3(x, y - 0.10, z), SCNVector3(x, 0, z), intensity, warm,
                        inner: 22, outer: 82, range: CGFloat(y) + 3, shadow: shadow)
        registerFlicker(l, intensity)
        floorPool(x, z, 1.5, 1.5, 0.24, warm)
    }

    /// Gusseiserner Rippenheizkoerper.
    func radiatorAt(_ x: Float, _ z: Float, _ len: CGFloat, _ alongZ: Bool) {
        let m = texMat(Tex.iron, 2, 1)
        let n = Int(len / 0.10)
        for k in 0..<n {
            let o = (Float(k) - Float(n - 1) / 2) * 0.10
            if alongZ { prop(0.13, 0.58, 0.072, x, 0.36, z + o, m) }
            else      { prop(0.072, 0.58, 0.13, x + o, 0.36, z, m) }
        }
        if alongZ {
            prop(0.17, 0.055, len, x, 0.66, z, m); prop(0.17, 0.055, len, x, 0.09, z, m)
            cyl(0.030, 0.16, x, 0.72, z + Float(len) / 2 - 0.10, texMat(Tex.brass, 1, 1))
        } else {
            prop(len, 0.055, 0.17, x, 0.66, z, m); prop(len, 0.055, 0.17, x, 0.09, z, m)
            cyl(0.030, 0.16, x + Float(len) / 2 - 0.10, 0.72, z, texMat(Tex.brass, 1, 1))
        }
    }

    /// Wandbank mit gedrechselten Beinen.
    func benchAt(_ x: Float, _ z: Float, _ len: CGFloat, _ alongZ: Bool, _ mat: SCNMaterial) {
        contactShadow(x, z, alongZ ? 0.6 : len + 0.2, alongZ ? len + 0.2 : 0.6)
        let w: CGFloat = alongZ ? 0.46 : len
        let d: CGFloat = alongZ ? len : 0.46
        prop(w, 0.06, d, x, 0.455, z, mat, solid: true)
        prop(w - 0.06, 0.05, d - 0.06, x, 0.415, z, mat)
        let lx = Float(w) / 2 - 0.14, lz = Float(d) / 2 - 0.14
        for sx in [-1, 1] { for sz in [-1, 1] {
            turnedLeg(x + lx * Float(sx), 0, z + lz * Float(sz), 0.41, 0.030, mat)
        }}
        if alongZ { prop(0.07, 0.42, d - 0.10, x - 0.19, 0.72, z, mat) }
        else      { prop(w - 0.10, 0.42, 0.07, x, 0.72, z - 0.19, mat) }
    }

    /// Fluegel mit aufgeklapptem Deckel.
    func pianoAt(_ x: Float, _ z: Float) {
        contactShadow(x, z + 0.2, 1.9, 2.8)
        let body = col(0.07, 0.06, 0.06)
        let key = col(0.86, 0.84, 0.78)
        let blk = col(0.06, 0.05, 0.05)
        let br = texMat(Tex.brass, 1, 1)
        prop(1.45, 0.30, 1.05, x, 0.78, z + 0.45, body, solid: true)
        cylE(0.72, 0.30, x - 0.05, 0.78, z - 0.35, SCNVector3(Float.pi/2, 0, 0), body)
        prop(1.45, 0.06, 1.05, x, 0.95, z + 0.45, body)
        propE(1.45, 0.045, 1.55, x, 1.32, z + 0.10, SCNVector3(0.42, 0, 0), body)
        prop(0.035, 0.62, 0.035, x + 0.60, 1.24, z - 0.30, br)
        prop(1.32, 0.09, 0.30, x, 0.78, z + 1.06, key)
        for k in 0..<16 {
            prop(0.035, 0.05, 0.19, x - 0.60 + Float(k) * 0.082, 0.845, z + 1.00, blk)
        }
        prop(1.42, 0.14, 0.14, x, 0.90, z + 1.20, body)
        propE(1.20, 0.035, 0.34, x, 1.12, z + 0.86, SCNVector3(-0.55, 0, 0), body)
        for (px, pz) in [(x - 0.62, z + 0.92), (x + 0.62, z + 0.92), (x - 0.05, z - 0.85)] {
            prop(0.11, 0.63, 0.11, px, 0.315, pz, body)
        }
        prop(0.16, 0.24, 0.14, x, 0.12, z + 0.70, br)
        blocker(x - 0.80, x + 0.80, z - 1.10, z + 1.25)
    }

    // ===================== Moebel-Bausteine =====================

    /// Umlaufendes Deckengesims. Der wirksamste einzelne Handgriff gegen den
    /// Kisteneindruck: ein Raum ohne Uebergang zwischen Wand und Decke bleibt
    /// immer ein Quader. Drei gestaffelte Profile reichen dafuer.
    func cornice(_ x0: Float, _ x1: Float, _ z0: Float, _ z1: Float, _ ceilY: Float,
                 _ mat: SCNMaterial) {
        let w = CGFloat(x1 - x0), d = CGFloat(z1 - z0)
        let cx = (x0 + x1) / 2, cz = (z0 + z1) / 2
        // (Vorsprung, Hoehe, Abstand unter der Decke)
        let steps: [(CGFloat, CGFloat, Float)] = [(0.06, 0.07, 0.05), (0.13, 0.09, 0.14), (0.09, 0.06, 0.23)]
        for (out, hh, drop) in steps {
            let y = ceilY - drop
            prop(w, hh, out, cx, y, z0 + Float(out)/2, mat)
            prop(w, hh, out, cx, y, z1 - Float(out)/2, mat)
            prop(out, hh, d, x0 + Float(out)/2, y, cz, mat)
            prop(out, hh, d, x1 - Float(out)/2, y, cz, mat)
        }
    }

    /// Sockel- und Kranzprofil fuer Schraenke. Ein Korpus mit abgesetztem Fuss
    /// und ueberstehendem Kranz sieht nach Moebel aus, ein nackter Quader nicht.
    func caseProfile(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat, _ h: Float,
                     _ mat: SCNMaterial) {
        prop(w + 0.09, 0.09, d + 0.09, x, 0.045, z, mat)          // Sockelplatte
        prop(w + 0.04, 0.07, d + 0.04, x, 0.125, z, mat)          // Sockelprofil
        prop(w + 0.13, 0.07, d + 0.12, x, h - 0.035, z, mat)      // Kranz
        prop(w + 0.06, 0.06, d + 0.06, x, h - 0.10, z, mat)
    }

    /// Gerundete Kante als Viertelstab - fuer Tischplatten und Simse.
    func roundedEdge(_ x: Float, _ y: Float, _ z: Float, _ len: CGFloat,
                     _ r: CGFloat, _ alongZ: Bool, _ mat: SCNMaterial) {
        cylE(r, len, x, y, z, alongZ ? SCNVector3(Float.pi/2, 0, 0) : SCNVector3(0, 0, Float.pi/2), mat)
    }

    /// Gedrechseltes Bein: Fuss, Ringe, verjuengter Schaft.
    func turnedLeg(_ x: Float, _ y0: Float, _ z: Float, _ h: Float, _ r: CGFloat, _ mat: SCNMaterial) {
        prop(r * 2.2, 0.045, r * 2.2, x, y0 + 0.022, z, mat)
        cyl(r * 0.80, CGFloat(h * 0.16), x, y0 + h * 0.12, z, mat)
        cyl(r * 1.30, 0.035, x, y0 + h * 0.21, z, mat)
        cyl(r * 0.66, CGFloat(h * 0.40), x, y0 + h * 0.43, z, mat)
        cyl(r * 1.18, 0.035, x, y0 + h * 0.65, z, mat)
        cyl(r * 0.88, CGFloat(h * 0.28), x, y0 + h * 0.81, z, mat)
        prop(r * 2.3, 0.05, r * 2.3, x, y0 + h - 0.025, z, mat)
    }

    /// Kerzenleuchter mit mehreren Armen, fuer Tische und Kommoden.
    func candelabra(_ x: Float, _ y: Float, _ z: Float, _ arms: Int) {
        let br = texMat(Tex.brass, 1, 1)
        let wax = col(0.84, 0.80, 0.68)
        prop(0.20, 0.035, 0.20, x, y + 0.017, z, br)
        cyl(0.028, 0.34, x, y + 0.20, z, br)
        cyl(0.055, 0.030, x, y + 0.12, z, br)
        for i in 0..<arms {
            let a = Double(i) / Double(arms) * Double.pi * 2.0
            let px = x + Float(cos(a)) * 0.13, pz = z + Float(sin(a)) * 0.13
            cylE(0.016, 0.17, (x + px) / 2, y + 0.33, (z + pz) / 2,
                 SCNVector3(Float(sin(a)) * 1.1, 0, -Float(cos(a)) * 1.1), br)
            cyl(0.042, 0.022, px, y + 0.38, pz, br)
            cyl(0.024, 0.13, px, y + 0.45, pz, wax)
            sph(0.034, px, y + 0.53, pz, glowMat(1.0, 0.88, 0.58))
        }
        cyl(0.026, 0.15, x, y + 0.46, z, wax)
        sph(0.036, x, y + 0.55, z, glowMat(1.0, 0.90, 0.62))
        addOmni(SCNVector3(x, y + 0.55, z), 260, UIColor(red: 1.0, green: 0.82, blue: 0.54, alpha: 1), range: 5)
    }

    // Zylinder mit freier Drehung - Grundlage fuer die Rohrleitungen
    func cylE(_ r: CGFloat, _ h: CGFloat, _ x: Float, _ y: Float, _ z: Float,
              _ euler: SCNVector3, _ mat: SCNMaterial) {
        let g = SCNCylinder(radius: r, height: h); g.radialSegmentCount = 10
        g.firstMaterial = mat
        let n = SCNNode(geometry: g); n.position = SCNVector3(x, y, z); n.eulerAngles = euler
        scene.rootNode.addChildNode(n)
    }
    // waagerechtes Rohr entlang x, mit Flanschen im Abstand
    func pipeX(_ x0: Float, _ x1: Float, _ y: Float, _ z: Float, _ r: CGFloat, _ mat: SCNMaterial) {
        cylE(r, CGFloat(abs(x1 - x0)), (x0 + x1) / 2, y, z, SCNVector3(0, 0, Float.pi / 2), mat)
        var t = min(x0, x1) + 1.1
        while t < max(x0, x1) - 0.3 {
            cylE(r * 1.45, 0.09, t, y, z, SCNVector3(0, 0, Float.pi / 2), mat); t += 1.7
        }
    }
    func pipeZ(_ z0: Float, _ z1: Float, _ y: Float, _ x: Float, _ r: CGFloat, _ mat: SCNMaterial) {
        cylE(r, CGFloat(abs(z1 - z0)), x, y, (z0 + z1) / 2, SCNVector3(Float.pi / 2, 0, 0), mat)
        var t = min(z0, z1) + 1.1
        while t < max(z0, z1) - 0.3 {
            cylE(r * 1.45, 0.09, x, y, t, SCNVector3(Float.pi / 2, 0, 0), mat); t += 1.7
        }
    }
    func pipeY(_ y0: Float, _ y1: Float, _ x: Float, _ z: Float, _ r: CGFloat, _ mat: SCNMaterial) {
        cyl(r, CGFloat(abs(y1 - y0)), x, (y0 + y1) / 2, z, mat)
        cyl(r * 1.45, 0.09, x, min(y0, y1) + 0.5, z, mat)
    }
    // Absperrschieber mit Handrad
    func valve(_ x: Float, _ y: Float, _ z: Float, _ mat: SCNMaterial) {
        cyl(0.10, 0.16, x, y, z, mat)
        let t = SCNTorus(ringRadius: 0.17, pipeRadius: 0.022); t.firstMaterial = mat
        let n = SCNNode(geometry: t); n.position = SCNVector3(x, y + 0.14, z)
        scene.rootNode.addChildNode(n)
        cylE(0.016, 0.34, x, y + 0.14, z, SCNVector3(0, 0, Float.pi / 2), mat)
        cylE(0.016, 0.34, x, y + 0.14, z, SCNVector3(Float.pi / 2, 0, 0), mat)
        cyl(0.030, 0.06, x, y + 0.16, z, mat)
    }
    // Pfuetze auf dem Boden - benutzt dieselbe Wasserlage
    func puddle(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat) {
        waterSurface(x, 0.012, z, w, d,
                     tint: UIColor(red: 0.36, green: 0.34, blue: 0.30, alpha: 1),
                     murk: 0.80, rep: Float(w) * 0.35, flow: 0.006)
    }

    // nackte Gluehbirne an einem Kabel
    func bulb(_ x: Float, _ z: Float, _ ceilY: Float, _ drop: Float, _ intensity: CGFloat) {
        let y = ceilY - drop
        cyl(0.008, CGFloat(drop), x, y + drop / 2, z, col(0.10, 0.09, 0.08))
        cyl(0.035, 0.07, x, y + 0.05, z, texMat(Tex.brass, 1, 1))
        sph(0.055, x, y, z, glowMat(1.0, 0.90, 0.68))
        addOmni(SCNVector3(x, y - 0.05, z), intensity, UIColor(red: 1.0, green: 0.88, blue: 0.68, alpha: 1), range: 9)
    }

    // Kasten mit freier Drehung (fuer Handlauf, Leuchterarme usw.)
    @discardableResult
    func propE(_ w: CGFloat, _ h: CGFloat, _ d: CGFloat, _ x: Float, _ y: Float, _ z: Float,
               _ euler: SCNVector3, _ mat: SCNMaterial) -> SCNNode {
        let g = SCNBox(width: w, height: h, length: d, chamferRadius: 0.01)
        g.firstMaterial = mat
        let n = SCNNode(geometry: g)
        n.position = SCNVector3(x, y, z)
        n.eulerAngles = euler
        scene.rootNode.addChildNode(n)
        return n
    }

    // ===================== Moebel =====================

    // Tisch: profilierte Platte, Zarge, vier gedrechselte Beine
    func tableAt(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat, _ h: Float,
                 _ top: SCNMaterial, _ leg: SCNMaterial) {
        contactShadow(x, z, w + 0.22, d + 0.22)
        prop(w, 0.055, d, x, h, z, top, solid: true)
        prop(w + 0.05, 0.035, d + 0.05, x, h - 0.038, z, top)      // ueberstehende Kante
        // gerundete Vorderkante statt scharfer Schnitt
        roundedEdge(x, h - 0.018, z - Float(d)/2 - 0.02, w, 0.028, false, top)
        roundedEdge(x, h - 0.018, z + Float(d)/2 + 0.02, w, 0.028, false, top)
        roundedEdge(x - Float(w)/2 - 0.02, h - 0.018, z, d, 0.028, true, top)
        roundedEdge(x + Float(w)/2 + 0.02, h - 0.018, z, d, 0.028, true, top)
        prop(w - 0.22, 0.13, d - 0.22, x, h - 0.13, z, leg)        // Zarge
        let lx = Float(w) / 2 - 0.15, lz = Float(d) / 2 - 0.15
        for sx in [-1, 1] { for sz in [-1, 1] {
            turnedLeg(x + lx * Float(sx), 0, z + lz * Float(sz), h - 0.20, 0.052, leg)
        }}
    }

    // Stuhl. back: "n" = Lehne im Norden (kleineres z), sonst "s","e","w"
    func chairAt(_ x: Float, _ z: Float, _ back: String, _ mat: SCNMaterial) {
        contactShadow(x, z, 0.62, 0.62)
        prop(0.46, 0.055, 0.46, x, 0.465, z, mat, solid: true)
        prop(0.42, 0.035, 0.42, x, 0.432, z, mat)
        for sx in [-1, 1] {
            turnedLeg(x + 0.175 * Float(sx), 0, z + 0.175, 0.43, 0.030, mat)
            turnedLeg(x + 0.175 * Float(sx), 0, z - 0.175, 0.43, 0.030, mat)
        }
        prop(0.40, 0.035, 0.035, x, 0.18, z + 0.175, mat)          // Sprossen unten
        prop(0.40, 0.035, 0.035, x, 0.18, z - 0.175, mat)
        prop(0.035, 0.035, 0.40, x - 0.175, 0.14, z, mat)

        var bx = x, bz = z, horiz = true
        switch back {
        case "n": bz = z - 0.20
        case "s": bz = z + 0.20
        case "w": bx = x - 0.20; horiz = false
        default:  bx = x + 0.20; horiz = false
        }
        let bw: CGFloat = horiz ? 0.46 : 0.055
        let bd: CGFloat = horiz ? 0.055 : 0.46
        // zwei Pfosten, oberer Abschluss, drei senkrechte Sprossen
        for sgn in [-1, 1] {
            let px = horiz ? x + 0.20 * Float(sgn) : bx
            let pz = horiz ? bz : z + 0.20 * Float(sgn)
            prop(0.055, 0.62, 0.055, px, 0.77, pz, mat)
            sph(0.036, px, 1.09, pz, mat)
        }
        prop(bw, 0.075, bd, bx, 1.06, bz, mat)
        prop(bw * 0.90, 0.05, bd * 0.90, bx, 0.60, bz, mat)
        for k in -1...1 {
            let px = horiz ? x + Float(k) * 0.125 : bx
            let pz = horiz ? bz : z + Float(k) * 0.125
            prop(0.038, 0.44, 0.038, px, 0.82, pz, mat)
        }
    }

    // Buecherregal. Die Buchruecken sind eine Textur - sieht dichter aus als
    // Einzelkloetze und spart ein paar hundert Knoten.
    func bookshelfZ(_ x: Float, _ z: Float, _ w: CGFloat, _ faceZ: Float, _ mat: SCNMaterial) {
        contactShadow(x, z, 0.7, 2.6)
        let h: CGFloat = 2.5
        let books = texMat(Tex.books, max(1, Float(w) / 1.3), 1)
        prop(w, h, 0.42, x, Float(h) / 2, z, mat, solid: true)
        prop(w + 0.12, 0.13, 0.52, x, Float(h) + 0.06, z, mat)      // Kranzgesims
        prop(w + 0.08, 0.11, 0.48, x, 0.055, z, mat)                // Sockel
        prop(0.07, h, 0.44, x - Float(w) / 2, Float(h) / 2, z, mat) // Seitenwangen
        prop(0.07, h, 0.44, x + Float(w) / 2, Float(h) / 2, z, mat)
        for i in 0..<4 {
            let sy = 0.30 + Float(i) * 0.55
            prop(w - 0.10, 0.05, 0.36, x, sy, z + faceZ * 0.03, mat)
            prop(w - 0.16, 0.42, 0.22, x, sy + 0.235, z + faceZ * 0.09, books)
        }
    }

    // Kommode / Anrichte
    func cabinetAt(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat, _ mat: SCNMaterial, _ knob: SCNMaterial) {
        contactShadow(x, z, w + 0.2, d + 0.2)
        prop(w, 0.78, d, x, 0.50, z, mat, solid: true)
        caseProfile(x, z, w, d, 0.95, mat)
        let n = Int(w / 0.55)
        for i in 0..<max(1, n) {
            let dx = -Float(w) / 2 + Float(w) / Float(max(1, n)) * (Float(i) + 0.5)
            prop(CGFloat(Float(w) / Float(max(1, n))) - 0.08, 0.30, 0.03, x + dx, 0.62, z + Float(d) / 2, mat)
            prop(CGFloat(Float(w) / Float(max(1, n))) - 0.08, 0.30, 0.03, x + dx, 0.26, z + Float(d) / 2, mat)
            sph(0.035, x + dx, 0.62, z + Float(d) / 2 + 0.03, knob)
            sph(0.035, x + dx, 0.26, z + Float(d) / 2 + 0.03, knob)
        }
    }

    // Kamin mit ausgemauertem Feuerraum, Sims auf Konsolen, Scheiten, Glut
    // und flackerndem Licht. faceX = +1 oeffnet nach +x, -1 nach -x.
    func fireplaceX(_ x: Float, _ z: Float, _ faceX: Float) {
        let stone = texMat(Tex.marble, 1, 2)
        let brickM = texMat(Tex.brick, 1, 1)
        let soot = col(0.06, 0.055, 0.05)
        let ironM = texMat(Tex.iron, 1, 1)
        let woodL = texMat(Tex.plankWood, 1, 1)

        // Korpus: zwei Wangen und ein Sturz, dazwischen bleibt der Feuerraum frei
        let bw: CGFloat = 1.0                      // Tiefe in x
        prop(bw, 2.7, 0.75, x, 1.35, z - 1.28, stone, solid: true)   // Wange
        prop(bw, 2.7, 0.75, x, 1.35, z + 1.28, stone, solid: true)
        prop(bw, 0.95, 1.85, x, 2.22, z, stone)                      // Sturz
        prop(bw + 0.34, 0.16, 3.5, x + faceX * 0.10, 1.80, z, stone) // Sims
        for sz in [-1, 1] {                                          // Konsolen
            prop(0.34, 0.30, 0.30, x + faceX * 0.22, 1.60, z + 1.05 * Float(sz), stone)
        }
        prop(bw + 0.30, 0.12, 3.4, x + faceX * 0.08, 0.06, z, stone) // Bodenplatte

        // Feuerraum ausgemauert
        prop(0.10, 1.55, 1.85, x - faceX * 0.42, 0.80, z, brickM)    // Rueckwand
        prop(0.86, 1.55, 0.10, x, 0.80, z - 0.92, brickM)            // Seiten
        prop(0.86, 1.55, 0.10, x, 0.80, z + 0.92, brickM)
        prop(0.86, 0.10, 1.85, x, 1.55, z, soot)                     // Rauchfang
        prop(0.86, 0.05, 1.85, x, 0.14, z, soot)                     // Aschebett

        // Feuerbock und Scheite
        for sz in [-1, 1] {
            prop(0.55, 0.05, 0.05, x, 0.28, z + 0.42 * Float(sz), ironM)
            prop(0.05, 0.26, 0.05, x - 0.24, 0.15, z + 0.42 * Float(sz), ironM)
            prop(0.05, 0.34, 0.05, x + 0.24, 0.19, z + 0.42 * Float(sz), ironM)
        }
        cylE(0.085, 0.95, x - 0.06, 0.36, z, SCNVector3(Float.pi / 2, 0, 0), woodL)
        cylE(0.075, 0.90, x + 0.14, 0.34, z - 0.10, SCNVector3(Float.pi / 2, 0.2, 0), woodL)
        cylE(0.070, 0.85, x + 0.02, 0.50, z + 0.08, SCNVector3(Float.pi / 2, -0.3, 0.15), woodL)

        // Glut: mehrere kleine Koerper statt eines Balkens
        for k in 0..<7 {
            let ex = x - 0.22 + Float(k % 3) * 0.20 + Float.random(in: -0.04...0.04)
            let ez = z - 0.55 + Float(k) * 0.18
            let hot = 0.55 + Float(k % 3) * 0.15
            sph(CGFloat(0.035 + Double(k % 2) * 0.02), ex, 0.20, ez,
                glowMat(1.0, CGFloat(0.30 + Double(hot) * 0.22), 0.06))
        }
        // Flammenzungen
        for k in 0..<4 {
            let fz = z - 0.34 + Float(k) * 0.22
            let g = SCNCone(topRadius: 0, bottomRadius: 0.085, height: CGFloat(0.26 + Double(k % 2) * 0.10))
            g.radialSegmentCount = 6
            g.firstMaterial = glowMat(1.0, 0.52, 0.14)
            let n = SCNNode(geometry: g)
            n.position = SCNVector3(x + Float.random(in: -0.06...0.10), 0.34, fz)
            scene.rootNode.addChildNode(n)
        }

        // Licht: warmer Kegel nach vorn, flackernd, plus Schein auf der Bodenplatte
        let fire = UIColor(red: 1.0, green: 0.48, blue: 0.16, alpha: 1)
        let key = addSpot(SCNVector3(x + faceX * 0.30, 0.62, z), SCNVector3(x + faceX * 4.0, 0.30, z),
                          1500, fire, inner: 26, outer: 92, range: 9)
        registerFlicker(key, 1500)
        let fill = addOmni(SCNVector3(x + faceX * 0.55, 0.55, z), 700, fire, range: 6)
        registerFlicker(fill, 700)
        floorPool(x + faceX * 1.25, z, 1.7, 1.5, 0.40, fire)
        lightShaft(SCNVector3(x + faceX * 0.35, 0.55, z), SCNVector3(x + faceX * 2.6, 0.05, z),
                   1.5, 0.26, fire)
        addDust(x + faceX * 1.4, 0.9, z, 3.2, 1.8, 3.0, 7)
    }

    // Standuhr
    func grandClock(_ x: Float, _ z: Float) {
        contactShadow(x, z, 0.75, 0.55)
        let w = col(0.30, 0.20, 0.11), g = col(0.62, 0.50, 0.22)
        prop(0.66, 2.3, 0.42, x, 1.15, z, w, solid: true)
        prop(0.78, 0.14, 0.52, x, 2.34, z, w)
        prop(0.46, 0.46, 0.05, x, 1.92, z + 0.22, col(0.86, 0.83, 0.74))
        cyl(0.02, 0.30, x, 1.92, z + 0.26, g)
        prop(0.30, 0.90, 0.05, x, 1.05, z + 0.22, col(0.10, 0.09, 0.08))
        sph(0.11, x, 0.78, z + 0.24, g)   // Pendel
    }

    // Chesterfield-artiges Sofa: getuftetes Polster, Rollarme, gedrechselte Fuesse.
    // faceZ = Blickrichtung (-1 = schaut nach -z)
    func sofaAt(_ x: Float, _ z: Float, _ w: CGFloat, _ faceZ: Float,
                _ fab: SCNMaterial, _ wood: SCNMaterial) {
        contactShadow(x, z, w + 0.3, 1.15)
        let fw = Float(w)
        let btn = col(0.42, 0.34, 0.20)
        prop(w, 0.20, 0.94, x, 0.40, z, fab, solid: true)                  // Sitzrahmen
        // zwei Sitzkissen
        for k in [-1, 1] {
            prop(w / 2 - 0.16, 0.16, 0.80, x + Float(k) * (fw / 4), 0.56, z, fab)
        }
        // Rueckenlehne, leicht nach hinten geneigt
        propE(w, 0.72, 0.20, x, 0.86, z - faceZ * 0.38, SCNVector3(faceZ * 0.13, 0, 0), fab)
        prop(w, 0.14, 0.26, x, 1.22, z - faceZ * 0.42, fab)                // Wulst oben
        // Armlehnen als liegende Rollen - vorher endete das Sofa in offenen
        // Kastenkanten. Vorn je eine Kugelkappe und ein gedrechselter Fuss.
        for sg2 in [-1, 1] {
            let ax = x + Float(sg2) * (fw / 2 + 0.02)
            cylE(0.105, 0.86, ax, 0.72, z - faceZ * 0.04,
                 SCNVector3(Float.pi / 2, 0, 0), fab)
            sph(0.105, ax, 0.72, z + faceZ * 0.38, fab)
            cyl(0.035, 0.30, ax, 0.15, z + faceZ * 0.34, wood)
        }
        // Knoepfe im Rautenraster
        var bxs: [Float] = []
        var t = -fw / 2 + 0.28
        while t < fw / 2 - 0.20 { bxs.append(t); t += 0.30 }
        for (i2, bx) in bxs.enumerated() {
            for (row, by) in [(0, Float(0.78)), (1, Float(1.03))] {
                if row == 1 && i2 % 2 == 0 { continue }
                sph(0.028, x + bx, by, z - faceZ * 0.475, btn)
            }
        }
        // Rollarme
        for sgn in [-1, 1] {
            let ax = x + (fw / 2 - 0.13) * Float(sgn)
            prop(0.26, 0.44, 0.94, ax, 0.62, z, fab)
            cylE(0.13, 0.90, ax, 0.86, z, SCNVector3(Float.pi / 2, 0, 0), fab)
            sph(0.13, ax, 0.86, z + 0.45, fab)
            sph(0.13, ax, 0.86, z - 0.45, fab)
        }
        // Fuesse
        for sx in [-1, 1] { for sz in [-1, 1] {
            turnedLeg(x + (fw / 2 - 0.18) * Float(sx), 0, z + 0.38 * Float(sz), 0.30, 0.036, wood)
        }}
        blocker(x - fw / 2, x + fw / 2, z - 0.55, z + 0.55)
    }

    /// Ohrensessel - dieselbe Machart, nur schmal.
    func armchairAt(_ x: Float, _ z: Float, _ faceZ: Float, _ fab: SCNMaterial, _ wood: SCNMaterial) {
        contactShadow(x, z, 1.05, 1.05)
        sofaAt(x, z, 0.98, faceZ, fab, wood)
        // Ohren an der Lehne
        for sgn in [-1, 1] {
            prop(0.14, 0.46, 0.30, x + 0.40 * Float(sgn), 1.18, z - faceZ * 0.26, fab)
        }
    }

    // Kiste
    func crateAt(_ x: Float, _ y: Float, _ z: Float, _ s: CGFloat, _ mat: SCNMaterial, _ trim: SCNMaterial) {
        prop(s, s, s, x, y + Float(s) / 2, z, mat, solid: y < 0.1)
        prop(s + 0.02, 0.06, 0.06, x, y + Float(s) - 0.06, z + Float(s) / 2, trim)
        prop(s + 0.02, 0.06, 0.06, x, y + 0.06, z + Float(s) / 2, trim)
        prop(0.06, s, 0.06, x - Float(s) / 2 + 0.05, y + Float(s) / 2, z + Float(s) / 2, trim)
        prop(0.06, s, 0.06, x + Float(s) / 2 - 0.05, y + Float(s) / 2, z + Float(s) / 2, trim)
    }

    func barrelAt(_ x: Float, _ z: Float) {
        contactShadow(x, z, 0.68, 0.68)
        let w = col(0.30, 0.20, 0.12), m = col(0.34, 0.32, 0.28)
        cyl(0.34, 0.92, x, 0.46, z, w)
        cyl(0.36, 0.07, x, 0.24, z, m)
        cyl(0.36, 0.07, x, 0.68, z, m)
        blocker(x - 0.34, x + 0.34, z - 0.34, z + 0.34)
    }

    // Kuechenzeile entlang x
    func counterRun(_ x0: Float, _ x1: Float, _ z: Float, _ faceZ: Float) {
        let body = col(0.42, 0.42, 0.38), top = col(0.30, 0.30, 0.28), knob = col(0.62, 0.62, 0.58)
        let w = CGFloat(x1 - x0), cx = (x0 + x1) / 2
        prop(w, 0.86, 0.68, cx, 0.43, z, body, solid: true)
        prop(w + 0.04, 0.07, 0.74, cx, 0.90, z, top)
        var dx = x0 + 0.35
        while dx < x1 - 0.2 {
            prop(0.56, 0.62, 0.03, dx, 0.52, z + faceZ * 0.35, body)
            prop(0.10, 0.035, 0.035, dx, 0.78, z + faceZ * 0.38, knob)
            dx += 0.70
        }
    }

    func stoveAt(_ x: Float, _ z: Float) {
        let m = texMat(Tex.iron, 1, 1), d = col(0.10, 0.10, 0.10)
        prop(1.1, 0.90, 0.70, x, 0.45, z, m, solid: true)
        prop(1.14, 0.06, 0.74, x, 0.93, z, d)
        for sx in [-1, 1] { for sz in [-1, 1] {
            cyl(0.13, 0.03, x + 0.26 * Float(sx), 0.97, z + 0.16 * Float(sz), col(0.16, 0.16, 0.16))
        }}
        prop(0.90, 0.44, 0.04, x, 0.50, z + 0.36, d)
        prop(0.90, 0.05, 0.09, x, 0.72, z + 0.40, col(0.60, 0.60, 0.58))
    }

    func fridgeAt(_ x: Float, _ z: Float) {
        let m = col(0.60, 0.60, 0.56), d = col(0.44, 0.44, 0.42)
        prop(1.0, 1.95, 0.72, x, 0.98, z, m, solid: true)
        prop(0.46, 1.85, 0.04, x - 0.25, 0.98, z + 0.37, d)
        prop(0.46, 1.85, 0.04, x + 0.25, 0.98, z + 0.37, d)
        prop(0.05, 0.60, 0.05, x - 0.04, 1.30, z + 0.41, col(0.70, 0.70, 0.66))
        prop(0.05, 0.60, 0.05, x + 0.04, 1.30, z + 0.41, col(0.70, 0.70, 0.66))
    }

    // Standwaschbecken mit Saeule, Armatur und zwei Ventilen
    /// base = Fussbodenhoehe, damit dieselben Becken auch im Obergeschoss stehen.
    func sinkAt(_ x: Float, _ z: Float, base: Float = 0) {
        let p = texMat(Tex.enamel, 1, 1)
        let foul = texMat(Tex.enamelFoul, 1, 1)
        let br = texMat(Tex.brass, 1, 1)
        contactShadow(x, z, 0.85, 0.65, y: base + 0.012)
        prop(0.34, 0.10, 0.30, x, base + 0.05, z - 0.06, p)               // Fuss
        prop(0.24, 0.64, 0.24, x, base + 0.37, z - 0.06, p, solid: true)  // Saeule
        prop(0.74, 0.17, 0.52, x, base + 0.78, z, p, solid: true)         // Becken
        prop(0.56, 0.06, 0.36, x, base + 0.855, z + 0.01, foul)           // Beckenmulde
        prop(0.16, 0.11, 0.11, x, base + 0.91, z - 0.20, br)
        cyl(0.022, 0.17, x, base + 0.99, z - 0.20, br)
        prop(0.045, 0.045, 0.15, x, base + 1.055, z - 0.13, br)           // Auslauf
        cyl(0.018, 0.07, x - 0.14, base + 0.94, z - 0.20, br)
        cyl(0.018, 0.07, x + 0.14, base + 0.94, z - 0.20, br)
    }

    // Spiegel mit Holzrahmen. faceZ = Blickrichtung der Glasflaeche
    func mirrorAt(_ x: Float, _ y: Float, _ z: Float, _ w: CGFloat, _ h: CGFloat, _ faceZ: Float) {
        prop(w + 0.11, h + 0.11, 0.06, x, y, z, texMat(Tex.wainscot, 1, 1))
        prop(w, h, 0.02, x, y, z + faceZ * 0.038, artMat(Tex.mirror))
    }

    // WC mit Spuelkasten
    func toiletAt(_ x: Float, _ z: Float) {
        let p = texMat(Tex.enamel, 1, 1)
        prop(0.34, 0.30, 0.44, x, 0.15, z, p, solid: true)
        prop(0.42, 0.17, 0.54, x, 0.375, z + 0.04, p)
        prop(0.32, 0.05, 0.42, x, 0.445, z + 0.04, texMat(Tex.enamelFoul, 1, 1))
        prop(0.44, 0.04, 0.50, x, 0.485, z + 0.04, texMat(Tex.wainscot, 1, 1))
        prop(0.46, 0.56, 0.22, x, 0.74, z - 0.28, p, solid: true)
        prop(0.50, 0.06, 0.26, x, 1.05, z - 0.28, p)
        prop(0.07, 0.05, 0.05, x + 0.17, 0.99, z - 0.16, texMat(Tex.brass, 1, 1))
    }

    // Offene Wanne aus fuenf Platten, damit man hineinsieht.
    // Innen die verdreckte Emailtextur - Rostfahnen, Schmutzrand, Pfuetze.
    /// Dreiecksnetz mit Flaechennormalen und einfacher planarer UV.
    @discardableResult
    func triMesh(_ tris: [(SCNVector3, SCNVector3, SCNVector3)], _ mat: SCNMaterial,
                 uvScale: Float = 1.1) -> SCNNode {
        var verts: [SCNVector3] = []; var norms: [SCNVector3] = []
        var uvs: [CGPoint] = []; var idx: [Int32] = []
        for t in tris {
            let u = SCNVector3(t.1.x - t.0.x, t.1.y - t.0.y, t.1.z - t.0.z)
            let v = SCNVector3(t.2.x - t.0.x, t.2.y - t.0.y, t.2.z - t.0.z)
            var n = SCNVector3(u.y*v.z - u.z*v.y, u.z*v.x - u.x*v.z, u.x*v.y - u.y*v.x)
            let l = max(1e-6, (n.x*n.x + n.y*n.y + n.z*n.z).squareRoot())
            n = SCNVector3(n.x/l, n.y/l, n.z/l)
            for p in [t.0, t.1, t.2] {
                verts.append(p); norms.append(n)
                uvs.append(CGPoint(x: CGFloat((p.x + p.z) * uvScale),
                                   y: CGFloat((p.y + p.z * 0.5) * uvScale)))
                idx.append(Int32(verts.count - 1))
            }
        }
        let g = SCNGeometry(sources: [SCNGeometrySource(vertices: verts),
                                      SCNGeometrySource(normals: norms),
                                      SCNGeometrySource(textureCoordinates: uvs)],
                            elements: [SCNGeometryElement(indices: idx, primitiveType: .triangles)])
        g.firstMaterial = mat
        let node = SCNNode(geometry: g)
        scene.rootNode.addChildNode(node)
        return node
    }

    /// Freistehende Wanne als echtes Becken. Superellipsen-Ringe: aussen hoch,
    /// ueber die Lippe, innen wieder hinab bis zum Beckenboden. In Python
    /// vermessen: Wand 5,5 cm, Tiefe 50 cm, Wasser 19 cm unter dem Rand.
    func bathtubAt(_ x: Float, _ z: Float, _ w: CGFloat, _ d: CGFloat) {
        contactShadow(x, z, w + 0.25, d + 0.25)
        let out = texMat(Tex.enamel, 2, 1)
        let br = texMat(Tex.brass, 1, 1)
        let rx = Float(w) / 2, rz = Float(d) / 2
        let ins: Float = 0.055
        let n = 16
        func spt(_ i: Int, _ ax: Float, _ az: Float, _ y: Float) -> SCNVector3 {
            let a = Float(i) / Float(n) * 2 * Float.pi
            let c = cos(a), sn = sin(a)
            let e: Float = 0.55
            let px = ax * (c < 0 ? -1 : 1) * pow(abs(c), e)
            let pz = az * (sn < 0 ? -1 : 1) * pow(abs(sn), e)
            return SCNVector3(x + px, y, z + pz)
        }
        // (y, HalbachseX, HalbachseZ) - aussen hinauf, innen hinab
        let R: [(Float, Float, Float)] = [
            (0.075, rx * 0.94,        rz * 0.94),
            (0.34,  rx,               rz),
            (0.60,  rx,               rz),
            (0.655, rx * 1.05,        rz * 1.035),         // Lippe
            (0.655, rx - ins,         rz - ins),
            (0.58,  rx - ins,         rz - ins),
            (0.24,  (rx - ins) * 0.90, (rz - ins) * 0.90),
            (0.155, (rx - ins) * 0.55, (rz - ins) * 0.55),
        ]
        var tris: [(SCNVector3, SCNVector3, SCNVector3)] = []
        for k in 0..<(R.count - 1) {
            for i in 0..<n {
                let j = (i + 1) % n
                // Gleiche Drehung wie beim Spielermodell: gegen den Uhrzeiger
                // von aussen, sonst cullt SceneKit die sichtbare Seite weg.
                tris.append((spt(i, R[k].1, R[k].2, R[k].0),
                             spt(j, R[k+1].1, R[k+1].2, R[k+1].0),
                             spt(i, R[k+1].1, R[k+1].2, R[k+1].0)))
                tris.append((spt(i, R[k].1, R[k].2, R[k].0),
                             spt(j, R[k].1, R[k].2, R[k].0),
                             spt(j, R[k+1].1, R[k+1].2, R[k+1].0)))
            }
        }
        let floorC = SCNVector3(x, 0.155, z)
        let baseC = SCNVector3(x, 0.075, z)
        for i in 0..<n {
            let j = (i + 1) % n
            tris.append((floorC, spt(i, R[7].1, R[7].2, 0.155), spt(j, R[7].1, R[7].2, 0.155)))
            tris.append((baseC,  spt(j, R[0].1, R[0].2, 0.075), spt(i, R[0].1, R[0].2, 0.075)))
        }
        triMesh(tris, out)

        // Wasser: 31 cm tief im Becken, traege fliessend
        // Kaltes, truebes Badewasser - das Braunschwarz davor las sich als
        // Blutsuppe und hat die ganze Wanne haesslich gemacht.
        waterSurface(x, 0.465, z, w - 0.17, d - 0.17,
                     tint: UIColor(red: 0.40, green: 0.47, blue: 0.44, alpha: 1),
                     murk: 0.58, rep: 1.3, flow: 0.006)
        for _ in 0..<4 {
            prop(CGFloat.random(in: 0.05...0.10), 0.012, CGFloat.random(in: 0.05...0.10),
                 x + Float.random(in: -0.3...0.3), 0.478, z + Float.random(in: -0.7...0.7),
                 col(0.58, 0.56, 0.50))    // Seifenreste statt Brocken
        }
        // Fuesse
        for sx in [-1, 1] { for sz in [-1, 1] {
            let px = x + (rx - 0.16) * Float(sx), pz = z + (rz - 0.16) * Float(sz)
            cyl(0.05, 0.10, px, 0.05, pz, br)
            sph(0.065, px, 0.045, pz, br)
        }}
        // Armatur am Kopfende
        prop(0.16, 0.14, 0.12, x, 0.72, z - rz + 0.16, br)
        cyl(0.030, 0.20, x, 0.82, z - rz + 0.16, br)
        prop(0.05, 0.05, 0.16, x, 0.90, z - rz + 0.24, br)
        cyl(0.025, 0.10, x - 0.11, 0.76, z - rz + 0.16, br)
        cyl(0.025, 0.10, x + 0.11, 0.76, z - rz + 0.16, br)
        blocker(x - rx, x + rx, z - rz, z + rz)
    }

    func statueAt(_ x: Float, _ z: Float) {
        contactShadow(x, z, 0.95, 0.95)
        let s = col(0.60, 0.59, 0.55), d = col(0.46, 0.45, 0.42)
        prop(0.90, 0.30, 0.90, x, 0.15, z, d, solid: true)
        prop(0.70, 0.90, 0.70, x, 0.75, z, d)
        prop(0.80, 0.10, 0.80, x, 1.25, z, d)
        prop(0.34, 0.90, 0.30, x, 1.75, z, s)          // Torso
        prop(0.14, 0.60, 0.16, x - 0.24, 1.70, z, s)   // Arme
        prop(0.14, 0.60, 0.16, x + 0.24, 1.70, z, s)
        prop(0.26, 0.28, 0.26, x, 2.34, z, s)          // Kopf
        blocker(x - 0.45, x + 0.45, z - 0.45, z + 0.45)
    }

    // Wandleuchte im Kerzenstil: Rueckplatte, geschwungener Arm, Tropfschale,
    // Kerze mit abgebranntem Wachs und Flamme. beam: true fuegt Lichtkegel dazu.
    func sconce(_ x: Float, _ y: Float, _ z: Float, _ dx: Float, _ dz: Float,
                beam: Bool = false) {
        let br = texMat(Tex.brass, 1, 1)
        let wax = col(0.80, 0.76, 0.64)
        let alongZ = abs(dx) > 0.5
        let pw: CGFloat = alongZ ? 0.045 : 0.17
        let pd: CGFloat = alongZ ? 0.17 : 0.045

        // Rueckplatte mit Profil
        prop(pw, 0.34, pd, x, y, z, br)
        prop(pw * 1.7, 0.05, pd * 1.7, x, y + 0.185, z, br)
        prop(pw * 1.7, 0.05, pd * 1.7, x, y - 0.185, z, br)
        prop(pw * 0.9, 0.09, pd * 0.9, x, y - 0.25, z, br)
        sph(0.030, x + dx * 0.02, y - 0.30, z + dz * 0.02, br)

        // Arm: zwei kurze Segmente, das gibt den Schwung
        propE(0.032, 0.16, 0.032, x + dx * 0.07, y + 0.05, z + dz * 0.07,
              SCNVector3(dz * 0.9, 0, -dx * 0.9), br)
        propE(0.030, 0.13, 0.030, x + dx * 0.17, y + 0.12, z + dz * 0.17,
              SCNVector3(dz * 0.35, 0, -dx * 0.35), br)

        // Tropfschale und Tuelle
        let fx = x + dx * 0.21, fz = z + dz * 0.21
        cyl(0.075, 0.022, fx, y + 0.175, fz, br)
        cyl(0.090, 0.014, fx, y + 0.188, fz, br)
        cyl(0.031, 0.055, fx, y + 0.215, fz, br)

        // Kerze, ungleich abgebrannt, mit Wachsnase
        let ch = CGFloat.random(in: 0.10...0.19)
        cyl(0.026, ch, fx, y + 0.24 + Float(ch) / 2, fz, wax)
        prop(0.020, 0.055, 0.020, fx + 0.020, y + 0.25, fz, wax)
        let tip = y + 0.24 + Float(ch)
        cyl(0.004, 0.020, fx, tip + 0.008, fz, col(0.12, 0.10, 0.09))   // Docht
        sph(0.026, fx, tip + 0.030, fz, glowMat(1.0, 0.72, 0.26))
        sph(0.014, fx, tip + 0.046, fz, glowMat(1.0, 0.94, 0.76))

        let warm = UIColor(red: 1.0, green: 0.78, blue: 0.46, alpha: 1)
        wallGlow(x, y + 0.22, z, 0.52, dx, dz, 0.36, warm)
        if beam {
            lightShaft(SCNVector3(fx, tip + 0.05, fz), SCNVector3(fx - dx * 0.22, y + 1.20, fz - dz * 0.22),
                       0.30, 0.24, warm)
            lightShaft(SCNVector3(fx, y + 0.18, fz), SCNVector3(fx - dx * 0.20, y - 1.00, fz - dz * 0.20),
                       0.30, 0.20, warm)
        }
        let l = addOmni(SCNVector3(fx + dx * 0.06, tip + 0.02, fz + dz * 0.06), 250, warm, range: 3.8)
        registerFlicker(l, 250)
    }

    // Bildmaterial unbeleuchtet-matt auf eine Flaeche legen
    func artMat(_ img: UIImage) -> SCNMaterial {
        let m = SCNMaterial()
        m.lightingModel = .lambert
        m.diffuse.contents = img
        m.diffuse.magnificationFilter = .nearest
        m.diffuse.mipFilter = .linear
        m.locksAmbientWithDiffuse = true
        return m
    }
    // Fenster leuchtet von sich aus, damit die Nacht dahinter sichtbar bleibt
    /// variant 0-2 = gleissende Wolkenscheibe (leuchtet und blueht ueber die
    /// Bloom-Schwelle), 3 = Sturmscheibe mit ablaufendem Regen.
    func windowMat(_ variant: Int = 0) -> SCNMaterial {
        let v = ((variant % 4) + 4) % 4
        let m = SCNMaterial()
        m.lightingModel = .constant
        m.diffuse.contents = Tex.windows[v]
        m.diffuse.wrapS = .repeat
        m.diffuse.wrapT = .repeat
        m.diffuse.magnificationFilter = .nearest
        if v == 3 {
            registerWater(m, 0, -0.055, 1.0)          // Regen laeuft die Scheibe hinab
        } else {
            m.emission.contents = Tex.windows[v]
            // 1.15 statt 2.20: mit 2.20 wurden aus Fenstern weisse Blueten,
            // die den halben Raum ueberstrahlt haben.
            m.emission.intensity = 1.15
            registerWater(m, 0.003, 0, 1.0)           // Wolken ziehen traege
        }
        return m
    }

    // Gemaelde. alongX = Bild haengt an einer Wand die entlang x laeuft.
    // Ohne art-Angabe wird eines der gemalten Bilder zufaellig gewaehlt.
    func picture(_ x: Float, _ y: Float, _ z: Float, _ w: CGFloat, _ h: CGFloat,
                 _ alongX: Bool, _ off: Float, _ art: UIImage? = nil) {
        let frame = col(0.46, 0.34, 0.15)
        let canvas = artMat(art ?? Tex.art.randomElement()!)
        if alongX {
            prop(w + 0.16, h + 0.16, 0.07, x, y, z, frame)
            prop(w, h, 0.02, x, y, z + off * 0.05, canvas)
        } else {
            prop(0.07, h + 0.16, w + 0.16, x, y, z, frame)
            prop(0.02, h, w, x + off * 0.05, y, z, canvas)
        }
    }

    func chandelier(_ x: Float, _ z: Float, _ y: Float, _ ceilY: Float, shadow: Bool = false) {
        let br = texMat(Tex.brass, 1, 1)
        let wax = col(0.86, 0.83, 0.72)
        cyl(0.022, CGFloat(ceilY - y), x, (y + ceilY) / 2, z, br)      // Abhaengung
        cyl(0.10, 0.07, x, ceilY - 0.04, z, br)                        // Deckenrosette
        cyl(0.09, 0.26, x, y + 0.02, z, br)                            // Mittelkorpus
        sph(0.11, x, y - 0.16, z, br)                                  // Abschlusskugel
        for tier in 0..<2 {
            let ty = y + Float(tier) * 0.28
            let rad = Float(0.68 - Double(tier) * 0.22)
            let arms = tier == 0 ? 8 : 6
            let ring = SCNTorus(ringRadius: CGFloat(rad), pipeRadius: 0.028)
            ring.firstMaterial = br
            let rn = SCNNode(geometry: ring); rn.position = SCNVector3(x, ty, z)
            scene.rootNode.addChildNode(rn)
            for i in 0..<arms {
                let a = Double(i) / Double(arms) * Double.pi * 2.0
                let ca = Float(cos(a)), sa = Float(sin(a))
                // Arm vom Korpus nach aussen, leicht ansteigend
                propE(0.035, CGFloat(rad), 0.035, x + ca * rad * 0.5, ty - 0.04, z + sa * rad * 0.5,
                      SCNVector3(sa * 1.35, 0, -ca * 1.35), br)
                let px = x + ca * rad, pz = z + sa * rad
                cyl(0.055, 0.035, px, ty + 0.06, pz, br)               // Tropfschale
                cyl(0.028, 0.15, px, ty + 0.15, pz, wax)               // Kerze
                sph(0.05, px, ty + 0.25, pz, glowMat(1.0, 0.88, 0.60))
                sph(0.026, px, ty + 0.285, pz, glowMat(1.0, 0.96, 0.82))
                // Behang
                sph(0.022, x + ca * rad * 0.78, ty - 0.13, z + sa * rad * 0.78, glowMat(0.80, 0.84, 0.92))
            }
        }
        // Lichtwirkung
        let warm = UIColor(red: 1.0, green: 0.84, blue: 0.56, alpha: 1)
        addSpot(SCNVector3(x, y - 0.10, z), SCNVector3(x, 0, z), 1500, warm,
                inner: 26, outer: 74, range: CGFloat(y) + 4, shadow: shadow)
        lightShaft(SCNVector3(x, y - 0.05, z), SCNVector3(x, 0.05, z), 1.7, 0.20, warm)
        floorPool(x, z, 2.5, 2.5, 0.34, warm)
    }

    func rug(_ w: CGFloat, _ d: CGFloat, _ x: Float, _ z: Float, _ img: UIImage) {
        let plane = SCNPlane(width: w, height: d)
        let m = SCNMaterial()
        m.lightingModel = .lambert
        m.diffuse.contents = img
        m.diffuse.magnificationFilter = .nearest
        m.diffuse.mipFilter = .linear
        m.diffuse.maxAnisotropy = 8
        m.locksAmbientWithDiffuse = true
        plane.firstMaterial = m
        plane.firstMaterial?.isDoubleSided = true
        let n = SCNNode(geometry: plane)
        n.eulerAngles.x = -Float.pi / 2
        n.position = SCNVector3(x, 0.015, z)
        scene.rootNode.addChildNode(n)
    }

    // Die alten Treppenbauer stairFlight() und switchbackStairs() sind
    // entfallen. Sie hatten feste 11 Stufen (damit liessen sich zwei
    // verschieden hohe Geschosse nie deckungsgleich stapeln) und setzten
    // Fuellkoerper mit blocksPlayer: true in den eigenen Lauf. Der Ersatz
    // steht in Stairwell.swift.

    // ===================== Villa =====================

    func buildVilla() {
        let fog = UIColor(red: 0.15, green: 0.15, blue: 0.17, alpha: 1)
        scene.background.contents = fog
        scene.fogColor = fog
        scene.fogStartDistance = 20
        scene.fogEndDistance = 62
        scene.fogDensityExponent = 1.2

        // Materialien
        let wHall  = texMat(Tex.wpGreen, 6, 2.6)
        let wDine  = texMat(Tex.wpRed, 6, 1.6)
        let wKit   = texMat(Tex.tileWhite, 6, 2.2)
        let wLib   = texMat(Tex.wpOlive, 5, 1.6)
        let wGal   = texMat(Tex.wpBrown, 4, 1.6)
        let wCorr  = texMat(Tex.wpBeige, 5, 1.6)
        let wBath  = texMat(Tex.tileGreen, 5, 2.2)
        let wStore = texMat(Tex.wpBrown, 3, 1.6)
        let wStudy = texMat(Tex.wpBlue, 6, 1.6)
        let wCell  = texMat(Tex.concrete, 4, 1.4)
        let wSalon = texMat(Tex.wpRed, 6, 1.8)

        let wood     = texMat(Tex.plankWood, 1, 1)
        let darkWood = texMat(Tex.wainscot, 2, 1)
        let stone    = texMat(Tex.marble, 1, 2)
        let brass    = col(0.66, 0.54, 0.24)
        let fabricRd = texMat(Tex.velvet, 2, 2)
        let fabricGn = texMat(Tex.velvetGreen, 2, 2)

        // ---------- Boeden + Decken ----------
        floorTile(16, 14, 0, 7, texMat(Tex.stoneFloor, 4, 3.5))
        floorTile(16, 12, -16, 8, texMat(Tex.parquet, 4, 3))
        floorTile(12, 12, -18, -4, texMat(Tex.tileWhite, 6, 6))
        floorTile(14, 12, 15, 8, texMat(Tex.parquet, 3.5, 3))
        floorTile(10, 12, 17, -4, texMat(Tex.stoneFloor, 2.5, 3))
        floorTile(6, 14, 0, -7, texMat(Tex.woodFloor, 1.5, 3.5))
        floorTile(7, 7, -6.5, -7.5, texMat(Tex.tileGreen, 3.5, 3.5))
        floorTile(7, 7, 6.5, -7.5, texMat(Tex.woodFloor, 2, 2))
        floorTile(14, 10, 0, -19, texMat(Tex.woodFloor, 3.5, 2.5))
        floorTile(7, 36, -27.5, -4, texMat(Tex.parquet, 2, 10))       // Westflur
        floorTile(16, 16, -39, -14, texMat(Tex.parquet, 4, 4))        // Salon
        floorTile(8, 1.8, 7, -12.5, texMat(Tex.concrete, 3, 1))
        floorTile(12, 11.5, 17, -17.25, texMat(Tex.concrete, 5, 5))

        // Hallendecke OHNE den Treppenschacht x[-8,-4] z[6,14] - dort geht der
        // Raum ueber drei Geschosse bis unters Badehaus durch. Eine durchgehende
        // Platte auf y = 6.0 lag bisher mitten im oberen Treppenlauf.
        ceiling(12, 14, 2, 7, 6)              // x[-4,8]
        ceiling(4, 6, -6, 3, 6)               // x[-8,-4], z[0,6]
        ceiling(16, 12, -16, 8, 4);   ceiling(12, 12, -18, -4, 3.2)
        ceiling(14, 12, 15, 8, 4);    ceiling(10, 12, 17, -4, 4)
        ceiling(6, 14, 0, -7, 3.0);   ceiling(7, 7, -6.5, -7.5, 2.7)
        ceiling(7, 7, 6.5, -7.5, 3.0); ceiling(14, 10, 0, -19, 3.6)
        ceiling(7, 36, -27.5, -4, 3.4); ceiling(16, 16, -39, -14, 4.2)
        ceiling(8, 1.8, 7, -12.5, 2.6); ceiling(12, 11.5, 17, -17.25, 2.6)

        // ---------- Waende ----------
        // Hoehe pro Raum: kleine Raeume niedriger, sonst wirken sie wie Hallen
        wallX(-8, 8, 14, wHall, h: 6)                                            // Haupthalle
        wallX(-8, 8, 0, wHall, gaps: [(0, 2.4), (-5.5, 1.3)], h: 6)
        wallZ(0, 14, -8, wHall, gaps: [(3.5, 2.4)], h: 6)
        wallZ(0, 14, 8, wHall, gaps: [(8, 2.4)], h: 6)

        // (Ostwand des Speisezimmers entfaellt - die Westflurwand bei x=-24
        //  steht schon da und hat dieselbe Tuerluecke. Drei Boxen an derselben
        //  Stelle haben um dieselben Pixel gekaempft.)
        wallX(-24, -8, 2, wDine, gaps: [(-18, 2.4)], h: 4)
        wallX(-24, -8, 14, wDine, h: 4)

        // (Ostwand der Kueche entfaellt - siehe oben, dieselbe Wand.)
        wallX(-24, -12, -10, wKit, h: 3.2, wainscot: false)
        wallZ(-10, 2, -12, wKit, h: 3.2, wainscot: false)

        wallZ(2, 14, 22, wLib, h: 4)                                             // Bibliothek
        wallX(8, 22, 2, wLib, gaps: [(17, 2.4)], h: 4)
        wallX(8, 22, 14, wLib, h: 4)

        wallZ(-10, 2, 12, wGal, h: 4)                                            // Galerie
        wallX(12, 22, -10, wGal, h: 4)
        wallZ(-10, 2, 22, wGal, h: 4)

        wallZ(-14, 0, -3, wCorr, gaps: [(-7.5, 2.2)], h: 3.0)                    // Nordflur
        wallZ(-14, 0, 3, wCorr, gaps: [(-7.5, 2.2), (-12.5, 1.8)], h: 3.0)

        wallZ(-11, -4, -10, wBath, h: 2.7, wainscot: false)                      // Bad
        wallX(-10, -3, -11, wBath, h: 2.7, wainscot: false)
        wallX(-10, -3, -4, wBath, h: 2.7, wainscot: false)

        wallZ(-11, -4, 10, wStore, h: 3.0)                                       // Lager
        wallX(3, 10, -11, wStore, h: 3.0)
        wallX(3, 10, -4, wStore, h: 3.0)

        wallX(-7, 7, -14, wStudy, gaps: [(0, 2.4)], h: 3.6)                      // Arbeitszimmer
        wallZ(-24, -14, -7, wStudy, h: 3.6)
        wallZ(-24, -14, 7, wStudy, h: 3.6)
        wallX(-7, 7, -24, wStudy, h: 3.6)

        // Westfluegel: langer Flur mit Fensterreihe, dahinter der Salon
        wallZ(-22, 14, -31, wCorr, gaps: [(-14, 2.4)], h: 3.4)                   // aussen + Salontuer
        wallZ(-22, 14, -24, wCorr, gaps: [(12, 2.4), (-1.5, 2.2)], h: 3.4)       // innen
        wallX(-31, -24, 14, wCorr, h: 3.4)
        wallX(-31, -24, -22, wCorr, h: 3.4)

        wallZ(-22, -6, -47, wSalon, h: 4.2)                                      // Salon
        wallX(-47, -31, -22, wSalon, h: 4.2)
        wallX(-47, -31, -6, wSalon, h: 4.2)

        // Gang zum Keller und der Keller selbst - roher Beton, niedrig
        wallX(3, 11, -13.4, wCell, gaps: [(9.0, 1.2)], h: 2.6, wainscot: false)
        wallX(3, 11, -11.6, wCell, h: 2.6, wainscot: false)
        wallZ(-23, -11.5, 11, wCell, gaps: [(-12.5, 1.8)], h: 2.6, wainscot: false)
        wallZ(-23, -11.5, 23, wCell, h: 2.6, wainscot: false)
        wallX(11, 23, -23, wCell, h: 2.6, wainscot: false)
        wallX(11, 23, -11.5, wCell, h: 2.6, wainscot: false)

        // ---------- Empfangshalle ----------
        // Der Eingang eines Sanatoriums ist ein Empfang, kein Wohnzimmer. Der
        // Ostteil der alten Halle wird Rezeption, der Westteil mit der Treppe
        // bekommt eine eigene Wand und wird zur Treppenhalle.
        // Tuer vom Empfang direkt in den Treppenvorplatz (z 8.6..10.2)
        wallZ(0, 14, -2, wHall, gaps: [(10.0, 1.8)], h: 6)
        // Nordabschluss des Treppenschachts. Zweiteilig, und das ist wichtig:
        // opening() setzt ueber JEDE Luecke einen Sturz ab doorH = 2.35 m. Die
        // Obergeschossplatte liegt auf 3.80 - mit einer durchgehenden Wand von
        // 0 bis 6 lief man oben durch 3.65 m massiv aussehendes Mauerwerk.
        // Unten also mit Sturz, oben als volle Oeffnung.
        wallX(-8, -2, 6.0, wHall, gaps: [(-4.0, 4.0)], h: 3.8)
        wall(2.0, SCNVector3(-7, 0, 6.0), 0, wHall, h: 2.2, base: 3.8)
        // Die Ostwand des Schachts baut buildStairwell - sie muss ueber dem
        // offenen Schacht hoeher werden als neben dem Bodenband.

        rug(7.5, 6.5, 3.0, 9.5, Tex.rugRed)
        receptionDesk(3.2, 2.6, 5.2)
        // Der Tresor des Hauses - Zahlenschloss, die Kombination liegt
        // irgendwo in den Dokumenten. Mechanik folgt.
        prop(0.72, 0.88, 0.62, 6.9, 0.46, 0.48, texMat(Tex.iron, 1, 1), solid: true)
        cylE(0.085, 0.05, 6.9, 0.60, 0.81, SCNVector3(Float.pi / 2, 0, 0), texMat(Tex.brass, 1, 1))
        cylE(0.022, 0.16, 7.14, 0.52, 0.81, SCNVector3(0, 0, Float.pi / 2), texMat(Tex.brass, 1, 1))
        contactShadow(6.9, 0.48, 1.0, 0.9)
        // (Empfangs- und Baedermoebel stehen jetzt in Furniture.swift)
        // er stand mitten im Nordflur-Durchgang
        // Wartebereich vor dem Tresen
        // Anschlagbrett neben dem Eingang
        prop(1.30, 0.95, 0.07, 6.6, 1.85, 13.82, darkWood)
        prop(1.16, 0.82, 0.02, 6.6, 1.85, 13.76, col(0.30, 0.28, 0.24))
        for k in 0..<5 {
            prop(0.24, 0.30, 0.008, 6.15 + Float(k % 3) * 0.42, 1.98 - Float(k / 3) * 0.34,
                 13.74, col(0.78, 0.75, 0.68))
        }
        chandelier(3.0, 8.5, 4.0, 6, shadow: true)
        cyl(0.40, 6, 6.6, 3, 2.4, stone)
        prop(1.0, 0.30, 1.0, 6.6, 5.85, 2.4, stone)
        prop(1.0, 0.24, 1.0, 6.6, 0.12, 2.4, stone)

        // Haupteingang
        prop(1.7, 3.0, 0.16, 2.1, 1.5, 13.82, texMat(Tex.doors[0], 1, 1.6))
        prop(1.7, 3.0, 0.16, 3.9, 1.5, 13.82, texMat(Tex.doors[0], 1, 1.6))
        prop(3.7, 0.30, 0.24, 3.0, 3.15, 13.80, col(0.46, 0.34, 0.15))
        sph(0.06, 2.84, 1.35, 13.71, brass); sph(0.06, 3.16, 1.35, 13.71, brass)
        stormWindow(0.2, 3.15, 13.86, 1.70, 3.30, 0, -1, 6.2)
        stormWindow(6.2, 3.15, 13.86, 1.70, 3.30, 0, -1, 6.2)
        // Das Tageslicht der Eingangsfenster als breiter kuehler Kegel quer
        // durch die Halle - die Rueckseite traegt jetzt den Raum.
        _ = addSpot(SCNVector3(3.2, 4.7, 13.5), SCNVector3(3.2, 0.4, 4.0), 520,
                    UIColor(red: 0.85, green: 0.87, blue: 0.92, alpha: 1),
                    inner: 30, outer: 75, range: 20)
        picture(1.0, 3.9, -1.80, 1.5, 1.9, true, 1)
        for z in [4.0, 8.0, 12.0] { sconce(7.78, 3.2, Float(z), -1, 0) }
        addOmni(SCNVector3(4, 3.0, 6), 620, UIColor(red: 1.0, green: 0.88, blue: 0.72, alpha: 1), range: 12)
        addDust(3, 2.6, 7, 9, 5.0, 12, 14)

        // ---------- Treppenhaus ----------
        // Beide Geschosse stehen in Stairwell.swift. Der ganze Schacht -
        // Waende, Decken, Bodenbaender, vier Laeufe, zwei Podeste - kommt aus
        // einer Hand, weil die Masse voneinander abhaengen.
        buildStairwell(wHall)
        rug(4.5, 4.0, -5.0, 3.0, Tex.rugGold)
        candelabra(-7.4, 0.96, 5.0, 3)
        picture(-7.78, 3.4, 9.0, 1.3, 1.7, false, 1)
        for z in [2.5, 6.0, 11.0] { sconce(-7.78, 3.0, Float(z), 1, 0, beam: true) }
        addOmni(SCNVector3(-5, 3.4, 5), 480, UIColor(red: 1.0, green: 0.86, blue: 0.66, alpha: 1), range: 11)
        addDust(-5, 2.4, 6, 5, 4.5, 11, 10)

        // ---------- Speisezimmer ----------
        rug(9, 8, -16, 8, Tex.rugGold)
        for z in [5.8, 7.2, 8.6, 10.0] {
            chairAt(-18.2, Float(z), "w", wood); chairAt(-13.8, Float(z), "e", wood)
        }
        chairAt(-16, 4.9, "n", wood); chairAt(-16, 11.1, "s", wood)
        for z in [6.5, 9.5] {
            cyl(0.045, 0.30, -16.3, 0.99, Float(z), col(0.86, 0.83, 0.72))
            sph(0.06, -16.3, 1.20, Float(z), glowMat(1.0, 0.86, 0.55))
            cyl(0.045, 0.30, -15.7, 0.99, Float(z), col(0.86, 0.83, 0.72))
            sph(0.06, -15.7, 1.20, Float(z), glowMat(1.0, 0.86, 0.55))
        }
        candelabra(-16, 0.83, 6.6, 4)
        candelabra(-16, 0.83, 9.4, 4)
        chandelier(-16, 8, 2.9, 4, shadow: true)
        fireplaceX(-23.3, 8, 1)
        picture(-16, 2.6, 13.75, 1.6, 1.1, true, -1)
        picture(-10.5, 2.6, 2.25, 1.2, 1.5, true, 1)
        sconce(-23.6, 2.7, 4.5, 1, 0); sconce(-23.6, 2.7, 11.5, 1, 0)
        addSpot(SCNVector3(-16, 3.6, 8), SCNVector3(-16, 0, 8), 1500,
                UIColor(red: 1.0, green: 0.88, blue: 0.70, alpha: 1), inner: 24, outer: 76, range: 12)
        floorPool(-16, 8, 3.0, 3.0, 0.26, UIColor(red: 1.0, green: 0.84, blue: 0.58, alpha: 1))
        addDust(-16, 2.0, 8, 12, 3.6, 9, 8)

        // ---------- Kueche ----------
        counterRun(-23.5, -17.5, -9.4, 1)
        stoveAt(-16.2, -9.4)
        fridgeAt(-13.2, -9.5)
        sinkAt(-23.4, -6.0)
        // Grosskueche: Haengerack ueber dem Arbeitstisch, Tellerbord, Vorraete
        cylE(0.022, 2.2, -18, 2.30, -3.5, SCNVector3(0, 0, Float.pi/2), texMat(Tex.brass, 1, 1))
        prop(0.03, 0.85, 0.03, -18.9, 2.72, -3.5, texMat(Tex.iron, 1, 1))
        prop(0.03, 0.85, 0.03, -17.1, 2.72, -3.5, texMat(Tex.iron, 1, 1))
        let copper = col(0.58, 0.34, 0.20)
        for k in 0..<5 {
            let hx = -18.0 - 0.88 + Float(k) * 0.44
            prop(0.016, 0.14, 0.016, hx, 2.22, -3.5, texMat(Tex.iron, 1, 1))
            cyl(CGFloat(0.09 + Double(k % 3) * 0.025), CGFloat(0.13 + Double((k + 1) % 3) * 0.03),
                hx, 2.02, -3.5, copper)
        }
        for b in 0..<2 {
            prop(0.30, 0.04, 3.2, -23.72, 1.30 + Float(b) * 0.42, -6.0, darkWood)
        }
        for st in 0..<4 {
            let sz = -7.3 + Float(st) * 0.9
            for p2 in 0..<5 {
                cyl(0.105, 0.016, -23.7, 1.335 + Float(p2) * 0.018, sz, col(0.80, 0.77, 0.70))
            }
            cyl(0.105, 0.016, -23.7, 1.755, sz, col(0.80, 0.77, 0.70))
        }
        let sack = col(0.55, 0.48, 0.38)
        for (sx2, sz2, sh) in [(-23.1, 1.15, Float(0.52)), (-22.6, 1.35, 0.44), (-23.25, 0.55, 0.38)] {
            cyl(0.20, CGFloat(sh), Float(sx2), sh / 2, Float(sz2), sack)
            cyl(0.14, 0.06, Float(sx2), sh + 0.02, Float(sz2), col(0.62, 0.58, 0.50))
        }
        prop(0.26, 0.14, 0.10, -18.5, 0.85, -4.1, darkWood)
        prop(0.42, 0.03, 0.30, -17.6, 0.795, -3.2, texMat(Tex.plankWood, 1, 1))
        chairAt(-18, -1.9, "s", wood); chairAt(-18, -5.1, "n", wood)
        for i in 0..<3 { crateAt(-13.0, 0, Float(-1.5 + Double(i) * 0.05), 0.7, col(0.40, 0.29, 0.16), col(0.28, 0.20, 0.11)) }
        crateAt(-13.0, 0.7, -1.5, 0.55, col(0.40, 0.29, 0.16), col(0.28, 0.20, 0.11))
        prop(5.0, 0.06, 0.34, -20.5, 1.85, -9.5, wood)      // Haengebord
        for i in 0..<6 { cyl(0.10, 0.22, -22.6 + Float(i) * 0.75, 1.98, -9.5, col(0.40, 0.40, 0.38)) }
        addSpot(SCNVector3(-18, 3.0, -6), SCNVector3(-18, 0, -6), 1150,
                UIColor(red: 0.94, green: 0.94, blue: 0.88, alpha: 1), inner: 24, outer: 78, range: 11)
        addOmni(SCNVector3(-20, 2.1, -9), 500, UIColor(red: 0.90, green: 0.92, blue: 0.90, alpha: 1), range: 9)

        // ---------- Bibliothek ----------
        rug(7, 7, 15, 8, Tex.rugBlue)
        bookshelfZ(11.5, 2.6, 5.0, 1, darkWood)
        bookshelfZ(18.0, 2.6, 5.0, 1, darkWood)
        bookshelfZ(15.0, 13.4, 6.0, -1, darkWood)
        prop(0.42, 2.5, 6.0, 21.6, 1.25, 8, darkWood, solid: true)
        for i in 0..<4 {
            let sy = Float(i + 1) * 0.5
            prop(0.34, 0.05, 5.6, 21.5, sy, 8, darkWood)
            var bz: Float = 5.4
            while bz < 10.6 {
                let bw = CGFloat.random(in: 0.05...0.10), bh = CGFloat.random(in: 0.22...0.32)
                prop(0.24, bh, bw, 21.44, sy + Float(bh) / 2 + 0.03, bz,
                     col(CGFloat.random(in: 0.22...0.55), CGFloat.random(in: 0.14...0.32), CGFloat.random(in: 0.12...0.26)))
                bz += Float(bw) + 0.012
            }
        }
        chairAt(15, 9.5, "s", wood)
        cyl(0.05, 0.36, 14.2, 0.97, 8.0, col(0.36, 0.30, 0.13))
        sph(0.10, 14.2, 1.22, 8.0, glowMat(1.0, 0.88, 0.60))
        prop(0.40, 0.06, 0.30, 15.6, 0.87, 8.0, col(0.44, 0.28, 0.18))   // Buch auf dem Tisch
        cyl(0.06, 0.80, 12.6, 0.40, 11.4, wood); sph(0.34, 12.6, 1.06, 11.4, col(0.32, 0.46, 0.38))
        candelabra(15.7, 0.82, 8.0, 3)
        sconce(21.7, 2.9, 5.0, -1, 0); sconce(21.7, 2.9, 11.0, -1, 0)
        addSpot(SCNVector3(15, 3.6, 8), SCNVector3(15, 0, 8), 1450,
                UIColor(red: 1.0, green: 0.88, blue: 0.72, alpha: 1), inner: 24, outer: 76, range: 12)
        floorPool(15, 8, 2.8, 2.8, 0.26, UIColor(red: 1.0, green: 0.84, blue: 0.58, alpha: 1))
        addDust(15, 2.0, 8, 11, 3.6, 9, 7)

        // ---------- Galerie ----------
        for z in [-2.5, -5.0, -7.5] {
            picture(12.25, 2.2, Float(z), 1.4, 1.8, false, 1)
        }
        // Mondlicht faellt durch drei hohe Fenster quer ueber die Galerie
        for z in [-1.2, -4.6, -8.0] {
            stormWindow(21.86, 2.45, Float(z), 1.25, 2.10, -1, 0, 5.4)
        }
        prop(1.6, 0.10, 0.45, 17, 0.46, -5.4, darkWood, solid: true)   // Bank
        for sx in [-1, 1] { prop(0.10, 0.44, 0.10, 17 + 0.66 * Float(sx), 0.22, -5.4, darkWood) }
        rug(5, 6, 17, -4.5, Tex.rugGold)
        for z in [-2.0, -6.5] { sconce(12.3, 2.9, Float(z), 1, 0, beam: true) }
        addDust(17, 1.8, -4.5, 9, 3.4, 10, 11)
        addSpot(SCNVector3(17, 3.6, -4), SCNVector3(17, 0, -4), 950,
                UIColor(red: 0.90, green: 0.92, blue: 0.96, alpha: 1), inner: 22, outer: 78, range: 12)

        // ---------- Nordflur ----------
        rug(2.2, 13, 0, -7, Tex.runner)
        for z in [-2.5, -6.0, -9.5, -12.5] {
            sconce(-2.78, 2.25, Float(z), 1, 0, beam: true)
            sconce(2.78, 2.25, Float(z), -1, 0, beam: true)
        }
        stormWindow(-2.86, 2.00, -1.8, 1.05, 1.70, 1, 0, 4.3)
        picture(2.72, 1.9, -4.2, 0.9, 1.2, false, -1)
        picture(-2.72, 1.9, -11.0, 0.9, 1.2, false, 1)
        addOmni(SCNVector3(0, 2.6, -3.0), 620, UIColor(red: 1.0, green: 0.88, blue: 0.68, alpha: 1), range: 9)
        addOmni(SCNVector3(0, 2.6, -7.5), 620, UIColor(red: 1.0, green: 0.88, blue: 0.68, alpha: 1), range: 9)
        addOmni(SCNVector3(0, 2.6, -12.0), 620, UIColor(red: 1.0, green: 0.88, blue: 0.68, alpha: 1), range: 9)

        // ---------- Bad ----------
        sinkAt(-5.0, -10.55)
        mirrorAt(-5.0, 1.62, -10.80, 0.80, 1.00, 1)
        toiletAt(-4.2, -5.0)
        // Handtuchstange an der Suedwand
        cyl(0.020, 1.10, -7.0, 1.42, -4.20, texMat(Tex.brass, 1, 1))
        prop(0.02, 0.10, 0.10, -7.55, 1.42, -4.20, texMat(Tex.brass, 1, 1))
        prop(0.02, 0.10, 0.10, -6.45, 1.42, -4.20, texMat(Tex.brass, 1, 1))
        prop(0.50, 0.80, 0.05, -7.0, 1.00, -4.24, col(0.62, 0.60, 0.54))
        prop(0.44, 0.72, 0.05, -6.55, 1.04, -4.24, col(0.56, 0.54, 0.48))
        // Hocker und Bodenablauf
        for sx in [-1, 1] { for sz in [-1, 1] {
            prop(0.06, 0.44, 0.06, -6.5 + 0.15 * Float(sx), 0.22, -6.2 + 0.15 * Float(sz),
                 texMat(Tex.plankWood, 1, 1))
        }}
        cyl(0.11, 0.02, -6.4, 0.02, -8.6, texMat(Tex.iron, 1, 1))
        // Zweite Wanne: eine Baederabteilung hat nie nur eine
        // Behandlungsliege mit Wachstuchbezug
        prop(0.72, 0.16, 1.90, -5.0, 0.68, -7.6, texMat(Tex.leather, 2, 1), solid: true)
        prop(0.62, 0.10, 0.44, -5.0, 0.80, -8.35, texMat(Tex.leather, 1, 1))
        for sx in [-1, 1] { for sz in [-1, 1] {
            prop(0.05, 0.60, 0.05, -5.0 + 0.28 * Float(sx), 0.30, -7.6 + 0.82 * Float(sz),
                 texMat(Tex.iron, 1, 1))
        }}
        prop(0.62, 0.04, 1.70, -5.0, 0.40, -7.6, texMat(Tex.iron, 2, 1))
        // Instrumentenwagen
        prop(0.50, 0.04, 0.36, -6.6, 0.86, -9.6, texMat(Tex.iron, 1, 1), solid: true)
        prop(0.50, 0.04, 0.36, -6.6, 0.48, -9.6, texMat(Tex.iron, 1, 1))
        for sx in [-1, 1] { for sz in [-1, 1] {
            prop(0.035, 0.84, 0.035, -6.6 + 0.21 * Float(sx), 0.42, -9.6 + 0.14 * Float(sz),
                 texMat(Tex.iron, 1, 1))
        }}
        for k in 0..<4 {
            prop(0.05, 0.03, 0.16, -6.78 + Float(k) * 0.10, 0.90, -9.6, texMat(Tex.brass, 1, 1))
        }
        // Wandschraenkchen und ein vergessener Eimer
        prop(0.55, 0.70, 0.26, -9.72, 1.55, -5.6, texMat(Tex.wainscot, 1, 1))
        prop(0.05, 0.60, 0.20, -9.58, 1.55, -5.6, artMat(Tex.mirror))
        cyl(0.17, 0.30, -9.4, 0.15, -9.8, texMat(Tex.iron, 1, 1))
        sconce(-3.20, 1.95, -9.6, -1, 0)
        sconce(-3.20, 1.95, -5.4, -1, 0)
        addOmni(SCNVector3(-6.5, 2.4, -7.5), 950, UIColor(red: 0.86, green: 0.93, blue: 0.92, alpha: 1), range: 11)

        // ---------- Lager ----------
        // Apotheke: Rezepturtisch, Flaschenregale, Apothekerwaage
        prop(0.30, 0.22, 0.20, 6.9, 0.98, -6.2, texMat(Tex.brass, 1, 1))     // Waagenfuss
        prop(0.60, 0.025, 0.05, 6.9, 1.12, -6.2, texMat(Tex.brass, 1, 1))    // Balken
        for sx in [-1, 1] {
            cyl(0.10, 0.02, 6.9 + 0.28 * Float(sx), 1.05, -6.2, texMat(Tex.brass, 1, 1))
            prop(0.008, 0.09, 0.008, 6.9 + 0.28 * Float(sx), 1.08, -6.2, texMat(Tex.brass, 1, 1))
        }
        prop(0.34, 0.05, 0.26, 5.8, 0.90, -6.0, col(0.80, 0.78, 0.70))       // Rezeptblock
        // Flaschenregal an der Nordwand
        prop(6.2, 2.10, 0.34, 6.5, 1.05, -10.75, darkWood, solid: true)
        for r in 0..<5 {
            let ry = 0.32 + Float(r) * 0.42
            prop(6.0, 0.045, 0.30, 6.5, ry, -10.72, darkWood)
            var bx: Float = 3.7
            while bx < 9.5 {
                let bh = CGFloat.random(in: 0.14...0.28)
                let tone = CGFloat.random(in: 0.18...0.42)
                cyl(CGFloat.random(in: 0.030...0.052), bh, bx, ry + Float(bh)/2 + 0.02, -10.68,
                    col(tone, tone * 1.5, tone * 0.9))
                bx += Float.random(in: 0.11...0.19)
            }
        }
        let crateM = col(0.40, 0.29, 0.16), crateT = col(0.28, 0.20, 0.11)
        crateAt(4.6, 0.9, -9.6, 0.7, crateM, crateT)
        crateAt(8.8, 1.0, -5.4, 0.75, crateM, crateT)
        prop(0.45, 2.2, 5.6, 9.6, 1.1, -7.5, darkWood, solid: true)
        for i in 0..<3 {
            prop(0.40, 0.06, 5.4, 9.55, Float(i) * 0.65 + 0.5, -7.5, darkWood)
            for j in 0..<5 {
                prop(0.30, 0.30, 0.36, 9.5, Float(i) * 0.65 + 0.68, -9.6 + Float(j) * 1.05,
                     col(CGFloat.random(in: 0.30...0.46), CGFloat.random(in: 0.24...0.34), CGFloat.random(in: 0.16...0.24)))
            }
        }
        sconce(3.3, 2.15, -7.5, 1, 0)
        addOmni(SCNVector3(6.5, 2.6, -7.5), 800, UIColor(red: 1.0, green: 0.86, blue: 0.64, alpha: 1), range: 11)

        // ---------- Arbeitszimmer ----------
        rug(8, 6, -1, -19.5, Tex.rugBlue)
        chairAt(-4.5, -20.0, "s", wood)
        prop(0.42, 0.03, 0.58, -5.4, 0.86, -21.7, col(0.86, 0.84, 0.76))
        prop(0.30, 0.05, 0.24, -3.9, 0.87, -21.4, col(0.44, 0.28, 0.18))
        cyl(0.05, 0.42, -3.4, 1.01, -22.0, col(0.36, 0.30, 0.13))
        sph(0.09, -3.4, 1.28, -22.0, glowMat(1.0, 0.88, 0.60))
        bookshelfZ(3.5, -23.4, 4.5, -1, darkWood)
        fireplaceX(6.3, -19, -1)
        grandClock(-6.2, -22.6)
        // Vorhaenge neben dem Fenster
        prop(0.10, 2.9, 0.80, -6.72, 1.55, -19.9, texMat(Tex.curtain, 1, 2))
        prop(0.10, 2.9, 0.80, -6.72, 1.55, -17.1, texMat(Tex.curtain, 1, 2))
        prop(0.14, 0.16, 3.2, -6.70, 3.10, -18.5, texMat(Tex.brass, 1, 1))
        // Fenster mit Nachthimmel
        prop(2.6, 2.0, 0.08, -6.85, 2.4, -18.5, windowMat())
        prop(0.12, 2.2, 0.16, -6.80, 2.4, -19.6, darkWood)
        prop(0.12, 2.2, 0.16, -6.80, 2.4, -17.4, darkWood)
        prop(0.12, 0.16, 2.3, -6.80, 3.45, -18.5, darkWood)
        prop(0.12, 0.16, 2.3, -6.80, 1.35, -18.5, darkWood)
        sconce(6.7, 2.8, -22.0, -1, 0); sconce(-6.7, 2.8, -22.0, 1, 0)
        addSpot(SCNVector3(-2, 3.3, -19), SCNVector3(-2, 0, -19), 1250,
                UIColor(red: 1.0, green: 0.90, blue: 0.72, alpha: 1), inner: 24, outer: 74, range: 11)
        floorPool(-2, -19, 2.4, 2.4, 0.24, UIColor(red: 1.0, green: 0.84, blue: 0.58, alpha: 1))
        addDust(-1, 1.8, -19, 11, 3.2, 8, 6)
        addOmni(SCNVector3(-6.4, 2.6, -18.5), 380, UIColor(red: 0.52, green: 0.62, blue: 0.95, alpha: 1), range: 8)

        // ---------- Gang zum Keller ----------
        let rustM = texMat(Tex.rust, 1, 1)
        let ironM = texMat(Tex.iron, 1, 1)
        pipeX(3.2, 10.8, 2.28, -12.0, 0.075, rustM)
        pipeX(3.2, 10.8, 2.08, -13.1, 0.055, rustM)
        puddle(6.0, -12.6, 2.2, 1.2)
        bulb(7.0, -12.5, 2.6, 0.45, 330)

        // ---------- Keller ----------
        // Nasser Beton, Rost, viele Leitungen. Der unangenehmste Ort im Haus.
        // Rohrbuendel unter der Decke, quer durch den ganzen Raum
        // Typ ausgeschrieben: als blankes Literal mit sechs Umwandlungen muss
        // der Typpruefer alle Zahlentypkombinationen durchgehen. Genau daran
        // ist die Schlaefer-Liste in Game.swift abgebrochen.
        let rohre: [(Float, CGFloat)] = [(2.30, 0.10), (2.30, 0.07), (2.06, 0.085)]
        for (yy, rr) in rohre {
            pipeX(11.3, 22.7, yy, -13.0, rr, rustM)
        }
        pipeX(11.3, 22.7, 2.24, -16.2, 0.12, rustM)
        pipeX(11.3, 22.7, 2.02, -16.8, 0.06, rustM)
        pipeZ(-22.6, -11.8, 2.18, 13.4, 0.09, rustM)
        pipeZ(-22.6, -11.8, 2.34, 20.6, 0.075, rustM)
        // Fallstraenge an den Waenden
        let straenge: [(Float, Float)] = [(11.5, -14.5), (22.5, -19.0),
                                          (11.5, -21.0), (16.0, -22.7)]
        for (px, pz) in straenge {
            pipeY(0.15, 2.30, px, pz, 0.085, rustM)
            valve(px, 1.25, pz, ironM)
        }
        // Bogen aus dem Buendel nach unten
        sph(0.13, 13.4, 2.18, -19.4, rustM)
        pipeY(0.2, 2.18, 13.4, -19.4, 0.09, rustM)
        // Kessel
        cyl(0.80, 1.90, 21.0, 0.95, -21.3, rustM)
        sph(0.80, 21.0, 1.90, -21.3, rustM)
        cyl(0.92, 0.16, 21.0, 0.08, -21.3, ironM)
        prop(0.72, 0.72, 0.10, 21.0, 0.85, -20.45, ironM)
        cyl(0.10, 0.10, 21.22, 0.85, -20.38, texMat(Tex.brass, 1, 1))
        prop(0.30, 0.30, 0.06, 20.70, 1.55, -20.46, texMat(Tex.mirror, 1, 1))   // Manometer
        pipeY(1.90, 2.40, 21.0, -21.3, 0.10, rustM)
        pipeX(13.4, 21.0, 2.40, -21.3, 0.10, rustM)
        blocker(20.1, 21.9, -22.2, -20.4)
        // Regal mit Gerümpel
        prop(0.45, 2.10, 3.20, 22.55, 1.05, -15.5, ironM, solid: true)
        for k in 0..<3 {
            prop(0.42, 0.05, 3.10, 22.50, 0.45 + Float(k) * 0.62, -15.5, ironM)
            for q in 0..<3 {
                prop(0.34, 0.34, 0.42, 22.46, 0.65 + Float(k) * 0.62, -16.6 + Float(q) * 1.1,
                     col(0.34 + CGFloat(q) * 0.06, 0.26, 0.18))
            }
        }
        // Kisten und Faesser
        crateAt(12.6, 0, -21.6, 0.95, col(0.36, 0.26, 0.15), col(0.24, 0.17, 0.10))
        crateAt(12.7, 0.95, -21.6, 0.70, col(0.36, 0.26, 0.15), col(0.24, 0.17, 0.10))
        barrelAt(14.2, -12.9); barrelAt(15.1, -12.6)
        barrelAt(19.4, -12.8)
        // Wasser auf dem Boden
        puddle(15.0, -16.0, 4.6, 3.0)
        puddle(19.6, -20.4, 3.4, 2.6)
        puddle(13.2, -19.2, 2.0, 2.4)
        cyl(0.13, 0.02, 15.0, 0.02, -16.0, ironM)
        cyl(0.13, 0.02, 19.6, 0.02, -20.4, ironM)
        // Bodenrinne
        prop(11.6, 0.03, 0.30, 17.0, 0.012, -17.6, ironM)
        // Ketten von der Decke
        for (cx2, cz2) in [(Float(18.4), Float(-14.2)), (Float(16.2), Float(-20.8))] {
            for k in 0..<6 {
                cyl(0.022, 0.10, cx2, 2.52 - Float(k) * 0.11, cz2, ironM)
            }
        }
        // Licht: zwei nackte Birnen, kaltes Grundlicht
        bulb(15.0, -14.6, 2.6, 0.50, 620)
        bulb(19.8, -20.0, 2.6, 0.50, 520)
        addOmni(SCNVector3(17, 2.2, -17.5), 300, UIColor(red: 0.60, green: 0.74, blue: 0.70, alpha: 1), range: 14)
        let bulbCol = UIColor(red: 1.0, green: 0.86, blue: 0.62, alpha: 1)
        lightShaft(SCNVector3(15.0, 2.05, -14.6), SCNVector3(15.0, 0.05, -14.6), 1.5, 0.26, bulbCol)
        lightShaft(SCNVector3(19.8, 2.05, -20.0), SCNVector3(19.8, 0.05, -20.0), 1.5, 0.24, bulbCol)
        floorPool(15.0, -14.6, 2.0, 2.0, 0.30, bulbCol)
        floorPool(19.8, -20.0, 1.9, 1.9, 0.28, bulbCol)
        addDust(17, 1.3, -17.2, 11, 2.4, 11, 16)

        // Deckengesimse. Ohne den Uebergang Wand/Decke bleibt jeder Raum ein Quader.
        let stucco = texMat(Tex.plaster, 2, 1)
        cornice(-8, 8, 0, 14, 6.0, stucco)          // Haupthalle
        cornice(-24, -8, 2, 14, 4.0, stucco)        // Speisezimmer
        cornice(8, 22, 2, 14, 4.0, stucco)          // Bibliothek
        cornice(12, 22, -10, 2, 4.0, stucco)        // Galerie
        cornice(-47, -31, -22, -6, 4.2, stucco)     // Salon
        cornice(-31, -24, -22, 14, 3.4, stucco)     // Westflur
        cornice(-3, 3, -14, 0, 3.0, stucco)         // Nordflur
        cornice(-7, 7, -24, -14, 3.6, stucco)       // Arbeitszimmer

        // ---------- Westflur ----------
        // 36 m lang, Fensterreihe nach Westen. Das Mondlicht wandert als Kette
        // heller Flecken den Flur entlang - genau der Blick aus den Vorlagen.
        let corrWood = texMat(Tex.wainscot, 2, 1)
        rug(2.4, 34, -27.5, -4, Tex.runner)
        for k in 0..<6 {
            let wz = 12.0 - Float(k) * 3.0
            // Wand steht bei x=-31 und ist 0.30 dick, Innenkante also -30.85.
            // Die Scheibe sass 1 cm davor und verschwand hinter Rahmen und
            // Gardine. Jetzt 7 cm im Raum und breiter als die Gardinenluecke.
            stormWindow(-30.78, 1.85, wz, 1.55, 2.40, 1, 0, 5.0)
            sheerCurtain(-30.50, wz, 2.60, 2.70, true, 0.30, 1)
            radiatorAt(-30.55, wz, 1.40, true)
            if k % 2 == 1 { benchAt(-24.55, wz - 1.5, 1.70, true, corrWood) }
        }
        // Keine Pendelleuchten mehr im Westflur. Das Mondlicht aus der
        // Fensterreihe traegt den Gang allein, die Laternen haben es erschlagen.
        // Nur ganz am Nordende eine, damit der Ausgang lesbar bleibt.
        pendantLamp(-27.5, -19.5, 3.4, 0.55, 300, shadow: true)
        // Nasser Boden, wie im Vorbild
        puddle(-27.8, 3.2, 2.6, 2.0)
        puddle(-26.9, -8.6, 2.2, 1.7)
        puddle(-28.4, -17.0, 2.4, 2.2)
        // Gerümpel an der Innenwand
        benchAt(-24.55, -12.0, 1.70, true, corrWood)
        cabinetAt(-24.9, -18.5, 1.30, 0.52, corrWood, texMat(Tex.brass, 1, 1))
        picture(-24.35, 1.95, -6.0, 1.00, 1.30, false, -1)
        picture(-24.35, 1.95, -15.5, 1.00, 1.30, false, -1)
        grandClock(-24.85, -21.0)
        addDust(-27.5, 1.7, -4, 6, 3.2, 34, 22)
        addOmni(SCNVector3(-27.5, 2.2, -20.5), 420, UIColor(red: 0.80, green: 0.83, blue: 0.88, alpha: 1), range: 10)

        // ---------- Salon ----------
        rug(11, 10, -39, -14, Tex.rugGold)
        pianoAt(-42.5, -17.5)
        sofaAt(-36.0, -11.0, 2.4, 1, fabricRd, darkWood)
        armchairAt(-37.5, -18.5, -1, fabricGn, darkWood)
        tableAt(-36.0, -14.4, 1.30, 0.85, 0.50, wood, darkWood)
        candelabra(-36.0, 0.54, -14.4, 3)
        fireplaceX(-46.3, -14.0, 1)
        cabinetAt(-39.0, -6.6, 2.20, 0.58, darkWood, texMat(Tex.brass, 1, 1))
        picture(-39.0, 2.55, -6.35, 1.70, 1.20, true, -1)
        picture(-33.5, 2.40, -21.75, 1.30, 1.60, true, 1)
        stormWindow(-39.0, 2.30, -21.86, 1.50, 2.30, 0, 1, 5.6)
        sheerCurtain(-39.0, -21.55, 3.30, 2.80, false, 0.28, 1)
        radiatorAt(-39.0, -21.55, 1.60, false)
        chandelier(-39, -14, 3.0, 4.2, shadow: true)
        for z in [-9.5, -18.5] { sconce(-46.72, 2.35, Float(z), 1, 0, beam: true) }
        addDust(-39, 2.0, -14, 14, 4.0, 14, 18)

        // ---------- Tuerblaetter ----------
        // Die Oeffnungen hatten bisher nur Zargen. Jetzt haengen Blaetter darin,
        // teils angelehnt - das gibt dem Grundriss erst Tiefe.
        doorLeaf(0, 0, 2.4, 2.30, false, 1, "Tuer", open: true)                 // Halle -> Nordflur
        doorLeaf(-8, 3.5, 2.4, 2.30, true, -1, "Tuer", open: true)              // Halle -> Speisezimmer
        doorLeaf(8, 8, 2.4, 2.30, true, 1, "Tuer", open: true)                  // Halle -> Bibliothek
        doorLeaf(-24, 12, 2.4, 2.30, true, 1, "Tuer")                           // Speisezimmer -> Westflur
        doorLeaf(-18, 2, 2.4, 2.30, false, -1, "Kuechentuer")                   // Speisezimmer -> Kueche
        doorLeaf(-24, -1.5, 2.2, 2.30, true, -1, "Tuer", open: true)            // Kueche -> Westflur
        doorLeaf(17, 2, 2.4, 2.30, false, 1, "Tuer", open: true)                // Bibliothek -> Galerie
        doorLeaf(-3, -7.5, 2.2, 2.25, true, 1, "Badtuer", open: true, style: 1, swing: 1)           // Nordflur -> Bad
        doorLeaf(3, -7.5, 2.2, 2.25, true, -1, "Lagertuer", style: 1, swing: 1)                     // Nordflur -> Lager
        doorLeaf(3, -12.5, 1.8, 2.20, true, 1, "Tuer", open: true, style: 2, swing: 1)              // Nordflur -> Kellergang
        doorLeaf(0, -14, 2.4, 2.30, false, -1, "Tuer zum Arbeitszimmer",
                 lock: .brassKey)                                               // Nordflur -> Arbeitszimmer
        doorLeaf(-31, -14, 2.4, 2.30, true, 1, "Salontuer",
                 lock: .rustyKey)                                               // Westflur -> Salon
        doorLeaf(11, -12.5, 1.8, 2.20, true, -1, "Kellertuer", boarded: true, style: 2)   // Kellergang -> Keller
        _ = doorLeaf(9, -13.4, 1.15, 2.1, false, 1, "Heizungsraum", style: 3, swing: 1)
        _ = doorLeaf(9, -18, 1.1, 2.05, false, -1, "Kohlenkeller", style: 3, swing: 1)

        // ---------- Gegenstaende ----------
        // Kette: Kueche -> Salon -> Arbeitszimmer, und Lager -> Keller.
        let steel = col(0.42, 0.42, 0.44)
        addPickup(.rustyKey, -18.0, 0.90, -3.5) { h in
            let g = SCNBox(width: 0.03, height: 0.015, length: 0.14, chamferRadius: 0.004)
            g.firstMaterial = texMat(Tex.rust, 1, 1)
            h.addChildNode(SCNNode(geometry: g))
            let r = SCNTorus(ringRadius: 0.035, pipeRadius: 0.009)
            r.firstMaterial = texMat(Tex.rust, 1, 1)
            let rn = SCNNode(geometry: r); rn.position = SCNVector3(0, 0, -0.09)
            h.addChildNode(rn)
        }
        addPickup(.crowbar, 4.4, 0.95, -9.6) { h in
            let g = SCNBox(width: 0.045, height: 0.045, length: 0.86, chamferRadius: 0.012)
            g.firstMaterial = texMat(Tex.iron, 1, 2)
            h.addChildNode(SCNNode(geometry: g))
            let c = SCNBox(width: 0.045, height: 0.11, length: 0.16, chamferRadius: 0.02)
            c.firstMaterial = texMat(Tex.iron, 1, 1)
            let cn = SCNNode(geometry: c)
            cn.position = SCNVector3(0, 0.05, 0.44); cn.eulerAngles.x = 0.55
            h.addChildNode(cn)
        }
        addPickup(.brassKey, -42.5, 1.42, -16.6) { h in
            let g = SCNBox(width: 0.028, height: 0.012, length: 0.12, chamferRadius: 0.003)
            g.firstMaterial = texMat(Tex.brass, 1, 1)
            h.addChildNode(SCNNode(geometry: g))
            let r = SCNTorus(ringRadius: 0.032, pipeRadius: 0.008)
            r.firstMaterial = texMat(Tex.brass, 1, 1)
            let rn = SCNNode(geometry: r); rn.position = SCNVector3(0, 0, -0.08)
            h.addChildNode(rn)
        }
        addPickup(.lighter, 15.6, 0.88, 8.0) { h in
            let g = SCNBox(width: 0.045, height: 0.075, length: 0.022, chamferRadius: 0.008)
            g.firstMaterial = steel
            h.addChildNode(SCNNode(geometry: g))
        }
        addPickup(.note, -3.6, 0.88, -21.7) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = 0.3
            h.addChildNode(n)
        }
        // Die Geschichte des Hauses, ueber vier Fundstellen verteilt
        addPickup(.gaestebuch, 2.45, 1.145, 2.85) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = 0.5
            h.addChildNode(n)
        }
        addPickup(.kurplan, -6.6, 0.90, -9.55) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = -0.4
            h.addChildNode(n)
        }
        addPickup(.brief, -4.9, 0.86, -21.4) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = 0.9
            h.addChildNode(n)
        }
        addPickup(.wartung, 14.3, 0.03, -20.6) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = 1.7
            h.addChildNode(n)
        }
        // Die Laterne: das wichtigste Fundstueck, gleich in der Halle
        addPickup(.lantern, 4.4, 1.16, 3.4) { h in
            let br = texMat(Tex.brass, 1, 1)
            let body = SCNCylinder(radius: 0.075, height: 0.16)
            body.radialSegmentCount = 8
            let glassM = SCNMaterial()
            glassM.lightingModel = .constant
            glassM.diffuse.contents = UIColor(red: 1.0, green: 0.85, blue: 0.55, alpha: 1)
            glassM.emission.contents = UIColor(red: 1.0, green: 0.80, blue: 0.45, alpha: 1)
            glassM.emission.intensity = 1.15
            body.firstMaterial = glassM
            let bn = SCNNode(geometry: body)
            bn.position = SCNVector3(0, 0.02, 0)
            h.addChildNode(bn)
            for yy in [Float(-0.08), 0.10] {
                let cap = SCNCylinder(radius: 0.085, height: 0.028)
                cap.radialSegmentCount = 8; cap.firstMaterial = br
                let cn = SCNNode(geometry: cap)
                cn.position = SCNVector3(0, yy, 0)
                h.addChildNode(cn)
            }
            let hoop = SCNTorus(ringRadius: 0.05, pipeRadius: 0.008)
            hoop.ringSegmentCount = 10; hoop.pipeSegmentCount = 4; hoop.firstMaterial = br
            let hn = SCNNode(geometry: hoop)
            hn.position = SCNVector3(0, 0.16, 0)
            hn.eulerAngles.z = Float.pi / 2
            h.addChildNode(hn)
        }
        addPickup(.heizer, 7.8, 0.63, -18.8) { h in
            let g = SCNBox(width: 0.16, height: 0.004, length: 0.22, chamferRadius: 0.001)
            g.firstMaterial = col(0.82, 0.79, 0.70)
            let n = SCNNode(geometry: g); n.eulerAngles.y = -0.7
            h.addChildNode(n)
        }

        // ===================== Erster Stock =====================
        // Patientenzimmer am Mittelflur. Sechs fast gleiche Zimmer sind in einem
        // Sanatorium keine Sparmassnahme, sondern der Normalfall.
        let F: Float = 3.8                       // Fussbodenhoehe
        let wArd = texMat(Tex.wpBeige, 5, 1.4)   // Flur oben
        let wZim = texMat(Tex.wpGreen, 4, 1.4)   // Zimmer
        let oakF = texMat(Tex.parquet, 2, 2)
        let linoF = texMat(Tex.woodFloor, 2, 2)

        // Galerie und Flur Ost. Der Treppenschacht x[-8,-4] z[6,14] bleibt
        // ausgespart - sein Bodenband baut buildStairwell, weil die Kante
        // genau am Austritt des oberen Laufs liegen muss.
        floorTile(6.0, 5.5, -5.0, 3.25, oakF, y: F)      // Galerie  x[-8,-2] z[0.5,6]
        floorTile(2.0, 8.0, -3.0, 10.0, oakF, y: F)      // Flur Ost x[-4,-2] z[6,14]
        // Verbindungsstueck Galerie <-> Stationsflur. Genau in die Luecke
        // gelegt: vorher ragte es 1.0 m in die Galerie und 0.5 m in den Flur,
        // beides auf y 3.80 - zwei Boeden auf gleicher Hoehe flimmern.
        floorTile(5.0, 1.5, 0.5, 0.75, oakF, y: F)
        // (Die zweite Decke auf F + 2.2 = 6.0 ist entfallen - sie lag deckungs-
        //  gleich auf der Hallendecke und erzeugte Z-Fighting.)
        // Bruestung zur Halle hin
        let balRail = texMat(Tex.plankWood, 2, 1)
        prop(0.10, 1.05, 11.5, -2.0, F + 0.52, 6.25, balRail)
        solids.append(WallBox(x0: -2.1, x1: -1.9, z0: 0.5, z1: 12.0, y0: F, y1: F + 1.2))
        // Treppenhalle als Flur: Laeufer, Konsole mit Spiegel - und unten die
        // verschlossene Eisentuer zur Anstalt. Den Schluessel gibt es noch
        // nirgends; die Tuer ist ein Versprechen an den Keller-Ausbau.
        rug(2.2, 7.6, -5.0, 4.4, Tex.runner)              // Laeufer nur im Flurteil
        tableAt(-5.0, 0.85, 1.5, 0.5, 0.85, wood, darkWood)
        mirrorAt(-5.0, 1.95, 0.42, 0.75, 0.95, 1)
        _ = doorLeaf(-5.5, 0, 1.3, 2.2, false, 1, "Zur Anstalt", lock: .asylumKey, style: 3)

        // (Die frühere Quer-Bruestung ist entfallen - die Ankunft von Lauf B
        //  liegt jetzt bei z=6.2 und ist durch das Schachtgelaender gesichert.)
        for z in [2.0, 5.0, 8.0, 11.0] {
            prop(0.09, 0.95, 0.09, -2.0, F + 0.48, Float(z), balRail)
        }

        // Mittelflur
        floorTile(6, 20, 0, -10, linoF, y: F)
        ceiling(6, 20, 0, -10, F + 2.6)
        wallZ(-20, 0.5, -3, wArd, gaps: [(-3.5, 1.15), (-10.5, 1.15), (-17.5, 1.15)], h: 2.6, base: F)
        wallZ(-20, 0.5, 3, wArd, gaps: [(-3.5, 1.15), (-10.5, 1.15), (-17.5, 1.15)], h: 2.6, base: F)
        wallX(-3, 3, -20, wArd, gaps: [(0.0, 1.2)], h: 2.6, base: F)

        // Vier Patientenzimmer
        let rooms1: [(Float, Float, Float, Float, Float)] = [
            (-11, -3, -6, -1, -3.5), (3, 11, -6, -1, -3.5),
            (-11, -3, -13, -8, -10.5), (3, 11, -13, -8, -10.5),
        ]
        for (rx0, rx1, rz0, rz1, _) in rooms1 {
            floorTile(CGFloat(rx1 - rx0), CGFloat(rz1 - rz0), (rx0 + rx1)/2, (rz0 + rz1)/2, linoF, y: F)
            ceiling(CGFloat(rx1 - rx0), CGFloat(rz1 - rz0), (rx0 + rx1)/2, (rz0 + rz1)/2, F + 2.6)
            wallX(rx0, rx1, rz0, wZim, h: 2.6, base: F)
            wallX(rx0, rx1, rz1, wZim, h: 2.6, base: F)
            wallZ(rz0, rz1, rx0 < 0 ? rx0 : rx1, wZim, h: 2.6, base: F)
            // Einrichtung: Bett, Nachttisch, Stuhl, Fenster
            let bx = rx0 < 0 ? rx0 + 1.4 : rx1 - 1.4
            let bz = (rz0 + rz1) / 2
            prop(1.05, 0.30, 2.10, bx, F + 0.42, bz, texMat(Tex.iron, 1, 1), solid: true)
            prop(1.00, 0.16, 2.00, bx, F + 0.62, bz, col(0.62, 0.60, 0.55))
            prop(1.00, 0.10, 0.55, bx, F + 0.72, bz - 0.72, col(0.72, 0.70, 0.64))
            prop(1.10, 0.75, 0.08, bx, F + 0.75, bz + 1.06, texMat(Tex.iron, 1, 1))
            prop(1.10, 0.95, 0.08, bx, F + 0.85, bz - 1.06, texMat(Tex.iron, 1, 1))
            cabinetAt(bx + (rx0 < 0 ? 1.3 : -1.3), bz - 0.9, 0.55, 0.45, darkWood, texMat(Tex.brass, 1, 1))
            chairAt(bx + (rx0 < 0 ? 1.5 : -1.5), bz + 1.0, rx0 < 0 ? "w" : "e", wood)
            let wxx: Float = rx0 < 0 ? rx0 + 0.14 : rx1 - 0.14
            stormWindow(wxx, F + 1.5, bz, 1.15, 1.55, rx0 < 0 ? 1 : -1, 0, 3.4)
            sconce(rx0 < 0 ? rx1 - 0.22 : rx0 + 0.22, F + 1.9, bz + 1.4, rx0 < 0 ? -1 : 1, 0)
            addOmni(SCNVector3((rx0+rx1)/2, F + 2.0, bz), 300,
                    UIColor(red: 0.94, green: 0.90, blue: 0.82, alpha: 1), range: 7)
        }
        // Flurbeleuchtung oben
        for z in [-2.5, -8.0, -14.0, -18.5] {
            pendantLamp(0, Float(z), F + 2.6, 0.45, 260, shadow: z == -8.0)
        }
        addDust(0, F + 1.4, -10, 5, 2.4, 18, 10)

        // Schwesternzimmer (Westseite) - von hier wurde die Station gefuehrt
        floorTile(8, 5, -7, -17.5, linoF, y: F)
        ceiling(8, 5, -7, -17.5, F + 2.6)
        wallX(-11, -3, -20, wZim, h: 2.6, base: F)
        wallX(-11, -3, -15, wZim, h: 2.6, base: F)
        wallZ(-20, -15, -11, wZim, h: 2.6, base: F)
        prop(1.05, 0.30, 2.05, -4.2, F + 0.42, -18.6, texMat(Tex.iron, 1, 1), solid: true)
        prop(1.00, 0.14, 1.95, -4.2, F + 0.62, -18.6, col(0.62, 0.60, 0.55))
        picture(-10.82, F + 1.7, -17.5, 0.9, 1.1, false, 1)
        sconce(-6.9, F + 1.9, -15.22, 0, 1)
        addOmni(SCNVector3(-7, F + 2.0, -17.5), 300,
                UIColor(red: 0.95, green: 0.90, blue: 0.80, alpha: 1), range: 6)
        contactShadow(-4.2, -18.6, 1.3, 2.3, y: F + 0.012)
        // Der Badehausschluessel liegt bei der Schwester - wer hinauf will,
        // muss erst durch die Station.
        addPickup(.bathKey, -8.5, F + 0.86, -18.4) { h in
            let g = SCNBox(width: 0.03, height: 0.015, length: 0.14, chamferRadius: 0.004)
            g.firstMaterial = texMat(Tex.brass, 1, 1)
            h.addChildNode(SCNNode(geometry: g))
            let r = SCNTorus(ringRadius: 0.035, pipeRadius: 0.009)
            r.firstMaterial = texMat(Tex.brass, 1, 1)
            let rn = SCNNode(geometry: r); rn.position = SCNVector3(0, 0, -0.09)
            h.addChildNode(rn)
        }

        // Waschraum (Ostseite): drei Becken in Reihe, Abfluss in der Mitte
        floorTile(8, 5, 7, -17.5, texMat(Tex.tileGreen, 4, 3), y: F)
        ceiling(8, 5, 7, -17.5, F + 2.6)
        wallX(3, 11, -20, wZim, h: 2.6, base: F)
        wallX(3, 11, -15, wZim, h: 2.6, base: F)
        wallZ(-20, -15, 11, wZim, h: 2.6, base: F)
        for k in 0..<3 {
            let sxp = 5.4 + Float(k) * 2.0
            sinkAt(sxp, -19.4, base: F)
            mirrorAt(sxp, F + 1.75, -19.80, 0.55, 0.75, 1)
        }
        cyl(0.09, 0.02, 7, F + 0.015, -17.2, texMat(Tex.iron, 1, 1))
        waterSurface(7.2, F + 0.012, -17.0, 1.6, 1.2,
                     tint: UIColor(red: 0.30, green: 0.30, blue: 0.28, alpha: 1),
                     murk: 0.7, rep: 1.2, flow: 0.010)
        addOmni(SCNVector3(7, F + 2.0, -17.5), 260,
                UIColor(red: 0.82, green: 0.88, blue: 0.90, alpha: 1), range: 6)

        // ================= Glasgeschoss: Badehaus =================
        // Ganz oben, ueber dem Patientenfluegel: erst der Waschsaal mit den
        // Schlauchstaenden, dahinter die Schwimmhalle - Glaswaende, Glasdach,
        // der hellste Ort des Hauses. Der Weg dorthin fuehrt durchs ganze Haus.
        let F2: Float = 6.6
        let tileFine = texMat(Tex.tileGreen, 10, 8)      // die Mini-Fliesen
        let tileWall = texMat(Tex.tileGreen, 8, 4)

        // Die obere Treppe steht jetzt mit der unteren zusammen in
        // Stairwell.swift - sie muessen deckungsgleich uebereinander liegen,
        // sonst schiebt sich ein Podest in den Lauf darunter.

        // Vorraum am Treppenkopf. Der Schacht x[-8,-4] z[6,14] bleibt frei;
        // sein Bodenband baut buildStairwell.
        floorTile(4.0, 3.0, -6.0, 4.5, linoF, y: F2)     // x[-8,-4] z[3,6]
        floorTile(3.0, 10.0, -2.5, 8.0, linoF, y: F2)    // x[-4,-1] z[3,13]
        ceiling(7, 11, -4.5, 8.5, F2 + 2.7)
        wallZ(3, 6, -8, wArd, h: 2.7, base: F2)          // noerdlich des Schachts
        wallX(-4, -1, 13, wArd, h: 2.7, base: F2)        // nur wo Boden liegt
        // (Nordwand entfaellt - weiter unten steht sie schon als x[-9,-1].)
        wallZ(3, 13, -1, wArd, gaps: [(9.5, 1.3)], h: 2.7, base: F2)
        addOmni(SCNVector3(-4.5, F2 + 2.2, 8), 300,
                UIColor(red: 0.92, green: 0.88, blue: 0.80, alpha: 1), range: 7)
        // Alte Plakate des Kurbetriebs
        prop(0.04, 1.15, 0.85, -7.94, F2 + 1.6, 9.5, texMat(Tex.poster1, 1, 1))
        prop(0.04, 1.15, 0.85, -7.94, F2 + 1.6, 5.0, texMat(Tex.poster2, 1, 1))

        // Waschsaal: Minifliesen, vier Schlauchstaende, Haltestange, Roste
        floorTile(10, 10, 4, 8, tileFine, y: F2)
        ceiling(10, 10, 4, 8, F2 + 2.7)
        wallX(-1, 9, 13, tileWall, h: 2.7, base: F2)
        wallZ(3, 13, 9, tileWall, h: 2.7, base: F2)
        wallX(-1, 9, 3, tileWall, gaps: [(4.0, 1.6)], h: 2.7, base: F2)
        for hx in [Float(0.6), 2.2, 6.0, 7.8] { hoseStation(hx, 3.25, F2) }
        prop(0.85, 1.15, 0.04, 5.0, F2 + 1.7, 12.94, texMat(Tex.poster1, 1, 1))
        // Haltestange, an der die Patienten standen
        for px in [Float(1.5), 4.0, 6.5] {
            prop(0.07, 1.05, 0.07, px, F2 + 0.52, 10.0, texMat(Tex.iron, 2, 1), solid: true)
        }
        prop(6.0, 0.06, 0.06, 4.0, F2 + 1.02, 10.0, texMat(Tex.brass, 1, 1))
        // Bodenablaeufe und Holzroste
        for dz in [Float(6.2), 8.4] {
            prop(7.6, 0.015, 0.18, 4.0, F2 + 0.012, dz, col(0.10, 0.10, 0.10))
        }
        for gx in [Float(1.2), 4.0, 6.8] {
            for k2 in 0..<5 {
                prop(1.5, 0.05, 0.14, gx, F2 + 0.035, 7.0 + Float(k2) * 0.24, texMat(Tex.plankWood, 1, 1))
            }
        }
        waterSurface(4.0, F2 + 0.012, 5.2, 2.4, 1.4,
                     tint: UIColor(red: 0.32, green: 0.34, blue: 0.32, alpha: 1),
                     murk: 0.65, rep: 1.4, flow: 0.012)
        addOmni(SCNVector3(4, F2 + 2.2, 8), 340,
                UIColor(red: 0.86, green: 0.90, blue: 0.90, alpha: 1), range: 8)
        contactShadow(4.0, 10.0, 6.4, 0.8, y: F2 + 0.012)

        // Schwimmhalle: Glas auf drei Seiten, Glasdach, Pflanzen, das Becken
        floorTile(18, 16, 0, -5, texMat(Tex.tileGreen, 9, 8), y: F2)
        wallX(-9, -1, 3, wArd, h: 2.7, base: F2)          // Rest der Suedwand
        glassRun(-13, 3, -9, alongX: false, F2, 2.6)
        glassRun(-13, 3, 9, alongX: false, F2, 2.6)
        glassRun(-9, 9, -13, alongX: true, F2, 2.6)
        // Blendenband zwischen Glaswand und Dach
        prop(18.4, 0.42, 0.22, 0, F2 + 3.26, -13, texMat(Tex.wainscot, 3, 1))
        prop(0.22, 0.42, 16.3, -9, F2 + 3.26, -5, texMat(Tex.wainscot, 3, 1))
        prop(0.22, 0.42, 16.3, 9, F2 + 3.26, -5, texMat(Tex.wainscot, 3, 1))
        // Glasdach: drei leuchtende Bahnen zwischen Eisensparren
        // Milchglas statt Leuchtplatte: leicht durchscheinend, ruhig gluehend -
        // draussen liegt dichter Nebel, durch den nur diffuses Licht faellt.
        // Eine Dachplatte statt drei. Milchglas: draussen liegt dichter Nebel,
        // durch den nur diffuses Licht faellt.
        let roofM = windowMat(0)
        roofM.emission.intensity = 0.50
        roofM.transparency = 0.84
        prop(17.6, 0.07, 15.6, 0, F2 + 3.44, -5.0, roofM)
        for rx in stride(from: Float(-8), through: 8, by: 2.0) {
            prop(0.12, 0.16, 16.2, rx, F2 + 3.36, -5, texMat(Tex.iron, 2, 1))
        }
        for sx in [Float(-5.5), 0, 5.5] {
            lightShaft(SCNVector3(sx, F2 + 3.3, -5), SCNVector3(sx, F2 + 0.06, -5),
                       1.7, 0.11, UIColor(red: 0.88, green: 0.90, blue: 0.92, alpha: 1))
            addOmni(SCNVector3(sx, F2 + 2.6, -5), 230,
                    UIColor(red: 0.94, green: 0.95, blue: 0.96, alpha: 1), range: 15)
        }
        floorPool(0, -5, 7.0, 5.0, 0.16, UIColor(red: 0.90, green: 0.92, blue: 0.94, alpha: 1))

        // Das Becken: Superellipsen-Ringe wie bei der Wanne, nur begehbar gross
        do {
            let bx: Float = 0, bz: Float = -5
            let bn = 14
            func bpt(_ i: Int, _ ax: Float, _ az: Float, _ y: Float) -> SCNVector3 {
                let a2 = Float(i) / Float(bn) * 2 * Float.pi
                let c = cos(a2), sn = sin(a2)
                let e: Float = 0.75
                return SCNVector3(bx + ax * (c < 0 ? -1 : 1) * pow(abs(c), e), y,
                                  bz + az * (sn < 0 ? -1 : 1) * pow(abs(sn), e))
            }
            let BR: [(Float, Float, Float)] = [
                (F2 + 0.005, 5.30, 3.30), (F2 + 0.05, 5.10, 3.10),
                (F2 + 0.05, 4.85, 2.85), (F2 - 0.32, 4.78, 2.78), (F2 - 0.92, 4.62, 2.62)]
            var bt: [(SCNVector3, SCNVector3, SCNVector3)] = []
            for k2 in 0..<(BR.count - 1) {
                for i in 0..<bn {
                    let j = (i + 1) % bn
                    bt.append((bpt(i, BR[k2].1, BR[k2].2, BR[k2].0),
                               bpt(j, BR[k2+1].1, BR[k2+1].2, BR[k2+1].0),
                               bpt(i, BR[k2+1].1, BR[k2+1].2, BR[k2+1].0)))
                    bt.append((bpt(i, BR[k2].1, BR[k2].2, BR[k2].0),
                               bpt(j, BR[k2].1, BR[k2].2, BR[k2].0),
                               bpt(j, BR[k2+1].1, BR[k2+1].2, BR[k2+1].0)))
                }
            }
            let bc = SCNVector3(bx, F2 - 0.94, bz)
            for i in 0..<bn {
                let j = (i + 1) % bn
                bt.append((bc, bpt(i, BR[4].1, BR[4].2, BR[4].0), bpt(j, BR[4].1, BR[4].2, BR[4].0)))
            }
            triMesh(bt, texMat(Tex.tileGreen, 6, 3))
            waterSurface(bx, F2 - 0.34, bz, 9.2, 5.2,
                         tint: UIColor(red: 0.30, green: 0.55, blue: 0.50, alpha: 1),
                         murk: 0.84, rep: 2.4, flow: 0.014)
            addOmni(SCNVector3(bx, F2 - 0.5, bz), 260,
                    UIColor(red: 0.45, green: 0.80, blue: 0.72, alpha: 1), range: 7)
            for _ in 0..<5 {
                prop(CGFloat.random(in: 0.10...0.2), 0.012, CGFloat.random(in: 0.08...0.16),
                     bx + Float.random(in: -4...4), F2 - 0.328, bz + Float.random(in: -2.2...2.2),
                     col(0.16, 0.30, 0.12))
            }
            blocker(bx - 5.2, bx + 5.2, bz - 3.2, bz + 3.2, base: F2, height: 1.2)
            // Einstiegsleiter
            cyl(0.022, 0.9, 3.0, F2 + 0.4, bz + 3.05, texMat(Tex.brass, 1, 1))
            cyl(0.022, 0.9, 3.4, F2 + 0.4, bz + 3.05, texMat(Tex.brass, 1, 1))
            for r2 in 0..<3 {
                prop(0.42, 0.035, 0.035, 3.2, F2 + 0.18 + Float(r2) * 0.26, bz + 3.05, texMat(Tex.brass, 1, 1))
            }
        }
        // Pflanzen: Palmen an den Glaswaenden, zwei umgestuerzt
        for (px2, pz2) in [(Float(-7.6), Float(-11.4)), (7.6, -11.4), (-7.6, 1.4),
                           (7.6, 1.4), (-7.4, -5.0), (7.4, -5.0)] {
            palmAt(px2, pz2, F2)
        }
        palmAt(5.6, -9.6, F2, leaning: true)
        palmAt(-4.4, 0.9, F2, leaning: true)

        _ = doorLeaf(-1, 9.5, 1.3, 2.15, true, 1, "Waschsaal", lock: .bathKey, style: 1, swing: 1, base: F2)
        _ = doorLeaf(4.0, 3, 1.5, 2.2, false, 1, "Schwimmhalle", open: true, style: 2, base: F2)

        // ============ Isolierzellen am Stationsende ============
        // Zwei Zellen mit Wandringen und haengenden Handschellen, Kratzspuren
        // an den Tueren. Hier ist jemandem etwas entglitten - Vorgriff auf den
        // Keller. Der Stichflur ist bewusst enger und dunkler als die Station.
        floorTile(2.4, 3.2, 0, -21.6, linoF, y: F)
        ceiling(2.4, 3.2, 0, -21.6, F + 2.6)
        wallZ(-23.2, -20, -1.2, wArd, gaps: [(-21.6, 0.95)], h: 2.6, base: F)
        wallZ(-23.2, -20, 1.2, wArd, gaps: [(-21.6, 0.95)], h: 2.6, base: F)
        wallX(-3.8, 3.8, -23.2, wArd, h: 2.6, base: F)
        wallX(-3.8, -1.2, -20.2, wArd, h: 2.6, base: F)
        wallX(1.2, 3.8, -20.2, wArd, h: 2.6, base: F)
        wallZ(-23.2, -20.2, -3.8, wArd, h: 2.6, base: F)
        wallZ(-23.2, -20.2, 3.8, wArd, h: 2.6, base: F)
        let cellTile = texMat(Tex.tileGreen, 3, 3)
        let ironC = texMat(Tex.iron, 2, 2)
        for sgc in [Float(-1), 1] {
            let cx2 = sgc * 2.5
            floorTile(2.6, 3.0, cx2, -21.7, cellTile, y: F)
            ceiling(2.6, 3.0, cx2, -21.7, F + 2.6)
            // Pritsche mit Eisenrahmen
            prop(0.62, 0.14, 1.85, sgc * 3.25, F + 0.30, -21.7, ironC, solid: true)
            prop(0.58, 0.08, 1.75, sgc * 3.25, F + 0.42, -21.7, col(0.52, 0.50, 0.46))
            // Wandring, Kette, Handschellen
            let ring = SCNTorus(ringRadius: 0.075, pipeRadius: 0.016)
            ring.ringSegmentCount = 10; ring.pipeSegmentCount = 5; ring.firstMaterial = ironC
            let rn = SCNNode(geometry: ring)
            rn.position = SCNVector3(sgc * 3.66, F + 1.42, -21.0)
            rn.eulerAngles = SCNVector3(0, Float.pi / 2, 0)
            scene.rootNode.addChildNode(rn)
            for k2 in 0..<3 {
                let link = SCNTorus(ringRadius: 0.035, pipeRadius: 0.011)
                link.ringSegmentCount = 8; link.pipeSegmentCount = 4; link.firstMaterial = ironC
                let lk = SCNNode(geometry: link)
                lk.position = SCNVector3(sgc * 3.62, F + 1.32 - Float(k2) * 0.075, -21.0)
                lk.eulerAngles = SCNVector3(0, k2 % 2 == 0 ? Float.pi / 2 : 0, 0.2)
                scene.rootNode.addChildNode(lk)
            }
            for dx in [Float(-0.045), 0.045] {
                let cuff = SCNTorus(ringRadius: 0.05, pipeRadius: 0.013)
                cuff.ringSegmentCount = 9; cuff.pipeSegmentCount = 4; cuff.firstMaterial = ironC
                let cn3 = SCNNode(geometry: cuff)
                cn3.position = SCNVector3(sgc * 3.60 + dx, F + 1.05, -21.0)
                cn3.eulerAngles = SCNVector3(0.4, 0, 0.5 * dx * 20)
                scene.rootNode.addChildNode(cn3)
            }
            // Kratzspuren neben der Tuer, von innen
            for k3 in 0..<6 {
                propE(0.006, 0.22 + CGFloat(k3 % 3) * 0.05, 0.015,
                      sgc * 1.30, F + 1.15 + Float(k3) * 0.045, -21.25 + Float(k3) * 0.04,
                      SCNVector3(0, 0, 0.15 + Float(k3 % 3) * 0.08), col(0.10, 0.08, 0.07))
            }
            floorPool(cx2 * 1.15, -22.5, 0.85, 0.65, 0.34,
                      UIColor(red: 0.24, green: 0.10, blue: 0.08, alpha: 1))
            _ = doorLeaf(sgc * 1.2, -21.6, 0.95, 2.05, true, -sgc, sgc < 0 ? "Zelle West" : "Zelle Ost",
                         style: 3, swing: 1, base: F)
        }
        let cellLight = addOmni(SCNVector3(0, F + 2.25, -21.3), 260,
                                UIColor(red: 0.92, green: 0.80, blue: 0.60, alpha: 1), range: 5.5)
        registerFlicker(cellLight, 260)

        // Tueren im ersten Stock
        _ = doorLeaf(-3, -3.5, 1.15, 2.15, true, 1, "Zimmer 1", open: true, style: 1, swing: 1, base: F)
        _ = doorLeaf(3, -3.5, 1.15, 2.15, true, -1, "Zimmer 2", style: 1, swing: 1, base: F)
        _ = doorLeaf(-3, -10.5, 1.15, 2.15, true, -1, "Zimmer 3", open: true, style: 1, swing: 1, base: F)
        _ = doorLeaf(3, -10.5, 1.15, 2.15, true, 1, "Zimmer 4", style: 1, swing: 1, base: F)
        _ = doorLeaf(-3, -17.5, 1.15, 2.15, true, -1, "Schwesternzimmer", style: 1, swing: 1, base: F)
        _ = doorLeaf(3, -17.5, 1.15, 2.15, true, 1, "Waschraum", style: 1, swing: 1, base: F)

        // ---------- Heizungsraum und Kohlenkeller ----------
        // Der Kessel aus dem Wartungsheft: er brennt seit drei Tagen ohne
        // Beschickung. Dahinter der Kohlenkeller mit Rutsche und Halden.
        floorTile(4, 4.6, 9, -15.7, texMat(Tex.stoneFloor, 2, 2), y: 0)
        floorTile(4, 5, 9, -20.5, texMat(Tex.stoneFloor, 2, 2), y: 0)
        ceiling(4, 4.6, 9, -15.7, 2.4)
        ceiling(4, 5, 9, -20.5, 2.4)
        // (Westwand des Kellergangs entfaellt - die Direktionswand bei x=7
        //  steht an derselben Stelle und ist hoeher.)
        wallX(7, 11, -23, wCell, h: 2.4, wainscot: false)
        wallX(7, 11, -18, wCell, gaps: [(9.0, 1.15)], h: 2.4, wainscot: false)

        do {
            let rust = texMat(Tex.rust, 2, 2)
            let ironD = texMat(Tex.iron, 2, 2)
            // Der Kessel: genieteter Zylinder, Feuerklappe glueht
            cyl(0.82, 2.0, 9, 1.0, -15.4, rust)
            cyl(0.55, 0.30, 9, 2.12, -15.4, rust)
            for by in [Float(0.45), 1.05, 1.65] {
                let band = SCNTorus(ringRadius: 0.83, pipeRadius: 0.035)
                band.ringSegmentCount = 14; band.pipeSegmentCount = 5
                band.firstMaterial = ironD
                let bn2 = SCNNode(geometry: band)
                bn2.position = SCNVector3(9, by, -15.4)
                scene.rootNode.addChildNode(bn2)
            }
            prop(0.58, 0.66, 0.12, 9, 0.72, -14.56, ironD, solid: true)
            let fire = SCNMaterial()
            fire.lightingModel = .constant
            fire.diffuse.contents = UIColor(red: 1.0, green: 0.44, blue: 0.10, alpha: 1)
            fire.emission.contents = UIColor(red: 1.0, green: 0.42, blue: 0.08, alpha: 1)
            fire.emission.intensity = 1.25
            prop(0.36, 0.09, 0.03, 9, 0.52, -14.49, fire)          // gluehender Spalt
            prop(0.10, 0.10, 0.03, 9.16, 0.92, -14.49, fire)       // Schauglas
            cylE(0.02, 0.26, 8.66, 0.72, -14.48, SCNVector3(0, 0, Float.pi / 2), texMat(Tex.brass, 1, 1))
            let fl = addOmni(SCNVector3(9, 0.9, -14.2), 300,
                             UIColor(red: 1.0, green: 0.55, blue: 0.22, alpha: 1), range: 6)
            registerFlicker(fl, 300)
            // Rohre: hinauf und hinueber zur Quelle
            cyl(0.09, 0.5, 9, 2.35, -15.4, rust)
            cylE(0.075, 2.6, 10.0, 1.85, -15.9, SCNVector3(0, 0, Float.pi / 2), rust)
            cylE(0.075, 2.6, 10.0, 1.55, -14.9, SCNVector3(0, 0, Float.pi / 2), rust)
            let vw = SCNTorus(ringRadius: 0.09, pipeRadius: 0.018)
            vw.ringSegmentCount = 10; vw.pipeSegmentCount = 5
            vw.firstMaterial = texMat(Tex.brass, 1, 1)
            let vn = SCNNode(geometry: vw)
            vn.position = SCNVector3(10.2, 1.72, -15.9)
            scene.rootNode.addChildNode(vn)
            // Manometer
            cyl(0.09, 0.03, 8.35, 1.55, -14.55, col(0.85, 0.83, 0.78))
            prop(0.012, 0.06, 0.012, 8.35, 1.57, -14.53, col(0.55, 0.12, 0.10))
            blocker(8.1, 9.9, -16.3, -14.5)
            contactShadow(9, -15.4, 2.2, 2.2)
            // Kohle-Rest, Schaufel und Eimer beim Kessel
            for _ in 0..<8 {
                sph(CGFloat.random(in: 0.04...0.08), 9 + Float.random(in: -1.2...1.2),
                    0.05, -14.0 + Float.random(in: -0.3...0.3), col(0.07, 0.07, 0.08))
            }
            cylE(0.02, 1.1, 7.5, 0.55, -14.0, SCNVector3(0.4, 0, 0.2), texMat(Tex.plankWood, 1, 1))
            prop(0.22, 0.05, 0.16, 7.62, 0.05, -13.82, ironD)
            cyl(0.14, 0.26, 10.5, 0.13, -14.0, ironD)

            // Kohlenkeller: Rutsche und zwei Halden
            propE(0.9, 0.08, 2.0, 9.8, 1.65, -22.3, SCNVector3(-0.62, 0, 0), texMat(Tex.plankWood, 1, 1))
            let coal = mat2(UIColor(red: 0.075, green: 0.075, blue: 0.085, alpha: 1))
            func coalPile(_ px2: Float, _ pz2: Float, _ r: Float, _ hgt: Float) {
                let pn2 = 10
                let PR: [(Float, Float)] = [(0, r), (hgt * 0.4, r * 0.78),
                                            (hgt * 0.75, r * 0.45), (hgt, r * 0.16)]
                var pt2: [(SCNVector3, SCNVector3, SCNVector3)] = []
                func cp(_ i: Int, _ rr: Float, _ y: Float) -> SCNVector3 {
                    let a2 = Float(i) / Float(pn2) * 2 * Float.pi
                    return SCNVector3(px2 + sin(a2) * rr, y, pz2 + cos(a2) * rr * 0.85)
                }
                for k2 in 0..<(PR.count - 1) {
                    for i in 0..<pn2 {
                        let j = (i + 1) % pn2
                        pt2.append((cp(i, PR[k2].1, PR[k2].0), cp(j, PR[k2+1].1, PR[k2+1].0), cp(i, PR[k2+1].1, PR[k2+1].0)))
                        pt2.append((cp(i, PR[k2].1, PR[k2].0), cp(j, PR[k2].1, PR[k2].0), cp(j, PR[k2+1].1, PR[k2+1].0)))
                    }
                }
                let tp = SCNVector3(px2, hgt + 0.04, pz2)
                for i in 0..<pn2 { pt2.append((tp, cp(i, PR[3].1, PR[3].0), cp((i + 1) % pn2, PR[3].1, PR[3].0))) }
                triMesh(pt2, coal)
                for _ in 0..<9 {
                    sph(CGFloat.random(in: 0.04...0.09), px2 + Float.random(in: -r...r),
                        0.05, pz2 + Float.random(in: -r * 0.8...r * 0.8), coal)
                }
                contactShadow(px2, pz2, CGFloat(r) * 2.6, CGFloat(r) * 2.3)
                blocker(px2 - r, px2 + r, pz2 - r * 0.85, pz2 + r * 0.85, height: hgt + 0.3)
            }
            coalPile(9.5, -21.4, 1.15, 0.85)
            coalPile(7.9, -19.6, 0.75, 0.55)
            crateAt(7.8, 0, -18.8, 0.6, col(0.40, 0.29, 0.16), col(0.28, 0.20, 0.11))
            let lant = addOmni(SCNVector3(9, 1.9, -19.8), 190,
                               UIColor(red: 0.95, green: 0.72, blue: 0.42, alpha: 1), range: 5.5)
            registerFlicker(lant, 190)
        }

        // ---------- Quellbecken ----------
        // Der Grund, warum das Haus existiert: ein Steinbecken ueber der Quelle,
        // das Wasser dunkel und zu warm. Zwei Rohre fuehren hinein.
        do {
            let qx: Float = 17.0, qz: Float = -19.5
            let stoneQ = texMat(Tex.stoneFloor, 2, 1)
            var qt: [(SCNVector3, SCNVector3, SCNVector3)] = []
            let qn = 12
            func qpt(_ i: Int, _ r: Float, _ y: Float) -> SCNVector3 {
                let a2 = Float(i) / Float(qn) * 2 * Float.pi
                return SCNVector3(qx + sin(a2) * r, y, qz + cos(a2) * r * 0.82)
            }
            let QR: [(Float, Float)] = [(0.02, 1.30), (0.42, 1.34), (0.55, 1.38),
                                        (0.55, 1.10), (0.10, 1.02)]
            for k in 0..<(QR.count - 1) {
                for i in 0..<qn {
                    let j = (i + 1) % qn
                    qt.append((qpt(i, QR[k].1, QR[k].0), qpt(j, QR[k+1].1, QR[k+1].0), qpt(i, QR[k+1].1, QR[k+1].0)))
                    qt.append((qpt(i, QR[k].1, QR[k].0), qpt(j, QR[k].1, QR[k].0), qpt(j, QR[k+1].1, QR[k+1].0)))
                }
            }
            triMesh(qt, stoneQ)
            waterSurface(qx, 0.44, qz, 2.05, 1.68,
                         tint: UIColor(red: 0.20, green: 0.10, blue: 0.08, alpha: 1),
                         murk: 0.95, rep: 1.1, flow: 0.004)
            cylE(0.07, 1.6, qx - 1.9, 0.9, qz, SCNVector3(0, 0, 1.15), texMat(Tex.rust, 2, 1))
            cylE(0.07, 1.4, qx + 1.8, 0.85, qz + 0.4, SCNVector3(0, 0, -1.05), texMat(Tex.rust, 2, 1))
            addDust(qx, 1.1, qz, 3.2, 1.6, 2.6, 16)
            addOmni(SCNVector3(qx, 1.3, qz), 240,
                    UIColor(red: 0.90, green: 0.55, blue: 0.34, alpha: 1), range: 6)
            blocker(qx - 1.45, qx + 1.45, qz - 1.2, qz + 1.2)
            contactShadow(qx, qz, 3.1, 2.6)
        }

        // ---------- Kamera-Zonen ----------
        // Alle Zonen laufen jetzt mit. Feste Winkel haben in diesen Raum-
        // groessen nie funktioniert - entweder war der Spieler weg oder
        // die halbe Einrichtung. y ist Versatz ueber dem Spieler.
zone(-2, 8, 0, 14,       SCNVector3(0.0, 3.4, 5.8), SCNVector3(0, 1.15, 0), 70,
             follow: true)                                   // Empfangshalle
zone(-8, -2, 0, 6.0,     SCNVector3(0.0, 3.0, 5.6), SCNVector3(0, 1.15, 0), 68,
             follow: true)                                   // Flur
        // Treppenhaus: EINE Zone ueber alle Hoehen (-1 bis 5.4). Vorher endete
        // sie bei yHi 2.6 - beim Hochsteigen fiel man aus der Zone heraus und
        // die Kamera drehte deshalb nie mit.
        zone(-4, -2, 6.0, 14,    SCNVector3(0.0, 2.8, 5.2), SCNVector3(0, 1.15, 0), 66,
             follow: true)                                    // Flur Ost
        // Treppenhaus: Blick von Norden schraeg herab in den Schacht. EINE Zone
        // ueber alle Hoehen, damit die Kamera beim Steigen mitgeht.
        // EINE Zone ueber alle drei Ebenen (0 / 3.8 / 6.6). Endete sie wie
        // frueher bei 5.4, fiel die Kamera auf dem oberen Lauf aus der Zone.
        //
        // Versatz auf 2.4 m verkuerzt: der Schacht ist innen nur 3.6 x 7.6 m.
        // Mit 4.2 m stand die Kamera fast immer JENSEITS der Nord- oder
        // Suedwand, wurde von hitsWall() herangezogen und sprang bei jedem
        // Schritt - das war das Schwimmen auf der Treppe. Dafuer steiler von
        // oben, das passt auch besser zu einem drei Geschosse hohen Schacht.
        zone(-8, -4, 6.0, 14,    SCNVector3(0.0, 3.9, -2.4), SCNVector3(0, 1.0, 0), 74,
             follow: true, yLo: -1, yHi: 7.4)                 // Treppenhaus
zone(-31, -24, -2, 14,   SCNVector3(0.0, 2.6, 5.6), SCNVector3(0, 1.15, 0), 60,
             follow: true)                                    // Westflur Sued
zone(-31, -24, -22, -2,  SCNVector3(0.0, 2.6, 5.6), SCNVector3(0, 1.15, 0), 62,
             follow: true, yaw: Float.pi)                                    // Westflur Nord
zone(-24, -8, 2, 14,     SCNVector3(0.0, 3.0, 5.6), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: -Float.pi/2)                                   // Speisezimmer
zone(8, 22, 2, 14,       SCNVector3(0.0, 3.0, 5.6), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: Float.pi/2)                                   // Bibliothek
zone(-47, -31, -22, -6,  SCNVector3(0.0, 3.1, 5.6), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: -Float.pi/2)                                   // Salon
zone(11, 23, -23, -11.5, SCNVector3(0.0, 2.0, 5.2), SCNVector3(0, 1.05, 0), 72,
             follow: true)                                   // Keller
        zone(7, 11, -18, -13.4, SCNVector3(0.0, 1.9, 4.6), SCNVector3(0, 1.1, 0), 64,
             follow: true)                                   // Heizungsraum
        zone(7, 11, -23, -18,   SCNVector3(0.0, 1.9, 4.6), SCNVector3(0, 1.1, 0), 64,
             follow: true)                                   // Kohlenkeller
        zone(-24.0, -12.0, -10.0, 2.0, SCNVector3(0.0, 2.75, 5.6), SCNVector3(0, 1.15, 0), 74,
             follow: true)   // 
        zone(12.0, 22.0, -10.0, 2.0, SCNVector3(0.0, 3.3, 5.6), SCNVector3(0, 1.15, 0), 74,
             follow: true)   // 
        zone(-3.0, 3.0, -14.0, 0.0, SCNVector3(0.0, 2.55, 5.6), SCNVector3(0, 1.15, 0), 66,
             follow: true)   // 
        zone(-10.0, -3.0, -11.0, -4.0, SCNVector3(0.0, 2.25, 5.6), SCNVector3(0, 1.15, 0), 76,
             follow: true, yaw: -Float.pi/2)   // 
        zone(3.0, 10.0, -11.0, -4.0, SCNVector3(0.0, 2.55, 5.6), SCNVector3(0, 1.15, 0), 74,
             follow: true, yaw: Float.pi/2)   // 
        zone(-7.0, 7.0, -24.0, -14.0, SCNVector3(0.0, 3.15, 5.6), SCNVector3(0, 1.15, 0), 74,
             follow: true)   // 
        zone(3.0, 11.0, -13.4, -11.6, SCNVector3(0.0, 2.15, 5.6), SCNVector3(0, 1.15, 0), 74,
             follow: true, yaw: Float.pi/2)   // ---------- Erster Stock ----------
zone(-8, -1.5, 0, 6.0,   SCNVector3(0.0, 2.1, 5.4), SCNVector3(0, 1.15, 0), 66,
             follow: true, yLo: 2.6, yHi: 5.4)                  // Galerie
zone(-3, 3, -20, -0.2,   SCNVector3(0.0, 2.1, 5.4), SCNVector3(0, 1.15, 0), 64,
             follow: true, yLo: 2.6, yHi: 5.4)                  // Flur oben
        zone(-11.0, -3.0, -6.0, -1.0, SCNVector3(0.0, 2.3, 5.6), SCNVector3(0, 1.15, 0), 72,
             follow: true, yaw: -Float.pi/2, yLo: 2.6, yHi: 5.4)   // Zimmer 1
        zone(3.0, 11.0, -6.0, -1.0, SCNVector3(0.0, 2.3, 5.6), SCNVector3(0, 1.15, 0), 72,
             follow: true, yaw: Float.pi/2, yLo: 2.6, yHi: 5.4)   // Zimmer 2
        zone(-11.0, -3.0, -13.0, -8.0, SCNVector3(0.0, 2.3, 5.6), SCNVector3(0, 1.15, 0), 72,
             follow: true, yaw: -Float.pi/2, yLo: 2.6, yHi: 5.4)   // Zimmer 3
        zone(3.0, 11.0, -13.0, -8.0, SCNVector3(0.0, 2.3, 5.6), SCNVector3(0, 1.15, 0), 72,
             follow: true, yaw: Float.pi/2, yLo: 2.6, yHi: 5.4)   // Zimmer 4
        zone(-11, -3, -20, -15, SCNVector3(0.0, 2.1, 5.4), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: -Float.pi/2, yLo: 2.6, yHi: 5.4)   // Schwesternzimmer
        zone(3, 11, -20, -15,   SCNVector3(0.0, 2.1, 5.4), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: Float.pi/2, yLo: 2.6, yHi: 5.4)    // Waschraum OG
        // Zweigeteilt, damit sich der Vorraum nicht mit der Treppenhauszone
        // ueberlappt - updateCamera nimmt die ERSTE passende Zone, die zweite
        // greift dann nie.
        zone(-8, -4, 3, 6.0,  SCNVector3(0.0, 2.2, 5.4), SCNVector3(0, 1.15, 0), 66,
             follow: true, yaw: Float.pi/2, yLo: 5.4, yHi: 12)   // Vorraum West
        zone(-4, -1, 3, 13,   SCNVector3(0.0, 2.2, 5.4), SCNVector3(0, 1.15, 0), 66,
             follow: true, yLo: 5.4, yHi: 12)                    // Vorraum Ost
        zone(-1, 9, 3, 13,    SCNVector3(0.0, 2.2, 5.4), SCNVector3(0, 1.15, 0), 68,
             follow: true, yaw: Float.pi/2, yLo: 5.4, yHi: 12)   // Waschsaal
        zone(-9, 9, -13, 3,   SCNVector3(0.0, 3.2, 5.8), SCNVector3(0, 1.2, 0), 74,
             follow: true, yLo: 5.4, yHi: 12)                    // Schwimmhalle
        // yaw: die Zelle ist 7.6 m breit und nur 3.2 m tief. Mit Blick nach
        // Norden sah man eine Wand; jetzt laengs durch die Zellenreihe.
        zone(-3.8, 3.8, -23.2, -20, SCNVector3(0.0, 2.0, 4.2), SCNVector3(0, 1.1, 0), 66,
             follow: true, yaw: Float.pi/2, yLo: 2.6, yHi: 5.4)   // Isolierzellen
    }
}
