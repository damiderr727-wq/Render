import Foundation

/// Locates the generated art and audio in the iPad build.
///
/// Swift Playgrounds puts everything under `Resources` into the app bundle,
/// but exactly *where* depends on how SwiftPM decides to process the folder,
/// so every lookup tries the bundle root first and then the plausible
/// subdirectories. Guessing wrong here shows up as a blank screen with no
/// explanation, which is the worst possible failure to debug on a tablet.
///
/// Same API as the SwiftPM build's copy, which is why `Atlas` and
/// `AudioMixer` are shared between the two unchanged.
enum GeneratedAssets {
    static var bundle: Bundle { Bundle.main }

    private static let searchPaths: [String?] = [nil, "Resources", "generated"]

    private static func locate(_ name: String, _ ext: String) -> URL? {
        for path in searchPaths {
            if let url = bundle.url(forResource: name, withExtension: ext,
                                    subdirectory: path) {
                return url
            }
        }
        return nil
    }

    static var manifestURL: URL? { locate("game", "json") }

    static func pageURL(named file: String) -> URL? {
        let name = (file as NSString).deletingPathExtension
        let ext = (file as NSString).pathExtension
        return locate(name, ext)
    }

    static func soundURLs() -> [URL] {
        for path in searchPaths {
            let found = bundle.urls(forResourcesWithExtension: "wav",
                                    subdirectory: path) ?? []
            if !found.isEmpty { return found }
        }
        return []
    }

    static var isBuilt: Bool { manifestURL != nil }
}
