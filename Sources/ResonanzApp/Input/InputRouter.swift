#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

#if canImport(GameController)
import GameController
#endif

/// Sammelt Tastatur, Gamepad und Bildschirmtasten zu einer Absicht
/// zusammen. Die Spiellogik kennt nur `PlayerInput` - sie weiss nicht,
/// womit gespielt wird.
public final class InputRouter {

    /// Belegung auf der Tastatur.
    ///
    ///   Bewegen        A D / Pfeile
    ///   Zielen         W S / hoch runter
    ///   Springen       Leertaste, Z
    ///   Nahklang       J, X
    ///   Fernklang      K, C
    ///   Herzschlag     Umschalt, L
    ///   Basston        runter + Nahklang in der Luft
    ///   Kern     1 2 3, Q E
    ///   Ansprechen     F, Eingabe
    private struct Held {
        var left = false
        var right = false
        var up = false
        var down = false
        var jump = false
        var melee = false
        var ranged = false
        var dash = false
        var interact = false
    }

    private var held = Held()
    private var pressed = Held()
    /// Stufenlose Seitwaertsbewegung vom Stick oder Gamepad. Solange
    /// niemand stufenlos steuert, bleibt sie 0 und die Tasten zaehlen.
    private var analogX: Double = 0
    private var pendingKern: Kern?
    private var pendingCycle = 0
    private var pendingEquipmentCycle = 0
    private var pendingBestiarium = false
    private var pendingSiegel: Int?

    #if os(macOS)
    private var keyMonitor: Any?
    #endif

    public init() {}

    public func attach(to view: SKView) {
        #if os(macOS)
        attachKeyboard()
        #endif
        #if os(iOS) || os(tvOS)
        attachTouchControls(to: view)
        #endif
        attachGameController()
    }

    /// Der Zustand fuer dieses Bild.
    public func snapshot() -> PlayerInput {
        pollGameController()

        let moveX = analogX != 0
            ? analogX
            : (held.right ? 1.0 : 0) - (held.left ? 1.0 : 0)
        let aimY = (held.down ? 1.0 : 0) - (held.up ? 1.0 : 0)

        // Der Basston ist kein eigener Knopf: nach unten zielen und
        // in der Luft zuschlagen. Das haelt die Belegung schmal.
        let slam = held.down && pressed.melee

        return PlayerInput(
            moveX: moveX,
            aimY: aimY,
            jumpHeld: held.jump,
            jumpPressed: pressed.jump,
            // Runter + Nahklang ist zuerst ein SCHLAG nach unten - mit
            // Abpraller auf Gegnern und Dornen. Der Basston kommt erst
            // beim zweiten Tipp in denselben Schwung (siehe Player).
            // Vorher schluckte diese Weiche den Schlag ganz, und das
            // Pogo, das die Simulation laengst konnte, war unerreichbar.
            meleePressed: pressed.melee,
            rangedPressed: pressed.ranged,
            dashPressed: pressed.dash,
            slamPressed: slam,
            interactPressed: pressed.interact,
            selectKern: pendingKern,
            cycleKern: pendingCycle,
            cycleEquipment: pendingEquipmentCycle,
            toggleSiegel: pendingSiegel,
            bestiariumPressed: pendingBestiarium)
    }

    /// Nach dem Auswerten die Flanken loeschen.
    public func endFrame() {
        pressed = Held()
        pendingKern = nil
        pendingCycle = 0
        pendingEquipmentCycle = 0
        pendingSiegel = nil
        pendingBestiarium = false
    }

    private func set(_ keyPath: WritableKeyPath<Held, Bool>, _ value: Bool) {
        if value && !held[keyPath: keyPath] {
            pressed[keyPath: keyPath] = true
        }
        held[keyPath: keyPath] = value
    }

    // MARK: - Tastatur (macOS)

