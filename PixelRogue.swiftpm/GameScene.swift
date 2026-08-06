#if canImport(SpriteKit)
import Foundation
import SpriteKit

#if canImport(AppKit)
import AppKit
#endif

/// The whole presentation layer: camera, screen effects, menus, and the loop
/// that drives the simulation and mirrors it into nodes.
final class GameScene: SKScene {

    enum Mode {
        case title
        case characterSelect
        case playing
        case paused
        case dead
        case victory
    }

    // -- configuration --------------------------------------------------------

    /// Integer zoom keeps every source pixel square on screen. Anything
    /// fractional makes 1px outlines shimmer as the camera moves.
    private let zoom: CGFloat = 3

    private let atlas: Atlas
    private let font: BitmapFont
    private let input = InputController()
    #if canImport(AVFoundation)
    private let audio = AudioMixer()
    #endif
    private var renderer: WorldRenderer!
    private var hud: HUD!

    private var world: World?
    private var mode: Mode = .title
    private var seed: UInt64 = 0
    private var characterIndex = 0

    private let cameraNode = SKCameraNode()
    private var overlay = SKNode()
    private var vignette: SKSpriteNode?
    private var damageFlash: SKSpriteNode?
    private var exitMarker: SKSpriteNode?
    #if canImport(UIKit)
    private var touchControls: TouchControls!
    /// Aim persists when the thumb leaves the stick, so the character keeps
    /// facing where you last pointed instead of snapping back.
    private var lastTouchAim = Vec2(1, 0)
    #endif

    private var lastUpdate: TimeInterval = 0
    private var hitStop: TimeInterval = 0
    private var trauma: Double = 0
    private var menuCooldown: TimeInterval = 0
    private var transitioning = false
    /// Set by the on-screen pause button; consumed by the next update.
    private var pendingTouchPause = false

    // -- setup ----------------------------------------------------------------

    init(size: CGSize, atlas: Atlas) {
        self.atlas = atlas
        self.font = BitmapFont(atlas: atlas)
        super.init(size: size)
        scaleMode = .resizeFill
        backgroundColor = SKColor(red: 0.03, green: 0.03, blue: 0.05, alpha: 1)
    }

    required init?(coder: NSCoder) { fatalError("not supported") }

    override func didMove(to view: SKView) {
        renderer = WorldRenderer(atlas: atlas)
        hud = HUD(atlas: atlas, font: font)

        addChild(renderer.root)
        camera = cameraNode
        addChild(cameraNode)
        cameraNode.setScale(1 / zoom)
        cameraNode.addChild(hud.root)
        cameraNode.addChild(overlay)
        overlay.zPosition = 200_000

        #if canImport(UIKit)
        touchControls = TouchControls(atlas: atlas, font: font)
        cameraNode.addChild(touchControls.root)
        isUserInteractionEnabled = true
        #endif

        buildScreenEffects()
        showTitle()

        #if canImport(AppKit)
        view.window?.acceptsMouseMovedEvents = true
        view.window?.makeFirstResponder(view)
        #endif
    }

    private func buildScreenEffects() {
        let vignetteNode = SKSpriteNode(frame: atlas.frame("ui/vignette"))
        vignetteNode.zPosition = 90_000
        vignetteNode.alpha = 0.75
        cameraNode.addChild(vignetteNode)
        vignette = vignetteNode

        let flash = SKSpriteNode(frame: atlas.frame("ui/damage_flash"))
        flash.zPosition = 95_000
        flash.alpha = 0
        cameraNode.addChild(flash)
        damageFlash = flash

        layoutScreenEffects()
    }

    private func layoutScreenEffects() {
        // Screen-space overlays are stretched from a small texture; nearest
        // filtering would make the gradient banded, so these two are the only
        // sprites in the game allowed to interpolate.
        let visible = CGSize(width: size.width / zoom + 4, height: size.height / zoom + 4)
        vignette?.size = visible
        vignette?.texture?.filteringMode = .linear
        damageFlash?.size = visible
        damageFlash?.texture?.filteringMode = .linear
        hud?.layout(for: visible)
        #if canImport(UIKit)
        touchControls?.layout(for: visible)
        #endif
    }

    override func didChangeSize(_ oldSize: CGSize) {
        super.didChangeSize(oldSize)
        layoutScreenEffects()
    }

