import SceneKit
import UIKit

// Villa Nachtschatten - Welt-Editor.
//
// WARUM ES DEN GIBT
// Der Moebel-Editor kann nur, was in furnitureList steht: 47 Stueck. Der
// Wand-Editor nur, was in wallList steht: zwei Waende. Alles andere - der
// Empfangstresen, die Treppengelaender, der Kessel, jedes Fensterbrett - baut
// Villa.swift fest im Code und war nicht anfassbar. Genau das war die Klage
// "allein der Tresen beim Eingang ist nicht anwaehlbar, Waende gibts nur 2 lol".
//
// WIE ER FUNKTIONIERT
// prop(), cyl(), sph(), propE() und cylE() melden inzwischen JEDEN Koerper
// ueber registerDetail() an - dieselbe Liste, aus der die Entfernungs-
// abschaltung lebt. Der Welt-Editor arbeitet direkt auf dieser Liste. Damit
// ist alles anwaehlbar, was das Haus ausmacht, ohne dass es doppelt als Daten
// gepflegt werden muesste.
//
// DIE INDEXFALLE - und wie sie entschaerft ist
// Ein Eintrag wird ueber seine POSITION in detailNodes gespeichert. Diese
// Reihenfolge ist beim Bauen deterministisch, also ueber Programmstarts hinweg
// stabil. Sie ist es NICHT mehr, sobald jemand (ich) in Villa.swift Koerper
// einfuegt oder entfernt: dann rutschen alle folgenden Indizes, und eine alte
// Verschiebung landet auf einem fremden Objekt.
// Deshalb speichert jeder Eintrag zusaetzlich seine Ursprungsposition auf 5 cm
// genau. Beim Laden wird verglichen; passt es nicht, wird der Eintrag
// verworfen und gezaehlt. Lieber eine verlorene Verschiebung als ein Fensterr-
// ahmen, der in die Kueche wandert.

/// Eine Aenderung an einem Weltkoerper.
struct WorldEdit {
    var dx: Float = 0
    var dy: Float = 0
    var dz: Float = 0
    var scale: Float = 1
    var hidden: Bool = false
    /// Ursprungsposition beim Anlegen - die Pruefsumme gegen die Indexfalle.
    var ox: Float = 0
    var oy: Float = 0
    var oz: Float = 0

    var istLeer: Bool {
        !hidden && abs(dx) < 0.001 && abs(dy) < 0.001 && abs(dz) < 0.001
            && abs(scale - 1) < 0.001
    }
}

extension GameController {

    // ---------- Auswahl ----------

    /// Welcher Weltkoerper liegt unter dem Bildschirmpunkt? -1 = keiner.
    /// Anders als pickFurniture sucht das NICHT nach einer "furn:"-Gruppe,
    /// sondern nimmt den getroffenen Knoten selbst und schlaegt ihn in
    /// detailNodes nach.
    func pickWorld(_ p: CGPoint) -> Int {
        guard let v = scnView else { return -1 }
        let treffer = v.hitTest(p, options: [.searchMode: SCNHitTestSearchMode.all.rawValue])
        for t in treffer {
            // Vom getroffenen Knoten aus nach oben, falls der Editor ihn
            // schon einmal in eine Moebelgruppe eingehaengt hat.
            var n: SCNNode? = t.node
            while let cur = n {
                if let i = detailNodes.firstIndex(where: { $0.node === cur }) { return i }
                n = cur.parent
            }
        }
        return -1
    }

    /// Antippen im Welt-Modus. Waehlt einen Koerper und - wenn `weit` gesetzt
    /// ist - alle Koerper in seiner Umgebung gleich mit. Ein Empfangstresen ist
    /// nicht EIN Koerper, sondern zwanzig Bretter; ohne Umkreis muesste man
    /// jedes einzeln schieben.
    func worldTap(_ p: CGPoint) {
        let i = pickWorld(p)
        if i < 0 {
            worldSel = []
            say("Nichts getroffen.")
            return
        }
        worldSel = [i]
        if worldRadius > 0.01 { erweitereWorldSel() }
        say(worldSel.count == 1 ? "1 Koerper gewaehlt."
                                : "\(worldSel.count) Koerper gewaehlt.")
    }

    /// Auswahl auf alle Koerper im Umkreis des ersten ausdehnen.
    func erweitereWorldSel() {
        guard let first = worldSel.first, first < detailNodes.count else { return }
        let a = detailNodes[first]
        let r2 = worldRadius * worldRadius
        var out: [Int] = []
        for (i, n) in detailNodes.enumerated() {
            let dx = n.x - a.x, dy = n.y - a.y, dz = n.z - a.z
            if dx * dx + dy * dy + dz * dz <= r2 { out.append(i) }
        }
        // Der angetippte Koerper bleibt vorne - er bestimmt den Mittelpunkt.
        worldSel = [first] + out.filter { $0 != first }
    }

