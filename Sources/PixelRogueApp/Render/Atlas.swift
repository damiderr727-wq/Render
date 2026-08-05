#if canImport(SpriteKit)
import Foundation
import SpriteKit
import PixelRogueAssets

#if canImport(AppKit)
import AppKit
#endif

/// The JSON contract emitted by `Tools/pixelforge/build_assets.py`.
struct AtlasManifest: Decodable {
    struct Page: Decodable {
        let file: String
        let width: Int
        let height: Int
    }

    struct SpriteRect: Decodable {
        let page: Int
        let x: Int
        let y: Int
        let w: Int
        let h: Int
    }

    struct Animation: Decodable {
        let frames: [String]
        let fps: Double
        let loop: Bool
    }

    struct Glyph: Decodable {
        let sprite: String
        let advance: Int
    }

    struct FontInfo: Decodable {
        let height: Int
        let baseline: Int
        let tracking: Int
        let glyphs: [String: Glyph]
    }

    struct WeaponAnchors: Decodable {
        let pivot: [Int]
        let muzzle: [Int]
    }

    struct PanelInfo: Decodable {
        let size: Int
        let inset: Int
    }

    let pages: [Page]
    let sprites: [String: SpriteRect]
    let animations: [String: Animation]
    let font: FontInfo
    let weapons: [String: WeaponAnchors]
    let tileSize: Int
    let wallHeight: Int
    let panels: PanelInfo
}

/// A single packed sprite, ready to hand to a node.
struct Frame {
    let texture: SKTexture
    let size: CGSize
}

/// Loads the generated atlas and vends textures by name.
///
/// Everything is resolved once at startup and cached: a bullet hell asks for
/// the same twenty textures thousands of times a second, and rebuilding a
/// subtexture per request is exactly the kind of quiet cost that turns into a
/// frame-rate mystery later.
final class Atlas {
    static let missingSpriteName = "__missing__"

    private(set) var manifest: AtlasManifest
    private var pageTextures: [SKTexture] = []
    private var frameCache: [String: Frame] = [:]
    private var animationCache: [String: [Frame]] = [:]
    private let fallback: Frame

    var tileSize: CGFloat { CGFloat(manifest.tileSize) }
    var wallHeight: CGFloat { CGFloat(manifest.wallHeight) }

    enum LoadError: Error, CustomStringConvertible {
        case manifestMissing
        case pageMissing(String)
        case imageUnreadable(String)

        var description: String {
            switch self {
            case .manifestMissing:
                return """
                Could not find Assets/generated/game.json.
                Run: python3 Tools/pixelforge/build_assets.py --out Assets/generated
                """
            case .pageMissing(let file):
                return "Atlas page \(file) is missing from the bundle."
            case .imageUnreadable(let file):
                return "Atlas page \(file) could not be decoded."
            }
        }
    }

    init() throws {
        guard let url = GeneratedAssets.manifestURL else {
            throw LoadError.manifestMissing
        }
        let data = try Data(contentsOf: url)
        manifest = try JSONDecoder().decode(AtlasManifest.self, from: data)

        for page in manifest.pages {
            guard let pageURL = GeneratedAssets.pageURL(named: page.file) else {
                throw LoadError.pageMissing(page.file)
            }
            #if canImport(AppKit)
            guard let image = NSImage(contentsOf: pageURL) else {
                throw LoadError.imageUnreadable(page.file)
            }
            let texture = SKTexture(image: image)
            #else
            let texture = SKTexture(imageNamed: pageURL.path)
            #endif
            texture.filteringMode = .nearest
            pageTextures.append(texture)
        }

        // A visible magenta square beats a silent blank when a name is wrong.
        let marker = SKTexture(noiseWithSmoothness: 0, size: CGSize(width: 8, height: 8),
                               grayscale: false)
        marker.filteringMode = .nearest
        fallback = Frame(texture: marker, size: CGSize(width: 8, height: 8))
    }

    // -- lookup --------------------------------------------------------------

    func frame(_ name: String) -> Frame {
        if let cached = frameCache[name] { return cached }

        guard let rect = manifest.sprites[name],
              pageTextures.indices.contains(rect.page) else {
            // Animated entries are addressed by base name in most call sites.
            if manifest.animations[name] != nil, let first = animation(name).first {
                frameCache[name] = first
                return first
            }
            frameCache[name] = fallback
            return fallback
        }

        let page = manifest.pages[rect.page]
        let pageW = CGFloat(page.width)
        let pageH = CGFloat(page.height)
        // The manifest uses a top-left origin; SpriteKit's texture rects are
        // bottom-left, so the y axis flips here and nowhere else.
        let normalized = CGRect(x: CGFloat(rect.x) / pageW,
                                y: (pageH - CGFloat(rect.y) - CGFloat(rect.h)) / pageH,
                                width: CGFloat(rect.w) / pageW,
                                height: CGFloat(rect.h) / pageH)
        let texture = SKTexture(rect: normalized, in: pageTextures[rect.page])
        texture.filteringMode = .nearest
        let made = Frame(texture: texture,
                         size: CGSize(width: CGFloat(rect.w), height: CGFloat(rect.h)))
        frameCache[name] = made
        return made
    }

    func animation(_ name: String) -> [Frame] {
        if let cached = animationCache[name] { return cached }
        guard let animation = manifest.animations[name] else {
            let single = [frame(name)]
            animationCache[name] = single
            return single
        }
        let frames = animation.frames.map { frame($0) }
        animationCache[name] = frames
        return frames
    }

    func animationInfo(_ name: String) -> AtlasManifest.Animation? {
        manifest.animations[name]
    }

    func has(_ name: String) -> Bool {
        manifest.sprites[name] != nil || manifest.animations[name] != nil
    }

    /// Frame for an animation at a given time, honouring its fps and loop flag.
    func frame(of animation: String, at time: TimeInterval) -> Frame {
        let frames = self.animation(animation)
        guard frames.count > 1, let info = animationInfo(animation) else {
            return frames.first ?? fallback
        }
        let index = Int(time * info.fps)
        if info.loop {
            return frames[((index % frames.count) + frames.count) % frames.count]
        }
        return frames[min(index, frames.count - 1)]
    }

    func weaponAnchors(_ id: String) -> AtlasManifest.WeaponAnchors? {
        manifest.weapons[id]
    }
}

extension SKSpriteNode {
    /// Builds a node from an atlas frame with a bottom-anchored origin, which
    /// is how every world-space actor is positioned.
    convenience init(frame: Frame, groundY: CGFloat? = nil) {
        self.init(texture: frame.texture, size: frame.size)
        if let groundY {
            // groundY is measured from the top of the frame; SpriteKit anchors
            // from the bottom.
            anchorPoint = CGPoint(x: 0.5,
                                  y: (frame.size.height - groundY) / frame.size.height)
        }
        texture?.filteringMode = .nearest
    }

    func apply(_ frame: Frame) {
        if texture !== frame.texture {
            texture = frame.texture
            texture?.filteringMode = .nearest
        }
        if size != frame.size { size = frame.size }
    }
}
#endif