    // -- run lifecycle --------------------------------------------------------

    private func startRun(seed: UInt64, character: CharacterDef) {
        self.seed = seed
        let run = RunState(seed: seed, character: character)
        let newWorld = World(run: run)
        world = newWorld
        renderer.build(dungeon: newWorld.dungeon)
        mode = .playing
        overlay.removeAllChildren()
        hud.root.isHidden = false
        #if canImport(UIKit)
        touchControls.setControlsVisible(true)
        #endif
        exitMarker = nil
        trauma = 0
        hitStop = 0
        transitioning = false
        centerCamera(on: newWorld)
        hud.announce("DEPTH 1")
        hud.notice("SEED  \(seedText(seed))")
    }

    private func descend() {
        guard let current = world, let next = current.descend() else {
            showVictory()
            return
        }
        transitioning = true
        let fade = SKSpriteNode(color: .black, size: CGSize(width: 4000, height: 4000))
        fade.zPosition = 150_000
        fade.alpha = 0
        cameraNode.addChild(fade)
        fade.run(.sequence([
            .fadeIn(withDuration: 0.35),
            .run { [weak self] in
                guard let self else { return }
                self.world = next
                self.exitMarker = nil
                self.renderer.build(dungeon: next.dungeon)
                self.centerCamera(on: next)
                self.hud.announce("DEPTH \(next.run.depth)")
            },
            .wait(forDuration: 0.15),
            .fadeOut(withDuration: 0.35),
            .removeFromParent(),
            .run { [weak self] in self?.transitioning = false },
        ]))
    }

    private func centerCamera(on world: World) {
        guard let player = world.playerActor else { return }
        cameraNode.position = WorldRenderer.scenePoint(player.position)
    }

    // -- main loop ------------------------------------------------------------

    override func update(_ currentTime: TimeInterval) {
        let delta = lastUpdate == 0 ? 1.0 / 60.0 : min(currentTime - lastUpdate, 0.1)
        lastUpdate = currentTime
        menuCooldown = max(0, menuCooldown - delta)

        updateAimFromMouse()

        switch mode {
        case .title, .characterSelect, .dead, .victory:
            updateMenus(dt: delta)
        case .paused:
            if input.pauseRequested || pendingTouchPause {
                pendingTouchPause = false
                resume()
            }
        case .playing:
            updatePlaying(dt: delta)
        }
    }

    private func updatePlaying(dt: TimeInterval) {
        guard let world else { return }

        if input.pauseRequested || pendingTouchPause {
            pendingTouchPause = false
            pause()
            return
        }

        // Hit stop: freeze the simulation for a few frames on a heavy hit so
        // the impact registers. Rendering keeps running, so it reads as
        // weight rather than as a stutter.
        if hitStop > 0 {
            hitStop -= dt
        } else if !transitioning {
            // renderer.root sits at the scene origin untransformed, so world
            // scene points are already scene coordinates.
            let playerScene = world.playerActor
                .map { WorldRenderer.scenePoint($0.position) } ?? .zero
            #if canImport(UIKit)
            let state = pollTouchInput(playerScenePoint: playerScene)
            #else
            let state = input.poll(playerScenePoint: playerScene)
            #endif
            world.step(dt: dt, input: state)
        }

        handle(events: world.drainEvents())
        renderer.sync(world: world, font: font)
        hud.update(world: world)
        #if canImport(UIKit)
        touchControls.setInteractVisible(world.player.interactTarget != nil)
        #endif
        updateCamera(world: world, dt: dt)
        updateExitMarker(world: world)

        if world.playerDead && mode == .playing {
            showGameOver()
        }
        if world.canDescend && world.playerIsOnExit && !transitioning {
            descend()
        }
    }

    private func updateAimFromMouse() {
        #if canImport(AppKit)
        guard let view, let window = view.window else { return }
        // Reading the pointer position directly rather than tracking
        // mouseMoved events: no tracking areas to maintain, and the aim never
        // goes stale when the cursor leaves and re-enters the window.
        let windowPoint = window.mouseLocationOutsideOfEventStream
        let viewPoint = view.convert(windowPoint, from: nil)
        input.setAim(scenePoint: convertPoint(fromView: viewPoint))
        #endif
    }

