import Foundation

/// Ein aufsammelbares Fundstueck im Raum.
public struct PickupInstance: Sendable {
    public enum Payload: Sendable {
        case kern(Kern)
        case ability(Ability)
        case equipment(Equipment)
        case siegel(Siegel)
        case klinge(Klinge)
    }
    public let key: String
    public let payload: Payload
    public var position: Vec2
    public var bobPhase: Double
}

/// Eine lesbare Inschrift.
public struct LoreInstance: Sendable {
    public let key: String
    public let position: Vec2
    public let text: String
}

/// Die Stimmgabel - Rast, Heilung, Speicherpunkt.
public struct BenchInstance: Sendable {
    public let position: Vec2
}

/// Wozu die Figur gerade aufgefordert wird, wenn sie vor etwas steht.
public enum Prompt: Sendable, Equatable {
    case none
    case bench
    case lore(String)
    case gate(Ability)
}

/// Der gesamte Spielzustand. Enthaelt keine Darstellung und keinen Ton -
/// nur was gilt.
public final class GameSimulation {
    public let catalog: WorldCatalog

    public private(set) var room: Room
    public private(set) var player: Player
    public private(set) var enemies: [Enemy] = []
    public private(set) var projectiles: [Projectile] = []
    public private(set) var boss: Boss?
    public private(set) var pickups: [PickupInstance] = []
    public private(set) var lore: [LoreInstance] = []
    public private(set) var benches: [BenchInstance] = []

    public private(set) var save: SaveState
    public private(set) var prompt: Prompt = .none
    public private(set) var elapsed: Double = 0
    public private(set) var musicTrack: String = "hain"
    public private(set) var musicIntensity: Double = 0
    public private(set) var isComplete = false

    /// Kamera-Zielpunkt in Weltpunkten.
    public private(set) var cameraTarget: Vec2 = .zero

    private var nextEntityID = 1
    private var deathTimer: Double = 0
    private var restTimer: Double = 0
    /// Angesammelter Zerfall im Bruch, in halben Kristallen.
    private var zerfall: Double = 0
    private var transitionCooldown: Double = 0
    private var intensityTarget: Double = 0
    private var shownGateHints: Set<String> = []

    // MARK: - Aufbau

    public init(catalog: WorldCatalog, save: SaveState = SaveState()) throws {
        self.catalog = catalog
        self.save = save
        let startRoom = try catalog.room(save.roomID)
        self.room = startRoom
        let spawn = startRoom.spawn(named: save.spawnName)
            ?? startRoom.spawn(named: catalog.index.startSpawn)
            ?? RoomData.SpawnPoint(x: 4, y: 4, facing: 1)
        self.player = Player(position: Vec2.entity(spawn.x, spawn.y),
                             progression: save.progression,
                             kern: save.kern)
        applyBrokenWalls(to: startRoom)
        populate(room: startRoom, spawn: spawn)
        cameraTarget = player.position
        musicTrack = startRoom.data.music
    }

    /// Neues Spiel vom Anfang.
    public static func newGame(catalog: WorldCatalog) throws -> GameSimulation {
        catalog.reset()
        let save = SaveState(roomID: catalog.index.startRoom,
                             spawnName: catalog.index.startSpawn)
        return try GameSimulation(catalog: catalog, save: save)
    }

    private func applyBrokenWalls(to room: Room) {
        guard let flat = save.brokenWalls[room.id] else { return }
        var i = 0
        while i + 1 < flat.count {
            room.setTile(flat[i], flat[i + 1], .air)
            i += 2
        }
    }

