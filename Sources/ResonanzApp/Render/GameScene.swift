#if canImport(SpriteKit) && !os(Linux)
import Foundation
import SpriteKit
import ResonanzCore

/// Die Buehne. Sie besitzt keine Spielregeln - sie zeigt nur, was die
/// Simulation entschieden hat, und gibt ihre Ereignisse an Klang und
/// Anzeige weiter.
public final class GameScene: SKScene {

    public static let designSize = CGSize(width: 512, height: 288)

    private var sim: GameSimulation!
    private let renderer = RoomRenderer()
    private let atlas = AtlasStore.shared
    private let hud = HUDNode()
    private let bestiarium = BestiariumNode()
    private let input = InputRouter()

    private let synth = SynthEngine()
    private var board: SoundBoard!
    private var music: MusicDirector!

    private let cameraNode = SKCameraNode()
    private var lastUpdate: TimeInterval = 0
    private var shake: Double = 0
    private var currentRoomID = ""
    private var playerState: PlayerState = .idle
    private var playerKern: Kern = .stimmgabel
    private var playerGarment = EquipmentCatalog.mantel.id

    private var playerNode = SKSpriteNode()
    /// Ihre Flamme an der Stimmgabel. Sie liegt still im Baum und wird
    /// nur sichtbar, wenn eine Einkehr laeuft.
    private var flammeNode = SKSpriteNode()
    private var bossNode: SKSpriteNode?
    private var enemyNodes: [Int: SKSpriteNode] = [:]
    private var projectileNodes: [SKSpriteNode] = []
    private var pickupNodes: [String: SKNode] = [:]
    private var hazardNodes: [SKShapeNode] = []
    /// Welches Bild eine Kreatur gerade zeigt - damit die Schleife nur
    /// dann neu gesetzt wird, wenn sich die Haltung wirklich aendert.
    private var enemyClip: [Int: String] = [:]
    private var bossClip = ""

    // MARK: - Aufbau

    public override func didMove(to view: SKView) {
        scaleMode = .aspectFit
        size = Self.designSize
        backgroundColor = SKColor(red: 0.02, green: 0.024, blue: 0.047, alpha: 1)
        view.preferredFramesPerSecond = 60
        view.ignoresSiblingOrder = false
        #if os(iOS) || os(tvOS)
        // Ohne das liefert die Sicht genau EINEN Finger. Laufen und
        // Springen zugleich war damit unmoeglich - der Daumen auf dem
        // Stick schluckte jede weitere Beruehrung. Das war der ganze
        // Grund, warum sich die Steuerung kaputt anfuehlte.
        view.isMultipleTouchEnabled = true
        #endif

        do {
            try atlas.loadAll()
            let catalog = try WorldCatalog()
            sim = try GameSimulation(catalog: catalog, save: SaveStore.load())
            music = MusicDirector(library: try ScoreLibrary())
        } catch {
            showFatal("\(error)")
            return
        }

        synth.start()
        board = SoundBoard(synth: synth)

        addChild(renderer.root)
        camera = cameraNode
        addChild(cameraNode)
        cameraNode.addChild(hud)
        hud.build(in: Self.designSize)
        cameraNode.addChild(bestiarium)
        bestiarium.build(in: Self.designSize)

        playerNode = atlas.sprite("cadence_stimmgabel_mantel_idle_0")
        playerNode.zPosition = 5
        renderer.layers.entities.addChild(playerNode)

        flammeNode = atlas.sprite("flamme_0")
        flammeNode.zPosition = 6
        flammeNode.alpha = 0
        flammeNode.isHidden = true
        if let loop = atlas.loop("flamme") { flammeNode.run(loop) }
        renderer.layers.entities.addChild(flammeNode)

        input.attach(to: view)

        #if os(iOS) || os(tvOS)
        let touchLayer = TouchControlLayer()
        touchLayer.build(in: Self.designSize)
        cameraNode.addChild(touchLayer)
        input.bind(touchLayer: touchLayer)
        #endif

        loadRoom(force: true)
    }

