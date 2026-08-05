// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "PixelRogue",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "PixelRogue", targets: ["PixelRogueApp"]),
        .library(name: "PixelRogueCore", targets: ["PixelRogueCore"]),
    ],
    targets: [
        // Pure Swift simulation: no SpriteKit, no AppKit, no Foundation-only
        // niceties that would tie it to one platform. Keeping it free of
        // Apple frameworks is what makes the rules testable in CI.
        .target(name: "PixelRogueCore"),

        // Generated art. A resource-only target needs one source file, hence
        // GeneratedAssets.swift.
        .target(
            name: "PixelRogueAssets",
            path: "Assets",
            resources: [.copy("generated")]
        ),

        // SpriteKit renderer and macOS shell. Every file is guarded with
        // `#if canImport(SpriteKit)` so the package still builds on Linux,
        // where only the core is meaningful.
        .executableTarget(
            name: "PixelRogueApp",
            dependencies: ["PixelRogueCore", "PixelRogueAssets"]
        ),

        // Headless renderer for CI and for looking at the game on a machine
        // without SpriteKit. Emits the same draw commands the real renderer
        // consumes, as JSON.
        .executableTarget(name: "PixelRogueSnapshot",
                          dependencies: ["PixelRogueCore"]),

        .testTarget(name: "PixelRogueCoreTests", dependencies: ["PixelRogueCore"]),
    ]
)
