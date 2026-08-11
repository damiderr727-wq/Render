import Foundation

/// Prueft Raumgeometrie gegen die echte Spielphysik.
///
/// Von Hand gesetzte Plattformen sind schnell einen halben Sprung zu weit
/// auseinander. Statt das im Spiel zu merken, simuliert dieses Werkzeug einen
/// Spieler mit einem gegebenen Koennen: Es faechert von jeder begehbaren
/// Flaeche eine Reihe von Sprungvarianten auf, verfolgt ihre Flugbahnen und
/// baut daraus einen Graphen begehbarer Flaechen.
///
/// Weil es dieselbe `Player`-Klasse und dieselben `Tuning`-Werte benutzt wie
/// das Spiel, koennen Physik und Levelbau nicht auseinanderlaufen.
public struct ReachabilityProbe {
    /// Ein Ziel, das erreichbar sein muss.
    public struct Target {
        public enum Kind: String { case pickup, door, bench, boss }
        public let name: String
        public let kind: Kind
        public let area: Rect

        public init(name: String, kind: Kind, area: Rect) {
            self.name = name
            self.kind = kind
            self.area = area
        }
    }

    public struct Result {
        public let roomID: String
        public let reachableSurfaces: Int
        public let totalSurfaces: Int
        public let reached: Set<String>
        public let unreached: [Target]
        /// Erreichte Standflaechen, kodiert als `ty * width + tx`.
        public let reachableTiles: Set<Int>

        public var ok: Bool { unreached.isEmpty }
    }

    /// Eine Flaeche, auf der man stehen kann: Kachel mit Luft darueber.
    private struct Surface: Hashable {
        let tx: Int
        let ty: Int
    }

    public let room: Room
    public let progression: Progression
    /// Wie lange eine einzelne Flugbahn hoechstens verfolgt wird.
    public var maxFlightTime: Double = 2.4
    public var dt: Double = 1.0 / 60.0

    public init(room: Room, progression: Progression) {
        self.room = room
        self.progression = progression
    }

    // MARK: - Flaechen

    private func surfaces() -> [Surface] {
        var out: [Surface] = []
        let headroom = Int(ceil(Tuning.playerHeight / tileSize))
        for ty in 1..<room.height {
            for tx in 0..<room.width where room.tile(tx, ty).isStandable {
                // Auf einer Schraege steht man in der Kachel selbst.
                guard room.tile(tx, ty).isSlope || room.tile(tx, ty - 1) == .air
                else { continue }
                var clear = true
                for h in 1...headroom where room.tile(tx, ty - h).isBlocking {
                    clear = false
                    break
                }
                guard clear else { continue }
                out.append(Surface(tx: tx, ty: ty))
            }
        }
        return out
    }

    private func standPosition(_ s: Surface) -> Vec2 {
        Vec2(Double(s.tx) * tileSize + tileSize / 2, Double(s.ty) * tileSize)
    }

    private func surface(under position: Vec2) -> Surface? {
        let tx = Int(floor(position.x / tileSize))
        let ty = Int(floor((position.y + 1) / tileSize))
        guard room.inBounds(tx, ty), room.tile(tx, ty).isStandable else { return nil }
        return Surface(tx: tx, ty: ty)
    }

    // MARK: - Eingabeprogramme

    /// Eine Bewegungsabsicht ueber die Zeit. Die Auswahl deckt die Varianten
    /// ab, die ein Mensch tatsaechlich spielt.
    private struct Program {
        let name: String
        let make: (Double, Player) -> PlayerInput
    }