    private func showFatal(_ message: String) {
        let label = SKLabelNode(text: "FEHLER: \(message)")
        label.fontName = "Menlo"
        label.fontSize = 10
        label.fontColor = .red
        label.position = CGPoint(x: size.width / 2, y: size.height / 2)
        label.numberOfLines = 4
        label.preferredMaxLayoutWidth = size.width - 40
        addChild(label)
    }

    // MARK: - Raum

    private func loadRoom(force: Bool = false) {
        guard force || sim.room.id != currentRoomID else { return }
        currentRoomID = sim.room.id

        renderer.build(room: sim.room)
        enemyNodes.values.forEach { $0.removeFromParent() }
        enemyNodes.removeAll()
        projectileNodes.forEach { $0.removeFromParent() }
        projectileNodes.removeAll()
        pickupNodes.values.forEach { $0.removeFromParent() }
        pickupNodes.removeAll()
        bossNode?.removeFromParent()
        bossNode = nil
        bossClip = ""
        enemyClip.removeAll()
        hazardNodes.forEach { $0.removeFromParent() }
        hazardNodes.removeAll()

        for pickup in sim.pickups {
            let name: String
            switch pickup.payload {
            case .kern(let kern): name = "sigil_\(kern.rawValue)"
            case .ability(let ability): name = "sigil_\(ability.rawValue)"
            case .equipment(let equipment): name = "sigil_\(equipment.id)"
            case .siegel(let siegel): name = "sigil_\(siegel.id)"
            case .klinge(let klinge): name = "sigil_klinge_\(klinge.id)"
            }
            let node = atlas.sprite(name)
            node.position = WorldSpace.scenePoint(pickup.position)
            node.zPosition = 6
            if let loop = atlas.loop(name) { node.run(loop) }
            node.run(.repeatForever(.sequence([
                .moveBy(x: 0, y: 3, duration: 1.1),
                .moveBy(x: 0, y: -3, duration: 1.1),
            ])))
            pickupNodes[pickup.key] = node
            renderer.layers.decor.addChild(node)
        }

        if let boss = sim.boss {
            let bild = "\(boss.art.rawValue)_idle"
            let node = atlas.sprite("\(bild)_0")
            node.zPosition = 7
            node.position = WorldSpace.scenePoint(boss.position)
            if let loop = atlas.loop(bild) { node.run(loop) }
            renderer.layers.entities.addChild(node)
            bossNode = node
        }

        hud.showRoomTitle(sim.room.name, region: sim.room.region.displayName)
        music.play(sim.musicTrack, now: synth.currentTime)
        cameraNode.position = WorldSpace.scenePoint(sim.cameraTarget)
    }

    // MARK: - Bild pro Bild

    public override func update(_ currentTime: TimeInterval) {
        guard sim != nil else { return }
        if lastUpdate == 0 { lastUpdate = currentTime }
        // Grosse Spruenge (App war im Hintergrund) nicht nachholen.
        let dt = min(1.0 / 30.0, max(0.0001, currentTime - lastUpdate))
        lastUpdate = currentTime

        let eingabe = input.snapshot()

        // Das Bestiarium haelt das Spiel an. Es ist kein Menue neben dem
        // Spiel, sondern ein Blick in etwas, das die Figur mit sich
        // fuehrt - und dabei laeuft die Welt nicht weiter.
        if eingabe.bestiariumPressed {
            bestiarium.toggle(save: sim.save)
            board.play(.pickup)
        }
        if bestiarium.offen {
            // aimY ist die senkrechte Achse der Steuerung: hoch ist
            // negativ, also blaettert hoch nach oben in der Liste.
            if eingabe.aimY != 0 {
                bestiarium.blaettern(eingabe.aimY > 0 ? 1 : -1, save: sim.save)
            }
            input.endFrame()
            return
        }

        let events = sim.update(dt: dt, input: eingabe)
        input.endFrame()

        handle(events: events)
        syncPlayer()
        syncEnemies()
        syncBoss()
        syncProjectiles()
        syncPickups()
        updateCamera(dt: dt)
        pumpMusic(dt: dt)
        hud.update(sim: sim, dt: dt)
    }

