#if canImport(SwiftUI) && canImport(SpriteKit) && !os(Linux)
import Foundation
import SwiftUI
import SpriteKit
import ResonanzCore

/// Speichert den Spielstand neben den Einstellungen der App.
/// Gespeichert wird nur an einer Stimmgabel - das ist Teil des Spiels.
public enum SaveStore {
    private static let key = "resonanz.spielstand.v1"

    public static func load() -> SaveState {
        guard let data = UserDefaults.standard.data(forKey: key),
              let state = try? JSONDecoder().decode(SaveState.self, from: data),
              state.version == SaveState.currentVersion
        else {
            return SaveState()
        }
        return state
    }

    public static func save(_ state: SaveState) {
        guard let data = try? JSONEncoder().encode(state) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }

    public static func hasSave() -> Bool {
        UserDefaults.standard.data(forKey: key) != nil
    }

    public static func clear() {
        UserDefaults.standard.removeObject(forKey: key)
    }
}

/// Der Rahmen um die Buehne: Titelbild, dann das Spiel.
public struct ResonanzView: View {
    @State private var gestartet = false

    public init() {}

    public var body: some View {
        ZStack {
            Color(red: 0.02, green: 0.024, blue: 0.047).ignoresSafeArea()

            if gestartet {
                SpriteView(scene: makeScene(),
                           options: [.ignoresSiblingOrder],
                           debugOptions: [])
                    .ignoresSafeArea()
            } else {
                TitleScreen(fortsetzenMoeglich: SaveStore.hasSave()) { neuBeginnen in
                    if neuBeginnen { SaveStore.clear() }
                    gestartet = true
                }
            }
        }
        .preferredColorScheme(.dark)
    }

    private func makeScene() -> SKScene {
        let scene = GameScene()
        scene.size = GameScene.designSize
        scene.scaleMode = .aspectFit
        return scene
    }
}

/// Titelbild. Der Klang beginnt erst nach einer Eingabe - so wollen es
/// die Systeme, und es passt zur Welt: erst wenn jemand anfaengt, klingt sie.
struct TitleScreen: View {
    let fortsetzenMoeglich: Bool
    let onStart: (Bool) -> Void

    @State private var puls = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Text("RESONANZ")
                .font(.system(size: 46, weight: .thin, design: .monospaced))
                .tracking(18)
                .foregroundStyle(.white)
                .shadow(color: Color(red: 0.5, green: 0.91, blue: 0.85).opacity(puls ? 0.75 : 0.35),
                        radius: puls ? 26 : 14)
                .padding(.leading, 18)

            Text("DIE WELT IST VERSTIMMT. BRING SIE ZUM KLINGEN.")
                .font(.system(size: 11, design: .monospaced))
                .tracking(3)
                .foregroundStyle(.white.opacity(0.45))
                .padding(.top, 14)

            Spacer()

            VStack(spacing: 14) {
                if fortsetzenMoeglich {
                    TitleButton(title: "FORTSETZEN") { onStart(false) }
                }
                TitleButton(title: fortsetzenMoeglich ? "NEU BEGINNEN" : "SPIEL BEGINNEN") {
                    onStart(true)
                }
            }

            Text(steuerung)
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(.white.opacity(0.3))
                .multilineTextAlignment(.center)
                .lineSpacing(4)
                .padding(.top, 34)

            Text("MUSIK NACH J. S. BACH  ·  BWV 846 · 578 · 1068 · 565")
                .font(.system(size: 8, design: .monospaced))
                .tracking(1.5)
                .foregroundStyle(.white.opacity(0.22))
                .padding(.top, 22)

            Spacer()
        }
        .padding(40)
        .onAppear {
            withAnimation(.easeInOut(duration: 2.6).repeatForever(autoreverses: true)) {
                puls = true
            }
        }
    }

    private var steuerung: String {
        #if os(macOS)
        return """
        A D  BEWEGEN     W S  ZIELEN     LEERTASTE  SPRINGEN
        J  NAHKLANG      K  FERNKLANG    UMSCHALT  HERZSCHLAG
        1 2 3  INSTRUMENT     F  ANSPRECHEN
        """
        #else
        return "BILDSCHIRMTASTEN ODER GAMEPAD"
        #endif
    }
}

private struct TitleButton: View {
    let title: String
    let action: () -> Void
    @State private var hover = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, design: .monospaced))
                .tracking(5)
                .foregroundStyle(.white.opacity(0.9))
                .padding(.vertical, 12)
                .padding(.horizontal, 34)
                .overlay(
                    Rectangle()
                        .stroke(Color(red: 0.5, green: 0.91, blue: 0.85)
                            .opacity(hover ? 0.9 : 0.35), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        #if os(macOS)
        .onHover { hover = $0 }
        #endif
    }
}
#endif
