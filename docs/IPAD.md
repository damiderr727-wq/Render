# Playing on iPad (Swift Playgrounds)

The game ships in two forms from one codebase:

| | |
|---|---|
| `Package.swift` at the repo root | the macOS build — four modules, AppKit window, mouse and keyboard |
| `PixelRogue.swiftpm/` | the iPad build — one flat module, SwiftUI shell, touch controls |

Swift Playgrounds compiles a single module called `AppModule`, so it cannot
consume a package that is split into `PixelRogueCore`, `PixelRogueAssets` and
so on. `PixelRogue.swiftpm` is assembled from exactly the same sources by
`Tools/make_swiftpm.py` — the entire simulation, `GameScene`, `WorldRenderer`,
`HUD` and `Atlas` are byte-identical between the two builds. Only the shell and
the input layer differ, and they differ inside the shared files behind
`#if canImport(UIKit)`.

## Getting it onto the iPad

**Requirements:** iPadOS 16 or newer, Swift Playgrounds 4.2 or newer.

1. In Safari on the iPad, open the repository and tap **Code → Download ZIP**.
2. Open the **Dateien** (Files) app, find the ZIP in *Downloads*, tap it to
   unpack.
3. Inside the unpacked folder, tap **`PixelRogue.swiftpm`**. It opens in Swift
   Playgrounds directly — it is a Playgrounds document, not a folder to
   import.
4. Tap ▶.

If tapping does nothing, open Swift Playgrounds first, then **Meine
Playgrounds → Öffnen**, and pick `PixelRogue.swiftpm` from Files.

Do **not** create a new app project and import the `.swift` files one by one.
That is what produces `Unable to find module dependency: 'PixelRogueAssets'` —
the files expect to be assembled the way the script assembles them.

## Controls

Twin-stick, both sticks *floating*: each appears wherever your thumb lands in
its half of the screen, so you never have to look down to find one.

| | |
|---|---|
| Left half | move |
| Right half | aim — **holding it also fires** |
| ROLL (bottom right) | dodge roll, brief invulnerability |
| Above it | reload |
| Left of it | blank (clears every enemy bullet) and weapon swap |
| TAKE (bottom centre) | appears only when standing on a gun or a passive |
| Top right | pause — also where you read your build and active synergies |

Holding the aim stick fires because a separate fire button costs a thumb you
do not have. Reloading is automatic when a magazine runs dry, so aiming
without firing is never something you need.

Menus are driven by where you tap: on character select the outer thirds step
through the roster and the middle confirms.

## Rebuilding the package

After changing any game code or regenerating the art:

```bash
python3 Tools/pixelforge/build_assets.py --out Assets/generated
python3 Tools/pixelforge/soundforge.py   --out Assets/generated/sfx
python3 Tools/make_swiftpm.py
```

The script refuses to run if two source files would flatten to the same name —
Playgrounds has one flat namespace, so file names have to stay unique across
`PixelRogueCore` and `PixelRogueApp`.

Resources are copied flat into `PixelRogue.swiftpm/Resources`, because
Playgrounds puts that folder's contents into the bundle root. The iPad copy of
`GeneratedAssets` looks them up in `Bundle.main` accordingly; the macOS copy
walks the nested `generated/` layout. Same API, so nothing above it changes.

## What is verified, and what is not

The whole simulation — generation, combat, synergies, depth ordering — is
covered by `swift test` on the macOS/Linux build, and the flattened copy is
checked to compile as a single module. The SpriteKit and UIKit layers cannot
be compiled anywhere except on an Apple device, so the first run on the iPad
is the first time that code is type-checked. If Playgrounds reports errors,
they will be in the presentation layer, not in the game.

One thing to expect: Swift Playgrounds may want an app icon and accent colour.
The manifest deliberately leaves them out; set them in **App-Einstellungen**
and Playgrounds writes them into `Package.swift` itself.
