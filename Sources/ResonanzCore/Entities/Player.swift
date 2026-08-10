import Foundation

/// Zustaende, die die Darstellung unterscheiden muss.
public enum PlayerState: String, Sendable {
    case idle, run, jump, fall, wallSlide, dash, melee, cast, hurt, slam, rest, dead
}

/// Cadence. Ihre Waffe ist der Schall; das Instrument gibt ihm nur die Form.
public final class Player {
    // MARK: Lage
    public var position: Vec2
    public var velocity: Vec2 = .zero
    public var facing: Double = 1

    // MARK: Bodenkontakt
    public private(set) var onGround = false
    public private(set) var onCeiling = false
    /// -1 Wand links, +1 Wand rechts, 0 keine.
    public private(set) var wallSide: Double = 0
    public private(set) var isWallSliding = false

    private var coyoteTimer: Double = 0
    private var jumpBufferTimer: Double = 0
    private var wallCoyoteTimer: Double = 0
    private var wallJumpLock: Double = 0
    private var airJumpsLeft: Int = 0
    private var jumpHeldLast = false

    // MARK: Herzschlag
    public private(set) var isDashing = false
    private var dashTimer: Double = 0
    private var dashCooldown: Double = 0
    private var dashAvailable = true
    private var dashDirection: Vec2 = Vec2(1, 0)

    // MARK: Basston
    public private(set) var isSlamming = false
    private var slamRecovery: Double = 0

    // MARK: Kampf
    public private(set) var instrument: Instrument = .leier
    public private(set) var attackTimer: Double = 0
    public private(set) var attackIsMelee = false
    private var attackCooldown: Double = 0
    private var attackHasHit = false
    public private(set) var aimY: Double = 0

    // MARK: Zustand
    public var health: Int
    public var resonance: Double
    public private(set) var invulnerable: Double = 0
    public private(set) var controlLock: Double = 0
    public private(set) var isResting = false
    public private(set) var isDead = false

    public private(set) var state: PlayerState = .idle
    /// Laeuft mit, damit die Darstellung Animationsphasen ableiten kann.
    public private(set) var stateTime: Double = 0

    private var progression: Progression

    public init(position: Vec2, progression: Progression, instrument: Instrument) {
        self.position = position
        self.progression = progression
        self.instrument = instrument
        self.health = progression.maxHealth
        self.resonance = progression.maxResonance
    }

    public var rect: Rect {
        Rect(footAt: position, width: Tuning.playerWidth, height: Tuning.playerHeight)
    }

    public var chest: Vec2 {
        Vec2(position.x, position.y - Tuning.playerHeight * 0.55)
    }

    public func sync(progression: Progression) {
        self.progression = progression
        if health > progression.maxHealth { health = progression.maxHealth }
    }

    public func equip(_ instrument: Instrument) {
        guard progression.has(instrument) else { return }
        self.instrument = instrument
    }

    /// Volle Kraft - nach dem Ausruhen an der Stimmgabel.
    public func restore() {
        health = progression.maxHealth
        resonance = progression.maxResonance
        isDead = false
        invulnerable = 0
        velocity = .zero
    }

    public func placeAt(_ point: Vec2, facing: Double) {
        position = point
        self.facing = facing
        velocity = .zero
        isDashing = false
        isSlamming = false
        dashTimer = 0
        attackTimer = 0
        controlLock = 0
    }

    // MARK: - Bild pro Bild

    public func update(dt: Double, input: PlayerInput, room: Room, events: inout [GameEvent]) {
        stateTime += dt
        tickTimers(dt: dt)

        if isDead {
            applyGravity(dt: dt)
            _ = moveY(velocity.y * dt, room: room)
            setState(.dead)
            return
        }

        if isResting {
            velocity = .zero
            setState(.rest)
            return
        }

        aimY = input.aimY

        handleAttacks(input: input, events: &events)
        handleDash(dt: dt, input: input, room: room, events: &events)
        handleSlam(input: input, events: &events)

        if !isDashing {
            applyHorizontalControl(dt: dt, input: input)
            applyGravity(dt: dt)
            handleJump(input: input, room: room, events: &events)
        }

        moveAndCollide(dt: dt, room: room, events: &events)
        updateWallState(room: room, input: input, dt: dt)
        regenerateResonance(dt: dt)
        updateState()
    }

