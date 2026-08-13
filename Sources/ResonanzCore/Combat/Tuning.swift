import Foundation

/// Alle Zahlen, die sich beim Spielen anfuehlen muessen, an einem Ort.
/// Die Raumpruefung (`ReachabilityProbe`) rechnet mit genau diesen Werten -
/// Level und Physik koennen also nicht auseinanderlaufen.
public enum Tuning {
    // MARK: Koerper
    public static let playerWidth: Double = 10
    public static let playerHeight: Double = 22

    // MARK: Laufen
    public static let runSpeed: Double = 145
    public static let groundAccel: Double = 1500
    public static let airAccel: Double = 950
    public static let groundFriction: Double = 1800
    public static let airFriction: Double = 420

    // MARK: Fallen und Springen
    public static let gravity: Double = 1500
    /// Beim Steigen zieht es weniger - der Sprung fuehlt sich dadurch offener an.
    public static let riseGravityScale: Double = 0.86
    public static let maxFallSpeed: Double = 620
    public static let jumpVelocity: Double = -400
    public static let doubleJumpVelocity: Double = -350
    /// Beim Loslassen der Sprungtaste wird der Aufstieg gekappt.
    public static let jumpCutFactor: Double = 0.42
    public static let coyoteTime: Double = 0.10
    public static let jumpBuffer: Double = 0.13

    // MARK: Wand
    public static let wallSlideSpeed: Double = 95
    public static let wallJumpVelocityX: Double = 215
    public static let wallJumpVelocityY: Double = -360
    /// So lange nach einem Wandsprung ignoriert die Steuerung die Richtung,
    /// damit man sich nicht sofort zurueck an die Wand klebt.
    public static let wallJumpLockTime: Double = 0.14
    public static let wallStickTime: Double = 0.16

    // MARK: Herzschlag (Dash)
    public static let dashSpeed: Double = 430
    public static let dashDuration: Double = 0.16
    public static let dashCooldown: Double = 0.42
    /// Restgeschwindigkeit nach dem Stoss, damit er nicht abrupt endet.
    public static let dashExitSpeed: Double = 165

    // MARK: Basston (Bruchschlag)
    public static let slamSpeed: Double = 520
    public static let slamRecovery: Double = 0.18

    // MARK: Treffer und Schaden
    public static let invulnerableTime: Double = 1.05
    public static let hurtKnockbackX: Double = 175
    public static let hurtKnockbackY: Double = -215
    public static let hurtControlLock: Double = 0.22
    /// Schaden an der Figur wird in halben Kristallen gerechnet: ein
    /// voller Kristall sind zwei. Dornen nehmen einen ganzen.
    public static let spikeDamage: Int = 2

    // MARK: Resonanz
    public static let resonanceRegen: Double = 2.5
    public static let resonancePerMeleeHit: Double = 14
    public static let resonancePerKill: Double = 8

    // MARK: Rueckstoss beim Aufprall auf Gegner von oben
    public static let pogoVelocity: Double = -330

    /// Rueckstoss auf die Heldin, wenn sie in der Luft zur Seite trifft.
    ///
    /// Der Abpraller nach unten gab es laengst; zur Seite passierte
    /// nichts. In den Vorbildern ist genau das der Grund, warum ein Kampf
    /// in der Luft ein Kampf ist und kein Zielen: jeder Treffer stoesst
    /// einen selbst zurueck, und man muss sich wieder heranarbeiten. Ohne
    /// das haengt man vor einem Gegner und drueckt.
    ///
    /// Klein genug, dass man nicht aus dem Raum fliegt - es soll den
    /// Schlag spuerbar machen, nicht die Bewegung uebernehmen.
    public static let meleeRecoil: Double = 138
    /// Wie lange die Steuerung danach nicht dagegenhaelt. Ohne diese
    /// kurze Sperre schiebt der gehaltene Laufknopf den Rueckstoss sofort
    /// wieder weg, und man spuert nichts.
    public static let meleeRecoilLock: Double = 0.09

    // MARK: Kamera
    public static let cameraLookAhead: Double = 34
    public static let cameraSmoothing: Double = 0.11
    public static let cameraVerticalDeadzone: Double = 18

