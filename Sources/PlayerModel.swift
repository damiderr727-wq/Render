import SceneKit
import UIKit
import simd

// Gerigte Spielerfigur, 1,78 m, facettiertes Low-Poly.
//
// Zwei Fehler aus der letzten Fassung sind hier behoben:
//  1. animate() hat frueher direkt in hip.position.y geschrieben. Das ist aber
//     die absolute Hoehe, nicht ein Versatz - die Figur sank dadurch im Stand
//     um einen ganzen Meter ein. Jetzt liegt die Ruhehoehe in hipBase und der
//     Gehzyklus addiert nur noch darauf.
//  2. flatMesh() hat Geometrie ohne Texturkoordinaten gebaut. Ein texturiertes
//     Material darauf rendert weiss - das war die "Maske" im Gesicht.
//     Jetzt gibt es eine zylindrische UV-Projektion.
//
// Masskette: Huefte 0.92, Oberschenkel 0.42, Unterschenkel 0.36,
// Knoechel 0.12, Sohlenunterkante exakt 0.00, Scheitel 1.78.

let kHipHeight: Float = 0.92
let kThigh: Float = 0.42
let kShin: Float = 0.36

// ---------- Netz mit harten Kanten ----------

/// planarUV = Projektion von vorn statt zylindrisch. Nur so sitzt eine gemalte
/// Gesichtstextur richtig auf den vorderen Polygonen - zylindrisch gewickelt
/// zieht sie sich um den ganzen Kopf.
private func flatMesh(_ tris: [(SCNVector3, SCNVector3, SCNVector3)], _ mat: SCNMaterial,
                      planarUV: Bool = false, uvW: Float = 0.22, uvH: Float = 0.26,
                      uvY: Float = 0.13) -> SCNNode {
    var verts: [SCNVector3] = []
    var norms: [SCNVector3] = []
    var uvs: [CGPoint] = []
    var idx: [Int32] = []
    for (a, b, c) in tris {
        let u = SIMD3<Float>(b.x - a.x, b.y - a.y, b.z - a.z)
        let v = SIMD3<Float>(c.x - a.x, c.y - a.y, c.z - a.z)
        var n = cross(u, v)
        let l = simd_length(n)
        if l > 1e-7 { n /= l }
        let nv = SCNVector3(n.x, n.y, n.z)
        let base = Int32(verts.count)
        for p in [a, b, c] {
            verts.append(p)
            norms.append(nv)
            // zylindrische Projektion: Winkel um die Hochachse -> u, Hoehe -> v
            if planarUV {
                uvs.append(CGPoint(x: CGFloat(p.x / uvW + 0.5),
                                   y: CGFloat(1 - (p.y + uvY) / uvH)))
            } else {
                uvs.append(CGPoint(x: CGFloat(atan2(p.x, p.z) / (2 * Float.pi) + 0.5),
                                   y: CGFloat(p.y * 2.6 + 0.5)))
            }
        }
        idx.append(base); idx.append(base + 1); idx.append(base + 2)
    }
    let g = SCNGeometry(
        sources: [SCNGeometrySource(vertices: verts),
                  SCNGeometrySource(normals: norms),
                  SCNGeometrySource(textureCoordinates: uvs)],
        elements: [SCNGeometryElement(indices: idx, primitiveType: .triangles)])
    g.firstMaterial = mat
    return SCNNode(geometry: g)
}

/// Umschaltbarer Figurenstil. false = das bisherige realistische Modell,
/// true = die cartoonige Fassung mit Fliegerhaube. Beide bleiben erhalten.
var cartoonStyle = false

