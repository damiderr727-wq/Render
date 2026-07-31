import SceneKit
import UIKit

// Villa Nachtschatten - Moebel als DATEN statt als Codezeilen.
//
// Warum das existiert: Moebel standen bisher als einzelne Funktionsaufrufe
// mitten in 2700 Zeilen Villa.swift. Jedes Umstellen war eine Codeaenderung,
// und falsch platzierte Stuecke blockierten Wege, ohne dass man es sah.
// Jetzt steht jedes Stueck als ein Eintrag in furnitureList. Der Editor im
// Spiel verschiebt und dreht sie, und gibt die Liste in genau diesem Format
// wieder aus - herauskopieren, hier ersetzen, fertig.

/// Ein Moebelstueck. a/b sind die Massparameter; 0 bedeutet "Standardmass".
struct Placement {
    var kind: String
    var x: Float
    var z: Float
    var rot: Float = 0        // Grad um die senkrechte Achse
    var floor: Int = 0        // 0 = Erdgeschoss, 1 = Obergeschoss, 2 = Badehaus
    var a: CGFloat = 0
    var b: CGFloat = 0
    var opt: String = ""      // Zusatz: Stuhlrichtung "n"/"s"/"o"/"w", "laengs" usw.
    /// Freie Hoehe UEBER der Etagenhoehe. 0 = steht auf dem Boden.
    /// Damit lassen sich Dinge auf Tische, Simse und Konsolen stellen.
    var dy: Float = 0
    /// Groesse. 1 = wie gebaut.
    var scale: Float = 1
}

/// Die bearbeitbare Liste. Vom Editor erzeugt und wieder eingelesen.
var furnitureList: [Placement] = [
    // ---- Empfangshalle ----
    Placement(kind: "luggageCart", x: 7.45, z: 5.40),
    Placement(kind: "armchair",    x: 0.50, z: 12.75, rot: 180),
    Placement(kind: "armchair",    x: 5.90, z: 12.75, rot: 180),
    Placement(kind: "table",       x: 7.15, z: 12.75, a: 0.80, b: 0.66),
    Placement(kind: "bench",       x: -1.55, z: 6.80, a: 2.00, opt: "laengs"),
    Placement(kind: "grandClock",  x: 7.40, z: 3.40),

    // ---- Baederabteilung ----
    Placement(kind: "bathtub",     x: -8.20, z: -7.50, a: 1.60, b: 3.00),
    Placement(kind: "bathtub",     x: -8.20, z: -5.30, a: 1.50, b: 2.00),
    Placement(kind: "chair",       x: -4.20, z: -6.40, opt: "w"),
    Placement(kind: "stool",       x: -6.50, z: -6.20),

    // ---- Speisesaal / Kueche / Lesesaal ----
    Placement(kind: "cabinet",     x: -7.40, z: 5.00, a: 1.40, b: 0.50),
    Placement(kind: "table",       x: -16.00, z: 8.00, a: 3.20, b: 5.40),
    Placement(kind: "cabinet",     x: -16.00, z: 13.40, a: 2.40, b: 0.60),
    Placement(kind: "table",       x: -18.00, z: -3.50, a: 1.60, b: 2.40),
    Placement(kind: "table",       x: 15.00, z: 8.00, a: 2.20, b: 1.30),
    Placement(kind: "armchair",    x: 18.60, z: 10.60, rot: 180),
    Placement(kind: "statue",      x: 14.20, z: -1.00),
    Placement(kind: "statue",      x: 19.80, z: -1.00),
    Placement(kind: "statue",      x: 17.00, z: -8.40),
    Placement(kind: "cabinet",     x: -2.40, z: -13.20, a: 1.20, b: 0.50),
    Placement(kind: "table",       x: 6.40, z: -6.20, a: 1.80, b: 0.85),

    // ---- Vorratsgang, Direktion, Musiksalon ----
    Placement(kind: "crate",       x: 4.40, z: -9.60, a: 0.90),
    Placement(kind: "crate",       x: 5.50, z: -10.20, a: 0.80),
    Placement(kind: "crate",       x: 8.80, z: -5.40, a: 1.00),
    Placement(kind: "barrel",      x: 6.90, z: -5.20),
    Placement(kind: "barrel",      x: 7.70, z: -6.00),
    Placement(kind: "table",       x: -4.50, z: -21.60, a: 2.60, b: 1.30),
    Placement(kind: "sofa",        x: -1.00, z: -16.40, rot: 180, a: 2.20),
    Placement(kind: "table",       x: -1.00, z: -18.20, a: 1.10, b: 0.70),
    Placement(kind: "bench",       x: -42.50, z: -15.60, a: 0.90),
    Placement(kind: "armchair",    x: -34.00, z: -16.50, rot: 180),

    // ---- Obergeschoss: Station, Schwesternzimmer, Waschraum ----
    Placement(kind: "table",       x: -8.50, z: -18.60, floor: 1, a: 1.70, b: 0.80),
    Placement(kind: "chair",       x: -8.50, z: -17.60, floor: 1, opt: "s"),
    Placement(kind: "cabinet",     x: -10.40, z: -16.20, floor: 1, a: 1.20, b: 0.50),
    Placement(kind: "sink",        x: 5.40, z: -19.40, floor: 1),
    Placement(kind: "sink",        x: 7.40, z: -19.40, floor: 1),
    Placement(kind: "sink",        x: 9.40, z: -19.40, floor: 1),
    Placement(kind: "bucket",      x: 4.20, z: -17.20, floor: 1),
    Placement(kind: "stool",       x: -6.20, z: -16.40, floor: 1),
    Placement(kind: "books",       x: -8.50, z: -18.60, floor: 1),

    // ---- Badehaus ----
    Placement(kind: "bench",       x: -7.40, z: 6.00, floor: 2, a: 2.00, opt: "laengs"),
    Placement(kind: "bench",       x: 0.00, z: 1.90, floor: 2, a: 2.40),
    Placement(kind: "stool",       x: 2.40, z: 11.00, floor: 2),
    Placement(kind: "bucket",      x: 1.20, z: 10.20, floor: 2),
]