    private func programs() -> [Program] {
        var result: [Program] = []
        let canDouble = progression.has(.fluegelschlag)
        let canWall = progression.has(.klangschritt)
        let canDash = progression.has(.herzschlag)

        for dir in [-1.0, 0.0, 1.0] {
            // Gehen und fallen lassen.
            result.append(Program(name: "walk\(Int(dir))") { _, _ in
                PlayerInput(moveX: dir)
            })

            // Voller Sprung und angetippter Sprung.
            for (label, holdTime) in [("full", 10.0), ("tap", 0.09)] {
                result.append(Program(name: "jump-\(label)\(Int(dir))") { t, _ in
                    PlayerInput(moveX: dir, jumpHeld: t < holdTime, jumpPressed: t < 0.001)
                })
            }

            guard canDouble else { continue }
            // Doppelsprung zu verschiedenen Zeitpunkten.
            for delay in [0.14, 0.26, 0.40] {
                result.append(Program(name: "double\(delay)-\(Int(dir))") { t, _ in
                    let second = t >= delay && t < delay + 0.02
                    return PlayerInput(moveX: dir,
                                       jumpHeld: true,
                                       jumpPressed: t < 0.001 || second)
                })
            }
        }

        if canDash {
            for dir in [-1.0, 1.0] {
                for delay in [0.0, 0.12, 0.3] {
                    result.append(Program(name: "dash\(delay)-\(Int(dir))") { t, _ in
                        PlayerInput(moveX: dir,
                                    jumpHeld: t < 10,
                                    jumpPressed: t < 0.001,
                                    dashPressed: t >= delay && t < delay + 0.02)
                    })
                }
                // Sprung, Doppelsprung, dann Stoss - die maximale Weite.
                if canDouble {
                    result.append(Program(name: "jump-double-dash\(Int(dir))") { t, _ in
                        PlayerInput(moveX: dir,
                                    jumpHeld: true,
                                    jumpPressed: t < 0.001 || (t >= 0.22 && t < 0.24),
                                    dashPressed: t >= 0.42 && t < 0.44)
                    })
                }
            }
        }

        if canWall {
            // Kaminklettern: an der Wand haften und immer wieder abspringen.
            for dir in [-1.0, 1.0] {
                result.append(Program(name: "wallclimb\(Int(dir))") { t, player in
                    // Zur Wand druecken; sobald sie greift, erneut springen.
                    let towards = player.wallSide != 0 ? player.wallSide : dir
                    let jump = player.wallSide != 0 && player.velocity.y > -30
                    return PlayerInput(moveX: towards,
                                       jumpHeld: true,
                                       jumpPressed: t < 0.001 || jump)
                })
            }
        }

        return result
    }

    // MARK: - Simulation

    /// Verfolgt eine Flugbahn und meldet Landeflaeche sowie beruehrte Ziele.
    private func fly(from start: Surface, program: Program, targets: [Target])
        -> (landing: Surface?, touched: Set<String>) {
        let player = Player(position: standPosition(start),
                            progression: progression,
                            kern: .leier)
        player.placeAt(standPosition(start), facing: 1)

        var touched: Set<String> = []
        var events: [GameEvent] = []
        var t = 0.0

        while t < maxFlightTime {
            let input = program.make(t, player)
            events.removeAll(keepingCapacity: true)
            player.update(dt: dt, input: input, room: room, events: &events)
            t += dt

            let body = player.rect
            for target in targets where body.intersects(target.area) {
                touched.insert(target.name)
            }

            // Dornen beenden den Versuch - dort will niemand landen.
            if room.overlapsHazard(body.inset(by: 2)) {
                return (nil, touched)
            }

            // Gelandet: erst ab etwas Flugzeit, damit der Start nicht zaehlt.
            if t > 0.12, player.onGround, abs(player.velocity.y) < 1 {
                let landing = surface(under: player.position)
                if landing != start || t > 0.35 {
                    return (landing, touched)
                }
            }
        }
        return (surface(under: player.position), touched)
    }

    // MARK: - Durchlauf

