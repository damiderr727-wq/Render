import Foundation

/// Ein geladener Raum mit veraenderlichem Zustand (zerschlagene Sperren,
/// eingesammelte Fundstuecke).
public final class Room {
    public let data: RoomData
    public private(set) var tiles: [Tile]

    public var id: String { data.id }
    public var name: String { data.name }
    public var region: Region { data.region }
    public var width: Int { data.width }
    public var height: Int { data.height }

    /// Raumgrenzen in Punkten.
    public var bounds: Rect {
        Rect(x: 0, y: 0, width: Double(width) * tileSize, height: Double(height) * tileSize)
    }

    public init(data: RoomData) {
        self.data = data
        var t = [Tile](repeating: .air, count: data.width * data.height)
        for (row, line) in data.tiles.enumerated() where row < data.height {
            for (col, ch) in line.enumerated() where col < data.width {
                t[row * data.width + col] = Tile(character: ch)
            }
        }
        self.tiles = t
    }

    // MARK: - Kachelzugriff

    @inlinable
    public func inBounds(_ tx: Int, _ ty: Int) -> Bool {
        tx >= 0 && ty >= 0 && tx < width && ty < height
    }

    /// Ausserhalb des Raums gilt Fels - so kann nichts hinausfallen.
    public func tile(_ tx: Int, _ ty: Int) -> Tile {
        guard inBounds(tx, ty) else { return .solid }
        return tiles[ty * width + tx]
    }

    public func tile(at point: Vec2) -> Tile {
        tile(Int(floor(point.x / tileSize)), Int(floor(point.y / tileSize)))
    }

    public func setTile(_ tx: Int, _ ty: Int, _ tile: Tile) {
        guard inBounds(tx, ty) else { return }
        tiles[ty * width + tx] = tile
    }

    /// Bricht eine verstimmte Sperre auf und meldet die betroffenen Kacheln.
    @discardableResult
    public func breakWalls(in area: Rect) -> [(Int, Int)] {
        var broken: [(Int, Int)] = []
        let x0 = Int(floor(area.minX / tileSize))
        let x1 = Int(floor(area.maxX / tileSize))
        let y0 = Int(floor(area.minY / tileSize))
        let y1 = Int(floor(area.maxY / tileSize))
        for ty in y0...max(y0, y1) {
            for tx in x0...max(x0, x1) where tile(tx, ty) == .dissoWall {
                setTile(tx, ty, .air)
                broken.append((tx, ty))
            }
        }
        return broken
    }

    // MARK: - Kollision

    /// Liegt ein blockierender Baustein im Rechteck?
    public func overlapsSolid(_ rect: Rect) -> Bool {
        forEachTile(in: rect) { tile, _, _ in tile.isBlocking } != nil
    }

    public func overlapsHazard(_ rect: Rect) -> Bool {
        forEachTile(in: rect) { tile, _, _ in tile.isHazard } != nil
    }

    /// Eine Einwegplattform zaehlt nur, wenn die Figur von oben kommt: ihre
    /// Fusslinie muss oberhalb der Plattformkante liegen.
    public func overlapsGround(_ rect: Rect, previousBottom: Double) -> Bool {
        if overlapsSolid(rect) { return true }
        return forEachTile(in: rect) { tile, _, ty in
            guard tile.isOneWay else { return false }
            let top = Double(ty) * tileSize
            return previousBottom <= top + 0.5
        } != nil
    }

    /// Sucht die erste Kachel im Rechteck, fuer die `predicate` zutrifft.
    @discardableResult
    public func forEachTile(in rect: Rect, _ predicate: (Tile, Int, Int) -> Bool) -> (Int, Int)? {
        let x0 = Int(floor(rect.minX / tileSize))
        let x1 = Int(floor((rect.maxX - 0.0001) / tileSize))
        let y0 = Int(floor(rect.minY / tileSize))
        let y1 = Int(floor((rect.maxY - 0.0001) / tileSize))
        guard x1 >= x0, y1 >= y0 else { return nil }
        for ty in y0...y1 {
            for tx in x0...x1 where predicate(tile(tx, ty), tx, ty) {
                return (tx, ty)
            }
        }
        return nil
    }

    /// Hoehe der Schraegen-Oberflaeche an einer Weltposition, sonst `nil`.
    ///
    /// Eine 45-Grad-Schraege ist die einfachste Form, die sich sauber in ein
    /// Kachelraster fuegt: an einer Kante liegt die Oberflaeche oben, an der
    /// anderen unten, dazwischen linear.
    public func slopeSurfaceY(_ tx: Int, _ ty: Int, worldX: Double) -> Double? {
        let tile = tile(tx, ty)
        guard tile.isSlope else { return nil }
        let localX = clamp((worldX - Double(tx) * tileSize) / tileSize, 0, 1)
        let top = Double(ty) * tileSize
        let rise = tile == .slopeUp ? (1 - localX) : localX
        return top + rise * tileSize
    }

    /// Sucht an der Fusslinie nach einer Schraege und meldet deren Hoehe.
    public func slopeUnder(footX: Double, footY: Double, tolerance: Double = 12) -> Double? {
        let tx = Int(floor(footX / tileSize))
        let center = Int(floor(footY / tileSize))
        for ty in [center, center - 1, center + 1] {
            guard let surface = slopeSurfaceY(tx, ty, worldX: footX) else { continue }
            if footY >= surface - tolerance && footY <= surface + tolerance {
                return surface
            }
        }
        return nil
    }

    /// Erste begehbare Oberflaeche unterhalb von `point` (in Punkten).
    public func floorBelow(_ point: Vec2, maxTiles: Int = 64) -> Double? {
        let tx = Int(floor(point.x / tileSize))
        var ty = Int(floor(point.y / tileSize))
        for _ in 0..<maxTiles {
            if let surface = slopeSurfaceY(tx, ty, worldX: point.x) {
                return surface
            }
            if tile(tx, ty).isStandable {
                return Double(ty) * tileSize
            }
            ty += 1
            if ty >= height { return nil }
        }
        return nil
    }

    // MARK: - Inhalte

    public func spawn(named name: String) -> RoomData.SpawnPoint? {
        data.spawns[name]
    }

    public func door(named name: String) -> RoomData.Door? {
        data.doors.first { $0.id == name }
    }

    /// Tuerflaeche in Punkten, etwas grosszuegiger als das Kachelrechteck,
    /// damit der Uebergang nicht knapp verfehlt wird.
    public func doorRect(_ door: RoomData.Door) -> Rect {
        Rect(x: Double(door.x) * tileSize - 2,
             y: Double(door.y) * tileSize,
             width: Double(door.w) * tileSize + 4,
             height: Double(door.h) * tileSize)
    }
}