/// Ein Wandstueck als Daten. axis "x" = laeuft entlang X, "z" = entlang Z.
/// a0/a1 sind Anfang und Ende auf dieser Achse, fixed die Querkoordinate.
/// gapC/gapW beschreiben eine Tuerlucke (gapW = 0 heisst keine).
struct WallSpec {
    var axis: String
    var a0: Float
    var a1: Float
    var fixed: Float
    var h: CGFloat = 4
    var floor: Int = 0
    var gapC: Float = 0
    var gapW: Float = 0
    var tex: String = "hall"
}

/// Bearbeitbare Waende. Beginnt mit dem Treppenhaus - genau dem Bereich, der
/// sich nicht von aussen geradeziehen liess. Neue Waende legt der Editor an.
var wallList: [WallSpec] = [
    WallSpec(axis: "x", a0: -8, a1: -2, fixed: 6.0, h: 6, gapC: -4.0, gapW: 4.0),
    WallSpec(axis: "z", a0: 6, a1: 14, fixed: -4.0, h: 6, gapC: 12.5, gapW: 1.6),
]

extension GameController {

    /// Baut alle Eintraege der Liste. Jedes Stueck bekommt einen eigenen
    /// Gruppenknoten, damit der Editor es als Ganzes anfassen kann.
    /// Waende aus der Liste bauen. Sie kommen ZUSAETZLICH zu den fest
    /// gebauten - so bleibt der Bestand unangetastet und du kannst neue
    /// Waende ziehen, ohne dass etwas Altes zerbricht.
    func buildWalls() {
        wallNodes.removeAll()
        wallBase.removeAll()
        for w in wallList {
            wallBase.append((w.a0, w.a1))
            wallNodes.append(spawnWall(w))
        }
    }

    @discardableResult
    func spawnWall(_ w: WallSpec) -> SCNNode {
        let before = scene.rootNode.childNodes.count
        let m: SCNMaterial
        switch w.tex {
        case "tile":  m = texMat(Tex.tileGreen, 6, 3)
        case "cell":  m = texMat(Tex.wpGreen, 4, 1.4)
        case "stone": m = texMat(Tex.stoneFloor, 3, 2)
        default:      m = texMat(Tex.wpGreen, 6, 2.6)
        }
        let gaps: [(Float, Float)] = w.gapW > 0.01 ? [(w.gapC, w.gapW)] : []
        let base = floorBase(w.floor)
        if w.axis == "x" {
            wallX(min(w.a0, w.a1), max(w.a0, w.a1), w.fixed, m,
                  gaps: gaps, h: w.h, base: base)
        } else {
            wallZ(min(w.a0, w.a1), max(w.a0, w.a1), w.fixed, m,
                  gaps: gaps, h: w.h, base: base)
        }
        let g = SCNNode()
        g.name = "wall"
        let all = scene.rootNode.childNodes
        if all.count > before {
            for n in all[before...] { n.removeFromParentNode(); g.addChildNode(n) }
        }
        scene.rootNode.addChildNode(g)
        return g
    }