    /// Baut den Erreichbarkeitsgraphen ab den Startflaechen.
    public func run(from origins: [Vec2], targets: [Target]) -> Result {
        let all = surfaces()
        let allSet = Set(all)

        var startSurfaces: Set<Surface> = []
        for origin in origins {
            // Vom Startpunkt nach unten auf die naechste Flaeche fallen lassen.
            if let floorY = room.floorBelow(origin) {
                let candidate = Surface(tx: Int((origin.x / tileSize).rounded(.down)),
                                        ty: Int(floorY / tileSize))
                if allSet.contains(candidate) { startSurfaces.insert(candidate) }
            }
        }
        // Ist der Startpunkt keine saubere Flaeche, die naechstgelegene nehmen.
        if startSurfaces.isEmpty, let origin = origins.first {
            if let nearest = all.min(by: {
                standPosition($0).distance(to: origin) < standPosition($1).distance(to: origin)
            }) {
                startSurfaces.insert(nearest)
            }
        }

        let allPrograms = programs()
        var visited = startSurfaces
        var queue = Array(startSurfaces)
        var reached: Set<String> = []

        // Ziele, die schon am Start beruehrt werden.
        for s in startSurfaces {
            let body = Rect(footAt: standPosition(s), width: Tuning.playerWidth,
                            height: Tuning.playerHeight)
            for target in targets where body.intersects(target.area) {
                reached.insert(target.name)
            }
        }

        while let current = queue.popLast() {
            for program in allPrograms {
                let (landing, touched) = fly(from: current, program: program, targets: targets)
                reached.formUnion(touched)
                guard let landing, allSet.contains(landing), !visited.contains(landing) else { continue }
                visited.insert(landing)
                queue.append(landing)
            }
        }

        let unreached = targets.filter { !reached.contains($0.name) }
        return Result(roomID: room.id,
                      reachableSurfaces: visited.count,
                      totalSurfaces: all.count,
                      reached: reached,
                      unreached: unreached,
                      reachableTiles: Set(visited.map { $0.ty * room.width + $0.tx }))
    }

    /// Listet fuer eine Startflaeche auf, wo jedes Bewegungsprogramm landet.
    /// Dient der Fehlersuche an einzelnen Stellen.
    public func trace(fromTile tx: Int, _ ty: Int) -> [(program: String, landing: (Int, Int)?, note: String)] {
        let start = Surface(tx: tx, ty: ty)
        return programs().map { program in
            let (landing, _) = fly(from: start, program: program, targets: [])
            // Denselben Lauf noch einmal, um den Endzustand zu beschreiben.
            let player = Player(position: standPosition(start), progression: progression,
                                kern: .leier)
            player.placeAt(standPosition(start), facing: 1)
            var events: [GameEvent] = []
            var t = 0.0
            var reason = "zeit"
            while t < maxFlightTime {
                player.update(dt: dt, input: program.make(t, player), room: room, events: &events)
                events.removeAll(keepingCapacity: true)
                t += dt
                if room.overlapsHazard(player.rect.inset(by: 2)) { reason = "dornen"; break }
                if t > 0.12, player.onGround, abs(player.velocity.y) < 1 {
                    let here = surface(under: player.position)
                    if here != start || t > 0.35 { reason = here == nil ? "kein-boden" : "gelandet"; break }
                }
            }
            let note = String(format: "%@ x=%.0f y=%.0f t=%.2f", reason,
                              player.position.x, player.position.y, t)
            return (program.name, landing.map { ($0.tx, $0.ty) }, note)
        }
    }

    // MARK: - Ziele aus den Raumdaten

    /// Alles, was in diesem Raum erreichbar sein muss.
    public static func targets(for room: Room) -> [Target] {
        var out: [Target] = []
        for p in room.data.pickups {
            out.append(Target(name: "\(p.kind):\(p.id)",
                              kind: .pickup,
                              area: Rect(center: Vec2.entity(p.x, p.y), radius: 10)))
        }
        for b in room.data.benches {
            out.append(Target(name: "bench@\(Int(b.x))",
                              kind: .bench,
                              area: Rect(center: Vec2.entity(b.x, b.y - 0.5), radius: 20)))
        }
        for d in room.data.doors {
            out.append(Target(name: "door:\(d.id)->\(d.target)",
                              kind: .door,
                              area: room.doorRect(d)))
        }
        if let boss = room.data.boss {
            out.append(Target(name: "boss:\(boss.type)",
                              kind: .boss,
                              area: Rect(center: Vec2.entity(boss.x, boss.y - 1), radius: 24)))
        }
        return out
    }

    /// Die Punkte, an denen der Spieler den Raum betreten kann.
    public static func origins(for room: Room) -> [Vec2] {
        room.data.spawns.values.map { Vec2.entity($0.x, $0.y) }
    }
}
