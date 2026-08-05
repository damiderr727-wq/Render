#if canImport(SpriteKit) && canImport(AppKit)
import AppKit
import SpriteKit

/// macOS shell. SwiftPM executables have no Info.plist and no nib, so the
/// window, menu bar and activation policy are all set up by hand here.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var skView: SKView!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let size = NSSize(width: 1280, height: 720)
        window = NSWindow(
            contentRect: NSRect(origin: .zero, size: size),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false)
        window.title = "Pixel Rogue"
        window.center()
        window.minSize = NSSize(width: 800, height: 480)
        window.backgroundColor = .black

        skView = SKView(frame: NSRect(origin: .zero, size: size))
        skView.autoresizingMask = [.width, .height]
        skView.ignoresSiblingOrder = true      // lets zPosition drive draw order
        skView.preferredFramesPerSecond = 60
        window.contentView = skView

        do {
            let atlas = try Atlas()
            let scene = GameScene(size: size, atlas: atlas)
            skView.presentScene(scene)
        } catch {
            presentLoadFailure(error)
            return
        }

        buildMenu()
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(skView)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool {
        true
    }

    /// The one failure worth a real message: the art has not been generated,
    /// and a black window would leave the player guessing.
    private func presentLoadFailure(_ error: Error) {
        let label = NSTextField(wrappingLabelWithString:
            "Pixel Rogue could not load its art.\n\n\(error)")
        label.frame = NSRect(x: 40, y: 40, width: 600, height: 200)
        label.isEditable = false
        label.alignment = .center
        label.textColor = .white
        let container = NSView(frame: NSRect(x: 0, y: 0, width: 680, height: 280))
        container.wantsLayer = true
        container.layer?.backgroundColor = NSColor.black.cgColor
        container.addSubview(label)
        window.contentView = container
        window.setContentSize(container.frame.size)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildMenu() {
        let mainMenu = NSMenu()
        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)

        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Pixel Rogue",
                        action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
                        keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Toggle Full Screen",
                        action: #selector(NSWindow.toggleFullScreen(_:)),
                        keyEquivalent: "f")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Pixel Rogue",
                        action: #selector(NSApplication.terminate(_:)),
                        keyEquivalent: "q")
        appMenuItem.submenu = appMenu
        NSApp.mainMenu = mainMenu
    }
}

let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()

#else

print("""
Pixel Rogue's renderer needs SpriteKit, so the playable build is macOS only.

The simulation itself is platform independent and does run here:
    swift test            # rules, generation and synergies

To generate the art on any platform:
    python3 Tools/pixelforge/build_assets.py --out Assets/generated
""")

#endif