    // MARK: Fernklang je Kern
    //
    // Der Nahkampf steht nicht hier, sondern beim Kampfstil: er haengt an
    // der Fassung, nicht am Kern. Hier steht nur, was in die Ferne geht.
    public static func ranged(_ kern: Kern) -> RangedProfile {
        switch kern {
        case .stimmgabel:
            return RangedProfile(damage: 1, speed: 320, cost: 12, cooldown: 0.26,
                                 count: 2, spread: 0.13, radius: 4,
                                 pierces: 0, lifetime: 1.0, gravity: 60)
        case .leier:
            return RangedProfile(damage: 1, speed: 300, cost: 14, cooldown: 0.28,
                                 count: 3, spread: 0.20, radius: 5,
                                 pierces: 0, lifetime: 1.1, gravity: 90)
        case .trommel:
            return RangedProfile(damage: 3, speed: 190, cost: 24, cooldown: 0.60,
                                 count: 1, spread: 0, radius: 9,
                                 pierces: 2, lifetime: 1.5, gravity: 0)
        case .floete:
            return RangedProfile(damage: 2, speed: 430, cost: 10, cooldown: 0.22,
                                 count: 1, spread: 0, radius: 4,
                                 pierces: 1, lifetime: 0.85, gravity: 0)
        case .metronom:
            // Ticken: einzeln fast nichts, aber ununterbrochen.
            return RangedProfile(damage: 1, speed: 340, cost: 6, cooldown: 0.13,
                                 count: 1, spread: 0, radius: 3,
                                 pierces: 0, lifetime: 0.70, gravity: 0)
        case .glocke:
            // Ein schwerer Schlag, der langsam durch den Raum wandert.
            return RangedProfile(damage: 4, speed: 150, cost: 30, cooldown: 0.78,
                                 count: 1, spread: 0, radius: 11,
                                 pierces: 3, lifetime: 1.9, gravity: 0)
        case .orgelpfeife:
            // Eine Lanze: schnell, schmal, geht durch alles hindurch.
            return RangedProfile(damage: 2, speed: 520, cost: 16, cooldown: 0.36,
                                 count: 1, spread: 0, radius: 3,
                                 pierces: 4, lifetime: 1.0, gravity: 0)
        }
    }
}

public struct MeleeProfile: Sendable {
    public enum Shape: Sendable { case arc, radial, thrust }

    /// Reichweite vor der Figur.
    public let reach: Double
    public let halfHeight: Double
    public let damage: Int
    public let cooldown: Double
    public let knockback: Double
    public let shape: Shape
    /// Zeit bis der Schlag trifft.
    public let windup: Double
    /// Wie lange er trifft.
    public let active: Double

    public var duration: Double { windup + active }

    /// Trefferflaeche relativ zum Fusspunkt der Figur.
    public func hitbox(origin: Vec2, facing: Double, aimY: Double) -> Rect {
        let chest = Vec2(origin.x, origin.y - Tuning.playerHeight * 0.55)
        switch shape {
        case .radial:
            return Rect(center: chest, radius: reach + 8)
        case .arc, .thrust:
            if aimY < -0.5 {
                return Rect(x: chest.x - halfHeight, y: chest.y - reach,
                            width: halfHeight * 2, height: reach)
            }
            if aimY > 0.5 {
                return Rect(x: chest.x - halfHeight, y: chest.y,
                            width: halfHeight * 2, height: reach)
            }
            let x = facing >= 0 ? chest.x : chest.x - reach
            return Rect(x: x, y: chest.y - halfHeight, width: reach, height: halfHeight * 2)
        }
    }
}

public struct RangedProfile: Sendable {
    public let damage: Int
    public let speed: Double
    public let cost: Double
    public let cooldown: Double
    /// Wie viele Geschosse pro Schuss.
    public let count: Int
    /// Streuwinkel in Radiant.
    public let spread: Double
    public let radius: Double
    /// Wie viele Gegner durchschlagen werden, bevor das Geschoss vergeht.
    public let pierces: Int
    public let lifetime: Double
    public let gravity: Double
}