    private func tickTimers(dt: Double) {
        coyoteTimer = max(0, coyoteTimer - dt)
        wallCoyoteTimer = max(0, wallCoyoteTimer - dt)
        jumpBufferTimer = max(0, jumpBufferTimer - dt)
        wallJumpLock = max(0, wallJumpLock - dt)
        dashCooldown = max(0, dashCooldown - dt)
        attackCooldown = max(0, attackCooldown - dt)
        attackTimer = max(0, attackTimer - dt)
        invulnerable = max(0, invulnerable - dt)
        controlLock = max(0, controlLock - dt)
        slamRecovery = max(0, slamRecovery - dt)
    }

    // MARK: - Laufen

    private func applyHorizontalControl(dt: Double, input: PlayerInput) {
        guard controlLock <= 0, slamRecovery <= 0 else { return }
        let wanted = wallJumpLock > 0 ? 0 : input.moveX
        if abs(wanted) > 0.01 {
            let accel = onGround ? Tuning.groundAccel : Tuning.airAccel
            velocity.x = approach(velocity.x, wanted * Tuning.runSpeed, accel * dt)
            if wallJumpLock <= 0 { facing = sign(wanted) }
        } else {
            let friction = onGround ? Tuning.groundFriction : Tuning.airFriction
            velocity.x = approach(velocity.x, 0, friction * dt)
        }
    }

    private func applyGravity(dt: Double) {
        guard !isSlamming else {
            velocity.y = Tuning.slamSpeed
            return
        }
        let scale = velocity.y < 0 ? Tuning.riseGravityScale : 1.0
        velocity.y = min(velocity.y + Tuning.gravity * scale * dt, Tuning.maxFallSpeed)
        if isWallSliding && velocity.y > Tuning.wallSlideSpeed {
            velocity.y = Tuning.wallSlideSpeed
        }
    }

    // MARK: - Springen

    private func handleJump(input: PlayerInput, room: Room, events: inout [GameEvent]) {
        if input.jumpPressed { jumpBufferTimer = Tuning.jumpBuffer }

        // Sprunghoehe kappen, sobald die Taste losgelassen wird.
        if jumpHeldLast && !input.jumpHeld && velocity.y < 0 {
            velocity.y *= Tuning.jumpCutFactor
        }
        jumpHeldLast = input.jumpHeld

        guard jumpBufferTimer > 0, controlLock <= 0 else { return }

        if coyoteTimer > 0 {
            velocity.y = Tuning.jumpVelocity
            coyoteTimer = 0
            jumpBufferTimer = 0
            events.append(.sound(.jump))
            events.append(.effect(.dust, position, .zero))
            return
        }

        if progression.has(.klangschritt), wallCoyoteTimer > 0, wallSide != 0 {
            velocity.y = Tuning.wallJumpVelocityY
            velocity.x = -wallSide * Tuning.wallJumpVelocityX
            facing = -wallSide
            wallJumpLock = Tuning.wallJumpLockTime
            wallCoyoteTimer = 0
            jumpBufferTimer = 0
            isWallSliding = false
            airJumpsLeft = progression.has(.fluegelschlag) ? 1 : 0
            events.append(.sound(.wallJump))
            events.append(.effect(.dust, Vec2(position.x + wallSide * 6, position.y - 10), .zero))
            return
        }

        if airJumpsLeft > 0 {
            airJumpsLeft -= 1
            velocity.y = Tuning.doubleJumpVelocity
            jumpBufferTimer = 0
            events.append(.sound(.doubleJump))
            events.append(.effect(.feather, Vec2(position.x, position.y - 8), .zero))
        }
    }

