import SwiftUI
import SceneKit

// Villa Nachtschatten - Oberflaeche.
// Interne Renderaufloesung: kleiner = groebere Pixel = mehr PS1.
// 0.35 waere PSX-Niveau, 0.68 ist der Kompromiss aus Kante und Lesbarkeit.
let kRenderScale: CGFloat = 0.5

struct ContentView: View {
    @StateObject private var game = GameController()

    var body: some View {
        ZStack {
            SceneKitView(controller: game)
                .ignoresSafeArea()
                .background(Color.black)

            VStack(spacing: 0) {
                header
                Spacer()
                if let t = game.toast { toastView(t) }
                if game.debugOn { debugPanel }
                if game.editMode {
                    if game.freeCam { flyPanel }
                    if game.wallMode { wallPanel } else { editorPanel }
                }
                controls
            }
            .padding(.horizontal, 22)
            .padding(.top, 10)
            .padding(.bottom, 26)

            if game.mapOpen {
                MapOverlay(rooms: game.rooms, px: game.mapX, pz: game.mapZ, floor: game.floorIdx) {
                    game.mapOpen = false
                }
                .transition(.opacity)
            }
            if game.journalOpen {
                JournalOverlay(docs: game.inventory.filter { $0.isDocument }) {
                    game.journalOpen = false
                }
            }
        }
        .animation(.easeInOut(duration: 0.18), value: game.mapOpen)
        .animation(.easeInOut(duration: 0.18), value: game.prompt)
    }

