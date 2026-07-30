import SceneKit
import UIKit

// Gegenstaende, Tueren, Aufsammelbares und die Kartendaten.
// Liegt bewusst in einer eigenen Datei, damit Game.swift die Spiellogik
// nicht mit der Szenenverwaltung vermischt.

// ===================== Gegenstaende =====================

enum ItemKind: String, CaseIterable {
    case crowbar    = "Brecheisen"
    case rustyKey   = "Rostiger Schluessel"
    case brassKey   = "Messingschluessel"
    case note       = "Zettel"
    case lighter    = "Feuerzeug"
    case lantern    = "Laterne"
    case bathKey    = "Badehausschluessel"
    case asylumKey  = "Anstaltsschluessel"
    case gaestebuch = "Gaestebuchseite"
    case kurplan    = "Kurplan"
    case brief      = "Brief des Badearztes"
    case wartung    = "Wartungsheft"
    case heizer     = "Notiz des Heizers"

    /// SF-Symbol fuer die Inventarleiste
    var symbol: String {
        switch self {
        case .crowbar:  return "wrench.and.screwdriver.fill"
        case .rustyKey: return "key.fill"
        case .brassKey: return "key.horizontal.fill"
        case .note:     return "doc.text.fill"
        case .lighter:  return "flame.fill"
        case .lantern:  return "lightbulb.fill"
        case .bathKey, .asylumKey: return "key.fill"
        case .gaestebuch, .kurplan, .brief, .wartung, .heizer: return "doc.plaintext.fill"
        }
    }
    /// Dokumente lassen sich im Journal nachlesen.
    var isDocument: Bool {
        switch self {
        case .note, .gaestebuch, .kurplan, .brief, .wartung, .heizer: return true
        default: return false
        }
    }
    /// Text, der beim Aufheben eingeblendet wird
    var pickupText: String {
        switch self {
        case .crowbar:  return "Brecheisen aufgenommen. Damit lassen sich Bretter loesen."
        case .rustyKey: return "Rostiger Schluessel aufgenommen."
        case .brassKey: return "Messingschluessel aufgenommen."
        case .note:     return "Ein Zettel. Die Schrift ist verwischt."
        case .lighter:  return "Feuerzeug aufgenommen."
        case .lantern:  return "Eine Sturmlaterne, noch halb voll. Antippen zum Anzuenden."
        case .bathKey:   return "Ein Messingschluessel, Anhaenger: BADEHAUS."
        case .asylumKey: return "Ein schwerer Schluessel ohne Anhaenger."
        case .gaestebuch: return "12. Oktober: Die Herrschaften reisen nicht mehr ab. Sie werden verlegt. Nach unten."
        case .kurplan:    return "Kurplan, Zimmer 3 - Dauerschlaf, 14. Tag. Dosis erneut erhoeht. Sie spricht im Schlaf von der Quelle."
        case .brief:      return "\"Das Quellwasser wird seit dem Fruehjahr waermer. Ich empfehle, den Badebetrieb auszusetzen. Man wird mir nicht folgen.\""
        case .wartung:    return "Wartungsheft: Der Kessel brennt seit drei Tagen ohne Beschickung. Ich steige da nicht mehr hinunter."
        case .heizer:     return "Dritte Nacht ohne Schlaf. Ich habe nicht nachgelegt, und der Druck steigt trotzdem. Wenn das Rohr zur Quelle singt, gehe ich nicht mehr hinein."
        }
    }
}

// ===================== Tuer =====================

final class Door {
    let hinge: SCNNode          // Knoten, um den das Blatt schwingt
    let solidIndex: Int         // Eintrag in solids, der im geschlossenen Zustand sperrt
    let closedAngle: Float
    let openAngle: Float
    let x: Float, z: Float
    let label: String
    var isOpen: Bool
    /// Gegenstand, der zum Aufschliessen noetig ist. nil = offen zugaenglich.
    var lock: ItemKind?
    /// Zugenagelt - braucht das Brecheisen, unabhaengig vom Schloss.
    var boarded: Bool
    /// Bretter als Knoten, damit sie beim Aufhebeln verschwinden koennen.
    var boards: [SCNNode] = []

    init(hinge: SCNNode, solidIndex: Int, closedAngle: Float, openAngle: Float,
         x: Float, z: Float, label: String, isOpen: Bool,
         lock: ItemKind?, boarded: Bool) {
        self.hinge = hinge
        self.solidIndex = solidIndex
        self.closedAngle = closedAngle
        self.openAngle = openAngle
        self.x = x; self.z = z
        self.label = label
        self.isOpen = isOpen
        self.lock = lock
        self.boarded = boarded
    }

    func distance(_ px: Float, _ pz: Float) -> Float {
        let dx = px - x, dz = pz - z
        return (dx * dx + dz * dz).squareRoot()
    }

    /// Dreht das Blatt weich in die Zielstellung.
    func swing(to open: Bool) {
        isOpen = open
        let target = open ? openAngle : closedAngle
        hinge.removeAllActions()
        let a = SCNAction.rotateTo(x: 0, y: CGFloat(target), z: 0, duration: 0.55, usesShortestUnitArc: true)
        a.timingMode = .easeInEaseOut
        hinge.runAction(a)
    }
}

// ===================== Aufsammelbares =====================

final class Pickup {
    let node: SCNNode
    let kind: ItemKind
    let x: Float, z: Float
    var taken = false

    init(node: SCNNode, kind: ItemKind, x: Float, z: Float) {
        self.node = node; self.kind = kind; self.x = x; self.z = z
    }