    /// Nach jeder Aenderung wird die Wand neu gebaut - anders als bei Moebeln
    /// aendert sich hier die Geometrie selbst (Laenge, Luecke, Hoehe).
    func rebuildWall(_ i: Int) {
        guard i >= 0, i < wallList.count, i < wallNodes.count else { return }
        wallNodes[i].removeFromParentNode()
        wallNodes[i] = spawnWall(wallList[i])
    }

    func selectNearestWall() {
        let px = player.position.x, pz = player.position.z
        var best = -1
        var bestD: Float = 9999
        for (i, w) in wallList.enumerated() where w.floor == floorIdx {
            let along = w.axis == "x" ? px : pz
            let cl = max(min(w.a0, w.a1), min(max(w.a0, w.a1), along))
            let dx = w.axis == "x" ? (cl - px) : (w.fixed - px)
            let dz = w.axis == "x" ? (w.fixed - pz) : (cl - pz)
            let d = (dx * dx + dz * dz).squareRoot()
            if d < bestD { bestD = d; best = i }
        }
        if best >= 0 { selectedWall = best; focusWallSelection(); say("Wand \(best + 1) gewaehlt.") }
        else { say("Keine Wand auf dieser Etage.") }
    }

    /// Ganze Wand querab verschieben.
    func nudgeWall(_ d: Float) {
        guard let i = selectedWall, i < wallList.count else { return }
        wallList[i].fixed += d
        rebuildWall(i)
        focusWallSelection()
    }

    /// Ein Ende verlaengern oder verkuerzen - so ziehst du Waende auf Laenge.
    func stretchWall(startEnd: Bool, _ d: Float) {
        guard let i = selectedWall, i < wallList.count else { return }
        if startEnd { wallList[i].a0 += d } else { wallList[i].a1 += d }
        rebuildWall(i)
    }

    func wallHeight(_ d: CGFloat) {
        guard let i = selectedWall, i < wallList.count else { return }
        wallList[i].h = max(1.0, min(8.0, wallList[i].h + d))
        rebuildWall(i)
    }

    /// Tuerluecke in die Mitte setzen oder wieder schliessen.
    func wallGap(_ width: Float) {
        guard let i = selectedWall, i < wallList.count else { return }
        if width <= 0 { wallList[i].gapW = 0 }
        else {
            wallList[i].gapC = (wallList[i].a0 + wallList[i].a1) / 2
            wallList[i].gapW = width
        }
        rebuildWall(i)
    }

    /// Luecke laengs verschieben.
    func slideGap(_ d: Float) {
        guard let i = selectedWall, i < wallList.count, wallList[i].gapW > 0 else { return }
        wallList[i].gapC += d
        rebuildWall(i)
    }

    func toggleWallAxis() {
        guard let i = selectedWall, i < wallList.count else { return }
        wallList[i].axis = wallList[i].axis == "x" ? "z" : "x"
        rebuildWall(i)
    }

    /// Neue Wand vor dem Spieler ziehen, 3 m lang auf der naeheren Achse.
    func addWall() {
        let px = player.position.x, pz = player.position.z
        let facingZ = abs(cos(player.eulerAngles.y)) > abs(sin(player.eulerAngles.y))
        let w = facingZ
            ? WallSpec(axis: "x", a0: px - 1.5, a1: px + 1.5, fixed: pz - 2.0,
                       h: 4, floor: floorIdx)
            : WallSpec(axis: "z", a0: pz - 1.5, a1: pz + 1.5, fixed: px - 2.0,
                       h: 4, floor: floorIdx)
        wallList.append(w)
        wallBase.append((w.a0, w.a1))
        wallNodes.append(spawnWall(w))
        selectedWall = wallList.count - 1
        say("Wand gezogen - mit den Pfeilen auf Laenge bringen.")
    }

    func deleteWall() {
        guard let i = selectedWall, i < wallList.count else { return }
        wallNodes[i].removeFromParentNode()
        wallNodes.remove(at: i)
        wallBase.remove(at: i)
        wallList.remove(at: i)
        selectedWall = wallList.isEmpty ? nil : min(i, wallList.count - 1)
        say("Wand entfernt.")
    }

