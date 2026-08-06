#if canImport(SpriteKit) && canImport(UIKit)
import Foundation
import SpriteKit
import UIKit

/// On-screen controls for touch devices.
///
/// Twin-stick, with one deliberate choice: **holding the aim stick fires**.
/// A separate fire button would cost a thumb the player does not have, and in
/// a bullet hell you are aiming and shooting at the same moment anyway — the
/// only time you aim without firing is while reloading, which is automatic.
///
/// Both sticks are *floating*: the stick appears wherever the thumb lands
/// inside its half of the screen rather than at a fixed spot. Fixed sticks
/// require you to look down to find them.
final class TouchControls {
    struct Button {
        let id: String
        let label: String
        var center: CGPoint = .zero
        var radius: CGFloat = 26
        var sprite: String
    }

    let root = SKNode()

    private let atlas: Atlas
    private let font: BitmapFont

    private var moveStick: Stick
    private var aimStick: Stick
    private var buttons: [Button] = []
    private var buttonNodes: [String: SKNode] = [:]
    private var pressedButtons: Set<String> = []

    /// A floating virtual stick and the touch currently driving it.
    private final class Stick {
        var touch: UITouch?
        var origin: CGPoint = .zero
        var current: CGPoint = .zero
        let base = SKNode()
        let baseRing = SKShapeNode(circleOfRadius: 46)
        let knob = SKShapeNode(circleOfRadius: 20)

        init(tint: SKColor) {
            baseRing.strokeColor = tint.withAlphaComponent(0.35)
            baseRing.lineWidth = 3
            baseRing.fillColor = .clear
            knob.strokeColor = tint.withAlphaComponent(0.6)
            knob.fillColor = tint.withAlphaComponent(0.22)
            knob.lineWidth = 2
            base.addChild(baseRing)
            base.addChild(knob)
            base.alpha = 0
            base.zPosition = 300_000
        }

        var isActive: Bool { touch != nil }

        /// -1...1 on each axis, in screen space with y up.
        var vector: CGPoint {
            let dx = current.x - origin.x
            let dy = current.y - origin.y
            let length = max(1, sqrt(dx * dx + dy * dy))
            let clamped = min(length, 46) / 46
            return CGPoint(x: dx / length * clamped, y: dy / length * clamped)
        }

        func begin(_ touch: UITouch, at point: CGPoint) {
            self.touch = touch
            origin = point
            current = point
            base.position = point
            knob.position = .zero
            base.alpha = 1
        }

        func move(to point: CGPoint) {
            current = point
            let dx = point.x - origin.x
            let dy = point.y - origin.y
            let length = max(1, sqrt(dx * dx + dy * dy))
            let capped = min(length, 46)
            knob.position = CGPoint(x: dx / length * capped, y: dy / length * capped)
        }

        func end() {
            touch = nil
            base.alpha = 0
            knob.position = .zero
        }
    }

    init(atlas: Atlas, font: BitmapFont) {
        self.atlas = atlas
        self.font = font
        moveStick = Stick(tint: SKColor(red: 0.55, green: 0.75, blue: 1, alpha: 1))
        aimStick = Stick(tint: SKColor(red: 1, green: 0.78, blue: 0.35, alpha: 1))

        root.zPosition = 300_000
        root.addChild(moveStick.base)
        root.addChild(aimStick.base)

        buttons = [
            Button(id: "dodge", label: "ROLL", radius: 32, sprite: "ui/slot_active"),
            Button(id: "blank", label: "", radius: 24, sprite: "ui/blank_icon"),
            Button(id: "reload", label: "R", radius: 24, sprite: "ui/ammo_icon"),
            Button(id: "swap", label: "", radius: 24, sprite: "ui/slot"),
            Button(id: "interact", label: "TAKE", radius: 30, sprite: "ui/slot_active"),
            Button(id: "pause", label: "", radius: 18, sprite: "ui/panel"),
        ]
        for button in buttons { buttonNodes[button.id] = makeButtonNode(button) }
        for node in buttonNodes.values { root.addChild(node) }
    }