    // --- Kopfzeile: Titel, Raumname, Inventar, Karte ---
    private var header: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 3) {
                Text("VILLA NACHTSCHATTEN")
                    .font(.system(size: 14, weight: .light, design: .serif))
                    .tracking(3)
                    .foregroundColor(Color.red.opacity(0.55))
                Text(game.currentRoom.uppercased())
                    .font(.system(size: 10, weight: .regular, design: .serif))
                    .tracking(2)
                    .foregroundColor(.white.opacity(0.32))
            }
            Spacer()
            HStack(spacing: 8) {
                ForEach(game.inventory, id: \.self) { item in
                    Button { game.toggleEquip(item) } label: {
                        Image(systemName: item.symbol)
                            .font(.system(size: 15))
                            .foregroundColor(game.isActive(item) ? Color(red: 1.0, green: 0.85, blue: 0.55)
                                                                 : Color(white: 0.85))
                            .frame(width: 36, height: 36)
                            .background(Circle().fill(Color.black.opacity(0.45)))
                            .overlay(Circle().stroke(game.isActive(item) ? Color(red: 1.0, green: 0.8, blue: 0.4).opacity(0.9)
                                                                        : Color.white.opacity(0.18),
                                                     lineWidth: game.isActive(item) ? 1.8 : 1))
                    }
                }
                if game.inventory.contains(where: { $0.isDocument }) {
                    Button { game.journalOpen.toggle() } label: {
                        Image(systemName: "book.closed")
                            .font(.system(size: 15))
                            .foregroundColor(Color(white: 0.85))
                            .frame(width: 40, height: 40)
                            .background(Circle().fill(Color.black.opacity(0.45)))
                            .overlay(Circle().stroke(Color.white.opacity(0.22), lineWidth: 1))
                    }
                }
                if game.editMode {
                    Button { game.wallMode.toggle() } label: {
                        Image(systemName: game.wallMode ? "rectangle.split.3x1" : "chair.lounge")
                            .font(.system(size: 14))
                            .foregroundColor(Color(red: 0.6, green: 0.9, blue: 1.0))
                            .frame(width: 34, height: 34)
                            .background(Circle().fill(Color.black.opacity(0.45)))
                    }
                    Button {
                        if !game.freeCam { game.syncFreeCam() }
                        game.fcLift = 0
                        game.freeCam.toggle()
                    } label: {
                        Image(systemName: "video")
                            .font(.system(size: 14))
                            .foregroundColor(game.freeCam ? Color(red: 1.0, green: 0.85, blue: 0.4)
                                                          : Color(white: 0.55))
                            .frame(width: 34, height: 34)
                            .background(Circle().fill(Color.black.opacity(0.45)))
                    }
                }
                Button { game.editMode.toggle() } label: {
                    Image(systemName: "pencil.and.ruler")
                        .font(.system(size: 14))
                        .foregroundColor(game.editMode ? Color(red: 1.0, green: 0.85, blue: 0.4)
                                                       : Color(white: 0.55))
                        .frame(width: 34, height: 34)
                        .background(Circle().fill(Color.black.opacity(0.45)))
                }
                Button { game.debugOn.toggle() } label: {
                    Image(systemName: "ladybug")
                        .font(.system(size: 14))
                        .foregroundColor(game.debugOn ? Color(red: 1.0, green: 0.85, blue: 0.55)
                                                      : Color(white: 0.55))
                        .frame(width: 34, height: 34)
                        .background(Circle().fill(Color.black.opacity(0.45)))
                }
                Button { game.mapOpen.toggle() } label: {
                    Image(systemName: "map")
                        .font(.system(size: 16))
                        .foregroundColor(Color(white: 0.85))
                        .frame(width: 40, height: 40)
                        .background(Circle().fill(Color.black.opacity(0.45)))
                        .overlay(Circle().stroke(Color.white.opacity(0.22), lineWidth: 1))
                }
            }
        }
    }

    // --- Moebel-Editor: verschieben, drehen, hinzufuegen, ausgeben ---
    private var editorPanel: some View {
        VStack(spacing: 6) {
            Text(game.selectedFurniture.map {
                    "\($0 + 1)/\(furnitureList.count)  \(furnitureList[$0].kind)"
                 } ?? "nichts gewaehlt")
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(Color(red: 1.0, green: 0.88, blue: 0.5))
            HStack(spacing: 6) {
                editBtn("scope") { game.selectNearestFurniture() }
                editBtn("chevron.left") {
                    let n = furnitureList.count
                    if n > 0 { game.selectedFurniture = ((game.selectedFurniture ?? 0) - 1 + n) % n }
                }
                editBtn("chevron.right") {
                    let n = furnitureList.count
                    if n > 0 { game.selectedFurniture = ((game.selectedFurniture ?? -1) + 1) % n }
                }
                editBtn("rotate.left") { game.rotateFurniture(-15) }
                editBtn("rotate.right") { game.rotateFurniture(15) }
                editBtn("trash") { game.deleteFurniture() }
            }
            HStack(spacing: 6) {
                editBtn("arrow.left") { game.nudgeFurniture(dx: -0.1, dz: 0) }
                editBtn("arrow.right") { game.nudgeFurniture(dx: 0.1, dz: 0) }
                editBtn("arrow.up") { game.nudgeFurniture(dx: 0, dz: -0.1) }
                editBtn("arrow.down") { game.nudgeFurniture(dx: 0, dz: 0.1) }
                editBtn("square.and.arrow.down") { game.saveFurniture() }
                editBtn("doc.on.clipboard") { game.copyFurnitureToClipboard() }
                editBtn("arrow.uturn.backward") { game.resetFurniture() }
            }
            HStack(spacing: 6) {
                ForEach(["table", "chair", "sofa", "cabinet", "crate", "palm",
                         "stool", "barrel", "sack"], id: \.self) { k in
                    Button { game.addFurniture(k) } label: {
                        Text(k).font(.system(size: 9, design: .monospaced))
                            .foregroundColor(Color(white: 0.85))
                            .padding(.horizontal, 6).padding(.vertical, 4)
                            .background(RoundedRectangle(cornerRadius: 4)
                                .fill(Color.white.opacity(0.12)))
                    }
                }
            }
            HStack(spacing: 6) {
                ForEach(["books", "candle", "bottle", "vase", "bucket",
                         "lamp", "toolbox", "plantSmall", "sink"], id: \.self) { k in
                    Button { game.addFurniture(k) } label: {
                        Text(k).font(.system(size: 9, design: .monospaced))
                            .foregroundColor(Color(red: 0.75, green: 0.9, blue: 0.75))
                            .padding(.horizontal, 5).padding(.vertical, 4)
                            .background(RoundedRectangle(cornerRadius: 4)
                                .fill(Color.white.opacity(0.10)))
                    }
                }
            }
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.72)))
    }

    // --- Wand-Editor: ziehen, verlaengern, Luecken setzen ---
    private var wallPanel: some View {
        VStack(spacing: 6) {
            Text(game.selectedWall.map { i -> String in
                    let w = wallList[i]
                    return String(format: "Wand %d/%d  %@  %.1f m", i + 1, wallList.count,
                                  w.axis == "x" ? "quer" : "laengs", abs(w.a1 - w.a0))
                 } ?? "keine Wand gewaehlt")
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(Color(red: 0.6, green: 0.9, blue: 1.0))
            HStack(spacing: 6) {
                editBtn("scope") { game.selectNearestWall() }
                editBtn("chevron.left") {
                    let n = wallList.count
                    if n > 0 { game.selectedWall = ((game.selectedWall ?? 0) - 1 + n) % n }
                }
                editBtn("chevron.right") {
                    let n = wallList.count
                    if n > 0 { game.selectedWall = ((game.selectedWall ?? -1) + 1) % n }
                }
                editBtn("arrow.left.and.right") { game.toggleWallAxis() }
                editBtn("plus.rectangle") { game.addWall() }
                editBtn("trash") { game.deleteWall() }
            }
            HStack(spacing: 6) {
                Text("quer").font(.system(size: 9)).foregroundColor(Color(white: 0.6))
                editBtn("minus") { game.nudgeWall(-0.25) }
                editBtn("plus") { game.nudgeWall(0.25) }
                Text("Anfang").font(.system(size: 9)).foregroundColor(Color(white: 0.6))
                editBtn("arrow.left.to.line") { game.stretchWall(startEnd: true, -0.5) }
                editBtn("arrow.right.to.line") { game.stretchWall(startEnd: true, 0.5) }
                Text("Ende").font(.system(size: 9)).foregroundColor(Color(white: 0.6))
                editBtn("arrow.left.to.line") { game.stretchWall(startEnd: false, -0.5) }
                editBtn("arrow.right.to.line") { game.stretchWall(startEnd: false, 0.5) }
            }
            HStack(spacing: 6) {
                Text("Hoehe").font(.system(size: 9)).foregroundColor(Color(white: 0.6))
                editBtn("minus.circle") { game.wallHeight(-0.5) }
                editBtn("plus.circle") { game.wallHeight(0.5) }
                Text("Tuer").font(.system(size: 9)).foregroundColor(Color(white: 0.6))
                editBtn("rectangle.portrait") { game.wallGap(1.4) }
                editBtn("rectangle.portrait.fill") { game.wallGap(0) }
                editBtn("arrow.left") { game.slideGap(-0.4) }
                editBtn("arrow.right") { game.slideGap(0.4) }
                editBtn("square.and.arrow.down") { game.saveWalls() }
                editBtn("doc.on.clipboard") {
                    UIPasteboard.general.string = game.exportWalls()
                    game.say("Waende als Swift-Code kopiert.")
                }
            }
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.72)))
    }

    // --- Freie Kamera: umsehen ohne den Spieler zu bewegen ---
    private var flyPanel: some View {
        HStack(spacing: 6) {
            editBtn("arrow.turn.up.left") { game.turnCamera(-0.18, 0) }
            editBtn("arrow.turn.up.right") { game.turnCamera(0.18, 0) }
            editBtn("arrow.up.circle") { game.turnCamera(0, 0.14) }
            editBtn("arrow.down.circle") { game.turnCamera(0, -0.14) }
            editBtn("arrow.up.to.line") { game.fcLift = game.fcLift > 0 ? 0 : 1 }
            editBtn("arrow.down.to.line") { game.fcLift = game.fcLift < 0 ? 0 : -1 }
        }
        .padding(6)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.6)))
    }

    private func editBtn(_ sym: String, _ act: @escaping () -> Void) -> some View {
        Button(action: act) {
            Image(systemName: sym)
                .font(.system(size: 13))
                .foregroundColor(Color(white: 0.9))
                .frame(width: 32, height: 30)
                .background(RoundedRectangle(cornerRadius: 5).fill(Color.white.opacity(0.14)))
        }
    }

    // --- Messwerte zum Diagnostizieren von Kamera und Position ---
    private var debugPanel: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Button { game.setCartoon(!game.cartoon) } label: {
                    Text(game.cartoon ? "Cartoon" : "Realistisch")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(game.cartoon ? Color(red: 1.0, green: 0.85, blue: 0.5)
                                                      : Color(white: 0.8))
                        .padding(.horizontal, 7).padding(.vertical, 4)
                        .background(RoundedRectangle(cornerRadius: 4)
                            .fill(Color.white.opacity(0.14)))
                }
            }
            HStack(spacing: 8) {
                Image(systemName: "sun.max").font(.system(size: 12))
                    .foregroundColor(Color(white: 0.8))
                Slider(value: Binding(get: { Double(game.brightness) },
                                      set: { game.setBrightness(Float($0)) }),
                       in: 0.4...2.2)
                    .frame(width: 150)
                Text(String(format: "%.2f", game.brightness))
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(Color(white: 0.8))
            }
            debugText
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.6)))
    }

    private var debugText: some View {
        Text(game.debugText)
            .font(.system(size: 11, weight: .regular, design: .monospaced))
            .foregroundColor(Color(red: 0.6, green: 1.0, blue: 0.7))
    }

    // --- Fusszeile: Joystick und Aktionsknopf ---
    private var controls: some View {
        HStack(alignment: .bottom) {
            Joystick(value: Binding(get: { game.move }, set: { game.move = $0 }))
            Spacer()
            Button { game.dodge() } label: {
                Image(systemName: "figure.run")
                    .font(.system(size: 20))
                    .foregroundColor(Color(white: 0.9))
                    .frame(width: 64, height: 64)
                    .background(Circle().fill(Color.black.opacity(0.5)))
                    .overlay(Circle().stroke(Color.white.opacity(0.28), lineWidth: 1.2))
            }
            .padding(.trailing, 10)
            if game.equipped == .crowbar {
                Button { game.attack() } label: {
                    Image(systemName: "burst.fill")
                        .font(.system(size: 22))
                        .foregroundColor(Color(white: 0.92))
                        .frame(width: 74, height: 74)
                        .background(Circle().fill(Color.black.opacity(0.5)))
                        .overlay(Circle().stroke(Color.white.opacity(0.3), lineWidth: 1.2))
                }
                .padding(.trailing, 14)
            }
            if let p = game.prompt {
                Button { game.interact() } label: {
                    VStack(spacing: 5) {
                        Image(systemName: "hand.tap.fill").font(.system(size: 19))
                        Text(p)
                            .font(.system(size: 10, weight: .medium))
                            .multilineTextAlignment(.center)
                            .lineLimit(2)
                            .frame(width: 96)
                    }
                    .foregroundColor(Color(white: 0.92))
                    .frame(width: 118, height: 92)
                    .background(RoundedRectangle(cornerRadius: 18).fill(Color.black.opacity(0.5)))
                    .overlay(RoundedRectangle(cornerRadius: 18).stroke(Color.white.opacity(0.25), lineWidth: 1))
                }
            }
        }
    }

    private func toastView(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 13, design: .serif))
            .foregroundColor(Color(white: 0.88))
            .padding(.horizontal, 18).padding(.vertical, 11)
            .background(RoundedRectangle(cornerRadius: 10).fill(Color.black.opacity(0.62)))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.white.opacity(0.14), lineWidth: 1))
            .padding(.bottom, 16)
    }
}