    func saveWalls() {
        let text = wallList.map {
            [$0.axis, String($0.a0), String($0.a1), String($0.fixed),
             String(Double($0.h)), String($0.floor), String($0.gapC),
             String($0.gapW), $0.tex].joined(separator: "|")
        }.joined(separator: "\n")
        UserDefaults.standard.set(text, forKey: "walls_v1")
        say("Waende gesichert.")
    }

    @discardableResult
    func loadWalls() -> Bool {
        guard let text = UserDefaults.standard.string(forKey: "walls_v1"),
              !text.isEmpty else { return false }
        var out: [WallSpec] = []
        for line in text.split(separator: "\n") {
            let c = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
            guard c.count >= 9 else { continue }
            out.append(WallSpec(axis: c[0], a0: Float(c[1]) ?? 0, a1: Float(c[2]) ?? 0,
                                fixed: Float(c[3]) ?? 0, h: CGFloat(Double(c[4]) ?? 4),
                                floor: Int(c[5]) ?? 0, gapC: Float(c[6]) ?? 0,
                                gapW: Float(c[7]) ?? 0, tex: c[8]))
        }
        guard !out.isEmpty else { return false }
        wallList = out
        return true
    }

    func exportWalls() -> String {
        var out = "var wallList: [WallSpec] = [\n"
        for w in wallList {
            var l = String(format: "    WallSpec(axis: \"%@\", a0: %.2f, a1: %.2f, fixed: %.2f",
                           w.axis, w.a0, w.a1, w.fixed)
            l += String(format: ", h: %.1f", Double(w.h))
            if w.floor != 0 { l += ", floor: \(w.floor)" }
            if w.gapW > 0.01 { l += String(format: ", gapC: %.2f, gapW: %.2f", w.gapC, w.gapW) }
            if w.tex != "hall" { l += ", tex: \"\(w.tex)\"" }
            out += l + "),\n"
        }
        return out + "]\n"
    }

    func buildFurniture() {
        furnitureNodes.removeAll()
        furnitureBase.removeAll()
        for p in furnitureList {
            furnitureBase.append((p.x, p.z))
            furnitureNodes.append(spawnPlacement(p))
        }
    }

    /// Basishoehe einer Etage.
    func floorBase(_ f: Int) -> Float {
        f == 2 ? 6.6 : (f == 1 ? 3.8 : 0)
    }

