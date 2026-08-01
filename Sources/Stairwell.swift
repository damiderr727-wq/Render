import SceneKit
import UIKit

// Villa Nachtschatten - Treppenhaus.
//
// Form: zweilaeufig gegenlaeufig, zweimal uebereinander.
//   Lauf steigt nach SUEDEN  ->  Zwischenpodest an der Suedwand (der Mini-Flur)
//   ->  Lauf steigt nach NORDEN zurueck  ->  naechste Etage
//   ->  dort beginnt dasselbe von vorn, im selben Stil.
//
// Alle Masse sind in tools/treppe_entwurf.py nachgerechnet: Schrittmass,
// Kopffreiheit, Wandabstaende, lichter Abstand zwischen den Geschossen und die
// Begehbarkeit - letztere mit derselben hits()/groundHeight()-Logik, die das
// Spiel benutzt. Wer hier Zahlen aendert, laesst das Skript danach laufen.
//
// ZWEI ENTWURFSENTSCHEIDUNGEN, die nicht offensichtlich sind:
//
// 1. Beide Geschosse haben GLEICH LANGE Laeufe (3.135 m), obwohl sie
//    verschieden hoch sind (3.80 m und 2.80 m). Erreicht wird das ueber
//    verschiedene Stufenzahlen: 11 Stufen a 17.27 cm unten, 10 Stufen a
//    14.00 cm oben. Dadurch liegt jeder Lauf exakt ueber seinem Gegenstueck
//    und der lichte Abstand ist ueberall mindestens 2.80 m. Die alte Fassung
//    hatte 3.135 m auf 2.24 m - dort schoben sich Podest und Lauf ineinander,
//    mit 1.40 m Kopffreiheit ueber dem Antritt.
//
// 2. Das Podest liegt am SUEDENDE an der Wand, und beide Laeufe teilen sich
//    denselben z-Bereich. Laege das Podest im Norden, endete der obere Lauf
//    21 cm vor der Suedwand - man koennte nicht aussteigen.
//
// Und der Fehler, der die alte Treppe unpassierbar gemacht hat, zweimal:
// Fuellkoerper und Bruestungen mit blocksPlayer auf dem Vorgabewert true,
// deren Hoehenbereich bis zur Lauf-Oberkante reichte. hits() blendet eine
// Sperre erst aus, wenn y1 < y + 0.15 ist - eine Fuellung, die bis zur
// Trittflaeche reicht, sperrt den Lauf, auf dem man steht. Deshalb bleibt
// hier jede Fuellung 30 cm unter der Rampe, und ueber Antritt und Austritt
// steht ueberhaupt keine Bruestung.

// --- Schacht, Wandachsen ---
private let shaftW: Float = -8.0
private let shaftE: Float = -4.0
private let shaftN: Float = 6.0
private let shaftS: Float = 14.0
// --- Innenflaechen: Wandachse plus halbe Wanddicke (0.19, siehe wall()) ---
private let shaftIW: Float = -7.81
private let shaftIE: Float = -4.19
private let shaftIS: Float = 13.81
// --- Laeufe ---
private let laneWidth: CGFloat = 1.40
private let laneWest: Float = -6.90
private let laneEast: Float = -5.10
private let runLength: Float = 3.135
private let landingDepth: Float = 1.70
// Abgeleitet, nicht abgeschrieben: sonst laufen die Werte beim naechsten
// Verschieben auseinander.
private let landingN: Float = shaftIS - landingDepth        // 12.110
private let stairFoot: Float = shaftIS - landingDepth - runLength   // 8.975
private let shaftCeil: Float = 9.3         // Unterkante der Badehausdecke

extension GameController {

