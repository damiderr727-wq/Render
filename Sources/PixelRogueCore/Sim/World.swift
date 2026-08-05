import Foundation

/// Player-only state that has no meaning for any other actor.
public struct PlayerState: Sendable {
    public var dodgeTimer: Double = 0
    public var dodgeCooldown: Double = 0
    public var dodgeDirection: Vec2 = .zero
    public var fireHeld: Double = 0
    public var chargeTime: Double = 0
    public var orbitAngle: Double = 0
    public var lastAimAngle: Double = 0
    public var recoilKick: Vec2 = .zero
    public var interactTarget: Int? = nil

    public var isDodging: Bool { dodgeTimer > 0 }
}

/// The whole simulation for one floor.
///
/// A class, not a struct: it is mutated tens of times per frame from the game
/// loop and passing 300 projectiles by value on every call would be silly.
/// Everything it *contains* is a value type, so state is still easy to reason
/// about and snapshot.
public final class World {
    public private(set) var dungeon: Dungeon
    public private(set) var actors: [Actor] = []
    public private(set) var projectiles: [Projectile] = []
    public private(set) var pickups: [Pickup] = []
    public private(set) var hazards: [HazardZone] = []
    public private(set) var events: [GameEvent] = []

    public var run: RunState
    public var player = PlayerState()
    public private(set) var playerID = ActorID.none
    public private(set) var time: Double = 0
    public private(set) var currentRoom: Int = 0
    public private(set) var doorsLocked = false
    public private(set) var floorComplete = false
    public private(set) var playerDead = false

    /// Slow motion. Driven by items and by the moment a boss dies.
    public var timeScale: Double = 1
    private var timeScaleRecovery: Double = 0

    private var rng: RNG
    private var nextActorRaw = 1
    private var nextProjectileRaw = 1
    private var nextPickupRaw = 1
    private var enemiesSpawnedForRoom: Set<Int> = []

    public static let dodgeDuration = 0.32
    public static let dodgeSpeed = 260.0
    public static let baseDodgeCooldown = 0.7

    public init(run: RunState, generator: DungeonGenerator = DungeonGenerator()) {
        self.run = run
        self.dungeon = generator.generate(floor: run.depth, theme: run.theme,
                                          seed: run.floorSeed)
        self.rng = RNG(seed: run.floorSeed &* 31 &+ 7)
        spawnPlayer()
        populateFloor()
    }

    // -- accessors -----------------------------------------------------------

    public var playerActor: Actor? { actor(playerID) }

    public func actor(_ id: ActorID) -> Actor? {
        actors.first { $0.id == id && $0.alive }
    }

    public func actorIndex(_ id: ActorID) -> Int? {
        actors.firstIndex { $0.id == id }
    }

    public var livingEnemies: [Actor] {
        actors.filter { $0.alive && $0.kind.isHostile }
    }

    public var activeBoss: Actor? {
        actors.first { $0.alive && $0.kind.isBoss }
    }

    public func drainEvents() -> [GameEvent] {
        defer { events.removeAll(keepingCapacity: true) }
        return events
    }

    public var room: Room { dungeon.rooms[currentRoom] }

    // -- setup ---------------------------------------------------------------

    private func newActorID() -> ActorID {
        defer { nextActorRaw += 1 }
        return ActorID(nextActorRaw)
    }

    private func spawnPlayer() {
        let start = dungeon.rooms[dungeon.startRoom]
        var actor = Actor(id: newActorID(), kind: .player, faction: .player,
                          position: start.center, health: run.health)
        actor.maxHealth = run.maxHealth
        actor.radius = 6
        actor.moveSpeed = run.moveSpeed
        actor.spriteBase = run.character.spriteBase
        actor.armor = run.armor
        actor.homeRoom = dungeon.startRoom
        playerID = actor.id
        actors.append(actor)
        currentRoom = dungeon.startRoom
    }

    /// Props and shop stock exist from the start; enemies spawn when their
    /// room is entered, so a floor does not simulate 200 actors at once.
    private func populateFloor() {
        for placement in dungeon.props {
            guard placement.blocking || placement.destructible else { continue }
            var prop = Actor(id: newActorID(), kind: .prop(placement.name),
                             faction: .neutral, position: placement.position,
                             health: placement.destructible ? 1 : 9999)
            prop.radius = placement.name == "pillar" ? 9 : 7
            prop.destructible = placement.destructible
            prop.homeRoom = placement.room
            prop.spriteBase = "prop/\(dungeon.theme)/\(placement.name)"
            actors.append(prop)
        }

        for room in dungeon.rooms {
            switch room.kind {
            case .shop:
                stockShop(room)
            case .treasure:
                spawnTreasure(room)
            default:
                break
            }
        }
    }

    private func stockShop(_ room: Room) {
        var offsets = [Vec2(-40, 10), Vec2(0, 14), Vec2(40, 10)]
        offsets = rng.shuffled(offsets)
        let owned = run.loadout.ownedItemIDs

        if let item = ItemCatalog.randomDrop(rng: &rng, luck: run.stats.luck,
                                             excluding: owned) {
            addPickup(.item(item.id), at: room.center + offsets[0],
                      room: room.index, price: run.price(item.price))
        }
        let weapon = WeaponCatalog.randomDrop(rng: &rng, luck: run.stats.luck,
                                              excluding: carriedWeaponIDs())
        addPickup(.weapon(weapon.id), at: room.center + offsets[1],
                  room: room.index, price: run.price(45 + weapon.rarity * 25))
        let consumable: Pickup.Payload = rng.chance(0.5) ? .heart(20) : .blank
        addPickup(consumable, at: room.center + offsets[2], room: room.index,
                  price: run.price(18))
    }

    private func spawnTreasure(_ room: Room) {
        let owned = run.loadout.ownedItemIDs
        if rng.chance(0.55), let item = ItemCatalog.randomDrop(
            rng: &rng, luck: run.stats.luck, excluding: owned) {
            addPickup(.item(item.id), at: room.center, room: room.index)
        } else {
            let weapon = WeaponCatalog.randomDrop(rng: &rng, luck: run.stats.luck,
                                                   excluding: carriedWeaponIDs())
            addPickup(.weapon(weapon.id), at: room.center, room: room.index)
        }
    }

    private func carriedWeaponIDs() -> Set<String> {
        Set(run.loadout.weapons.map(\.def.id))
    }

    @discardableResult
    private func addPickup(_ payload: Pickup.Payload, at position: Vec2,
                           room: Int, price: Int = 0) -> Int {
        defer { nextPickupRaw += 1 }
        let pickup = Pickup(id: nextPickupRaw, payload: payload,
                            position: dungeon.map.nearestWalkable(to: position),
                            bobPhase: rng.double(0, 6.28), room: room,
                            price: price)
        pickups.append(pickup)
        return pickup.id
    }

    // -- main loop -----------------------------------------------------------

    public func step(dt rawDt: Double, input: InputState) {
        // Clamp so a stalled frame (window drag, breakpoint) cannot teleport
        // everything through walls.
        let frame = min(rawDt, 1.0 / 20.0)
        let dt = frame * timeScale
        time += dt
        run.elapsed += frame

        if timeScaleRecovery > 0 {
            timeScaleRecovery -= frame
            if timeScaleRecovery <= 0 { timeScale = 1 }
        }

        updatePlayer(dt: dt, input: input)
        updateEnemies(dt: dt)
        updateProjectiles(dt: dt)
        updateHazards(dt: dt)
        updateStatuses(dt: dt)
        updatePickups(dt: dt, input: input)
        updateRoomState()
        compact()
    }

    // -- player --------------------------------------------------------------