// ===================== Karte =====================

struct MapOverlay: View {
    let rooms: [RoomInfo]
    let px: Float
    let pz: Float
    let floor: Int
    let close: () -> Void

    // Papierfarben: Tinte auf vergilbtem Bogen statt Linien auf Schwarz
    private let paper = Color(red: 0.87, green: 0.82, blue: 0.69)
    private let ink = Color(red: 0.24, green: 0.17, blue: 0.11)

    var body: some View {
        ZStack {
            Color.black.opacity(0.78).ignoresSafeArea()
                .onTapGesture { close() }
            VStack(spacing: 10) {
                Text("SANATORIUM NACHTSCHATTEN")
                    .font(.system(size: 13, weight: .semibold, design: .serif))
                    .tracking(4).foregroundColor(ink)
                Text(floor == 2 ? "— BADEHAUS —" : (floor == 1 ? "— OBERGESCHOSS —" : "— ERDGESCHOSS —"))
                    .font(.system(size: 10, weight: .regular, design: .serif))
                    .tracking(3).foregroundColor(ink.opacity(0.7))
                Canvas { ctx, size in draw(ctx, size) }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                Text("Zum Schliessen tippen")
                    .font(.system(size: 9, design: .serif)).foregroundColor(ink.opacity(0.45))
            }
            .padding(24)
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: 4).fill(paper)
                    // Vergilbung zu den Raendern, Falzlinien, ein alter Fleck
                    RoundedRectangle(cornerRadius: 4)
                        .fill(RadialGradient(colors: [.clear, ink.opacity(0.16)],
                                             center: .center, startRadius: 60, endRadius: 560))
                    Rectangle().fill(ink.opacity(0.08)).frame(width: 1.2)
                    Rectangle().fill(ink.opacity(0.06)).frame(height: 1.2)
                    Circle().stroke(ink.opacity(0.10), lineWidth: 7)
                        .frame(width: 90).offset(x: 120, y: -150)
                    RoundedRectangle(cornerRadius: 4).stroke(ink.opacity(0.55), lineWidth: 1.4)
                    RoundedRectangle(cornerRadius: 4).inset(by: 5)
                        .stroke(ink.opacity(0.30), lineWidth: 0.8)
                }
            )
            .padding(26)
            .rotationEffect(.degrees(-0.6))
            .shadow(color: .black.opacity(0.6), radius: 18, y: 8)
        }
    }

    private func draw(_ ctx: GraphicsContext, _ size: CGSize) {
        let b = MapData.bounds
        let worldW = CGFloat(b.x1 - b.x0), worldD = CGFloat(b.z1 - b.z0)
        let pad: CGFloat = 26
        let scale = min((size.width - pad * 2) / worldW, (size.height - pad * 2) / worldD)
        let offX = (size.width - worldW * scale) / 2
        let offY = (size.height - worldD * scale) / 2
        // -z liegt oben: Norden zeigt nach oben
        func sx(_ x: Float) -> CGFloat { offX + CGFloat(x - b.x0) * scale }
        func sy(_ z: Float) -> CGFloat { offY + CGFloat(z - b.z0) * scale }

        // Handgezeichnete Anmutung: Doppelstrich, Schraffur fuer Unbekanntes,
        // Raumnamen in Serifen - und nur die Etage, auf der man steht.
        let inkC = Color(red: 0.24, green: 0.17, blue: 0.11)
        for r in rooms where r.floor == floor {
            let rect = CGRect(x: sx(r.x0), y: sy(r.z0),
                              width: CGFloat(r.x1 - r.x0) * scale,
                              height: CGFloat(r.z1 - r.z0) * scale)
            let path = Path(rect)
            if r.visited {
                ctx.fill(path, with: .color(Color(red: 0.80, green: 0.73, blue: 0.58)))
                ctx.stroke(path, with: .color(inkC), lineWidth: 1.6)
                ctx.stroke(Path(rect.insetBy(dx: 2.5, dy: 2.5)),
                           with: .color(inkC.opacity(0.45)), lineWidth: 0.7)
                ctx.draw(Text(r.short.uppercased())
                            .font(.system(size: 7.5, weight: .medium, design: .serif))
                            .foregroundColor(inkC),
                         at: CGPoint(x: rect.midX, y: rect.midY))
            } else {
                ctx.stroke(path, with: .color(inkC.opacity(0.28)), lineWidth: 1)
                var hatch = Path()
                var hx = rect.minX - rect.height
                while hx < rect.maxX {
                    hatch.move(to: CGPoint(x: max(rect.minX, hx), y: min(rect.maxY, rect.minY + max(0, rect.minX - hx))))
                    hatch.addLine(to: CGPoint(x: min(rect.maxX, hx + rect.height), y: rect.minY + max(0, min(rect.height, rect.height - (hx + rect.height - rect.maxX)))))
                    hx += 9
                }
                // GraphicsContext ist ein Werttyp: fuer clip eine Kopie anlegen,
                // damit die Schraffur nur diesen Raum fuellt.
                var hctx = ctx
                hctx.clip(to: path)
                hctx.stroke(hatch, with: .color(inkC.opacity(0.12)), lineWidth: 0.7)
            }
        }
        // Spielerposition als Tintenkreuz
        let p = CGPoint(x: sx(px), y: sy(pz))
        var cross = Path()
        cross.move(to: CGPoint(x: p.x - 6, y: p.y - 6)); cross.addLine(to: CGPoint(x: p.x + 6, y: p.y + 6))
        cross.move(to: CGPoint(x: p.x + 6, y: p.y - 6)); cross.addLine(to: CGPoint(x: p.x - 6, y: p.y + 6))
        ctx.stroke(cross, with: .color(Color(red: 0.55, green: 0.12, blue: 0.10)), lineWidth: 2.4)
        ctx.stroke(Path(ellipseIn: CGRect(x: p.x - 9, y: p.y - 9, width: 18, height: 18)),
                   with: .color(Color(red: 0.55, green: 0.12, blue: 0.10).opacity(0.5)), lineWidth: 1.2)
    }
}

