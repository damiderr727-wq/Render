#if canImport(SpriteKit) && canImport(AVFoundation)
import AVFoundation
import Foundation
import PixelRogueAssets

/// Plays the generated sound effects.
///
/// Each cue gets a small ring of players rather than one, because a shotgun
/// and four impacts can land inside the same frame and a single `AVAudioPlayer`
/// restarting mid-sound turns a volley into one clipped click.
final class AudioMixer {
    private struct Voice {
        var players: [AVAudioPlayer]
        var next: Int
    }

    private var voices: [String: Voice] = [:]
    private let voicesPerSound = 4
    /// Cues fired more often than this in the same frame are dropped. A
    /// machine gun should sound like a machine gun, not like static.
    private var lastPlayed: [String: TimeInterval] = [:]
    private let minimumGap: TimeInterval = 0.035

    var masterVolume: Float = 0.7
    var enabled = true

    init() {
        preloadAll()
    }

    /// Sound files are small, and loading one on the frame it is first needed
    /// is exactly when a hitch is most noticeable.
    private func preloadAll() {
        guard let directory = GeneratedAssets.bundle.url(
            forResource: "sfx", withExtension: nil, subdirectory: "generated")
        else { return }

        let contents = (try? FileManager.default.contentsOfDirectory(
            at: directory, includingPropertiesForKeys: nil)) ?? []

        for url in contents where url.pathExtension == "wav" {
            let name = url.deletingPathExtension().lastPathComponent
            var players: [AVAudioPlayer] = []
            for _ in 0..<voicesPerSound {
                guard let player = try? AVAudioPlayer(contentsOf: url) else { break }
                player.prepareToPlay()
                players.append(player)
            }
            if !players.isEmpty {
                voices[name] = Voice(players: players, next: 0)
            }
        }
    }

    func play(_ name: String, volume: Double) {
        guard enabled, var voice = voices[name] else { return }

        let now = CACurrentMediaTime()
        if let last = lastPlayed[name], now - last < minimumGap { return }
        lastPlayed[name] = now

        let player = voice.players[voice.next]
        voice.next = (voice.next + 1) % voice.players.count
        voices[name] = voice

        player.volume = Float(volume) * masterVolume
        player.currentTime = 0
        player.play()
    }

    func stopAll() {
        for voice in voices.values {
            for player in voice.players { player.stop() }
        }
    }
}
#endif
