#if canImport(SpriteKit)
import Foundation
import SpriteKit

/// Draws text with the generated 5x8 pixel font.
///
/// `SKLabelNode` renders through Core Text, which anti-aliases — soft grey
/// edges next to hard pixel art look like a rendering bug even when nobody
/// can say why. Every string in this game is stamped from glyph sprites
/// instead, so the UI and the world share one resolution.
final class BitmapFont {
    private let atlas: Atlas
    private let info: AtlasManifest.FontInfo

    var lineHeight: CGFloat { CGFloat(info.height) }
    var tracking: CGFloat { CGFloat(info.tracking) }

    init(atlas: Atlas) {
        self.atlas = atlas
        self.info = atlas.manifest.font
    }

    private func glyph(_ character: Character) -> AtlasManifest.Glyph? {
        guard let scalar = character.unicodeScalars.first else { return nil }
        return info.glyphs[String(scalar.value)]
    }

    func width(of text: String) -> CGFloat {
        guard !text.isEmpty else { return 0 }
        var total: CGFloat = 0
        for character in text {
            total += CGFloat(glyph(character)?.advance ?? 3) + tracking
        }
        return total - tracking
    }

    enum Alignment {
        case left, center, right
    }

    /// Builds a node containing one sprite per glyph.
    ///
    /// Text is rebuilt rather than mutated when it changes: strings in this
    /// UI are short and change a few times a second at most, and pooling
    /// glyph nodes costs more complexity than it saves.
    func node(_ text: String, color: SKColor = .white,
              align: Alignment = .left, shadow: Bool = true) -> SKNode {
        let container = SKNode()
        let total = width(of: text)
        var cursor: CGFloat
        switch align {
        case .left: cursor = 0
        case .center: cursor = -total / 2
        case .right: cursor = -total
        }

        for character in text {
            guard let glyph = glyph(character) else {
                cursor += 3 + tracking
                continue
            }
            if character != " " {
                let frame = atlas.frame(glyph.sprite)
                if shadow {
                    let shade = SKSpriteNode(texture: frame.texture, size: frame.size)
                    shade.anchorPoint = CGPoint(x: 0, y: 1)
                    shade.position = CGPoint(x: cursor + 1, y: -1)
                    shade.color = SKColor(red: 0.03, green: 0.02, blue: 0.06, alpha: 1)
                    shade.colorBlendFactor = 1
                    shade.alpha = 0.85
                    shade.zPosition = -1
                    shade.texture?.filteringMode = .nearest
                    container.addChild(shade)
                }
                let sprite = SKSpriteNode(texture: frame.texture, size: frame.size)
                sprite.anchorPoint = CGPoint(x: 0, y: 1)
                sprite.position = CGPoint(x: cursor, y: 0)
                sprite.color = color
                sprite.colorBlendFactor = 1
                sprite.texture?.filteringMode = .nearest
                container.addChild(sprite)
            }
            cursor += CGFloat(glyph.advance) + tracking
        }
        return container
    }

    /// Wraps to `maxWidth` and stacks lines downward.
    func paragraph(_ text: String, color: SKColor = .white,
                   maxWidth: CGFloat, align: Alignment = .left,
                   lineSpacing: CGFloat = 3) -> SKNode {
        let container = SKNode()
        var line = ""
        var y: CGFloat = 0

        func flush() {
            guard !line.isEmpty else { return }
            let node = node(line, color: color, align: align)
            node.position = CGPoint(x: 0, y: y)
            container.addChild(node)
            y -= lineHeight + lineSpacing
            line = ""
        }

        for word in text.split(separator: " ", omittingEmptySubsequences: false) {
            let candidate = line.isEmpty ? String(word) : line + " " + word
            if width(of: candidate) > maxWidth && !line.isEmpty {
                flush()
                line = String(word)
            } else {
                line = candidate
            }
        }
        flush()
        return container
    }
}

/// A text node that only rebuilds its glyphs when the string actually changes.
/// The HUD updates every frame; most of those frames say the same thing.
final class TextNode: SKNode {
    private let font: BitmapFont
    private var current: String = ""
    private var color: SKColor
    private var align: BitmapFont.Alignment
    private var shadow: Bool

    init(font: BitmapFont, color: SKColor = .white,
         align: BitmapFont.Alignment = .left, shadow: Bool = true) {
        self.font = font
        self.color = color
        self.align = align
        self.shadow = shadow
        super.init()
    }

    required init?(coder: NSCoder) { fatalError("not supported") }

    var text: String {
        get { current }
        set {
            guard newValue != current else { return }
            current = newValue
            removeAllChildren()
            addChild(font.node(newValue, color: color, align: align, shadow: shadow))
        }
    }

    func setColor(_ newColor: SKColor) {
        guard newColor != color else { return }
        color = newColor
        let text = current
        current = ""
        self.text = text
    }
}
#endif