    /// Umkreis umschalten: einzeln - 0.6 m - 1.4 m - 3.0 m.
    func worldRadiusNext() {
        let stufen: [Float] = [0, 0.6, 1.4, 3.0]
        let k = stufen.firstIndex(where: { $0 > worldRadius + 0.01 }) ?? 0
        worldRadius = stufen[k]
        if !worldSel.isEmpty {
            let first = worldSel[0]
            worldSel = [first]
            if worldRadius > 0.01 { erweitereWorldSel() }
        }
        say(worldRadius < 0.01 ? "Umkreis: einzeln"
                               : String(format: "Umkreis: %.1f m (%d)", worldRadius, worldSel.count))
    }

    /// Naechstgelegenen Koerper vor dem Spieler waehlen - fuer den Fall, dass
    /// das Antippen daneben geht.
    func worldSelectNearest() {
        let px = player.position.x, py = player.position.y, pz = player.position.z
        var best = -1
        var bestD: Float = 9999
        for (i, n) in detailNodes.enumerated() {
            let dx = n.x - px, dy = n.y - py - 1.0, dz = n.z - pz
            let d = dx * dx + dy * dy + dz * dz
            if d < bestD { bestD = d; best = i }
        }
        guard best >= 0 else { say("Nichts in der Naehe."); return }
        worldSel = [best]
        if worldRadius > 0.01 { erweitereWorldSel() }
        say("\(worldSel.count) Koerper gewaehlt.")
    }

    // ---------- Aendern ----------

    /// Alle gewaehlten Koerper verschieben.
    func worldNudge(_ dx: Float, _ dy: Float, _ dz: Float) {
        guard !worldSel.isEmpty else { say("Erst etwas waehlen."); return }
        for i in worldSel {
            guard i < detailNodes.count else { continue }
            var e = worldEdits[i] ?? neuerEdit(i)
            e.dx += dx; e.dy += dy; e.dz += dz
            worldEdits[i] = e
            wendeWorldEditAn(i)
        }
    }

    func worldScale(_ f: Float) {
        guard !worldSel.isEmpty else { say("Erst etwas waehlen."); return }
        for i in worldSel {
            guard i < detailNodes.count else { continue }
            var e = worldEdits[i] ?? neuerEdit(i)
            e.scale = max(0.15, min(6.0, e.scale * f))
            worldEdits[i] = e
            wendeWorldEditAn(i)
        }
    }

    /// Ausblenden statt loeschen: der Index bleibt gueltig, und ein
    /// versehentliches Wegraeumen laesst sich zuruecknehmen.
    func worldHide() {
        guard !worldSel.isEmpty else { say("Erst etwas waehlen."); return }
        for i in worldSel {
            guard i < detailNodes.count else { continue }
            var e = worldEdits[i] ?? neuerEdit(i)
            e.hidden = true
            worldEdits[i] = e
            wendeWorldEditAn(i)
        }
        say("\(worldSel.count) ausgeblendet.")
    }

    /// Einen Koerper auf den Bauzustand zuruecksetzen. Ausgeblendete Koerper
    /// sind AUS DER SZENE genommen (siehe wendeWorldEditAn) - isHidden allein
    /// wuerde sie nicht zurueckholen, sie muessen wieder angehaengt werden.
    private func stelleWiederHer(_ i: Int) {
        guard i < detailNodes.count else { return }
        let n = detailNodes[i]
        n.node.position = SCNVector3(n.x, n.y, n.z)
        n.node.scale = SCNVector3(1, 1, 1)
        n.node.isHidden = false
        if n.node.parent == nil { scene.rootNode.addChildNode(n.node) }
    }

    /// Auswahl auf den Bauzustand zuruecksetzen.
    func worldReset() {
        guard !worldSel.isEmpty else { say("Erst etwas waehlen."); return }
        for i in worldSel {
            worldEdits[i] = nil
            stelleWiederHer(i)
        }
        say("\(worldSel.count) zurueckgesetzt.")
    }

    /// Alles im ganzen Haus zuruecksetzen - der Notausgang.
    func worldResetAll() {
        let n = worldEdits.count
        for (i, _) in worldEdits { stelleWiederHer(i) }
        worldEdits = [:]
        say("\(n) Aenderungen verworfen.")
    }

    private func neuerEdit(_ i: Int) -> WorldEdit {
        let n = detailNodes[i]
        return WorldEdit(ox: n.x, oy: n.y, oz: n.z)
    }

    /// Traegt den gespeicherten Zustand auf den Knoten auf.
    func wendeWorldEditAn(_ i: Int) {
        guard i < detailNodes.count else { return }
        let n = detailNodes[i]
        guard let e = worldEdits[i] else {
            n.node.position = SCNVector3(n.x, n.y, n.z)
            n.node.scale = SCNVector3(1, 1, 1)
            return
        }
        n.node.position = SCNVector3(n.x + e.dx, n.y + e.dy, n.z + e.dz)
        n.node.scale = SCNVector3(e.scale, e.scale, e.scale)
        // isHidden gehoert auch der Entfernungsabschaltung. Ausgeblendete
        // Koerper werden deshalb zusaetzlich aus der Szene genommen - sonst
        // holt updateCulling sie beim naechsten Durchlauf zurueck.
        if e.hidden {
            if n.node.parent != nil { n.node.removeFromParentNode() }
        }
    }

