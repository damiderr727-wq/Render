import Foundation

/// Things the simulation wants the presentation layer to do.
///
/// The sim never touches SpriteKit, never plays a sound and never shakes a
/// camera — it appends to `events` and the renderer drains the queue. That
/// boundary is what lets the whole ruleset run headless in tests.
public enum GameEvent: Sendable {
    case effect(EffectRequest)
    case sound(String, volume: Double)
    case shake(strength: Double, duration: Double)
    /// Freeze-frame on a heavy hit. Measured in seconds of real time.
    case hitStop(Double)
    case damageNumber(amount: Double, at: Vec2, crit: Bool)
    case healNumber(amount: Double, at: Vec2)

    case playerHurt(remaining: Double)
    case playerDied
    case playerDodged
    case blankUsed(at: Vec2)

    case enemyKilled(kind: String, at: Vec2)
    case bossPhaseChanged(name: String, phase: Int)
    case bossDefeated(name: String)

    case roomEntered(Int)
    case roomCleared(Int)
    case doorsLocked
    case doorsUnlocked
    case floorCleared(depth: Int)

    case pickedUp(label: String, sprite: String)
    case synergyActivated(id: String, name: String, summary: String)
    case notice(String)
    case shopRefused(reason: String)
}

/// Player intent for one frame. The app layer maps keyboard, mouse and
/// gamepad into this; the sim never asks what device produced it.
public struct InputState: Sendable {
    public var move: Vec2 = .zero
    /// Aim target in world coordinates.
    public var aim: Vec2 = .zero
    public var firing: Bool = false
    public var dodgePressed: Bool = false
    public var reloadPressed: Bool = false
    public var blankPressed: Bool = false
    public var interactPressed: Bool = false
    public var weaponCycle: Int = 0
    public var weaponSelect: Int? = nil

    public init() {}

    public mutating func clearEdges() {
        dodgePressed = false
        reloadPressed = false
        blankPressed = false
        interactPressed = false
        weaponCycle = 0
        weaponSelect = nil
    }
}