    /// Ruft den passenden Bauer auf und sammelt alles Neue in einer Gruppe.
    /// Die Bauer haengen ihre Knoten direkt an die Szene - deshalb merken wir
    /// uns den Stand vorher und holen die Zugaenge anschliessend ab.
    @discardableResult
    func spawnPlacement(_ p: Placement) -> SCNNode {
        let before = scene.rootNode.childNodes.count
        let base = floorBase(p.floor)
        let wood = texMat(Tex.plankWood, 1, 1)
        let darkWood = texMat(Tex.wainscot, 2, 1)
        let fabric = texMat(Tex.velvetGreen, 2, 2)

        switch p.kind {
        case "table":
            tableAt(p.x, p.z, p.a > 0 ? p.a : 1.2, p.b > 0 ? p.b : 0.8,
                    base + 0.78, wood, darkWood)
        case "chair":
            chairAt(p.x, p.z, p.opt.isEmpty ? "n" : p.opt, wood)
        case "armchair":
            armchairAt(p.x, p.z, p.rot > 90 && p.rot < 270 ? -1 : 1, fabric, darkWood)
        case "sofa":
            sofaAt(p.x, p.z, p.a > 0 ? p.a : 1.9,
                   p.rot > 90 && p.rot < 270 ? -1 : 1, fabric, darkWood)
        case "cabinet":
            cabinetAt(p.x, p.z, p.a > 0 ? p.a : 1.2, p.b > 0 ? p.b : 0.5,
                      darkWood, texMat(Tex.brass, 1, 1))
        case "bench":
            benchAt(p.x, p.z, p.a > 0 ? p.a : 2.0, p.opt == "laengs", darkWood)
        case "crate":
            crateAt(p.x, base, p.z, p.a > 0 ? p.a : 0.6,
                    col(0.40, 0.29, 0.16), col(0.28, 0.20, 0.11))
        case "barrel":       barrelAt(p.x, p.z)
        case "statue":       statueAt(p.x, p.z)
        case "luggageCart":  luggageCart(p.x, p.z)
        case "grandClock":   grandClock(p.x, p.z)
        case "bathtub":
            bathtubAt(p.x, p.z, p.a > 0 ? p.a : 1.6, p.b > 0 ? p.b : 3.0)
        case "sink":         sinkAt(p.x, p.z, base: base)
        case "palm":         palmAt(p.x, p.z, base, leaning: p.opt == "gekippt")
        // ---- kleine Deko. Alles ohne Sperrkoerper, damit nichts Wege blockiert ----
        case "books":
            let cols: [SCNMaterial] = [col(0.42, 0.16, 0.12), col(0.18, 0.24, 0.36),
                                       col(0.30, 0.26, 0.14)]
            for k in 0..<3 {
                prop(0.20, 0.045, 0.14, p.x + Float(k) * 0.01, base + 0.80 + Float(k) * 0.047,
                     p.z, cols[k])
            }
        case "candle":
            prop(0.11, 0.02, 0.11, p.x, base + 0.79, p.z, texMat(Tex.brass, 1, 1))
            cyl(0.022, 0.14, p.x, base + 0.87, p.z, col(0.90, 0.87, 0.76))
            let fl = SCNMaterial(); fl.lightingModel = .constant
            fl.diffuse.contents = UIColor(red: 1.0, green: 0.78, blue: 0.36, alpha: 1)
            fl.emission.contents = UIColor(red: 1.0, green: 0.72, blue: 0.28, alpha: 1)
            sph(0.018, p.x, base + 0.955, p.z, fl)
            addOmni(SCNVector3(p.x, base + 1.0, p.z), 110,
                    UIColor(red: 1.0, green: 0.80, blue: 0.48, alpha: 1), range: 3.4)
        case "bottle":
            cyl(0.038, 0.20, p.x, base + 0.88, p.z, col(0.16, 0.26, 0.16))
            cyl(0.014, 0.09, p.x, base + 1.02, p.z, col(0.16, 0.26, 0.16))
        case "vase":
            cyl(0.075, 0.22, p.x, base + 0.89, p.z, col(0.62, 0.60, 0.56))
            for k in 0..<4 {
                let a3 = Float(k) / 4 * 2 * Float.pi
                cylE(0.008, 0.24, p.x + sin(a3) * 0.03, base + 1.10, p.z + cos(a3) * 0.03,
                     SCNVector3(sin(a3) * 0.3, 0, cos(a3) * 0.3), col(0.24, 0.30, 0.16))
            }
        case "bucket":
            cyl(0.13, 0.26, p.x, base + 0.13, p.z, texMat(Tex.iron, 1, 1))
            let hp = SCNTorus(ringRadius: 0.13, pipeRadius: 0.010)
            hp.ringSegmentCount = 10; hp.pipeSegmentCount = 4
            hp.firstMaterial = texMat(Tex.iron, 1, 1)
            let hn = SCNNode(geometry: hp)
            hn.position = SCNVector3(p.x, base + 0.30, p.z)
            hn.eulerAngles.z = Float.pi / 2
            scene.rootNode.addChildNode(hn)
            contactShadow(p.x, p.z, 0.36, 0.36, y: base + 0.012)
        case "lamp":
            cyl(0.09, 0.03, p.x, base + 0.79, p.z, darkWood)
            cyl(0.022, 0.20, p.x, base + 0.90, p.z, texMat(Tex.brass, 1, 1))
            let sh = SCNCone(topRadius: 0.07, bottomRadius: 0.13, height: 0.15)
            sh.radialSegmentCount = 9
            let sm = SCNMaterial(); sm.lightingModel = .constant
            sm.diffuse.contents = UIColor(red: 0.92, green: 0.80, blue: 0.58, alpha: 1)
            sm.emission.contents = UIColor(red: 0.80, green: 0.62, blue: 0.34, alpha: 1)
            sh.firstMaterial = sm
            let sn = SCNNode(geometry: sh)
            sn.position = SCNVector3(p.x, base + 1.06, p.z)
            scene.rootNode.addChildNode(sn)
            addOmni(SCNVector3(p.x, base + 1.02, p.z), 190,
                    UIColor(red: 1.0, green: 0.84, blue: 0.56, alpha: 1), range: 5)
        case "sack":
            let sc = col(0.55, 0.48, 0.38)
            cyl(0.20, 0.50, p.x, base + 0.25, p.z, sc)
            cyl(0.14, 0.06, p.x, base + 0.52, p.z, col(0.62, 0.58, 0.50))
            contactShadow(p.x, p.z, 0.55, 0.55, y: base + 0.012)
        case "toolbox":
            prop(0.44, 0.20, 0.24, p.x, base + 0.10, p.z, darkWood)
            prop(0.03, 0.10, 0.03, p.x, base + 0.25, p.z, texMat(Tex.iron, 1, 1))
            prop(0.30, 0.03, 0.03, p.x, base + 0.30, p.z, texMat(Tex.iron, 1, 1))
            contactShadow(p.x, p.z, 0.6, 0.4, y: base + 0.012)
        case "plantSmall":
            cyl(0.13, 0.20, p.x, base + 0.10, p.z, texMat(Tex.brick, 1, 1))
            for k in 0..<5 {
                let a3 = Float(k) / 5 * 2 * Float.pi
                cylE(0.010, 0.30, p.x + sin(a3) * 0.06, base + 0.34, p.z + cos(a3) * 0.06,
                     SCNVector3(sin(a3) * 0.5, 0, cos(a3) * 0.5), col(0.20, 0.34, 0.16))
            }
            contactShadow(p.x, p.z, 0.4, 0.4, y: base + 0.012)
        case "stool":
            contactShadow(p.x, p.z, 0.5, 0.5, y: base + 0.012)
            prop(0.40, 0.06, 0.40, p.x, base + 0.45, p.z, wood, solid: true)
            for sx in [-1, 1] { for sz in [-1, 1] {
                prop(0.05, 0.44, 0.05, p.x + Float(sx) * 0.15, base + 0.22,
                     p.z + Float(sz) * 0.15, darkWood)
            }}
        default:
            break
        }

        // Alles Neue einsammeln. Die Kinder behalten ihre Weltkoordinaten,
        // deshalb sitzt die Gruppe im Ursprung - der Drehpunkt wird auf das
        // Moebelstueck gelegt, damit Drehen um die eigene Achse geht.
        let g = SCNNode()
        g.name = "furn:" + p.kind
        let all = scene.rootNode.childNodes
        if all.count > before {
            for n in all[before...] {
                n.removeFromParentNode()
                g.addChildNode(n)
            }
        }
        g.pivot = SCNMatrix4MakeTranslation(p.x, 0, p.z)
        g.position = SCNVector3(p.x, 0, p.z)
        g.eulerAngles.y = p.rot * Float.pi / 180
        scene.rootNode.addChildNode(g)
        return g
    }