    private func updatePlayer(dt: Double, input: InputState) {
        guard let index = actorIndex(playerID), actors[index].alive else { return }
        let stats = run.stats

        actors[index].moveSpeed = run.character.moveSpeed * stats.moveSpeedMultiplier
        if player.dodgeCooldown > 0 { player.dodgeCooldown -= dt }
        if actors[index].invulnerableFor > 0 { actors[index].invulnerableFor -= dt }
        if actors[index].hitFlashFor > 0 { actors[index].hitFlashFor -= dt }

        // Dodge roll: fixed-length burst with invulnerability, and no steering
        // once committed. Being unable to correct mid-roll is the whole reason
        // the move has weight.
        if input.dodgePressed && !player.isDodging && player.dodgeCooldown <= 0 {
            let direction = input.move != .zero
                ? input.move.normalized
                : (input.aim - actors[index].position).normalized
            if direction != .zero {
                player.dodgeTimer = Self.dodgeDuration
                player.dodgeDirection = direction
                player.dodgeCooldown = Self.baseDodgeCooldown *
                    stats.dodgeCooldownMultiplier
                actors[index].invulnerableFor = Self.dodgeDuration * 0.8 +
                    stats.invulnBonus
                events.append(.playerDodged)
                events.append(.effect(EffectRequest(
                    name: "fx/dust_ring",
                    position: actors[index].position + Vec2(0, 6))))
                events.append(.sound("dodge", volume: 0.6))
            }
        }

        var velocity: Vec2
        if player.isDodging {
            player.dodgeTimer -= dt
            let progress = 1 - (player.dodgeTimer / Self.dodgeDuration)
            let speedCurve = 1.25 - Ease.inCubic(progress) * 0.75
            velocity = player.dodgeDirection * Self.dodgeSpeed *
                speedCurve * stats.dodgeDistanceMultiplier
        } else {
            velocity = input.move.clampedLength(1) * actors[index].moveSpeed
        }

        velocity += player.recoilKick
        player.recoilKick = Vec2.damp(player.recoilKick, .zero, rate: 9, dt: dt)

        actors[index].velocity = velocity
        move(&actors[index], dt: dt)

        let aimVector = input.aim - actors[index].position
        if aimVector.lengthSquared > 4 {
            actors[index].aimAngle = aimVector.angle
            player.lastAimAngle = actors[index].aimAngle
        }
        actors[index].facing = facingFor(velocity: velocity,
                                         aim: aimVector,
                                         moving: input.move != .zero)
        actors[index].animation = player.isDodging
            ? "roll"
            : (input.move != .zero ? walkAnim(actors[index].facing)
                                   : idleAnim(actors[index].facing))
        actors[index].animationTime += dt

        run.health = actors[index].health
        run.armor = actors[index].armor

        handleWeaponInput(dt: dt, input: input, playerIndex: index)
        updateOrbitals(dt: dt, playerIndex: index)

        if input.blankPressed { useBlank() }
    }

    private func facingFor(velocity: Vec2, aim: Vec2, moving: Bool) -> Cardinal {
        // Aim wins when standing still, movement wins when running: that
        // combination reads correctly in both twin-stick and keyboard play.
        let reference = moving ? velocity : aim
        return reference == .zero ? .south : reference.cardinal
    }

    private func idleAnim(_ facing: Cardinal) -> String {
        switch facing {
        case .north: return "idle_back"
        case .south: return "idle_front"
        default: return "idle_side"
        }
    }

    private func walkAnim(_ facing: Cardinal) -> String {
        switch facing {
        case .north: return "walk_back"
        case .south: return "walk_front"
        default: return "walk_side"
        }
    }

    private func handleWeaponInput(dt: Double, input: InputState,
                                   playerIndex: Int) {
        if input.weaponCycle != 0 {
            run.loadout.cycleWeapon(by: input.weaponCycle)
            events.append(.sound("weapon_switch", volume: 0.5))
        }
        if let slot = input.weaponSelect {
            run.loadout.selectWeapon(slot)
        }

        let stats = run.stats
        var didFire = false
        var shotOrigin = Vec2.zero
        var shotAngle = 0.0
        var firedDef: WeaponDef?

        run.loadout.updateActiveWeapon { weapon in
            if weapon.cooldown > 0 { weapon.cooldown -= dt }

            if weapon.isReloading {
                weapon.reloadRemaining -= dt
                if weapon.reloadRemaining <= 0 { weapon.finishReload() }
                return
            }
            if input.reloadPressed { weapon.beginReload(speedMultiplier: stats.reloadSpeedMultiplier) }
            if weapon.isEmpty {
                if weapon.canRefill {
                    weapon.beginReload(speedMultiplier: stats.reloadSpeedMultiplier)
                }
                return
            }

            let def = weapon.def
            let origin = self.actors[playerIndex].position
            let angle = self.actors[playerIndex].aimAngle

            // Charge weapons hold the trigger, everything else taps it.
            if def.mode == .charge {
                if input.firing {
                    weapon.chargeHeld += dt
                    return
                }
                if weapon.chargeHeld > 0 {
                    let ratio = min(1, weapon.chargeHeld / max(0.05, def.chargeTime))
                    weapon.chargeHeld = 0
                    guard ratio > 0.35, weapon.cooldown <= 0 else { return }
                    weapon.cooldown = WeaponMath.interval(def, stats)
                    weapon.ammoInMagazine -= 1
                    didFire = true
                    shotOrigin = origin
                    shotAngle = angle
                    var scaled = def
                    scaled.pellets = max(3, Int(Double(def.pellets) * ratio))
                    scaled.damage = def.damage * (0.5 + ratio * 0.8)
                    firedDef = scaled
                }
                return
            }

            // Burst weapons keep firing after the trigger is released.
            if weapon.burstRemaining > 0 {
                weapon.burstTimer -= dt
                if weapon.burstTimer <= 0 && weapon.ammoInMagazine > 0 {
                    weapon.burstRemaining -= 1
                    weapon.burstTimer = def.burstInterval
                    weapon.ammoInMagazine -= 1
                    didFire = true
                    shotOrigin = origin
                    shotAngle = angle
                    firedDef = def
                }
                return
            }

            guard input.firing, weapon.cooldown <= 0 else { return }
            weapon.cooldown = WeaponMath.interval(def, stats)
            weapon.ammoInMagazine -= 1
            didFire = true
            shotOrigin = origin
            shotAngle = angle
            firedDef = def
            if def.mode == .burst {
                weapon.burstRemaining = def.burstCount - 1
                weapon.burstTimer = def.burstInterval
            }
        }

        if didFire, let def = firedDef {
            fire(def: def, from: shotOrigin, angle: shotAngle, stats: stats,
                 faction: .player, owner: playerID)
            // Recoil shoves the player: with the Hand Cannon this is a
            // mobility tool, which is the joke the weapon is built around.
            player.recoilKick -= Vec2.angle(shotAngle) * def.recoil * 6
            events.append(.shake(strength: def.shake, duration: 0.12))
            events.append(.sound("shoot_\(def.id)", volume: 0.7))
        }
    }

    private func updateOrbitals(dt: Double, playerIndex: Int) {
        let wanted = run.stats.orbitals
        let existing = actors.filter { $0.alive && $0.kind == .orbital }
        player.orbitAngle += dt * 2.4

        if existing.count < wanted {
            var orb = Actor(id: newActorID(), kind: .orbital, faction: .player,
                            position: actors[playerIndex].position, health: 1)
            orb.radius = 6
            orb.contactDamage = 12
            orb.spriteBase = "proj/saw"
            actors.append(orb)
        }

        let center = actors[playerIndex].position
        var slot = 0
        for i in actors.indices where actors[i].kind == .orbital && actors[i].alive {
            let count = max(1, wanted)
            let angle = player.orbitAngle + Double(slot) * 2 * .pi / Double(count)
            actors[i].position = center + Vec2.angle(angle) * 34
            actors[i].contactDamage = 12 * run.stats.damageMultiplier
            slot += 1
            if slot > wanted { actors[i].alive = false }
        }

        // Orbitals hurt whatever they sweep through.
        for i in actors.indices where actors[i].kind == .orbital && actors[i].alive {
            let orbPos = actors[i].position
            for j in actors.indices where actors[j].alive && actors[j].kind.isHostile {
                if Collision.circlesOverlap(orbPos, actors[i].radius,
                                            actors[j].position, actors[j].radius) {
                    if actors[j].invulnerableFor <= 0 {
                        applyDamage(to: j, info: DamageInfo(
                            amount: actors[i].contactDamage * dt * 4,
                            source: orbPos, knockback: 20))
                    }
                }
            }
        }
    }

