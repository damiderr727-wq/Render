#if canImport(SpriteKit) && (os(iOS) || os(tvOS))
import Foundation
import SpriteKit
import UIKit

/// Beruehrungssteuerung: links ein schwebender Stick, rechts vier Tasten.
///
/// Der erste Wurf war ein gezeichnetes Steuerkreuz aus vier Kaestchen.
/// Auf Glas ist das die falsche Form: man trifft die Kaestchen nicht,
/// man verliert sie beim Umgreifen, und die Kante zwischen "links" und
/// "rechts" liegt genau dort, wo der Daumen ohnehin schon steht. Ein
/// Stick, der dort entsteht, wo der Daumen aufsetzt, hat keine Kanten -
/// die Mitte ist immer da, wo man angefasst hat.
public final class TouchControlLayer: SKNode {

    public struct State {
        public var moveX: Double = 0
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
        let center: CGPoint
        let radius: CGFloat
        let label: String
    }

    private var buttons: [Button] = []
    private var buttonTouches: [UITouch: String] = [:]
    private var state = State()

    // Der Stick: ein Finger, der auf der linken Haelfte aufsetzt.
    private var stickTouch: UITouch?
    private var stickOrigin: CGPoint = .zero
    private var stickBase = SKShapeNode()
    private var stickKnob = SKShapeNode()
    private var halbeBreite: CGFloat = 256

    /// Wie weit der Daumen ziehen muss, bis die Richtung voll ist.
    private let stickReichweite: CGFloat = 22
    /// Unterhalb davon zaehlt die Auslenkung nicht - Wackeln ist kein Wille.
    private let totzone: CGFloat = 0.22

    private let akzent = SKColor(red: 0.37, green: 0.84, blue: 0.71, alpha: 1)

    public func build(in size: CGSize) {
        isUserInteractionEnabled = true
        zPosition = 2000
        halbeBreite = size.width / 2

        // SpriteKit stellt Beruehrungen ueber die Rahmen der KINDER zu.
        // Die linke Haelfte war leer: ein Daumen dort traf keinen
        // Knoten, die Beruehrung ging an die Szene, und der Stick
        // erschien nie. Ein beinahe unsichtbares Tuch ueber der ganzen
        // Flaeche macht jede Beruehrung zu einer Beruehrung dieser
        // Schicht - erst damit gibt es den Stick ueberhaupt.
        let fang = SKSpriteNode(color: SKColor(white: 0, alpha: 0.02),
                                size: CGSize(width: size.width, height: size.height))
        fang.position = .zero
        fang.zPosition = -1
        addChild(fang)

        let right = size.width / 2
        let bottom = -size.height / 2

        // Rechts vier Tasten im Bogen, wie der Daumen faechert: der
        // Sprung am naechsten, gross; darum herum Nah, Fern, Herzschlag.
        // F liegt abseits - Reden ist nie eilig.
        buttons = [
            Button(name: "jump", center: CGPoint(x: right - 34, y: bottom + 34),
                   radius: 22, label: "SPRUNG"),
            Button(name: "melee", center: CGPoint(x: right - 78, y: bottom + 26),
                   radius: 16, label: "NAH"),
            Button(name: "ranged", center: CGPoint(x: right - 86, y: bottom + 64),
                   radius: 16, label: "FERN"),
            Button(name: "dash", center: CGPoint(x: right - 40, y: bottom + 82),
                   radius: 16, label: "HERZ"),
            Button(name: "interact", center: CGPoint(x: right - 124, y: bottom + 100),
                   radius: 11, label: "F"),
        ]

        for button in buttons {
            let shape = SKShapeNode(circleOfRadius: button.radius)
            shape.position = button.center
            shape.fillColor = SKColor(white: 1, alpha: 0.05)
            shape.strokeColor = SKColor(white: 1, alpha: 0.22)
            shape.lineWidth = 1
            shape.name = "btn_\(button.name)"
            addChild(shape)

            let label = SKLabelNode(text: button.label)
            label.fontName = "Menlo-Bold"
            label.fontSize = button.radius > 18 ? 8 : 6
            label.fontColor = SKColor(white: 1, alpha: 0.45)
            label.verticalAlignmentMode = .center
            label.position = button.center
            addChild(label)
        }

        // Der Stick zeigt sich erst, wenn ein Daumen da ist.
        stickBase = SKShapeNode(circleOfRadius: stickReichweite + 6)
        stickBase.fillColor = .clear
        stickBase.strokeColor = SKColor(white: 1, alpha: 0.20)
        stickBase.lineWidth = 1
        stickBase.alpha = 0
        addChild(stickBase)

        stickKnob = SKShapeNode(circleOfRadius: 9)
        stickKnob.fillColor = akzent.withAlphaComponent(0.25)
        stickKnob.strokeColor = akzent.withAlphaComponent(0.8)
        stickKnob.lineWidth = 1
        stickKnob.alpha = 0
        addChild(stickKnob)
    }

