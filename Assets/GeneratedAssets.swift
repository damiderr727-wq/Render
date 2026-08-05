import Foundation

/// Locates the generated atlas and manifest inside the resource bundle.
///
/// The art lives in `Assets/generated`, produced by
/// `Tools/pixelforge/build_assets.py`. Nothing here parses it — that is
/// `AtlasLoader`'s job in the app target — this type only answers "where".
public enum GeneratedAssets {
    public static var bundle: Bundle { Bundle.module }

    public static var manifestURL: URL? {
        bundle.url(forResource: "game", withExtension: "json",
                   subdirectory: "generated")
    }

    public static func pageURL(named file: String) -> URL? {
        let name = (file as NSString).deletingPathExtension
        let ext = (file as NSString).pathExtension
        return bundle.url(forResource: name, withExtension: ext,
                          subdirectory: "generated")
    }

    /// Directory holding the generated .wav cues, if they were built.
    public static var soundsURL: URL? {
        bundle.url(forResource: "sfx", withExtension: nil,
                   subdirectory: "generated")
    }

    /// True when the atlas has been generated. A fresh clone has the art
    /// committed, but a `git clean` does not, and failing with a clear
    /// message beats a black window.
    public static var isBuilt: Bool { manifestURL != nil }
}