    private func useBlank() {
        guard run.blanks > 0, let player = playerActor else { return }
        run.blanks -= 1
        var cleared = 0
        for i in projectiles.indices where projectiles[i].faction == .enemy {
            projectiles[i].alive = false
            cleared += 1
        }
        // A blank also pushes enemies off you, which is what makes it a
        // panic button rather than merely a screen wipe.
        for i in actors.indices where actors[i].alive && actors[i].kind.isHostile {
            let away = (actors[i].position - player.position).normalized
            actors[i].velocity += away * 220
            applyDamage(to: i, info: DamageInfo(amount: 6, source: player.position,
                                                knockback: 180))
        }
        events.append(.blankUsed(at: player.position))
        events.append(.effect(EffectRequest(name: "fx/shockwave",
                                            position: player.position, scale: 3)))
        events.append(.shake(strength: 5, duration: 0.25))
        events.append(.sound("blank", volume: 0.9))
    }

    // -- movement ------------------------------------------------------------

    private func move(_ actor: inout Actor, dt: Double) {
        guard actor.velocity != .zero else { return }
        let flying = actor.enemy?.flying ?? false
        var next = actor.position + actor.velocity * dt

        if !flying {
            next = dungeon.map.collide(position: next, radius: actor.radius)
        } else {
            // Flyers ignore interior walls but still respect the map edge.
            let bounds = dungeon.map.worldBounds.inset(by: actor.radius + 8)
            next = bounds.clamp(next)
        }
        actor.position = next
    }

    /// Actors push each other apart so a swarm does not stack into one pixel.
    private func separate(_ index: Int, dt: Double) {
        let position = actors[index].position
        let radius = actors[index].radius
        var push = Vec2.zero
        for j in actors.indices where j != index && actors[j].alive {
            guard actors[j].kind.isHostile || actors[j].kind == .player else { continue }
            let delta = position - actors[j].position
            let minDistance = radius + actors[j].radius
            let distanceSquared = delta.lengthSquared
            if distanceSquared < minDistance * minDistance && distanceSquared > 1e-6 {
                let distance = distanceSquared.squareRoot()
                push += delta.normalized * ((minDistance - distance) * 0.5)
            }
        }
        if push != .zero {
            actors[index].position += push.clampedLength(40 * dt + 1)
        }
    }

    // -- enemies -------------------------------------------------------------

    private func updateEnemies(dt: Double) {
        guard let player = playerActor else { return }

        for i in actors.indices {
            guard actors[i].alive, actors[i].kind.isHostile else {
                if !actors[i].alive && actors[i].deathTimer > 0 {
                    actors[i].deathTimer -= dt
                }
                continue
            }
            if actors[i].invulnerableFor > 0 { actors[i].invulnerableFor -= dt }
            if actors[i].hitFlashFor > 0 { actors[i].hitFlashFor -= dt }
            if actors[i].stunnedFor > 0 { actors[i].stunnedFor -= dt }
            if actors[i].attackCooldown > 0 { actors[i].attackCooldown -= dt }

            if actors[i].kind.isBoss {
                stepBoss(index: i, player: player, dt: dt)
            } else {
                stepEnemy(index: i, player: player, dt: dt)
            }

            separate(i, dt: dt)
            actors[i].animationTime += dt
            actors[i].animation = animationFor(actors[i])

            // Contact damage, both directions.
            if Collision.circlesOverlap(actors[i].position, actors[i].radius,
                                        player.position, player.radius) {
                if actors[i].contactDamage > 0 {
                    damagePlayer(amount: actors[i].contactDamage * dt * 2.2,
                                 from: actors[i].position, knockback: 90)
                }
                let thorns = run.stats.contactDamage
                if thorns > 0 && actors[i].invulnerableFor <= 0 {
                    applyDamage(to: i, info: DamageInfo(amount: thorns * dt * 2,
                                                        source: player.position,
                                                        knockback: 30))
                }
            }
        }
    }

    private func animationFor(_ actor: Actor) -> String {
        guard actor.enemy?.rig == .humanoid else { return "" }
        let moving = actor.velocity.lengthSquared > 200
        let facing = actor.velocity == .zero ? actor.facing : actor.velocity.cardinal
        switch facing {
        case .north: return moving ? "walk_back" : "idle_back"
        case .south: return moving ? "walk_front" : "idle_front"
        default: return moving ? "walk_side" : "idle_side"
        }
    }

    private func stepEnemy(index: Int, player: Actor, dt: Double) {
        guard let def = actors[index].enemy else { return }
        // Enemies only think while the player is in their room, which keeps
        // a full floor cheap and stops off-screen enemies wandering away.
        guard actors[index].homeRoom == currentRoom || actors[index].kind.isBoss else {
            actors[index].velocity = .zero
            return
        }

        let toPlayer = player.position - actors[index].position
        let distance = toPlayer.length
        let direction = toPlayer.normalized
        let speed = def.speed * actors[index].speedMultiplier
        var desired = Vec2.zero

        switch actors[index].ai {
        case .windUp(let remaining):
            actors[index].aiTimer -= dt
            desired = .zero
            if actors[index].aiTimer <= 0 {
                performAttack(index: index, target: player.position)
                actors[index].ai = .recover(def.attackCooldown)
                actors[index].aiTimer = def.attackCooldown
            } else {
                _ = remaining
            }

        case .recover(let total):
            actors[index].aiTimer -= dt
            desired = -direction * speed * 0.35
            if actors[index].aiTimer <= 0 { actors[index].ai = .chase }
            _ = total

        case .attack:
            // Charger dash: committed movement, no steering.
            actors[index].aiTimer -= dt
            desired = actors[index].velocity
            if actors[index].aiTimer <= 0 {
                actors[index].ai = .recover(def.attackCooldown)
                actors[index].aiTimer = def.attackCooldown
            }

        default:
            switch def.behavior {
            case .chaser, .flyer:
                desired = direction * speed
                if def.behavior == .flyer {
                    // Sine drift so flyers do not travel in a dead-straight line.
                    let wobble = sin(time * 3 + Double(actors[index].id.raw)) * 0.5
                    desired = desired.rotated(by: wobble * 0.6)
                }
            case .shooter:
                if distance < def.preferredRange * 0.75 {
                    desired = -direction * speed
                } else if distance > def.preferredRange * 1.25 {
                    desired = direction * speed
                } else {
                    desired = direction.perpendicular * speed * 0.5
                }
            case .strafer:
                let orbit = direction.perpendicular *
                    (actors[index].patternIndex % 2 == 0 ? 1 : -1)
                let radial = distance > def.preferredRange ? direction : -direction
                desired = (orbit * 0.8 + radial * 0.5).normalized * speed
            case .charger:
                desired = distance > def.attackRange ? direction * speed
                                                     : direction * speed * 0.4
            case .turret:
                desired = .zero
            case .bomber:
                desired = direction * speed
            case .summoner:
                desired = distance < def.preferredRange
                    ? -direction * speed
                    : direction.perpendicular * speed * 0.6
            }

            let canSee = def.flying ||
                dungeon.map.hasLineOfSight(from: actors[index].position,
                                           to: player.position)
            if def.attack != nil, distance <= def.attackRange, canSee,
               actors[index].attackCooldown <= 0 {
                actors[index].ai = .windUp(def.windUp)
                actors[index].aiTimer = def.windUp
                actors[index].attackCooldown = def.attackCooldown + def.windUp
                events.append(.effect(EffectRequest(
                    name: "fx/impact_spark",
                    position: actors[index].position - Vec2(0, 14), scale: 0.6)))
            }
        }

        if actors[index].stunnedFor > 0 { desired = .zero }
        actors[index].velocity = Vec2.damp(actors[index].velocity, desired,
                                           rate: 12, dt: dt)
        move(&actors[index], dt: dt)
    }