    private func updateCamera(world: World, dt: TimeInterval) {
        guard let player = world.playerActor else { return }
        let target = WorldRenderer.scenePoint(player.position)

        // Lead the camera slightly toward the crosshair so you can see what
        // you are aiming at without the camera feeling loose.
        let aim = WorldRenderer.scenePoint(Vec2(Double(input.aimScenePoint.x),
                                                Double(-input.aimScenePoint.y)))
        let lead = CGPoint(x: (aim.x - target.x) * 0.12,
                           y: (aim.y - target.y) * 0.12)
        let desired = CGPoint(x: target.x + max(-40, min(40, lead.x)),
                              y: target.y + max(-30, min(30, lead.y)))

        let smoothing = CGFloat(1 - exp(-9 * dt))
        var position = CGPoint(
            x: cameraNode.position.x + (desired.x - cameraNode.position.x) * smoothing,
            y: cameraNode.position.y + (desired.y - cameraNode.position.y) * smoothing)

        // Screen shake, on a squared curve so small hits barely register and
        // explosions really move.
        trauma = max(0, trauma - dt * 1.8)
        if trauma > 0 {
            let magnitude = trauma * trauma * 9
            position.x += CGFloat(Double.random(in: -magnitude...magnitude))
            position.y += CGFloat(Double.random(in: -magnitude...magnitude))
        }

        // Snap to whole source pixels: the single most effective thing you can
        // do to stop pixel art crawling as the camera moves.
        cameraNode.position = CGPoint(x: (position.x * zoom).rounded() / zoom,
                                      y: (position.y * zoom).rounded() / zoom)
    }

    private func updateExitMarker(world: World) {
        guard let exit = world.exitPosition else {
            exitMarker?.removeFromParent()
            exitMarker = nil
            return
        }
        if exitMarker == nil {
            let node = SKSpriteNode(frame: atlas.frame(of: "fx/portal", at: 0))
            node.zPosition = -5_000
            renderer.root.addChild(node)
            let frames = atlas.animation("fx/portal").map(\.texture)
            node.run(.repeatForever(.animate(with: frames, timePerFrame: 1.0 / 12,
                                             resize: false, restore: false)))
            exitMarker = node
        }
        exitMarker?.position = WorldRenderer.scenePoint(exit)
    }

    // -- events ---------------------------------------------------------------

    private func handle(events: [GameEvent]) {
        for event in events {
            switch event {
            case .effect(let request):
                renderer.play(effect: request)

            case .shake(let strength, _):
                trauma = min(1.2, trauma + strength / 12)

            case .hitStop(let duration):
                hitStop = max(hitStop, duration)

            case .damageNumber(let amount, let position, let crit):
                guard amount >= 1 else { continue }
                renderer.showNumber(
                    "\(Int(amount.rounded()))", at: position,
                    color: crit ? SKColor(red: 1, green: 0.85, blue: 0.3, alpha: 1)
                                : SKColor(red: 1, green: 0.95, blue: 0.9, alpha: 1),
                    font: font, scale: crit ? 1.5 : 1)

            case .healNumber(let amount, let position):
                renderer.showNumber("+\(Int(amount.rounded()))", at: position,
                                    color: SKColor(red: 0.5, green: 1, blue: 0.6,
                                                   alpha: 1),
                                    font: font)

            case .playerHurt:
                flashDamage()

            case .playerDied:
                trauma = 1.2

            case .blankUsed:
                flashWhite()

            case .roomCleared:
                hud.notice("ROOM CLEAR")

            case .bossPhaseChanged:
                trauma = min(1.2, trauma + 0.6)

            case .bossDefeated(let name):
                hud.announce("\(name) FALLS")

            case .floorCleared:
                hud.announce("THE WAY DOWN OPENS")

            case .notice(let text):
                hud.announce(text)

            case .synergyActivated(_, let name, let summary):
                hud.announceSynergy(name: name, summary: summary)

            case .pickedUp(let label, let sprite):
                hud.notice(label.uppercased(), sprite: sprite)

            case .shopRefused(let reason):
                hud.notice(reason.uppercased())

            case .sound(let name, let volume):
                #if canImport(AVFoundation)
                audio.play(name, volume: volume)
                #endif

            case .playerDodged, .doorsLocked, .doorsUnlocked, .roomEntered,
                 .enemyKilled:
                break
            }
        }
    }