/// Cartoon-Kopf: gross, rund, wenige Formen. Fliegerhaube mit Ohrenklappen und
/// hochgeschobener Brille - genau die Zeichnung. Bewusst NICHT vermessen wie
/// der realistische Kopf: hier soll die Proportion uebertrieben sein.
func cartoonHead(_ skinM: SCNMaterial, _ capM: SCNMaterial,
                 _ darkM: SCNMaterial, _ glassM: SCNMaterial) -> SCNNode {
    let holder = SCNNode()
    let n = 12
    // Kugelkopf, leicht eifoermig, deutlich groesser als am realistischen Modell
    let R: [(Float, Float, Float, Float, Float, Float)] = [
        ( 0.150, 0.052, 0.054, 0, 0, 0),
        ( 0.115, 0.112, 0.112, 0, 0, 0),
        ( 0.060, 0.140, 0.134, 0, 0, 0.10),
        ( 0.000, 0.146, 0.138, 0, 0, 0.14),
        (-0.060, 0.136, 0.130, 0, 0, 0.16),
        (-0.115, 0.104, 0.104, 0, 0, 0.12),
        (-0.155, 0.052, 0.058, 0, 0, 0),
    ]
    func pt(_ r: (Float, Float, Float, Float, Float, Float), _ i: Int) -> SCNVector3 {
        ringPoint(r.0, r.1, r.2, r.3, i, n, r.4, r.5)
    }
    var tris: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for k in 0..<(R.count - 1) {
        for i in 0..<n {
            let j = (i + 1) % n
            tris.append((pt(R[k], i), pt(R[k+1], j), pt(R[k+1], i)))
            tris.append((pt(R[k], i), pt(R[k], j), pt(R[k+1], j)))
        }
    }
    let top = SCNVector3(0, 0.168, 0), bot = SCNVector3(0, -0.172, 0)
    for i in 0..<n {
        let j = (i + 1) % n
        tris.append((top, pt(R[0], j), pt(R[0], i)))
        tris.append((bot, pt(R[R.count-1], i), pt(R[R.count-1], j)))
    }
    holder.addChildNode(flatMesh(tris, skinM))

    // Grosse einfache Augen: weisses Oval, dicke dunkle Pupille
    for sg in [-1, 1] {
        let ex = Float(sg) * 0.055, ey: Float = -0.005, ez: Float = 0.132
        let w: Float = 0.036, hh: Float = 0.044
        let q = [SCNVector3(ex-w, ey+hh, ez), SCNVector3(ex+w, ey+hh, ez),
                 SCNVector3(ex+w, ey-hh, ez), SCNVector3(ex-w, ey-hh, ez)]
        holder.addChildNode(flatMesh([(q[0], q[2], q[1]), (q[0], q[3], q[2])],
                                     mat(UIColor(white: 0.96, alpha: 1))))
        let pp: Float = 0.019, pz = ez + 0.004
        let r2 = [SCNVector3(ex-pp, ey+pp*1.3, pz), SCNVector3(ex+pp, ey+pp*1.3, pz),
                  SCNVector3(ex+pp, ey-pp*1.3, pz), SCNVector3(ex-pp, ey-pp*1.3, pz)]
        holder.addChildNode(flatMesh([(r2[0], r2[2], r2[1]), (r2[0], r2[3], r2[2])], darkM))
        // Braue als dicker Strich
        let bw: Float = 0.040
        let b = [SCNVector3(ex-bw, 0.058, ez), SCNVector3(ex+bw, 0.064, ez),
                 SCNVector3(ex+bw, 0.046, ez), SCNVector3(ex-bw, 0.040, ez)]
        holder.addChildNode(flatMesh([(b[0], b[2], b[1]), (b[0], b[3], b[2])], darkM))
    }
    // Kleine Nase und Mund
    let nt = SCNVector3(0, -0.052, 0.158)
    holder.addChildNode(flatMesh([
        (SCNVector3(-0.014, -0.020, 0.138), nt, SCNVector3(0.014, -0.020, 0.138)),
        (SCNVector3(-0.014, -0.076, 0.136), SCNVector3(0.014, -0.076, 0.136), nt)], skinM))
    let mq = [SCNVector3(-0.030, -0.104, 0.128), SCNVector3(0.030, -0.104, 0.128),
              SCNVector3(0.024, -0.118, 0.128), SCNVector3(-0.024, -0.118, 0.128)]
    holder.addChildNode(flatMesh([(mq[0], mq[2], mq[1]), (mq[0], mq[3], mq[2])], darkM))

    // Fliegerhaube: Kappe ueber den Schaedel, Ohrenklappen an den Seiten
    let cap = SCNSphere(radius: 0.152); cap.segmentCount = 12
    cap.firstMaterial = capM
    let cn = SCNNode(geometry: cap)
    cn.position = SCNVector3(0, 0.030, -0.004)
    cn.scale = SCNVector3(1.0, 0.98, 1.0)
    holder.addChildNode(cn)
    // Stirnkante der Haube - laesst das Gesicht frei
    let br = SCNTorus(ringRadius: 0.140, pipeRadius: 0.020)
    br.ringSegmentCount = 14; br.pipeSegmentCount = 6; br.firstMaterial = capM
    let brn = SCNNode(geometry: br)
    brn.position = SCNVector3(0, 0.052, 0.004)
    brn.eulerAngles.x = 0.20
    holder.addChildNode(brn)
    for sg in [-1, 1] {
        let fl = SCNSphere(radius: 0.062); fl.segmentCount = 8
        fl.firstMaterial = capM
        let fn = SCNNode(geometry: fl)
        fn.position = SCNVector3(Float(sg) * 0.140, -0.048, 0.006)
        fn.scale = SCNVector3(0.55, 1.25, 1.0)
        holder.addChildNode(fn)
    }
    // Brille hochgeschoben auf die Haube: Band plus zwei Glaeser
    let strap = SCNTorus(ringRadius: 0.142, pipeRadius: 0.014)
    strap.ringSegmentCount = 14; strap.pipeSegmentCount = 5; strap.firstMaterial = darkM
    let sn2 = SCNNode(geometry: strap)
    sn2.position = SCNVector3(0, 0.096, -0.006)
    sn2.eulerAngles.x = 0.38
    holder.addChildNode(sn2)
    for sg in [-1, 1] {
        let g = SCNCylinder(radius: 0.040, height: 0.030)
        g.radialSegmentCount = 10; g.firstMaterial = glassM
        let gn = SCNNode(geometry: g)
        gn.position = SCNVector3(Float(sg) * 0.052, 0.126, 0.048)
        gn.eulerAngles = SCNVector3(1.15, 0, 0)
        holder.addChildNode(gn)
        let rim = SCNTorus(ringRadius: 0.042, pipeRadius: 0.010)
        rim.ringSegmentCount = 10; rim.pipeSegmentCount = 4; rim.firstMaterial = darkM
        let rn = SCNNode(geometry: rim)
        rn.position = SCNVector3(Float(sg) * 0.052, 0.126, 0.048)
        rn.eulerAngles = SCNVector3(1.15, 0, 0)
        holder.addChildNode(rn)
    }
    return holder
}

/// Ringpunkt mit zwei Formreglern:
///   frontPull schiebt den vordersten Punkt heraus (Braue, Kinn)
///   flatFront drueckt die Vorderseite flach - ein Gesicht ist keine Kugel
private func ringPoint(_ y: Float, _ rx: Float, _ rz: Float, _ zOff: Float,
                       _ i: Int, _ n: Int, _ frontPull: Float = 0, _ flatFront: Float = 0) -> SCNVector3 {
    let a = Float(i) / Float(n) * 2 * Float.pi
    let sn = sin(a), cs = cos(a)
    var fz = rz
    if cs > 0 { fz = rz * (1 - flatFront * cs) }
    return SCNVector3(sn * rx, y, cs * fz + zOff + (i == 0 ? frontPull : 0))
}

/// Ringnetz aus beliebigen Querschnitten - fuer Rumpf und Gliedmassen.
/// capTop/capBot schliessen die Enden. Sie standen an Armen, Beinen und Hals
/// auf false, weil dort eine Kugel (Schulter, Knie, Ellbogen) daruebersitzt -
/// die deckt das offene Ende aber nicht zuverlaessig ab. Die Schulterkappe
/// liegt zum Beispiel bei x 0.158, die Armroehre bei x 0.180 und ist breiter
/// als die Kappe: rund 1.5 cm des offenen Rohrs standen frei. Von der Seite
/// sieht man dann in den Koerper hinein - genau die gemeldeten "nicht
/// ausgefuellten Stellen". Ein Deckel kostet n Dreiecke, das ist nichts.
private func tubeMesh(_ rings: [(Float, Float, Float)], _ mat: SCNMaterial,
                      _ n: Int = 7, capTop: Bool = true, capBot: Bool = true) -> SCNNode {
    var tris: [(SCNVector3, SCNVector3, SCNVector3)] = []
    func pt(_ r: (Float, Float, Float), _ i: Int) -> SCNVector3 {
        let a = Float(i) / Float(n) * 2 * Float.pi
        return SCNVector3(sin(a) * r.1, r.0, cos(a) * r.2)
    }
    for k in 0..<(rings.count - 1) {
        for i in 0..<n {
            let j = (i + 1) % n
            // Wicklung gegen den Uhrzeigersinn von aussen - SceneKit cullt sonst
            // die Vorderseite und man blickt in den Koerper hinein. Genau das
            // war das "Invertierte": von vorn sah man den Ruecken.
            tris.append((pt(rings[k], i), pt(rings[k+1], j), pt(rings[k+1], i)))
            tris.append((pt(rings[k], i), pt(rings[k], j), pt(rings[k+1], j)))
        }
    }
    if capTop {
        let t = SCNVector3(0, rings[rings.count - 1].0 + 0.012, 0)
        for i in 0..<n { tris.append((t, pt(rings[rings.count-1], i), pt(rings[rings.count-1], (i+1)%n))) }
    }
    if capBot {
        let b = SCNVector3(0, rings[0].0 - 0.012, 0)
        for i in 0..<n { tris.append((b, pt(rings[0], (i+1)%n), pt(rings[0], i))) }
    }
    return flatMesh(tris, mat)
}