    private func performAttack(index: Int, target: Vec2) {
        guard let def = actors[index].enemy, let pattern = def.attack else { return }
        let origin = actors[index].position
        actors[index].patternPhase += 1
        actors[index].patternIndex += 1

        switch pattern {
        case let .dash(speed, duration):
            let direction = (target - origin).normalized
            actors[index].velocity = direction * speed
            actors[index].ai = .attack
            actors[index].aiTimer = duration
            events.append(.sound("dash", volume: 0.5))

        case let .detonate(radius, damage):
            explode(at: origin, radius: radius, damage: damage, faction: .enemy)
            actors[index].health = 0
            killActor(index: index)

        case let .summon(kind, count):
            guard let summon = EnemyCatalog.enemy(kind) else { return }
            for _ in 0..<count {
                let offset = rng.unitVector() * rng.double(24, 48)
                spawnEnemy(summon, at: origin + offset, room: actors[index].homeRoom)
            }
            events.append(.effect(EffectRequest(name: "fx/teleport",
                                                position: origin)))

        case .beamSweep:
            // Reserved for bosses; enemies fall back to a fan.
            let specs = BulletPatterns.emit(
                .aimed(count: 5, spread: 0.8, speed: 180, damage: 8,
                       sprite: "proj/bolt_enemy"),
                origin: origin, toward: target,
                phase: actors[index].patternPhase, rng: &rng)
            spawn(specs, from: origin, faction: .enemy, owner: actors[index].id)

        default:
            let specs = BulletPatterns.emit(pattern, origin: origin,
                                            toward: target,
                                            phase: actors[index].patternPhase,
                                            rng: &rng)
            spawn(specs, from: origin, faction: .enemy, owner: actors[index].id)
            events.append(.sound("enemy_shoot", volume: 0.4))
        }
    }

    // -- bosses --------------------------------------------------------------

    private func stepBoss(index: Int, player: Actor, dt: Double) {
        guard case let .boss(bossID) = actors[index].kind,
              let def = BossCatalog.boss(bossID) else { return }

        let phaseIndex = def.phaseIndex(forHealthFraction: actors[index].healthFraction)
        if phaseIndex != actors[index].bossPhase {
            actors[index].bossPhase = phaseIndex
            actors[index].invulnerableFor = 0.8
            let phase = def.phases[phaseIndex]
            events.append(.bossPhaseChanged(name: def.name, phase: phaseIndex))
            if !phase.announcement.isEmpty {
                events.append(.notice(phase.announcement))
            }
            events.append(.effect(EffectRequest(name: "fx/shockwave",
                                                position: actors[index].position,
                                                scale: 4)))
            events.append(.shake(strength: 8, duration: 0.5))
            // Clear the screen on a phase change: inheriting the last phase's
            // bullet wall on top of a new pattern is unfair, not hard.
            for i in projectiles.indices where projectiles[i].faction == .enemy {
                projectiles[i].alive = false
            }
        }

        let phase = def.phases[phaseIndex]
        let toPlayer = player.position - actors[index].position
        let direction = toPlayer.normalized
        let speed = def.speed * phase.speedMultiplier * actors[index].speedMultiplier

        switch actors[index].ai {
        case .idle, .chase:
            if actors[index].attackCooldown <= 0 {
                let weights = phase.moves.map { (value: $0, weight: $0.weight) }
                guard let move = rng.weighted(weights) else { break }
                actors[index].patternIndex = phase.moves.firstIndex { $0.name == move.name } ?? 0
                actors[index].ai = .windUp(move.windUp)
                actors[index].aiTimer = move.windUp
                events.append(.effect(EffectRequest(
                    name: "fx/impact_spark",
                    position: actors[index].position, scale: 1.5)))
            }
            actors[index].velocity = Vec2.damp(actors[index].velocity,
                                                direction * speed * 0.5,
                                                rate: 6, dt: dt)

        case .windUp:
            actors[index].aiTimer -= dt
            actors[index].velocity = Vec2.damp(actors[index].velocity, .zero,
                                                rate: 8, dt: dt)
            if actors[index].aiTimer <= 0 {
                let move = phase.moves[min(actors[index].patternIndex,
                                           phase.moves.count - 1)]
                actors[index].ai = .attack
                actors[index].aiTimer = 0
                actors[index].patternPhase += 1
                actors[index].bossVolleysLeft = move.volleys
            }

        case .attack:
            let move = phase.moves[min(actors[index].patternIndex,
                                       phase.moves.count - 1)]
            actors[index].aiTimer -= dt
            if actors[index].aiTimer <= 0 && actors[index].bossVolleysLeft > 0 {
                fireBossMove(move, index: index, target: player.position)
                actors[index].bossVolleysLeft -= 1
                actors[index].aiTimer = move.volleyInterval
                actors[index].patternPhase += 1
            }
            if actors[index].bossVolleysLeft <= 0 && actors[index].ai == .attack {
                actors[index].ai = .recover(move.recover)
                actors[index].aiTimer = move.recover
                actors[index].attackCooldown = move.recover
            }
            actors[index].velocity = bossDrift(move.drift, index: index,
                                                direction: direction,
                                                speed: speed, dt: dt)

        case .recover:
            actors[index].aiTimer -= dt
            actors[index].velocity = Vec2.damp(actors[index].velocity,
                                                -direction * speed * 0.3,
                                                rate: 5, dt: dt)
            if actors[index].aiTimer <= 0 { actors[index].ai = .chase }

        default:
            actors[index].ai = .chase
        }

        move(&actors[index], dt: dt)
    }

    private func bossDrift(_ drift: BossDrift, index: Int, direction: Vec2,
                           speed: Double, dt: Double) -> Vec2 {
        let target: Vec2
        switch drift {
        case .hold: target = .zero
        case .approach: target = direction * speed * 0.8
        case .retreat: target = -direction * speed * 0.7
        case .circle: target = direction.perpendicular * speed
        case .reposition:
            let wobble = sin(time * 1.6 + Double(index))
            target = (direction.perpendicular * wobble + direction * 0.3) * speed
        }
        return Vec2.damp(actors[index].velocity, target, rate: 6, dt: dt)
    }

    private func fireBossMove(_ move: BossMove, index: Int, target: Vec2) {
        let origin = actors[index].position
        switch move.pattern {
        case let .dash(speed, duration):
            actors[index].velocity = (target - origin).normalized * speed
            actors[index].aiTimer = duration
            events.append(.shake(strength: 3, duration: 0.2))
        case let .summon(kind, count):
            guard let def = EnemyCatalog.enemy(kind) else { return }
            for _ in 0..<count {
                let offset = rng.unitVector() * rng.double(50, 90)
                spawnEnemy(def, at: origin + offset, room: actors[index].homeRoom)
            }
            events.append(.effect(EffectRequest(name: "fx/teleport",
                                                position: origin, scale: 2)))
        case .detonate(let radius, let damage):
            explode(at: origin, radius: radius, damage: damage, faction: .enemy)
        default:
            let specs = BulletPatterns.emit(move.pattern, origin: origin,
                                            toward: target,
                                            phase: actors[index].patternPhase,
                                            rng: &rng)
            spawn(specs, from: origin, faction: .enemy, owner: actors[index].id)
            events.append(.sound("boss_shoot", volume: 0.5))
        }
    }

    // -- projectiles ---------------------------------------------------------

    private func spawn(_ specs: [BulletSpec], from origin: Vec2,
                       faction: Faction, owner: ActorID) {
        for spec in specs {
            var projectile = Projectile(
                id: nextProjectileRaw, position: origin + spec.offset,
                velocity: spec.direction.normalized * spec.speed,
                radius: spec.radius, damage: spec.damage, faction: faction,
                owner: owner, sprite: spec.sprite)
            nextProjectileRaw += 1
            projectile.lifetime = spec.lifetime
            projectile.curve = spec.curve
            projectile.homing = spec.homing
            projectile.status = spec.status
            projectile.statusChance = spec.status != nil ? 1 : 0
            projectile.scale = spec.scale
            projectile.spin = spec.spin
            projectiles.append(projectile)
        }
    }