    private func handle(events: [GameEvent]) {
        for event in events {
            switch event {
            case .sound(let cue):
                board.play(cue)

            case .effect(let kind, let position, _):
                spawnEffect(kind, at: position)

            case .shake(let amount):
                shake = max(shake, amount)

            case .wallsBroken(_, let tiles):
                for (tx, ty) in tiles { renderer.breakTile(room: sim.room, tx: tx, ty: ty) }

            case .roomChanged:
                loadRoom()

            case .musicChanged(let track, _):
                music.play(track, now: synth.currentTime)

            case .bestiariumEintrag(let eintrag):
                hud.announce(eintrag.name,
                             subtitle: "BESTIARIUM - EINTRAG VOLLSTAENDIG",
                             lore: eintrag.deutung.joined(separator: " "))

            case .kernPicked(let kern):
                hud.announce(kern.displayName, subtitle: kern.summary,
                             lore: kern.loreLine)

            case .abilityPicked(let ability):
                hud.announce(ability.displayName, subtitle: ability.summary,
                             lore: ability.loreLine)

            case .equipmentFound(let equipment):
                hud.announce(equipment.name, subtitle: equipment.summary,
                             lore: equipment.flavour)

            case .equipmentWorn(let equipment):
                hud.showHint("\(equipment.name) - \(equipment.summary)")

            case .siegelFound(let siegel):
                hud.announce(siegel.name,
                             subtitle: "\(siegel.kerben) KERBEN - \(siegel.summary)",
                             lore: siegel.flavour)

            case .siegelWorn(let siegel, let angelegt):
                hud.showHint(angelegt ? "\(siegel.name) ANGELEGT" : "\(siegel.name) ABGELEGT")

            case .klingeFound(let klinge):
                hud.announce(klinge.name, subtitle: "SIE SCHLAEGT WIE JEDE ANDERE",
                             lore: klinge.flavour)

            case .kernSwitched:
                hud.flashKern()

            case .loreRead(let text):
                hud.showLore(text)

            case .gateHint(let ability):
                hud.showHint("HIER FEHLT: \(ability.displayName)")

            case .bruch:
                hud.announce("DER BRUCH",
                             subtitle: "SIE FAEHRT AUS IHRER FASSUNG",
                             lore: "DAS GEFAESS HAELT NICHT MEHR, UND DER KERN "
                                 + "AUCH NICHT. WAS JETZT KLINGT, KLINGT IN ALLE "
                                 + "RICHTUNGEN - UND ES ZIEHT DICH AUS.")

            case .bossPhaseChanged(let phase):
                bossNode?.removeAllActions()
                let name = phase >= 3 ? "kantor_rage" : "kantor_idle"
                if let loop = atlas.loop(name) { bossNode?.run(loop) }

            case .gameCompleted:
                hud.announce("DIE WELT KLINGT WIEDER",
                             subtitle: "DANK FUER DAS SPIELEN",
                             lore: "MUSIK NACH J. S. BACH - BWV 846, 578, 1068, 565")

            case .benchRested:
                SaveStore.save(sim.snapshotSave())
                hud.showHint("GESPEICHERT")

            default:
                break
            }
        }
    }

    // MARK: - Figuren

