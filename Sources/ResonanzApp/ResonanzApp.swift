#if canImport(SwiftUI) && canImport(SpriteKit) && !os(Linux)
import Foundation
import SwiftUI
import SpriteKit
import ResonanzCore
#if os(macOS)
import AppKit
#else
import UIKit
#endif

/// Speichert den Spielstand neben den Einstellungen der App.
/// Gespeichert wird nur an einer Stimmgabel - das ist Teil des Spiels.
public enum SaveStore {
    private static let key = "resonanz.spielstand.v1"

    public static func load() -> SaveState {
        guard let data = UserDefaults.standard.data(forKey: key),
              let state = try? JSONDecoder().decode(SaveState.self, from: data),
              state.version == SaveState.currentVersion
        else {
            return SaveState()
        }
        return state
    }

    public static func save(_ state: SaveState) {
        guard let data = try? JSONEncoder().encode(state) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }

    public static func hasSave() -> Bool {
        UserDefaults.standard.data(forKey: key) != nil
    }

    public static func clear() {
        UserDefaults.standard.removeObject(forKey: key)
    }
}

/// Laedt eines der grossen Bilder aus Resources/Titel - Titelbild und
/// Intro-Tafeln liegen als ganze PNGs im Bundle, nicht im Atlas.
func tafelBild(_ name: String) -> Image? {
    guard let url = try? Resources.url(subdirectory: "Titel", name: name, ext: "png")
    else { return nil }
    #if os(macOS)
    guard let img = NSImage(contentsOf: url) else { return nil }
    return Image(nsImage: img)
    #else
    guard let img = UIImage(contentsOfFile: url.path) else { return nil }
    return Image(uiImage: img)
    #endif
}

/// Der Rahmen um die Buehne: Titel, dann (bei neuem Spiel) das Intro,
/// dann das Spiel.
public struct ResonanzView: View {
    private enum Schritt {
        case titel
        case intro
        case spiel
    }

    @State private var schritt: Schritt = .titel

    public init() {}

    public var body: some View {
        ZStack {
            Color(red: 0.02, green: 0.024, blue: 0.047).ignoresSafeArea()

            switch schritt {
            case .titel:
                TitleScreen(fortsetzenMoeglich: SaveStore.hasSave()) { neuBeginnen in
                    if neuBeginnen {
                        SaveStore.clear()
                        withAnimation(.easeInOut(duration: 0.6)) { schritt = .intro }
                    } else {
                        schritt = .spiel
                    }
                }
                .transition(.opacity)
            case .intro:
                IntroView { schritt = .spiel }
                    .transition(.opacity)
            case .spiel:
                SpriteView(scene: makeScene(),
                           options: [.ignoresSiblingOrder],
                           debugOptions: [])
                    .ignoresSafeArea()
            }
        }
        .preferredColorScheme(.dark)
    }

    private func makeScene() -> SKScene {
        let scene = GameScene()
        scene.size = GameScene.designSize
        scene.scaleMode = .aspectFit
        return scene
    }
}

/// Titelbild. Der Klang beginnt erst nach einer Eingabe - so wollen es
/// die Systeme, und es passt zur Welt: erst wenn jemand anfaengt, klingt sie.
struct TitleScreen: View {
    let fortsetzenMoeglich: Bool
    let onStart: (Bool) -> Void

    @State private var puls = false

    var body: some View {
        GeometryReader { geo in
            ZStack {
                // Das Bild: die Finsternis ueber der Welt, pixelgenau
                // skaliert. `interpolation(.none)` haelt die Kanten hart.
                if let bild = tafelBild("titel") {
                    bild
                        .interpolation(.none)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: geo.size.width, height: geo.size.height)
                        .clipped()
                        .ignoresSafeArea()
                }

                // Ein Schleier unten, damit Schrift und Tasten auf dem
                // Bild stehen koennen, ohne dass man es uebermalt.
                LinearGradient(
                    stops: [
                        .init(color: .clear, location: 0.0),
                        .init(color: .clear, location: 0.45),
                        .init(color: Color(red: 0.03, green: 0.02, blue: 0.06)
                            .opacity(0.85), location: 1.0),
                    ],
                    startPoint: .top, endPoint: .bottom)
                    .ignoresSafeArea()

                VStack(spacing: 0) {
                    Spacer()

                    Text("RESONANZ")
                        .font(.system(size: 44, weight: .thin, design: .monospaced))
                        .tracking(18)
                        .foregroundStyle(.white)
                        .shadow(color: Color(red: 0.5, green: 0.91, blue: 0.85)
                            .opacity(puls ? 0.75 : 0.35),
                                radius: puls ? 26 : 14)
                        .padding(.leading, 18)

                    Text("DIE LETZTE IHRER ART. DER WEG IN DEN KERNSCHATTEN.")
                        .font(.system(size: 10, design: .monospaced))
                        .tracking(3)
                        .foregroundStyle(.white.opacity(0.55))
                        .padding(.top, 12)

                    Spacer()

                    VStack(spacing: 12) {
                        if fortsetzenMoeglich {
                            TitleButton(title: "FORTSETZEN", betont: true) { onStart(false) }
                            TitleButton(title: "NEU BEGINNEN", betont: false) { onStart(true) }
                        } else {
                            TitleButton(title: "AUFBRECHEN", betont: true) { onStart(true) }
                        }
                    }

                    Text(steuerung)
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.35))
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                        .padding(.top, 26)

                    Text("MUSIK NACH J. S. BACH  ·  BWV 846 · 578 · 1068 · 565")
                        .font(.system(size: 8, design: .monospaced))
                        .tracking(1.5)
                        .foregroundStyle(.white.opacity(0.25))
                        .padding(.top, 16)
                        .padding(.bottom, 26)
                }
                .padding(.horizontal, 40)
            }
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 2.6).repeatForever(autoreverses: true)) {
                puls = true
            }
        }
    }

    private var steuerung: String {
        #if os(macOS)
        return """
        A D  BEWEGEN     W S  ZIELEN     LEERTASTE  SPRINGEN
        J  NAHKLANG      K  FERNKLANG    UMSCHALT  HERZSCHLAG
        """
        #else
        return "LINKE HAELFTE: STICK  ·  RECHTS: SPRUNG NAH FERN HERZ"
        #endif
    }
}