// ===================== SceneKit einbetten =====================

struct SceneKitView: UIViewRepresentable {
    let controller: GameController
    func makeUIView(context: Context) -> SCNView {
        let v = SCNView()
        v.scene = controller.scene
        v.pointOfView = controller.cameraNode
        v.delegate = controller
        v.isPlaying = true
        v.rendersContinuously = true
        v.backgroundColor = .black
        v.allowsCameraControl = false
        v.antialiasingMode = .none
        v.preferredFramesPerSecond = 30
        v.contentScaleFactor = kRenderScale
        v.layer.magnificationFilter = .nearest
        v.layer.minificationFilter = .nearest
        return v
    }
    func updateUIView(_ uiView: SCNView, context: Context) {
        if uiView.contentScaleFactor != kRenderScale {
            uiView.contentScaleFactor = kRenderScale
        }
    }
}

// ===================== Joystick =====================

struct Joystick: View {
    @Binding var value: CGVector
    @State private var knob = CGSize.zero
    let radius: CGFloat = 55
    var body: some View {
        ZStack {
            Circle().stroke(Color.white.opacity(0.2), lineWidth: 2)
            Circle().fill(Color.white.opacity(0.25))
                .frame(width: 50, height: 50)
                .offset(knob)
        }
        .frame(width: 120, height: 120)
        .contentShape(Circle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { g in
                    var dx = g.translation.width
                    var dy = g.translation.height
                    let dist = sqrt(dx * dx + dy * dy)
                    if dist > radius { dx = dx / dist * radius; dy = dy / dist * radius }
                    knob = CGSize(width: dx, height: dy)
                    value = CGVector(dx: dx / radius, dy: dy / radius)
                }
                .onEnded { _ in
                    knob = .zero
                    value = .zero
                }
        )
    }
}


