#!/usr/bin/env python3
"""Composite a scene dump from PixelRogueSnapshot into a PNG.

    swift run PixelRogueSnapshot --scenario combat --out scene.json
    python3 Tools/pixelforge/render_scene.py scene.json --out frame.png

The point is to be able to *look at the game* on a machine that has no
SpriteKit. It consumes the same draw commands the real renderer does — same
sprite names, same anchors, same depth ordering — so a frame produced here is
a faithful preview of a frame produced on macOS, and a mistake in sprite
naming or sort order shows up as a wrong picture rather than as nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class AtlasReader:
    """Reads the packed atlas and vends sprites by name."""

    def __init__(self, directory: str) -> None:
        with open(os.path.join(directory, "game.json")) as fh:
            self.manifest = json.load(fh)
        self.pages = [
            Image.open(os.path.join(directory, page["file"])).convert("RGBA")
            for page in self.manifest["pages"]
        ]
        self.cache: dict[str, Image.Image] = {}
        self.font = self.manifest["font"]
        self.missing: set[str] = set()

    def sprite(self, name: str) -> Image.Image | None:
        if name in self.cache:
            return self.cache[name]
        rect = self.manifest["sprites"].get(name)
        if rect is None:
            self.missing.add(name)
            return None
        page = self.pages[rect["page"]]
        image = page.crop((rect["x"], rect["y"],
                           rect["x"] + rect["w"], rect["y"] + rect["h"]))
        self.cache[name] = image
        return image

    def frame(self, name: str, time: float) -> Image.Image | None:
        """Resolve an animation to the frame showing at ``time``."""
        animation = self.manifest["animations"].get(name)
        if animation is None:
            return self.sprite(name)
        frames = animation["frames"]
        if not frames:
            return None
        index = int(time * animation["fps"])
        if animation["loop"]:
            index %= len(frames)
        else:
            index = min(index, len(frames) - 1)
        return self.sprite(frames[index])

    # -- text --------------------------------------------------------------

    def text_width(self, text: str) -> int:
        total = 0
        for char in text:
            glyph = self.font["glyphs"].get(str(ord(char)))
            total += (glyph["advance"] if glyph else 3) + self.font["tracking"]
        return max(0, total - self.font["tracking"])

    def draw_text(self, target: Image.Image, text: str, x: int, y: int,
                  color: tuple[int, int, int] = (238, 240, 250),
                  align: str = "left", shadow: bool = True) -> None:
        if align == "center":
            x -= self.text_width(text) // 2
        elif align == "right":
            x -= self.text_width(text)

        cursor = x
        for char in text:
            glyph = self.font["glyphs"].get(str(ord(char)))
            if glyph is None:
                cursor += 3 + self.font["tracking"]
                continue
            image = self.sprite(glyph["sprite"])
            if image is not None and char != " ":
                if shadow:
                    target.alpha_composite(
                        tinted(image, (8, 6, 14), 1.0, 0.85),
                        (cursor + 1, y + 1))
                target.alpha_composite(tinted(image, color, 1.0, 1.0),
                                       (cursor, y))
            cursor += glyph["advance"] + self.font["tracking"]


def tinted(image: Image.Image, color: tuple[int, int, int], amount: float,
           alpha: float) -> Image.Image:
    """Blend toward a colour and scale opacity, without touching the source."""
    if amount <= 0 and alpha >= 1:
        return image
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            if amount > 0:
                r = round(r + (color[0] - r) * amount)
                g = round(g + (color[1] - g) * amount)
                b = round(b + (color[2] - b) * amount)
            pixels[x, y] = (r, g, b, round(a * alpha))
    return out


def anchor_pixel(anchor: dict, size: tuple[int, int], sprite: str,
                 atlas: "AtlasReader") -> tuple[float, float]:
    """Where the sprite's origin sits inside its own frame, in pixels."""
    width, height = size
    kind = anchor.get("kind", "center")
    if kind == "bottom":
        return (width / 2, height)
    if kind == "top":
        return (width / 2, 0)
    if kind == "ground":
        return (width / 2, float(anchor.get("row", height)))
    if kind == "pivot":
        # Guns rotate about their grip. The pixel lives in the manifest, next
        # to the art that defines it.
        weapon = sprite.split("/")[-1]
        anchors = atlas.manifest.get("weapons", {}).get(weapon)
        if anchors:
            return (float(anchors["pivot"][0]), float(anchors["pivot"][1]))
    return (width / 2, height / 2)


