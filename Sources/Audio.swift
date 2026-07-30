import AVFoundation

// Villa Nachtschatten - Klang.
// Alles wird in Echtzeit errechnet, es gibt keine Audiodateien:
//   Regen        = hochpassgefiltertes Rauschen plus zufaellige Tropfen
//   Grundrauschen = braunes Rauschen, tief und traege
//   Donner       = seltene, langsam abklingende Schwellung des Rauschens
// Der Regenpegel kommt von aussen (setRain) - unterm Glasdach am lautesten,
// im Keller nur noch dumpf.
final class AudioController {
    private let engine = AVAudioEngine()
    private var started = false

    // Zustand des Synthesizers - nur im Render-Block angefasst
    private var rainVol: Float = 0.55
    private var rainTarget: Float = 0.55
    private var brown: Float = 0
    private var lpRain: Float = 0
    private var dropEnv: Float = 0
    private var thunderEnv: Float = 0
    private var thunderTimer: Float = 28

    func start() {
        guard !started else { return }
        started = true
        let sr = 44_100.0
        guard let fmt = AVAudioFormat(standardFormatWithSampleRate: sr, channels: 2) else { return }
        let srF = Float(sr)

        let node = AVAudioSourceNode { [weak self] _, _, frameCount, audioBufferList -> OSStatus in
            guard let self else { return noErr }
            let ablp = UnsafeMutableAudioBufferListPointer(audioBufferList)
            for frame in 0..<Int(frameCount) {
                // Regen: nur der Hochtonanteil des Rauschens zischt
                let white = Float.random(in: -1...1)
                self.lpRain += (white - self.lpRain) * 0.16
                let hiss = (white - self.lpRain) * 0.55
                // Einzelne Tropfen als kurze Knackser
                if Float.random(in: 0...1) < 0.00045 {
                    self.dropEnv = Float.random(in: 0.4...1.0)
                }
                self.dropEnv *= 0.994
                let drop = self.dropEnv * Float.random(in: -1...1) * 0.7

                // Braunes Rauschen: integriertes Weiss, weich begrenzt
                self.brown += Float.random(in: -1...1) * 0.02
                self.brown = max(-1, min(1, self.brown)) * 0.996

                // Ferner Donner
                self.thunderTimer -= 1 / srF
                if self.thunderTimer <= 0 {
                    self.thunderEnv = Float.random(in: 0.6...1.0)
                    self.thunderTimer = Float.random(in: 22...60)
                }
                self.thunderEnv *= 0.99996

                // Pegel weich nachziehen (Zeitkonstante rund eine Sekunde)
                self.rainVol += (self.rainTarget - self.rainVol) * 0.00003

                let sample = (hiss + drop) * 0.42 * self.rainVol
                    + self.brown * (0.16 + 1.1 * self.thunderEnv * self.thunderEnv)

                for buffer in ablp {
                    guard let data = buffer.mData else { continue }
                    data.assumingMemoryBound(to: Float.self)[frame] = sample
                }
            }
            return noErr
        }
        engine.attach(node)
        engine.connect(node, to: engine.mainMixerNode, format: fmt)
        engine.mainMixerNode.outputVolume = 0.5
        try? AVAudioSession.sharedInstance().setCategory(.ambient, options: [.mixWithOthers])
        try? AVAudioSession.sharedInstance().setActive(true)
        try? engine.start()
    }

    /// Ziel-Regenpegel 0...1. Wird im Render-Block traege angefahren.
    func setRain(_ v: Float) {
        rainTarget = max(0, min(1, v))
    }
}