/// Rumpf: schmale Taille, breiter Brustkorb, abfallende Schulter.
private func torsoMesh(_ mat: SCNMaterial) -> SCNNode {
    tubeMesh([(0.000, 0.104, 0.078),   // Taille, schmalste Stelle
              (0.105, 0.132, 0.094),   // untere Rippen
              (0.230, 0.176, 0.114),   // Brustkorb
              (0.330, 0.196, 0.112),   // obere Brust
              (0.408, 0.205, 0.100),   // Schulterlinie, breiteste Stelle
              (0.452, 0.094, 0.080)],  // Halsansatz
             mat, 8)
}

/// Kopf. Diese Ringe wurden vor der Uebersetzung in Python vermessen:
/// Nase projiziert 2,4 cm ueber die Braue (real 2-3), Kinn ist 28 % der
/// Schlaefenbreite, Haar liegt 6 mm ueber dem Schaedel.
private func headMesh(_ mat: SCNMaterial, _ hairM: SCNMaterial,
                      _ dark: SCNMaterial, _ white: SCNMaterial) -> SCNNode {
    let n = 12
    // (y, rx, rz, zOff, frontPull, flatFront)
    let R: [(Float, Float, Float, Float, Float, Float)] = [
        ( 0.118, 0.036, 0.040, -0.004, 0,     0    ),   // Scheitel
        ( 0.092, 0.070, 0.078, -0.002, 0,     0.18 ),
        ( 0.052, 0.082, 0.090,  0.000, 0,     0.22 ),   // Schlaefe, breiteste Stelle
        ( 0.020, 0.086, 0.092,  0.002, 0.006, 0.24 ),   // Braue
        (-0.020, 0.080, 0.089,  0.004, 0,     0.26 ),   // Wangenknochen
        (-0.058, 0.065, 0.080,  0.006, 0,     0.24 ),   // Wange
        (-0.090, 0.044, 0.061,  0.008, 0.004, 0.18 ),   // Kiefer
        (-0.112, 0.026, 0.038,  0.010, 0,     0    ),   // Kinn
    ]
    func pt(_ r: (Float, Float, Float, Float, Float, Float), _ i: Int) -> SCNVector3 {
        ringPoint(r.0, r.1, r.2, r.3, i, n, r.4, r.5)
    }
    var tris: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for k in 0..<(R.count - 1) {
        for i in 0..<n {
            let j = (i + 1) % n
            tris.append((pt(R[k], i), pt(R[k+1], j), pt(R[k+1], i)))
            tris.append((pt(R[k], i), pt(R[k], j), pt(R[k+1], j)))
        }
    }
    let top = SCNVector3(0, 0.130, -0.004)
    let bot = SCNVector3(0, -0.124, 0.010)
    for i in 0..<n {
        let j = (i + 1) % n
        tris.append((top, pt(R[0], j), pt(R[0], i)))
        tris.append((bot, pt(R[R.count-1], i), pt(R[R.count-1], j)))
    }
    // Die abgeflachte Vorderseite liegt viel weiter hinten als der reine
    // Radius: bei flatFront 0.30 sind das ueber 2 cm. Augen, Brauen und Mund
    // lagen deshalb frei vor dem Gesicht in der Luft - genau das "Schweben".
    // surfaceZ rechnet die tatsaechliche Oberflaeche aus.
    func surfaceZ(_ yy: Float, _ xx: Float) -> Float {
        var lo = R[R.count - 1], hi = R[0]
        for k in 0..<(R.count - 1) where yy <= R[k].0 && yy >= R[k+1].0 {
            hi = R[k]; lo = R[k+1]; break
        }
        let span = hi.0 - lo.0
        let t = abs(span) < 1e-5 ? 0 : (yy - lo.0) / span
        let rxx = lo.1 + (hi.1 - lo.1) * t
        let rzz = lo.2 + (hi.2 - lo.2) * t
        let zoo = lo.3 + (hi.3 - lo.3) * t
        let ff  = lo.5 + (hi.5 - lo.5) * t
        let sn = max(-0.999, min(0.999, xx / max(0.001, rxx)))
        let cs = (1 - sn * sn).squareRoot()
        return rzz * (1 - ff * cs) * cs + zoo
    }

    // Die Gesichtstextur wird planar auf die VORDEREN Dreiecke des Kopfnetzes
    // projiziert - sie zieht sich damit ueber Braue, Wange und Kinn, statt als
    // flaches Viereck davorzukleben. Hinterkopf bleibt einfarbige Haut.
    var faceTris: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for t in tris {
        let cz = (t.0.z + t.1.z + t.2.z) / 3
        let cy = (t.0.y + t.1.y + t.2.y) / 3
        if cz > 0.012 && cy < 0.105 && cy > -0.118 { faceTris.append(t) }
    }
    let faceM = SCNMaterial()
    faceM.lightingModel = .lambert
    faceM.diffuse.contents = Tex.face
    faceM.diffuse.wrapS = .clamp
    faceM.diffuse.wrapT = .clamp
    // linear statt nearest: harte Pixelkanten liessen die Textur wie ein
    // aufgeklebtes Bild wirken statt wie ein gemaltes Gesicht.
    faceM.diffuse.magnificationFilter = .linear

    let holder = SCNNode()
    // WICHTIG: der Schaedel wird VOLLSTAENDIG gebaut, nicht nur die Rueckseite.
    // Vorher fehlten dem Kopf genau die Dreiecke, die zur Gesichtsschale gehoerten -
    // an jeder Kante dazwischen sah man ins Innere und damit auf den Hinterkopf.
    holder.addChildNode(flatMesh(tris, mat))
    // Die Gesichtsschale liegt als zweite Lage 3 mm DAVOR, entlang der eigenen
    // Flaechennormale versetzt. So kann nie eine Luecke entstehen.
    var faceShell: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for t in faceTris {
        let ux = t.1.x - t.0.x, uy = t.1.y - t.0.y, uz = t.1.z - t.0.z
        let vx = t.2.x - t.0.x, vy = t.2.y - t.0.y, vz = t.2.z - t.0.z
        var nx = uy * vz - uz * vy
        var ny = uz * vx - ux * vz
        var nz = ux * vy - uy * vx
        let l = max(1e-6, (nx*nx + ny*ny + nz*nz).squareRoot())
        nx /= l; ny /= l; nz /= l
        let o: Float = 0.003
        faceShell.append((SCNVector3(t.0.x + nx*o, t.0.y + ny*o, t.0.z + nz*o),
                          SCNVector3(t.1.x + nx*o, t.1.y + ny*o, t.1.z + nz*o),
                          SCNVector3(t.2.x + nx*o, t.2.y + ny*o, t.2.z + nz*o)))
    }
    // uvW/uvH/uvY aus den Ringmassen: x +-0.086 -> u 0.07..0.93,
    // y -0.116..0.118 -> v 0..1. Augen der Textur landen so auf Brauenhoehe.
    holder.addChildNode(flatMesh(faceShell, faceM,
                                 planarUV: true, uvW: 0.20, uvH: 0.220, uvY: 0.115))

    // Nase als schmaler Keil, Spitze 2,4 cm vor der Braue
    let br = SCNVector3(0, 0.030, surfaceZ(0.030, 0) - 0.004)
    let tip = SCNVector3(0, -0.024, surfaceZ(-0.024, 0) + 0.036)
    let nl = SCNVector3(-0.020, -0.040, surfaceZ(-0.040, -0.020) - 0.002)
    let nr = SCNVector3(0.020, -0.040, surfaceZ(-0.040, 0.020) - 0.002)
    holder.addChildNode(flatMesh([(br, nl, tip), (br, tip, nr), (tip, nl, nr)], mat))

    // (Die aufgeklebten Textur-Vierecke sind entfallen - die Textur sitzt
    //  jetzt direkt auf dem Kopfnetz.)

    // Haar ist auf dieser Aufloesung als Flaeche nie gut geworden - es
    // bleibt beim Nackenkranz weiter unten plus Koteletten am Schaedel.

    // Nacken: nur die hinteren Flaechen
    let N: [(Float, Float, Float, Float, Float, Float)] = [
        (-0.070, 0.062, 0.050, -0.036, 0, 0),
        ( 0.020, 0.086, 0.062, -0.032, 0, 0),
        ( 0.060, 0.088, 0.066, -0.028, 0, 0),
    ]
    var nt: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for k in 0..<(N.count - 1) {
        for i in 0..<n {
            let j = (i + 1) % n
            let quad = [(pt(N[k], i), pt(N[k+1], j), pt(N[k+1], i)),
                        (pt(N[k], i), pt(N[k], j), pt(N[k+1], j))]
            for q in quad where (q.0.z + q.1.z + q.2.z) / 3 < -0.02 { nt.append(q) }
        }
    }
    holder.addChildNode(flatMesh(nt, hairM))
    return holder
}

