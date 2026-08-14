import Foundation

/// Die Bewohner der verstimmten Welt. Keiner von ihnen ist boese - sie sind
/// nur seit langem falsch gestimmt.
public enum EnemyKind: String, Sendable, CaseIterable {
    /// Die erste Kreatur ueberhaupt: huschendes Tierchen mit Gabelohren.
    case gabelmaus
    /// Taumelnder Falter aus verklungenen Toenen.
    case klangmotte
    /// Schwerer Waechter, der Klang schluckt.
    case stilleschreiter
    /// Festgewachsen; spuckt schiefe Toene.
    case dissonanzknospe
    /// Springender Kristallsplitter, prallt von allem ab.
    case echoscherbe
    /// Kathedrale: haengt unter der Decke und laesst sich fallen, wenn
    /// jemand darunter durchgeht.
    case chorschatten
    /// Grotten: treibt durch den Hohlraum und pulst im Takt des Echos.
    case hallqualle
    /// Bruecke: hockt auf dem Gelaender und stoesst im Bogen herab.
    case steinfink

    public var maxHealth: Int {
        switch self {
        case .gabelmaus: return 2
        case .klangmotte: return 3
        case .stilleschreiter: return 8
        case .dissonanzknospe: return 4
        case .echoscherbe: return 4
        case .chorschatten: return 5
        case .hallqualle: return 3
        case .steinfink: return 6
        }
    }

    /// Schaden an der Figur, in halben Kristallen. Ein voller Kristall
    /// sind zwei - der Stilleschreiter nimmt anderthalb.
    ///
    /// Die Gabelmaus nimmt einen halben. Das ist der einzige Wert im Spiel,
    /// der kleiner als ein Kristall ist, und er ist Absicht: der allererste
    /// Gegner soll wehtun, ohne zu bestrafen.
    public var contactDamage: Int {
        switch self {
        case .gabelmaus: return 1
        case .klangmotte: return 2
        case .stilleschreiter: return 3
        case .dissonanzknospe: return 2
        case .echoscherbe: return 2
        case .chorschatten: return 3
        case .hallqualle: return 2
        case .steinfink: return 3
        }
    }

    public var size: (width: Double, height: Double) {
        switch self {
        case .gabelmaus: return (11, 9)
        case .klangmotte: return (12, 10)
        case .stilleschreiter: return (18, 18)
        case .dissonanzknospe: return (12, 16)
        case .echoscherbe: return (11, 11)
        case .chorschatten: return (14, 20)
        case .hallqualle: return (15, 14)
        case .steinfink: return (16, 12)
        }
    }

    /// Faellt die Kreatur, oder schwebt sie?
    public var isAirborne: Bool {
        self == .klangmotte || self == .echoscherbe || self == .hallqualle
    }

    /// Bleibt sie stehen, wo sie steht?
    public var isRooted: Bool {
        self == .dissonanzknospe
    }

    public var resonanceReward: Double {
        switch self {
        case .stilleschreiter: return 16
        case .gabelmaus: return Tuning.resonancePerKill * 0.6
        default: return Tuning.resonancePerKill
        }
    }

    /// Wie viele Stimmen sie zuruecklaesst.
    ///
    /// Was schwerer zu erlegen ist, laesst mehr zurueck - aber nicht
    /// proportional zum Leben. Sonst wird das Dorf zu einer Frage der
    /// Geduld: wer lange genug dieselbe Kreatur erschlaegt, kauft alles.
    /// Der Abstand zwischen der kleinsten und der groessten Beute ist
    /// darum knapp drei zu eins, nicht zehn zu eins.
    public var stimmenReward: Int {
        switch self {
        case .gabelmaus: return 2
        case .klangmotte: return 3
        case .dissonanzknospe: return 3
        case .hallqualle: return 3
        case .echoscherbe: return 4
        case .chorschatten: return 4
        case .steinfink: return 5
        case .stilleschreiter: return 5
        }
    }

