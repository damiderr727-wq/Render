import Foundation

/// Axis-aligned rectangle in world units.
public struct Rect: Equatable, Sendable {
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

    public init(center: Vec2, size: Vec2) {
        self.init(x: center.x - size.x / 2, y: center.y - size.y / 2,
                  width: size.x, height: size.y)
    }

    public var minX: Double { x }
    public var minY: Double { y }
    public var maxX: Double { x + width }
    public var maxY: Double { y + height }
    public var center: Vec2 { Vec2(x + width / 2, y + height / 2) }
    public var size: Vec2 { Vec2(width, height) }

    public func contains(_ point: Vec2) -> Bool {
        point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY
    }

    public func intersects(_ other: Rect) -> Bool {
        minX < other.maxX && maxX > other.minX &&
        minY < other.maxY && maxY > other.minY
    }

    public func inset(by amount: Double) -> Rect {
        Rect(x: x + amount, y: y + amount,
             width: max(0, width - amount * 2), height: max(0, height - amount * 2))
    }

    public func expanded(by amount: Double) -> Rect { inset(by: -amount) }

    public func clamp(_ point: Vec2) -> Vec2 {
        Vec2(point.x.clamped(minX, maxX), point.y.clamped(minY, maxY))
    }

    /// Nearest point on the rectangle's surface or interior.
    public func closestPoint(to point: Vec2) -> Vec2 { clamp(point) }

    public func overlaps(circleAt center: Vec2, radius: Double) -> Bool {
        closestPoint(to: center).distanceSquared(to: center) <= radius * radius
    }
}

public enum Collision {
    /// Resolves a circle against a rectangle, returning the smallest push-out
    /// that separates them. Zero when they are not overlapping.
    ///
    /// Chosen over a proper swept test because the game's actors move at most
    /// a few pixels per frame and never tunnel; a push-out is cheaper, and it
    /// behaves better when an actor is spawned inside geometry.
    public static func resolve(circle center: Vec2, radius: Double,
                               rect: Rect) -> Vec2 {
        let closest = rect.closestPoint(to: center)
        let delta = center - closest
        let distSq = delta.lengthSquared

        if distSq > radius * radius { return .zero }

        if distSq > 1e-12 {
            let dist = distSq.squareRoot()
            return delta * ((radius - dist) / dist)
        }

        // Centre is inside the rect: push out along the shallowest axis.
        let toLeft = center.x - rect.minX
        let toRight = rect.maxX - center.x
        let toTop = center.y - rect.minY
        let toBottom = rect.maxY - center.y
        let minPen = min(min(toLeft, toRight), min(toTop, toBottom))
        if minPen == toLeft { return Vec2(-(toLeft + radius), 0) }
        if minPen == toRight { return Vec2(toRight + radius, 0) }
        if minPen == toTop { return Vec2(0, -(toTop + radius)) }
        return Vec2(0, toBottom + radius)
    }

    public static func circlesOverlap(_ a: Vec2, _ ar: Double,
                                      _ b: Vec2, _ br: Double) -> Bool {
        let r = ar + br
        return a.distanceSquared(to: b) <= r * r
    }

    /// Ray/AABB slab test. Returns the entry distance along `direction`,
    /// or nil when the ray misses.
    public static func rayHits(origin: Vec2, direction: Vec2, rect: Rect,
                               maxDistance: Double) -> Double? {
        var tMin = 0.0
        var tMax = maxDistance

        for axis in 0..<2 {
            let o = axis == 0 ? origin.x : origin.y
            let d = axis == 0 ? direction.x : direction.y
            let lo = axis == 0 ? rect.minX : rect.minY
            let hi = axis == 0 ? rect.maxX : rect.maxY

            if abs(d) < 1e-9 {
                if o < lo || o > hi { return nil }
                continue
            }
            var t1 = (lo - o) / d
            var t2 = (hi - o) / d
            if t1 > t2 { swap(&t1, &t2) }
            tMin = max(tMin, t1)
            tMax = min(tMax, t2)
            if tMin > tMax { return nil }
        }
        return tMin
    }
}

/// Easing curves. Used for camera moves, UI transitions and boss telegraphs,
/// where a linear ramp always reads as cheap.
public enum Ease {
    public static func outCubic(_ t: Double) -> Double {
        let p = 1 - t.clamped(0, 1)
        return 1 - p * p * p
    }

    public static func inCubic(_ t: Double) -> Double {
        let p = t.clamped(0, 1)
        return p * p * p
    }

    public static func inOutQuad(_ t: Double) -> Double {
        let p = t.clamped(0, 1)
        return p < 0.5 ? 2 * p * p : 1 - pow(-2 * p + 2, 2) / 2
    }

    public static func outBack(_ t: Double) -> Double {
        let c1 = 1.70158, c3 = c1 + 1
        let p = t.clamped(0, 1) - 1
        return 1 + c3 * p * p * p + c1 * p * p
    }

    public static func outElastic(_ t: Double) -> Double {
        let p = t.clamped(0, 1)
        if p == 0 || p == 1 { return p }
        let c4 = (2 * Double.pi) / 3
        return pow(2, -10 * p) * sin((p * 10 - 0.75) * c4) + 1
    }

    /// 1 at t=0, decaying to 0 at t=1 with a few oscillations. Screen shake
    /// and hit wobble both ride this.
    public static func decayingWave(_ t: Double, cycles: Double = 3) -> Double {
        let p = t.clamped(0, 1)
        return (1 - p) * cos(p * cycles * 2 * .pi)
    }
}
