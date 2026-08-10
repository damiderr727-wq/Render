import Foundation

/// Die Bewohner der verstimmten Welt. Keiner von ihnen ist boese - sie sind
/// nur seit langem falsch gestimmt.
public enum EnemyKind: String, Sendable, CaseIterable {
    /// Taumelnder Falter aus verklungenen Toenen.
    case klangmotte
    /// Schwerer Waechter, der Klang schluckt.
    case stilleschreiter
    /// Festgewachsen; spuckt schiefe Toene.
    case dissonanzknospe
    /// Springender Kristallsplitter, prallt von allem ab.
    case echoscherbe

    public var maxHealth: Int {
        switch self {
        case .klangmotte: return 3
        case .stilleschreiter: return 8
        case .dissonanzknospe: return 4
        case .echoscherbe: return 4
        }
    }

    public var contactDamage: Int { 1 }

    public var size: (width: Double, height: Double) {
        switch self {
        case .klangmotte: return (12, 10)
        case .stilleschreiter: return (18, 18)
        case .dissonanzknospe: return (12, 16)
        case .echoscherbe: return (11, 11)
        }
    }

    /// Faellt die Kreatur, oder schwebt sie?
    public var isAirborne: Bool {
        self == .klangmotte || self == .echoscherbe
    }

    /// Bleibt sie stehen, wo sie steht?
    public var isRooted: Bool {
        self == .dissonanzknospe
    }

    public var resonanceReward: Double {
        switch self {
        case .stilleschreiter: return 16
        default: return Tuning.resonancePerKill
        }
    }
}

public final class Enemy {
    public let id: Int
    public let kind: EnemyKind
    public var position: Vec2
    public var velocity: Vec2 = .zero
    public var health: Int
    public var facing: Double = -1
    public private(set) var alive = true

    /// Kurzes Aufblitzen nach einem Treffer.
    public private(set) var hitFlash: Double = 0
    /// Wie lange die Kreatur noch benommen ist.
    private var stagger: Double = 0
    private var attackTimer: Double = 0
    private var stateTime: Double = 0
    private var aggro = false

    private let home: Vec2
    private let patrolRange: Double
    private var rng: Rng

    public init(id: Int, kind: EnemyKind, position: Vec2, patrolTiles: Double?) {
        self.id = id
        self.kind = kind
        self.position = position
        self.home = position
        self.patrolRange = (patrolTiles ?? 4) * tileSize
        self.health = kind.maxHealth
        self.rng = Rng(seed: UInt64(id &* 2654435761 &+ 12345))
        self.attackTimer = 0.6 + Double(id % 5) * 0.25
    }

    public var rect: Rect {
        let s = kind.size
        return Rect(footAt: position, width: s.width, height: s.height)
    }

    public var center: Vec2 {
        rect.center
    }

    // MARK: - Verhalten

    public func update(dt: Double, room: Room, player: Player, events: inout [GameEvent],
                       spawnProjectile: (Projectile) -> Void) {
        guard alive else { return }
        stateTime += dt
        hitFlash = max(0, hitFlash - dt)
        stagger = max(0, stagger - dt)
        attackTimer -= dt

        let toPlayer = player.chest - center
        let distance = toPlayer.length
        if distance < 190 { aggro = true }
        if distance > 340 { aggro = false }

        if stagger <= 0 {
            switch kind {
            case .klangmotte: updateMoth(dt: dt, toPlayer: toPlayer, distance: distance)
            case .stilleschreiter: updateWalker(dt: dt, room: room, toPlayer: toPlayer, distance: distance)
            case .dissonanzknospe:
                updateBud(dt: dt, toPlayer: toPlayer, distance: distance, spawnProjectile: spawnProjectile)
            case .echoscherbe: updateShard(dt: dt)
            }
        } else {
            velocity.x = approach(velocity.x, 0, 600 * dt)
        }

        applyPhysics(dt: dt, room: room)
    }

    private func updateMoth(dt: Double, toPlayer: Vec2, distance: Double) {
        // Taumelt auf einer Sinuslinie und driftet dabei zum Spieler.
        let drift = Vec2(sin(stateTime * 1.7), cos(stateTime * 2.3)) * 34
        let pull = aggro && distance > 1 ? toPlayer.normalized * 52 : .zero
        let homePull = (home - position) * (aggro ? 0.1 : 0.7)
        let target = drift + pull + homePull
        velocity.x = damp(velocity.x, target.x, rate: 0.06, dt: dt)
        velocity.y = damp(velocity.y, target.y, rate: 0.06, dt: dt)
        if abs(velocity.x) > 4 { facing = sign(velocity.x) }
    }

