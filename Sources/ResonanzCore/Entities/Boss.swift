import Foundation

/// Eine angekuendigte Gefahrenzone - erst leuchtet sie, dann trifft sie.
/// Der Spieler soll immer sehen koennen, was gleich passiert.
public struct BossHazard: Sendable {
    public var rect: Rect
    /// Vorwarnzeit, in der die Zone nur leuchtet.
    public var warmup: Double
    /// Wie lange sie danach trifft.
    public var active: Double
    public var damage: Int
    public var age: Double = 0
    public var kind: String

    public var isWarning: Bool { age < warmup }
    public var isLethal: Bool { age >= warmup && age < warmup + active }
    public var isFinished: Bool { age >= warmup + active }
    /// 0..1 waehrend der Vorwarnung - fuer das Aufleuchten.
    public var warningProgress: Double { warmup <= 0 ? 1 : clamp(age / warmup, 0, 1) }

    /// `damage` in halben Kristallen: der Kantor nimmt anderthalb.
    public init(rect: Rect, warmup: Double, active: Double, damage: Int = 3, kind: String) {
        self.rect = rect
        self.warmup = warmup
        self.active = active
        self.damage = damage
        self.kind = kind
    }
}

/// Der Verstimmte Kantor.
///
/// Er gab einst den Takt. Niemand hat ihm gesagt, wann er aufhoeren soll -
/// also dirigiert er weiter, gegen eine Welt, die laengst nicht mehr mitspielt.
public final class Boss {
    public enum Phase: Int, Sendable {
        case takt = 1      // Taktschlag: Akkorde und Stossweillen
        case fuge = 2      // Fuge: mehrere Stimmen zugleich
        case toccata = 3   // Toccata: Orgelpfeifen brechen aus dem Boden
    }

    public enum Action: String, Sendable {
        case entrance, hover, chord, sweep, pipes, summon, stagger, defeated
    }

    /// Welcher Boss. Beide benutzen denselben Ablauf - der Unterschied
    /// liegt darin, wie lange sie ausholen und was sie koennen.
    public enum Art: String, Sendable {
        /// Der grosse Auftakt: erster Boss, Tutorial. Sieht furchtbar aus,
        /// kann genau eine Sache, und sagt sie viel zu lange vorher an.
        case auftakt
        /// Der verstimmte Kantor: Endgegner.
        case kantor

        var health: Int { self == .auftakt ? 28 : 72 }
        /// Wie lange er schwebt, bevor er zuschlaegt. Beim Auftakt ist das
        /// der ganze Witz: man hat Zeit, den Schlag zu lesen.
        var ansage: Double { self == .auftakt ? 2.1 : 1.0 }
        var kannPfeifen: Bool { self == .kantor }
        var kannRufen: Bool { self == .kantor }
    }

    public let art: Art
    public var maxHealth: Int { art.health }
    public private(set) var health: Int
    public private(set) var phase: Phase = .takt
    public private(set) var action: Action = .entrance
    public private(set) var actionTime: Double = 0
    public private(set) var alive = true
    public private(set) var hitFlash: Double = 0

    public var position: Vec2
    public var velocity: Vec2 = .zero
    public var facing: Double = -1

    /// Angekuendigte Gefahrenzonen.
    public private(set) var hazards: [BossHazard] = []
    /// Kreaturen, die er in Phase 2 herbeiruft.
    public private(set) var pendingSummons: [(EnemyKind, Vec2)] = []

    public let arena: Rect
    private let floorY: Double
    private var rng = Rng(seed: 0xC0FFEE)
    private var targetX: Double
    private var attacksSinceMove = 0

    public init(position: Vec2, arena: Rect, art: Art = .kantor) {
        self.art = art
        self.position = position
        self.arena = arena
        self.floorY = position.y
        self.targetX = position.x
        self.health = art.health
    }

    public var rect: Rect {
        Rect(footAt: position, width: 34, height: 46)
    }

    public var center: Vec2 { rect.center }

    public var healthFraction: Double {
        Double(health) / Double(maxHealth)
    }