    private func flashDamage() {
        damageFlash?.removeAllActions()
        damageFlash?.alpha = 0.85
        damageFlash?.run(.fadeAlpha(to: 0, duration: 0.5))
    }

    private func flashWhite() {
        let flash = SKSpriteNode(color: .white,
                                 size: CGSize(width: size.width / zoom + 8,
                                              height: size.height / zoom + 8))
        flash.zPosition = 96_000
        flash.alpha = 0.55
        cameraNode.addChild(flash)
        flash.run(.sequence([.fadeOut(withDuration: 0.22), .removeFromParent()]))
    }

    // -- menus ----------------------------------------------------------------

    private func updateMenus(dt: TimeInterval) {
        let menu = input.pollMenu()

        switch mode {
        case .title:
            if menu.confirm || input.confirmPressed {
                showCharacterSelect()
            }
        case .characterSelect:
            let step = input.consumeDirectionEdge()
            if step != 0 && menuCooldown <= 0 {
                menuCooldown = 0.18
                let count = CharacterCatalog.all.count
                characterIndex = ((characterIndex + step) % count + count) % count
                showCharacterSelect()
            }
            if menu.confirm {
                startRun(seed: UInt64.random(in: 1...UInt64.max),
                         character: CharacterCatalog.all[characterIndex])
            }
            if menu.back { showTitle() }
        case .dead, .victory:
            if menu.confirm { showTitle() }
        default:
            break
        }
    }

    private func pause() {
        guard mode == .playing else { return }
        mode = .paused
        isPaused = false          // the scene keeps animating; the sim does not
        showPauseScreen()
    }

    private func resume() {
        overlay.removeAllChildren()
        mode = .playing
        input.releaseAll()
    }

    private func panel(width: CGFloat, height: CGFloat) -> SKSpriteNode {
        let node = SKSpriteNode(frame: atlas.frame("ui/panel"))
        // 9-slice: the manifest's inset keeps the corners crisp while the
        // middle stretches.
        let inset = CGFloat(atlas.manifest.panels.inset)
        let full = CGFloat(atlas.manifest.panels.size)
        node.centerRect = CGRect(x: inset / full, y: inset / full,
                                 width: (full - inset * 2) / full,
                                 height: (full - inset * 2) / full)
        node.size = CGSize(width: width, height: height)
        return node
    }

    private func showTitle() {
        mode = .title
        overlay.removeAllChildren()
        #if canImport(UIKit)
        touchControls?.setControlsVisible(false)
        touchControls?.endAll()
        #endif
        world = nil
        exitMarker = nil
        renderer.root.removeFromParent()
        renderer = WorldRenderer(atlas: atlas)
        addChild(renderer.root)
        cameraNode.position = .zero
        hud.root.isHidden = true

        let banner = SKSpriteNode(frame: atlas.frame("ui/title_banner"))
        banner.position = CGPoint(x: 0, y: 60)
        overlay.addChild(banner)

        let title = font.node("PIXEL ROGUE", color: .white, align: .center)
        title.setScale(3)
        title.position = CGPoint(x: 0, y: 74)
        overlay.addChild(title)

        let subtitle = font.node("A DESCENT IN FOUR FLOORS",
                                 color: SKColor(red: 0.8, green: 0.8, blue: 0.9,
                                                alpha: 1),
                                 align: .center)
        subtitle.position = CGPoint(x: 0, y: 24)
        overlay.addChild(subtitle)

        let prompt = font.node("PRESS SPACE TO BEGIN",
                               color: SKColor(red: 1, green: 0.85, blue: 0.35,
                                              alpha: 1),
                               align: .center)
        prompt.setScale(1.5)
        prompt.position = CGPoint(x: 0, y: -30)
        prompt.run(.repeatForever(.sequence([
            .fadeAlpha(to: 0.35, duration: 0.7),
            .fadeAlpha(to: 1, duration: 0.7),
        ])))
        overlay.addChild(prompt)

        let controls = font.paragraph(
            "WASD MOVE   MOUSE AIM   CLICK FIRE   SPACE DODGE   R RELOAD   "
            + "Q BLANK   E TAKE   TAB SWAP   ESC PAUSE",
            color: SKColor(red: 0.6, green: 0.62, blue: 0.72, alpha: 1),
            maxWidth: 300, align: .center)
        controls.position = CGPoint(x: 0, y: -80)
        overlay.addChild(controls)
    }

