import Foundation

/// Locates the generated art and audio in the iPad build.
///
/// Swift Playgrounds puts everything under `Resources` into the app bundle,
/// so the files sit flat in `Bundle.main` rather than in the nested
/// `generated/` layout the SwiftPM build uses. Same API either way, which is
/// why `Atlas` and `AudioMixer` are shared between the two builds unchanged.
enum GeneratedAssets {
    static var bundle: Bundle { Bundle.main }

    static var manifestURL: URL? {
        bundle.url(forResource: "game", withExtension: "json")
    }

    static func pageURL(named file: String) -> URL? {
        let name = (file as NSString).deletingPathExtension
        let ext = (file as NSString).pathExtension
        return bundle.url(forResource: name, withExtension: ext)
    }

    static func soundURLs() -> [URL] {
        bundle.urls(forResourcesWithExtension: "wav", subdirectory: nil) ?? []
    }

    static var isBuilt: Bool { manifestURL != nil }
}