    /// Turns one trigger pull into projectiles, applying every player stat.
    public func fire(def: WeaponDef, from origin: Vec2, angle: Double,
                     stats: StatBlock, faction: Faction, owner: ActorID) {
        let muzzleDistance = 14.0
        let muzzle = origin + Vec2.angle(angle) * muzzleDistance
        events.append(.effect(EffectRequest(name: def.muzzleFX, position: muzzle,
                                            angle: angle)))

        if def.mode == .beam {
            fireBeam(def: def, from: muzzle, angle: angle, stats: stats,
                     faction: faction, owner: owner)
            return
        }

        let count = WeaponMath.pelletCount(def, stats)
        let spread = def.spread * stats.spreadMultiplier
        let offsets = WeaponMath.spreadAngles(count: count, spread: spread,
                                              rng: &rng)
        let damage = WeaponMath.damage(def, stats)

        for offset in offsets {
            let direction = Vec2.angle(angle + offset)
            var projectile = Projectile(
                id: nextProjectileRaw,
                position: muzzle,
                velocity: direction * def.projectileSpeed *
                    stats.projectileSpeedMultiplier,
                radius: def.projectileRadius * stats.projectileSizeMultiplier,
                damage: damage, faction: faction, owner: owner,
                sprite: def.projectileSprite)
            nextProjectileRaw += 1
            projectile.lifetime = def.projectileLife * stats.projectileRangeMultiplier
            projectile.pierce = def.pierce + stats.pierce
            projectile.bounces = def.bounces + stats.bounces
            projectile.homing = def.homing + stats.homingStrength
            projectile.chain = def.chain
            projectile.knockback = def.knockback * stats.knockbackMultiplier
            projectile.impactFX = def.impactFX
            projectile.scale = stats.projectileSizeMultiplier
            projectile.curve = def.curve
            projectile.explodeRadius = def.explodeRadius +
                (stats.explosiveShots ? 24 + stats.explosionRadiusBonus : 0)
            if def.explodeRadius > 0 {
                projectile.explodeRadius += stats.explosionRadiusBonus
            }

            // Weapon status first, then whatever items add on top.
            if let status = def.status, rng.chance(def.statusChance) {
                projectile.status = status
            } else {
                for kind in StatusKind.allCases where projectile.status == nil {
                    if rng.chance(stats.chance(for: kind)) { projectile.status = kind }
                }
            }

            switch def.mode {
            case .arc:
                projectile.arcGravity = def.arcGravity
                projectile.height = 1
                // Enough upward speed to land near the aim point.
                projectile.verticalSpeed = def.arcGravity * def.projectileLife * 0.5
            case .boomerang:
                projectile.returnsTo = owner
            case .orbit:
                projectile.orbitOwner = owner
                projectile.orbitRadius = 34
                projectile.orbitAngle = angle + rng.double(-0.6, 0.6)
                projectile.orbitDelay = 0.55
            default:
                break
            }

            projectiles.append(projectile)
        }
    }

    private func fireBeam(def: WeaponDef, from origin: Vec2, angle: Double,
                          stats: StatBlock, faction: Faction, owner: ActorID) {
        let direction = Vec2.angle(angle)
        let range = def.beamRange * stats.projectileRangeMultiplier
        let wallHit = dungeon.map.raycast(from: origin, direction: direction,
                                          maxDistance: range)
        var endpoint = wallHit ?? (origin + direction * range)
        let damage = WeaponMath.damage(def, stats) * 0.2   // per tick

        var hits: [(index: Int, distance: Double)] = []
        for i in actors.indices where actors[i].alive {
            guard actors[i].faction.isHostile(to: faction) else { continue }
            let toActor = actors[i].position - origin
            let along = toActor.dot(direction)
            guard along > 0, along < endpoint.distance(to: origin) + actors[i].radius
            else { continue }
            let perpendicular = (toActor - direction * along).length
            if perpendicular <= actors[i].radius + 5 {
                hits.append((i, along))
            }
        }
        hits.sort { $0.distance < $1.distance }

        for hit in hits {
            applyDamage(to: hit.index, info: DamageInfo(
                amount: damage, source: origin, knockback: 0,
                isCrit: rng.chance(stats.critChance),
                status: def.status, faction: faction))
            if def.pierce <= 0 && !def.tags.contains(.void) {
                endpoint = actors[hit.index].position
                break
            }
        }

        events.append(.effect(EffectRequest(
            name: def.impactFX, position: endpoint, angle: angle)))
        beamEndpoint = (origin, endpoint)
        beamAge = 0.08
    }

    /// The renderer draws the beam from this, refreshed every shot tick.
    public private(set) var beamEndpoint: (Vec2, Vec2)? = nil
    private var beamAge: Double = 0

    private func updateProjectiles(dt: Double) {
        if beamAge > 0 {
            beamAge -= dt
            if beamAge <= 0 { beamEndpoint = nil }
        }

        for i in projectiles.indices {
            guard projectiles[i].alive else { continue }
            projectiles[i].age += dt
            if projectiles[i].age >= projectiles[i].lifetime {
                expire(projectileIndex: i)
                continue
            }
            projectiles[i].rotation += projectiles[i].spin * dt

            // Orbit motes hang around the owner, then launch.
            if projectiles[i].orbitOwner != .none {
                if projectiles[i].orbitDelay > 0 {
                    projectiles[i].orbitDelay -= dt
                    if let owner = actor(projectiles[i].orbitOwner) {
                        projectiles[i].orbitAngle += dt * 5
                        projectiles[i].position = owner.position +
                            Vec2.angle(projectiles[i].orbitAngle) *
                            projectiles[i].orbitRadius
                    }
                    if projectiles[i].orbitDelay <= 0 {
                        let target = nearestHostile(to: projectiles[i].position,
                                                    faction: projectiles[i].faction)
                        let direction = target.map {
                            ($0.position - projectiles[i].position).normalized
                        } ?? Vec2.angle(projectiles[i].orbitAngle)
                        projectiles[i].velocity = direction * 300
                        projectiles[i].orbitOwner = .none
                    }
                    continue
                }
            }

            // Boomerangs decelerate, reverse, and are caught by their owner.
            if projectiles[i].returnsTo != .none {
                let owner = actor(projectiles[i].returnsTo)
                if projectiles[i].age > projectiles[i].lifetime * 0.4 {
                    projectiles[i].returning = true
                }
                if projectiles[i].returning, let owner {
                    let home = (owner.position - projectiles[i].position)
                    if home.length < 14 {
                        projectiles[i].alive = false
                        continue
                    }
                    projectiles[i].velocity = Vec2.damp(
                        projectiles[i].velocity, home.normalized * 420,
                        rate: 4, dt: dt)
                    projectiles[i].hitActors.removeAll()
                }
            }

            if projectiles[i].homing > 0 {
                steer(projectileIndex: i, dt: dt)
            }

            var velocity = projectiles[i].velocity
            if projectiles[i].curve != 0 {
                projectiles[i].curvePhase += dt * 9
                let sideways = velocity.normalized.perpendicular
                velocity += sideways * (cos(projectiles[i].curvePhase) *
                                        projectiles[i].curve)
            }

            if projectiles[i].arcGravity > 0 {
                projectiles[i].verticalSpeed -= projectiles[i].arcGravity * dt
                projectiles[i].height += projectiles[i].verticalSpeed * dt
                if projectiles[i].height <= 0 {
                    projectiles[i].height = 0
                    land(projectileIndex: i)
                    continue
                }
            }

            projectiles[i].position += velocity * dt

            if resolveWorldCollision(projectileIndex: i) { continue }
            resolveActorCollision(projectileIndex: i)
        }
    }

    private func steer(projectileIndex i: Int, dt: Double) {
        if projectiles[i].homingTarget == .none ||
            actor(projectiles[i].homingTarget) == nil {
            projectiles[i].homingTarget = nearestHostile(
                to: projectiles[i].position,
                faction: projectiles[i].faction)?.id ?? .none
        }
        guard let target = actor(projectiles[i].homingTarget) else { return }
        let speed = projectiles[i].velocity.length
        guard speed > 1 else { return }
        let wanted = (target.position - projectiles[i].position).normalized
        let current = projectiles[i].velocity.normalized
        let blended = Vec2.lerp(current, wanted,
                                min(1, projectiles[i].homing * dt)).normalized
        projectiles[i].velocity = blended * speed
    }

    private func nearestHostile(to point: Vec2, faction: Faction) -> Actor? {
        var best: Actor?
        var bestDistance = Double.infinity
        for candidate in actors where candidate.alive {
            guard candidate.faction.isHostile(to: faction) else { continue }
            let distance = candidate.position.distanceSquared(to: point)
            if distance < bestDistance {
                bestDistance = distance
                best = candidate
            }
        }
        return best
    }