    private func syncPlayer() {
        let player = sim.player
        playerNode.position = WorldSpace.scenePoint(player.position)
        playerNode.xScale = player.facing >= 0 ? 1 : -1

        // Nach dem Bruch gibt es nur noch ein Bild: kein Gefaess, kein
        // heiler Kern. Deshalb faellt auch der Kernname darauf zurueck.
        let gebrochen = sim.save.progression.gebrochen
        let garment = gebrochen ? "bruch" : sim.save.progression.equipment.id
        if player.state != playerState || player.kern != playerKern
            || garment != playerGarment {
            playerState = player.state
            playerKern = player.kern
            playerGarment = garment
            let name = "cadence_\(gebrochen ? "bruch" : player.kern.rawValue)_\(garment)_"
                     + animationName(for: player.state)
            playerNode.removeAllActions()
            if let info = atlas.frame(name) {
                playerNode.texture = info.texture
                playerNode.size = info.size
                playerNode.anchorPoint = info.anchor
            }
            if let loop = atlas.loop(name) { playerNode.run(loop) }
        }

        // Waehrend der Unverwundbarkeit blinkt die Figur.
        if player.isDead {
            playerNode.alpha = 0.4
        } else if player.invulnerable > 0 {
            playerNode.alpha = Int(sim.elapsed * 20) % 2 == 0 ? 0.35 : 1.0
        } else {
            playerNode.alpha = 1.0
        }

        // Die Einkehr: die Gestalt verliert sich, die Flamme steigt.
        //
        // Beides blendet ueber denselben Anteil, damit es ein Vorgang
        // bleibt und nicht zwei. Die Flamme sitzt mit ihrem Fuss auf der
        // Gabel - der Ursprung ihres Bildes liegt unten - und steigt von
        // dort aus auf.
        let anteil = sim.einkehr.flammenanteil
        if sim.einkehr.aktiv {
            flammeNode.isHidden = false
            flammeNode.alpha = anteil
            let hoch = sim.einkehr.schwebe * 20
            flammeNode.position = CGPoint(x: playerNode.position.x,
                                          y: playerNode.position.y + hoch + 4)
            playerNode.alpha *= max(0, 1 - anteil * 1.25)
        } else if !flammeNode.isHidden {
            flammeNode.isHidden = true
            flammeNode.alpha = 0
        }
    }

    private func animationName(for state: PlayerState) -> String {
        switch state {
        case .idle: return "idle"
        case .run: return "run"
        case .jump: return "jump"
        case .fall: return "fall"
        case .wallSlide: return "wall"
        case .dash: return "dash"
        case .melee:
            // Nach oben und nach unten hat der Schlag eigene Bilder.
            // Vorher lief immer der Seitwaertsschnitt, waehrend der
            // Gegner ueber ihr starb.
            if sim.player.aimY < -0.5 { return "melee_up" }
            if sim.player.aimY > 0.5 { return "melee_down" }
            return "melee"
        case .cast: return "cast"
        case .hurt, .dead: return "hurt"
        case .slam: return "fall"
        case .rest: return "rest"
        }
    }

    private func syncEnemies() {
        var lebend: Set<Int> = []
        for enemy in sim.enemies {
            lebend.insert(enemy.id)
            let node: SKSpriteNode
            if let existing = enemyNodes[enemy.id] {
                node = existing
            } else {
                node = atlas.sprite(spriteName(for: enemy))
                node.zPosition = 4
                renderer.layers.entities.addChild(node)
                enemyNodes[enemy.id] = node
            }

            // Haltung gewechselt? Dann anderes Bild - aber nur dann, sonst
            // faengt die Schleife jedes Bild von vorn an und steht still.
            let name = spriteName(for: enemy)
            if enemyClip[enemy.id] != name {
                enemyClip[enemy.id] = name
                node.removeAllActions()
                node.texture = atlas.sprite(name).texture
                if let loop = atlas.loop(name) { node.run(loop) }
            }
            node.position = WorldSpace.scenePoint(enemy.position)
            node.xScale = enemy.facing >= 0 ? 1 : -1
            node.colorBlendFactor = enemy.hitFlash > 0 ? 0.8 : 0
            node.color = .white
        }
        for (id, node) in enemyNodes where !lebend.contains(id) {
            node.removeFromParent()
            enemyNodes.removeValue(forKey: id)
            enemyClip.removeValue(forKey: id)
        }
    }