    private func showCharacterSelect() {
        mode = .characterSelect
        overlay.removeAllChildren()
        hud.root.isHidden = true
        #if canImport(UIKit)
        touchControls?.setControlsVisible(false)
        #endif

        let heading = font.node("CHOOSE YOUR DESCENT", color: .white, align: .center)
        heading.setScale(2)
        heading.position = CGPoint(x: 0, y: 110)
        overlay.addChild(heading)

        let spacing: CGFloat = 46
        let count = CharacterCatalog.all.count
        for (index, character) in CharacterCatalog.all.enumerated() {
            let x = (CGFloat(index) - CGFloat(count - 1) / 2) * spacing
            let selected = index == characterIndex

            let slot = SKSpriteNode(frame: atlas.frame(selected ? "ui/slot_active"
                                                                : "ui/slot"))
            slot.size = CGSize(width: 40, height: 40)
            slot.position = CGPoint(x: x, y: 40)
            overlay.addChild(slot)

            let portrait = SKSpriteNode(frame: atlas.frame(character.portrait))
            portrait.setScale(selected ? 1.1 : 0.9)
            portrait.position = CGPoint(x: x, y: 40)
            portrait.alpha = selected ? 1 : 0.65
            overlay.addChild(portrait)
        }

        let character = CharacterCatalog.all[characterIndex]
        let name = font.node(character.name.uppercased(), color: .white, align: .center)
        name.setScale(1.6)
        name.position = CGPoint(x: 0, y: -6)
        overlay.addChild(name)

        let blurb = font.paragraph(character.blurb,
                                   color: SKColor(red: 0.78, green: 0.79,
                                                  blue: 0.88, alpha: 1),
                                   maxWidth: 280, align: .center)
        blurb.position = CGPoint(x: 0, y: -26)
        overlay.addChild(blurb)

        let passive = font.node(character.passiveText.uppercased(),
                                color: SKColor(red: 1, green: 0.85, blue: 0.35,
                                               alpha: 1),
                                align: .center)
        passive.position = CGPoint(x: 0, y: -52)
        overlay.addChild(passive)

        var gear = "STARTS WITH  \(WeaponCatalog.weapon(character.startingWeapon)?.name.uppercased() ?? "")"
        if let item = character.startingItem, let def = ItemCatalog.item(item) {
            gear += "  +  \(def.name.uppercased())"
        }
        let gearNode = font.node(gear,
                                 color: SKColor(red: 0.7, green: 0.72, blue: 0.82,
                                                alpha: 1),
                                 align: .center)
        gearNode.position = CGPoint(x: 0, y: -70)
        overlay.addChild(gearNode)

        let prompt = font.node("A / D  CHOOSE      E  BEGIN",
                               color: SKColor(red: 0.6, green: 0.62, blue: 0.72,
                                              alpha: 1),
                               align: .center)
        prompt.position = CGPoint(x: 0, y: -100)
        overlay.addChild(prompt)
    }