    private func resolveWorldCollision(projectileIndex i: Int) -> Bool {
        // Airborne lobbed shots fly over walls.
        if projectiles[i].isAirborne { return false }
        let position = projectiles[i].position
        let (tx, ty) = dungeon.map.tileCoord(position)
        guard dungeon.map[tx, ty].blocksSight else { return false }

        if projectiles[i].bounces > 0 {
            projectiles[i].bounces -= 1
            // Reflect off whichever axis we crossed this frame.
            let previous = position - projectiles[i].velocity * (1.0 / 60.0)
            let (px, py) = dungeon.map.tileCoord(previous)
            if px != tx && !dungeon.map[px, ty].blocksSight {
                projectiles[i].velocity.x *= -1
            } else if py != ty && !dungeon.map[tx, py].blocksSight {
                projectiles[i].velocity.y *= -1
            } else {
                projectiles[i].velocity = -projectiles[i].velocity
            }
            projectiles[i].position = previous
            projectiles[i].hitActors.removeAll()
            events.append(.effect(EffectRequest(name: "fx/impact_spark",
                                                position: position, scale: 0.6)))
            return false
        }

        expire(projectileIndex: i)
        return true
    }

    private func resolveActorCollision(projectileIndex i: Int) {
        guard projectiles[i].alive, !projectiles[i].isAirborne else { return }
        let stats = run.stats

        for j in actors.indices where actors[j].alive {
            guard !projectiles[i].hitActors.contains(actors[j].id.raw) else { continue }

            let hostile = actors[j].faction.isHostile(to: projectiles[i].faction)
            let breakable = actors[j].destructible && projectiles[i].faction == .player
            guard hostile || breakable else { continue }
            guard Collision.circlesOverlap(projectiles[i].position,
                                            projectiles[i].radius,
                                            actors[j].position,
                                            actors[j].radius) else { continue }

            projectiles[i].hitActors.insert(actors[j].id.raw)

            if actors[j].kind == .player {
                // Mirror Shard: turn the shot around instead of eating it.
                if rng.chance(stats.reflectChance) {
                    projectiles[i].faction = .player
                    projectiles[i].velocity = -projectiles[i].velocity
                    projectiles[i].hitActors.removeAll()
                    projectiles[i].damage *= 1.5
                    events.append(.effect(EffectRequest(
                        name: "fx/shockwave", position: projectiles[i].position,
                        scale: 0.6)))
                    continue
                }
                damagePlayer(amount: projectiles[i].damage,
                             from: projectiles[i].position,
                             knockback: projectiles[i].knockback)
            } else if breakable {
                breakProp(index: j)
            } else {
                let crit = projectiles[i].faction == .player
                    && rng.chance(stats.critChance)
                var amount = projectiles[i].damage
                if crit { amount *= stats.critMultiplier }
                applyDamage(to: j, info: DamageInfo(
                    amount: amount, source: projectiles[i].position,
                    knockback: projectiles[i].knockback, isCrit: crit,
                    status: projectiles[i].status,
                    faction: projectiles[i].faction))

                if projectiles[i].chain > 0 {
                    chainLightning(from: j, projectileIndex: i)
                }
            }

            if projectiles[i].explodeRadius > 0 {
                explode(at: projectiles[i].position,
                        radius: projectiles[i].explodeRadius,
                        damage: projectiles[i].damage * 0.8,
                        faction: projectiles[i].faction)
                projectiles[i].alive = false
                return
            }

            events.append(.effect(EffectRequest(name: projectiles[i].impactFX,
                                                position: projectiles[i].position,
                                                angle: projectiles[i].angle)))
            if projectiles[i].pierce > 0 {
                projectiles[i].pierce -= 1
            } else if projectiles[i].returnsTo == .none {
                projectiles[i].alive = false
                return
            }
        }
    }

    private func chainLightning(from actorIndex: Int, projectileIndex i: Int) {
        var remaining = projectiles[i].chain
        var origin = actors[actorIndex].position
        var struck: Set<Int> = [actors[actorIndex].id.raw]

        while remaining > 0 {
            var best: Int?
            var bestDistance = 140.0
            for j in actors.indices where actors[j].alive && actors[j].kind.isHostile {
                guard !struck.contains(actors[j].id.raw) else { continue }
                let distance = actors[j].position.distance(to: origin)
                if distance < bestDistance {
                    bestDistance = distance
                    best = j
                }
            }
            guard let next = best else { break }
            struck.insert(actors[next].id.raw)
            let target = actors[next].position
            events.append(.effect(EffectRequest(
                name: "fx/lightning_arc",
                position: Vec2.lerp(origin, target, 0.5),
                angle: (target - origin).angle,
                scale: origin.distance(to: target) / 32)))
            applyDamage(to: next, info: DamageInfo(
                amount: projectiles[i].damage * 0.6, source: origin,
                knockback: 20, status: .shock,
                faction: projectiles[i].faction))
            origin = target
            remaining -= 1
        }
    }

    private func land(projectileIndex i: Int) {
        let position = projectiles[i].position
        if projectiles[i].explodeRadius > 0 {
            explode(at: position, radius: projectiles[i].explodeRadius,
                    damage: projectiles[i].damage, faction: projectiles[i].faction)
        }
        projectiles[i].alive = false
    }

    private func expire(projectileIndex i: Int) {
        if projectiles[i].explodeRadius > 0 && projectiles[i].faction == .player {
            explode(at: projectiles[i].position,
                    radius: projectiles[i].explodeRadius,
                    damage: projectiles[i].damage * 0.7,
                    faction: projectiles[i].faction)
        }
        projectiles[i].alive = false
    }

    public func explode(at position: Vec2, radius: Double, damage: Double,
                        faction: Faction) {
        events.append(.effect(EffectRequest(name: "fx/explosion",
                                            position: position,
                                            scale: radius / 20)))
        events.append(.shake(strength: min(9, radius / 8), duration: 0.28))
        events.append(.sound("explosion", volume: 0.8))

        for j in actors.indices where actors[j].alive {
            let distance = actors[j].position.distance(to: position)
            guard distance < radius + actors[j].radius else { continue }
            // Falloff so standing at the rim is survivable.
            let falloff = 1 - (distance / (radius + actors[j].radius)) * 0.55

            if actors[j].kind == .player {
                if faction == .enemy {
                    damagePlayer(amount: damage * falloff, from: position,
                                 knockback: 140)
                }
            } else if actors[j].destructible {
                breakProp(index: j)
            } else if actors[j].faction.isHostile(to: faction) {
                applyDamage(to: j, info: DamageInfo(amount: damage * falloff,
                                                    source: position,
                                                    knockback: 150,
                                                    faction: faction))
            }
        }

        // Explosions set off other barrels.
        for j in actors.indices where actors[j].alive && actors[j].destructible {
            if actors[j].position.distance(to: position) < radius {
                breakProp(index: j)
            }
        }
    }

    // -- damage --------------------------------------------------------------

    private func applyDamage(to index: Int, info: DamageInfo) {
        guard actors[index].alive, actors[index].invulnerableFor <= 0 else { return }
        var amount = info.amount
        let stats = run.stats

        // Status vulnerabilities: cursed and chilled targets take more.
        for status in StatusKind.allCases where actors[index].has(status) {
            amount *= 1 + (stats.statusDamageBonus[status] ?? 0)
        }

        actors[index].health -= amount
        actors[index].hitFlashFor = 0.09
        if info.knockback > 0 {
            let push = (actors[index].position - info.source).normalized
            actors[index].velocity += push * info.knockback
        }
        if let status = info.status {
            actors[index].apply(status: status, sourceDamage: amount)
        }

        events.append(.damageNumber(amount: amount,
                                    at: actors[index].position - Vec2(0, 16),
                                    crit: info.isCrit))
        if info.isCrit {
            events.append(.hitStop(0.045))
            events.append(.sound("crit", volume: 0.7))
        }

        if actors[index].health <= 0 {
            killActor(index: index)
        }
    }

