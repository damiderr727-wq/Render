import Foundation
import ResonanzCore

/// Prueft die Welt gegen die echte Spielphysik.
///
///     swift run -c release resonanz-check
///
/// Fuer jeden Raum wird ermittelt, welches Koennen die Figur beim ersten
/// Betreten hat, und dann simuliert, ob sie von den Eingaengen aus alle
/// Fundstuecke, Baenke und weiterfuehrenden Tueren erreicht.

struct Report {
    var failures: [String] = []
    var notes: [String] = []
}

let green = "\u{001B}[32m"
let red = "\u{001B}[31m"
let dim = "\u{001B}[2m"
let reset = "\u{001B}[0m"

/// Zeigt einen Raum so, wie die Physikpruefung ihn sieht.
///
/// Wenn eine Tuer als unerreichbar gemeldet wird, ist die Frage nie "ob",
/// sondern "wo bricht der Weg ab" - und das laesst sich aus einer
/// Fehlermeldung nicht ablesen. Diese Ansicht malt den Raum aus und
/// markiert jede Standflaeche danach, ob die Figur sie erreicht:
///
///     resonanz-check --zeige A5
///
///   +  erreichbar      x  Standflaeche ohne Weg dorthin
///   T  Tuer            o  Eingang
func zeige(_ room: Room, alle: Set<Ability>) {
    let progression = Progression(abilities: alle, kerne: Set(Kern.allCases))
    let probe = ReachabilityProbe(room: room, progression: progression)
    let targets = ReachabilityProbe.targets(for: room)
    let result = probe.run(from: ReachabilityProbe.origins(for: room), targets: targets)

    print("\n\(room.id)  \(room.data.name)   \(room.width)x\(room.height)")
    var zeilen: [[Character]] = []
    for ty in 0..<room.height {
        var zeile: [Character] = []
        for tx in 0..<room.width {
            let tile = room.tile(tx, ty)
            if tile.isStandable, ty > 0, room.tile(tx, ty - 1) == .air || tile.isSlope {
                zeile.append(result.reachableTiles.contains(ty * room.width + tx) ? "+" : "x")
            } else if tile == .air {
                zeile.append(" ")
            } else {
                zeile.append("#")
            }
        }
        zeilen.append(zeile)
    }
    for door in room.data.doors {
        for tx in door.x..<(door.x + door.w) where tx < room.width {
            for ty in door.y..<(door.y + door.h) where ty < room.height {
                zeilen[ty][tx] = "T"
            }
        }
    }
    for spawn in room.data.spawns.values {
        let tx = Int(spawn.x), ty = Int(spawn.y)
        if tx >= 0, tx < room.width, ty >= 0, ty < room.height { zeilen[ty][tx] = "o" }
    }
    for (i, zeile) in zeilen.enumerated() {
        print(String(format: "%3d ", i) + String(zeile))
    }
    for t in result.unreached {
        print("  nicht erreicht: \(t.name)  \(t.area)")
    }
}

