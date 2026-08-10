"""
Zeichnet einen Raum als Bild - dieselben Atlanten, dieselbe Kantenwahl
wie der SpriteKit-Renderer.

    python3 Tools/preview_room.py A1 --out vorschau.png
    python3 Tools/preview_room.py --alle

Das ist kein Teil des Spiels. Es dient dazu, Levelbau und Grafik zu
begutachten, ohne das Spiel starten zu muessen - und um zu pruefen, ob
Kachelsatz und Raumdaten ueberhaupt zusammenpassen.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "Sources" / "ResonanzCore" / "Resources"
TS = 16

KNOWN_EDGES = ["", "t", "tl", "tr", "tlr", "l", "r", "lr", "b", "tb", "blr", "tblr"]
BLOCKING = {"#", "D"}


class Atlas:
    def __init__(self, name: str):
        self.meta = json.loads((RES / "Atlas" / f"{name}.json").read_text())
        self.sheet = Image.open(RES / "Atlas" / f"{name}.png").convert("RGBA")

    def has(self, name: str) -> bool:
        return name in self.meta["frames"]

    def frame(self, name: str):
        f = self.meta["frames"].get(name)
        if f is None:
            return None, (0.5, 1.0)
        img = self.sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        return img, (f["pivotX"], f["pivotY"])


def edge_key(tiles, x: int, y: int, w: int, h: int) -> str:
    def blocking(xx: int, yy: int) -> bool:
        if not (0 <= xx < w and 0 <= yy < h):
            return True     # ausserhalb gilt als Fels
        return tiles[yy][xx] in BLOCKING

    key = ""
    if not blocking(x, y - 1):
        key += "t"
    if not blocking(x - 1, y):
        key += "l"
    if not blocking(x + 1, y):
        key += "r"
    if not blocking(x, y + 1):
        key += "b"
    if key not in KNOWN_EDGES:
        return "mid"
    return key or "mid"


def render(room_id: str) -> Image.Image:
    room = json.loads((RES / "Levels" / f"{room_id}.json").read_text())
    w, h = room["width"], room["height"]
    region = room["region"]
    tiles = room["tiles"]

    tile_atlas = Atlas("tiles")
    props = Atlas("props")
    chars = Atlas("characters")
    fx = Atlas("fx")
    backdrops = Atlas("backdrops")

    canvas = Image.new("RGBA", (w * TS, h * TS), (5, 6, 12, 255))

    # Hintergrundschichten
    for layer in range(3):
        img, _ = backdrops.frame(f"{region}_bg{layer}")
        if img is None:
            continue
        alpha = [0.55, 0.7, 0.85][layer]
        faded = img.copy()
        faded.putalpha(faded.getchannel("A").point(lambda v: int(v * alpha)))
        for oy in range(h * TS - img.height, -img.height, -img.height):
            for ox in range(0, w * TS, img.width):
                canvas.alpha_composite(faded, (ox, oy))

    # Gelaende
    for y in range(h):
        for x in range(w):
            ch = tiles[y][x]
            if ch == ".":
                continue
            if ch == "#":
                name = f"{region}_solid_{edge_key(tiles, x, y, w, h)}_{(x * 31 + y * 17) % 4}"
            elif ch == "=":
                name = f"{region}_platform"
            elif ch == "^":
                name = f"{region}_spike"
            elif ch == "D":
                name = "dissowall_0"
            else:
                continue
            img, _ = tile_atlas.frame(name)
            if img is not None:
                canvas.alpha_composite(img, (x * TS, y * TS))

    def place(img, pivot, tx: float, ty: float) -> None:
        if img is None:
            return
        px = int(tx * TS + TS / 2 - img.width * pivot[0])
        py = int(ty * TS - img.height * pivot[1])
        canvas.alpha_composite(img, (px, py))

    # Ausstattung
    for decor in room["decor"]:
        if decor["kind"] == "crystal":
            name = f"crystal_{region}_{min(2, max(0, decor.get('size', 1)))}_1"
        else:
            name = f"reed_{region}_1"
        place(*props.frame(name), decor["x"], decor["y"])

    for bench in room["benches"]:
        place(*props.frame("bench_1"), bench["x"], bench["y"])

    for pickup in room["pickups"]:
        place(*props.frame(f"sigil_{pickup['id']}_2"), pickup["x"], pickup["y"] + 0.5)

    # Kreaturen
    sprite_for = {
        "klangmotte": "klangmotte_fly_1",
        "stilleschreiter": "stilleschreiter_walk_2",
        "dissonanzknospe": "dissonanzknospe_bloom_3",
        "echoscherbe": "echoscherbe_spin_1",
    }
    for enemy in room["enemies"]:
        name = sprite_for.get(enemy["type"])
        if name:
            place(*chars.frame(name), enemy["x"], enemy["y"])

    if room.get("boss"):
        place(*chars.frame("kantor_idle_2"), room["boss"]["x"], room["boss"]["y"])

    # Die Heldin an ihrem Startpunkt
    spawns = room["spawns"]
    start = spawns.get("start") or next(iter(spawns.values()), None)
    if start:
        place(*chars.frame("cadence_leier_idle_0"), start["x"], start["y"])

    # Inschriften als Funke
    for lore in room["lore"]:
        place(*fx.frame("mote_1"), lore["x"], lore["y"] - 0.7)

    # Vorderste Schicht: fast schwarze Massen, laufen vor allem anderen.
    fg_img, _ = backdrops.frame(f"{region}_fg")
    if fg_img is not None:
        for ox in range(0, w * TS, fg_img.width):
            canvas.alpha_composite(fg_img, (ox, h * TS - fg_img.height))

    # Verdunklung tiefer Regionen
    if room.get("darkness", 0) > 0:
        veil = Image.new("RGBA", canvas.size, (0, 0, 0, int(255 * room["darkness"])))
        canvas.alpha_composite(veil)

    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("room", nargs="?", help="Raumkennung, etwa A1")
    parser.add_argument("--out", default=None, help="Zieldatei")
    parser.add_argument("--alle", action="store_true", help="alle Raeume rendern")
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()

    index = json.loads((RES / "Levels" / "index.json").read_text())
    ids = [entry["id"] for entry in index["rooms"]] if args.alle else [args.room or "A1"]

    out_dir = Path(args.out).parent if args.out else ROOT / "vorschau"
    out_dir.mkdir(parents=True, exist_ok=True)

    for room_id in ids:
        image = render(room_id)
        if args.scale > 1:
            image = image.resize((image.width * args.scale, image.height * args.scale),
                                 Image.NEAREST)
        target = Path(args.out) if (args.out and not args.alle) else out_dir / f"{room_id}.png"
        image.save(target)
        print(f"{room_id}: {image.width}x{image.height} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