    // MARK: - Ablauf

    public func update(dt: Double, room: Room, player: Player, events: inout [GameEvent],
                       spawnProjectile: (Projectile) -> Void) {
        guard alive else { return }
        actionTime += dt
        hitFlash = max(0, hitFlash - dt)

        for i in hazards.indices { hazards[i].age += dt }
        hazards.removeAll { $0.isFinished }

        facing = player.position.x < position.x ? -1 : 1

        switch action {
        case .entrance:
            if actionTime > 2.0 { begin(.hover) }
        case .hover:
            drift(dt: dt)
            if actionTime > hoverDuration { chooseAttack(player: player, events: &events) }
        case .chord:
            runChord(player: player, spawnProjectile: spawnProjectile, events: &events)
        case .sweep:
            runSweep(spawnProjectile: spawnProjectile, events: &events)
        case .pipes:
            runPipes(player: player, events: &events)
        case .summon:
            runSummon(events: &events)
        case .stagger:
            drift(dt: dt * 0.3)
            if actionTime > 1.1 { begin(.hover) }
        case .defeated:
            velocity = .zero
        }

        position.x = clamp(position.x, arena.minX + 24, arena.maxX - 24)
    }

    private var hoverDuration: Double {
        // Die Ansage ist beim Auftakt der ganze Kampf: er holt lange aus,
        // damit man lernt, dass hier jeder Schlag vorher zu sehen ist.
        let basis: Double
        switch phase {
        case .takt: basis = 1.5
        case .fuge: basis = 1.05
        case .toccata: basis = 0.7
        }
        return basis * art.ansage
    }

    private func begin(_ next: Action) {
        action = next
        actionTime = 0
        firedThisAction = 0
    }

    private var firedThisAction = 0

    private func drift(dt: Double) {
        // Schwebt zum Zielpunkt und wippt dabei im Takt.
        let dx = targetX - position.x
        velocity.x = damp(velocity.x, clamp(dx * 2.2, -95, 95), rate: 0.08, dt: dt)
        position.x += velocity.x * dt
        position.y = floorY + sin(actionTime * 2.4) * 3
    }

    private func chooseAttack(player: Player, events: inout [GameEvent]) {
        attacksSinceMove += 1
        // Gelegentlich die Seite wechseln, damit der Kampf in Bewegung bleibt.
        if attacksSinceMove >= 2 {
            attacksSinceMove = 0
            targetX = rng.chance(0.5) ? arena.minX + 40 : arena.maxX - 40
        }

        var options: [Action] = [.chord, .sweep]
        // Der Auftakt kann genau diese zwei Dinge. Keine Pfeifen, keine
        // gerufenen Kreaturen - er ist eine Uebung, kein Kampf.
        if phase != .takt, art.kannPfeifen { options.append(.pipes) }
        if phase == .fuge, art.kannRufen { options.append(.summon) }
        if phase == .toccata, art.kannPfeifen {
            options.append(contentsOf: [.pipes, .sweep])
        }

        let pick = options[rng.int(0, options.count - 1)]
        begin(pick)
        if pick == .pipes || pick == .summon {
            events.append(.sound(.bossRoar))
        }
    }

    // MARK: - Angriffe

    /// Akkord: ein Faecher schiefer Toene in Richtung Spieler.
    private func runChord(player: Player, spawnProjectile: (Projectile) -> Void,
                          events: inout [GameEvent]) {
        let shots = phase == .takt ? 1 : (phase == .fuge ? 2 : 3)
        let interval = 0.34
        let expected = Int(actionTime / interval)
        while firedThisAction < min(expected, shots) {
            firedThisAction += 1
            let toPlayer = player.chest - center
            let base = atan2(toPlayer.y, toPlayer.x)
            // Ein Dreiklang - nur eben verstimmt.
            for offset in [-0.22, 0.0, 0.22] {
                let angle = base + offset
                spawnProjectile(.dissonantNote(origin: center,
                                               direction: Vec2(cos(angle), sin(angle)),
                                               speed: phase == .toccata ? 190 : 155))
            }
            events.append(.effect(.ringKlein, center, .zero))
        }
        if actionTime > interval * Double(shots) + 0.3 { begin(.hover) }
    }

