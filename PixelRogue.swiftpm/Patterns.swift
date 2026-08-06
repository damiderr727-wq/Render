import Foundation

/// One bullet an attack wants to create.
public struct BulletSpec: Sendable {
    public var direction: Vec2
    public var speed: Double
    public var damage: Double
    public var radius: Double = 4
    public var sprite: String = "proj/bolt_enemy"
    public var lifetime: Double = 4.0
    public var curve: Double = 0
    public var homing: Double = 0
    public var status: StatusKind?
    public var scale: Double = 1
    public var spin: Double = 0
    public var offset: Vec2 = .zero
}

/// The bullet-hell vocabulary.
///
/// Each case is a *shape*, not a script: the emitter is a pure function of
/// (pattern, origin, aim, phase), so a boss can advance `phase` a little each
/// volley and get a rotating flower for free. That is what turns a handful of
/// cases into hundreds of distinguishable attacks.
public enum AttackPattern: Sendable {
    /// Straight at the target, optionally as a fan.
    case aimed(count: Int, spread: Double, speed: Double, damage: Double,
               sprite: String)
    /// Evenly spaced full circle. `offsetByPhase` rotates it per volley.
    case radial(count: Int, speed: Double, damage: Double, sprite: String,
                offsetByPhase: Bool)
    /// A circle with a hole in it — the classic "find the gap" attack.
    case ringGap(count: Int, gapWidth: Double, speed: Double, damage: Double,
                 sprite: String)
    /// Arms of a rotating spiral.
    case spiral(arms: Int, speed: Double, damage: Double, sprite: String,
                turnPerVolley: Double)
    /// An arc centred on the aim direction, bullets at staggered speeds so
    /// the wall of bullets arrives slanted.
    case wave(count: Int, arc: Double, speed: Double, speedStep: Double,
              damage: Double, sprite: String)
    /// Petals: several tight clusters spaced around a circle.
    case flower(petals: Int, perPetal: Int, petalSpread: Double, speed: Double,
                damage: Double, sprite: String)
    /// Bullets that weave as they travel.
    case serpent(count: Int, spread: Double, speed: Double, curve: Double,
                 damage: Double, sprite: String)
    /// Slow homing orbs — pressure rather than damage.
    case seekers(count: Int, speed: Double, homing: Double, damage: Double,
                 sprite: String)
    /// A cross of four lines, rotated by phase.
    case cross(perArm: Int, spacing: Double, speed: Double, damage: Double,
               sprite: String)
    /// Non-projectile behaviours the AI resolves itself.
    case dash(speed: Double, duration: Double)
    case detonate(radius: Double, damage: Double)
    case summon(kind: String, count: Int)
    case beamSweep(damage: Double, arc: Double, duration: Double)

    public var isProjectilePattern: Bool {
        switch self {
        case .dash, .detonate, .summon, .beamSweep: return false
        default: return true
        }
    }
}