    /// Ein gerader Lauf mit `steps` gleichen Stufen von (zFrom, yFrom) nach
    /// (zTo, yTo). Die Stufenzahl kommt von aussen - nur so lassen sich zwei
    /// verschieden hohe Geschosse mit gleich langen Laeufen bauen.
    func stairRun(_ x: Float, _ zFrom: Float, _ zTo: Float, _ w: CGFloat,
                  _ yFrom: Float, _ yTo: Float, steps n: Int) {
        let tread = texMat(Tex.plankWood, 1, 1)
        let riser = texMat(Tex.wainscot, 2, 1)
        let rail = texMat(Tex.plankWood, 1, 1)
        let runnerM = texMat(Tex.runner, 1, 1)
        let fw = Float(w)
        let dz = (zTo - zFrom) / Float(n)
        let dy = (yTo - yFrom) / Float(n)
        let railOff = fw / 2 + 0.09

        for i in 0..<n {
            let y = yFrom + dy * Float(i + 1)              // Oberkante der Stufe
            let zc = zFrom + dz * (Float(i) + 0.5)
            prop(w + 0.06, 0.075, CGFloat(abs(dz)) + 0.05, x, y - 0.037, zc, tread)
            // Setzstufe nur als sichtbare Vorderseite. Der alte Bauer hat je
            // Stufe einen Vollkoerper bis zum Boden gesetzt - bei vier Laeufen
            // waren das ueber vierzig ueberfluessige Koerper.
            prop(w, CGFloat(abs(dy)), 0.06, x, y - abs(dy) / 2, zc - dz / 2, riser)
        }

        let ang = Float(atan2(Double(yTo - yFrom), Double(zTo - zFrom)))
        let midZ = (zFrom + zTo) / 2
        let midY = (yFrom + yTo) / 2
        let dzT = zTo - zFrom, dyT = yTo - yFrom
        let len = CGFloat((dzT * dzT + dyT * dyT).squareRoot())
        let tilt = SCNVector3(-ang, 0, 0)

        // Laeufer als EINE durchgehende Bahn statt einer je Stufe
        propE(w * 0.56, 0.012, len, x, midY + 0.025, midZ, tilt, runnerM)
        // Untersicht - sonst sieht man von unten zwischen die Setzstufen
        propE(w, 0.05, len + 0.10, x, midY - 0.26, midZ, tilt, riser)
        for s in [-1, 1] {
            let sx = Float(s)
            propE(0.09, 0.46, len + 0.16, x + (fw / 2 + 0.045) * sx, midY - 0.13,
                  midZ, tilt, rail)                                  // Wange
            propE(0.085, 0.085, len + 0.16, x + railOff * sx, midY + 0.95,
                  midZ, tilt, rail)                                  // Handlauf
        }
        for i in stride(from: 0, to: n, by: 2) {
            let y = yFrom + dy * Float(i + 1)
            let zc = zFrom + dz * (Float(i) + 0.5)
            for s in [-1, 1] {
                prop(0.045, 0.90, 0.045, x + railOff * Float(s), y + 0.45, zc, rail)
            }
        }

        // --- Laufflaeche. FloorArea rechnet von z0 nach z1, also muss die
        // --- Hoehe zur KLEINEREN z-Koordinate zuerst stehen.
        let zLo = min(zFrom, zTo), zHi = max(zFrom, zTo)
        let yAtLo = zFrom < zTo ? yFrom : yTo
        let yAtHi = zFrom < zTo ? yTo : yFrom
        addFloorArea(x - fw / 2, x + fw / 2, zLo, zHi, yAtLo, yAtHi, alongZ: true)

        let segs = 6
        for k in 0..<segs {
            let t0 = Float(k) / Float(segs), t1 = Float(k + 1) / Float(segs)
            let za = zFrom + (zTo - zFrom) * t0, zb = zFrom + (zTo - zFrom) * t1
            let ya = yFrom + (yTo - yFrom) * t0, yb = yFrom + (yTo - yFrom) * t1
            // Kamera bleibt ueber den Stufen, der Spieler laeuft hindurch
            solids.append(WallBox(x0: x - fw / 2, x1: x + fw / 2,
                                  z0: min(za, zb), z1: max(za, zb),
                                  y0: min(ya, yb) - 0.85, y1: max(ya, yb),
                                  blocksCamera: true, blocksPlayer: false))
            // Wangen halten den Spieler AUF dem Lauf. Ohne sie laeuft er
            // seitlich ins Treppenauge, findet dort keine Laufflaeche und
            // faellt ins Erdgeschoss.
            for s in [-1, 1] {
                let cx = x + railOff * Float(s)
                solids.append(WallBox(x0: cx - 0.07, x1: cx + 0.07,
                                      z0: min(za, zb), z1: max(za, zb),
                                      y0: min(ya, yb) - 0.10, y1: max(ya, yb) + 1.10,
                                      blocksCamera: false))
            }
        }
    }

    /// Zwischenpodest ueber die volle Schachtbreite.
    func stairLanding(_ y: Float, _ mat: SCNMaterial) {
        prop(CGFloat(shaftIE - shaftIW), 0.18, CGFloat(shaftIS - landingN),
             (shaftIW + shaftIE) / 2, y - 0.09, (landingN + shaftIS) / 2, mat)
        addFloorArea(shaftIW, shaftIE, landingN, shaftIS, y)
    }

    /// Schliesst den Raum unter einem Lauf, damit niemand mit 1.20 m
    /// Kopffreiheit hineinlaeuft. Die Oberkante bleibt 30 cm UNTER der Rampe -
    /// siehe die Erklaerung im Dateikopf.
    func stairUnderFill(_ x: Float, _ zFrom: Float, _ zTo: Float, _ w: CGFloat,
                        _ yFrom: Float, _ yTo: Float, floorY: Float = 0) {
        let fw = Float(w)
        let segs = 8
        for k in 0..<segs {
            let t0 = Float(k) / Float(segs), t1 = Float(k + 1) / Float(segs)
            let za = zFrom + (zTo - zFrom) * t0, zb = zFrom + (zTo - zFrom) * t1
            let ya = yFrom + (yTo - yFrom) * t0, yb = yFrom + (yTo - yFrom) * t1
            let top = min(ya, yb) - 0.30
            if top < floorY + 0.25 { continue }
            solids.append(WallBox(x0: x - fw / 2 - 0.04, x1: x + fw / 2 + 0.04,
                                  z0: min(za, zb), z1: max(za, zb),
                                  y0: floorY, y1: top, blocksCamera: false))
        }
    }