    private func updateWalker(dt: Double, room: Room, toPlayer: Vec2, distance: Double) {
        let chargeRange = 130.0
        let speed: Double = aggro && distance < chargeRange ? 105 : 42
        if aggro && distance < chargeRange {
            facing = sign(toPlayer.x) == 0 ? facing : sign(toPlayer.x)
        } else {
            // Patrouille um den Ausgangspunkt.
            if position.x > home.x + patrolRange { facing = -1 }
            if position.x < home.x - patrolRange { facing = 1 }
        }

        // Nicht ins Leere laufen: Boden vor den Fuessen pruefen.
        let ahead = Vec2(position.x + facing * (kind.size.width / 2 + 4), position.y + 4)
        let wallProbe = rect.offset(by: Vec2(facing * 3, 0))
        if !room.tile(at: ahead).isStandable || room.overlapsSolid(wallProbe) {
            facing = -facing
        }
        velocity.x = approach(velocity.x, facing * speed, 700 * dt)
    }

    private func updateBud(dt: Double, toPlayer: Vec2, distance: Double,
                           spawnProjectile: (Projectile) -> Void) {
        velocity.x = 0
        facing = sign(toPlayer.x) == 0 ? facing : sign(toPlayer.x)
        guard aggro, distance < 260, attackTimer <= 0 else { return }
        attackTimer = 1.9 + rng.range(0, 0.7)
        // Drei schiefe Toene faecherfoermig.
        let base = atan2(toPlayer.y, toPlayer.x)
        for offset in [-0.24, 0.0, 0.24] {
            let angle = base + offset
            spawnProjectile(.dissonantNote(origin: center,
                                           direction: Vec2(cos(angle), sin(angle))))
        }
    }

    private func updateShard(dt: Double) {
        // Prallt frei umher; die Kollision dreht die Richtung.
        if velocity.lengthSquared < 100 {
            let angle = rng.range(0, .pi * 2)
            velocity = Vec2(cos(angle), sin(angle)) * 120
        }
        let speed = velocity.length
        velocity = velocity.normalized * approach(speed, 132, 90 * dt)
        facing = sign(velocity.x) == 0 ? facing : sign(velocity.x)
    }

    // MARK: - Physik

    private func applyPhysics(dt: Double, room: Room) {
        guard !kind.isRooted else { return }

        if !kind.isAirborne {
            velocity.y = min(velocity.y + Tuning.gravity * dt, Tuning.maxFallSpeed)
        }

        // X
        let stepX = velocity.x * dt
        let probeX = rect.offset(by: Vec2(stepX, 0))
        if room.overlapsSolid(probeX) {
            if kind == .echoscherbe {
                velocity.x = -velocity.x
                facing = sign(velocity.x)
            } else {
                velocity.x = 0
                facing = -facing
            }
        } else {
            position.x += stepX
        }

        // Y
        let stepY = velocity.y * dt
        let probeY = rect.offset(by: Vec2(0, stepY))
        let collides = stepY > 0
            ? room.overlapsGround(probeY, previousBottom: rect.maxY)
            : room.overlapsSolid(probeY)
        if collides {
            if kind == .echoscherbe {
                velocity.y = -velocity.y
            } else {
                velocity.y = 0
            }
        } else {
            position.y += stepY
        }

        position.x = clamp(position.x, 8, room.bounds.maxX - 8)
        position.y = clamp(position.y, 8, room.bounds.maxY - 4)
    }

    // MARK: - Schaden

    /// Meldet, ob die Kreatur daran gestorben ist.
    @discardableResult
    public func takeDamage(_ amount: Int, knockback: Vec2, events: inout [GameEvent]) -> Bool {
        guard alive else { return false }
        health -= amount
        hitFlash = 0.12
        stagger = kind == .stilleschreiter ? 0.14 : 0.22
        aggro = true
        if !kind.isRooted {
            velocity += knockback * (kind == .stilleschreiter ? 0.45 : 1.0)
        }
        events.append(.sound(.hit(strong: amount >= 3)))
        events.append(.effect(.burstGlow, center, .zero))

        if health <= 0 {
            alive = false
            events.append(.sound(.enemyDeath))
            events.append(.effect(.burstRot, center, .zero))
            events.append(.enemyKilled(kind: kind.rawValue, position: center))
            return true
        }
        return false
    }
}