    // MARK: - Herzschlag

    private func handleDash(dt: Double, input: PlayerInput, room: Room, events: inout [GameEvent]) {
        if isDashing {
            dashTimer -= dt
            velocity = dashDirection * Tuning.dashSpeed
            if dashTimer <= 0 {
                isDashing = false
                velocity = dashDirection * Tuning.dashExitSpeed
            }
            return
        }

        guard input.dashPressed,
              progression.has(.herzschlag),
              dashAvailable,
              dashCooldown <= 0,
              controlLock <= 0
        else { return }

        var dir = Vec2(input.moveX, 0)
        if abs(input.moveX) < 0.01 { dir = Vec2(facing, 0) }
        // Schraeg nach oben oder unten, wenn gezielt wird.
        if abs(input.aimY) > 0.5 {
            dir = Vec2(dir.x, input.aimY).normalized
        }
        dashDirection = dir.normalized
        isDashing = true
        dashAvailable = false
        dashTimer = Tuning.dashDuration
        dashCooldown = Tuning.dashCooldown
        invulnerable = max(invulnerable, Tuning.dashDuration + 0.04)
        if abs(dashDirection.x) > 0.01 { facing = sign(dashDirection.x) }
        events.append(.sound(.dash))
        events.append(.effect(.heartbeat, chest, .zero))
    }

    // MARK: - Basston

    private func handleSlam(input: PlayerInput, events: inout [GameEvent]) {
        if isSlamming { return }
        guard input.slamPressed,
              progression.has(.basston),
              !onGround,
              !isDashing,
              controlLock <= 0
        else { return }
        isSlamming = true
        velocity.x = 0
        velocity.y = Tuning.slamSpeed
        events.append(.sound(.slamStart))
    }

    private func finishSlam(room: Room, events: inout [GameEvent]) {
        isSlamming = false
        slamRecovery = Tuning.slamRecovery
        velocity.x = 0

        let area = Rect(x: position.x - 22, y: position.y - 6, width: 44, height: 26)
        let broken = room.breakWalls(in: area)
        events.append(.sound(broken.isEmpty ? .slamLand : .wallBreak))
        events.append(.effect(.ringTrommel, position, .zero))
        events.append(.shake(broken.isEmpty ? 3.0 : 6.0))
        if !broken.isEmpty {
            events.append(.wallsBroken(roomID: room.id, tiles: broken))
        }
        events.append(.slamShockwave(origin: position, radius: 34))
    }

    // MARK: - Angriffe

    private func handleAttacks(input: PlayerInput, events: inout [GameEvent]) {
        guard attackCooldown <= 0, controlLock <= 0, !isSlamming else { return }

        if input.meleePressed {
            let profile = Tuning.melee(instrument)
            attackIsMelee = true
            attackTimer = profile.duration
            attackCooldown = profile.cooldown
            attackHasHit = false
            stateTime = 0
            events.append(.sound(.meleeSwing(instrument)))
            return
        }

        if input.rangedPressed {
            let profile = Tuning.ranged(instrument)
            guard resonance >= profile.cost else {
                events.append(.sound(.outOfResonance))
                return
            }
            resonance -= profile.cost
            attackIsMelee = false
            attackTimer = 0.18
            attackCooldown = profile.cooldown
            stateTime = 0
            events.append(.sound(.rangedShot(instrument)))
            events.append(.fireProjectiles(instrument: instrument,
                                           origin: muzzle(),
                                           direction: aimDirection()))
        }
    }

    /// Der Punkt, an dem der Ton die Figur verlaesst.
    public func muzzle() -> Vec2 {
        let dir = aimDirection()
        return chest + dir * 12
    }

    public func aimDirection() -> Vec2 {
        if aimY < -0.5 { return Vec2(0, -1) }
        if aimY > 0.5 && !onGround { return Vec2(0, 1) }
        return Vec2(facing, 0)
    }

