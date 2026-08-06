import Foundation

public enum RoomKind: String, Sendable, CaseIterable {
    case start
    case combat
    case treasure
    case shop
    case boss
    case reward   // post-boss room with the floor's reward pedestal
    case secret

    public var spawnsEnemies: Bool { self == .combat }
    public var minimapKey: String {
        switch self {
        case .start: return "start"
        case .combat: return "normal"
        case .treasure: return "treasure"
        case .shop: return "shop"
        case .boss: return "boss"
        case .reward: return "treasure"
        case .secret: return "unknown"
        }
    }
}

public struct Door: Sendable, Equatable {
    public var tileX: Int
    public var tileY: Int
    public var side: Cardinal
    public var roomA: Int
    public var roomB: Int
    public var locked: Bool
    public var isBossDoor: Bool

    public var axis: String { side == .north || side == .south ? "h" : "v" }
}

public struct Room: Sendable {
    public let index: Int
    public var kind: RoomKind
    /// Cell footprint on the coarse grid.
    public var cells: [GridCell]
    /// Floor area in tiles, excluding the wall ring.
    public var floorRect: TileRect
    public var doors: [Int] = []
    public var cleared: Bool = false
    public var visited: Bool = false
    public var discovered: Bool = false
    /// Distance from the start room, in rooms. Drives difficulty and where
    /// the boss goes.
    public var depth: Int = 0

    public var centerTile: (Int, Int) {
        (floorRect.x + floorRect.width / 2, floorRect.y + floorRect.height / 2)
    }

    public var center: Vec2 {
        Vec2((Double(floorRect.x) + Double(floorRect.width) / 2) * TileMap.tileSize,
             (Double(floorRect.y) + Double(floorRect.height) / 2) * TileMap.tileSize)
    }

    public var worldRect: Rect {
        Rect(x: Double(floorRect.x) * TileMap.tileSize,
             y: Double(floorRect.y) * TileMap.tileSize,
             width: Double(floorRect.width) * TileMap.tileSize,
             height: Double(floorRect.height) * TileMap.tileSize)
    }
}

public struct GridCell: Hashable, Sendable {
    public var x: Int
    public var y: Int
    public init(_ x: Int, _ y: Int) { self.x = x; self.y = y }

    public func offset(_ dir: Cardinal) -> GridCell {
        switch dir {
        case .north: return GridCell(x, y - 1)
        case .south: return GridCell(x, y + 1)
        case .east: return GridCell(x + 1, y)
        case .west: return GridCell(x - 1, y)
        }
    }
}

public struct TileRect: Sendable, Equatable {
    public var x: Int
    public var y: Int
    public var width: Int
    public var height: Int

    public func contains(_ tx: Int, _ ty: Int) -> Bool {
        tx >= x && ty >= y && tx < x + width && ty < y + height
    }
}

/// One generated floor: tiles, rooms, doors and the props scattered in them.
public struct Dungeon: Sendable {
    public var map: TileMap
    public var rooms: [Room]
    public var doors: [Door]
    public var theme: String
    public var startRoom: Int
    public var bossRoom: Int
    public var props: [PropPlacement]
    public var seed: UInt64

    public func room(at point: Vec2) -> Int? { map.room(at: point) }
}

public struct PropPlacement: Sendable {
    public var name: String
    public var position: Vec2
    public var room: Int
    public var blocking: Bool
    public var destructible: Bool
}

/// Grid-of-rooms generator.
///
/// Rooms sit on a coarse grid and connect only to orthogonal neighbours, the
/// way Binding of Isaac lays out a floor. That structure is what makes
/// "clear the room, doors open" and a legible minimap possible; a free-form
/// corridor maze looks prettier in a screenshot and plays worse for a
/// room-clear roguelike.
public struct DungeonGenerator {
    public static let cellW = 19   // tiles per grid cell, including walls
    public static let cellH = 15

    public var gridWidth = 9
    public var gridHeight = 8

    public init() {}

