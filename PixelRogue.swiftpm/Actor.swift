import Foundation

/// Stable handle to an actor. The raw value is a monotonically increasing
/// counter, never an array index — indices shift when the dead are compacted
/// out, and a stale index silently addresses the wrong enemy.
public struct ActorID: Hashable, Sendable {
    public let raw: Int
    public init(_ raw: Int) { self.raw = raw }
    public static let none = ActorID(-1)
}

public enum ActorKind: Sendable, Equatable {
    case player
    case enemy(String)
    case boss(String)
    case prop(String)
    case orbital

    public var isHostile: Bool {
        switch self {
        case .enemy, .boss: return true
        default: return false
        }
    }

    public var isBoss: Bool {
        if case .boss = self { return true }
        return false
    }
}

/// How an enemy is currently behaving. Kept as plain state rather than a
/// behaviour tree: with a dozen enemy types, a tree costs more than it saves.
public enum AIState: Sendable, Equatable {
    case idle
    case chase
    case strafe
    case reposition(Vec2)
    case windUp(Double)     // telegraphing an attack
    case attack
    case recover(Double)
    case flee
    case dead
}

public struct Actor: Sendable {
    public var id: ActorID
    public var kind: ActorKind
    public var faction: Faction

    public var position: Vec2
    public var velocity: Vec2 = .zero
    public var radius: Double = 7
    /// Vertical offset for flyers and hops. Purely visual: collision stays
    /// on the ground plane, which is what keeps a top-down game readable.
    public var height: Double = 0

    public var health: Double
    public var maxHealth: Double
    public var armor: Int = 0
    public var contactDamage: Double = 0

    public var facing: Cardinal = .south
    public var aimAngle: Double = 0
    public var moveSpeed: Double = 90

    public var ai: AIState = .idle
    public var aiTimer: Double = 0
    public var attackCooldown: Double = 0
    public var patternPhase: Double = 0
    public var patternIndex: Int = 0
    public var bossPhase: Int = 0
    /// Volleys left in the boss move currently being executed.
    public var bossVolleysLeft: Int = 0

    public var invulnerableFor: Double = 0
    public var hitFlashFor: Double = 0
    public var stunnedFor: Double = 0
    public var statuses: [StatusEffect] = []

    public var animation: String = "idle_front"
    public var animationTime: Double = 0
    public var spriteBase: String = ""
    public var homeRoom: Int = -1
    public var alive: Bool = true
    public var deathTimer: Double = 0

    /// Enemy definition, absent for the player and props.
    public var enemy: EnemyDef?
    /// Set for props that break open.
    public var destructible: Bool = false

    public init(id: ActorID, kind: ActorKind, faction: Faction,
                position: Vec2, health: Double) {
        self.id = id
        self.kind = kind
        self.faction = faction
        self.position = position
        self.health = health
        self.maxHealth = health
    }

    public var healthFraction: Double {
        maxHealth > 0 ? (health / maxHealth).clamped(0, 1) : 0
    }

    public var isDying: Bool { !alive && deathTimer > 0 }

    public func has(_ status: StatusKind) -> Bool {
        statuses.contains { $0.kind == status }
    }

    public func stacks(of status: StatusKind) -> Int {
        statuses.first { $0.kind == status }?.stacks ?? 0
    }

    /// Chill slows, shock stops you dead.
    public var speedMultiplier: Double {
        var multiplier = 1.0
        if let chill = statuses.first(where: { $0.kind == .chill }) {
            multiplier *= max(0.25, 1.0 - 0.22 * Double(chill.stacks))
        }
        if stunnedFor > 0 { multiplier = 0 }
        return multiplier
    }

    public mutating func apply(status: StatusKind, duration: Double? = nil,
                               sourceDamage: Double = 0) {
        let length = duration ?? status.defaultDuration
        if let index = statuses.firstIndex(where: { $0.kind == status }) {
            statuses[index].remaining = max(statuses[index].remaining, length)
            statuses[index].stacks = min(5, statuses[index].stacks + 1)
            statuses[index].sourceDamage = max(statuses[index].sourceDamage, sourceDamage)
        } else {
            statuses.append(StatusEffect(kind: status, duration: length,
                                         sourceDamage: sourceDamage))
        }
        if status == .shock {
            stunnedFor = max(stunnedFor, 0.45)
        }
    }
}

/// A gun, item or consumable lying on the floor.
public struct Pickup: Sendable {
    public enum Payload: Sendable, Equatable {
        case heart(Double)
        case armor
        case ammo
        case key
        case coin(Int)
        case blank
        case item(String)
        case weapon(String)
    }

    public var id: Int
    public var payload: Payload
    public var position: Vec2
    public var bobPhase: Double
    public var room: Int
    public var price: Int = 0          // > 0 means it's shop stock
    public var age: Double = 0

    public var sprite: String {
        switch payload {
        case .heart: return "pickup/heart"
        case .armor: return "pickup/armor"
        case .ammo: return "pickup/ammo_box"
        case .key: return "pickup/key"
        case .coin: return "pickup/coin"
        case .blank: return "pickup/blank"
        case .item(let id): return "item/\(id)"
        case .weapon(let id): return "weapon/\(id)"
        }
    }

    public var label: String {
        switch payload {
        case .heart: return "Heart"
        case .armor: return "Armour"
        case .ammo: return "Ammo"
        case .key: return "Key"
        case .coin(let amount): return "\(amount) coins"
        case .blank: return "Blank"
        case .item(let id): return ItemCatalog.item(id)?.name ?? id
        case .weapon(let id): return WeaponCatalog.weapon(id)?.name ?? id
        }
    }

    /// Only guns and passives need a confirm press; consumables auto-collect.
    public var requiresInteract: Bool {
        switch payload {
        case .item, .weapon: return true
        default: return price > 0
        }
    }
}
