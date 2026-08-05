import Foundation

/// 2D vector in world units. One world unit is one pixel of source art;
/// the renderer applies the camera zoom on top.
public struct Vec2: Equatable, Hashable, Sendable {
    public var x: Double
    public var y: Double

    public init(_ x: Double, _ y: Double) {
        self.x = x
        self.y = y
    }

    public static let zero = Vec2(0, 0)
    public static let up = Vec2(0, -1)
    public static let down = Vec2(0, 1)
    public static let left = Vec2(-1, 0)
    public static let right = Vec2(1, 0)

    public static func + (a: Vec2, b: Vec2) -> Vec2 { Vec2(a.x + b.x, a.y + b.y) }
    public static func - (a: Vec2, b: Vec2) -> Vec2 { Vec2(a.x - b.x, a.y - b.y) }
    public static func * (v: Vec2, s: Double) -> Vec2 { Vec2(v.x * s, v.y * s) }
    public static func * (s: Double, v: Vec2) -> Vec2 { Vec2(v.x * s, v.y * s) }
    public static func / (v: Vec2, s: Double) -> Vec2 { Vec2(v.x / s, v.y / s) }
    public static prefix func - (v: Vec2) -> Vec2 { Vec2(-v.x, -v.y) }
    public static func += (a: inout Vec2, b: Vec2) { a = a + b }
    public static func -= (a: inout Vec2, b: Vec2) { a = a - b }
    public static func *= (a: inout Vec2, s: Double) { a = a * s }

    public var lengthSquared: Double { x * x + y * y }
    public var length: Double { (x * x + y * y).squareRoot() }

    /// Zero-length vectors normalize to zero rather than NaN — every caller
    /// here would otherwise need the same guard.
    public var normalized: Vec2 {
        let len = length
        return len > 1e-9 ? Vec2(x / len, y / len) : .zero
    }

    /// Screen-space angle in radians, with +y pointing down.
    public var angle: Double { atan2(y, x) }

    public func dot(_ other: Vec2) -> Double { x * other.x + y * other.y }
    public func cross(_ other: Vec2) -> Double { x * other.y - y * other.x }
    public func distance(to other: Vec2) -> Double { (self - other).length }
    public func distanceSquared(to other: Vec2) -> Double { (self - other).lengthSquared }

    public func rotated(by radians: Double) -> Vec2 {
        let c = cos(radians), s = sin(radians)
        return Vec2(x * c - y * s, x * s + y * c)
    }

    public var perpendicular: Vec2 { Vec2(-y, x) }

    public func clampedLength(_ maxLength: Double) -> Vec2 {
        let len = length
        return len > maxLength && len > 1e-9 ? self * (maxLength / len) : self
    }

    public static func angle(_ radians: Double) -> Vec2 {
        Vec2(cos(radians), sin(radians))
    }

    public static func lerp(_ a: Vec2, _ b: Vec2, _ t: Double) -> Vec2 {
        Vec2(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
    }

    /// Frame-rate independent exponential smoothing. `rate` is roughly
    /// "fraction closed per second", so the same call behaves identically at
    /// 60 and 144 Hz.
    public static func damp(_ a: Vec2, _ b: Vec2, rate: Double, dt: Double) -> Vec2 {
        lerp(a, b, 1 - exp(-rate * dt))
    }

    /// Eight-way snap, used for picking a walk animation from a velocity.
    public var cardinal: Cardinal {
        if abs(x) > abs(y) {
            return x > 0 ? .east : .west
        }
        return y > 0 ? .south : .north
    }
}

public enum Cardinal: Int, Sendable, CaseIterable {
    case north, east, south, west

    public var vector: Vec2 {
        switch self {
        case .north: return Vec2(0, -1)
        case .east: return Vec2(1, 0)
        case .south: return Vec2(0, 1)
        case .west: return Vec2(-1, 0)
        }
    }

    public var opposite: Cardinal {
        switch self {
        case .north: return .south
        case .east: return .west
        case .south: return .north
        case .west: return .east
        }
    }
}

public extension Double {
    /// Shortest signed difference between two angles, in -pi...pi.
    func angleDelta(to target: Double) -> Double {
        var d = (target - self).truncatingRemainder(dividingBy: 2 * .pi)
        if d > .pi { d -= 2 * .pi }
        if d < -.pi { d += 2 * .pi }
        return d
    }

    func rotatedToward(_ target: Double, maxStep: Double) -> Double {
        let delta = angleDelta(to: target)
        if abs(delta) <= maxStep { return target }
        return self + (delta > 0 ? maxStep : -maxStep)
    }

    func clamped(_ lo: Double, _ hi: Double) -> Double { min(max(self, lo), hi) }

    func lerped(to other: Double, _ t: Double) -> Double { self + (other - self) * t }
}

public extension Int {
    func clamped(_ lo: Int, _ hi: Int) -> Int { Swift.min(Swift.max(self, lo), hi) }
}