    func distance(_ px: Float, _ pz: Float) -> Float {
        let dx = px - x, dz = pz - z
        return (dx * dx + dz * dz).squareRoot()
    }
}

// ===================== Karte =====================

struct RoomInfo: Identifiable {
    let id = UUID()
    let name: String
    let short: String          // Kuerzel fuer die Karte
    let x0: Float, x1: Float, z0: Float, z1: Float
    var visited: Bool = false
    /// 0 = Erdgeschoss und Keller, 1 = Obergeschoss. Die Karte zeigt nur die
    /// Etage, auf der der Spieler gerade steht.
    var floor: Int = 0

    func contains(_ x: Float, _ z: Float) -> Bool {
        x >= x0 && x <= x1 && z >= z0 && z <= z1
    }
}

enum MapData {
    /// Grundriss der Villa. Reihenfolge egal, die Karte skaliert sich selbst.
    static let rooms: [RoomInfo] = [
        RoomInfo(name: "Isolierung",  short: "Isolierung", x0: -1.2, x1: 1.2, z0: -23.2, z1: -20, floor: 1),
        RoomInfo(name: "Zelle West",  short: "Zelle W",    x0: -3.8, x1: -1.2, z0: -23.2, z1: -20.2, floor: 1),
        RoomInfo(name: "Zelle Ost",   short: "Zelle O",    x0: 1.2,  x1: 3.8,  z0: -23.2, z1: -20.2, floor: 1),
        RoomInfo(name: "Vorraum",     short: "Vorraum",     x0: -8, x1: -1, z0: 3,   z1: 13, floor: 2),
        RoomInfo(name: "Waschsaal",   short: "Waschsaal",   x0: -1, x1: 9,  z0: 3,   z1: 13, floor: 2),
        RoomInfo(name: "Schwimmhalle", short: "Schwimmhalle", x0: -9, x1: 9, z0: -13, z1: 3, floor: 2),
        RoomInfo(name: "Galerie",         short: "Galerie",  x0: -8,  x1: -1.5, z0: 0,   z1: 12.5, floor: 1),
        RoomInfo(name: "Stationsflur",    short: "Flur",     x0: -3,  x1: 3,    z0: -20, z1: 0,    floor: 1),
        RoomInfo(name: "Zimmer 1",        short: "Z 1",      x0: -11, x1: -3,   z0: -6,  z1: -1,   floor: 1),
        RoomInfo(name: "Zimmer 2",        short: "Z 2",      x0: 3,   x1: 11,   z0: -6,  z1: -1,   floor: 1),
        RoomInfo(name: "Zimmer 3",        short: "Z 3",      x0: -11, x1: -3,   z0: -13, z1: -8,   floor: 1),
        RoomInfo(name: "Zimmer 4",        short: "Z 4",      x0: 3,   x1: 11,   z0: -13, z1: -8,   floor: 1),
        RoomInfo(name: "Schwesternzimmer", short: "Schwestern", x0: -11, x1: -3, z0: -20, z1: -15, floor: 1),
        RoomInfo(name: "Waschraum",       short: "Waschraum", x0: 3,  x1: 11,   z0: -20, z1: -15,  floor: 1),
        RoomInfo(name: "Empfangshalle",  short: "Empfang", x0: -2, x1: 8,  z0: 0,     z1: 14),
        RoomInfo(name: "Flur",           short: "Flur",   x0: -8, x1: -2, z0: 0,     z1: 8.6),
        RoomInfo(name: "Treppenraum",    short: "Treppe", x0: -8, x1: -2, z0: 8.6,   z1: 14),
        RoomInfo(name: "Speisesaal",   short: "Speisesaal", x0: -24, x1: -8, z0: 2,     z1: 14),
        RoomInfo(name: "Kueche",         short: "Kueche", x0: -24, x1: -12, z0: -10,  z1: 2),
        RoomInfo(name: "Lesesaal",     short: "Lesesaal", x0: 8,   x1: 22, z0: 2,     z1: 14),
        RoomInfo(name: "Wandelhalle",        short: "Gal",    x0: 12,  x1: 22, z0: -10,   z1: 2),
        RoomInfo(name: "Nordflur",       short: "Flur",   x0: -3,  x1: 3,  z0: -14,   z1: 0),
        RoomInfo(name: "Baederabteilung",            short: "Baeder",    x0: -10, x1: -3, z0: -11,   z1: -4),
        RoomInfo(name: "Apotheke",          short: "Apotheke",  x0: 3,   x1: 10, z0: -11,   z1: -4),
        RoomInfo(name: "Direktion",  short: "Direktion", x0: -7,  x1: 7,  z0: -24,   z1: -14),
        RoomInfo(name: "Westflur",       short: "W-Flur", x0: -31, x1: -24, z0: -22,  z1: 14),
        RoomInfo(name: "Musiksalon",          short: "Musiksalon",  x0: -47, x1: -31, z0: -22,  z1: -6),
        RoomInfo(name: "Kellergang",     short: "Gang",   x0: 3,   x1: 11, z0: -13.4, z1: -11.6),
        RoomInfo(name: "Quellkammer",         short: "Quelle", x0: 11,  x1: 23, z0: -23,   z1: -11.5),
    ]

    /// Aussenmasse des Grundrisses, damit die Karte passend skaliert.
    static var bounds: (x0: Float, x1: Float, z0: Float, z1: Float) {
        var a: Float = 1e9, b: Float = -1e9, c: Float = 1e9, d: Float = -1e9
        for r in rooms {
            a = min(a, r.x0); b = max(b, r.x1)
            c = min(c, r.z0); d = max(d, r.z1)
        }
        return (a, b, c, d)
    }
}
