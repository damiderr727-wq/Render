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
    case meleeSwing
    case rangedShot(Kern)
    case hit(strong: Bool)
    /// Ein Treffer, der auf dem Schlag lag. `glieder` faerbt die Tonhoehe:
    /// die Kette klingt aufwaerts, damit man sie hoert, ohne hinzusehen.
    case imTakt(glieder: Int)
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
    /// Klangringe nach Groesse. Sie gehoeren keiner Waffe - sie sind das,
    /// was ein Stoss in der Luft hinterlaesst.
    case ringKlein
    case ringMittel
    case ringGross
    /// Der Schlagbogen. Wie er aussieht, entscheidet die gefuehrte Klinge -
    /// die Darstellung schlaegt den Namen im Fortschritt nach.
    case klingenschlag
    case mote
}

/// Was die Darstellungsschicht nach einem Simulationsschritt erfaehrt.
public enum GameEvent: Sendable {
    case sound(SoundCue)
    case effect(EffectKind, Vec2, Vec2)
    case shake(Double)

    case fireProjectiles(kern: Kern, origin: Vec2, direction: Vec2)
    case slamShockwave(origin: Vec2, radius: Double)
    case wallsBroken(roomID: String, tiles: [(Int, Int)])

    case enemyKilled(kind: String, position: Vec2)
    /// Ein Bestiariumseintrag hat sich ganz geoeffnet.
    case bestiariumEintrag(Bestiarium.Eintrag)
    /// Ein Treffer hat die Klangkette veraendert - fuer Anzeige und Klang.
    case klangkette(Klangkette.Wirkung, glieder: Int)
    case playerDied

    case roomChanged(from: String, to: String, door: String)
    case musicChanged(track: String, intensity: Double)
    case intensityChanged(Double)

    case equipmentFound(Equipment)
    case equipmentWorn(Equipment)
    case siegelFound(Siegel)
    case siegelWorn(Siegel, angelegt: Bool)
    case klingeFound(Klinge)
    case kernPicked(Kern)
    case abilityPicked(Ability)
    case kernSwitched(Kern)

    case loreRead(text: String)
    case benchRested
    case gateHint(Ability)

    /// Sie faehrt aus ihrer Fassung. Einmal, am Ende.
    case bruch
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