    private func showPauseScreen() {
        overlay.removeAllChildren()
        guard let world else { return }

        let backdrop = SKSpriteNode(color: SKColor(red: 0.02, green: 0.02,
                                                   blue: 0.04, alpha: 0.82),
                                    size: CGSize(width: size.width / zoom,
                                                 height: size.height / zoom))
        overlay.addChild(backdrop)

        let heading = font.node("PAUSED", color: .white, align: .center)
        heading.setScale(2)
        heading.position = CGPoint(x: 0, y: 130)
        overlay.addChild(heading)

        // The pause screen is where a player actually reads their build, so
        // it lists items with their effects and every live synergy.
        var y: CGFloat = 96
        let items = world.run.loadout.itemDefs
        if items.isEmpty {
            let none = font.node("NO PASSIVES YET",
                                 color: SKColor(red: 0.55, green: 0.57, blue: 0.66,
                                                alpha: 1), align: .center)
            none.position = CGPoint(x: 0, y: y)
            overlay.addChild(none)
            y -= 18
        }
        for item in items.prefix(10) {
            let icon = SKSpriteNode(frame: atlas.frame(item.sprite))
            icon.position = CGPoint(x: -150, y: y)
            icon.setScale(0.8)
            overlay.addChild(icon)

            let name = font.node(item.name.uppercased(), color: .white)
            name.position = CGPoint(x: -136, y: y + 4)
            overlay.addChild(name)

            let effect = font.node(item.effect,
                                   color: SKColor(red: 0.7, green: 0.72,
                                                  blue: 0.82, alpha: 1))
            effect.position = CGPoint(x: 10, y: y + 4)
            overlay.addChild(effect)
            y -= 16
        }

        y -= 10
        let synergies = world.run.loadout.synergyDefs
        let heading2 = font.node(synergies.isEmpty ? "NO SYNERGIES ACTIVE"
                                                   : "ACTIVE SYNERGIES",
                                 color: SKColor(red: 1, green: 0.85, blue: 0.35,
                                                alpha: 1),
                                 align: .center)
        heading2.position = CGPoint(x: 0, y: y)
        overlay.addChild(heading2)
        y -= 18

        for synergy in synergies.prefix(6) {
            let name = font.node(synergy.name.uppercased(),
                                 color: SKColor(red: 1, green: 0.9, blue: 0.55,
                                                alpha: 1),
                                 align: .center)
            name.position = CGPoint(x: 0, y: y)
            overlay.addChild(name)
            y -= 12
            let summary = font.node(synergy.summary,
                                    color: SKColor(red: 0.72, green: 0.74,
                                                   blue: 0.84, alpha: 1),
                                    align: .center)
            summary.position = CGPoint(x: 0, y: y)
            overlay.addChild(summary)
            y -= 18
        }

        let prompt = font.node("ESC  RESUME",
                               color: SKColor(red: 0.6, green: 0.62, blue: 0.72,
                                              alpha: 1),
                               align: .center)
        prompt.position = CGPoint(x: 0, y: -size.height / (2 * zoom) + 30)
        overlay.addChild(prompt)
    }

    private func showGameOver() {
        mode = .dead
        overlay.removeAllChildren()
        hud.root.isHidden = true
        #if canImport(UIKit)
        touchControls.setControlsVisible(false)
        #endif
        guard let world else { return }

        let backdrop = SKSpriteNode(color: SKColor(red: 0.05, green: 0.01,
                                                   blue: 0.02, alpha: 0.86),
                                    size: CGSize(width: size.width / zoom,
                                                 height: size.height / zoom))
        overlay.addChild(backdrop)

        let heading = font.node("YOU DIED",
                                color: SKColor(red: 1, green: 0.35, blue: 0.32,
                                               alpha: 1),
                                align: .center)
        heading.setScale(3)
        heading.position = CGPoint(x: 0, y: 80)
        overlay.addChild(heading)

        var y: CGFloat = 30
        for line in world.run.summaryLines {
            let node = font.node(line.uppercased(), color: .white, align: .center)
            node.position = CGPoint(x: 0, y: y)
            overlay.addChild(node)
            y -= 16
        }

        let synergies = world.run.loadout.synergyDefs
        if !synergies.isEmpty {
            let node = font.node(
                "SYNERGIES  " + synergies.map { $0.name.uppercased() }
                    .joined(separator: "  -  "),
                color: SKColor(red: 1, green: 0.85, blue: 0.35, alpha: 1),
                align: .center)
            node.position = CGPoint(x: 0, y: y - 10)
            overlay.addChild(node)
        }

        let prompt = font.node("E  TRY AGAIN",
                               color: SKColor(red: 0.75, green: 0.77, blue: 0.86,
                                              alpha: 1),
                               align: .center)
        prompt.position = CGPoint(x: 0, y: -70)
        overlay.addChild(prompt)
    }

    private func showVictory() {
        mode = .victory
        overlay.removeAllChildren()
        hud.root.isHidden = true
        #if canImport(UIKit)
        touchControls.setControlsVisible(false)
        #endif

        let backdrop = SKSpriteNode(color: SKColor(red: 0.03, green: 0.03,
                                                   blue: 0.07, alpha: 0.88),
                                    size: CGSize(width: size.width / zoom,
                                                 height: size.height / zoom))
        overlay.addChild(backdrop)

        let heading = font.node("THE DESCENT ENDS",
                                color: SKColor(red: 1, green: 0.9, blue: 0.5, alpha: 1),
                                align: .center)
        heading.setScale(2.5)
        heading.position = CGPoint(x: 0, y: 70)
        overlay.addChild(heading)

        if let world {
            var y: CGFloat = 20
            for line in world.run.summaryLines {
                let node = font.node(line.uppercased(), color: .white, align: .center)
                node.position = CGPoint(x: 0, y: y)
                overlay.addChild(node)
                y -= 16
            }
        }

        let prompt = font.node("E  RETURN TO THE SURFACE",
                               color: SKColor(red: 0.75, green: 0.77, blue: 0.86,
                                              alpha: 1),
                               align: .center)
        prompt.position = CGPoint(x: 0, y: -60)
        overlay.addChild(prompt)
    }

