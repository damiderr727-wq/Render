#!/usr/bin/env python3
"""Assemble the Swift Playgrounds app package for iPad.

    python3 Tools/make_swiftpm.py

Swift Playgrounds builds one flat module (`AppModule`), so it cannot consume
the repository's four-target package. Rather than maintaining a second copy of
the game, this script assembles `PixelRogue.swiftpm` from the same sources:

* every file from `PixelRogueCore` verbatim — it has no Apple dependencies
* the shared SpriteKit layer, with its cross-module `import`s stripped
* iPad-only files from `Tools/swiftpm-template` (SwiftUI entry point, the
  Bundle.main asset locator, the Playgrounds manifest)
* the generated art and audio, flattened into `Resources`

The macOS build is untouched. Both builds share `GameScene`, `WorldRenderer`,
`HUD`, `Atlas` and the entire simulation; only the shell and the input layer
differ, and those differ by `#if canImport(UIKit)` inside the shared files.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files shared with the macOS build. main.swift is excluded: it is the AppKit
# shell, replaced here by PixelRogueApp.swift.
SHARED_APP_FILES = [
    "Sources/PixelRogueApp/Render/Atlas.swift",
    "Sources/PixelRogueApp/Render/BitmapFont.swift",
    "Sources/PixelRogueApp/Render/WorldRenderer.swift",
    "Sources/PixelRogueApp/UI/HUD.swift",
    "Sources/PixelRogueApp/Audio/AudioMixer.swift",
    "Sources/PixelRogueApp/Input/InputController.swift",
    "Sources/PixelRogueApp/Input/TouchControls.swift",
    "Sources/PixelRogueApp/GameScene.swift",
]

TEMPLATE_FILES = [
    "Package.swift",
    "PixelRogueApp.swift",
    "GeneratedAssets.swift",
]

# Imports that only exist when the project is split into modules.
MODULE_IMPORTS = ("import PixelRogueCore", "import PixelRogueAssets")


def strip_module_imports(source: str) -> str:
    """Removes cross-module imports; everything lives in one module here."""
    lines = [line for line in source.splitlines()
             if line.strip() not in MODULE_IMPORTS]
    return "\n".join(lines) + "\n"


def collect_core_files() -> list[str]:
    core = os.path.join(ROOT, "Sources/PixelRogueCore")
    found: list[str] = []
    for directory, _, files in os.walk(core):
        for name in sorted(files):
            if name.endswith(".swift"):
                found.append(os.path.join(directory, name))
    return sorted(found)


def build(out_dir: str) -> None:
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    resources = os.path.join(out_dir, "Resources")
    os.makedirs(resources)

    written: dict[str, str] = {}

    def emit(name: str, text: str, origin: str) -> None:
        if name in written:
            raise SystemExit(
                f"name collision: {origin} and {written[name]} both flatten to "
                f"{name}. Playgrounds has one flat module, so file names must "
                f"be unique.")
        written[name] = origin
        with open(os.path.join(out_dir, name), "w") as fh:
            fh.write(text)

    # -- sources ------------------------------------------------------------
    for path in collect_core_files():
        with open(path) as fh:
            emit(os.path.basename(path), strip_module_imports(fh.read()),
                 os.path.relpath(path, ROOT))

    for relative in SHARED_APP_FILES:
        path = os.path.join(ROOT, relative)
        with open(path) as fh:
            emit(os.path.basename(path), strip_module_imports(fh.read()),
                 relative)

    for name in TEMPLATE_FILES:
        path = os.path.join(ROOT, "Tools/swiftpm-template", name)
        with open(path) as fh:
            text = fh.read()
        # Package.swift is the manifest, not a source file, so it keeps its
        # place at the package root rather than going through the collision
        # check with the sources.
        with open(os.path.join(out_dir, name), "w") as fh:
            fh.write(text)
        if name != "Package.swift":
            written[name] = f"Tools/swiftpm-template/{name}"

    # -- resources ----------------------------------------------------------
    generated = os.path.join(ROOT, "Assets/generated")
    if not os.path.isdir(generated):
        raise SystemExit("Assets/generated is missing — run build_assets.py first")

    copied = 0
    for name in ("game.json", "game0.png"):
        source = os.path.join(generated, name)
        if not os.path.exists(source):
            raise SystemExit(f"missing {name}; run build_assets.py")
        shutil.copy2(source, os.path.join(resources, name))
        copied += 1

    # Extra atlas pages, if the art ever outgrows one sheet.
    for name in sorted(os.listdir(generated)):
        if name.startswith("game") and name.endswith(".png") and name != "game0.png":
            shutil.copy2(os.path.join(generated, name),
                         os.path.join(resources, name))
            copied += 1

    sfx = os.path.join(generated, "sfx")
    if os.path.isdir(sfx):
        for name in sorted(os.listdir(sfx)):
            if name.endswith(".wav"):
                shutil.copy2(os.path.join(sfx, name),
                             os.path.join(resources, name))
                copied += 1

    print(f"wrote {out_dir}")
    print(f"  {len(written)} source files, {copied} resources")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(ROOT, "PixelRogue.swiftpm"))
    args = parser.parse_args()
    build(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