def prepare(image: Image.Image, command: dict,
            atlas: "AtlasReader") -> tuple[Image.Image, float, float]:
    """Apply flip, rotation, scale and tint. Returns the image and the anchor
    position inside it."""
    anchor_x, anchor_y = anchor_pixel(command["anchor"], image.size,
                                      command["sprite"], atlas)

    if command.get("flipX"):
        image = image.transpose(Image.FLIP_LEFT_RIGHT)
        anchor_x = image.width - anchor_x
    if command.get("flipY"):
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        anchor_y = image.height - anchor_y

    tint = command.get("tint")
    alpha = float(command.get("alpha", 1.0))
    if tint or alpha < 1:
        color = (round(tint[0] * 255), round(tint[1] * 255),
                 round(tint[2] * 255)) if tint else (255, 255, 255)
        image = tinted(image, color, float(command.get("tintAmount", 0)), alpha)

    rotation = float(command.get("rotation", 0.0))
    if abs(rotation) > 1e-4:
        # Rotate about the anchor by first padding it to the centre, so the
        # grip of a gun stays in the hand instead of orbiting the sprite.
        pad_x = max(anchor_x, image.width - anchor_x)
        pad_y = max(anchor_y, image.height - anchor_y)
        canvas = Image.new("RGBA", (int(pad_x * 2), int(pad_y * 2)), (0, 0, 0, 0))
        canvas.alpha_composite(image, (int(pad_x - anchor_x), int(pad_y - anchor_y)))
        # World angles are clockwise with y down; PIL rotates anticlockwise.
        image = canvas.rotate(-math.degrees(rotation), resample=Image.NEAREST)
        anchor_x, anchor_y = image.width / 2, image.height / 2

    scale = float(command.get("scale", 1.0))
    if abs(scale - 1.0) > 1e-3 and scale > 0:
        new_size = (max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)))
        image = image.resize(new_size, Image.NEAREST)
        anchor_x *= scale
        anchor_y *= scale

    return image, anchor_x, anchor_y


def composite_additive(target: Image.Image, source: Image.Image,
                       position: tuple[int, int]) -> None:
    """Additive blend, for anything that should glow rather than occlude."""
    x0, y0 = position
    region = target.crop((x0, y0, x0 + source.width, y0 + source.height))
    base = region.load()
    src = source.load()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            br, bg, bb, ba = base[x, y]
            f = a / 255.0
            base[x, y] = (min(255, round(br + r * f)),
                          min(255, round(bg + g * f)),
                          min(255, round(bb + b * f)),
                          max(ba, a))
    target.paste(region, (x0, y0))


def render(scene: dict, atlas: AtlasReader, hud: bool = True) -> Image.Image:
    viewport = scene["viewport"]
    width, height = viewport["width"], viewport["height"]
    camera = scene["camera"]
    # Snap the camera to whole pixels, exactly as the real renderer does.
    origin_x = round(camera["x"] - width / 2)
    origin_y = round(camera["y"] - height / 2)

    frame = Image.new("RGBA", (width, height), (8, 7, 12, 255))
    drawn = 0

    for command in scene["sprites"]:
        image = atlas.frame(command["sprite"], command.get("time", 0.0))
        if image is None:
            continue

        prepared, anchor_x, anchor_y = prepare(image, command, atlas)
        x = round(command["x"] - origin_x - anchor_x)
        y = round(command["y"] - origin_y - anchor_y)

        # Cull before doing any per-pixel work.
        if (x + prepared.width < 0 or y + prepared.height < 0
                or x >= width or y >= height):
            continue

        if command.get("additive"):
            # Additive compositing needs the source fully inside the target.
            if x < 0 or y < 0 or x + prepared.width > width \
                    or y + prepared.height > height:
                frame.alpha_composite(prepared, (max(0, x), max(0, y)))
            else:
                composite_additive(frame, prepared, (x, y))
        else:
            frame.alpha_composite(prepared, (x, y))
        drawn += 1

    if hud and "hud" in scene:
        draw_hud(frame, scene["hud"], atlas, scene)

    if atlas.missing:
        print(f"  warning: {len(atlas.missing)} sprite(s) not in the atlas: "
              + ", ".join(sorted(atlas.missing)[:6]), file=sys.stderr)
    print(f"  composited {drawn}/{len(scene['sprites'])} sprites")
    return frame