func run() throws -> Int32 {
    let catalog = try WorldCatalog()
    let rooms = try catalog.loadAll()
    let byID = Dictionary(uniqueKeysWithValues: rooms.map { ($0.id, $0) })

    if let i = CommandLine.arguments.firstIndex(of: "--zeige"),
       i + 1 < CommandLine.arguments.count,
       let room = byID[CommandLine.arguments[i + 1]] {
        var alle: Set<Ability> = []
        for r in rooms {
            for p in r.data.pickups where p.kind == "ability" {
                if let a = Ability(rawValue: p.id) { alle.insert(a) }
            }
        }
        zeige(room, alle: alle)
        return 0
    }

    print("RESONANZ - Raumpruefung gegen die Spielphysik")
    print(String(repeating: "-", count: 62))

    // --- Welches Koennen hat die Figur beim ersten Betreten eines Raums? ---
    var arrival: [String: Set<Ability>] = [:]
    var abilities: Set<Ability> = []
    var seen: Set<String> = []

    while true {
        var frontier = [catalog.index.startRoom]
        var visitedNow: Set<String> = [catalog.index.startRoom]
        while let id = frontier.popLast() {
            if arrival[id] == nil { arrival[id] = abilities }
            guard let room = byID[id] else { continue }
            for door in room.data.doors {
                if let requirement = door.requires,
                   let ability = Ability(rawValue: requirement),
                   !abilities.contains(ability) { continue }
                if !visitedNow.contains(door.target) {
                    visitedNow.insert(door.target)
                    frontier.append(door.target)
                }
            }
        }
        seen = visitedNow

        var gained = false
        for id in visitedNow.sorted() {
            for p in byID[id]?.data.pickups ?? [] where p.kind == "ability" {
                if let ability = Ability(rawValue: p.id), !abilities.contains(ability) {
                    abilities.insert(ability)
                    gained = true
                }
            }
        }
        if !gained { break }
    }

    var report = Report()
    for id in catalog.roomIDs {
        guard let room = byID[id] else { continue }
        guard seen.contains(id) else {
            report.failures.append("\(id): mit dem erreichbaren Koennen nie betretbar")
            continue
        }

        let held = arrival[id] ?? []
        let progression = Progression(abilities: held,
                                      kerne: Set(Kern.allCases))

        // Gesperrte Tueren gehoeren nicht in den ersten Durchgang - sie sind
        // beim Ankommen ohnehin zu.
        let all = ReachabilityProbe.targets(for: room)
        let atArrival = all.filter { target in
            guard target.kind == .door else { return true }
            guard let door = room.data.doors.first(where: {
                target.name == "door:\($0.id)->\($0.target)"
            }) else { return true }
            guard let requirement = door.requires,
                  let ability = Ability(rawValue: requirement) else { return true }
            return held.contains(ability)
        }

        let probe = ReachabilityProbe(room: room, progression: progression)
        let result = probe.run(from: ReachabilityProbe.origins(for: room), targets: atArrival)

        // Zweiter Durchgang: alles, was beim Ankommen fehlte oder gar nicht
        // erst geprueft wurde, muss spaeter erreichbar sein - sonst liegt es
        // fuer immer hinter Glas.
        let deferredNames = Set(result.unreached.map(\.name))
            .union(all.filter { t in !atArrival.contains(where: { $0.name == t.name }) }.map(\.name))
        var laterOnly: [String] = []
        var lost: [String] = []
        if !deferredNames.isEmpty {
            let full = Progression(abilities: abilities,
                                   kerne: Set(Kern.allCases))
            let revisit = ReachabilityProbe(room: room, progression: full)
                .run(from: ReachabilityProbe.origins(for: room),
                     targets: all.filter { deferredNames.contains($0.name) })
            let stillOut = Set(revisit.unreached.map(\.name))
            lost = deferredNames.filter(stillOut.contains).sorted()
            laterOnly = deferredNames.subtracting(stillOut).sorted()
        }

        let abilityList = held.isEmpty
            ? "-"
            : Ability.allCases.filter(held.contains).map(\.rawValue).joined(separator: ",")
        let mark = lost.isEmpty ? "\(green)ok \(reset)" : "\(red)!! \(reset)"
        let coverage = "\(result.reachableSurfaces)/\(result.totalSurfaces)"
        print("\(mark) \(id.padding(toLength: 4, withPad: " ", startingAt: 0)) "
            + "\(room.name.padding(toLength: 30, withPad: " ", startingAt: 0)) "
            + "\(dim)Flaechen \(coverage.padding(toLength: 10, withPad: " ", startingAt: 0)) "
            + "Koennen: \(abilityList)\(reset)")

        for name in lost {
            report.failures.append("\(id): \(name) ist von keinem Eingang aus erreichbar")
        }
        for name in laterOnly {
            report.notes.append("\(id): \(name) erst bei spaeterer Rueckkehr erreichbar")
        }
    }

    print(String(repeating: "-", count: 62))
    for note in report.notes {
        print("\(dim)spaeter\(reset) \(note)")
    }
    if report.failures.isEmpty {
        print("\(green)Alles erreichbar.\(reset) \(catalog.roomIDs.count) Raeume geprueft.")
        return 0
    }
    for failure in report.failures {
        print("\(red)FEHLER\(reset) \(failure)")
    }
    print("\n\(report.failures.count) Beanstandungen.")
    return 1
}