    /// Verschieben und Drehen wirken auf die Gruppe.
    /// WICHTIG: der Drehpunkt bleibt auf der BAUposition stehen, nur die
    /// Position wandert. Vorher habe ich beides auf denselben neuen Wert
    /// gesetzt - die heben sich in der Matrix exakt auf, deshalb bewegte sich
    /// nichts. Weltmatrix = Position * Drehung * Drehpunkt^-1.
    func applyPlacement(_ i: Int) {
        guard i >= 0, i < furnitureList.count, i < furnitureNodes.count,
              i < furnitureBase.count else { return }
        let p = furnitureList[i]
        let g = furnitureNodes[i]
        let b = furnitureBase[i]
        g.pivot = SCNMatrix4MakeTranslation(b.0, 0, b.1)   // bleibt, wo gebaut wurde
        g.position = SCNVector3(p.x, p.dy, p.z)            // wandert mit
        g.eulerAngles.y = p.rot * Float.pi / 180
        g.scale = SCNVector3(p.scale, p.scale, p.scale)
    }

    // ============ Editor: anfassen statt durchblaettern ============

    /// Antippen im Bild waehlt aus. Trifft man nichts, wird abgewaehlt.
    func tapSelect(_ p: CGPoint) {
        let i = pickFurniture(p)
        if i >= 0 {
            selectedFurniture = i
            say("\(furnitureList[i].kind) gewaehlt")
        } else {
            selectedFurniture = nil
        }
    }