final class PlayerRig {
    let root = SCNNode()
    let hip = SCNNode()
    let torso = SCNNode()
    let neck = SCNNode()
    var shoulderL = SCNNode(), shoulderR = SCNNode()
    var elbowL = SCNNode(), elbowR = SCNNode()
    var thighL = SCNNode(), thighR = SCNNode()
    var kneeL = SCNNode(), kneeR = SCNNode()

    /// Ruhehoehe der Huefte. Der Gehzyklus rechnet nur noch Versatz darauf.
    var hipBase: Float = kHipHeight
    private var phase: Float = 0
    /// Schlagfortschritt, -1 = kein Schlag. crowbar haengt am rechten Ellbogen.
    var swingT: Float = -1
    var crowbar: SCNNode?

    var handLantern: SCNNode?
    func setCrowbar(visible: Bool) { crowbar?.isHidden = !visible }
    func setLantern(visible: Bool) { handLantern?.isHidden = !visible }
    func startSwing() { if swingT < 0 { swingT = 0 } }

    private func ease(_ n: SCNNode, _ target: Float, _ k: Float) {
        n.eulerAngles.x += (target - n.eulerAngles.x) * k
    }

    func animate(dt: Float, speed: Float) {
        let amt = min(1, speed / 2.8)
        let k = min(1, 12 * dt)
        // Der Zyklus laeuft jetzt nach zurueckgelegter STRECKE, nicht nach Zeit.
        // Vermessen an der Beinkette (Huefte 0.42 + Unterschenkel 0.465, Ausschlag
        // 0.58 rad): die Beinkette ist aber 0.90 m lang, nicht 0.78 - der
        // Knoechel bis zur Sohle war vergessen. Schritt also 0.99 m statt
        // 0.84 m, 1.97 m je voller Phase -> Faktor 3.18 statt 3.73. Mit 3.73
        // drehte sich der Zyklus 18 % zu schnell, und die Fuesse rutschten.
        // Da die Amplitude mit amt skaliert, skaliert die Schrittlaenge mit -
        // deshalb durch amt teilen. Vorher lief der Zyklus mit fester Rate weiter
        // und die Fuesse rutschten ueber den Boden.
        if amt > 0.05 {
            phase += dt * speed * 3.18 / amt
        }
        let s = sin(phase), c = cos(phase)
        var bob: Float = 0

        if amt > 0.05 {
            ease(thighL, -s * 0.58 * amt, k)
            ease(thighR, s * 0.58 * amt, k)
            // KONVENTION, einmal sauber: positive x-Rotation schwingt ein
            // haengendes Glied nach HINTEN (-z), negative nach vorn (+z).
            // thighL steht auf -s * 0.58, also ist Bein L bei s = +1 VORN.
            // Das Knie beugt im Vorwaertsschwung -> links max(0, s).
            // Mein voriger "Fix" hatte genau das Vorzeichen verwechselt.
            ease(kneeL, (0.08 + 0.60 * max(0, s)) * amt, k)
            ease(kneeR, (0.08 + 0.60 * max(0, -s)) * amt, k)
            ease(shoulderL, s * 0.40 * amt, k)
            ease(shoulderR, -s * 0.40 * amt, k)
            ease(elbowL, -(0.20 + 0.24 * (1 + s)) * amt, k)
            ease(elbowR, -(0.20 + 0.24 * (1 - s)) * amt, k)
            bob = abs(s) * 0.032 * amt
            torso.eulerAngles.z += (c * 0.045 * amt - torso.eulerAngles.z) * k
            ease(torso, 0.06 * amt, k)
            ease(neck, -0.04 * amt, k)
        } else {
            let b = sin(phase * 0.55)
            ease(thighL, 0, k); ease(thighR, 0, k)
            ease(kneeL, 0.03, k); ease(kneeR, 0.03, k)
            ease(shoulderL, 0.05 + b * 0.02, k)
            ease(shoulderR, 0.05 - b * 0.02, k)
            ease(elbowL, -0.16, k); ease(elbowR, -0.16, k)
            bob = abs(b) * 0.005
            torso.eulerAngles.z += (0 - torso.eulerAngles.z) * k
            ease(torso, b * 0.010, k)
            ease(neck, 0, k)
        }
        // Versatz auf die Ruhehoehe, nicht als absolute Position
        // Schlag ueberlagert den rechten Arm: ausholen, dann herabziehen
        if swingT >= 0 {
            swingT += dt
            let p = swingT / 0.45
            if p >= 1 { swingT = -1 }
            else {
                let lift: Float = p < 0.42 ? (p / 0.42) : max(0, 1 - (p - 0.42) / 0.30)
                shoulderR.eulerAngles.x = -2.1 * lift + 0.7 * max(0, (p - 0.42) / 0.58)
                elbowR.eulerAngles.x = -0.5 - 0.9 * lift
            }
        }
        // Natuerlicher: der Oberkoerper dreht dem Schritt leicht entgegen,
        // die Huefte pendelt seitlich mit.
        torso.eulerAngles.y += ((s * 0.05 * amt) - torso.eulerAngles.y) * k
        hip.position.x += ((c * 0.018 * amt) - hip.position.x) * k
        hip.position.y += (hipBase + bob - hip.position.y) * k
    }
}