    private func damagePlayer(amount: Double, from source: Vec2,
                              knockback: Double) {
        guard let index = actorIndex(playerID), actors[index].alive else { return }
        guard actors[index].invulnerableFor <= 0, !player.isDodging else { return }

        if actors[index].armor > 0 {
            actors[index].armor -= 1
            run.armor = actors[index].armor
            actors[index].invulnerableFor = 1.0 + run.stats.invulnBonus
            events.append(.effect(EffectRequest(name: "fx/shockwave",
                                                position: actors[index].position,
                                                scale: 0.8)))
            events.append(.sound("armor_break", volume: 0.8))
            events.append(.playerHurt(remaining: actors[index].health))
            return
        }

        actors[index].health -= amount
        run.health = actors[index].health
        run.damageTaken += amount
        actors[index].invulnerableFor = 1.1 + run.stats.invulnBonus
        actors[index].hitFlashFor = 0.2

        if knockback > 0 {
            let push = (actors[index].position - source).normalized
            actors[index].velocity += push * knockback
        }

        events.append(.playerHurt(remaining: actors[index].health))
        events.append(.shake(strength: 6, duration: 0.3))
        events.append(.hitStop(0.08))
        events.append(.sound("player_hurt", volume: 0.9))
        events.append(.effect(EffectRequest(name: "fx/blood_splat",
                                            position: actors[index].position)))

        // Clock Spring: a hit buys you a moment to recover from it.
        if run.stats.timeSlowOnHit > 0 {
            timeScale = 0.35
            timeScaleRecovery = run.stats.timeSlowOnHit
        }

        if actors[index].health <= 0 {
            actors[index].alive = false
            playerDead = true
            events.append(.playerDied)
            events.append(.shake(strength: 10, duration: 0.6))
        }
    }

    private func killActor(index: Int) {
        guard actors[index].alive else { return }
        actors[index].alive = false
        actors[index].deathTimer = 0.5
        actors[index].velocity = .zero
        let position = actors[index].position

        if case let .enemy(id) = actors[index].kind {
            run.kills += 1
            events.append(.enemyKilled(kind: id, at: position))
            events.append(.effect(EffectRequest(name: "fx/blood_splat",
                                                position: position)))
            dropLoot(from: actors[index])
            // Pyroclasm: things that die on fire take the room with them.
            if actors[index].has(.burn) && run.stats.chance(for: .burn) > 0.5 {
                explode(at: position, radius: 40, damage: 12, faction: .player)
            }
        } else if case let .boss(id) = actors[index].kind {
            events.append(.bossDefeated(name: BossCatalog.boss(id)?.name ?? id))
            events.append(.shake(strength: 12, duration: 1.0))
            timeScale = 0.4
            timeScaleRecovery = 1.6
            run.bossesFelled.append(id)
            for _ in 0..<3 {
                addPickup(.coin(rng.int(8, 16)),
                          at: position + rng.unitVector() * 30,
                          room: currentRoom)
            }
            addPickup(.heart(20), at: position + Vec2(0, 26), room: currentRoom)
            spawnFloorReward(at: position)
        }

        let heal = run.stats.lifestealOnKill
        if heal > 0, let playerIndex = actorIndex(playerID) {
            actors[playerIndex].health = min(actors[playerIndex].maxHealth,
                                             actors[playerIndex].health + heal)
            run.health = actors[playerIndex].health
            events.append(.healNumber(amount: heal,
                                      at: actors[playerIndex].position))
        }
        if rng.chance(run.stats.healOnKillChance),
           let playerIndex = actorIndex(playerID) {
            actors[playerIndex].health = min(actors[playerIndex].maxHealth,
                                             actors[playerIndex].health + 5)
            run.health = actors[playerIndex].health
        }
    }

    private func breakProp(index: Int) {
        guard actors[index].alive else { return }
        actors[index].alive = false
        let position = actors[index].position
        events.append(.effect(EffectRequest(name: "fx/smoke_puff",
                                            position: position)))
        events.append(.sound("break", volume: 0.6))

        if case let .prop(name) = actors[index].kind, name == "barrel_explosive" {
            explode(at: position, radius: 62, damage: 34, faction: .player)
            return
        }
        if rng.chance(0.3) {
            let payload: Pickup.Payload = rng.chance(0.5)
                ? .coin(rng.int(1, 3)) : .ammo
            addPickup(payload, at: position, room: actors[index].homeRoom)
        }
    }

    private func dropLoot(from actor: Actor) {
        guard let def = actor.enemy else { return }
        let luck = run.stats.luck
        if rng.chance(0.55) {
            addPickup(.coin(def.coinValue), at: actor.position, room: currentRoom)
        }
        if rng.chance(0.1 + luck * 0.02) {
            addPickup(.ammo, at: actor.position + Vec2(6, 0), room: currentRoom)
        }
        if rng.chance(0.05 + luck * 0.015) {
            addPickup(.heart(10), at: actor.position - Vec2(6, 0), room: currentRoom)
        }
        if rng.chance(0.02 + luck * 0.01) {
            addPickup(.blank, at: actor.position, room: currentRoom)
        }
    }

    private func spawnFloorReward(at position: Vec2) {
        let owned = run.loadout.ownedItemIDs
        if let item = ItemCatalog.randomDrop(rng: &rng, luck: run.stats.luck + 2,
                                             excluding: owned) {
            addPickup(.item(item.id), at: position + Vec2(0, -30),
                      room: currentRoom)
        }
    }

    // -- statuses and hazards -------------------------------------------------

    private func updateStatuses(dt: Double) {
        for i in actors.indices where actors[i].alive && !actors[i].statuses.isEmpty {
            var died = false
            for s in actors[i].statuses.indices.reversed() {
                actors[i].statuses[s].remaining -= dt
                actors[i].statuses[s].tickTimer -= dt

                let effect = actors[i].statuses[s]
                if effect.tickTimer <= 0 && effect.kind.tickDamage > 0 {
                    actors[i].statuses[s].tickTimer = 0.5
                    if actors[i].kind != .player {
                        let tick = effect.kind.tickDamage * Double(effect.stacks) * 0.5
                        actors[i].health -= tick
                        events.append(.damageNumber(
                            amount: tick,
                            at: actors[i].position - Vec2(0, 20), crit: false))
                        if actors[i].health <= 0 { died = true }
                    }
                }
                if actors[i].statuses[s].remaining <= 0 {
                    actors[i].statuses.remove(at: s)
                }
            }
            if died { killActor(index: i) }
        }
    }

    private func updateHazards(dt: Double) {
        for i in hazards.indices.reversed() {
            hazards[i].remaining -= dt
            hazards[i].tickTimer -= dt
            if hazards[i].tickTimer <= 0 {
                hazards[i].tickTimer = 0.4
                for j in actors.indices where actors[j].alive {
                    guard actors[j].faction.isHostile(to: hazards[i].faction) else { continue }
                    guard actors[j].position.distance(to: hazards[i].position)
                            < hazards[i].radius else { continue }
                    if actors[j].kind == .player {
                        damagePlayer(amount: hazards[i].damagePerSecond * 0.4,
                                     from: hazards[i].position, knockback: 0)
                    } else {
                        applyDamage(to: j, info: DamageInfo(
                            amount: hazards[i].damagePerSecond * 0.4,
                            source: hazards[i].position,
                            status: hazards[i].status,
                            faction: hazards[i].faction))
                    }
                }
            }
            if hazards[i].remaining <= 0 { hazards.remove(at: i) }
        }
    }

    // -- pickups and rooms ----------------------------------------------------

    private func updatePickups(dt: Double, input: InputState) {
        guard let playerIndex = actorIndex(playerID), actors[playerIndex].alive
        else { return }
        let position = actors[playerIndex].position
        let magnetRange = 26 + run.stats.pickupRadiusBonus
        player.interactTarget = nil

        for i in pickups.indices.reversed() {
            pickups[i].age += dt
            let distance = pickups[i].position.distance(to: position)

            // Free pickups drift toward the player once in range.
            if pickups[i].price == 0 && !pickups[i].requiresInteract
                && distance < magnetRange && distance > 4 {
                let pull = (position - pickups[i].position).normalized
                pickups[i].position += pull * min(240, 60 + magnetRange) * dt
            }

            guard distance < 16 else { continue }

            if pickups[i].requiresInteract {
                player.interactTarget = pickups[i].id
                if input.interactPressed {
                    if collect(pickupIndex: i) { pickups.remove(at: i) }
                }
            } else if collect(pickupIndex: i) {
                pickups.remove(at: i)
            }
        }
    }