private struct TitleButton: View {
    let title: String
    let betont: Bool
    let action: () -> Void
    @State private var hover = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, design: .monospaced))
                .tracking(5)
                .foregroundStyle(.white.opacity(betont ? 1.0 : 0.75))
                .padding(.vertical, 12)
                .padding(.horizontal, 34)
                .background(Color.black.opacity(betont ? 0.4 : 0.25))
                .overlay(
                    Rectangle()
                        .stroke(Color(red: 0.5, green: 0.91, blue: 0.85)
                            .opacity(hover ? 0.9 : (betont ? 0.55 : 0.3)),
                                lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        #if os(macOS)
        .onHover { hover = $0 }
        #endif
    }
}

// MARK: - Das Intro

/// Fuenf Tafeln: warum sie die sichere Heimat verlaesst.
///
/// Der Text liegt nicht in den Bildern - er wird hier gesetzt, scharf
/// und austauschbar. Jede Beruehrung blaettert weiter; wer die
/// Geschichte kennt, kann sie ueberspringen.
struct IntroView: View {
    let onFinish: () -> Void

    private static let tafeln: [(bild: String, text: String)] = [
        ("intro_0", "ES GAB EINEN ORT, DER SICHER WAR.\nVERBORGEN UNTER DEM FELS.\nDIE LETZTEN IHRER ART."),
        ("intro_1", "DANN KAM DIE KRANKHEIT.\nDIE HUELLE, DIE UNS ZUSAMMENHAELT, BEKAM RISSE.\nWER SIE VERLIERT, VERLISCHT."),
        ("intro_2", "DIE ALTEN SAGTEN: BLEIB.\nABER BLEIBEN HIESS NUR:\nLANGSAMER VERLOESCHEN."),
        ("intro_3", "DIE ANTWORT LIEGT IM KERNSCHATTEN.\nWO DIE SONNE SCHWARZ STEHT.\nWO ER WARTET."),
        ("intro_4", "ALSO GING SIE."),
    ]

    @State private var index = 0
    @State private var sichtbar = false

    var body: some View {
        GeometryReader { geo in
            ZStack {
                Color.black.ignoresSafeArea()

                if let bild = tafelBild(Self.tafeln[index].bild) {
                    bild
                        .interpolation(.none)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: geo.size.width, height: geo.size.height)
                        .opacity(sichtbar ? 1 : 0)
                }

                VStack {
                    Spacer()
                    Text(Self.tafeln[index].text)
                        .font(.system(size: 12, design: .monospaced))
                        .tracking(2)
                        .lineSpacing(7)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.white.opacity(0.92))
                        .shadow(color: .black, radius: 6)
                        .padding(.bottom, 44)
                        .opacity(sichtbar ? 1 : 0)
                }

                VStack {
                    HStack {
                        Spacer()
                        Button("UEBERSPRINGEN") { onFinish() }
                            .font(.system(size: 9, design: .monospaced))
                            .tracking(2)
                            .foregroundStyle(.white.opacity(0.35))
                            .buttonStyle(.plain)
                            .padding(20)
                    }
                    Spacer()
                }
            }
            .contentShape(Rectangle())
            .onTapGesture { weiter() }
        }
        .onAppear {
            withAnimation(.easeIn(duration: 1.2)) { sichtbar = true }
        }
    }

    private func weiter() {
        guard index < Self.tafeln.count - 1 else {
            onFinish()
            return
        }
        withAnimation(.easeOut(duration: 0.35)) { sichtbar = false }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            index += 1
            withAnimation(.easeIn(duration: 0.8)) { sichtbar = true }
        }
    }
}
#endif