/// Zeichnet den Raum als ASCII-Karte: `o` erreichbare Standflaeche,
/// `x` unerreichbare, `T` Ziel. So sieht man sofort, wo der Weg abreisst.
func drawMap(roomID: String, abilities: Set<Ability>) throws -> Int32 {
    let catalog = try WorldCatalog()
    let room = try catalog.room(roomID)
    let progression = Progression(abilities: abilities,
                                  kerne: Set(Kern.allCases))
    let targets = ReachabilityProbe.targets(for: room)
    let probe = ReachabilityProbe(room: room, progression: progression)
    let result = probe.run(from: ReachabilityProbe.origins(for: room), targets: targets)

    print("\(room.id) - \(room.name)  (\(room.width)x\(room.height))")
    var rows: [[Character]] = (0..<room.height).map { ty in
        (0..<room.width).map { tx in
            switch room.tile(tx, ty) {
            case .solid: return "#"
            case .platform: return "="
            case .balken: return "b"
            case .spike: return "^"
            case .spikeDown: return "v"
            case .spikeLeft: return "<"
            case .spikeRight: return ">"
            case .dissoWall: return "D"
            case .slopeUp: return "/"
            case .slopeDown: return "\\"
            case .slopeUpLow: return "1"
            case .slopeUpHigh: return "2"
            case .slopeDownHigh: return "3"
            case .slopeDownLow: return "4"
            case .ceilDownHigh: return "q"
            case .ceilDownLow: return "w"
            case .ceilUpLow: return "e"
            case .ceilUpHigh: return "r"
            case .air: return " "
            }
        }
    }
    for encoded in result.reachableTiles {
        let ty = encoded / room.width
        let tx = encoded % room.width
        if ty > 0 { rows[ty - 1][tx] = "o" }
    }
    for target in targets {
        let tx = Int(target.area.center.x / tileSize)
        let ty = Int(target.area.center.y / tileSize)
        if room.inBounds(tx, ty) {
            rows[ty][tx] = result.reached.contains(target.name) ? "T" : "?"
        }
    }
    for (i, row) in rows.enumerated() {
        print(String(format: "%3d ", i) + String(row))
    }
    print("\nerreichbar \(result.reachableSurfaces)/\(result.totalSurfaces)")
    for target in result.unreached { print("  ? \(target.name)") }
    return result.ok ? 0 : 1
}

/// Zeigt fuer eine einzelne Standflaeche, wohin jede Bewegungsvariante fuehrt.
func trace(roomID: String, tx: Int, ty: Int, abilities: Set<Ability>) throws -> Int32 {
    let catalog = try WorldCatalog()
    let room = try catalog.room(roomID)
    let probe = ReachabilityProbe(room: room,
                                  progression: Progression(abilities: abilities,
                                                           kerne: Set(Kern.allCases)))
    print("\(roomID) von Kachel (\(tx),\(ty)):")
    for entry in probe.trace(fromTile: tx, ty) {
        let where_ = entry.landing.map { "(\($0.0),\($0.1))" } ?? "-"
        print("  \(entry.program.padding(toLength: 22, withPad: " ", startingAt: 0)) -> "
            + "\(where_.padding(toLength: 10, withPad: " ", startingAt: 0)) \(entry.note)")
    }
    return 0
}

let arguments = CommandLine.arguments
do {
    if let index = arguments.firstIndex(of: "--trace"), index + 3 < arguments.count {
        var abilities = Set(Ability.allCases)
        if let k = arguments.firstIndex(of: "--koennen"), k + 1 < arguments.count {
            let list = arguments[k + 1]
            abilities = list == "-" ? [] : Set(list.split(separator: ",").compactMap {
                Ability(rawValue: String($0))
            })
        }
        exit(try trace(roomID: arguments[index + 1],
                       tx: Int(arguments[index + 2]) ?? 0,
                       ty: Int(arguments[index + 3]) ?? 0,
                       abilities: abilities))
    }
    if let index = arguments.firstIndex(of: "--map"), index + 1 < arguments.count {
        // Optional: --koennen fluegelschlag,herzschlag  (Standard: alles)
        var abilities = Set(Ability.allCases)
        if let k = arguments.firstIndex(of: "--koennen"), k + 1 < arguments.count {
            let list = arguments[k + 1]
            abilities = list == "-" ? [] : Set(list.split(separator: ",").compactMap {
                Ability(rawValue: String($0))
            })
        }
        exit(try drawMap(roomID: arguments[index + 1], abilities: abilities))
    }
    exit(try run())
} catch {
    FileHandle.standardError.write(Data("Pruefung fehlgeschlagen: \(error)\n".utf8))
    exit(2)
}
