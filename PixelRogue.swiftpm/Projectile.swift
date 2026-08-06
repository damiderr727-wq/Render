import Foundation

/// A bullet in flight.
///
/// Everything a bullet can do lives in this one struct rather than in
/// subclasses: a bullet hell spawns hundreds per second, and branchy value
/// types stay in contiguous memory where a class hierarchy would not.
public struct Projectile: Sendable {
    public var id: Int
    public var position: Vec2
    public var velocity: Vec2
    public var radius: Double
    public var damage: Double
    public var faction: Faction
    public var owner: ActorID

    public var age: Double = 0
    public var lifetime: Double = 1.5
    public var sprite: String
    public var spriteFrames: Int = 1
    public var scale: Double = 1
    public var spin: Double = 0
    public var rotation: Double = 0

    public var pierce: Int = 0
    public var bounces: Int = 0
    public var homing: Double = 0
    public var homingTarget: ActorID = .none
    public var chain: Int = 0
    public var explodeRadius: Double = 0
    public var status: StatusKind?
    public var statusChance: Double = 0
    public var knockback: Double = 0
    public var impactFX: String = "fx/impact_spark"

    /// Lobbed shots: `height` rises then falls, and the bullet only resolves
    /// when it lands. Nothing else in the game uses a z axis.
    public var arcGravity: Double = 0
    public var height: Double = 0
    public var verticalSpeed: Double = 0

    /// Sine weave perpendicular to travel, in world units of amplitude.
    public var curve: Double = 0
    public var curvePhase: Double = 0

    /// Boomerangs decelerate, stop, and come home.
    public var returnsTo: ActorID = .none
    public var returning: Bool = false

    /// Orbit motes circle the owner before launching at a target.
    public var orbitOwner: ActorID = .none
    public var orbitRadius: Double = 0
    public var orbitAngle: Double = 0
    public var orbitDelay: Double = 0

    public var hitActors: Set<Int> = []
    public var alive: Bool = true

    public init(id: Int, position: Vec2, velocity: Vec2, radius: Double,
                damage: Double, faction: Faction, owner: ActorID,
                sprite: String) {
        self.id = id
        self.position = position
        self.velocity = velocity
        self.radius = radius
        self.damage = damage
        self.faction = faction
        self.owner = owner
        self.sprite = sprite
    }

    public var isAirborne: Bool { arcGravity > 0 && height > 0.5 }
    public var angle: Double { velocity.angle }
}

/// A short-lived, non-damaging visual the sim asks the renderer to play.
public struct EffectRequest: Sendable {
    public var name: String
    public var position: Vec2
    public var angle: Double
    public var scale: Double
    public var lifetime: Double

    public init(name: String, position: Vec2, angle: Double = 0,
                scale: Double = 1, lifetime: Double = 0.3) {
        self.name = name
        self.position = position
        self.angle = angle
        self.scale = scale
        self.lifetime = lifetime
    }
}

/// Damage-over-time areas: poison clouds, fire pools.
public struct HazardZone: Sendable {
    public var id: Int
    public var position: Vec2
    public var radius: Double
    public var damagePerSecond: Double
    public var remaining: Double
    public var faction: Faction
    public var status: StatusKind?
    public var sprite: String
    public var tickTimer: Double = 0
}
