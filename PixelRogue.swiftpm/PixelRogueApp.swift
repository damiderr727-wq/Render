import SwiftUI
import SpriteKit

/// SwiftUI entry point for the iPad build.
///
/// The macOS build has an AppKit shell that opens an NSWindow; on iPadOS
/// there is no window to open, so SwiftUI hosts an `SKView` filling the
/// screen and the same `GameScene` runs inside it.
@main
struct PixelRogueApp: App {
    var body: some Scene {
        WindowGroup {
            GameContainer()
                .ignoresSafeArea()
                .statusBarHidden()
                .background(Color.black)
        }
    }
}

struct GameContainer: View {
    @State private var loadError: String?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            SceneHost(onError: { loadError = $0 })
                .ignoresSafeArea()

            if let loadError {
                // The one failure worth a real message: the art did not load,
                // and a blank screen would leave the player guessing.
                VStack(spacing: 12) {
                    Text("Pixel Rogue could not load its art")
                        .font(.headline)
                    Text(loadError)
                        .font(.system(.footnote, design: .monospaced))
                        .multilineTextAlignment(.center)
                }
                .foregroundColor(.white)
                .padding(32)
                .background(Color.black.opacity(0.9))
            }
        }
    }
}

/// An `SKView` that presents the game the first time it is given a real size.
///
/// Presenting from `updateUIView` does not work: SwiftUI calls it once before
/// layout has assigned any bounds and then — with no state changing — never
/// calls it again, so the view sits there empty and SpriteKit draws its
/// default grey. Hooking `layoutSubviews` instead means the scene is created
/// at the exact moment a real size exists.
final class GameHostView: SKView {
    private var presented = false
    private var failed = false
    var onError: ((String) -> Void)?

    override func layoutSubviews() {
        super.layoutSubviews()
        guard !presented, !failed, bounds.width > 1, bounds.height > 1 else {
            return
        }
        do {
            let atlas = try Atlas()
            let scene = GameScene(size: bounds.size, atlas: atlas)
            scene.scaleMode = .resizeFill
            presentScene(scene)
            presented = true
        } catch {
            failed = true
            let message = "\(error)"
            // Never mutate SwiftUI state from inside a layout pass.
            DispatchQueue.main.async { [weak self] in self?.onError?(message) }
        }
    }
}

private struct SceneHost: UIViewRepresentable {
    let onError: (String) -> Void

    func makeUIView(context: Context) -> GameHostView {
        let view = GameHostView()
        view.ignoresSiblingOrder = true      // lets zPosition drive draw order
        view.preferredFramesPerSecond = 60
        view.isMultipleTouchEnabled = true   // twin-stick needs both thumbs
        view.backgroundColor = .black
        view.onError = onError
        return view
    }

    func updateUIView(_ view: GameHostView, context: Context) {
        view.onError = onError
    }
}