    /// Aktive Trefferflaeche des Nahkampfs, sonst `nil`.
    public func activeMeleeHitbox() -> Rect? {
        guard attackIsMelee, attackTimer > 0 else { return nil }
        let profile = Tuning.melee(instrument)
        let elapsed = profile.duration - attackTimer
        guard elapsed >= profile.windup else { return nil }
        return profile.hitbox(origin: position, facing: facing, aimY: aimY)
    }

    public func registerMeleeHit(count: Int) {
        guard count > 0 else { return }
        attackHasHit = true
        resonance = min(progression.maxResonance,
                        resonance + Tuning.resonancePerMeleeHit * Double(min(count, 3)))
    }

    /// Abprallen, wenn nach unten geschlagen wurde (Hollow-Knight-Manier).
    public func pogo() {
        velocity.y = Tuning.pogoVelocity
        airJumpsLeft = progression.has(.fluegelschlag) ? 1 : 0
        dashAvailable = true
        isSlamming = false
    }

    public func gainResonance(_ amount: Double) {
        resonance = min(progression.maxResonance, resonance + amount)
    }

    // MARK: - Bewegung und Kollision

    private func moveAndCollide(dt: Double, room: Room, events: inout [GameEvent]) {
        let wasOnGround = onGround
        let fallSpeed = velocity.y

        let hitWall = moveX(velocity.x * dt, room: room)
        if hitWall { velocity.x = 0 }

        let vertical = moveY(velocity.y * dt, room: room)
        switch vertical {
        case .none:
            onGround = false
            onCeiling = false
        case .ceiling:
            onCeiling = true
            onGround = false
            velocity.y = max(velocity.y, 0)
        case .ground:
            onCeiling = false
            onGround = true
            if isSlamming {
                finishSlam(room: room, events: &events)
            } else if !wasOnGround && fallSpeed > 220 {
                events.append(.sound(.land(min(1, fallSpeed / Tuning.maxFallSpeed))))
                events.append(.effect(.dust, position, .zero))
            }
            velocity.y = 0
        }

        if onGround {
            coyoteTimer = Tuning.coyoteTime
            airJumpsLeft = progression.has(.fluegelschlag) ? 1 : 0
            dashAvailable = true
        }

        position.x = clamp(position.x, Tuning.playerWidth / 2, room.bounds.maxX - Tuning.playerWidth / 2)
    }

    private enum VerticalContact { case none, ground, ceiling }

    /// Schiebt die Figur so weit wie moeglich in die gewuenschte Richtung und
    /// legt sie danach buendig an das Hindernis. Ohne dieses Nachruecken
    /// bliebe nach einer Landung bis zu eine Schrittweite Luft unter den
    /// Fuessen - und die naechste Bodenpruefung waere falsch.
    private func slide(_ amount: Double, axis: Vec2, blocked: (Rect) -> Bool) -> Bool {
        guard amount != 0 else { return false }
        let maxStep = 3.0
        var remaining = amount
        var hit = false
        while abs(remaining) > 1e-6 {
            let delta = abs(remaining) < maxStep ? remaining : (remaining > 0 ? maxStep : -maxStep)
            if blocked(rect.offset(by: axis * delta)) {
                hit = true
                // Rest halbierend annaehern, bis es buendig sitzt.
                var fine = delta
                while abs(fine) > 0.03 {
                    fine *= 0.5
                    if !blocked(rect.offset(by: axis * fine)) {
                        position += axis * fine
                    }
                }
                break
            }
            position += axis * delta
            remaining -= delta
        }
        return hit
    }

    /// Bewegt in X-Richtung und meldet, ob eine Wand im Weg war.
    @discardableResult
    private func moveX(_ amount: Double, room: Room) -> Bool {
        slide(amount, axis: Vec2(1, 0)) { room.overlapsSolid($0) }
    }