def draw_hud(frame: Image.Image, hud: dict, atlas: AtlasReader,
             scene: dict) -> None:
    width, height = frame.size
    gold = (255, 217, 92)
    pale = (219, 222, 240)
    margin = 8

    def blit(name: str, x: int, y: int) -> None:
        image = atlas.sprite(name)
        if image is not None:
            frame.alpha_composite(image, (x, y))

    # hearts and armour
    per_heart = 20.0
    total = max(1, math.ceil(hud["maxHealth"] / per_heart))
    for i in range(total):
        filled = hud["health"] - i * per_heart
        name = ("ui/heart_full" if filled >= per_heart * 0.75
                else "ui/heart_half" if filled > 0 else "ui/heart_empty")
        blit(name, margin + i * 15, margin)
    for i in range(int(hud.get("armor", 0))):
        blit("ui/armor_ui", margin + total * 15 + 6 + i * 14, margin)

    # consumables
    y = margin + 18
    blit("ui/coin_icon", margin, y)
    atlas.draw_text(frame, str(hud["coins"]), margin + 14, y, gold)
    blit("ui/key_icon", margin + 52, y + 1)
    atlas.draw_text(frame, str(hud["keys"]), margin + 68, y, pale)
    blit("ui/blank_icon", margin + 100, y)
    atlas.draw_text(frame, str(hud["blanks"]), margin + 116, y, pale)

    # depth banner
    theme_names = {"keep": "THE UNDERKEEP", "crypt": "THE BONE CRYPT",
                   "foundry": "THE FOUNDRY", "sanctum": "THE SANCTUM"}
    atlas.draw_text(frame, f"DEPTH {hud['depth']}  -  "
                    f"{theme_names.get(hud['theme'], hud['theme'].upper())}",
                    width // 2, margin, pale, align="center")

    # weapon panel
    wy = height - margin - 10
    atlas.draw_text(frame, hud["ammo"], width - margin, wy, gold, align="right")
    atlas.draw_text(frame, hud["weapon"].upper(), width - margin, wy - 12, pale,
                    align="right")
    for i, sprite in enumerate(hud.get("weapons", [])):
        slot_x = width - margin - 22 - (len(hud["weapons"]) - 1 - i) * 24
        slot_y = wy - 48
        blit("ui/slot_active" if i == hud.get("activeWeapon") else "ui/slot",
             slot_x, slot_y)
        icon = atlas.sprite(sprite)
        if icon is not None:
            icon = icon.resize((max(1, icon.width * 2 // 3),
                                max(1, icon.height * 2 // 3)), Image.NEAREST)
            frame.alpha_composite(icon, (slot_x + 11 - icon.width // 2,
                                         slot_y + 11 - icon.height // 2))

    # passives
    for i, sprite in enumerate(hud.get("items", [])):
        icon = atlas.sprite(sprite)
        if icon is not None:
            frame.alpha_composite(icon, (margin + i * 16, height - margin - 18))

    # minimap
    current = hud.get("currentCell", {"x": 0, "y": 0})
    map_x = width - margin - 46
    map_y = margin + 22
    for room in hud.get("minimap", []):
        cell = atlas.sprite(f"ui/minimap_{room['kind']}")
        if cell is None:
            continue
        frame.alpha_composite(cell,
                              (map_x + (room["x"] - current["x"]) * 12,
                               map_y + (room["y"] - current["y"]) * 10))

    # boss bar
    boss = hud.get("boss")
    if isinstance(boss, dict):
        bar = atlas.sprite("ui/boss_bar_frame")
        fill = atlas.sprite("ui/bar_fill_boss")
        if bar is not None and fill is not None:
            bx = width // 2 - bar.width // 2
            by = margin + 14
            frame.alpha_composite(bar, (bx, by))
            keep = max(1, round(fill.width * boss["fraction"]))
            frame.alpha_composite(fill.crop((0, 0, keep, fill.height)),
                                  (bx + 2, by + 3))
            atlas.draw_text(frame, boss["name"].upper(), width // 2, by + 16,
                            pale, align="center")

    # active synergies
    for i, name in enumerate(hud.get("synergies", [])):
        atlas.draw_text(frame, f"SYNERGY  {name.upper()}", margin,
                        height - margin - 34 - i * 10, gold)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", help="JSON produced by PixelRogueSnapshot")
    parser.add_argument("--atlas", default="Assets/generated")
    parser.add_argument("--out", default="frame.png")
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--no-hud", action="store_true")
    args = parser.parse_args()

    with open(args.scene) as fh:
        scene = json.load(fh)

    atlas = AtlasReader(args.atlas)
    frame = render(scene, atlas, hud=not args.no_hud)
    if args.scale > 1:
        frame = frame.resize((frame.width * args.scale, frame.height * args.scale),
                             Image.NEAREST)
    frame.convert("RGB").save(args.out)
    print(f"  wrote {args.out} ({frame.width}x{frame.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