    /// Der ganze Schacht: Waende, Decken, Bodenbaender, vier Laeufe, zwei
    /// Podeste, Fuellungen und Licht.
    func buildStairwell(_ mat: SCNMaterial) {
        let oak  = texMat(Tex.parquet, 2, 2)
        let lino = texMat(Tex.woodFloor, 2, 2)
        let slab = texMat(Tex.plankWood, 2, 1)
        let bandD = CGFloat(stairFoot - shaftN)
        let bandZ = (shaftN + stairFoot) / 2
        let shaftD = CGFloat(shaftS - stairFoot)
        let shaftZ = (stairFoot + shaftS) / 2
        let cx = (shaftW + shaftE) / 2

        // ---------- Waende ----------
        // Ostwand: neben dem Bodenband nur bis zur Badehausplatte, ueber dem
        // offenen Schacht bis unter die Decke.
        wallZ(shaftN, stairFoot, shaftE, mat, h: 6.6)
        wallZ(stairFoot, shaftS, shaftE, mat, h: CGFloat(shaftCeil))
        // West- und Suedwand gibt es bis y = 6 schon aus buildVilla. Das Stueck
        // von 6.0 bis unter die Decke fehlte bisher voellig - zwischen
        // Hallendecke und Badehauswand klaffte ein halber Meter.
        wallZ(shaftN, shaftS, shaftW, mat, h: CGFloat(shaftCeil - 6.0),
              wainscot: false, base: 6.0)
        wallX(shaftW, shaftE, shaftS, mat, h: CGFloat(shaftCeil - 6.0),
              wainscot: false, base: 6.0)

        // ---------- Decken ----------
        // Ueber dem Bodenband normale Raumhoehe, ueber dem Schacht selbst erst
        // auf Badehausniveau. Genau diese Trennung fehlte: eine durchgehende
        // Decke auf y = 6.0 lag mitten im Weg des oberen Laufs.
        ceiling(4.0, bandD, cx, bandZ, 6.0)
        ceiling(4.0, shaftD, cx, shaftZ, shaftCeil)

        // ---------- Bodenbaender ----------
        // Jede Etage bekommt nur im Norden eine Platte. Suedlich davon bleibt
        // der Schacht offen, damit die Laeufe hindurchsteigen koennen.
        floorTile(4.0, bandD, cx, bandZ, oak,  y: 3.8)
        floorTile(4.0, bandD, cx, bandZ, lino, y: 6.6)

        // ---------- Erdgeschoss -> Obergeschoss: 11 Stufen a 17.27 cm ----------
        stairRun(laneWest, stairFoot, landingN, laneWidth, 0.00, 1.90, steps: 11)
        stairLanding(1.90, slab)
        stairRun(laneEast, landingN, stairFoot, laneWidth, 1.90, 3.80, steps: 11)

        // ---------- Obergeschoss -> Badehaus: 10 Stufen a 14.00 cm ----------
        stairRun(laneWest, stairFoot, landingN, laneWidth, 3.80, 5.20, steps: 10)
        stairLanding(5.20, slab)
        stairRun(laneEast, landingN, stairFoot, laneWidth, 5.20, 6.60, steps: 10)

        // ---------- Unter der untersten Treppe zumauern ----------
        // Nur im Erdgeschoss noetig - unter den oberen Laeufen ist der Schacht
        // offen, dort kann ohnehin niemand stehen.
        stairUnderFill(laneWest, stairFoot, landingN, laneWidth, 0.00, 1.90)
        stairUnderFill(laneEast, landingN, stairFoot, laneWidth, 1.90, 3.80)
        solids.append(WallBox(x0: shaftIW, x1: shaftIE,
                              z0: landingN + 0.05, z1: shaftIS,
                              y0: 0, y1: 1.60, blocksCamera: false))
        // Sichtbare Wand der Kammer unter dem Podest
        prop(CGFloat(shaftIE - shaftIW), 1.60, 0.10, (shaftIW + shaftIE) / 2,
             0.80, landingN + 0.05, mat)

        // ---------- Licht ----------
        // Sparsam: der Schacht ist drei Geschosse hoch, jede Lampe leuchtet
        // hier weiter als in einem Zimmer.
        let warm = UIColor(red: 1.0, green: 0.86, blue: 0.62, alpha: 1)
        addOmni(SCNVector3(cx, 2.90, landingN + 0.7), 420, warm, range: 9)
        addOmni(SCNVector3(cx, 6.20, landingN + 0.7), 380, warm, range: 9)
        addOmni(SCNVector3(cx, 4.10, stairFoot + 0.8), 360, warm, range: 10)
        sconce(shaftIW + 0.03, 2.60, landingN + 0.5, 1, 0, beam: true)
        sconce(shaftIW + 0.03, 5.90, landingN + 0.5, 1, 0, beam: true)
        addDust(cx, 3.20, shaftZ, 3.4, 6.0, 4.6, 12)
    }
}
