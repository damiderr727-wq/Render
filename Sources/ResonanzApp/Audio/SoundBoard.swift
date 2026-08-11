#if canImport(AVFoundation) && !os(Linux)
import Foundation
import ResonanzCore

/// Uebersetzt Spielereignisse in Klang.
///
/// Die Waffe ist der Schall - deshalb sind die Angriffe selbst Musik:
/// die Leier zupft Akkordtoene, die Trommel schlaegt Grundtoene, die
/// Floete traegt reine Sinustoene. Damit nichts falsch klingt, laufen
/// alle Treffer ueber eine gemeinsame Tonleiter.
public final class SoundBoard {
    private let synth: SynthEngine

    /// Aeolisch gefaerbte Leiter auf D - hier klingt kein Treffer daneben.
    private let scale = [0, 2, 3, 5, 7, 8, 10]
    private let root = 62.0
    private var comboStep = 0
    private var comboResetAt: Double = 0

    public init(synth: SynthEngine) {
        self.synth = synth
    }

    /// Der naechste Ton der Leiter. Nach kurzer Pause faengt sie von vorn an,
    /// sodass eine Angriffsserie als aufsteigende Linie klingt.
    private func nextComboNote(octave: Double = 0) -> Double {
        let now = synth.currentTime
        if now > comboResetAt { comboStep = 0 }
        comboResetAt = now + 1.4
        let index = comboStep % scale.count
        let step = Double(comboStep / scale.count)
        comboStep = (comboStep + 1) % 14
        return root + Double(scale[index]) + (step + octave) * 12
    }

