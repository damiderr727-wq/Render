#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Laedt die vom Python-Generator gebauten Atlanten und schneidet sie in
/// einzelne Bilder. Ein Atlas pro Thema haelt die Zahl der Zeichenaufrufe
/// klein, weil SpriteKit Sprites derselben Textur zusammenfasst.
public final class AtlasStore {

    public struct FrameInfo {
        public let texture: SKTexture
        public let size: CGSize
        /// 0..1, gemessen von links unten.
        public let anchor: CGPoint
        public let fps: Double
    }

    private struct AtlasMeta: Decodable {
        struct Frame: Decodable {
            let x: Int
            let y: Int
            let w: Int
            let h: Int
            let pivotX: Double
            let pivotY: Double
            let fps: Double?
            let parallax: Double?
        }
        let atlas: String
        let width: Int
        let height: Int
        let frames: [String: Frame]
    }

    private var frames: [String: FrameInfo] = [:]
    private var sequences: [String: [FrameInfo]] = [:]
    public private(set) var parallaxFactors: [String: Double] = [:]

    public static let shared = AtlasStore()

    private init() {}

    public func loadAll() throws {
        for name in ["characters", "tiles", "props", "fx", "backdrops"] {
            try load(name)
        }
        buildSequences()
    }

    private func load(_ name: String) throws {
        let metaURL = try Resources.url(subdirectory: "Atlas", name: name, ext: "json")
        let imageURL = try Resources.url(subdirectory: "Atlas", name: name, ext: "png")

        let meta = try JSONDecoder().decode(AtlasMeta.self, from: Data(contentsOf: metaURL))
        let sheet = SKTexture(image: try loadImage(at: imageURL))
        sheet.filteringMode = .nearest

        for (frameName, frame) in meta.frames {
            // Der Atlas zaehlt y von oben, SKTexture von unten.
            let rect = CGRect(
                x: CGFloat(frame.x) / CGFloat(meta.width),
                y: 1 - CGFloat(frame.y + frame.h) / CGFloat(meta.height),
                width: CGFloat(frame.w) / CGFloat(meta.width),
                height: CGFloat(frame.h) / CGFloat(meta.height))
            let texture = SKTexture(rect: rect, in: sheet)
            texture.filteringMode = .nearest

            // Der Ursprung liegt im Atlas oben-links, in SpriteKit unten-links.
            let anchor = CGPoint(x: CGFloat(frame.pivotX), y: 1 - CGFloat(frame.pivotY))
            frames[frameName] = FrameInfo(
                texture: texture,
                size: CGSize(width: frame.w, height: frame.h),
                anchor: anchor,
                fps: frame.fps ?? 8)
            if let parallax = frame.parallax {
                parallaxFactors[frameName] = parallax
            }
        }
    }

    /// Fasst durchnummerierte Bilder ("name_0", "name_1", ...) zu Reihen zusammen.
    private func buildSequences() {
        var grouped: [String: [(Int, FrameInfo)]] = [:]
        for (name, info) in frames {
            guard let separator = name.lastIndex(of: "_"),
                  let index = Int(name[name.index(after: separator)...])
            else { continue }
            grouped[String(name[..<separator]), default: []].append((index, info))
        }
        for (base, list) in grouped {
            sequences[base] = list.sorted { $0.0 < $1.0 }.map(\.1)
        }
    }

    public func frame(_ name: String) -> FrameInfo? {
        frames[name] ?? sequences[name]?.first
    }

    public func sequence(_ name: String) -> [FrameInfo] {
        if let list = sequences[name] { return list }
        if let single = frames[name] { return [single] }
        return []
    }

    /// Baut ein Sprite mit richtigem Ursprung und Groesse.
    public func sprite(_ name: String) -> SKSpriteNode {
        guard let info = frame(name) else {
            // Fehlt ein Bild, faellt ein sichtbarer Platzhalter auf.
            let node = SKSpriteNode(color: .magenta, size: CGSize(width: 8, height: 8))
            node.name = "fehlt:\(name)"
            return node
        }
        let node = SKSpriteNode(texture: info.texture, size: info.size)
        node.anchorPoint = info.anchor
        node.texture?.filteringMode = .nearest
        return node
    }

    /// Endlosschleife einer Bildreihe.
    public func loop(_ name: String, speed: Double = 1) -> SKAction? {
        let list = sequence(name)
        guard list.count > 1 else { return nil }
        let interval = 1.0 / (list[0].fps * speed)
        return .repeatForever(.animate(with: list.map(\.texture),
                                       timePerFrame: interval,
                                       resize: false,
                                       restore: false))
    }

    /// Einmalige Bildreihe, danach verschwindet der Knoten.
    public func once(_ name: String, speed: Double = 1) -> SKAction {
        let list = sequence(name)
        guard list.count > 1 else { return .sequence([.wait(forDuration: 0.2), .removeFromParent()]) }
        let interval = 1.0 / (list[0].fps * speed)
        return .sequence([
            .animate(with: list.map(\.texture), timePerFrame: interval, resize: false, restore: false),
            .removeFromParent(),
        ])
    }
}

// MARK: - Bild laden

#if canImport(UIKit)
import UIKit
private func loadImage(at url: URL) throws -> UIImage {
    guard let image = UIImage(contentsOfFile: url.path) else {
        throw ResourceError.missing(url.lastPathComponent)
    }
    return image
}
#elseif canImport(AppKit)
import AppKit
private func loadImage(at url: URL) throws -> NSImage {
    guard let image = NSImage(contentsOf: url) else {
        throw ResourceError.missing(url.lastPathComponent)
    }
    return image
}
#endif
#endif