    private func moveY(_ amount: Double, room: Room) -> VerticalContact {
        // Die Einwegplattform darf nur greifen, wenn die Fusslinie zu Beginn
        // der Bewegung oberhalb ihrer Kante lag.
        let entryBottom = rect.maxY

        guard amount != 0 else {
            let probe = rect.offset(by: Vec2(0, 0.6))
            return room.overlapsGround(probe, previousBottom: entryBottom) ? .ground : .none
        }

        let falling = amount > 0
        let hit = slide(amount, axis: Vec2(0, 1)) { probe in
            falling
                ? room.overlapsGround(probe, previousBottom: entryBottom)
                : room.overlapsSolid(probe)
        }

        if hit { return falling ? .ground : .ceiling }
        if falling {
            let probe = rect.offset(by: Vec2(0, 0.6))
            if room.overlapsGround(probe, previousBottom: rect.maxY) { return .ground }
        }
        return .none
    }

    // MARK: - Wand

    private func updateWallState(room: Room, input: PlayerInput, dt: Double) {
        wallSide = 0
        if !onGround {
            let left = rect.offset(by: Vec2(-2, 0))
            let right = rect.offset(by: Vec2(2, 0))
            if room.overlapsSolid(right) { wallSide = 1 }
            if room.overlapsSolid(left) { wallSide = -1 }
        }

        let wantsWall = progression.has(.klangschritt)
            && wallSide != 0
            && !onGround
            && !isDashing
            && !isSlamming
            && velocity.y > -20
            && abs(input.moveX) > 0.1
            && sign(input.moveX) == wallSide

        isWallSliding = wantsWall
        if wallSide != 0 && progression.has(.klangschritt) {
            wallCoyoteTimer = Tuning.wallStickTime
        }
        if isWallSliding {
            facing = -wallSide
            velocity.y = min(velocity.y, Tuning.wallSlideSpeed)
            airJumpsLeft = progression.has(.fluegelschlag) ? 1 : 0
            dashAvailable = true
        }
    }

    private func regenerateResonance(dt: Double) {
        resonance = min(progression.maxResonance, resonance + Tuning.resonanceRegen * dt)
    }

    // MARK: - Schaden

    /// Meldet, ob der Treffer angekommen ist.
    @discardableResult
    public func takeDamage(_ amount: Int, from source: Vec2, events: inout [GameEvent]) -> Bool {
        guard invulnerable <= 0, !isDead, !isResting else { return false }
        health -= amount
        invulnerable = Tuning.invulnerableTime
        controlLock = Tuning.hurtControlLock
        isDashing = false
        isSlamming = false
        dashTimer = 0

        let away = position.x < source.x ? -1.0 : 1.0
        velocity.x = away * Tuning.hurtKnockbackX
        velocity.y = Tuning.hurtKnockbackY

        if health <= 0 {
            health = 0
            isDead = true
            events.append(.sound(.playerDeath))
            events.append(.playerDied)
        } else {
            events.append(.sound(.playerHurt))
            events.append(.shake(5))
        }
        return true
    }

    public func beginRest() {
        isResting = true
        velocity = .zero
    }

    public func endRest() {
        isResting = false
    }

    // MARK: - Zustandsableitung

    private func setState(_ next: PlayerState) {
        if state != next {
            state = next
            stateTime = 0
        }
    }

    private func updateState() {
        if isDead { setState(.dead); return }
        if isResting { setState(.rest); return }
        if isSlamming { setState(.slam); return }
        if isDashing { setState(.dash); return }
        if controlLock > 0 { setState(.hurt); return }
        if attackTimer > 0 { setState(attackIsMelee ? .melee : .cast); return }
        if isWallSliding { setState(.wallSlide); return }
        if !onGround { setState(velocity.y < 0 ? .jump : .fall); return }
        setState(abs(velocity.x) > 12 ? .run : .idle)
    }
}