    public func play(_ cue: SoundCue) {
        switch cue {
        case .jump:
            synth.sweep(fromMidi: 69, toMidi: 78, duration: 0.13, gain: 0.16, waveform: "triangle")

        case .doubleJump:
            synth.sweep(fromMidi: 76, toMidi: 88, duration: 0.22, gain: 0.16)
            synth.noise(duration: 0.2, gain: 0.09, cutoff: 3600, sweepTo: 8000)
            synth.play(.bell, midi: 88, duration: 0.7, gain: 0.10)

        case .wallJump:
            synth.sweep(fromMidi: 64, toMidi: 74, duration: 0.16, gain: 0.14, waveform: "triangle")
            synth.noise(duration: 0.12, gain: 0.07, cutoff: 3000, sweepTo: 1200)

        case .land(let force):
            synth.noise(duration: 0.09, gain: 0.10 * force, cutoff: 700, sweepTo: 240)

        case .dash:
            // Zwei tiefe Impulse - der geliehene Herzschlag.
            synth.sweep(fromMidi: 50, toMidi: 34, duration: 0.22, gain: 0.20, waveform: "saw")
            synth.noise(duration: 0.1, gain: 0.22, cutoff: 150, sweepTo: 60)
            synth.noise(duration: 0.12, gain: 0.16, cutoff: 130, sweepTo: 55, delaySeconds: 0.11)

        case .slamStart:
            synth.sweep(fromMidi: 60, toMidi: 30, duration: 0.35, gain: 0.18, waveform: "saw")

        case .slamLand:
            synth.noise(duration: 0.3, gain: 0.24, cutoff: 500, sweepTo: 120)
            synth.play(.bass, midi: 26, duration: 0.5, gain: 0.26)

        case .wallBreak:
            synth.noise(duration: 0.5, gain: 0.30, cutoff: 1800, sweepTo: 220)
            synth.sweep(fromMidi: 40, toMidi: 20, duration: 0.6, gain: 0.26, waveform: "saw")
            // Der Akkord loest sich endlich auf.
            for (i, interval) in [0, 7, 12, 16].enumerated() {
                synth.play(.pluck, midi: 50 + Double(interval), duration: 0.8,
                           gain: 0.08, delaySeconds: Double(i) * 0.05)
            }

        case .meleeSwing(let kern):
            switch kern {
            case .leier:
                let base = nextComboNote()
                for (i, interval) in [0.0, 4, 7, 12].enumerated() {
                    synth.play(.pluck, midi: base + interval, duration: 0.5,
                               gain: 0.13, delaySeconds: Double(i) * 0.018)
                }
            case .trommel:
                synth.noise(duration: 0.26, gain: 0.30, cutoff: 420, sweepTo: 90)
                synth.sweep(fromMidi: 45, toMidi: 28, duration: 0.3, gain: 0.26)
            case .floete:
                let note = nextComboNote(octave: 1)
                synth.sweep(fromMidi: note - 3, toMidi: note, duration: 0.09, gain: 0.14)
                synth.noise(duration: 0.07, gain: 0.05, cutoff: 5000)
            }

        case .rangedShot(let kern):
            switch kern {
            case .leier:
                let base = nextComboNote(octave: 1)
                for (i, interval) in [0.0, 3, 7].enumerated() {
                    synth.play(.pluck, midi: base + interval, duration: 0.7,
                               gain: 0.11, delaySeconds: Double(i) * 0.03)
                }
            case .trommel:
                synth.sweep(fromMidi: 38, toMidi: 24, duration: 0.45, gain: 0.24, waveform: "triangle")
                synth.noise(duration: 0.3, gain: 0.14, cutoff: 320, sweepTo: 100)
            case .floete:
                let note = nextComboNote(octave: 2)
                synth.sweep(fromMidi: note, toMidi: note + 7, duration: 0.3, gain: 0.13)
            }

        case .hit(let strong):
            synth.noise(duration: strong ? 0.16 : 0.09, gain: strong ? 0.22 : 0.13,
                        cutoff: strong ? 900 : 1700, sweepTo: strong ? 360 : 700)
            synth.sweep(fromMidi: strong ? 55 : 67, toMidi: strong ? 40 : 55,
                        duration: 0.09, gain: strong ? 0.16 : 0.10, waveform: "saw")

        case .enemyDeath:
            synth.sweep(fromMidi: 60, toMidi: 36, duration: 0.36, gain: 0.16, waveform: "triangle")
            synth.noise(duration: 0.3, gain: 0.13, cutoff: 2400, sweepTo: 400)
            synth.play(.bell, midi: 74, duration: 0.9, gain: 0.08, delaySeconds: 0.04)

        case .playerHurt:
            // Kleine Sekunde: die Dissonanz greift nach ihr.
            synth.sweep(fromMidi: 58, toMidi: 52, duration: 0.4, gain: 0.22, waveform: "saw")
            synth.sweep(fromMidi: 59, toMidi: 53, duration: 0.4, gain: 0.16, waveform: "saw")
            synth.noise(duration: 0.24, gain: 0.20, cutoff: 1100, sweepTo: 220)

        case .playerDeath:
            for (i, note) in [62.0, 61, 59, 56, 50].enumerated() {
                synth.play(.organ, midi: note, duration: 1.6, gain: 0.14,
                           delaySeconds: Double(i) * 0.18)
            }
            synth.sweep(fromMidi: 50, toMidi: 24, duration: 2.2, gain: 0.16, waveform: "saw")

        case .outOfResonance:
            synth.play(.pluck, midi: 55, duration: 0.18, gain: 0.06)
            synth.noise(duration: 0.08, gain: 0.04, cutoff: 900)

        case .pickup:
            for (i, note) in [74.0, 78, 81, 86].enumerated() {
                synth.play(.bell, midi: note, duration: 1.4, gain: 0.13,
                           delaySeconds: Double(i) * 0.075)
            }

        case .abilityGained:
            for (i, note) in [50.0, 57, 62, 66, 69, 74].enumerated() {
                synth.play(.organ, midi: note, duration: 2.4, gain: 0.11,
                           delaySeconds: Double(i) * 0.1)
            }
            for (i, note) in [86.0, 90, 93].enumerated() {
                synth.play(.bell, midi: note, duration: 2.2, gain: 0.10,
                           delaySeconds: 0.7 + Double(i) * 0.14)
            }

        case .bench:
            // Stimmgabel: ein Ton pendelt sich ein.
            synth.sweep(fromMidi: 68.6, toMidi: 69, duration: 1.1, gain: 0.14)
            synth.play(.bell, midi: 81, duration: 2.0, gain: 0.08, delaySeconds: 0.1)

        case .door:
            synth.noise(duration: 0.4, gain: 0.08, cutoff: 800, sweepTo: 240)

        case .bossRoar:
            // Tritonus - der Diabolus in musica.
            synth.play(.organ, midi: 38, duration: 2.2, gain: 0.22)
            synth.play(.organ, midi: 44, duration: 2.2, gain: 0.20)
            synth.sweep(fromMidi: 45, toMidi: 26, duration: 1.6, gain: 0.24, waveform: "saw")
            synth.noise(duration: 1.2, gain: 0.20, cutoff: 900, sweepTo: 180)

        case .bossPhase:
            for (i, note) in [38.0, 41, 44, 47].enumerated() {
                synth.play(.organ, midi: note, duration: 2.8, gain: 0.16,
                           delaySeconds: Double(i) * 0.06)
            }

        case .bossDeath:
            // Der Akkord loest sich nach D-Dur auf.
            for (i, note) in [38.0, 45, 50, 54, 57, 62].enumerated() {
                synth.play(.organ, midi: note, duration: 4.0, gain: 0.14,
                           delaySeconds: Double(i) * 0.12)
            }
            for (i, note) in [78.0, 81, 86].enumerated() {
                synth.play(.bell, midi: note, duration: 3.0, gain: 0.11,
                           delaySeconds: 1.0 + Double(i) * 0.2)
            }
        }
    }
}
#endif
