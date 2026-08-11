import Foundation

/// Was die Steuerung dem Spiel in einem Bild mitteilt. Die Kern-Bibliothek
/// kennt keine Tasten, kein Pad und keinen Bildschirm - nur Absichten.
public struct PlayerInput: Sendable, Equatable {
    /// -1 links, 0 nichts, +1 rechts (Zwischenwerte fuer Analogsticks erlaubt).
    public var moveX: Double
    /// -1 nach oben zielen, +1 nach unten.
    public var aimY: Double

    public var jumpHeld: Bool
    public var jumpPressed: Bool
    public var meleePressed: Bool
    public var rangedPressed: Bool
    public var dashPressed: Bool
    public var slamPressed: Bool
    public var interactPressed: Bool

    /// Direktwahl eines Instruments, sonst `nil`.
    public var selectKern: Kern?
    /// Durchschalten: -1 zurueck, +1 vor.
    public var cycleKern: Int
    /// Fassung wechseln - wirkt nur an der Stimmgabel.
    public var cycleEquipment: Int
    /// Siegel an dieser Stelle der Fundliste umschalten - nur an der Stimmgabel.
    public var toggleSiegel: Int?

    public init(moveX: Double = 0,
                aimY: Double = 0,
                jumpHeld: Bool = false,
                jumpPressed: Bool = false,
                meleePressed: Bool = false,
                rangedPressed: Bool = false,
                dashPressed: Bool = false,
                slamPressed: Bool = false,
                interactPressed: Bool = false,
                selectKern: Kern? = nil,
                cycleKern: Int = 0,
                cycleEquipment: Int = 0,
                toggleSiegel: Int? = nil) {
        self.moveX = moveX
        self.aimY = aimY
        self.jumpHeld = jumpHeld
        self.jumpPressed = jumpPressed
        self.meleePressed = meleePressed
        self.rangedPressed = rangedPressed
        self.dashPressed = dashPressed
        self.slamPressed = slamPressed
        self.interactPressed = interactPressed
        self.selectKern = selectKern
        self.cycleKern = cycleKern
        self.cycleEquipment = cycleEquipment
        self.toggleSiegel = toggleSiegel
    }

    public static let neutral = PlayerInput()

    /// Nur Halten, keine Flanken - praktisch fuer Tests und Pruefwerkzeuge.
    public static func holding(moveX: Double = 0, jump: Bool = false) -> PlayerInput {
        PlayerInput(moveX: moveX, jumpHeld: jump)
    }
}
