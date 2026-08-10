import Foundation

/// Die Welt rechnet in Punkten, nicht in Kacheln. Eine Kachel ist 16 Punkte
/// gross - genau die Aufloesung, in der die Pixelgrafik gezeichnet wurde.
public let tileSize: Double = 16

/// Achtung: y waechst nach unten, wie im Kachelraster. Die Darstellung
/// spiegelt das beim Zeichnen; die Logik bleibt dadurch frei von Vorzeichen-
/// akrobatik.
public struct Vec2: Equatable, Hashable, Codable, Sendable {
    public var x: Double
    public var y: Double

    public init(_ x: Double = 0, _ y: Double = 0) {
        self.x = x
        self.y = y
    }

    public static let zero = Vec2(0, 0)

    public var length: Double { (x * x + y * y).squareRoot() }
    public var lengthSquared: Double { x * x + y * y }

    public var normalized: Vec2 {
        let l = length
        return l > 1e-9 ? Vec2(x / l, y / l) : .zero
    }

    public func distance(to other: Vec2) -> Double { (self - other).length }

    public static func + (a: Vec2, b: Vec2) -> Vec2 { Vec2(a.x + b.x, a.y + b.y) }
    public static func - (a: Vec2, b: Vec2) -> Vec2 { Vec2(a.x - b.x, a.y - b.y) }
    public static func * (a: Vec2, s: Double) -> Vec2 { Vec2(a.x * s, a.y * s) }
    public static func * (s: Double, a: Vec2) -> Vec2 { a * s }
    public static func / (a: Vec2, s: Double) -> Vec2 { Vec2(a.x / s, a.y / s) }
    public static func += (a: inout Vec2, b: Vec2) { a = a + b }
    public static func -= (a: inout Vec2, b: Vec2) { a = a - b }
    public static prefix func - (a: Vec2) -> Vec2 { Vec2(-a.x, -a.y) }

    /// Kachelecke -> Punktkoordinate (fuer Gelaende und Rechtecke).
    public static func tiles(_ x: Double, _ y: Double) -> Vec2 {
        Vec2(x * tileSize, y * tileSize)
    }

    /// Entitaetskoordinate -> Punktkoordinate.
    ///
    /// In den Leveldaten benennt `x` die Kachelspalte und `y` die Fusslinie.
    /// Eine Figur steht in der Mitte ihrer Spalte, nicht auf deren linker
    /// Kante - sonst ragt ihr halber Koerper in die Nachbarkachel.
    public static func entity(_ x: Double, _ y: Double) -> Vec2 {
        Vec2(x * tileSize + tileSize / 2, y * tileSize)
    }
}

public struct Rect: Equatable, Codable, Sendable {
    public var x: Double
    public var y: Double
    public var width: Double
    public var height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    /// Rechteck aus Mittelpunkt-unten (Fusspunkt) heraus.
    public init(footAt foot: Vec2, width: Double, height: Double) {
        self.init(x: foot.x - width / 2, y: foot.y - height, width: width, height: height)
    }

    public init(center: Vec2, radius: Double) {
        self.init(x: center.x - radius, y: center.y - radius, width: radius * 2, height: radius * 2)
    }

    public var minX: Double { x }
    public var maxX: Double { x + width }
    public var minY: Double { y }
    public var maxY: Double { y + height }
    public var center: Vec2 { Vec2(x + width / 2, y + height / 2) }
    public var foot: Vec2 { Vec2(x + width / 2, y + height) }

    public func intersects(_ other: Rect) -> Bool {
        minX < other.maxX && maxX > other.minX && minY < other.maxY && maxY > other.minY
    }

    public func contains(_ p: Vec2) -> Bool {
        p.x >= minX && p.x <= maxX && p.y >= minY && p.y <= maxY
    }

    public func inset(by d: Double) -> Rect {
        Rect(x: x + d, y: y + d, width: width - d * 2, height: height - d * 2)
    }

    public func offset(by v: Vec2) -> Rect {
        Rect(x: x + v.x, y: y + v.y, width: width, height: height)
    }

    /// Kuerzeste Strecke vom Rechteckrand zum Punkt (0, wenn innen).
    public func distance(to p: Vec2) -> Double {
        let dx = max(minX - p.x, 0, p.x - maxX)
        let dy = max(minY - p.y, 0, p.y - maxY)
        return (dx * dx + dy * dy).squareRoot()
    }
}

// MARK: - Hilfsfunktionen

@inlinable
public func clamp<T: Comparable>(_ v: T, _ lo: T, _ hi: T) -> T {
    min(max(v, lo), hi)
}

@inlinable
public func lerp(_ a: Double, _ b: Double, _ t: Double) -> Double {
    a + (b - a) * t
}

/// Bewegt `value` um hoechstens `step` in Richtung `target`.
@inlinable
public func approach(_ value: Double, _ target: Double, _ step: Double) -> Double {
    value < target ? min(value + step, target) : max(value - step, target)
}

/// Bilduebergreifend gleichmaessiges Glaetten (unabhaengig von der Bildrate).
@inlinable
public func damp(_ a: Double, _ b: Double, rate: Double, dt: Double) -> Double {
    lerp(a, b, 1 - pow(1 - rate, dt * 60))
}

@inlinable
public func sign(_ v: Double) -> Double {
    v < 0 ? -1 : (v > 0 ? 1 : 0)
}

/// Deterministischer Zufall - gleiche Eingabe, gleiches Spiel.
public struct Rng: Sendable {
    private var state: UInt64

    public init(seed: UInt64 = 0x9E3779B97F4A7C15) {
        state = seed == 0 ? 1 : seed
    }

    public mutating func nextUInt() -> UInt64 {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }

    public mutating func next() -> Double {
        Double(nextUInt() >> 11) * (1.0 / 9007199254740992.0)
    }

    public mutating func range(_ a: Double, _ b: Double) -> Double {
        a + next() * (b - a)
    }

    public mutating func int(_ a: Int, _ b: Int) -> Int {
        guard b > a else { return a }
        return a + Int(nextUInt() % UInt64(b - a + 1))
    }

    public mutating func chance(_ p: Double) -> Bool {
        next() < p
    }
}
