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

    /// Every generated .wav cue. Callers key off the file name, so the
    /// on-disk layout can differ per platform without them caring.
    ///
    /// Walks the directory rather than using `Bundle.urls(forResources…)`,
    /// whose signature differs between Darwin and corelibs Foundation.
    public static func soundURLs() -> [URL] {
        guard let directory = bundle.url(forResource: "sfx", withExtension: nil,
                                         subdirectory: "generated") else {
            return []
        }
        let contents = (try? FileManager.default.contentsOfDirectory(
            at: directory, includingPropertiesForKeys: nil)) ?? []
        return contents.filter { $0.pathExtension == "wav" }
    }

    /// True when the atlas has been generated. A fresh clone has the art
    /// committed, but a `git clean` does not, and failing with a clear
    /// message beats a black window.
    public static var isBuilt: Bool { manifestURL != nil }
}
