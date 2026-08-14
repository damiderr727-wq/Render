// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Resonanz",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
        .tvOS(.v16),
    ],
    products: [
        // Die Spiellogik ist plattformfrei und laesst sich ohne Apple-SDK bauen.
        .library(name: "ResonanzCore", targets: ["ResonanzCore"]),
        // Die Darstellungsschicht (SpriteKit, SwiftUI, AVAudioEngine).
        .library(name: "ResonanzApp", targets: ["ResonanzApp"]),
        // Prueft Raumgeometrie gegen die echte Spielphysik.
        .executable(name: "resonanz-check", targets: ["ResonanzCheck"]),
    ],
    targets: [
        .target(
            name: "ResonanzCore",
            resources: [
                .copy("Resources/Atlas"),
                .copy("Resources/Levels"),
                .copy("Resources/Scores"),
                .copy("Resources/Titel"),
            ]
        ),
        .target(
            name: "ResonanzApp",
            dependencies: ["ResonanzCore"]
        ),
        .executableTarget(
            name: "ResonanzCheck",
            dependencies: ["ResonanzCore"]
        ),
        .testTarget(
            name: "ResonanzCoreTests",
            dependencies: ["ResonanzCore"]
        ),
    ]
)