    private func makeButtonNode(_ button: Button) -> SKNode {
        let container = SKNode()
        container.zPosition = 300_001

        let disc = SKShapeNode(circleOfRadius: button.radius)
        disc.fillColor = SKColor(red: 0.09, green: 0.09, blue: 0.13, alpha: 0.62)
        disc.strokeColor = SKColor(red: 0.78, green: 0.72, blue: 0.5, alpha: 0.6)
        disc.lineWidth = 2
        container.addChild(disc)

        let icon = SKSpriteNode(frame: atlas.frame(button.sprite))
        icon.setScale(button.radius / 26)
        icon.alpha = 0.9
        container.addChild(icon)

        if !button.label.isEmpty {
            let text = font.node(button.label, color: .white, align: .center)
            text.position = CGPoint(x: 0, y: -button.radius - 2)
            container.addChild(text)
        }
        return container
    }

    // -- layout ---------------------------------------------------------------

    /// `size` is the visible area in the camera's coordinate space.
    func layout(for size: CGSize) {
        let right = size.width / 2
        let bottom = -size.height / 2
        let margin: CGFloat = 46

        func place(_ id: String, _ point: CGPoint) {
            if let index = buttons.firstIndex(where: { $0.id == id }) {
                buttons[index].center = point
            }
            buttonNodes[id]?.position = point
        }

        place("dodge", CGPoint(x: right - margin, y: bottom + margin + 84))
        place("blank", CGPoint(x: right - margin - 62, y: bottom + margin + 40))
        place("reload", CGPoint(x: right - margin, y: bottom + margin + 158))
        place("swap", CGPoint(x: right - margin - 62, y: bottom + margin + 112))
        place("interact", CGPoint(x: 0, y: bottom + margin + 26))
        place("pause", CGPoint(x: right - 30, y: size.height / 2 - 30))

        buttonNodes["interact"]?.isHidden = true
    }

    /// The take prompt only exists when there is something to take.
    func setInteractVisible(_ visible: Bool) {
        buttonNodes["interact"]?.isHidden = !visible
    }

    func setControlsVisible(_ visible: Bool) {
        root.isHidden = !visible
    }

    // -- touch handling -------------------------------------------------------

    /// Returns the ids of buttons pressed by this touch, if any.
    @discardableResult
    func began(_ touch: UITouch, at point: CGPoint, viewport: CGSize) -> [String] {
        // Buttons win over sticks: they sit inside the right-hand stick zone,
        // and a thumb landing on one clearly means the button.
        if let hit = buttonHit(point) {
            pressedButtons.insert(hit)
            flash(hit)
            return [hit]
        }
        if point.x < 0 {
            if !moveStick.isActive { moveStick.begin(touch, at: point) }
        } else {
            if !aimStick.isActive { aimStick.begin(touch, at: point) }
        }
        return []
    }

    func moved(_ touch: UITouch, to point: CGPoint) {
        if moveStick.touch === touch { moveStick.move(to: point) }
        if aimStick.touch === touch { aimStick.move(to: point) }
    }

    func ended(_ touch: UITouch) {
        if moveStick.touch === touch { moveStick.end() }
        if aimStick.touch === touch { aimStick.end() }
    }

    func endAll() {
        moveStick.end()
        aimStick.end()
        pressedButtons.removeAll()
    }

    private func buttonHit(_ point: CGPoint) -> String? {
        for button in buttons {
            guard let node = buttonNodes[button.id], !node.isHidden else { continue }
            let dx = point.x - button.center.x
            let dy = point.y - button.center.y
            // A generous hit radius: thumbs are imprecise and a missed dodge
            // is the most expensive miss in the game.
            if dx * dx + dy * dy <= (button.radius + 12) * (button.radius + 12) {
                return button.id
            }
        }
        return nil
    }

    private func flash(_ id: String) {
        guard let node = buttonNodes[id] else { return }
        node.removeAllActions()
        node.setScale(0.86)
        node.run(.scale(to: 1, duration: 0.14))
    }

    // -- state for the simulation ---------------------------------------------

    var moveVector: CGPoint { moveStick.isActive ? moveStick.vector : .zero }
    var aimVector: CGPoint { aimStick.isActive ? aimStick.vector : .zero }
    var isAiming: Bool { aimStick.isActive }

    /// Consumes the edge-triggered presses collected since the last call.
    func consumePresses() -> Set<String> {
        defer { pressedButtons.removeAll() }
        return pressedButtons
    }
}
#endif
