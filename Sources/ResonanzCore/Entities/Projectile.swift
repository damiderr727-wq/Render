import Foundation

/// Ein hoerbar gewordener Ton. Geschosse sind die Fernkampfform des Schalls.
public struct Projectile: Sendable {
    public enum Owner: Sendable { case player, enemy }

    public var position: Vec2
    public var velocity: Vec2
    public var radius: Double
    public var damage: Int
    public var piercesLeft: Int
    public var lifetime: Double
    public var gravity: Double
    public let owner: Owner
    /// Bestimmt Sprite und Farbe in der Darstellung.
    public let kind: String
    public var age: Double = 0
    public var alive = true
    /// Bereits getroffene Gegner, damit ein Durchschlag nicht mehrfach zaehlt.
    public var hitIDs: Set<Int> = []

    public init(position: Vec2, velocity: Vec2, radius: Double, damage: Int,
                piercesLeft: Int, lifetime: Double, gravity: Double,
                owner: Owner, kind: String) {
        self.position = position
        self.velocity = velocity
        self.radius = radius
        self.damage = damage
        self.piercesLeft = piercesLeft
        self.lifetime = lifetime
        self.gravity = gravity
        self.owner = owner
        self.kind = kind
    }

    public var rect: Rect {
        Rect(center: position, radius: radius)
    }

    /// Bewegt das Geschoss und meldet, ob es auf Fels getroffen ist.
    public mutating func update(dt: Double, room: Room) -> Bool {
        age += dt
        lifetime -= dt
        if lifetime <= 0 {
            alive = false
            return false
        }
        velocity.y += gravity * dt

        // In kleinen Schritten, damit nichts durch duenne Waende schluepft.
        let distance = velocity.length * dt
        let steps = max(1, Int(ceil(distance / 5)))
        let step = dt / Double(steps)
        for _ in 0..<steps {
            position += velocity * step
            if room.overlapsSolid(rect) {
                alive = false
                return true
            }
            if !room.bounds.inset(by: -8).contains(position) {
                alive = false
                return false
            }
        }
        return false
    }

    /// Trifft einen Gegner und meldet, ob das Geschoss danach vergeht.
    public mutating func consumeHit(entityID: Int) -> Bool {
        hitIDs.insert(entityID)
        if piercesLeft > 0 {
            piercesLeft -= 1
            return false
        }
        alive = false
        return true
    }

    // MARK: - Erzeugung

    /// Baut die Geschosse eines Fernkampfangriffs.
    public static func volley(instrument: Instrument, origin: Vec2, direction: Vec2) -> [Projectile] {
        let profile = Tuning.ranged(instrument)
        let base = direction.normalized
        let baseAngle = atan2(base.y, base.x)
        var result: [Projectile] = []
        for i in 0..<profile.count {
            let offset = profile.count == 1
                ? 0
                : (Double(i) - Double(profile.count - 1) / 2) * profile.spread
            let angle = baseAngle + offset
            let velocity = Vec2(cos(angle), sin(angle)) * profile.speed
            result.append(Projectile(position: origin,
                                     velocity: velocity,
                                     radius: profile.radius,
                                     damage: profile.damage,
                                     piercesLeft: profile.pierces,
                                     lifetime: profile.lifetime,
                                     gravity: profile.gravity,
                                     owner: .player,
                                     kind: "note_\(instrument.rawValue)"))
        }
        return result
    }

    /// Der schiefe Ton, den die Dissonanz zurueckwirft.
    public static func dissonantNote(origin: Vec2, direction: Vec2,
                                     speed: Double = 135, damage: Int = 1) -> Projectile {
        Projectile(position: origin,
                   velocity: direction.normalized * speed,
                   radius: 5,
                   damage: damage,
                   piercesLeft: 0,
                   lifetime: 4.0,
                   gravity: 0,
                   owner: .enemy,
                   kind: "note_dissonanz")
    }
}