    /// Haengt sie an der Decke, statt auf dem Boden zu stehen?
    ///
    /// Das ist keine Spielerei mit der Schwerkraft, sondern die einzige
    /// Art, einen Gang gefaehrlich zu machen, der sonst nur breit ist:
    /// wer nach unten schaut, sieht nichts.
    public var haengtOben: Bool {
        self == .chorschatten
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
    /// Nur die Gabelmaus: huscht sie gerade, oder sitzt sie?
    private var huscht = false
    /// Nur der Chorschatten: haengt er noch?
    private var haengt = true

    /// Was die Kreatur gerade tut - fuer die Wahl des Bildes.
    ///
    /// Sie hatte bisher genau eine Bewegung, und damit sah man ihr nie
    /// an, was sie vorhat. Ein Gegner ohne Ansage ist keine Aufgabe,
    /// sondern eine Falle.
    public enum Haltung: String, Sendable {
        case ruhe, lauf, angriff
    }
    public private(set) var haltung: Haltung = .lauf

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
            case .gabelmaus: updateMaus(dt: dt, room: room, toPlayer: toPlayer)
            case .klangmotte: updateMoth(dt: dt, toPlayer: toPlayer, distance: distance)
            case .stilleschreiter: updateWalker(dt: dt, room: room, toPlayer: toPlayer, distance: distance)
            case .dissonanzknospe:
                updateBud(dt: dt, toPlayer: toPlayer, distance: distance, spawnProjectile: spawnProjectile)
            case .echoscherbe: updateShard(dt: dt)
            case .chorschatten:
                updateSchatten(dt: dt, room: room, toPlayer: toPlayer, distance: distance)
            case .hallqualle: updateQualle(dt: dt, toPlayer: toPlayer, distance: distance)
            case .steinfink: updateFink(dt: dt, room: room, toPlayer: toPlayer, distance: distance)
            }
        } else {
            velocity.x = approach(velocity.x, 0, 600 * dt)
        }

        applyPhysics(dt: dt, room: room)
    }

    /// Der Chorschatten haengt und faellt.
    ///
    /// Er hat genau zwei Zustaende, und der Uebergang zwischen ihnen ist
    /// die ganze Kreatur: solange er haengt, tut er nichts und bewegt
    /// sich nicht - er ist Teil der Decke. Kommt jemand darunter, laesst
    /// er los.
    ///
    /// Der Ausloeser ist bewusst eng: nur die Waagerechte zaehlt, nicht
    /// der Abstand. Wer ihn sieht, kann in aller Ruhe drumherum. Wer nach
    /// vorn schaut statt nach oben, bekommt ihn auf den Kopf. Das ist
    /// eine Falle, die man nach dem ersten Mal nie wieder auslaesst, und
    /// genau so soll sie sein.
    private func updateSchatten(dt: Double, room: Room, toPlayer: Vec2, distance: Double) {
        if haengt {
            velocity = .zero
            // Losgelassen wird, wenn jemand fast senkrecht darunter steht.
            if abs(toPlayer.x) < 14 && toPlayer.y > 0 && toPlayer.y < 150 {
                haengt = false
                attackTimer = 0.9
            }
            return
        }
        // Unten angekommen schleicht er auf die Figur zu - langsam, aber
        // er gibt nicht mehr auf.
        let unten = Vec2(position.x, position.y + 3)
        if room.tile(at: unten).isStandable {
            if attackTimer > 0 { return }
            facing = sign(toPlayer.x) == 0 ? facing : sign(toPlayer.x)
            velocity.x = approach(velocity.x, facing * 34, 260 * dt)
        }
    }

    /// Die Hallqualle treibt und pulst.
    ///
    /// Sie verfolgt nicht - sie *driftet*, und zwar nur dann, wenn sie
    /// gerade zusammengezogen ist. Zwischen zwei Stoessen haengt sie
    /// still in der Luft. Dadurch bewegt sie sich in Schueben wie etwas
    /// im Wasser, und man kann ihre Bahn lesen, ohne sie zu jagen.
    private func updateQualle(dt: Double, toPlayer: Vec2, distance: Double) {
        stateTime += dt
        let takt = sin(stateTime * 2.2)
        let stoss = max(0, takt)
        if aggro {
            let richtung = toPlayer.normalized
            velocity.x = approach(velocity.x, richtung.x * 46 * stoss, 120 * dt)
            velocity.y = approach(velocity.y, richtung.y * 34 * stoss - 8, 120 * dt)
        } else {
            velocity.x = approach(velocity.x, sin(stateTime * 0.7) * 20 * stoss, 90 * dt)
            velocity.y = approach(velocity.y, cos(stateTime * 0.5) * 14 * stoss, 90 * dt)
        }
        facing = velocity.x < 0 ? -1 : 1
    }

    /// Der Steinfink hockt und stoesst herab.
    ///
    /// Er wartet auf dem Gelaender, bis jemand nah genug ist, und faehrt
    /// dann einen Bogen - nicht auf die Figur zu, sondern auf die Stelle,
    /// an der sie stand. Wer weiterlaeuft, wird nie getroffen; wer
    /// stehenbleibt und blockt, schon. Danach steigt er wieder und
    /// beginnt von vorn.
    private func updateFink(dt: Double, room: Room, toPlayer: Vec2, distance: Double) {
        stateTime += dt
        if attackTimer > 0 {
            // Im Stoss: er faellt schraeg und laesst sich nicht lenken.
            velocity.x = approach(velocity.x, facing * 150, 300 * dt)
            velocity.y = approach(velocity.y, 120, 420 * dt)
            return
        }
        let unten = Vec2(position.x, position.y + 3)
        if room.tile(at: unten).isStandable {
            velocity.x = approach(velocity.x, 0, 500 * dt)
            if aggro && distance < 140 && stateTime > 1.1 {
                stateTime = 0
                attackTimer = 0.85
                facing = sign(toPlayer.x) == 0 ? facing : sign(toPlayer.x)
                velocity.y = -120
            }
        } else {
            // Zurueck nach oben, sobald der Stoss vorbei ist.
            velocity.x = approach(velocity.x, 0, 200 * dt)
        }
    }

    /// Die Gabelmaus laeuft nicht, sie huscht.
    ///
    /// Ein Waechter geht gleichmaessig; ein Tier tut das nie. Also gibt es
    /// nur zwei Zustaende: sitzen und rennen. Im Sitzen zielt sie neu, im
    /// Rennen zielt sie gar nicht mehr - sie schiesst geradeaus los und
    /// laeuft an der Figur vorbei, statt sie zu verfolgen. Genau das macht
    /// sie als ersten Gegner brauchbar: gefaehrlich nur, wenn man
    /// stehenbleibt, und mit einem Schlag zu treffen, wenn man wartet.
    private func updateMaus(dt: Double, room: Room, toPlayer: Vec2) {
        if attackTimer <= 0 {
            huscht.toggle()
            if huscht {
                // Losrennen: die Richtung wird jetzt gewaehlt und danach
                // nicht mehr korrigiert.
                if aggro {
                    facing = sign(toPlayer.x) == 0 ? facing : sign(toPlayer.x)
                } else if position.x > home.x + patrolRange {
                    facing = -1
                } else if position.x < home.x - patrolRange {
                    facing = 1
                } else if rng.chance(0.35) {
                    facing = -facing
                }
                attackTimer = aggro ? 0.5 + rng.range(0, 0.2) : 0.35 + rng.range(0, 0.35)
                // Der Satz nach vorn - aber nur vom Boden aus.
                let unten = Vec2(position.x, position.y + 3)
                if room.tile(at: unten).isStandable {
                    velocity.y = -70
                }
            } else {
                attackTimer = aggro ? 0.35 + rng.range(0, 0.25) : 0.7 + rng.range(0, 0.9)
            }
        }

        // Nicht ins Leere huschen, nicht in die Wand.
        let ahead = Vec2(position.x + facing * (kind.size.width / 2 + 3), position.y + 4)
        let wallProbe = rect.offset(by: Vec2(facing * 3, 0))
        if !room.tile(at: ahead).isStandable || room.overlapsSolid(wallProbe) {
            facing = -facing
        }

        haltung = huscht ? .lauf : .ruhe
        let ziel = huscht ? facing * 132 : 0
        velocity.x = approach(velocity.x, ziel, (huscht ? 900 : 500) * dt)
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
        let stuermt = aggro && distance < chargeRange
        haltung = stuermt ? .angriff : .lauf
        let speed: Double = stuermt ? 105 : 42
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
        // Kurz vor dem Schuss sichtbar aufreissen - das ist die Ansage.
        haltung = (aggro && distance < 260 && attackTimer < 0.45) ? .angriff : .ruhe
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
        switch kind {
        case .stilleschreiter: stagger = 0.14
        // Die Maus bleibt nach einem Treffer nicht stehen, sie flieht -
        // in die Richtung, in die der Schlag sie geschoben hat.
        case .gabelmaus:
            stagger = 0.08
            huscht = true
            attackTimer = 0.55
            if knockback.x != 0 { facing = sign(knockback.x) }
        default: stagger = 0.22
        }
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
