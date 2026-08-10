#if canImport(SpriteKit) && (os(iOS) || os(tvOS))
import Foundation
import SpriteKit
import UIKit

/// Bildschirmtasten fuer Beruehrungsgeraete.
///
/// Links ein Steuerkreuz, rechts die drei Knoepfe. Alle Flaechen sind
/// grosszuegiger als ihre Zeichnung - auf Glas trifft man ungenauer.
public final class TouchControlLayer: SKNode {

    public struct State {
        public var left = false
        public var right = false
        public var up = false
        public var down = false
        public var jump = false
        public var melee = false
        public var ranged = false
        public var dash = false
        public var interact = false
    }

    public var onChange: ((State) -> Void)?

    private struct Button {
        let name: String
        let rect: CGRect
        let label: String
    }

    private var buttons: [Button] = []
    private var touchAssignments: [UITouch: String] = [:]
    private var state = State()

    public func build(in size: CGSize) {
        isUserInteractionEnabled = true
        zPosition = 2000

        let left = -size.width / 2
        let right = size.width / 2
        let bottom = -size.height / 2
        let pad: CGFloat = 8
        let button: CGFloat = 34

        buttons = [
            Button(name: "left", rect: CGRect(x: left + pad, y: bottom + pad + button,
                                              width: button, height: button), label: "<"),
            Button(name: "right", rect: CGRect(x: left + pad + button * 2, y: bottom + pad + button,
                                               width: button, height: button), label: ">"),
            Button(name: "up", rect: CGRect(x: left + pad + button, y: bottom + pad + button * 2,
                                            width: button, height: button), label: "^"),
            Button(name: "down", rect: CGRect(x: left + pad + button, y: bottom + pad,
                                              width: button, height: button), label: "v"),

            Button(name: "jump", rect: CGRect(x: right - pad - button, y: bottom + pad,
                                              width: button, height: button), label: "SPR"),
            Button(name: "melee", rect: CGRect(x: right - pad - button * 2, y: bottom + pad + button,
                                               width: button, height: button), label: "NAH"),
            Button(name: "ranged", rect: CGRect(x: right - pad - button, y: bottom + pad + button * 2,
                                                width: button, height: button), label: "FERN"),
            Button(name: "dash", rect: CGRect(x: right - pad - button * 3, y: bottom + pad,
                                              width: button, height: button), label: "HRZ"),
            Button(name: "interact", rect: CGRect(x: right - pad - button * 3,
                                                  y: bottom + pad + button * 2,
                                                  width: button, height: button), label: "F"),
        ]

        for button in buttons {
            let shape = SKShapeNode(rectOf: CGSize(width: button.rect.width - 4,
                                                   height: button.rect.height - 4),
                                    cornerRadius: 6)
            shape.position = CGPoint(x: button.rect.midX, y: button.rect.midY)
            shape.fillColor = SKColor(white: 1, alpha: 0.07)
            shape.strokeColor = SKColor(white: 1, alpha: 0.20)
            shape.lineWidth = 1
            shape.name = "btn_\(button.name)"
            addChild(shape)

            let label = SKLabelNode(text: button.label)
            label.fontName = "Menlo-Bold"
            label.fontSize = 7
            label.fontColor = SKColor(white: 1, alpha: 0.5)
            label.verticalAlignmentMode = .center
            label.position = shape.position
            addChild(label)
        }
    }

    private func button(at point: CGPoint) -> String? {
        // Grosszuegige Trefferflaeche.
        buttons.first { $0.rect.insetBy(dx: -6, dy: -6).contains(point) }?.name
    }

    private func apply(_ name: String, _ value: Bool) {
        switch name {
        case "left": state.left = value
        case "right": state.right = value
        case "up": state.up = value
        case "down": state.down = value
        case "jump": state.jump = value
        case "melee": state.melee = value
        case "ranged": state.ranged = value
        case "dash": state.dash = value
        case "interact": state.interact = value
        default: break
        }
        childNode(withName: "btn_\(name)")?.alpha = value ? 1.0 : 0.55
        onChange?(state)
    }

    public override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            guard let name = button(at: touch.location(in: self)) else { continue }
            touchAssignments[touch] = name
            apply(name, true)
        }
    }

    public override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            let neu = button(at: touch.location(in: self))
            let alt = touchAssignments[touch]
            guard neu != alt else { continue }
            if let alt { apply(alt, false) }
            if let neu {
                touchAssignments[touch] = neu
                apply(neu, true)
            } else {
                touchAssignments.removeValue(forKey: touch)
            }
        }
    }

    public override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            if let name = touchAssignments.removeValue(forKey: touch) { apply(name, false) }
        }
    }

    public override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        touchesEnded(touches, with: event)
    }
}
#endif