private func mat(_ c: UIColor) -> SCNMaterial {
    let m = SCNMaterial()
    m.lightingModel = .lambert
    m.diffuse.contents = c
    return m
}


private func chunk(_ parent: SCNNode, _ w: CGFloat, _ h: CGFloat, _ d: CGFloat,
                   _ x: Float, _ y: Float, _ z: Float, _ m: SCNMaterial,
                   _ ch: CGFloat = 0.012, _ euler: SCNVector3? = nil) {
    let g = SCNBox(width: w, height: h, length: d, chamferRadius: ch)
    g.firstMaterial = m
    let n = SCNNode(geometry: g); n.position = SCNVector3(x, y, z)
    if let e = euler { n.eulerAngles = e }
    parent.addChildNode(n)
}

func makePlayerRig() -> PlayerRig {
    let r = PlayerRig()

    let skinCol = UIColor(red: 0.74, green: 0.57, blue: 0.46, alpha: 1)
    let skin = mat(skinCol)
    let skinTex = texMat(Tex.skin, 1, 1)
    let shirt = texMat(Tex.clothShirt, 3, 3)
    let vest = texMat(Tex.clothVest, 3, 3)
    let pad = texMat(Tex.clothVest, 2, 2)
    let pants = texMat(Tex.clothPants, 3, 3)
    let belt = texMat(Tex.leather, 2, 2)
    let boot = texMat(Tex.leather, 2, 2)
    let hairM = texMat(Tex.hair, 1, 1)
    let beret = texMat(Tex.felt, 2, 2)
    let dark = mat(UIColor(red: 0.09, green: 0.07, blue: 0.06, alpha: 1))

    // ---- Huefte ----
    r.hipBase = kHipHeight
    r.hip.position = SCNVector3(0, kHipHeight, 0)
    r.root.addChildNode(r.hip)
    chunk(r.hip, 0.248, 0.19, 0.186, 0, 0.02, 0, pants, 0.05)
    chunk(r.hip, 0.268, 0.068, 0.198, 0, 0.110, 0, belt)
    chunk(r.hip, 0.082, 0.105, 0.058, -0.134, 0.048, 0.086, belt)
    chunk(r.hip, 0.082, 0.105, 0.058, 0.134, 0.048, 0.086, belt)

    // ---- Beine ----
    for side in [-1, 1] {
        let sx = Float(side) * 0.092
        let thigh = SCNNode(); thigh.position = SCNVector3(sx, -0.02, 0); r.hip.addChildNode(thigh)
        let thighMesh = tubeMesh([(-kThigh, 0.056, 0.060), (-kThigh*0.55, 0.068, 0.074),
                                  (-kThigh*0.18, 0.082, 0.088), (0.01, 0.090, 0.094)],
                                 pants, 7, capTop: true)
        thigh.addChildNode(thighMesh)
        let knee = SCNNode(); knee.position = SCNVector3(0, -kThigh, 0); thigh.addChildNode(knee)
        let kneeCap = SCNSphere(radius: 0.054); kneeCap.segmentCount = 7
        kneeCap.firstMaterial = pants
        let kc = SCNNode(geometry: kneeCap); kc.position = SCNVector3(0, -0.005, 0.006)
        kc.scale = SCNVector3(1.06, 0.86, 1.06); knee.addChildNode(kc)
        // Wadenbauch: oben duenn, in der Mitte dicker, zum Knoechel schlank
        let shinMesh = tubeMesh([(-kShin, 0.040, 0.044), (-kShin*0.62, 0.052, 0.058),
                                 (-kShin*0.30, 0.061, 0.070), (0.0, 0.056, 0.060)],
                                pants, 7, capTop: true)
        knee.addChildNode(shinMesh)
        chunk(knee, 0.128, 0.20, 0.140, 0, -0.250, 0, boot, 0.05)     // Hosenbein/Schaft

        // Schuh aus Querschnitten laengs des Fusses: Fersenkappe, Rist, breite
        // Ballenpartie, verjuengte runde Spitze. Vorher waren das zwei Kloetze
        // plus eine Kugel - deshalb sah es aus wie ein Bauklotz.
        // (z, Halbbreite, Hoehe ueber der Sohle)
        let shoe: [(Float, Float, Float)] = [
            (-0.082, 0.040, 0.070),   // Fersenkappe hinten
            (-0.048, 0.055, 0.092),   // Ferse, hoechster Punkt
            (-0.004, 0.062, 0.086),   // Knoechel/Rist
            ( 0.048, 0.065, 0.070),   // Ballen, breiteste Stelle
            ( 0.108, 0.060, 0.055),
            ( 0.158, 0.046, 0.038),
            ( 0.194, 0.024, 0.020),   // Spitze
        ]
        let sn2 = 8
        let footY: Float = -0.478                                     // Sohlenunterkante
        func shoePt(_ si: Int, _ i: Int, _ grow: Float = 0) -> SCNVector3 {
            let a = Float(i) / Float(sn2) * 2 * Float.pi
            let w = shoe[si].1 + grow, h = shoe[si].2 + grow
            let yy = h * 0.5 + h * 0.5 * cos(a)
            return SCNVector3(sin(a) * w, footY + max(0.004, yy), shoe[si].0)
        }
        var shoeTris: [(SCNVector3, SCNVector3, SCNVector3)] = []
        for si in 0..<(shoe.count - 1) {
            for i in 0..<sn2 {
                let j = (i + 1) % sn2
                shoeTris.append((shoePt(si, i), shoePt(si + 1, j), shoePt(si + 1, i)))
                shoeTris.append((shoePt(si, i), shoePt(si, j), shoePt(si + 1, j)))
            }
        }
        let heelC = SCNVector3(0, footY + 0.035, shoe[0].0 - 0.012)
        let toeC = SCNVector3(0, footY + 0.012, shoe[shoe.count - 1].0 + 0.010)
        for i in 0..<sn2 {
            let j = (i + 1) % sn2
            shoeTris.append((heelC, shoePt(0, i), shoePt(0, j)))
            shoeTris.append((toeC, shoePt(shoe.count - 1, j), shoePt(shoe.count - 1, i)))
        }
        knee.addChildNode(flatMesh(shoeTris, boot))

        // Sohle als flacher dunkler Rand rundherum, Absatz hinten
        var soleTris: [(SCNVector3, SCNVector3, SCNVector3)] = []
        for si in 0..<(shoe.count - 1) {
            for i in 0..<sn2 {
                let j = (i + 1) % sn2
                let a0 = shoePt(si, i, 0.006), a1 = shoePt(si, j, 0.006)
                let b0 = shoePt(si + 1, i, 0.006), b1 = shoePt(si + 1, j, 0.006)
                let f0 = SCNVector3(a0.x, footY - 0.014, a0.z), f1 = SCNVector3(a1.x, footY - 0.014, a1.z)
                let g0 = SCNVector3(b0.x, footY - 0.014, b0.z), g1 = SCNVector3(b1.x, footY - 0.014, b1.z)
                if a0.y < footY + 0.026 {
                    soleTris.append((f0, g1, g0)); soleTris.append((f0, f1, g1))
                }
                _ = (a0, a1, b0, b1)
            }
        }
        knee.addChildNode(flatMesh(soleTris, dark))
        chunk(knee, 0.118, 0.030, 0.088, 0, footY - 0.006, -0.052, dark, 0.010)  // Absatz
        if side < 0 { r.thighL = thigh; r.kneeL = knee } else { r.thighR = thigh; r.kneeR = knee }
    }

    // ---- Torso ----
    r.torso.position = SCNVector3(0, 0.09, 0)
    r.hip.addChildNode(r.torso)
    let tm = torsoMesh(shirt)
    tm.position = SCNVector3(0, 0.02, 0)
    r.torso.addChildNode(tm)
    // Weste als zweite, minimal groessere Huelle darueber
    let vm = torsoMesh(vest)
    vm.position = SCNVector3(0, 0.055, 0)
    vm.scale = SCNVector3(1.045, 0.80, 1.055)
    r.torso.addChildNode(vm)
    // Schulterpartie als flache Kappe, die auf dem Rumpf aufliegt statt als
    // Kugel danebenzustehen. Die 14-cm-Baelle davor waren der Grund, warum die
    // Figur wie eine Marionette aussah.
    for sg in [-1, 1] {
        let cap = SCNSphere(radius: 0.052); cap.segmentCount = 7; cap.firstMaterial = pad
        let cn = SCNNode(geometry: cap)
        cn.position = SCNVector3(Float(sg) * 0.158, 0.392, 0)
        cn.scale = SCNVector3(1.18, 0.52, 1.10)
        r.torso.addChildNode(cn)
    }

    // ---- Arme ----
    for side in [-1, 1] {
        let sx = Float(side) * 0.180
        let sh = SCNNode(); sh.position = SCNVector3(sx, 0.385, 0); r.torso.addChildNode(sh)
        sh.addChildNode(tubeMesh([(-0.275, 0.041, 0.043), (-0.155, 0.050, 0.053),
                                  (-0.060, 0.058, 0.061), (0.0, 0.054, 0.057)],
                                 shirt, 7, capTop: true))
        let el = SCNNode(); el.position = SCNVector3(0, -0.275, 0); sh.addChildNode(el)
        let elbowCap = SCNSphere(radius: 0.042); elbowCap.segmentCount = 7
        elbowCap.firstMaterial = shirt
        el.addChildNode(SCNNode(geometry: elbowCap))
        el.addChildNode(tubeMesh([(-0.245, 0.031, 0.033), (-0.130, 0.038, 0.041),
                                  (-0.045, 0.045, 0.047), (0.0, 0.042, 0.044)],
                                 skinTex, 7, capTop: true))
        chunk(el, 0.082, 0.125, 0.096, 0, -0.290, 0.008, belt, 0.03)
        // Brecheisen, standardmaessig verborgen - sichtbar beim Ausruesten
        if sx > 0 {
            let ir = SCNMaterial(); ir.lightingModel = .lambert
            ir.diffuse.contents = UIColor(red: 0.16, green: 0.15, blue: 0.16, alpha: 1)
            let cb = SCNNode()
            let shaft = SCNCylinder(radius: 0.016, height: 0.52)
            shaft.radialSegmentCount = 6; shaft.firstMaterial = ir
            let sh2 = SCNNode(geometry: shaft)
            sh2.position = SCNVector3(0, -0.20, 0.05)
            sh2.eulerAngles.x = 0.35
            cb.addChildNode(sh2)
            let hook = SCNTorus(ringRadius: 0.045, pipeRadius: 0.014)
            hook.ringSegmentCount = 8; hook.pipeSegmentCount = 5; hook.firstMaterial = ir
            let hn = SCNNode(geometry: hook)
            hn.position = SCNVector3(0, -0.44, 0.135)
            hn.eulerAngles = SCNVector3(Float.pi / 2, 0, 0)
            cb.addChildNode(hn)
            cb.isHidden = true
            el.addChildNode(cb)
            r.crowbar = cb
        } else {
            // Getragene Laterne am linken Arm, sichtbar sobald sie brennt
            let brM = SCNMaterial(); brM.lightingModel = .lambert
            brM.diffuse.contents = UIColor(red: 0.55, green: 0.45, blue: 0.22, alpha: 1)
            let ln = SCNNode()
            let gl = SCNCylinder(radius: 0.052, height: 0.11)
            gl.radialSegmentCount = 7
            let gm2 = SCNMaterial(); gm2.lightingModel = .constant
            gm2.diffuse.contents = Tex.lanternGlass
            gm2.emission.contents = Tex.lanternGlass
            gm2.emission.intensity = 1.2
            gl.firstMaterial = gm2
            ln.addChildNode(SCNNode(geometry: gl))
            for yy2 in [Float(-0.065), 0.07] {
                let cap = SCNCylinder(radius: 0.060, height: 0.022)
                cap.radialSegmentCount = 7; cap.firstMaterial = brM
                let cn2 = SCNNode(geometry: cap)
                cn2.position = SCNVector3(0, yy2, 0)
                ln.addChildNode(cn2)
            }
            ln.position = SCNVector3(0, -0.33, 0.05)
            ln.isHidden = true
            el.addChildNode(ln)
            r.handLantern = ln
        }
        if side < 0 { r.shoulderL = sh; r.elbowL = el } else { r.shoulderR = sh; r.elbowR = el }
    }

    // ---- Hals ----
    r.neck.position = SCNVector3(0, 0.460, 0)
    r.torso.addChildNode(r.neck)
    let nk = SCNCylinder(radius: 0.050, height: 0.10)
    nk.radialSegmentCount = 8; nk.firstMaterial = skin
    let nkn = SCNNode(geometry: nk); nkn.position = SCNVector3(0, 0.035, 0)
    r.neck.addChildNode(nkn)

    // ---- Kopf ----
    let head = SCNNode(); head.position = SCNVector3(0, 0.170, 0)
    r.neck.addChildNode(head)
    if cartoonStyle {
        // Cartoon: grosser Kopf, Fliegerhaube. Der Rumpf bleibt derselbe, wird
        // aber schmaler skaliert, damit der Kopf gross wirkt.
        let capM = mat(UIColor(red: 0.34, green: 0.26, blue: 0.18, alpha: 1))
        let glassM = SCNMaterial()
        glassM.lightingModel = .lambert
        glassM.diffuse.contents = UIColor(red: 0.62, green: 0.74, blue: 0.72, alpha: 1)
        glassM.transparency = 0.62
        head.addChildNode(cartoonHead(mat(UIColor(red: 0.96, green: 0.80, blue: 0.66, alpha: 1)),
                                      capM, dark, glassM))
        head.scale = SCNVector3(1.05, 1.05, 1.05)
        r.torso.scale = SCNVector3(0.90, 0.94, 0.90)
    } else {
        head.addChildNode(headMesh(skin, hairM, dark, mat(UIColor(red: 0.70, green: 0.67, blue: 0.62, alpha: 1))))
    }
    chunk(head, 0.015, 0.048, 0.033, 0.088, -0.008, -0.006, skin, 0.005, SCNVector3(0, 0, -0.12))

    // Haar aus gekippten Keilen

    // Barett sitzt AUF dem Schaedel (Scheitel 0.118) statt darueber zu
    // schweben, leicht nach rechts gezogen; Rand als flacher Wulst darunter.
    if !cartoonStyle {
        // Muetze als gedrueckte Kugel: schmiegt sich an den Schaedel, statt als
        // Zylinder darueber zu schweben. Kleiner Schirm vorn, Knopf oben.
        let capS = SCNSphere(radius: 0.128); capS.segmentCount = 10
        capS.firstMaterial = beret
        let capN = SCNNode(geometry: capS)
        capN.position = SCNVector3(0.008, 0.078, -0.006)
        capN.scale = SCNVector3(1.0, 0.44, 1.05)
        capN.eulerAngles = SCNVector3(0.06, 0.2, 0.10)
        head.addChildNode(capN)
        chunk(head, 0.085, 0.014, 0.052, 0.004, 0.086, 0.088, beret, 0.006, SCNVector3(-0.28, 0, 0))
        chunk(head, 0.026, 0.020, 0.026, 0.046, 0.136, -0.004, beret, 0.008)
        // Koteletten - das restliche sichtbare Haar unter der Muetze
        chunk(head, 0.014, 0.050, 0.030, -0.082, -0.004, 0.014, hairM, 0.006)
        chunk(head, 0.014, 0.050, 0.030, 0.082, -0.004, 0.014, hairM, 0.006)
    }

    return r
}