    /// Returns true when the pickup was consumed.
    private func collect(pickupIndex i: Int) -> Bool {
        let pickup = pickups[i]

        if pickup.price > 0 {
            guard run.coins >= pickup.price else {
                events.append(.shopRefused(reason: "Need \(pickup.price) coins"))
                events.append(.sound("refused", volume: 0.5))
                return false
            }
            run.coins -= pickup.price
        }

        switch pickup.payload {
        case .heart(let amount):
            guard run.health < run.maxHealth || pickup.price > 0 else { return false }
            run.heal(amount)
            syncPlayerHealth()
            events.append(.healNumber(amount: amount, at: pickup.position))
        case .armor:
            run.armor += 1
            syncPlayerHealth()
        case .ammo:
            run.loadout.refillAmmo(fraction: 0.35)
        case .key:
            run.keys += 1
        case .coin(let amount):
            run.addCoins(amount)
        case .blank:
            run.blanks += 1
        case .item(let id):
            let gained = run.loadout.add(item: id)
            run.refreshDerivedHealth()
            syncPlayerHealth()
            for synergy in gained {
                events.append(.synergyActivated(id: synergy.id, name: synergy.name,
                                                summary: synergy.summary))
            }
        case .weapon(let id):
            guard let def = WeaponCatalog.weapon(id) else { return false }
            let result = run.loadout.add(weapon: def)
            for synergy in result.gained {
                events.append(.synergyActivated(id: synergy.id, name: synergy.name,
                                                summary: synergy.summary))
            }
            if let dropped = result.dropped {
                addPickup(.weapon(dropped.id),
                          at: pickup.position + Vec2(0, 20), room: pickup.room)
            }
        }

        events.append(.pickedUp(label: pickup.label, sprite: pickup.sprite))
        events.append(.effect(EffectRequest(name: "fx/pickup_shine",
                                            position: pickup.position)))
        events.append(.sound("pickup", volume: 0.7))
        return true
    }

    private func syncPlayerHealth() {
        guard let index = actorIndex(playerID) else { return }
        actors[index].health = run.health
        actors[index].maxHealth = run.maxHealth
        actors[index].armor = run.armor
    }

    private func updateRoomState() {
        guard let player = playerActor else { return }
        guard let roomIndex = dungeon.map.room(at: player.position) else { return }

        if roomIndex != currentRoom {
            currentRoom = roomIndex
            dungeon.rooms[roomIndex].visited = true
            dungeon.rooms[roomIndex].discovered = true
            for doorIndex in dungeon.rooms[roomIndex].doors {
                let door = dungeon.doors[doorIndex]
                let other = door.roomA == roomIndex ? door.roomB : door.roomA
                dungeon.rooms[other].discovered = true
            }
            events.append(.roomEntered(roomIndex))
            enterRoom(roomIndex)
        }

        if doorsLocked {
            let remaining = actors.contains {
                $0.alive && $0.kind.isHostile && $0.homeRoom == currentRoom
            }
            if !remaining {
                doorsLocked = false
                dungeon.rooms[currentRoom].cleared = true
                run.roomsCleared += 1
                events.append(.roomCleared(currentRoom))
                events.append(.doorsUnlocked)
                events.append(.sound("room_cleared", volume: 0.8))
                rewardRoomClear()
            }
        }
    }

    private func enterRoom(_ index: Int) {
        let room = dungeon.rooms[index]
        guard !room.cleared, !enemiesSpawnedForRoom.contains(index) else { return }

        if room.kind == .boss {
            enemiesSpawnedForRoom.insert(index)
            spawnBoss(in: room)
            doorsLocked = true
            events.append(.doorsLocked)
            return
        }

        guard room.kind.spawnsEnemies else { return }
        enemiesSpawnedForRoom.insert(index)

        let budget = 3 + run.depth * 2 + room.depth
        let roster = EnemyCatalog.roll(budget: budget, floor: run.depth, rng: &rng)
        guard !roster.isEmpty else {
            dungeon.rooms[index].cleared = true
            return
        }

        for def in roster {
            let spot = spawnPoint(in: room, awayFrom: playerActor?.position)
            spawnEnemy(def, at: spot, room: index)
        }
        doorsLocked = true
        events.append(.doorsLocked)
        events.append(.sound("doors_close", volume: 0.6))
    }

    private func spawnPoint(in room: Room, awayFrom origin: Vec2?) -> Vec2 {
        let rect = room.worldRect.inset(by: 24)
        for _ in 0..<24 {
            let candidate = Vec2(rng.double(rect.minX, rect.maxX),
                                 rng.double(rect.minY, rect.maxY))
            guard dungeon.map.isWalkable(candidate) else { continue }
            if let origin, candidate.distance(to: origin) < 70 { continue }
            return candidate
        }
        return dungeon.map.nearestWalkable(to: room.center)
    }

    @discardableResult
    public func spawnEnemy(_ def: EnemyDef, at position: Vec2,
                           room: Int) -> ActorID {
        var actor = Actor(id: newActorID(), kind: .enemy(def.id),
                          faction: .enemy,
                          position: dungeon.map.nearestWalkable(to: position),
                          health: def.health * healthScale)
        actor.radius = def.radius
        actor.moveSpeed = def.speed
        actor.contactDamage = def.contactDamage
        actor.enemy = def
        actor.spriteBase = def.spriteBase
        actor.homeRoom = room
        actor.ai = .chase
        actor.attackCooldown = rng.double(0.3, def.attackCooldown)
        actor.height = def.flying ? 10 : 0
        actors.append(actor)
        events.append(.effect(EffectRequest(name: "fx/teleport",
                                            position: actor.position)))
        return actor.id
    }

    /// Enemies scale a little with depth so floor 4 trash is not a nuisance.
    private var healthScale: Double { 1 + Double(run.depth - 1) * 0.22 }

    private func spawnBoss(in room: Room) {
        let def = BossCatalog.boss(forFloor: run.depth)
        let anchor = dungeon.map.nearestWalkable(to: room.center - Vec2(0, 40))
        var actor = Actor(id: newActorID(), kind: .boss(def.id), faction: .enemy,
                          position: anchor, health: def.health)
        actor.radius = def.radius
        actor.moveSpeed = def.speed
        actor.contactDamage = def.contactDamage
        actor.spriteBase = def.spriteBase
        actor.homeRoom = room.index
        actor.ai = .chase
        actor.attackCooldown = 1.2
        actors.append(actor)
        events.append(.notice(def.phases.first?.announcement ?? def.name))
        events.append(.sound("boss_intro", volume: 1.0))
        events.append(.shake(strength: 6, duration: 0.6))
    }

    private func rewardRoomClear() {
        guard let player = playerActor else { return }
        if rng.chance(0.35) {
            addPickup(.coin(rng.int(2, 6)), at: player.position + Vec2(20, 0),
                      room: currentRoom)
        }
        if dungeon.rooms[currentRoom].kind == .boss {
            floorComplete = true
            events.append(.floorCleared(depth: run.depth))
        }
    }

    /// Removes the dead once their death animation has played out.
    private func compact() {
        projectiles.removeAll { !$0.alive }
        actors.removeAll { !$0.alive && $0.deathTimer <= 0 && $0.kind != .player }
        if projectiles.count > 1200 {
            // Hard cap: a runaway pattern should degrade, not freeze the game.
            projectiles.removeFirst(projectiles.count - 1200)
        }
    }

    // -- floor transition -----------------------------------------------------

    /// Moves the player instantly. Used by the descend transition and by
    /// tests that need to reach a specific room without playing the floor.
    public func teleportPlayer(to position: Vec2) {
        guard let index = actorIndex(playerID) else { return }
        actors[index].position = dungeon.map.nearestWalkable(to: position)
        actors[index].velocity = .zero
        if let room = dungeon.map.room(at: actors[index].position) {
            currentRoom = room
            dungeon.rooms[room].visited = true
            dungeon.rooms[room].discovered = true
            enterRoom(room)
        }
        events.append(.effect(EffectRequest(name: "fx/teleport",
                                            position: actors[index].position)))
    }

    public var canDescend: Bool { floorComplete }

    /// Builds the next floor, carrying the run over.
    public func descend() -> World? {
        guard floorComplete, run.depth < RunState.maxDepth else { return nil }
        var next = run
        next.depth += 1
        next.loadout.refillAmmo(fraction: 0.5)
        return World(run: next)
    }
}