    // -- touch input -----------------------------------------------------------

    #if canImport(UIKit)
    /// Builds a frame of intent from the on-screen controls.
    private func pollTouchInput(playerScenePoint: CGPoint) -> InputState {
        var state = InputState()

        // Scene space is y-up, world space is y-down.
        let move = touchControls.moveVector
        state.move = Vec2(Double(move.x), Double(-move.y))

        let aim = touchControls.aimVector
        if touchControls.isAiming, aim != .zero {
            lastTouchAim = Vec2(Double(aim.x), Double(-aim.y)).normalized
            // Holding the aim stick *is* the trigger — see TouchControls.
            state.firing = true
        }
        let target = Vec2(Double(playerScenePoint.x), Double(-playerScenePoint.y))
        state.aim = target + lastTouchAim * 140

        let presses = touchControls.consumePresses()
        state.dodgePressed = presses.contains("dodge")
        state.reloadPressed = presses.contains("reload")
        state.blankPressed = presses.contains("blank")
        state.interactPressed = presses.contains("interact")
        if presses.contains("swap") { state.weaponCycle = 1 }
        if presses.contains("pause") { pendingTouchPause = true }
        return state
    }

    private func scenePoint(for touch: UITouch) -> CGPoint {
        // Controls live under the camera, so their coordinates are the
        // camera's, not the scene's.
        cameraNode.convert(touch.location(in: self), from: self)
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            let point = scenePoint(for: touch)
            if mode == .playing {
                touchControls.began(touch, at: point, viewport: size)
            } else {
                handleMenuTap(at: point)
            }
        }
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard mode == .playing else { return }
        for touch in touches {
            touchControls.moved(touch, to: scenePoint(for: touch))
        }
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches { touchControls.ended(touch) }
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches { touchControls.ended(touch) }
    }

    /// Menus are driven by where you tap: the outer thirds step through a
    /// list, the middle confirms. No on-screen arrows to miss.
    private func handleMenuTap(at point: CGPoint) {
        let third = size.width / zoom / 3
        switch mode {
        case .title:
            showCharacterSelect()
        case .characterSelect:
            let count = CharacterCatalog.all.count
            if point.x < -third / 2 {
                characterIndex = (characterIndex - 1 + count) % count
                showCharacterSelect()
            } else if point.x > third / 2 {
                characterIndex = (characterIndex + 1) % count
                showCharacterSelect()
            } else {
                startRun(seed: UInt64.random(in: 1...UInt64.max),
                         character: CharacterCatalog.all[characterIndex])
            }
        case .paused:
            resume()
        case .dead, .victory:
            showTitle()
        case .playing:
            break
        }
    }
    #endif

    // -- events from AppKit ----------------------------------------------------

    #if canImport(AppKit)
    override func keyDown(with event: NSEvent) {
        input.keyDown(event.keyCode)
    }

    override func keyUp(with event: NSEvent) {
        input.keyUp(event.keyCode)
    }

    override func mouseDown(with event: NSEvent) {
        input.mouseDown(left: true)
    }

    override func mouseUp(with event: NSEvent) {
        input.mouseUp(left: true)
    }

    override func rightMouseDown(with event: NSEvent) {
        input.mouseDown(left: false)
    }

    override func rightMouseUp(with event: NSEvent) {
        input.mouseUp(left: false)
    }

    override func mouseMoved(with event: NSEvent) {
        input.setAim(scenePoint: event.location(in: self))
    }

    override func mouseDragged(with event: NSEvent) {
        input.setAim(scenePoint: event.location(in: self))
    }

    override func scrollWheel(with event: NSEvent) {
        input.scrolled(by: event.scrollingDeltaY)
    }
    #endif
}
#endif