    public func generate(floor: Int, theme: String, seed: UInt64) -> Dungeon {
        var rng = RNG(seed: seed)
        let targetRooms = min(18, 7 + floor * 2 + rng.int(0, 2))

        var occupied = layoutCells(targetRooms: targetRooms, rng: &rng)
        // Deterministic order so the same seed always numbers rooms the same.
        let ordered = occupied.sorted { ($0.y, $0.x) < ($1.y, $1.x) }
        occupied = Set(ordered)

        var rooms = ordered.enumerated().map { index, cell in
            Room(index: index, kind: .combat, cells: [cell],
                 floorRect: TileRect(x: 0, y: 0, width: 0, height: 0))
        }

        var cellToRoom: [GridCell: Int] = [:]
        for room in rooms { cellToRoom[room.cells[0]] = room.index }

        let startCell = ordered.min { a, b in
            (abs(a.x - gridWidth / 2) + abs(a.y - gridHeight / 2)) <
            (abs(b.x - gridWidth / 2) + abs(b.y - gridHeight / 2))
        } ?? ordered[0]
        let startIndex = cellToRoom[startCell]!

        assignDepths(&rooms, cellToRoom: cellToRoom, from: startIndex)
        assignKinds(&rooms, cellToRoom: cellToRoom, start: startIndex, rng: &rng)
        // Sizing happens after kinds are known: a boss room needs the whole
        // cell, or its bullet patterns die against the walls before they ever
        // reach the player.
        for i in rooms.indices {
            rooms[i].floorRect = floorRect(for: rooms[i].cells[0],
                                           kind: rooms[i].kind, rng: &rng)
        }

        var map = TileMap(width: gridWidth * Self.cellW,
                          height: gridHeight * Self.cellH)
        for room in rooms { carve(room: room, into: &map) }

        let doors = connect(rooms: &rooms, cellToRoom: cellToRoom, into: &map)
        let bossIndex = rooms.firstIndex { $0.kind == .boss } ?? startIndex
        rooms[startIndex].visited = true
        rooms[startIndex].discovered = true
        rooms[startIndex].cleared = true

        let props = placeProps(rooms: rooms, map: map, theme: theme, rng: &rng)

        return Dungeon(map: map, rooms: rooms, doors: doors, theme: theme,
                       startRoom: startIndex, bossRoom: bossIndex,
                       props: props, seed: seed)
    }

    // -- layout -------------------------------------------------------------

    /// Random growth from the centre. Cells with three or more occupied
    /// neighbours are rejected, which keeps the floor branchy instead of
    /// collapsing into a solid blob.
    private func layoutCells(targetRooms: Int, rng: inout RNG) -> Set<GridCell> {
        var occupied: Set<GridCell> = []
        var frontier: [GridCell] = []
        let start = GridCell(gridWidth / 2, gridHeight / 2)
        occupied.insert(start)
        frontier.append(start)

        var guardCounter = 0
        while occupied.count < targetRooms && guardCounter < 4000 {
            guardCounter += 1
            guard !frontier.isEmpty else { break }
            let from = frontier[rng.index(frontier.count)]
            let dir = Cardinal.allCases[rng.index(4)]
            let candidate = from.offset(dir)

            guard candidate.x >= 0, candidate.y >= 0,
                  candidate.x < gridWidth, candidate.y < gridHeight,
                  !occupied.contains(candidate) else { continue }

            let neighbours = Cardinal.allCases
                .filter { occupied.contains(candidate.offset($0)) }.count
            if neighbours > 1 && rng.chance(0.75) { continue }

            occupied.insert(candidate)
            frontier.append(candidate)
            if frontier.count > 12 { frontier.removeFirst() }
        }
        return occupied
    }

    /// A room's floor is its cell minus a wall ring, jittered a little so
    /// rooms are not all the same rectangle. Arena rooms skip the jitter.
    private func floorRect(for cell: GridCell, kind: RoomKind,
                           rng: inout RNG) -> TileRect {
        let arena = kind == .boss || kind == .shop
        let inset = arena ? 1 : rng.int(1, 2)
        let shrinkX = arena ? 0 : rng.int(0, 2)
        let shrinkY = arena ? 0 : rng.int(0, 1)
        return TileRect(
            x: cell.x * Self.cellW + 1 + inset + shrinkX,
            y: cell.y * Self.cellH + 1 + inset + shrinkY,
            width: Self.cellW - 2 - inset * 2 - shrinkX * 2,
            height: Self.cellH - 2 - inset * 2 - shrinkY * 2
        )
    }