    private func populate(room: Room, spawn: RoomData.SpawnPoint) {
        enemies.removeAll()
        projectiles.removeAll()
        pickups.removeAll()
        lore.removeAll()
        benches.removeAll()
        boss = nil

        for e in room.data.enemies {
            guard let kind = EnemyKind(rawValue: e.type) else { continue }
            enemies.append(Enemy(id: takeID(), kind: kind,
                                 position: Vec2.entity(e.x, e.y),
                                 patrolTiles: e.patrol))
        }

        for p in room.data.pickups {
            let key = "\(room.id)/\(p.id)"
            guard !save.collected.contains(key) else { continue }
            let payload: PickupInstance.Payload?
            switch p.kind {
            case "kern": payload = Kern(rawValue: p.id).map { .kern($0) }
            case "ability": payload = Ability(rawValue: p.id).map { .ability($0) }
            case "equipment": payload = EquipmentCatalog.find(p.id).map { .equipment($0) }
            case "siegel": payload = SiegelKatalog.find(p.id).map { .siegel($0) }
            case "klinge": payload = KlingenKatalog.find(p.id).map { .klinge($0) }
            default: payload = nil
            }
            guard let payload else { continue }
            pickups.append(PickupInstance(key: key, payload: payload,
                                          position: Vec2.entity(p.x, p.y),
                                          bobPhase: Double(pickups.count) * 0.7))
        }

        for (i, l) in room.data.lore.enumerated() {
            lore.append(LoreInstance(key: "\(room.id)/lore\(i)",
                                     position: Vec2.entity(l.x, l.y),
                                     text: l.text))
        }

        for b in room.data.benches {
            benches.append(BenchInstance(position: Vec2.entity(b.x, b.y)))
        }

        if let b = room.data.boss, b.type == "kantor" {
            let arena = Rect(x: Double(b.arena.x) * tileSize,
                             y: Double(b.arena.y) * tileSize,
                             width: Double(b.arena.w) * tileSize,
                             height: Double(b.arena.h) * tileSize)
            if !save.collected.contains("\(room.id)/boss") {
                boss = Boss(position: Vec2.entity(b.x, b.y), arena: arena,
                            art: Boss.Art(rawValue: b.type) ?? .kantor)
            }
        }

        player.placeAt(Vec2.entity(spawn.x, spawn.y), facing: Double(spawn.facing))
    }

    /// Setzt eine Kreatur zur Laufzeit in den Raum (Boss-Rufe, Tests).
    func insert(enemy: Enemy) {
        enemies.append(enemy)
    }

    private func takeID() -> Int {
        defer { nextEntityID += 1 }
        return nextEntityID
    }

    // MARK: - Hauptschleife

    public func update(dt: Double, input: PlayerInput) -> [GameEvent] {
        var events: [GameEvent] = []
        elapsed += dt
        save.playTime += dt
        transitionCooldown = max(0, transitionCooldown - dt)

        handleKernSwitch(input: input, events: &events)

        if player.isDead {
            deathTimer += dt
            player.update(dt: dt, input: .neutral, room: room, events: &events)
            if deathTimer > 2.4 {
                respawnAtBench(events: &events)
            }
            updateCamera(dt: dt)
            return events
        }

        if player.isResting {
            restTimer += dt
            if input.cycleEquipment != 0 {
                cycleEquipment(by: input.cycleEquipment, events: &events)
            }
            if let index = input.toggleSiegel {
                let owned = save.progression.ownedSiegel
                if index >= 0, index < owned.count, toggleSiegel(owned[index].id) {
                    events.append(.sound(.pickup))
                    events.append(.siegelWorn(owned[index],
                                              angelegt: save.progression.siegelWorn
                                                  .contains(owned[index].id)))
                }
            }
            if input.interactPressed && restTimer > 0.35 {
                player.endRest()
                restTimer = 0
            }
            updateCamera(dt: dt)
            updateMusic(dt: dt, events: &events)
            return events
        }

        player.update(dt: dt, input: input, room: room, events: &events)
        updateBruch(dt: dt, events: &events)
        applyPlayerActions(events: &events)

        updateEnemies(dt: dt, events: &events)
        updateBoss(dt: dt, events: &events)
        updateProjectiles(dt: dt, events: &events)
        resolveMeleeHits(events: &events)
        resolveContactDamage(events: &events)
        resolveHazards(events: &events)
        resolvePickups(events: &events)
        updatePrompt(input: input, events: &events)
        checkDoors(events: &events)
        updateCamera(dt: dt)
        updateMusic(dt: dt, events: &events)

        return events
    }

    // MARK: - Wirkung der Spieleraktionen
    //
    // Der Spieler meldet nur seine Absicht. Was daraus in der Welt wird -
    // fliegende Toene, eine Druckwelle - entscheidet die Simulation.

