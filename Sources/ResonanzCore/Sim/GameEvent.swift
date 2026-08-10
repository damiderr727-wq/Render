import Foundation

/// Klangereignisse. Die Kern-Bibliothek erzeugt keinen Ton, sie sagt nur,
/// was gerade zu hoeren waere.
public enum SoundCue: Sendable, Equatable {
    case jump
    case doubleJump
    case wallJump
    case land(Double)
    case dash
    case slamStart
    case slamLand
    case wallBreak
    case meleeSwing(Instrument)
    case rangedShot(Instrument)
    case hit(strong: Bool)
    case enemyDeath
    case playerHurt
    case playerDeath
    case outOfResonance
    case pickup
    case abilityGained
    case bench
    case door
    case bossRoar
    case bossPhase
    case bossDeath
}

/// Kurzlebige Sichtbarkeiten - Ringe, Federn, Staub.
public enum EffectKind: String, Sendable {
    case dust
    case feather
    case heartbeat
    case burstGlow
    case burstRot
    case ringLeier
    case ringTrommel
    case ringFloete
    case mote
}

/// Was die Darstellungsschicht nach einem Simulationsschritt erfaehrt.
public enum GameEvent: Sendable {
    case sound(SoundCue)
    case effect(EffectKind, Vec2, Vec2)
    case shake(Double)

    case fireProjectiles(instrument: Instrument, origin: Vec2, direction: Vec2)
    case slamShockwave(origin: Vec2, radius: Double)
    case wallsBroken(roomID: String, tiles: [(Int, Int)])

    case enemyKilled(kind: String, position: Vec2)
    case playerDied

    case roomChanged(from: String, to: String, door: String)
    case musicChanged(track: String, intensity: Double)
    case intensityChanged(Double)

    case instrumentPicked(Instrument)
    case abilityPicked(Ability)
    case instrumentSwitched(Instrument)

    case loreRead(text: String)
    case benchRested
    case gateHint(Ability)

    case bossPhaseChanged(Int)
    case bossDefeated
    case gameCompleted
}

/// Kleine Helfer, damit die Darstellung Ereignisse leicht filtern kann.
public extension Array where Element == GameEvent {
    var sounds: [SoundCue] {
        compactMap { if case .sound(let cue) = $0 { return cue } else { return nil } }
    }

    var shakeAmount: Double {
        reduce(0) { acc, event in
            if case .shake(let amount) = event { return Swift.max(acc, amount) }
            return acc
        }
    }
}