    #if os(macOS)
    private func attachKeyboard() {
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp, .flagsChanged]) {
            [weak self] event in
            guard let self else { return event }
            switch event.type {
            case .keyDown where !event.isARepeat:
                self.handleKey(event.keyCode, down: true)
                self.handleCharacter(event.charactersIgnoringModifiers)
                return nil
            case .keyUp:
                self.handleKey(event.keyCode, down: false)
                return nil
            case .flagsChanged:
                self.set(\.dash, event.modifierFlags.contains(.shift))
                return event
            default:
                return event
            }
        }
    }

    private func handleKey(_ code: UInt16, down: Bool) {
        switch code {
        case 0, 123: set(\.left, down)      // A, Pfeil links
        case 2, 124: set(\.right, down)     // D, Pfeil rechts
        case 13, 126: set(\.up, down)       // W, Pfeil hoch
        case 1, 125: set(\.down, down)      // S, Pfeil runter
        case 49, 6: set(\.jump, down)       // Leertaste, Z
        case 38, 7: set(\.melee, down)      // J, X
        case 40, 8: set(\.ranged, down)     // K, C
        case 37: set(\.dash, down)          // L
        case 3, 36: set(\.interact, down)   // F, Eingabe
        default: break
        }
    }

    private func handleCharacter(_ characters: String?) {
        switch characters {
        case "1": pendingKern = .leier
        case "2": pendingKern = .trommel
        case "3": pendingKern = .floete
        // Das Bestiarium - jederzeit, nicht nur an der Bank.
        case "b": pendingBestiarium = true
        case "q": pendingCycle = -1
        case "e": pendingCycle = 1
        // Fassung wechseln - wirkt nur an der Stimmgabel.
        case ",": pendingEquipmentCycle = -1
        case ".": pendingEquipmentCycle = 1
        // Siegel an- und ablegen, ebenfalls nur an der Stimmgabel.
        case "4", "5", "6", "7", "8", "9":
            pendingSiegel = Int(characters ?? "") .map { $0 - 4 }
        default: break
        }
    }
    #endif

    // MARK: - Bildschirmtasten (iOS)

    #if os(iOS) || os(tvOS)
    private weak var touchLayer: TouchControlLayer?

    private func attachTouchControls(to view: SKView) {
        // Die Bildschirmtasten legt die Szene an; hier wird nur gelesen.
    }

    public func bind(touchLayer: TouchControlLayer) {
        self.touchLayer = touchLayer
        touchLayer.onChange = { [weak self] state in
            guard let self else { return }
            // Der Stick ist stufenlos; die Flanken-Logik braucht trotzdem
            // links/rechts als Schwellen, und den feinen Wert traegt
            // `analogX` an der Verzweigung vorbei bis in `snapshot()`.
            self.analogX = state.moveX
            self.set(\.left, state.moveX < -0.01)
            self.set(\.right, state.moveX > 0.01)
            self.set(\.up, state.up)
            self.set(\.down, state.down)
            self.set(\.jump, state.jump)
            self.set(\.melee, state.melee)
            self.set(\.ranged, state.ranged)
            self.set(\.dash, state.dash)
            self.set(\.interact, state.interact)
        }
    }
    #endif

    // MARK: - Gamepad

    private func attachGameController() {
        #if canImport(GameController)
        GCController.startWirelessControllerDiscovery(completionHandler: nil)
        #endif
    }

    private func pollGameController() {
        #if canImport(GameController)
        guard let pad = GCController.controllers().first?.extendedGamepad else { return }
        let stick = pad.leftThumbstick
        set(\.left, stick.xAxis.value < -0.4 || pad.dpad.left.isPressed)
        set(\.right, stick.xAxis.value > 0.4 || pad.dpad.right.isPressed)
        set(\.up, stick.yAxis.value > 0.5 || pad.dpad.up.isPressed)
        set(\.down, stick.yAxis.value < -0.5 || pad.dpad.down.isPressed)
        set(\.jump, pad.buttonA.isPressed)
        set(\.melee, pad.buttonX.isPressed)
        set(\.ranged, pad.buttonY.isPressed)
        set(\.dash, pad.rightShoulder.isPressed || pad.rightTrigger.isPressed)
        set(\.interact, pad.buttonB.isPressed)
        if pad.leftShoulder.isPressed { pendingCycle = -1 }
        #endif
    }

    deinit {
        #if os(macOS)
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor) }
        #endif
    }
}

#if os(macOS)
import AppKit
#endif
#endif
