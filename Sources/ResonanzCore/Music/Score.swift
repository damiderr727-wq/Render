import Foundation

/// Klangfarben, die die Darstellungsschicht bereitstellen muss.
public enum Voice: String, Codable, Sendable, CaseIterable {
    /// Gezupfte Saite - Leier, Cembalo.
    case pluck
    /// Kirchenorgel aus gestapelten Registern.
    case organ
    /// Weiche Flaeche, der Atem der Welt.
    case pad
    /// Tiefes Fundament.
    case bass
    /// Kristallglocke.
    case bell
    /// Perkussion aus gefiltertem Rauschen (n: 0 tief, 1 mittig, 2 hoch).
    case perc
}

public struct ScoreNote: Codable, Sendable {
    /// Zeit in Schlaegen ab Schleifenbeginn.
    public let t: Double
    /// MIDI-Tonhoehe (bei `perc` die Klangnummer).
    public let n: Int
    /// Dauer in Schlaegen.
    public let d: Double
    /// Anschlagstaerke 0..1.
    public let v: Double
}

public struct ScoreTrack: Codable, Sendable {
    public let voice: Voice
    public let gain: Double
    /// Erst ab dieser Intensitaet erklingt die Spur.
    public let layer: Double
    public let detune: Double?
    public let notes: [ScoreNote]
}

/// Ein Stueck. Bach, fuer diese Welt umgeschrieben.
public struct Score: Codable, Sendable {
    public let id: String
    /// Herkunft des Materials, fuer den Abspann.
    public let source: String
    public let bpm: Double
    /// Schleifenlaenge in Schlaegen.
    public let loop: Double
    public let tracks: [ScoreTrack]

    public var secondsPerBeat: Double { 60 / bpm }
    public var loopDuration: Double { loop * secondsPerBeat }
}

public struct ScoreIndex: Codable, Sendable {
    public struct Entry: Codable, Sendable {
        public let id: String
        public let source: String
        public let bpm: Double
        public let loop: Double
        public let tracks: Int
        public let notes: Int
    }
    public let scores: [Entry]
}

/// Eine eingeplante Note - was, wann, wie laut.
public struct ScheduledNote: Sendable {
    public let voice: Voice
    public let midi: Int
    /// Absolute Startzeit auf der Uhr des Aufrufers.
    public let time: Double
    public let duration: Double
    public let gain: Double
    public let detune: Double
}

public final class ScoreLibrary {
    public private(set) var scores: [String: Score] = [:]
    public let index: ScoreIndex

    public init() throws {
        index = try Resources.decode(ScoreIndex.self, subdirectory: "Scores", name: "index")
        for entry in index.scores {
            scores[entry.id] = try Resources.decode(Score.self, subdirectory: "Scores", name: entry.id)
        }
    }

    public func score(_ id: String) -> Score? { scores[id] }
}

/// Plant Noten im Voraus ein und blendet Stuecke ineinander.
///
/// Der Dirigent erzeugt keinen Ton. Er sagt nur, welche Note wann faellig
/// waere - die Klangschicht setzt das um. Dadurch bleibt die Musik testbar.
public final class MusicDirector {
    public private(set) var currentID: String?
    public private(set) var intensity: Double = 0
    public var targetIntensity: Double = 0

    private var score: Score?
    private var startTime: Double = 0
    private var scheduledUpTo: Double = 0
    private let library: ScoreLibrary

    /// Wie weit im Voraus geplant wird.
    public var lookahead: Double = 0.35

    public init(library: ScoreLibrary) {
        self.library = library
    }

    /// Wechselt das Stueck. `now` ist die Uhr des Aufrufers (Audio-Zeit).
    public func play(_ id: String, now: Double, restart: Bool = false) {
        guard restart || id != currentID else { return }
        guard let next = library.score(id) else { return }
        score = next
        currentID = id
        startTime = now + 0.05
        scheduledUpTo = startTime
    }

    public func stop() {
        score = nil
        currentID = nil
    }

    /// Liefert alle Noten, die zwischen dem letzten Aufruf und
    /// `now + lookahead` beginnen.
    public func pull(now: Double, dt: Double) -> [ScheduledNote] {
        intensity = damp(intensity, targetIntensity, rate: 0.04, dt: dt)
        guard let score else { return [] }

        let horizon = now + lookahead
        guard horizon > scheduledUpTo else { return [] }

        let spb = score.secondsPerBeat
        let fromBeat = (scheduledUpTo - startTime) / spb
        let toBeat = (horizon - startTime) / spb
        scheduledUpTo = horizon

        var out: [ScheduledNote] = []
        let firstLoop = Int(floor(fromBeat / score.loop))
        let lastLoop = Int(floor(toBeat / score.loop))
        guard lastLoop >= firstLoop else { return [] }

        for loopIndex in firstLoop...lastLoop {
            let origin = Double(loopIndex) * score.loop
            for track in score.tracks {
                // Sanftes Einblenden knapp oberhalb der Schwelle.
                let head = clamp((intensity - track.layer) / 0.15, 0, 1)
                guard head > 0.02 else { continue }
                for note in track.notes {
                    let beat = origin + note.t
                    guard beat >= fromBeat, beat < toBeat else { continue }
                    out.append(ScheduledNote(
                        voice: track.voice,
                        midi: note.n,
                        time: startTime + beat * spb,
                        duration: note.d * spb,
                        gain: note.v * track.gain * head,
                        detune: track.detune ?? 0))
                }
            }
        }
        return out.sorted { $0.time < $1.time }
    }
}

/// MIDI-Note zu Frequenz.
public func midiToFrequency(_ midi: Double) -> Double {
    440 * pow(2, (midi - 69) / 12)
}