    private func applyPlayerActions(events: inout [GameEvent]) {
        var nachtrag: [GameEvent] = []
        for event in events {
            switch event {
            case .fireProjectiles(let kern, let origin, let direction):
                projectiles.append(contentsOf:
                    Projectile.volley(profile: player.stats.ranged,
                                      kern: kern,
                                      origin: origin, direction: direction))
            case .slamShockwave(let origin, let radius):
                applySlam(origin: origin, radius: radius, events: &nachtrag)
            default:
                break
            }
        }
        events.append(contentsOf: nachtrag)
    }

    /// Der Basston wirft alles um, was in Reichweite steht.
    private func applySlam(origin: Vec2, radius: Double, events: inout [GameEvent]) {
        let area = Rect(center: origin, radius: radius)
        var getroffen = 0
        for enemy in enemies where enemy.alive && enemy.rect.intersects(area) {
            let away = Vec2(sign(enemy.center.x - origin.x), -0.6).normalized
            enemy.takeDamage(player.stats.slamDamage, knockback: away * 260, events: &events)
            if !enemy.alive { player.gainResonance(enemy.kind.resonanceReward) }
            getroffen += 1
        }
        if let boss, boss.alive, boss.rect.intersects(area) {
            boss.takeDamage(player.stats.slamDamage, events: &events)
            getroffen += 1
        }
        if getroffen > 0 { player.registerMeleeHit(count: getroffen) }
    }

    // MARK: - Instrumente

    private func handleKernSwitch(input: PlayerInput, events: inout [GameEvent]) {
        let owned = save.progression.orderedKerne
        guard owned.count > 1 else { return }

        if let wanted = input.selectKern, save.progression.has(wanted),
           wanted != player.kern {
            player.equip(wanted)
            save.kern = wanted
            events.append(.kernSwitched(wanted))
            return
        }

        guard input.cycleKern != 0,
              let current = owned.firstIndex(of: player.kern) else { return }
        let count = owned.count
        let next = owned[((current + input.cycleKern) % count + count) % count]
        player.equip(next)
        save.kern = next
        events.append(.kernSwitched(next))
    }

    // MARK: - Kreaturen

    private func updateEnemies(dt: Double, events: inout [GameEvent]) {
        var spawned: [Projectile] = []
        for enemy in enemies {
            enemy.update(dt: dt, room: room, player: player, events: &events) { spawned.append($0) }
        }
        projectiles.append(contentsOf: spawned)
        enemies.removeAll { !$0.alive }
    }

    private func updateBoss(dt: Double, events: inout [GameEvent]) {
        guard let boss, boss.alive || boss.action == .defeated else { return }
        var spawned: [Projectile] = []
        boss.update(dt: dt, room: room, player: player, events: &events) { spawned.append($0) }
        projectiles.append(contentsOf: spawned)

        for (kind, position) in boss.drainSummons() {
            enemies.append(Enemy(id: takeID(), kind: kind, position: position, patrolTiles: 3))
        }

        // Der Bruch. Wenn der Kantor in den letzten Satz geht, haelt sie es
        // nicht mehr aus - das ist der Punkt, an dem sie aus sich
        // herausfaehrt. Ein festes Ereignis, kein Fundstueck.
        if boss.phase == .toccata, !save.progression.gebrochen {
            brich(events: &events)
        }

        if !boss.alive && !isComplete {
            isComplete = true
            save.collected.insert("\(room.id)/boss")
            projectiles.removeAll { $0.owner == .enemy }
            events.append(.gameCompleted)
            events.append(.musicChanged(track: "aufloesung", intensity: 0))
        }
    }

    // MARK: - Geschosse

