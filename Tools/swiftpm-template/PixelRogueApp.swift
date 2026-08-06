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
            if let loadError {
                // The one failure worth a real message: the art did not load,
                // and a black screen would leave the player guessing.
                VStack(spacing: 12) {
                    Text("Pixel Rogue could not load its art")
                        .font(.headline)
                    Text(loadError)
                        .font(.system(.footnote, design: .monospaced))
                        .multilineTextAlignment(.center)
                }
                .foregroundColor(.white)
                .padding(32)
            } else {
                SceneHost(onError: { loadError = $0 })
                    .ignoresSafeArea()
            }
        }
    }
}

private struct SceneHost: UIViewRepresentable {
    let onError: (String) -> Void

    func makeUIView(context: Context) -> SKView {
        let view = SKView()
        view.ignoresSiblingOrder = true      // lets zPosition drive draw order
        view.preferredFramesPerSecond = 60
        view.isMultipleTouchEnabled = true   // twin-stick needs both thumbs
        view.backgroundColor = .black
        return view
    }

    func updateUIView(_ view: SKView, context: Context) {
        // SwiftUI can call this before layout has given the view a size, and
        // a scene presented at zero size lays its HUD out off screen.
        guard view.scene == nil, view.bounds.width > 1, view.bounds.height > 1
        else { return }

        do {
            let atlas = try Atlas()
            let scene = GameScene(size: view.bounds.size, atlas: atlas)
            scene.scaleMode = .resizeFill
            view.presentScene(scene)
        } catch {
            DispatchQueue.main.async { onError("\(error)") }
        }
    }
}
