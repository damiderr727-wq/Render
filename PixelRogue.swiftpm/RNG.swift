import Foundation

/// Deterministic PRNG (xoshiro256**).
///
/// A roguelike lives or dies on reproducibility: the same seed has to produce
/// the same floor, the same chests and the same drops, both so players can
/// share seeds and so a failing test can be replayed exactly. `SystemRandom`
/// gives none of that, so the whole simulation draws from this instead.
public struct RNG: Sendable {
    private var s0: UInt64
    private var s1: UInt64
    private var s2: UInt64
    private var s3: UInt64

    public private(set) var seed: UInt64

    public init(seed: UInt64) {
        self.seed = seed
        // SplitMix64 expands one seed into the four words xoshiro needs.
        var z = seed &+ 0x9E3779B97F4A7C15
        func next() -> UInt64 {
            z = z &+ 0x9E3779B97F4A7C15
            var x = z
            x = (x ^ (x >> 30)) &* 0xBF58476D1CE4E5B9
            x = (x ^ (x >> 27)) &* 0x94D049BB133111EB
            return x ^ (x >> 31)
        }
        s0 = next()
        s1 = next()
        s2 = next()
        s3 = next()
    }

    public mutating func nextUInt64() -> UInt64 {
        let result = rotl(s1 &* 5, 7) &* 9
        let t = s1 << 17
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = rotl(s3, 45)
        return result
    }

    private func rotl(_ x: UInt64, _ k: UInt64) -> UInt64 {
        (x << k) | (x >> (64 - k))
    }

    /// Uniform in 0..<1.
    public mutating func nextDouble() -> Double {
        Double(nextUInt64() >> 11) * (1.0 / 9007199254740992.0)
    }

    public mutating func double(_ lo: Double, _ hi: Double) -> Double {
        lo + nextDouble() * (hi - lo)
    }

    /// Uniform in `range`, inclusive of both ends.
    public mutating func int(_ lo: Int, _ hi: Int) -> Int {
        guard hi > lo else { return lo }
        let span = UInt64(hi - lo + 1)
        return lo + Int(nextUInt64() % span)
    }

    public mutating func index(_ count: Int) -> Int {
        count <= 0 ? 0 : Int(nextUInt64() % UInt64(count))
    }

    public mutating func chance(_ probability: Double) -> Bool {
        nextDouble() < probability
    }

    public mutating func sign() -> Double { chance(0.5) ? 1 : -1 }

    public mutating func angle() -> Double { nextDouble() * 2 * .pi }

    public mutating func unitVector() -> Vec2 { Vec2.angle(angle()) }

    public mutating func pick<T>(_ items: [T]) -> T? {
        items.isEmpty ? nil : items[index(items.count)]
    }

    public mutating func shuffled<T>(_ items: [T]) -> [T] {
        var out = items
        guard out.count > 1 else { return out }
        for i in stride(from: out.count - 1, to: 0, by: -1) {
            out.swapAt(i, index(i + 1))
        }
        return out
    }

    /// Weighted pick. Weights need not sum to anything in particular;
    /// non-positive weights are skipped.
    public mutating func weighted<T>(_ items: [(value: T, weight: Double)]) -> T? {
        let total = items.reduce(0.0) { $0 + max(0, $1.weight) }
        guard total > 0 else { return nil }
        var roll = nextDouble() * total
        for item in items where item.weight > 0 {
            roll -= item.weight
            if roll <= 0 { return item.value }
        }
        return items.last?.value
    }

    /// Picks `count` distinct entries, or as many as exist.
    public mutating func sample<T>(_ items: [T], count: Int) -> [T] {
        Array(shuffled(items).prefix(count))
    }

    /// A child generator whose stream is independent of this one. Used to
    /// keep, say, loot rolls from shifting when level layout changes.
    public mutating func fork() -> RNG {
        RNG(seed: nextUInt64())
    }
}

/// Turns a human-typed seed like "GUNGEON" into a stable numeric seed.
public func seedValue(from text: String) -> UInt64 {
    if let numeric = UInt64(text) { return numeric }
    var hash: UInt64 = 0xCBF29CE484222325
    for byte in text.uppercased().utf8 {
        hash ^= UInt64(byte)
        hash = hash &* 0x100000001B3
    }
    return hash
}

/// Renders a seed back into a short, typeable string.
public func seedText(_ seed: UInt64) -> String {
    let alphabet = Array("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
    var value = seed
    var out = ""
    for _ in 0..<8 {
        out.append(alphabet[Int(value % UInt64(alphabet.count))])
        value /= UInt64(alphabet.count)
    }
    return out
}