    private func updateProjectiles(dt: Double, events: inout [GameEvent]) {
        for i in projectiles.indices {
            guard projectiles[i].alive else { continue }
            let hitWall = projectiles[i].update(dt: dt, room: room)
            if hitWall {
                events.append(.effect(projectiles[i].owner == .player ? .burstGlow : .burstRot,
                                      projectiles[i].position, .zero))
            }
        }

        // Spielergeschosse gegen Kreaturen und Boss.
        for i in projectiles.indices where projectiles[i].alive && projectiles[i].owner == .player {
            for enemy in enemies where enemy.alive && !projectiles[i].hitIDs.contains(enemy.id) {
                guard projectiles[i].rect.intersects(enemy.rect) else { continue }
                let knock = projectiles[i].velocity.normalized * 90
                enemy.takeDamage(projectiles[i].damage, knockback: knock, events: &events)
                if !enemy.alive { player.gainResonance(enemy.kind.resonanceReward) }
                if projectiles[i].consumeHit(entityID: enemy.id) { break }
            }
            if let boss, boss.alive, projectiles[i].alive,
               !projectiles[i].hitIDs.contains(-1),
               projectiles[i].rect.intersects(boss.rect) {
                boss.takeDamage(projectiles[i].damage, events: &events)
                _ = projectiles[i].consumeHit(entityID: -1)
            }
        }

        // Gegnergeschosse gegen den Spieler.
        for i in projectiles.indices where projectiles[i].alive && projectiles[i].owner == .enemy {
            guard projectiles[i].rect.intersects(player.rect) else { continue }
            if player.takeDamage(projectiles[i].damage, from: projectiles[i].position, events: &events) {
                projectiles[i].alive = false
            }
        }

        projectiles.removeAll { !$0.alive }
    }

    // MARK: - Nahkampf

    private func resolveMeleeHits(events: inout [GameEvent]) {
        guard let hitbox = player.activeMeleeHitbox() else { return }
        let profile = player.stats.melee
        let downward = player.aimY > 0.5 && !player.onGround
        var hits = 0

        for enemy in enemies where enemy.alive && hitbox.intersects(enemy.rect) {
            let away = Vec2(sign(enemy.center.x - player.position.x), -0.35).normalized
            let knock = away * profile.knockback
            enemy.takeDamage(profile.damage, knockback: knock, events: &events)
            if !enemy.alive { player.gainResonance(enemy.kind.resonanceReward) }
            hits += 1
        }

        if let boss, boss.alive, hitbox.intersects(boss.rect) {
            boss.takeDamage(profile.damage, events: &events)
            hits += 1
        }

        // Auch Dornen tragen den Abpraller - der Spieler kann sie als
        // Sprungbrett nutzen, statt nur an ihnen zu sterben.
        if downward && hits == 0 && room.overlapsHazard(hitbox) {
            hits = 1
        }

        if hits > 0 {
            player.registerMeleeHit(count: hits)
            events.append(.shake(profile.shape == .radial ? 4 : 2))
            events.append(.effect(.klingenschlag, hitbox.center, .zero))
            if downward { player.pogo() }
        }
    }

    // MARK: - Schaden am Spieler

    private func resolveContactDamage(events: inout [GameEvent]) {
        let body = player.rect
        for enemy in enemies where enemy.alive && enemy.rect.intersects(body) {
            player.takeDamage(enemy.kind.contactDamage, from: enemy.center, events: &events)
            break
        }
        if let boss, boss.alive, boss.action != .entrance, boss.rect.intersects(body) {
            // Der Kantor nimmt anderthalb Kristalle - drei Haelften.
            player.takeDamage(3, from: boss.center, events: &events)
        }
    }

    private func resolveHazards(events: inout [GameEvent]) {
        // Dornen: der Spieler wird zurueck auf sicheren Boden gesetzt, statt
        // in der Gefahrenzone festzuhaengen.
        if room.overlapsHazard(player.rect.inset(by: 2)) {
            let before = player.health
            player.takeDamage(Tuning.spikeDamage, from: player.position, events: &events)
            if player.health < before && !player.isDead {
                nudgeOutOfHazard()
            }
        }

        if let boss {
            for hazard in boss.lethalHazards where hazard.rect.intersects(player.rect) {
                player.takeDamage(hazard.damage, from: hazard.rect.center, events: &events)
                break
            }
        }
    }