// ===================== Der Schlaefer =====================
// Dauerschlafkur-Patient. Das Unheimliche kommt nicht aus einem Monsterdesign,
// sondern aus falschem Verhalten: er gleitet zu glatt (das Nachthemd verdeckt
// die Beine, es gibt keine Schritte), der Kopf haengt schief und verfolgt den
// Spieler unabhaengig vom Koerper, die Augen sind geschlossen - und wenn er
// jemanden hoert, schnappt die Drehung OHNE Uebergang um.
final class Sleeper {
    let root = SCNNode()
    let body = SCNNode()
    let headPivot = SCNNode()
    private let gown: SCNNode
    private let armL: SCNNode
    private let armR: SCNNode

    // Revier: er verlaesst seinen Flur nie
    let minX: Float, maxX: Float, minZ: Float, maxZ: Float
    let baseY: Float
    private var target: SIMD2<Float>
    private var t: Float = 0
    private var staringFor: Float = 0
    private enum Mode { case patrol, drawn, staring }
    private var mode: Mode = .patrol

    init(bounds: (Float, Float, Float, Float), baseY: Float,
         gown: SCNNode, armL: SCNNode, armR: SCNNode) {
        (minX, maxX, minZ, maxZ) = bounds
        self.baseY = baseY
        self.gown = gown; self.armL = armL; self.armR = armR
        target = SIMD2((minX + maxX) / 2, maxZ - 0.6)
    }

