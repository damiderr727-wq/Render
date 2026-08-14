#if canImport(AVFoundation) && !os(Linux)
import AVFoundation
import Foundation
import ResonanzCore

/// Ein kleiner polyphoner Synthesizer.
///
/// Das Spiel bringt keine Audiodateien mit - jeder Ton wird zur Laufzeit
/// gerechnet. Die Noten kommen sample-genau aus der Partitur, die
/// Klangeffekte dazwischen. Hall und Echo uebernehmen die Bausteine von
/// AVAudioEngine.
public final class SynthEngine {

    // MARK: Stimmen

    private enum Waveform {
        case sine, triangle, sawtooth, noise
    }

    /// Ein Teilton einer Stimme.
    private struct Partial {
        var multiplier: Double
        var level: Double
        var waveform: Waveform
        var phase: Double = 0
    }

    private struct ActiveVoice {
        var partials: [Partial]
        var amplitude: Double
        /// Huellkurve in Sekunden.
        var attack: Double
        var decay: Double
        var sustain: Double
        var release: Double
        var holdDuration: Double

        var age: Double = 0
        var released = false
        var releaseAge: Double = 0
        var finished = false

        /// Tiefpass, zwei Pole in Reihe.
        var cutoffStart: Double
        var cutoffEnd: Double
        var lp1: Double = 0
        var lp2: Double = 0

        /// Frequenzmodulation fuer Glocken.
        var fmDepth: Double = 0
        var fmRatio: Double = 0
        var fmPhase: Double = 0
        var fmDecay: Double = 1

        /// Gleitende Tonhoehe (fuer Sweeps).
        var baseFrequency: Double
        var targetFrequency: Double
        var glideTime: Double = 0

        var noiseState: UInt64 = 0x2545F4914F6CDD1D

        /// Eine Stimme, die schon fertig ist - der Rueckfall, wenn eine
        /// Wellenform nicht gebaut werden konnte.
        ///
        /// Sie stand als Erweiterung von `SynthEngine.ActiveVoice` am
        /// Dateiende. `private` reicht in Swift bis in Erweiterungen
        /// **desselben** Typs in derselben Datei - eine Erweiterung des
        /// verschachtelten Typs ist etwas anderes, und damit kam sie an
        /// ihren eigenen Speicher nicht heran. Innerhalb des Typs
        /// stellt sich die Frage nicht.
        static var silent: ActiveVoice {
            var v = ActiveVoice(
                partials: [], amplitude: 0, attack: 0.001, decay: 0.001,
                sustain: 0, release: 0.001, holdDuration: 0,
                cutoffStart: 1000, cutoffEnd: 1000,
                baseFrequency: 440, targetFrequency: 440)
            v.finished = true
            return v
        }
    }

    private struct PendingNote {
        let startSample: Int64
        let make: () -> ActiveVoice
    }

    // MARK: Aufbau

    private let engine = AVAudioEngine()
    private var sourceNode: AVAudioSourceNode?
    private let delay = AVAudioUnitDelay()
    private let reverb = AVAudioUnitReverb()

    private let sampleRate: Double
    private let lock = NSLock()
    private var pending: [PendingNote] = []
    private var voices: [ActiveVoice] = []
    private var sampleClock: Int64 = 0
    private let maxVoices = 48

    public private(set) var isRunning = false
    public var masterVolume: Float = 0.8 {
        didSet { engine.mainMixerNode.outputVolume = masterVolume }
    }

    /// Uhr fuer die Partitur: Sekunden seit dem Start der Klangmaschine.
    public var currentTime: Double {
        lock.lock()
        defer { lock.unlock() }
        return Double(sampleClock) / sampleRate
    }

    public init(sampleRate: Double = 48_000) {
        self.sampleRate = sampleRate
        voices.reserveCapacity(maxVoices)
    }

    public func start() {
        guard !isRunning else { return }
        configureSession()

        let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 2)!
        let node = AVAudioSourceNode(format: format) { [weak self] _, _, frameCount, audioBufferList in
            guard let self else { return noErr }
            self.render(frameCount: Int(frameCount), into: audioBufferList)
            return noErr
        }
        sourceNode = node

        delay.delayTime = 0.42
        delay.feedback = 34
        delay.lowPassCutoff = 2400
        delay.wetDryMix = 18

        reverb.loadFactoryPreset(.cathedral)
        reverb.wetDryMix = 32

