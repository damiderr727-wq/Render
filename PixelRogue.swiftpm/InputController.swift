#if canImport(SpriteKit)
import Foundation
import SpriteKit

#if canImport(AppKit)
import AppKit
#endif

#if canImport(GameController)
import GameController
#endif

/// Turns keyboard, mouse and gamepad into the sim's `InputState`.
///
/// The simulation never learns which device produced a frame of input, which
/// is what lets a gamepad's right stick and a mouse cursor both mean "aim
/// here" without a branch anywhere in the game rules.
final class InputController {
    private var pressed: Set<UInt16> = []
    private var mouseDownLeft = false
    private var mouseDownRight = false

    /// Edge-triggered actions, consumed once by the next `poll`.
    private var pendingDodge = false
    private var pendingReload = false
    private var pendingBlank = false
    private var pendingInteract = false
    private var pendingCycle = 0
    private var pendingSelect: Int?
    private var pendingPause = false

    /// Aim point in scene coordinates, updated from the mouse or the stick.
    private(set) var aimScenePoint: CGPoint = .zero
    private var usingGamepadAim = false
    private var gamepadAim = CGPoint(x: 1, y: 0)

    // macOS virtual key codes.
    private enum Key {
        static let w: UInt16 = 13, a: UInt16 = 0, s: UInt16 = 1, d: UInt16 = 2
        static let up: UInt16 = 126, down: UInt16 = 125
        static let left: UInt16 = 123, right: UInt16 = 124
        static let space: UInt16 = 49, shift: UInt16 = 56
        static let r: UInt16 = 15, q: UInt16 = 12, e: UInt16 = 14, f: UInt16 = 3
        static let tab: UInt16 = 48, escape: UInt16 = 53, enter: UInt16 = 36
        static let one: UInt16 = 18, two: UInt16 = 19
        static let three: UInt16 = 20, four: UInt16 = 21
    }

    var pauseRequested: Bool {
        defer { pendingPause = false }
        return pendingPause
    }

    var confirmPressed: Bool {
        pressed.contains(Key.enter) || pressed.contains(Key.space) || mouseDownLeft
    }

    // -- event intake ---------------------------------------------------------

    func keyDown(_ keyCode: UInt16) {
        // Ignore auto-repeat for edge actions: holding space should roll once.
        let isNew = !pressed.contains(keyCode)
        pressed.insert(keyCode)
        guard isNew else { return }

        switch keyCode {
        case Key.space, Key.shift: pendingDodge = true
        case Key.r: pendingReload = true
        case Key.q: pendingBlank = true
        case Key.e, Key.f: pendingInteract = true
        case Key.tab: pendingCycle = 1
        case Key.escape: pendingPause = true
        case Key.one: pendingSelect = 0
        case Key.two: pendingSelect = 1
        case Key.three: pendingSelect = 2
        case Key.four: pendingSelect = 3
        default: break
        }
    }

    func keyUp(_ keyCode: UInt16) {
        pressed.remove(keyCode)
    }

    func mouseDown(left: Bool) {
        if left { mouseDownLeft = true } else { mouseDownRight = true; pendingBlank = true }
    }

    func mouseUp(left: Bool) {
        if left { mouseDownLeft = false } else { mouseDownRight = false }
    }

    func scrolled(by delta: CGFloat) {
        guard abs(delta) > 0.1 else { return }
        pendingCycle = delta > 0 ? 1 : -1
    }

    func setAim(scenePoint: CGPoint) {
        aimScenePoint = scenePoint
        usingGamepadAim = false
    }

    func releaseAll() {
        pressed.removeAll()
        mouseDownLeft = false
        mouseDownRight = false
    }

    // -- polling --------------------------------------------------------------

    /// Builds one frame of intent. `playerScenePoint` is where the player is
    /// on screen, needed to turn a stick direction into an aim point.
    func poll(playerScenePoint: CGPoint) -> InputState {
        var state = InputState()

        var move = Vec2.zero
        if pressed.contains(Key.w) || pressed.contains(Key.up) { move.y -= 1 }
        if pressed.contains(Key.s) || pressed.contains(Key.down) { move.y += 1 }
        if pressed.contains(Key.a) || pressed.contains(Key.left) { move.x -= 1 }
        if pressed.contains(Key.d) || pressed.contains(Key.right) { move.x += 1 }
        state.firing = mouseDownLeft

        #if canImport(GameController)
        if let pad = GCController.current?.extendedGamepad {
            let stick = pad.leftThumbstick
            if abs(stick.xAxis.value) > 0.2 || abs(stick.yAxis.value) > 0.2 {
                // Stick y is up-positive; world y is down-positive.
                move = Vec2(Double(stick.xAxis.value), -Double(stick.yAxis.value))
            }
            let aim = pad.rightThumbstick
            if abs(aim.xAxis.value) > 0.25 || abs(aim.yAxis.value) > 0.25 {
                usingGamepadAim = true
                gamepadAim = CGPoint(x: CGFloat(aim.xAxis.value),
                                     y: CGFloat(aim.yAxis.value))
            }
            if pad.rightTrigger.value > 0.25 || pad.rightShoulder.isPressed {
                state.firing = true
            }
            if pad.buttonA.isPressed { pendingDodge = true }
            if pad.buttonX.isPressed { pendingReload = true }
            if pad.buttonB.isPressed { pendingInteract = true }
            if pad.leftShoulder.isPressed { pendingBlank = true }
            if pad.buttonY.isPressed { pendingCycle = 1 }
        }
        #endif

        state.move = move.clampedLength(1)

        // Aim: a gamepad points from the player, a mouse points at a spot.
        let aimScene: CGPoint
        if usingGamepadAim {
            let length = max(1, hypot(gamepadAim.x, gamepadAim.y))
            aimScene = CGPoint(x: playerScenePoint.x + gamepadAim.x / length * 140,
                               y: playerScenePoint.y + gamepadAim.y / length * 140)
        } else {
            aimScene = aimScenePoint
        }
        // Scene space is y-up, world space is y-down.
        state.aim = Vec2(Double(aimScene.x), Double(-aimScene.y))

        state.dodgePressed = pendingDodge
        state.reloadPressed = pendingReload
        state.blankPressed = pendingBlank
        state.interactPressed = pendingInteract
        state.weaponCycle = pendingCycle
        state.weaponSelect = pendingSelect

        pendingDodge = false
        pendingReload = false
        pendingBlank = false
        pendingInteract = false
        pendingCycle = 0
        pendingSelect = nil

        return state
    }

    /// Menu navigation, separate from gameplay so a held fire button does not
    /// skip three screens in a row.
    func pollMenu() -> (confirm: Bool, back: Bool) {
        let confirm = pendingInteract || pendingDodge
        let back = pendingPause
        pendingInteract = false
        pendingDodge = false
        pendingPause = false
        pendingSelect = nil
        pendingCycle = 0
        return (confirm, back)
    }

    func consumeDirectionEdge() -> Int {
        // Menus step one entry per press rather than per frame.
        var step = 0
        if pressed.contains(Key.d) || pressed.contains(Key.right) { step += 1 }
        if pressed.contains(Key.a) || pressed.contains(Key.left) { step -= 1 }
        return step
    }
}
#endif