    private func newTarget() {
        // Laengsachse des Reviers ablaufen, mit etwas Seitenversatz
        if (maxZ - minZ) > (maxX - minX) {
            let goFar = abs(root.position.z - maxZ) > abs(root.position.z - minZ)
            target = SIMD2(Float.random(in: minX...maxX), goFar ? maxZ - 0.5 : minZ + 0.5)
        } else {
            let goFar = abs(root.position.x - maxX) > abs(root.position.x - minX)
            target = SIMD2(goFar ? maxX - 0.5 : minX + 0.5, Float.random(in: minZ...maxZ))
        }
    }

    func update(dt: Float, px: Float, pz: Float, py: Float, playerMoving: Bool) {
        t += dt
        // Nur aktiv, wenn der Spieler auf derselben Etage ist
        guard abs(py - baseY) < 1.6 else { return }
        let dx = px - root.position.x, dz = pz - root.position.z
        let dist = (dx * dx + dz * dz).squareRoot()

        switch mode {
        case .patrol:
            if dist < 5.5 && playerMoving {
                mode = .drawn
                // Der Schnapp: die Drehung passiert in EINEM Frame
                root.eulerAngles.y = atan2(dx, dz)
            }
        case .drawn:
            if dist < 1.35 { mode = .staring; staringFor = 0 }
            else if dist > 11 { mode = .patrol; newTarget() }
        case .staring:
            staringFor += dt
            if dist > 2.3 || staringFor > 4.5 { mode = .patrol; newTarget() }
        }

        var speed: Float = 0
        var tx = target.x, tz = target.y
        switch mode {
        case .patrol:
            speed = 0.5
            if abs(tx - root.position.x) < 0.3 && abs(tz - root.position.z) < 0.3 { newTarget() }
        case .drawn:
            // Langsam, aber unbeirrbar - die Richtung fuer den Standardgegner.
            speed = 0.85
            tx = px; tz = pz
        case .staring:
            speed = 0
            root.eulerAngles.y = atan2(dx, dz)
        }
        if speed > 0 {
            let mx = tx - root.position.x, mz = tz - root.position.z
            let l = max(0.001, (mx * mx + mz * mz).squareRoot())
            root.position.x = min(maxX, max(minX, root.position.x + mx / l * speed * dt))
            root.position.z = min(maxZ, max(minZ, root.position.z + mz / l * speed * dt))
            let want = atan2(mx, mz)
            var dy = want - root.eulerAngles.y
            while dy > Float.pi { dy -= 2 * Float.pi }
            while dy < -Float.pi { dy += 2 * Float.pi }
            root.eulerAngles.y += dy * min(1, (mode == .drawn ? 9 : 2.2) * dt)
        }
        // Gleiten statt Schritte: nur ein leises Heben und Senken
        root.position.y = baseY + sin(t * 1.1) * 0.015
        gown.eulerAngles.z = sin(t * 0.9) * 0.045
        armL.eulerAngles.z = 0.10 + sin(t * 0.8) * 0.05
        armR.eulerAngles.z = -0.10 + sin(t * 0.8 + 1.9) * 0.05

        // Der Kopf sucht den Spieler unabhaengig vom Koerper - auch beim
        // Wegdrehen bleibt das Gesicht noch einen Moment auf ihm.
        if dist < 9 {
            var hy = atan2(dx, dz) - root.eulerAngles.y
            while hy > Float.pi { hy -= 2 * Float.pi }
            while hy < -Float.pi { hy += 2 * Float.pi }
            hy = max(-1.25, min(1.25, hy))
            headPivot.eulerAngles.y += (hy - headPivot.eulerAngles.y) * min(1, 3 * dt)
        } else {
            headPivot.eulerAngles.y += (0 - headPivot.eulerAngles.y) * min(1, 2 * dt)
        }
    }
}