public enum BulletPatterns {
    /// Expands a pattern into concrete bullets.
    ///
    /// `phase` is the emitter's running counter — bosses increment it every
    /// volley, which is what makes spirals turn and rings drift.
    public static func emit(_ pattern: AttackPattern, origin: Vec2,
                            toward target: Vec2, phase: Double,
                            rng: inout RNG) -> [BulletSpec] {
        let aim = (target - origin).normalized
        let aimAngle = aim == .zero ? 0 : aim.angle

        switch pattern {
        case let .aimed(count, spread, speed, damage, sprite):
            guard count > 0 else { return [] }
            var out: [BulletSpec] = []
            let step = count > 1 ? spread / Double(count - 1) : 0
            for i in 0..<count {
                let angle = aimAngle - spread / 2 + step * Double(i)
                out.append(BulletSpec(direction: .angle(angle), speed: speed,
                                      damage: damage, sprite: sprite))
            }
            return out

        case let .radial(count, speed, damage, sprite, offsetByPhase):
            guard count > 0 else { return [] }
            let base = offsetByPhase ? phase * 0.35 : 0
            return (0..<count).map { i in
                let angle = base + Double(i) * 2 * .pi / Double(count)
                return BulletSpec(direction: .angle(angle), speed: speed,
                                  damage: damage, sprite: sprite)
            }

        case let .ringGap(count, gapWidth, speed, damage, sprite):
            guard count > 0 else { return [] }
            // The gap tracks the player, so standing still is never safe but
            // moving into the gap always is.
            let gapCenter = aimAngle + .pi
            var out: [BulletSpec] = []
            for i in 0..<count {
                let angle = Double(i) * 2 * .pi / Double(count) + phase * 0.15
                if abs(angle.angleDelta(to: gapCenter)) < gapWidth / 2 { continue }
                out.append(BulletSpec(direction: .angle(angle), speed: speed,
                                      damage: damage, sprite: sprite))
            }
            return out

        case let .spiral(arms, speed, damage, sprite, turnPerVolley):
            guard arms > 0 else { return [] }
            let base = phase * turnPerVolley
            return (0..<arms).map { i in
                let angle = base + Double(i) * 2 * .pi / Double(arms)
                return BulletSpec(direction: .angle(angle), speed: speed,
                                  damage: damage, sprite: sprite)
            }

        case let .wave(count, arc, speed, speedStep, damage, sprite):
            guard count > 0 else { return [] }
            var out: [BulletSpec] = []
            let step = count > 1 ? arc / Double(count - 1) : 0
            for i in 0..<count {
                let angle = aimAngle - arc / 2 + step * Double(i)
                // Speed ramps across the fan so the wall arrives at a slant.
                let offset = Double(i) - Double(count - 1) / 2
                out.append(BulletSpec(direction: .angle(angle),
                                      speed: speed + abs(offset) * speedStep,
                                      damage: damage, sprite: sprite))
            }
            return out

        case let .flower(petals, perPetal, petalSpread, speed, damage, sprite):
            guard petals > 0, perPetal > 0 else { return [] }
            var out: [BulletSpec] = []
            for p in 0..<petals {
                let center = phase * 0.22 + Double(p) * 2 * .pi / Double(petals)
                let step = perPetal > 1 ? petalSpread / Double(perPetal - 1) : 0
                for j in 0..<perPetal {
                    let angle = center - petalSpread / 2 + step * Double(j)
                    out.append(BulletSpec(direction: .angle(angle), speed: speed,
                                          damage: damage, sprite: sprite))
                }
            }
            return out

        case let .serpent(count, spread, speed, curve, damage, sprite):
            guard count > 0 else { return [] }
            var out: [BulletSpec] = []
            let step = count > 1 ? spread / Double(count - 1) : 0
            for i in 0..<count {
                let angle = aimAngle - spread / 2 + step * Double(i)
                var spec = BulletSpec(direction: .angle(angle), speed: speed,
                                      damage: damage, sprite: sprite)
                // Alternating weave direction reads as a braid.
                spec.curve = i % 2 == 0 ? curve : -curve
                out.append(spec)
            }
            return out

        case let .seekers(count, speed, homing, damage, sprite):
            guard count > 0 else { return [] }
            return (0..<count).map { i in
                let spin = Double(i) * 2 * .pi / Double(count) + rng.double(-0.2, 0.2)
                var spec = BulletSpec(direction: .angle(spin), speed: speed,
                                      damage: damage, sprite: sprite)
                spec.homing = homing
                spec.radius = 5
                spec.lifetime = 6
                return spec
            }

        case let .cross(perArm, spacing, speed, damage, sprite):
            var out: [BulletSpec] = []
            for arm in 0..<4 {
                let angle = phase * 0.25 + Double(arm) * .pi / 2
                let dir = Vec2.angle(angle)
                for i in 0..<max(1, perArm) {
                    var spec = BulletSpec(direction: dir, speed: speed,
                                          damage: damage, sprite: sprite)
                    spec.offset = dir * (spacing * Double(i))
                    out.append(spec)
                }
            }
            return out

        case .dash, .detonate, .summon, .beamSweep:
            return []
        }
    }
}