    /// Welches Bild eine Kreatur gerade braucht.
    ///
    /// Nicht nur die Art entscheidet, sondern was sie tut: der Schreiter
    /// geht anders, wenn er gleich losstuermt, und die Knospe reisst auf,
    /// bevor sie schiesst. Wer keine Pose fuer eine Haltung hat, behaelt
    /// seine gewoehnliche - das ist der Rueckfall, nicht ein Fehler.
    private func spriteName(for enemy: Enemy) -> String {
        switch (enemy.kind, enemy.haltung) {
        case (.gabelmaus, .ruhe): return "gabelmaus_sitz"
        case (.gabelmaus, _): return "gabelmaus_husch"
        case (.stilleschreiter, .angriff): return "stilleschreiter_sturm"
        case (.stilleschreiter, _): return "stilleschreiter_walk"
        case (.dissonanzknospe, .angriff): return "dissonanzknospe_spucken"
        case (.dissonanzknospe, _): return "dissonanzknospe_bloom"
        case (.klangmotte, _): return "klangmotte_fly"
        case (.echoscherbe, _): return "echoscherbe_spin"
        case (.chorschatten, .ruhe): return "chorschatten_haengt"
        case (.chorschatten, _): return "chorschatten_faellt"
        case (.hallqualle, _): return "hallqualle_treibt"
        case (.steinfink, .angriff): return "steinfink_stoss"
        case (.steinfink, _): return "steinfink_hockt"
        case (.zerrmaul, .angriff): return "zerrmaul_schnappt"
        case (.zerrmaul, _): return "zerrmaul_wartet"
        case (.taumler, .angriff): return "taumler_ansturm"
        case (.taumler, _): return "taumler_taumelt"
        }
    }

    /// Und dasselbe fuer den Boss: er zeigt, was er vorhat.
    private func spriteName(for boss: Boss) -> String {
        switch boss.action {
        case .schattenwurf: return "\(boss.art.rawValue)_schatten"
        case .summon where boss.art == .hallwaechter: return "hallwaechter_ruf"
        case .chord, .sweep: return "\(boss.art.rawValue)_schlag"
        case .hover, .entrance: return "\(boss.art.rawValue)_idle"
        default: return "\(boss.art.rawValue)_aufschwung"
        }
    }

    private func syncBoss() {
        guard let boss = sim.boss, let node = bossNode else { return }

        // Der Boss zeigt, was er vorhat. Das ist bei ihm nicht Schmuck,
        // sondern die halbe Aufgabe: wer die Ansage liest, gewinnt.
        let name = spriteName(for: boss)
        if bossClip != name {
            bossClip = name
            node.removeAllActions()
            node.texture = atlas.sprite(name).texture
            if let loop = atlas.loop(name) { node.run(loop) }
        }
        node.position = WorldSpace.scenePoint(boss.position)
        node.xScale = boss.facing >= 0 ? 1 : -1
        node.colorBlendFactor = boss.hitFlash > 0 ? 0.7 : 0
        node.color = .white
        node.alpha = boss.alive ? 1 : max(0, node.alpha - 0.02)

        // Angekuendigte Gefahrenzonen: erst leuchten, dann treffen.
        while hazardNodes.count < boss.hazards.count {
            let shape = SKShapeNode(rectOf: CGSize(width: 20, height: 70))
            shape.lineWidth = 1
            shape.zPosition = 8
            renderer.layers.effects.addChild(shape)
            hazardNodes.append(shape)
        }
        for (index, node) in hazardNodes.enumerated() {
            guard index < boss.hazards.count else {
                node.isHidden = true
                continue
            }
            let hazard = boss.hazards[index]
            node.isHidden = false
            let rect = hazard.rect
            node.path = CGPath(rect: CGRect(x: -rect.width / 2, y: -rect.height / 2,
                                            width: rect.width, height: rect.height),
                               transform: nil)
            node.position = WorldSpace.scenePoint(rect.center)
            if hazard.isWarning {
                node.strokeColor = SKColor(red: 1, green: 0.75, blue: 0.4, alpha: 0.9)
                node.fillColor = SKColor(red: 1, green: 0.6, blue: 0.3,
                                         alpha: CGFloat(0.1 + 0.2 * hazard.warningProgress))
            } else {
                node.strokeColor = SKColor(red: 1, green: 0.95, blue: 0.85, alpha: 1)
                node.fillColor = SKColor(red: 0.95, green: 0.4, blue: 0.5, alpha: 0.65)
            }
        }
    }