    /// Stossweille: ein voller Kreis aus Toenen.
    private func runSweep(spawnProjectile: (Projectile) -> Void, events: inout [GameEvent]) {
        if firedThisAction == 0 && actionTime > 0.45 {
            firedThisAction = 1
            let count = phase == .takt ? 8 : (phase == .fuge ? 10 : 14)
            let twist = rng.range(0, .pi / 4)
            for i in 0..<count {
                let angle = Double(i) / Double(count) * .pi * 2 + twist
                spawnProjectile(.dissonantNote(origin: center,
                                               direction: Vec2(cos(angle), sin(angle)),
                                               speed: 128))
            }
            events.append(.sound(.bossPhase))
            events.append(.effect(.ringGross, center, .zero))
            events.append(.shake(4))
        }
        if actionTime > 1.0 { begin(.hover) }
    }

    /// Orgelpfeifen brechen aus dem Boden - vorher leuchtet ihr Umriss auf.
    private func runPipes(player: Player, events: inout [GameEvent]) {
        if firedThisAction == 0 && actionTime > 0.25 {
            firedThisAction = 1
            let count = phase == .toccata ? 5 : 3
            // Eine Pfeife zielt auf den Spieler, die uebrigen verteilen sich -
            // ausweichen bleibt dadurch immer moeglich.
            var columns: [Double] = [player.position.x]
            for _ in 1..<count {
                columns.append(rng.range(arena.minX + 20, arena.maxX - 20))
            }
            for x in columns {
                let width = 20.0
                let height = 70.0
                hazards.append(BossHazard(
                    rect: Rect(x: x - width / 2, y: arena.maxY - height,
                               width: width, height: height),
                    warmup: phase == .toccata ? 0.55 : 0.75,
                    active: 0.42,
                    kind: "pipe"))
            }
            events.append(.shake(3))
        }
        if actionTime > 1.5 { begin(.hover) }
    }

    /// Er ruft, was von seinem Chor uebrig ist.
    private func runSummon(events: inout [GameEvent]) {
        if firedThisAction == 0 && actionTime > 0.5 {
            firedThisAction = 1
            for i in 0..<2 {
                let x = position.x + (i == 0 ? -46 : 46)
                pendingSummons.append((.klangmotte, Vec2(clamp(x, arena.minX + 16, arena.maxX - 16),
                                                         arena.minY + 46)))
            }
            events.append(.effect(.ringMittel, center, .zero))
        }
        if actionTime > 1.2 { begin(.hover) }
    }

    public func drainSummons() -> [(EnemyKind, Vec2)] {
        defer { pendingSummons.removeAll() }
        return pendingSummons
    }

    // MARK: - Schaden

    @discardableResult
    public func takeDamage(_ amount: Int, events: inout [GameEvent]) -> Bool {
        guard alive, action != .entrance else { return false }
        health -= amount
        hitFlash = 0.1
        events.append(.sound(.hit(strong: amount >= 3)))
        events.append(.effect(.burstGlow, center, .zero))

        let fraction = healthFraction
        if phase == .takt && fraction <= 0.66 {
            phase = .fuge
            begin(.stagger)
            events.append(.bossPhaseChanged(2))
            events.append(.sound(.bossPhase))
            events.append(.shake(7))
        } else if phase == .fuge && fraction <= 0.33 {
            phase = .toccata
            begin(.stagger)
            events.append(.bossPhaseChanged(3))
            events.append(.sound(.bossPhase))
            events.append(.shake(9))
        }

        if health <= 0 {
            health = 0
            alive = false
            begin(.defeated)
            hazards.removeAll()
            events.append(.sound(.bossDeath))
            events.append(.shake(12))
            events.append(.bossDefeated)
            return true
        }
        return false
    }

    /// Gefahrenzonen, die gerade wirklich treffen.
    public var lethalHazards: [BossHazard] {
        hazards.filter(\.isLethal)
    }
}