    /// Sucht die naechste sichere Kachel und setzt die Figur dorthin.
    private func nudgeOutOfHazard() {
        let start = player.position
        for radius in stride(from: tileSize, through: tileSize * 6, by: tileSize) {
            for angle in stride(from: 0.0, to: .pi * 2, by: .pi / 6) {
                let candidate = Vec2(start.x + cos(angle) * radius,
                                     start.y + sin(angle) * radius)
                let probe = Rect(footAt: candidate, width: Tuning.playerWidth,
                                 height: Tuning.playerHeight)
                guard !room.overlapsSolid(probe), !room.overlapsHazard(probe) else { continue }
                guard let floor = room.floorBelow(candidate, maxTiles: 6) else { continue }
                let landing = Vec2(candidate.x, floor)
                let landed = Rect(footAt: landing, width: Tuning.playerWidth,
                                  height: Tuning.playerHeight)
                guard !room.overlapsHazard(landed), !room.overlapsSolid(landed.inset(by: 1)) else { continue }
                player.position = landing
                return
            }
        }
    }

    // MARK: - Fundstuecke

    private func resolvePickups(events: inout [GameEvent]) {
        let body = player.rect.inset(by: -6)
        for (index, pickup) in pickups.enumerated().reversed() {
            guard body.contains(pickup.position) || body.intersects(Rect(center: pickup.position, radius: 10))
            else { continue }
            pickups.remove(at: index)
            save.collected.insert(pickup.key)

            switch pickup.payload {
            case .kern(let kern):
                save.progression.kerne.insert(kern)
                player.sync(progression: save.progression)
                player.equip(kern)
                save.kern = kern
                events.append(.sound(.pickup))
                events.append(.kernPicked(kern))
            case .ability(let ability):
                save.progression.abilities.insert(ability)
                player.sync(progression: save.progression)
                events.append(.sound(.abilityGained))
                events.append(.abilityPicked(ability))
                events.append(.shake(6))
            case .equipment(let equipment):
                save.progression.equipmentOwned.insert(equipment.id)
                events.append(.sound(.abilityGained))
                events.append(.equipmentFound(equipment))
            case .siegel(let siegel):
                save.progression.siegelOwned.insert(siegel.id)
                events.append(.sound(.abilityGained))
                events.append(.siegelFound(siegel))
            case .klinge(let klinge):
                save.progression.klingenOwned.insert(klinge.id)
                events.append(.sound(.pickup))
                events.append(.klingeFound(klinge))
            }
            events.append(.effect(.mote, pickup.position, .zero))
        }
    }

    // MARK: - Ansprechbare Dinge

    private func updatePrompt(input: PlayerInput, events: inout [GameEvent]) {
        prompt = .none

        if let bench = benches.first(where: { $0.position.distance(to: player.position) < 26 }) {
            prompt = .bench
            if input.interactPressed && player.onGround {
                player.placeAt(Vec2(bench.position.x, bench.position.y), facing: player.facing)
                player.beginRest()
                player.restore()
                restTimer = 0
                save.roomID = room.id
                save.spawnName = benchSpawnName()
                events.append(.sound(.bench))
                events.append(.benchRested)
            }
            return
        }

        if let entry = lore.first(where: { $0.position.distance(to: player.position) < 24 }) {
            prompt = .lore(entry.text)
            if input.interactPressed && !save.progression.readLore.contains(entry.key) {
                save.progression.readLore.insert(entry.key)
                events.append(.loreRead(text: entry.text))
            }
            return
        }

        // Hinweis an gesperrten Tueren, damit niemand ratlos davorsteht.
        for door in room.data.doors {
            guard let requirement = door.requires,
                  let ability = Ability(rawValue: requirement),
                  !save.progression.has(ability) else { continue }
            let near = room.doorRect(door).inset(by: -20)
            if near.intersects(player.rect) {
                prompt = .gate(ability)
                let key = "\(room.id)/\(door.id)"
                if !shownGateHints.contains(key) {
                    shownGateHints.insert(key)
                    events.append(.gateHint(ability))
                }
                return
            }
        }
    }

    /// Der Name des Spawnpunkts, an dem nach dem Tod neu begonnen wird.
    /// Bevorzugt eine echte Tuer, sonst der Raumstart.
    private func benchSpawnName() -> String {
        if room.spawn(named: "bench") != nil { return "bench" }
        if room.spawn(named: catalog.index.startSpawn) != nil,
           room.id == catalog.index.startRoom {
            return catalog.index.startSpawn
        }
        return room.data.spawns.keys.sorted().first ?? catalog.index.startSpawn
    }