    /// Ziehen: das Stueck folgt dem Finger auf seiner eigenen Standebene.
    /// dragStart merkt sich den Griffversatz, damit es nicht unter den Finger
    /// springt.
    func dragBegin(_ p: CGPoint) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        let f = furnitureList[i]
        let y = floorBase(f.floor) + f.dy
        if let w = groundPoint(p, y: y) {
            dragGrab = (w.x - f.x, w.z - f.z)
        } else {
            dragGrab = (0, 0)
        }
    }

    func dragMove(_ p: CGPoint) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        let f = furnitureList[i]
        let y = floorBase(f.floor) + f.dy
        guard let w = groundPoint(p, y: y) else { return }
        furnitureList[i].x = w.x - dragGrab.0
        furnitureList[i].z = w.z - dragGrab.1
        applyPlacement(i)
    }

    /// Hoehe ueber dem Boden aendern - fuer Dinge auf Tischen und Simsen.
    func raiseFurniture(_ d: Float) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        furnitureList[i].dy = max(-1.0, min(6.0, furnitureList[i].dy + d))
        applyPlacement(i)
    }

    func scaleFurniture(_ f: Float) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        furnitureList[i].scale = max(0.25, min(4.0, furnitureList[i].scale * f))
        applyPlacement(i)
    }

    /// Kopie des gewaehlten Stuecks, leicht versetzt.
    func duplicateFurniture() {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        var p = furnitureList[i]
        p.x += 0.4
        p.z += 0.4
        furnitureList.append(p)
        furnitureBase.append((p.x, p.z))
        furnitureNodes.append(spawnPlacement(p))
        selectedFurniture = furnitureList.count - 1
        say("Kopie abgelegt.")
    }

    /// Kamera auf das gewaehlte Stueck richten. Beim Verschieben laeuft sie
    /// mit - man arbeitet dadurch am Objekt statt es aus der Ferne zu schubsen.
    func focusSelection() {
        guard freeCam, let i = selectedFurniture, i < furnitureList.count else { return }
        let p = furnitureList[i]
        let y = floorBase(p.floor)
        // Blickrichtung beibehalten, nur den Abstand neu setzen
        let d: Float = 3.2
        fcPos = SCNVector3(p.x + sin(fcYaw) * d, y + 2.1, p.z + cos(fcYaw) * d)
        aimAt(SCNVector3(p.x, y + 0.6, p.z))
    }

    func focusWallSelection() {
        guard freeCam, let i = selectedWall, i < wallList.count else { return }
        let w = wallList[i]
        let cx = w.axis == "x" ? (w.a0 + w.a1) / 2 : w.fixed
        let cz = w.axis == "x" ? w.fixed : (w.a0 + w.a1) / 2
        let y = floorBase(w.floor)
        let d: Float = 5.0
        fcPos = SCNVector3(cx + sin(fcYaw) * d, y + 2.6, cz + cos(fcYaw) * d)
        aimAt(SCNVector3(cx, y + 1.2, cz))
    }

    /// Kamerawinkel so setzen, dass sie auf einen Punkt zeigt.
    func aimAt(_ t: SCNVector3) {
        let dx = t.x - fcPos.x, dy = t.y - fcPos.y, dz = t.z - fcPos.z
        let flat = (dx * dx + dz * dz).squareRoot()
        fcYaw = atan2(-dx, -dz)
        fcPitch = max(-1.4, min(1.4, atan2(dy, flat)))
    }

    /// Das naechstgelegene Stueck auf der aktuellen Etage auswaehlen.
    func selectNearestFurniture() {
        let px = player.position.x, pz = player.position.z
        var best = -1
        var bestD: Float = 9999
        for (i, p) in furnitureList.enumerated() where p.floor == floorIdx {
            let dx = p.x - px, dz = p.z - pz
            let d = (dx * dx + dz * dz).squareRoot()
            if d < bestD { bestD = d; best = i }
        }
        if best >= 0 {
            selectedFurniture = best
            focusSelection()
            say("Ausgewaehlt: \(furnitureList[best].kind)")
        } else {
            say("Nichts in der Naehe.")
        }
    }

    /// Ausgewaehltes Stueck verschieben. Schrittweite 10 cm.
    func nudgeFurniture(dx: Float, dz: Float) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        furnitureList[i].x += dx
        furnitureList[i].z += dz
        applyPlacement(i)
        focusSelection()
    }

    func rotateFurniture(_ deg: Float) {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        furnitureList[i].rot = (furnitureList[i].rot + deg).truncatingRemainder(dividingBy: 360)
        applyPlacement(i)
    }

    /// Neues Stueck vor dem Spieler absetzen.
    func addFurniture(_ kind: String) {
        let fx = -sin(player.eulerAngles.y), fz = -cos(player.eulerAngles.y)
        let p = Placement(kind: kind,
                          x: player.position.x + fx * 1.4,
                          z: player.position.z + fz * 1.4,
                          floor: floorIdx)
        furnitureList.append(p)
        furnitureBase.append((p.x, p.z))
        furnitureNodes.append(spawnPlacement(p))
        selectedFurniture = furnitureList.count - 1
        say("\(kind) abgesetzt.")
    }

    func deleteFurniture() {
        guard let i = selectedFurniture, i < furnitureList.count else { return }
        let kind = furnitureList[i].kind
        furnitureNodes[i].removeFromParentNode()
        furnitureNodes.remove(at: i)
        furnitureBase.remove(at: i)
        furnitureList.remove(at: i)
        selectedFurniture = furnitureList.isEmpty ? nil : min(i, furnitureList.count - 1)
        say("\(kind) entfernt.")
    }

    /// Die Liste als fertiger Swift-Code. Genau dieses Format liest
    /// furnitureList oben wieder ein.
    func exportFurniture() -> String {
        var out = "var furnitureList: [Placement] = [\n"
        for p in furnitureList {
            var line = String(format: "    Placement(kind: \"%@\", x: %.2f, z: %.2f",
                              p.kind, p.x, p.z)
            if abs(p.rot) > 0.01 { line += String(format: ", rot: %.0f", p.rot) }
            if p.floor != 0 { line += ", floor: \(p.floor)" }
            if p.a > 0 { line += String(format: ", a: %.2f", Double(p.a)) }
            if p.b > 0 { line += String(format: ", b: %.2f", Double(p.b)) }
            if !p.opt.isEmpty { line += ", opt: \"\(p.opt)\"" }
            if abs(p.dy) > 0.001 { line += String(format: ", dy: %.2f", p.dy) }
            if abs(p.scale - 1) > 0.001 { line += String(format: ", scale: %.2f", p.scale) }
            out += line + "),\n"
        }
        return out + "]\n"
    }

    /// In die Zwischenablage legen - nur noetig, wenn du den Stand fest in
    /// den Code uebernehmen willst. Fuers Weiterspielen reicht Sichern.
    func copyFurnitureToClipboard() {
        UIPasteboard.general.string = exportFurniture()
        say("Als Swift-Code kopiert.")
    }

    // ============ Sichern und Laden ============
    // Der Stand liegt in den App-Einstellungen und wird beim Start automatisch
    // geladen. Kein Kopieren, kein Neustart des Projekts noetig.

    func saveFurniture() {
        var rows: [[String]] = []
        for p in furnitureList {
            rows.append([p.kind, String(p.x), String(p.z), String(p.rot),
                         String(p.floor), String(Double(p.a)), String(Double(p.b)),
                         p.opt, String(p.dy), String(p.scale)])
        }
        let text = rows.map { $0.joined(separator: "|") }.joined(separator: "\n")
        UserDefaults.standard.set(text, forKey: "furniture_v2")
        say("Gesichert - bleibt auch nach dem Neustart.")
    }

    /// Gibt true zurueck, wenn ein gesicherter Stand geladen wurde.
    /// Liest v2 (mit Hoehe und Groesse), faellt auf v1 zurueck. Ein alter
    /// gesicherter Stand darf nicht verlorengehen, nur weil zwei Felder
    /// dazugekommen sind.
    @discardableResult
    func loadFurniture() -> Bool {
        let text0 = UserDefaults.standard.string(forKey: "furniture_v2")
            ?? UserDefaults.standard.string(forKey: "furniture_v1")
        guard let text = text0, !text.isEmpty else { return false }
        var loaded: [Placement] = []
        for line in text.split(separator: "\n") {
            let c = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
            guard c.count >= 8 else { continue }
            loaded.append(Placement(kind: c[0],
                                    x: Float(c[1]) ?? 0, z: Float(c[2]) ?? 0,
                                    rot: Float(c[3]) ?? 0, floor: Int(c[4]) ?? 0,
                                    a: CGFloat(Double(c[5]) ?? 0),
                                    b: CGFloat(Double(c[6]) ?? 0),
                                    opt: c[7],
                                    dy: c.count > 8 ? (Float(c[8]) ?? 0) : 0,
                                    scale: c.count > 9 ? (Float(c[9]) ?? 1) : 1))
        }
        guard !loaded.isEmpty else { return false }
        furnitureList = loaded
        return true
    }

    /// Zurueck auf den Stand, der im Code steht.
    func resetFurniture() {
        UserDefaults.standard.removeObject(forKey: "furniture_v2")
        UserDefaults.standard.removeObject(forKey: "furniture_v1")
        say("Gesicherter Stand geloescht - beim Neustart gilt wieder der Code.")
    }
}