    private func button(at point: CGPoint) -> String? {
        // Grosszuegig: auf Glas trifft man ungenauer, als man glaubt.
        buttons.first {
            hypot(point.x - $0.center.x, point.y - $0.center.y) <= $0.radius + 9
        }?.name
    }

    private func apply(_ name: String, _ value: Bool) {
        switch name {
        case "jump": state.jump = value
        case "melee": state.melee = value
        case "ranged": state.ranged = value
        case "dash": state.dash = value
        case "interact": state.interact = value
        default: break
        }
        childNode(withName: "btn_\(name)")?.run(
            .fadeAlpha(to: value ? 1.0 : 0.55, duration: 0.05))
        onChange?(state)
    }

    private func updateStick(to point: CGPoint) {
        var dx = (point.x - stickOrigin.x) / stickReichweite
        var dy = (point.y - stickOrigin.y) / stickReichweite
        let laenge = hypot(dx, dy)
        if laenge > 1 { dx /= laenge; dy /= laenge }

        state.moveX = abs(dx) < totzone ? 0
            : Double((abs(dx) - totzone) / (1 - totzone)) * (dx < 0 ? -1 : 1)
        // Hoch und runter wollen mehr Absicht als seitwaerts: wer nach
        // rechts oben laeuft, meint rechts - nicht "rechts und zielt".
        state.up = dy > 0.55
        state.down = dy < -0.55

        stickBase.position = stickOrigin
        stickKnob.position = CGPoint(
            x: stickOrigin.x + dx * stickReichweite,
            y: stickOrigin.y + dy * stickReichweite)
        onChange?(state)
    }

    private func endStick() {
        stickTouch = nil
        state.moveX = 0
        state.up = false
        state.down = false
        stickBase.run(.fadeOut(withDuration: 0.15))
        stickKnob.run(.fadeOut(withDuration: 0.15))
        onChange?(state)
    }

    public override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            let point = touch.location(in: self)
            if let name = button(at: point) {
                buttonTouches[touch] = name
                apply(name, true)
            } else if point.x < 0 && stickTouch == nil {
                // Die ganze linke Haelfte ist Stick - er entsteht, wo
                // der Daumen aufsetzt.
                stickTouch = touch
                stickOrigin = point
                stickBase.removeAllActions()
                stickKnob.removeAllActions()
                stickBase.alpha = 1
                stickKnob.alpha = 1
                updateStick(to: point)
            }
        }
    }

    public override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            if touch == stickTouch {
                updateStick(to: touch.location(in: self))
                continue
            }
            // Ein Daumen, der von einer Taste rutscht, laesst sie los;
            // rutscht er auf eine andere, nimmt er sie mit.
            let neu = button(at: touch.location(in: self))
            let alt = buttonTouches[touch]
            guard neu != alt else { continue }
            if let alt { apply(alt, false) }
            if let neu {
                buttonTouches[touch] = neu
                apply(neu, true)
            } else {
                buttonTouches.removeValue(forKey: touch)
            }
        }
    }

    public override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            if touch == stickTouch { endStick() }
            if let name = buttonTouches.removeValue(forKey: touch) { apply(name, false) }
        }
    }

    public override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        touchesEnded(touches, with: event)
    }
}
#endif