/// Kopf des Schlaefers: gleiche Ringform wie der Spieler, aber fahl, kahl,
/// Augen geschlossen (zwei dunkle Lidstriche), Mund einen Spalt offen.
private func sleeperHead(_ skin: SCNMaterial, _ dark: SCNMaterial) -> SCNNode {
    let n = 8
    let R: [(Float, Float, Float, Float, Float, Float)] = [
        ( 0.118, 0.034, 0.038, -0.004, 0,     0    ),
        ( 0.092, 0.066, 0.074, -0.002, 0,     0.18 ),
        ( 0.052, 0.080, 0.087,  0.000, 0,     0.26 ),
        ( 0.020, 0.084, 0.090,  0.002, 0.005, 0.30 ),
        (-0.020, 0.079, 0.087,  0.004, 0,     0.32 ),
        (-0.058, 0.063, 0.078,  0.006, 0,     0.30 ),
        (-0.092, 0.042, 0.060,  0.008, 0.004, 0.22 ),
        (-0.116, 0.022, 0.034,  0.010, 0,     0    ),
    ]
    func pt(_ r: (Float, Float, Float, Float, Float, Float), _ i: Int) -> SCNVector3 {
        ringPoint(r.0, r.1, r.2, r.3, i, n, r.4, r.5)
    }
    var tris: [(SCNVector3, SCNVector3, SCNVector3)] = []
    for k in 0..<(R.count - 1) {
        for i in 0..<n {
            let j = (i + 1) % n
            tris.append((pt(R[k], i), pt(R[k+1], j), pt(R[k+1], i)))
            tris.append((pt(R[k], i), pt(R[k], j), pt(R[k+1], j)))
        }
    }
    let top = SCNVector3(0, 0.130, -0.004), bot = SCNVector3(0, -0.128, 0.010)
    for i in 0..<n {
        let j = (i + 1) % n
        tris.append((top, pt(R[0], j), pt(R[0], i)))
        tris.append((bot, pt(R[R.count-1], i), pt(R[R.count-1], j)))
    }
    let holder = SCNNode()
    holder.addChildNode(flatMesh(tris, skin))
    // Nase
    let br2 = SCNVector3(0, 0.028, 0.084), tip = SCNVector3(0, -0.022, 0.104)
    let nl = SCNVector3(-0.018, -0.038, 0.080), nr = SCNVector3(0.018, -0.038, 0.080)
    holder.addChildNode(flatMesh([(br2, nl, tip), (br2, tip, nr), (tip, nl, nr)], skin))
    // Geschlossene Lider: abwaerts gebogene Striche
    for sg: Float in [-1, 1] {
        let ex = sg * 0.038
        let q = [SCNVector3(ex - 0.026, 0.016, 0.082), SCNVector3(ex + 0.026, 0.014, 0.082),
                 SCNVector3(ex + 0.022, 0.006, 0.083), SCNVector3(ex - 0.022, 0.004, 0.083)]
        holder.addChildNode(flatMesh([(q[0], q[2], q[1]), (q[0], q[3], q[2])], dark))
    }
    // Mund einen Spalt offen
    let mq = [SCNVector3(-0.020, -0.058, 0.070), SCNVector3(0.020, -0.058, 0.070),
              SCNVector3(0.016, -0.074, 0.070), SCNVector3(-0.016, -0.074, 0.070)]
    holder.addChildNode(flatMesh([(mq[0], mq[2], mq[1]), (mq[0], mq[3], mq[2])], dark))
    return holder
}

/// Baut den Schlaefer. bounds = Revier (x0, x1, z0, z1).
func makeSleeper(bounds: (Float, Float, Float, Float), baseY: Float) -> Sleeper {
    let skin = mat(UIColor(red: 0.72, green: 0.72, blue: 0.66, alpha: 1))     // fahl
    let cloth = mat(UIColor(red: 0.66, green: 0.68, blue: 0.62, alpha: 1))    // Nachthemd
    let dark = mat(UIColor(red: 0.12, green: 0.10, blue: 0.09, alpha: 1))

    // Nachthemd: eine Roehre von den Schultern bis zu den Knoecheln. Sie
    // verdeckt die Beine - deshalb kann er gleiten, ohne dass es auffaellt.
    let gown = tubeMesh([(0.06, 0.170, 0.130), (0.55, 0.150, 0.115),
                         (1.05, 0.145, 0.112), (1.32, 0.160, 0.120),
                         (1.42, 0.088, 0.075)], cloth, 8)
    let gownPivot = SCNNode()
    gownPivot.addChildNode(gown)

    let aL = SCNNode(); aL.position = SCNVector3(-0.175, 1.36, 0)
    aL.addChildNode(tubeMesh([(-0.62, 0.026, 0.028), (-0.30, 0.032, 0.034),
                              (0.0, 0.040, 0.043)], skin, 6, capTop: true))
    let aR = SCNNode(); aR.position = SCNVector3(0.175, 1.36, 0)
    aR.addChildNode(tubeMesh([(-0.62, 0.026, 0.028), (-0.30, 0.032, 0.034),
                              (0.0, 0.040, 0.043)], skin, 6, capTop: true))

    let headPivot = SCNNode()
    headPivot.position = SCNVector3(0, 1.47, 0)
    let head = sleeperHead(skin, dark)
    head.position = SCNVector3(0, 0.10, 0.01)
    head.eulerAngles.z = 0.34                     // der schiefe Kopf
    headPivot.addChildNode(head)
    // Hals
    let neck = tubeMesh([(0.0, 0.040, 0.038), (0.12, 0.036, 0.034)], skin, 6)
    neck.position = SCNVector3(0, 1.40, 0)

    let sl = Sleeper(bounds: bounds, baseY: baseY, gown: gownPivot, armL: aL, armR: aR)
    sl.body.addChildNode(gownPivot)
    sl.body.addChildNode(aL)
    sl.body.addChildNode(aR)
    sl.body.addChildNode(neck)
    sl.headPivot.position = headPivot.position
    for c in headPivot.childNodes { sl.headPivot.addChildNode(c) }
    sl.body.addChildNode(sl.headPivot)
    sl.body.eulerAngles.x = 0.12                  // leicht vornuebergebeugt
    sl.root.addChildNode(sl.body)
    // Kontaktschatten
    let bg = SCNPlane(width: 0.7, height: 0.7)
    let bm = SCNMaterial(); bm.lightingModel = .constant
    bm.diffuse.contents = Tex.shadowBlob; bm.writesToDepthBuffer = false
    bg.firstMaterial = bm
    let blob = SCNNode(geometry: bg)
    blob.eulerAngles.x = -Float.pi / 2
    blob.position = SCNVector3(0, 0.015, 0)
    blob.renderingOrder = 6
    sl.root.addChildNode(blob)
    return sl
}
