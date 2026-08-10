import Foundation

public enum ResourceError: Error, CustomStringConvertible {
    case missing(String)
    case unreadable(String, underlying: Error)

    public var description: String {
        switch self {
        case .missing(let name):
            return "Ressource fehlt: \(name)"
        case .unreadable(let name, let error):
            return "Ressource unlesbar: \(name) - \(error)"
        }
    }
}

/// Zugriff auf die erzeugten Daten im Bundle.
public enum Resources {
    /// Ausweg fuer Umgebungen ohne Bundle (etwa Werkzeuge, die direkt im
    /// Arbeitsverzeichnis laufen).
    public static var overrideRoot: URL?

    public static func url(subdirectory: String, name: String, ext: String) throws -> URL {
        if let root = overrideRoot {
            let candidate = root
                .appendingPathComponent(subdirectory)
                .appendingPathComponent("\(name).\(ext)")
            if FileManager.default.fileExists(atPath: candidate.path) { return candidate }
        }
        if let url = Bundle.module.url(forResource: name, withExtension: ext, subdirectory: subdirectory) {
            return url
        }
        // SwiftPM legt `.copy`-Verzeichnisse als Ordner ab; je nach Plattform
        // greift die Unterverzeichnis-Suche nicht. Deshalb der zweite Versuch.
        let fallback = Bundle.module.bundleURL
            .appendingPathComponent(subdirectory)
            .appendingPathComponent("\(name).\(ext)")
        if FileManager.default.fileExists(atPath: fallback.path) { return fallback }
        throw ResourceError.missing("\(subdirectory)/\(name).\(ext)")
    }

    public static func decode<T: Decodable>(_ type: T.Type, subdirectory: String,
                                            name: String, ext: String = "json") throws -> T {
        let url = try url(subdirectory: subdirectory, name: name, ext: ext)
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ResourceError.unreadable("\(subdirectory)/\(name).\(ext)", underlying: error)
        }
    }
}

/// Laedt und puffert alle Raeume der Welt.
public final class WorldCatalog {
    public let index: WorldIndex
    private var cache: [String: Room] = [:]

    public init() throws {
        index = try Resources.decode(WorldIndex.self, subdirectory: "Levels", name: "index")
    }

    public var roomIDs: [String] { index.rooms.map(\.id) }

    public func entry(for id: String) -> WorldIndex.Entry? {
        index.rooms.first { $0.id == id }
    }

    /// Laedt einen Raum frisch (verwirft dabei den zwischengespeicherten Zustand).
    public func loadFresh(_ id: String) throws -> Room {
        let data = try Resources.decode(RoomData.self, subdirectory: "Levels", name: id)
        let room = Room(data: data)
        cache[id] = room
        return room
    }

    /// Gibt den Raum zurueck; behaelt zerschlagene Sperren zwischen Besuchen bei.
    public func room(_ id: String) throws -> Room {
        if let cached = cache[id] { return cached }
        return try loadFresh(id)
    }

    /// Vergisst alle Raumzustaende (neues Spiel).
    public func reset() {
        cache.removeAll()
    }

    /// Laedt jeden Raum einmal - fuer Pruefwerkzeuge und Tests.
    public func loadAll() throws -> [Room] {
        try roomIDs.map { try room($0) }
    }
}