    // MARK: - Raumwechsel

    private func checkDoors(events: inout [GameEvent]) {
        guard transitionCooldown <= 0 else { return }
        let body = player.rect
        for door in room.data.doors where room.doorRect(door).intersects(body) {
            do {
                try enter(door: door, events: &events)
            } catch {
                // Ein fehlender Raum darf das Spiel nicht anhalten.
                events.append(.sound(.outOfResonance))
            }
            return
        }
    }

    private func enter(door: RoomData.Door, events: inout [GameEvent]) throws {
        let from = room.id
        let target = try catalog.room(door.target)
        applyBrokenWalls(to: target)
        let spawn = target.spawn(named: door.targetDoor)
            ?? RoomData.SpawnPoint(x: 4, y: 4, facing: 1)
        room = target
        populate(room: target, spawn: spawn)
        transitionCooldown = 0.35
        cameraTarget = player.position
        events.append(.sound(.door))
        events.append(.roomChanged(from: from, to: target.id, door: door.id))
    }

    // MARK: - Tod und Rast

    private func respawnAtBench(events: inout [GameEvent]) {
        deathTimer = 0
        do {
            let target = try catalog.loadFresh(save.roomID)
            applyBrokenWalls(to: target)
            let spawn = target.spawn(named: save.spawnName)
                ?? target.data.spawns.values.first
                ?? RoomData.SpawnPoint(x: 4, y: 4, facing: 1)
            room = target
            populate(room: target, spawn: spawn)
            player.sync(progression: save.progression)
            player.restore()
            player.equip(save.kern)
            events.append(.roomChanged(from: room.id, to: target.id, door: "respawn"))
        } catch {
            player.restore()
        }
    }

    // MARK: - Kamera und Musik

    private func updateCamera(dt: Double) {
        let lookAhead = player.facing * Tuning.cameraLookAhead
        let wanted = Vec2(player.position.x + lookAhead,
                          player.position.y - Tuning.playerHeight * 0.5)
        cameraTarget.x = damp(cameraTarget.x, wanted.x, rate: Tuning.cameraSmoothing, dt: dt)
        if abs(cameraTarget.y - wanted.y) > Tuning.cameraVerticalDeadzone || !player.onGround {
            cameraTarget.y = damp(cameraTarget.y, wanted.y, rate: Tuning.cameraSmoothing * 0.8, dt: dt)
        }
    }

    private func updateMusic(dt: Double, events: inout [GameEvent]) {
        let track = isComplete ? "aufloesung" : (boss != nil && boss!.alive ? "boss" : room.data.music)
        if track != musicTrack {
            musicTrack = track
            events.append(.musicChanged(track: track, intensity: musicIntensity))
        }

        // Die Musik verdichtet sich mit der Gefahr, statt lauter zu werden.
        if let boss, boss.alive {
            intensityTarget = [0.35, 0.7, 1.0][max(0, boss.phase.rawValue - 1)]
        } else if isComplete {
            intensityTarget = 0
        } else {
            let threats = enemies.filter { $0.alive && $0.center.distance(to: player.chest) < 180 }
            let hurt = 1 - Double(player.health) / Double(max(1, player.maxHealth))
            intensityTarget = clamp(Double(threats.count) * 0.22 + hurt * 0.3, 0, 1)
        }

        let before = musicIntensity
        musicIntensity = damp(musicIntensity, intensityTarget, rate: 0.03, dt: dt)
        if abs(musicIntensity - before) > 0.02 {
            events.append(.intensityChanged(musicIntensity))
        }
    }

    // MARK: - Fassungen

    /// Schaltet an der Stimmgabel durch die gefundenen Fassungen.
    private func cycleEquipment(by step: Int, events: inout [GameEvent]) {
        let owned = save.progression.ownedEquipment
        guard owned.count > 1,
              let current = owned.firstIndex(where: { $0.id == save.progression.equipmentWorn })
        else { return }
        let count = owned.count
        let next = owned[((current + step) % count + count) % count]
        guard next.id != save.progression.equipmentWorn, wear(next.id) else { return }
        events.append(.sound(.pickup))
        events.append(.equipmentWorn(next))
    }

