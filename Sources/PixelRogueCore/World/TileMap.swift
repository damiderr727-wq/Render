import Foundation

public enum Tile: UInt8, Sendable {
    case wall
    case floor
    case pit
    case doorway

    /// Blocks walking. Pits block movement but not bullets.
    public var blocksMovement: Bool { self != .floor && self != .doorway }
    /// Blocks bullets and line of sight.
    public var blocksSight: Bool { self == .wall }
}

/// The tile grid for one floor.
///
/// World coordinates are pixels with +y downward — the same orientation the
/// art is drawn in — so tile (0,0) covers the world rect (0,0,16,16).
public struct TileMap: Sendable {
    public static let tileSize: Double = 16

    public let width: Int
    public let height: Int
    public private(set) var tiles: [Tile]
    /// Room index per tile, or -1 outside any room. Drives "which room am I
    /// in" without a point-in-rect scan every frame.
    public private(set) var roomIndex: [Int32]

    public init(width: Int, height: Int) {
        self.width = width
        self.height = height
        self.tiles = Array(repeating: .wall, count: width * height)
        self.roomIndex = Array(repeating: -1, count: width * height)
    }

    @inline(__always)
    public func inBounds(_ x: Int, _ y: Int) -> Bool {
        x >= 0 && y >= 0 && x < width && y < height
    }

    public subscript(x: Int, y: Int) -> Tile {
        get { inBounds(x, y) ? tiles[y * width + x] : .wall }
        set { if inBounds(x, y) { tiles[y * width + x] = newValue } }
    }

    public mutating func setRoom(_ index: Int, x: Int, y: Int) {
        guard inBounds(x, y) else { return }
        roomIndex[y * width + x] = Int32(index)
    }

    public func room(atTile x: Int, _ y: Int) -> Int? {
        guard inBounds(x, y) else { return nil }
        let value = roomIndex[y * width + x]
        return value >= 0 ? Int(value) : nil
    }

    public func room(at point: Vec2) -> Int? {
        let (tx, ty) = tileCoord(point)
        return room(atTile: tx, ty)
    }

    // -- coordinate helpers -------------------------------------------------

    @inline(__always)
    public func tileCoord(_ point: Vec2) -> (Int, Int) {
        (Int(floor(point.x / Self.tileSize)), Int(floor(point.y / Self.tileSize)))
    }

    public func tileRect(_ x: Int, _ y: Int) -> Rect {
        Rect(x: Double(x) * Self.tileSize, y: Double(y) * Self.tileSize,
             width: Self.tileSize, height: Self.tileSize)
    }

    public func tileCenter(_ x: Int, _ y: Int) -> Vec2 {
        Vec2((Double(x) + 0.5) * Self.tileSize, (Double(y) + 0.5) * Self.tileSize)
    }

    public var worldBounds: Rect {
        Rect(x: 0, y: 0,
             width: Double(width) * Self.tileSize,
             height: Double(height) * Self.tileSize)
    }

    // -- queries ------------------------------------------------------------

    public func isSolid(_ x: Int, _ y: Int) -> Bool {
        self[x, y].blocksMovement
    }

    public func isWalkable(_ point: Vec2) -> Bool {
        let (tx, ty) = tileCoord(point)
        return !isSolid(tx, ty)
    }

    /// 4-bit neighbour mask used to pick the right autotiled wall cap:
    /// N=1, E=2, S=4, W=8. Out-of-bounds counts as wall so the map edge
    /// doesn't grow a rim.
    public func wallMask(_ x: Int, _ y: Int) -> Int {
        var mask = 0
        if !inBounds(x, y - 1) || self[x, y - 1] == .wall { mask |= 1 }
        if !inBounds(x + 1, y) || self[x + 1, y] == .wall { mask |= 2 }
        if !inBounds(x, y + 1) || self[x, y + 1] == .wall { mask |= 4 }
        if !inBounds(x - 1, y) || self[x - 1, y] == .wall { mask |= 8 }
        return mask
    }

    /// True when this wall tile should also draw a front face below it —
    /// that is, when the tile to its south is walkable.
    public func needsWallFace(_ x: Int, _ y: Int) -> Bool {
        self[x, y] == .wall && !isSolid(x, y + 1)
    }

    /// Solid tile rects overlapping `area`, for circle-vs-world collision.
    public func solidRects(overlapping area: Rect) -> [Rect] {
        let x0 = max(0, Int(floor(area.minX / Self.tileSize)))
        let y0 = max(0, Int(floor(area.minY / Self.tileSize)))
        let x1 = min(width - 1, Int(floor(area.maxX / Self.tileSize)))
        let y1 = min(height - 1, Int(floor(area.maxY / Self.tileSize)))
        guard x0 <= x1, y0 <= y1 else { return [] }

        var rects: [Rect] = []
        rects.reserveCapacity((x1 - x0 + 1) * (y1 - y0 + 1) / 2)
        for y in y0...y1 {
            for x in x0...x1 where isSolid(x, y) {
                rects.append(tileRect(x, y))
            }
        }
        return rects
    }

    /// Pushes a circle out of any solid tile it overlaps.
    /// Runs a couple of passes so corners resolve instead of oscillating.
    public func collide(position: Vec2, radius: Double) -> Vec2 {
        var pos = position
        for _ in 0..<3 {
            let area = Rect(center: pos, size: Vec2(radius * 2 + 2, radius * 2 + 2))
            var moved = false
            for rect in solidRects(overlapping: area) {
                let push = Collision.resolve(circle: pos, radius: radius, rect: rect)
                if push != .zero {
                    pos += push
                    moved = true
                }
            }
            if !moved { break }
        }
        return pos
    }

    /// Bresenham line of sight over tile centres. Used by ranged AI so
    /// enemies don't shoot through walls.
    public func hasLineOfSight(from: Vec2, to: Vec2) -> Bool {
        var (x0, y0) = tileCoord(from)
        let (x1, y1) = tileCoord(to)
        let dx = abs(x1 - x0), dy = -abs(y1 - y0)
        let sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1
        var err = dx + dy

        while true {
            if self[x0, y0].blocksSight { return false }
            if x0 == x1 && y0 == y1 { return true }
            let e2 = 2 * err
            if e2 >= dy { err += dy; x0 += sx }
            if e2 <= dx { err += dx; y0 += sy }
        }
    }

    /// First solid tile a ray hits, sampled at sub-tile steps. Returns the
    /// impact point, or nil within `maxDistance`.
    public func raycast(from origin: Vec2, direction: Vec2,
                        maxDistance: Double) -> Vec2? {
        let dir = direction.normalized
        guard dir != .zero else { return nil }
        let step = Self.tileSize * 0.25
        var travelled = 0.0
        var previous = origin
        while travelled < maxDistance {
            travelled += step
            let point = origin + dir * travelled
            let (tx, ty) = tileCoord(point)
            if self[tx, ty].blocksSight {
                return previous
            }
            previous = point
        }
        return nil
    }

    /// Nearest walkable point, spiralling outward. Used when a spawn or a
    /// teleport lands inside geometry.
    public func nearestWalkable(to point: Vec2, maxRadius: Int = 8) -> Vec2 {
        if isWalkable(point) { return point }
        let (cx, cy) = tileCoord(point)
        for r in 1...maxRadius {
            for dy in -r...r {
                for dx in -r...r where abs(dx) == r || abs(dy) == r {
                    let x = cx + dx, y = cy + dy
                    if inBounds(x, y) && !isSolid(x, y) {
                        return tileCenter(x, y)
                    }
                }
            }
        }
        return point
    }
}