    private func carve(room: Room, into map: inout TileMap) {
        let r = room.floorRect
        for ty in r.y..<(r.y + r.height) {
            for tx in r.x..<(r.x + r.width) {
                map[tx, ty] = .floor
                map.setRoom(room.index, x: tx, y: ty)
            }
        }
    }

    // -- graph --------------------------------------------------------------

    private func assignDepths(_ rooms: inout [Room],
                              cellToRoom: [GridCell: Int], from start: Int) {
        var depths = [Int](repeating: Int.max, count: rooms.count)
        depths[start] = 0
        var queue = [start]
        var head = 0
        while head < queue.count {
            let current = queue[head]
            head += 1
            let cell = rooms[current].cells[0]
            for dir in Cardinal.allCases {
                guard let next = cellToRoom[cell.offset(dir)] else { continue }
                if depths[next] > depths[current] + 1 {
                    depths[next] = depths[current] + 1
                    queue.append(next)
                }
            }
        }
        for i in rooms.indices {
            rooms[i].depth = depths[i] == Int.max ? 0 : depths[i]
        }
    }

    /// Special rooms go on dead ends, so taking a detour to a shop never
    /// blocks the path to the boss.
    private func assignKinds(_ rooms: inout [Room], cellToRoom: [GridCell: Int],
                             start: Int, rng: inout RNG) {
        rooms[start].kind = .start

        func neighbourCount(_ index: Int) -> Int {
            let cell = rooms[index].cells[0]
            return Cardinal.allCases.filter { cellToRoom[cell.offset($0)] != nil }.count
        }

        var deadEnds = rooms.indices
            .filter { $0 != start && neighbourCount($0) == 1 }
            .sorted { rooms[$0].depth > rooms[$1].depth }

        if let bossIndex = deadEnds.first {
            rooms[bossIndex].kind = .boss
            deadEnds.removeFirst()
        } else if let deepest = rooms.indices.filter({ $0 != start })
            .max(by: { rooms[$0].depth < rooms[$1].depth }) {
            rooms[deepest].kind = .boss
        }

        var remaining = rng.shuffled(deadEnds)
        if let treasure = remaining.popLast() { rooms[treasure].kind = .treasure }
        if let shop = remaining.popLast() { rooms[shop].kind = .shop }
        if let secret = remaining.popLast(), rng.chance(0.6) {
            rooms[secret].kind = .secret
        }
        if rooms.count > 12, let extra = remaining.popLast(), rng.chance(0.5) {
            rooms[extra].kind = .treasure
        }
    }

    /// Opens a two-tile doorway in the wall between adjacent rooms.
    private func connect(rooms: inout [Room], cellToRoom: [GridCell: Int],
                         into map: inout TileMap) -> [Door] {
        var doors: [Door] = []
        var seen: Set<Int> = []

        for room in rooms {
            let cell = room.cells[0]
            for dir in [Cardinal.east, Cardinal.south] {
                guard let otherIndex = cellToRoom[cell.offset(dir)] else { continue }
                let key = min(room.index, otherIndex) * 1000 + max(room.index, otherIndex)
                if seen.contains(key) { continue }
                seen.insert(key)

                let other = rooms[otherIndex]
                let isBossDoor = room.kind == .boss || other.kind == .boss
                let locked = room.kind == .secret || other.kind == .secret

                guard let door = carveDoorway(from: room, to: other, side: dir,
                                              into: &map) else { continue }
                var made = door
                made.locked = locked
                made.isBossDoor = isBossDoor
                doors.append(made)
                rooms[room.index].doors.append(doors.count - 1)
                rooms[otherIndex].doors.append(doors.count - 1)
            }
        }
        return doors
    }