// ===================== Journal =====================
// Gefundene Dokumente zum Nachlesen - gleiche Papieranmutung wie die Karte.
struct JournalOverlay: View {
    let docs: [ItemKind]
    let close: () -> Void
    private let paper = Color(red: 0.87, green: 0.82, blue: 0.69)
    private let ink = Color(red: 0.24, green: 0.17, blue: 0.11)

    var body: some View {
        ZStack {
            Color.black.opacity(0.78).ignoresSafeArea()
                .onTapGesture { close() }
            VStack(spacing: 12) {
                Text("AUFZEICHNUNGEN")
                    .font(.system(size: 13, weight: .semibold, design: .serif))
                    .tracking(4).foregroundColor(ink)
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        ForEach(docs, id: \.self) { d in
                            VStack(alignment: .leading, spacing: 5) {
                                Text(d.rawValue.uppercased())
                                    .font(.system(size: 11, weight: .semibold, design: .serif))
                                    .tracking(2).foregroundColor(ink)
                                Text(d.pickupText)
                                    .font(.system(size: 13, design: .serif))
                                    .foregroundColor(ink.opacity(0.85))
                                    .fixedSize(horizontal: false, vertical: true)
                                Rectangle().fill(ink.opacity(0.25)).frame(height: 1)
                            }
                        }
                    }
                    .padding(.horizontal, 6)
                }
                Text("Zum Schliessen tippen")
                    .font(.system(size: 9, design: .serif))
                    .foregroundColor(ink.opacity(0.45))
            }
            .padding(22)
            .frame(maxWidth: 520, maxHeight: 560)
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: 4).fill(paper)
                    RoundedRectangle(cornerRadius: 4).stroke(ink.opacity(0.55), lineWidth: 1.4)
                    RoundedRectangle(cornerRadius: 4).inset(by: 5)
                        .stroke(ink.opacity(0.30), lineWidth: 0.8)
                }
            )
            .rotationEffect(.degrees(0.5))
            .shadow(color: .black.opacity(0.6), radius: 18, y: 8)
        }
    }
}