    /// Ziehen im Welt-Modus: die Auswahl folgt dem Finger auf ihrer Ebene.
    func worldDragBegin(_ p: CGPoint) {
        guard let first = worldSel.first, first < detailNodes.count else { return }
        let n = detailNodes[first]
        let e = worldEdits[first] ?? WorldEdit()
        let y = n.y + e.dy
        if let w = groundPoint(p, y: y) {
            dragGrab = (w.x - (n.x + e.dx), w.z - (n.z + e.dz))
        } else {
            dragGrab = (0, 0)
        }
    }

    func worldDragMove(_ p: CGPoint) {
        guard let first = worldSel.first, first < detailNodes.count else { return }
        let n = detailNodes[first]
        let e = worldEdits[first] ?? WorldEdit()
        guard let w = groundPoint(p, y: n.y + e.dy) else { return }
        // Verschiebung des ANGETIPPTEN Koerpers, auf alle anderen uebertragen -
        // so bleibt die Gruppe in sich stehen.
        let zielDX = (w.x - dragGrab.0) - n.x
        let zielDZ = (w.z - dragGrab.1) - n.z
        let schubX = zielDX - e.dx
        let schubZ = zielDZ - e.dz
        if abs(schubX) < 0.0001 && abs(schubZ) < 0.0001 { return }
        for i in worldSel {
            guard i < detailNodes.count else { continue }
            var ei = worldEdits[i] ?? neuerEdit(i)
            ei.dx += schubX; ei.dz += schubZ
            worldEdits[i] = ei
            wendeWorldEditAn(i)
        }
    }

    // ---------- Sichern und Laden ----------

    func saveWorldEdits() {
        var zeilen: [String] = []
        for (i, e) in worldEdits.sorted(by: { $0.key < $1.key }) where !e.istLeer {
            zeilen.append([String(i), String(e.dx), String(e.dy), String(e.dz),
                           String(e.scale), e.hidden ? "1" : "0",
                           String(e.ox), String(e.oy), String(e.oz)]
                          .joined(separator: "|"))
        }
        UserDefaults.standard.set(zeilen.joined(separator: "\n"), forKey: "world_v1")
        say("\(zeilen.count) Weltaenderungen gesichert.")
    }

    /// Laedt und traegt auf. Eintraege, deren Ursprungsposition nicht mehr
    /// stimmt, werden verworfen - siehe die Indexfalle im Dateikopf.
    func loadWorldEdits() {
        guard let text = UserDefaults.standard.string(forKey: "world_v1"),
              !text.isEmpty else { return }
        var geladen = 0, verworfen = 0
        for zeile in text.split(separator: "\n") {
            let c = zeile.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
            guard c.count >= 9, let i = Int(c[0]), i >= 0, i < detailNodes.count else {
                verworfen += 1; continue
            }
            let e = WorldEdit(dx: Float(c[1]) ?? 0, dy: Float(c[2]) ?? 0, dz: Float(c[3]) ?? 0,
                              scale: Float(c[4]) ?? 1, hidden: c[5] == "1",
                              ox: Float(c[6]) ?? 0, oy: Float(c[7]) ?? 0, oz: Float(c[8]) ?? 0)
            // Pruefsumme: steht der Koerper noch da, wo er beim Sichern stand?
            let n = detailNodes[i]
            if abs(n.x - e.ox) > 0.05 || abs(n.y - e.oy) > 0.05 || abs(n.z - e.oz) > 0.05 {
                verworfen += 1; continue
            }
            worldEdits[i] = e
            wendeWorldEditAn(i)
            geladen += 1
        }
        if verworfen > 0 {
            say("\(geladen) Weltaenderungen geladen, \(verworfen) passten nicht mehr.")
        }
    }

    /// Als Swift-Code ausgeben, damit Aenderungen dauerhaft in Villa.swift
    /// wandern koennen statt nur in UserDefaults zu liegen.
    func exportWorldEdits() -> String {
        var out = "// Weltaenderungen - Index in detailNodes, Verschiebung, Groesse\n"
        for (i, e) in worldEdits.sorted(by: { $0.key < $1.key }) where !e.istLeer {
            if e.hidden {
                out += String(format: "// %d  bei (%.2f, %.2f, %.2f)  AUSGEBLENDET\n",
                              i, e.ox, e.oy, e.oz)
            } else {
                out += String(format: "// %d  bei (%.2f, %.2f, %.2f)  ->  (%+.2f, %+.2f, %+.2f)  x%.2f\n",
                              i, e.ox, e.oy, e.oz, e.dx, e.dy, e.dz, e.scale)
            }
        }
        return out
    }

    /// Auswahlring auf den ersten gewaehlten Koerper setzen.
    func worldSelCenter() -> SCNVector3? {
        guard let first = worldSel.first, first < detailNodes.count else { return nil }
        let n = detailNodes[first]
        let e = worldEdits[first] ?? WorldEdit()
        return SCNVector3(n.x + e.dx, n.y + e.dy, n.z + e.dz)
    }
}