    // MARK: - Der Bruch

    /// Loest den Bruch aus. Ein festes Ereignis der Geschichte, keine Wahl -
    /// und es gibt kein Zurueck.
    @discardableResult
    public func brich(events: inout [GameEvent]) -> Bool {
        guard !save.progression.gebrochen else { return false }
        save.progression.gebrochen = true
        player.sync(progression: save.progression)
        // Sie faehrt aus der Fassung heraus: der Zusammenhalt aendert sich,
        // also wird sie voll - was danach abgeht, geht von hier ab.
        player.restore()
        events.append(.sound(.bossPhase))
        events.append(.shake(14))
        events.append(.effect(.burstGlow, player.chest, .zero))
        events.append(.bruch)
        return true
    }

    /// Ohne Gefaess zerstreut sie sich. Der Bruch ist ein Wettlauf.
    private func updateBruch(dt: Double, events: inout [GameEvent]) {
        guard save.progression.gebrochen, !player.isDead, !player.isResting else { return }
        zerfall += Bruch.lebensverlust * dt
        guard zerfall >= 1 else { return }
        let haelften = Int(zerfall)
        zerfall -= Double(haelften)
        // Er soll draengen, nicht toeten: der letzte halbe Kristall bleibt.
        player.drain(haelften, floor: Bruch.untergrenze, events: &events)
    }

    /// Legt ein Siegel an oder ab. Nur an der Stimmgabel - ein Siegel sitzt
    /// nicht in der Tasche, es steckt in ihr.
    @discardableResult
    public func toggleSiegel(_ siegelID: String) -> Bool {
        guard player.isResting || player.isDead else { return false }
        let vorher = save.progression.siegelWorn
        if save.progression.siegelWorn.contains(siegelID) {
            save.progression.ablegen(siegelID)
        } else {
            save.progression.anlegen(siegelID)
        }
        guard save.progression.siegelWorn != vorher else { return false }
        player.sync(progression: save.progression)
        player.restore()
        return true
    }

    // MARK: - Speichern

    /// Legt eine gefundene Fassung an. Nur an der Stimmgabel - sich mitten
    /// im Kampf neu zu fassen waere kein Kleiderwechsel, sondern ein Umbau.
    /// Nach dem Bruch gar nicht mehr: es gibt keine Fassung, in die sie
    /// zurueckkoennte.
    @discardableResult
    public func wear(_ equipmentID: String) -> Bool {
        guard !save.progression.gebrochen,
              save.progression.equipmentOwned.contains(equipmentID),
              EquipmentCatalog.find(equipmentID) != nil,
              player.isResting || player.isDead
        else { return false }
        save.progression.equipmentWorn = equipmentID
        player.sync(progression: save.progression)
        player.restore()
        return true
    }

    /// Wechselt die gefuehrte Klinge. Sie aendert nur das Aussehen des
    /// Schlags, also darf das jederzeit passieren.
    @discardableResult
    public func fuehre(_ klingeID: String) -> Bool {
        guard save.progression.klingenOwned.contains(klingeID),
              KlingenKatalog.find(klingeID) != nil else { return false }
        save.progression.klingeWorn = klingeID
        player.sync(progression: save.progression)
        return true
    }

    /// Erzeugt den aktuellen Speicherstand (Aufruf an der Stimmgabel).
    public func snapshotSave() -> SaveState {
        var out = save
        out.progression = save.progression
        out.kern = player.kern
        var walls: [String: [Int]] = save.brokenWalls
        var flat: [Int] = []
        for ty in 0..<room.height {
            for tx in 0..<room.width where room.data.tiles[ty].count > tx {
                let original = Tile(character: Array(room.data.tiles[ty])[tx])
                if original == .dissoWall && room.tile(tx, ty) == .air {
                    flat.append(tx)
                    flat.append(ty)
                }
            }
        }
        if !flat.isEmpty { walls[room.id] = flat }
        out.brokenWalls = walls
        save = out
        return out
    }
}