    private func syncProjectiles() {
        while projectileNodes.count < sim.projectiles.count {
            let node = atlas.sprite("note_leier")
            node.zPosition = 9
            renderer.layers.effects.addChild(node)
            projectileNodes.append(node)
        }
        for (index, node) in projectileNodes.enumerated() {
            guard index < sim.projectiles.count else {
                node.isHidden = true
                continue
            }
            let projectile = sim.projectiles[index]
            node.isHidden = false
            if let info = atlas.frame(projectile.kind) {
                node.texture = info.texture
                node.size = info.size
                node.anchorPoint = info.anchor
            }
            node.position = WorldSpace.scenePoint(projectile.position)
            node.zRotation = CGFloat(atan2(-projectile.velocity.y, projectile.velocity.x))
        }
    }

    private func syncPickups() {
        let vorhanden = Set(sim.pickups.map(\.key))
        for (key, node) in pickupNodes where !vorhanden.contains(key) {
            node.run(.sequence([
                .group([.scale(to: 2.2, duration: 0.35), .fadeOut(withDuration: 0.35)]),
                .removeFromParent(),
            ]))
            pickupNodes.removeValue(forKey: key)
        }
    }

    // MARK: - Wirkung

    private func spawnEffect(_ kind: EffectKind, at position: Vec2) {
        let name: String
        switch kind {
        case .dust: name = "dust"
        case .feather: name = "feather"
        case .heartbeat: name = "heartbeat"
        case .burstGlow: name = "burst_glow"
        case .burstRot: name = "burst_rot"
        case .ringMittel: name = "ring_mittel"
        case .ringGross: name = "ring_gross"
        case .ringKlein: name = "ring_klein"
        // Wie der Schlagbogen aussieht, haengt an der gefuehrten Klinge -
        // nicht am Ereignis. Deshalb wird er hier erst nachgeschlagen.
        case .klingenschlag: name = sim.save.progression.klinge.effect
        case .mote: name = "mote"
        }
        let node = atlas.sprite("\(name)_0")
        node.position = WorldSpace.scenePoint(position)
        node.zPosition = 12
        node.blendMode = .add

        // Der Schlagbogen waechst mit der Kette. Das ist die Rueckmeldung
        // dort, wo man ohnehin hinsieht - die Anzeige oben links traegt
        // die Zahl, der Schlag selbst traegt das Gefuehl.
        if kind == .klingenschlag {
            let stufe = Double(sim.kette.glieder)
            node.setScale(1.0 + stufe * 0.11)
            node.alpha = 0.75 + stufe * 0.06
        }

        renderer.layers.effects.addChild(node)
        node.run(atlas.once(name))
    }

    // MARK: - Kamera

    private func updateCamera(dt: Double) {
        var target = WorldSpace.scenePoint(sim.cameraTarget)

        // Der Blick bleibt im Raum, damit man nie ins Leere schaut.
        let halfWidth = Self.designSize.width / 2
        let halfHeight = Self.designSize.height / 2
        let roomWidth = Double(sim.room.width) * tileSize
        let roomHeight = Double(sim.room.height) * tileSize
        if roomWidth > Double(halfWidth) * 2 {
            target.x = CGFloat(clamp(Double(target.x), Double(halfWidth), roomWidth - Double(halfWidth)))
        } else {
            target.x = CGFloat(roomWidth / 2)
        }
        if roomHeight > Double(halfHeight) * 2 {
            target.y = CGFloat(clamp(Double(target.y), -roomHeight + Double(halfHeight), -Double(halfHeight)))
        } else {
            target.y = CGFloat(-roomHeight / 2)
        }

        if shake > 0.02 {
            shake = max(0, shake - dt * 22)
            target.x += CGFloat.random(in: -CGFloat(shake)...CGFloat(shake))
            target.y += CGFloat.random(in: -CGFloat(shake)...CGFloat(shake))
        }

        cameraNode.position = target
        renderer.updateParallax(cameraPosition: target, dt: dt)
    }

    // MARK: - Musik

    private func pumpMusic(dt: Double) {
        music.targetIntensity = sim.musicIntensity
        for note in music.pull(now: synth.currentTime, dt: dt) {
            synth.schedule(note)
        }
    }
}
#endif