    private func carveDoorway(from: Room, to: Room, side: Cardinal,
                              into map: inout TileMap) -> Door? {
        let a = from.floorRect, b = to.floorRect

        if side == .east {
            let overlapLo = max(a.y, b.y)
            let overlapHi = min(a.y + a.height, b.y + b.height)
            guard overlapHi - overlapLo >= 2 else { return nil }
            let doorY = (overlapLo + overlapHi) / 2 - 1
            for tx in (a.x + a.width)..<b.x {
                for ty in doorY..<(doorY + 2) {
                    map[tx, ty] = .doorway
                    map.setRoom(from.index, x: tx, y: ty)
                }
            }
            return Door(tileX: a.x + a.width, tileY: doorY, side: .east,
                        roomA: from.index, roomB: to.index,
                        locked: false, isBossDoor: false)
        }

        let overlapLo = max(a.x, b.x)
        let overlapHi = min(a.x + a.width, b.x + b.width)
        guard overlapHi - overlapLo >= 2 else { return nil }
        let doorX = (overlapLo + overlapHi) / 2 - 1
        for ty in (a.y + a.height)..<b.y {
            for tx in doorX..<(doorX + 2) {
                map[tx, ty] = .doorway
                map.setRoom(from.index, x: tx, y: ty)
            }
        }
        return Door(tileX: doorX, tileY: a.y + a.height, side: .south,
                    roomA: from.index, roomB: to.index,
                    locked: false, isBossDoor: false)
    }

    // -- decoration ---------------------------------------------------------

    private func placeProps(rooms: [Room], map: TileMap, theme: String,
                            rng: inout RNG) -> [PropPlacement] {
        var props: [PropPlacement] = []

        for room in rooms {
            let r = room.floorRect
            // Keep a clear ring near doorways so props never wall one off.
            func freeSpot() -> Vec2? {
                for _ in 0..<12 {
                    let tx = rng.int(r.x + 1, r.x + r.width - 2)
                    let ty = rng.int(r.y + 1, r.y + r.height - 2)
                    let center = map.tileCenter(tx, ty)
                    let tooClose = props.contains {
                        $0.position.distanceSquared(to: center) < 24 * 24
                    }
                    if !tooClose && !map.isSolid(tx, ty) { return center }
                }
                return nil
            }

            switch room.kind {
            case .shop:
                if let spot = freeSpot() {
                    props.append(PropPlacement(name: "shop_counter",
                                               position: spot, room: room.index,
                                               blocking: true, destructible: false))
                }
            case .treasure, .reward:
                props.append(PropPlacement(name: "chest_rare",
                                           position: room.center, room: room.index,
                                           blocking: false, destructible: false))
            case .boss:
                for side in [-1.0, 1.0] {
                    props.append(PropPlacement(
                        name: "pillar",
                        position: room.center + Vec2(side * 5 * TileMap.tileSize,
                                                     -3 * TileMap.tileSize),
                        room: room.index, blocking: true, destructible: false))
                }
            case .start:
                props.append(PropPlacement(name: "statue",
                                           position: room.center - Vec2(0, 40),
                                           room: room.index,
                                           blocking: true, destructible: false))
            default:
                let count = rng.int(1, 4)
                for _ in 0..<count {
                    guard let spot = freeSpot() else { continue }
                    let name = rng.weighted([
                        ("barrel", 3.0), ("crate", 3.0),
                        ("barrel_explosive", 1.2), ("bone_pile", 1.5),
                        ("pillar", 0.8),
                    ]) ?? "barrel"
                    props.append(PropPlacement(
                        name: name, position: spot, room: room.index,
                        blocking: name == "pillar",
                        destructible: name != "pillar" && name != "bone_pile"))
                }
            }

            // Torches on the north wall of every room, for light and rhythm.
            let torchCount = max(1, r.width / 6)
            for i in 0..<torchCount {
                let tx = r.x + 2 + i * (r.width - 4) / max(1, torchCount - 1 == 0 ? 1 : torchCount - 1)
                props.append(PropPlacement(
                    name: "torch",
                    // The wall face is drawn over the room's first floor row,
                    // so the torch hangs one row lower than the wall tile to
                    // land on the face rather than on the cap above it.
                    position: Vec2((Double(min(tx, r.x + r.width - 1)) + 0.5) * TileMap.tileSize,
                                   Double(r.y + 1) * TileMap.tileSize),
                    room: room.index, blocking: false, destructible: false))
            }
        }
        return props
    }
}