        engine.attach(node)
        engine.attach(delay)
        engine.attach(reverb)
        engine.connect(node, to: delay, format: format)
        engine.connect(delay, to: reverb, format: format)
        engine.connect(reverb, to: engine.mainMixerNode, format: format)
        engine.mainMixerNode.outputVolume = masterVolume

        do {
            try engine.start()
            isRunning = true
        } catch {
            // Ohne Klang laesst sich immer noch spielen.
            isRunning = false
        }
    }

    public func stop() {
        engine.stop()
        isRunning = false
    }

    private func configureSession() {
        #if os(iOS) || os(tvOS)
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.ambient, mode: .default, options: [.mixWithOthers])
        try? session.setActive(true)
        #endif
    }

    // MARK: - Noten annehmen

    /// Plant eine Note der Partitur ein. `time` ist die Uhr aus `currentTime`.
    public func schedule(_ note: ScheduledNote) {
        let frequency = midiToFrequency(Double(note.midi) + note.detune / 100)
        let startSample = Int64(note.time * sampleRate)
        let voice = note.voice
        let duration = note.duration
        let gain = note.gain

        enqueue(startSample: startSample) { [weak self] in
            self?.makeVoice(voice, frequency: frequency, duration: duration, gain: gain)
                ?? ActiveVoice.silent
        }
    }

    /// Spielt sofort - fuer Klangeffekte.
    public func play(_ voice: Voice, midi: Double, duration: Double, gain: Double,
                     delaySeconds: Double = 0) {
        let frequency = midiToFrequency(midi)
        let startSample = currentSampleClock() + Int64(delaySeconds * sampleRate)
        enqueue(startSample: startSample) { [weak self] in
            self?.makeVoice(voice, frequency: frequency, duration: duration, gain: gain)
                ?? ActiveVoice.silent
        }
    }

    /// Gleitender Ton - Sprung, Stoss, Treffer.
    public func sweep(fromMidi: Double, toMidi: Double, duration: Double, gain: Double,
                      waveform: String = "sine", delaySeconds: Double = 0) {
        let start = midiToFrequency(fromMidi)
        let end = midiToFrequency(toMidi)
        let startSample = currentSampleClock() + Int64(delaySeconds * sampleRate)
        let wave: Waveform = {
            switch waveform {
            case "saw": return .sawtooth
            case "triangle": return .triangle
            default: return .sine
            }
        }()
        enqueue(startSample: startSample) {
            var v = ActiveVoice(
                partials: [Partial(multiplier: 1, level: 1, waveform: wave)],
                amplitude: gain, attack: 0.006, decay: duration * 0.6, sustain: 0.5,
                release: duration * 0.4, holdDuration: duration,
                cutoffStart: 9000, cutoffEnd: 2200,
                baseFrequency: start, targetFrequency: end)
            v.glideTime = duration
            return v
        }
    }

    /// Gefiltertes Rauschen - Schlag, Staub, Bruch.
    public func noise(duration: Double, gain: Double, cutoff: Double,
                      sweepTo: Double? = nil, delaySeconds: Double = 0) {
        let startSample = currentSampleClock() + Int64(delaySeconds * sampleRate)
        enqueue(startSample: startSample) {
            ActiveVoice(
                partials: [Partial(multiplier: 1, level: 1, waveform: .noise)],
                amplitude: gain, attack: 0.001, decay: duration * 0.7, sustain: 0.2,
                release: duration * 0.3, holdDuration: duration,
                cutoffStart: cutoff, cutoffEnd: sweepTo ?? cutoff * 0.4,
                baseFrequency: 220, targetFrequency: 220)
        }
    }

    private func enqueue(startSample: Int64, make: @escaping () -> ActiveVoice) {
        lock.lock()
        pending.append(PendingNote(startSample: startSample, make: make))
        // Die Liste bleibt klein; ein einfacher Schnitt genuegt.
        if pending.count > 512 { pending.removeFirst(pending.count - 512) }
        lock.unlock()
    }

    private func currentSampleClock() -> Int64 {
        lock.lock()
        defer { lock.unlock() }
        return sampleClock
    }

    // MARK: - Stimmen bauen

    private func makeVoice(_ voice: Voice, frequency: Double, duration: Double,
                           gain: Double) -> ActiveVoice {
        switch voice {
        case .pluck:
            return ActiveVoice(
                partials: [Partial(multiplier: 1, level: 0.85, waveform: .triangle),
                           Partial(multiplier: 1.001, level: 0.22, waveform: .sawtooth),
                           Partial(multiplier: 2, level: 0.10, waveform: .sine)],
                amplitude: gain, attack: 0.004, decay: max(0.12, duration * 0.55),
                sustain: 0.18, release: 0.30, holdDuration: duration,
                cutoffStart: min(9000, frequency * 9), cutoffEnd: max(240, frequency * 2.2),
                baseFrequency: frequency, targetFrequency: frequency)

        case .organ:
            // Registerzug: Grundton plus Oktaven und Quinten.
            let drawbars: [(Double, Double)] = [(1, 1.0), (2, 0.45), (3, 0.24),
                                                (4, 0.18), (6, 0.09), (8, 0.06)]
            return ActiveVoice(
                partials: drawbars.map {
                    Partial(multiplier: $0.0, level: $0.1, waveform: .sine)
                },
                amplitude: gain * 0.8, attack: 0.045, decay: 0.12, sustain: 0.85,
                release: 0.35, holdDuration: duration,
                cutoffStart: 8000, cutoffEnd: 6000,
                baseFrequency: frequency, targetFrequency: frequency)

        case .pad:
            return ActiveVoice(
                partials: [Partial(multiplier: 0.997, level: 0.4, waveform: .sawtooth),
                           Partial(multiplier: 1.0, level: 0.4, waveform: .sawtooth),
                           Partial(multiplier: 1.003, level: 0.4, waveform: .sawtooth)],
                amplitude: gain * 0.7, attack: max(0.4, duration * 0.3),
                decay: duration * 0.2, sustain: 0.7, release: max(0.8, duration * 0.4),
                holdDuration: duration,
                cutoffStart: 900, cutoffEnd: 1600,
                baseFrequency: frequency, targetFrequency: frequency)

        case .bass:
            return ActiveVoice(
                partials: [Partial(multiplier: 1, level: 0.9, waveform: .sine),
                           Partial(multiplier: 1, level: 0.26, waveform: .sawtooth),
                           Partial(multiplier: 0.5, level: 0.18, waveform: .sine)],
                amplitude: gain, attack: 0.012, decay: max(0.15, duration * 0.4),
                sustain: 0.55, release: 0.22, holdDuration: duration,
                cutoffStart: min(1500, frequency * 8), cutoffEnd: max(120, frequency * 3),
                baseFrequency: frequency, targetFrequency: frequency)

        case .bell:
            var v = ActiveVoice(
                partials: [Partial(multiplier: 1, level: 1, waveform: .sine)],
                amplitude: gain, attack: 0.005, decay: max(0.6, duration),
                sustain: 0.0, release: 0.4, holdDuration: max(0.6, duration),
                cutoffStart: 12000, cutoffEnd: 9000,
                baseFrequency: frequency, targetFrequency: frequency)
            v.fmRatio = 2.76
            v.fmDepth = frequency * 3.2
            v.fmDecay = max(0.4, duration * 0.8)
            return v

        case .perc:
            // n=0 tief, 1 mittig, 2 hoch - der Wert steckt in der Frequenz.
            let cutoff: Double
            let length: Double
            if frequency < midiToFrequency(0.5) { cutoff = 260; length = 0.16 }
            else if frequency < midiToFrequency(1.5) { cutoff = 1900; length = 0.12 }
            else { cutoff = 6500; length = 0.05 }
            return ActiveVoice(
                partials: [Partial(multiplier: 1, level: 1, waveform: .noise)],
                amplitude: gain, attack: 0.001, decay: length * 0.8, sustain: 0.1,
                release: length * 0.2, holdDuration: length,
                cutoffStart: cutoff, cutoffEnd: cutoff * 0.3,
                baseFrequency: 220, targetFrequency: 220)
        }
    }

    // MARK: - Klangberechnung

    private func render(frameCount: Int, into audioBufferList: UnsafeMutablePointer<AudioBufferList>) {
        let buffers = UnsafeMutableAudioBufferListPointer(audioBufferList)
        for buffer in buffers {
            memset(buffer.mData, 0, Int(buffer.mDataByteSize))
        }

        lock.lock()
        let blockStart = sampleClock
        let blockEnd = blockStart + Int64(frameCount)

        // Faellige Noten in Stimmen verwandeln.
        var stillPending: [PendingNote] = []
        stillPending.reserveCapacity(pending.count)
        for note in pending {
            if note.startSample < blockEnd {
                if voices.count < maxVoices {
                    var voice = note.make()
                    // Verspaetete Noten beginnen sofort.
                    let offset = max(0, note.startSample - blockStart)
                    voice.age = -Double(offset) / sampleRate
                    voices.append(voice)
                }
            } else {
                stillPending.append(note)
            }
        }
        pending = stillPending

        let dt = 1.0 / sampleRate
        var mix = [Double](repeating: 0, count: frameCount)

        for index in voices.indices {
            renderVoice(&voices[index], into: &mix, frames: frameCount, dt: dt)
        }
        voices.removeAll { $0.finished }
        sampleClock = blockEnd
        lock.unlock()

        // In alle Kanaele schreiben, weich begrenzt.
        for buffer in buffers {
            guard let data = buffer.mData?.assumingMemoryBound(to: Float.self) else { continue }
            for frame in 0..<frameCount {
                data[frame] = Float(tanh(mix[frame] * 0.8))
            }
        }
    }

    private func renderVoice(_ voice: inout ActiveVoice, into mix: inout [Double],
                             frames: Int, dt: Double) {
        for frame in 0..<frames {
            if voice.age < 0 {
                voice.age += dt
                continue
            }

            let envelope = envelopeValue(&voice, dt: dt)
            if voice.finished { return }

            // Tonhoehe: gleitend, wenn ein Ziel gesetzt ist.
            var frequency = voice.baseFrequency
            if voice.glideTime > 0 {
                let t = min(1, voice.age / voice.glideTime)
                frequency = voice.baseFrequency * pow(voice.targetFrequency / voice.baseFrequency, t)
            }

            // Frequenzmodulation (Glocke).
            var fmOffset = 0.0
            if voice.fmDepth > 0 {
                voice.fmPhase += (frequency * voice.fmRatio) * dt
                if voice.fmPhase > 1 { voice.fmPhase -= floor(voice.fmPhase) }
                let decay = exp(-voice.age / voice.fmDecay)
                fmOffset = sin(voice.fmPhase * 2 * .pi) * voice.fmDepth * decay
            }

            var sample = 0.0
            for partialIndex in voice.partials.indices {
                var partial = voice.partials[partialIndex]
                if partial.waveform == .noise {
                    sample += partial.level * nextNoise(&voice)
                } else {
                    let f = (frequency + fmOffset) * partial.multiplier
                    partial.phase += f * dt
                    if partial.phase > 1 { partial.phase -= floor(partial.phase) }
                    sample += partial.level * waveformValue(partial.waveform, phase: partial.phase)
                }
                voice.partials[partialIndex] = partial
            }

            // Tiefpass: zwei Pole, Grenzfrequenz faehrt ueber die Zeit herab.
            let progress = voice.holdDuration > 0
                ? min(1, voice.age / max(0.05, voice.holdDuration))
                : 1
            let cutoff = voice.cutoffStart + (voice.cutoffEnd - voice.cutoffStart) * progress
            let alpha = 1 - exp(-2 * .pi * max(40, cutoff) * dt)
            voice.lp1 += alpha * (sample - voice.lp1)
            voice.lp2 += alpha * (voice.lp1 - voice.lp2)

            mix[frame] += voice.lp2 * envelope * voice.amplitude
            voice.age += dt
        }
    }

    private func envelopeValue(_ voice: inout ActiveVoice, dt: Double) -> Double {
        if !voice.released && voice.age >= voice.holdDuration {
            voice.released = true
            voice.releaseAge = 0
        }

        if voice.released {
            voice.releaseAge += dt
            if voice.releaseAge >= voice.release {
                voice.finished = true
                return 0
            }
            let t = voice.releaseAge / max(0.001, voice.release)
            return voice.sustain * (1 - t) * (1 - t)
        }

        if voice.age < voice.attack {
            return voice.age / max(0.0001, voice.attack)
        }
        let decayAge = voice.age - voice.attack
        if decayAge < voice.decay {
            let t = decayAge / max(0.0001, voice.decay)
            return 1 + (voice.sustain - 1) * t
        }
        return voice.sustain
    }

    private func waveformValue(_ waveform: Waveform, phase: Double) -> Double {
        switch waveform {
        case .sine:
            return sin(phase * 2 * .pi)
        case .triangle:
            return 4 * abs(phase - 0.5) - 1
        case .sawtooth:
            return 2 * phase - 1
        case .noise:
            return 0
        }
    }

    private func nextNoise(_ voice: inout ActiveVoice) -> Double {
        voice.noiseState ^= voice.noiseState << 13
        voice.noiseState ^= voice.noiseState >> 7
        voice.noiseState ^= voice.noiseState << 17
        return Double(Int64(bitPattern: voice.noiseState)) / Double(Int64.max)
    }
}

#endif
