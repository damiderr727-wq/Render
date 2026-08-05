#!/usr/bin/env python3
"""Generate every sprite in the game and pack it into atlases.

    python3 Tools/pixelforge/build_assets.py --out Assets/generated

Output:
    game0.png, game1.png, ...   packed sheets
    game.json                   manifest the Swift side loads at startup
    preview_*.png               contact sheets, handy in code review

The manifest is the contract between this tool and ``AtlasLoader.swift``:
sprite keys, animation names, weapon anchors and font metrics all come from
here, so renaming anything is a two-file change.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pixelforge import chars, enemies, font, fx, items, tiles, ui, weapons
from pixelforge.atlas import AtlasBuilder
from pixelforge.canvas import Canvas
from pixelforge.shapes import contact_shadow

# Frame rates chosen so that everything reads at 60fps without shimmering.
FPS = {
    "idle": 4.0,
    "walk": 12.0,
    "roll": 16.0,
    "die": 9.0,
    "enemy": 8.0,
    "boss": 5.0,
    "prop": 8.0,
    "fx_fast": 24.0,
    "fx": 16.0,
    "ui": 3.0,
}


def _anim_fps(anim_name: str) -> float:
    for key in ("idle", "walk", "roll", "die"):
        if anim_name.startswith(key):
            return FPS[key]
    return FPS["enemy"]


def build(out_dir: str, preview_dir: str | None) -> dict:
    atlas = AtlasBuilder("game")

    # -- characters --------------------------------------------------------
    player_meta = {}
    for spec in chars.player_specs():
        anims = chars.build_character(spec)
        for anim_name, frames in anims.items():
            loop = anim_name not in ("die", "hurt")
            atlas.add_frames(f"char/{spec.name}/{anim_name}", frames,
                             _anim_fps(anim_name), loop)
        atlas.add(f"portrait/{spec.name}", chars.build_portrait(spec))
        player_meta[spec.name] = {
            "title": spec.extras.get("title", spec.name.title()),
            "frameWidth": chars.FRAME_W,
            "frameHeight": chars.FRAME_H,
            "groundY": chars.GROUND_Y,
        }

    enemy_meta = {}
    for spec in enemies.humanoid_specs():
        anims = enemies.build_humanoid(spec)
        for anim_name, frames in anims.items():
            loop = anim_name not in ("die", "hurt")
            atlas.add_frames(f"char/{spec.name}/{anim_name}", frames,
                             _anim_fps(anim_name), loop)
        enemy_meta[spec.name] = {"rig": "humanoid",
                                 "groundY": chars.GROUND_Y}

    for name, frames in enemies.build_non_humanoids().items():
        atlas.add_frames(f"enemy/{name}", frames, FPS["enemy"])
        enemy_meta[name] = {"rig": "creature",
                            "groundY": frames[0].h - 2}

    boss_meta = {}
    for name, frames in enemies.build_bosses().items():
        atlas.add_frames(f"boss/{name}", frames, FPS["boss"])
        boss_meta[name] = {"width": frames[0].w, "height": frames[0].h}

    # -- environment -------------------------------------------------------
    for theme_name, theme in tiles.THEMES.items():
        for i in range(4):
            atlas.add(f"tile/{theme_name}/floor_{i}", tiles.floor_tile(theme, i))
        atlas.add(f"tile/{theme_name}/floor_grate", tiles.floor_grate(theme))
        atlas.add(f"tile/{theme_name}/floor_pit", tiles.floor_pit(theme))
        for part in ("center", "edge_n", "edge_s", "edge_w", "edge_e",
                     "corner"):
            atlas.add(f"tile/{theme_name}/rug_{part}",
                      tiles.floor_rug(theme, part))
        for mask in range(16):
            atlas.add(f"tile/{theme_name}/cap_{mask}",
                      tiles.wall_cap(theme, mask))
        for i in range(4):
            atlas.add(f"tile/{theme_name}/face_{i}", tiles.wall_face(theme, i))
        atlas.add(f"tile/{theme_name}/wall_side", tiles.wall_side(theme))
        atlas.add(f"tile/{theme_name}/wall_shadow", tiles.wall_shadow())
        for state in ("closed", "open", "locked", "boss"):
            for axis in ("v", "h"):
                atlas.add(f"tile/{theme_name}/door_{state}_{axis}",
                          tiles.door_tile(theme, state, axis))
        for name, art in tiles.all_props(theme).items():
            if isinstance(art, list):
                atlas.add_frames(f"prop/{theme_name}/{name}", art, FPS["prop"])
            else:
                atlas.add(f"prop/{theme_name}/{name}", art)

    for w, h in ((12, 5), (16, 6), (22, 8), (34, 12), (48, 16)):
        atlas.add(f"shadow/{w}x{h}", contact_shadow(w, h))

    # -- gear --------------------------------------------------------------
    weapon_meta = {}
    for art in weapons.build_weapons():
        atlas.add(f"weapon/{art.name}", art.canvas)
        weapon_meta[art.name] = art.to_meta()

    for name, canvas in items.build_items().items():
        atlas.add(f"item/{name}", canvas)
    for name, canvas in items.build_pickups().items():
        atlas.add(f"pickup/{name}", canvas)

    # -- combat fx ---------------------------------------------------------
    for name, frames in fx.build_projectiles().items():
        if len(frames) == 1:
            atlas.add(f"proj/{name}", frames[0])
        else:
            atlas.add_frames(f"proj/{name}", frames, FPS["fx"])
    for name, frames in fx.build_effects().items():
        rate = FPS["fx_fast"] if name in ("muzzle_flash", "impact_spark") \
            else FPS["fx"]
        atlas.add_frames(f"fx/{name}", frames, rate, loop=name == "portal")

    # -- ui ----------------------------------------------------------------
    for name, frames in ui.build_ui().items():
        if len(frames) == 1:
            atlas.add(f"ui/{name}", frames[0])
        else:
            atlas.add_frames(f"ui/{name}", frames, FPS["ui"])

    font_glyphs = {}
    for ch, canvas in font.build_font_sheet().items():
        key = f"font/{ord(ch)}"
        atlas.add(key, canvas)
        font_glyphs[str(ord(ch))] = {"sprite": key, "advance": font.ink_width(ch)}

    # -- metadata ----------------------------------------------------------
    atlas.meta = {
        "tileSize": tiles.TILE,
        "wallHeight": tiles.WALL_H,
        "themes": list(tiles.THEMES),
        "players": player_meta,
        "enemies": enemy_meta,
        "bosses": boss_meta,
        "weapons": weapon_meta,
        "panels": {"size": ui.PANEL_SIZE, "inset": ui.PANEL_INSET},
        "font": {
            "height": font.GLYPH_H,
            "baseline": font.BASELINE,
            "tracking": 1,
            "glyphs": font_glyphs,
        },
    }

    data = atlas.write(out_dir)
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        _write_previews(preview_dir)
    return data


def _write_previews(out_dir: str) -> None:
    """Contact sheets. Not loaded by the game — they exist so a human can see
    what changed when a generator is edited."""
    def sheet(rows: list[list[Canvas]], pad: int = 2, scale: int = 3) -> Canvas:
        w = max((sum(c.w + pad for c in row) for row in rows), default=1)
        h = sum(max((c.h for c in row), default=0) + pad for row in rows)
        out = Canvas(max(1, w), max(1, h), (24, 22, 32, 255))
        y = pad
        for row in rows:
            x = pad
            for c in row:
                out.blit(c, x, y)
                x += c.w + pad
            y += max((c.h for c in row), default=0) + pad
        return out.scaled(scale)

    rows = []
    for spec in chars.player_specs():
        a = chars.build_character(spec)
        rows.append(a["idle_front"] + a["walk_front"] + a["idle_side"] +
                    a["idle_back"] + a["roll"])
    sheet(rows).save(os.path.join(out_dir, "preview_players.png"))

    rows = []
    for spec in enemies.humanoid_specs():
        a = enemies.build_humanoid(spec)
        rows.append(a["idle_front"] + a["walk_front"][:3] + a["idle_side"])
    for name, frames in enemies.build_non_humanoids().items():
        rows.append(frames)
    sheet(rows).save(os.path.join(out_dir, "preview_enemies.png"))

    sheet([f for f in enemies.build_bosses().values()],
          scale=2).save(os.path.join(out_dir, "preview_bosses.png"))

    ws = weapons.build_weapons()
    sheet([[w.canvas for w in ws[i:i + 4]] for i in range(0, len(ws), 4)]) \
        .save(os.path.join(out_dir, "preview_weapons.png"))

    its = list(items.build_items().values()) + list(items.build_pickups().values())
    sheet([its[i:i + 8] for i in range(0, len(its), 8)]) \
        .save(os.path.join(out_dir, "preview_items.png"))

    fx_rows = [frames for frames in fx.build_effects().values()]
    sheet(fx_rows, scale=2).save(os.path.join(out_dir, "preview_fx.png"))

    for theme_name, theme in tiles.THEMES.items():
        room = _preview_room(theme)
        room.save(os.path.join(out_dir, f"preview_room_{theme_name}.png"))


def _preview_room(theme) -> Canvas:
    """A furnished room per theme — the fastest way to spot a tile that does
    not sit right next to its neighbours."""
    import random

    T = tiles.TILE
    W, H = 20, 14
    out = Canvas(W * T, H * T, (8, 7, 12, 255))
    rng = random.Random(theme.seed)

    def is_wall(x: int, y: int) -> bool:
        return x < 2 or y < 2 or x >= W - 2 or y >= H - 2

    floors = [tiles.floor_tile(theme, i) for i in range(4)]
    faces = [tiles.wall_face(theme, i) for i in range(4)]
    shadow = tiles.wall_shadow()
    caps = {m: tiles.wall_cap(theme, m) for m in range(16)}

    for y in range(H):
        for x in range(W):
            if not is_wall(x, y):
                out.blit(floors[0 if rng.random() < 0.7 else rng.randrange(4)],
                         x * T, y * T)
    for y in range(H):
        for x in range(W):
            if not is_wall(x, y):
                continue
            mask = ((1 if is_wall(x, y - 1) else 0) |
                    (2 if is_wall(x + 1, y) else 0) |
                    (4 if is_wall(x, y + 1) else 0) |
                    (8 if is_wall(x - 1, y) else 0))
            out.blit(caps[mask], x * T, y * T)
            if not is_wall(x, y + 1) and y + 1 < H:
                out.blit(faces[0 if rng.random() < 0.8 else rng.randrange(4)],
                         x * T, (y + 1) * T)
                out.blit(shadow, x * T, (y + 2) * T)

    props = tiles.all_props(theme)
    layout = [("barrel", 4, 6), ("crate", 6, 6), ("chest_closed", 9, 5),
              ("pillar", 15, 5), ("statue", 4, 9), ("pedestal", 12, 9),
              ("bone_pile", 7, 10), ("shop_counter", 13, 11)]
    for name, tx, ty in layout:
        art = props[name]
        out.blit(art if not isinstance(art, list) else art[0], tx * T, ty * T)
    out.blit(props["torch"][0], 8 * T + 2, 2 * T - 2)
    out.blit(props["torch"][2], 12 * T + 2, 2 * T - 2)

    spec = chars.player_specs()[0]
    pose = chars.build_character(spec)["idle_front"][0]
    out.blit(contact_shadow(12, 5), 10 * T - 6, 8 * T + 16)
    out.blit(pose, 10 * T - 10, 8 * T - 3)
    for i, espec in enumerate(enemies.humanoid_specs()[:3]):
        e = enemies.build_humanoid(espec)["idle_front"][0]
        out.blit(contact_shadow(12, 5), (5 + i * 3) * T - 6, 4 * T + 16)
        out.blit(e, (5 + i * 3) * T - 10, 4 * T - 3)
    return out.scaled(3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="Assets/generated",
                    help="output directory for atlases and manifest")
    ap.add_argument("--previews", default="docs/previews",
                    help="where to write the contact sheets")
    ap.add_argument("--no-preview", action="store_true",
                    help="skip the contact sheets")
    args = ap.parse_args()

    # Previews live outside the atlas directory so they are not copied into
    # the app bundle at build time.
    data = build(args.out, None if args.no_preview else args.previews)
    pages = data["pages"]
    print(f"packed {len(data['sprites'])} sprites, "
          f"{len(data['animations'])} animations into {len(pages)} page(s)")
    for page in pages:
        print(f"  {page['file']}  {page['width']}x{page['height']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
