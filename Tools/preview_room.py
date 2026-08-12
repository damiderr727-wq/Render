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

KNOWN_EDGES = ['', 't', 'l', 'r', 'b', 'tl', 'tr', 'tb', 'lr', 'lb', 'rb', 'tlr', 'tlb', 'trb', 'lrb', 'tlrb']
BLOCKING = {"#", "D"}
SLOPES = {"/": "up", "\\": "down", "1": "uplow", "2": "uphigh",
          "3": "downhigh", "4": "downlow"}
# Dornen in vier Ausrichtungen - dieselbe Kachel, nur gedreht.
SPIKES = {"^": "", "v": "_down", "<": "_left", ">": "_right"}
# Deckenschraegen - dieselbe Schraege, senkrecht gespiegelt.
CEILS = {"q": "downhigh", "w": "downlow", "e": "uplow", "r": "uphigh"}
BLOCKING |= set(SLOPES) | set(CEILS)


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


def variante(tx: int, ty: int, anzahl: int, salz: int = 0) -> int:
    """
    Welche Variante einer Kachel an dieser Stelle steht - gestreut, nicht
    gerechnet.

    Vorher stand hier `(tx * 31 + ty * 17) % n`. Geht man eine Kachel nach
    rechts, steigt der Wert um genau eins: dieselben Varianten laufen in
    schnurgeraden Diagonalen durch den Raum. Solange die Kacheln kaum
    Zeichnung hatten, fiel das nicht auf - mit Rissen und Schichtung
    sofort. Dieselbe Funktion wie im Spiel, damit Vorschau und Spiel
    dasselbe Bild zeigen.
    """
    h = (tx * 73856093) & 0xFFFFFFFF
    h ^= (ty * 19349663) & 0xFFFFFFFF
    h ^= (salz * 83492791) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 2654435761) & 0xFFFFFFFF
    h ^= h >> 16
    return h % anzahl


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
    # Die Kulisse kann von der Region abweichen (siehe RoomData.backdrop).
    kulisse = room.get("backdrop") or region
    tiles = room["tiles"]

    tile_atlas = Atlas("tiles")
    props = Atlas("props")
    chars = Atlas("characters")
    fx = Atlas("fx")
    backdrops = Atlas("backdrops")

    canvas = Image.new("RGBA", (w * TS, h * TS), (5, 6, 12, 255))

    # Hintergrundschichten. Sie sind genau bildschirmhoch und werden nur
    # waagerecht gekachelt - senkrecht wiederholt gaebe der Himmelsverlauf
    # eine sichtbare Naht.
    #
    # Ist der Raum hoeher als ein Bildschirm, bleibt oben Himmel stehen:
    # die Schichten selbst sind in ihren obersten Reihen durchsichtig
    # gezeichnet (siehe `in_dunst` in gen_backdrops.py) und gehen darum
    # ohne Kante in ihn ueber.
    # Ganz hinten eine durchgehende Himmelsflaeche - dieselbe, die im Spiel
    # als eigener Knoten hinter allem liegt. Ohne sie stehen ueberall dort,
    # wo alle drei Schichten durchsichtig sind, Loecher in der Grundfarbe;
    # in breiten Raeumen ergab das eine schwarze Linie an jeder Kachelfuge.
    # Ganz hinten der Himmelsverlauf, ueber die ganze Raumhoehe gezogen -
    # derselbe Streifen, den das Spiel dort hinlegt. Damit ist es gleich,
    # wie hoch ein Raum ist.
    streifen, _ = backdrops.frame(f"{kulisse}_himmel")
    if streifen is not None:
        canvas.paste(streifen.resize((w * TS, h * TS)), (0, 0))

    # Wohin die Kamera schaut - danach richtet sich, wo die bildschirmfeste
    # Schicht liegt.
    spawn = next(iter(room.get("spawns", {}).values()), None)
    blickpunkt = spawn["x"] * TS if spawn else w * TS / 2

    for layer in range(4):
        img, _ = backdrops.frame(f"{kulisse}_bg{layer}")
        if img is None:
            continue
        # Die Staffelung steckt in der Farbe, nicht in der Deckkraft
        # (siehe `in_ferne` in gen_backdrops.py). Jede Schicht deckt.
        faded = img
        oben = h * TS - img.height

        # Schicht 0 laeuft mit dem Faktor 0, klebt also am Bildschirm: im
        # Spiel sieht man immer dieselbe Kopie, egal wie weit man laeuft.
        # Hier lag sie gekachelt im Raum, und dann stand der Mond zweimal
        # im Bild - ein Fehler der Vorschau, nicht des Spiels, aber einer,
        # den man dem Spiel anlastet. Also genau einmal, dort wo die
        # Kamera steht.
        if layer == 0:
            # Von Hand zuschneiden. `alpha_composite` will ein Ziel
            # innerhalb der Leinwand; steht die Kamera nah am linken Rand,
            # ist der Zielpunkt negativ, und dann klebt ein verschobenes
            # Stueck Himmel mitten im Raum - der Mond als weisser Fetzen
            # neben einem Sigil. Ein Fehler der Vorschau, aber einer, der
            # wie ein Fehler des Spiels aussieht.
            dx = int(blickpunkt - img.width / 2)
            x0, x1 = max(0, dx), min(w * TS, dx + img.width)
            if x1 > x0:
                # Und oben angeschlagen, nicht unten: Schicht 0 ist Luft.
                canvas.alpha_composite(
                    faded.crop((x0 - dx, 0, x1 - dx, img.height)), (x0, 0))
            continue

        # Jede zweite Kachel gespiegelt: sonst stoesst die rechte Kante der
        # Schicht auf ihre eigene linke, und alle 512 Pixel laeuft eine
        # harte senkrechte Naht durchs Bild. Derselbe Kniff wie im Spiel.
        gespiegelt = faded.transpose(Image.FLIP_LEFT_RIGHT)
        for i, ox in enumerate(range(0, w * TS, img.width)):
            canvas.alpha_composite(gespiegelt if i % 2 else faded, (ox, oben))

    # Der Unterbau der Plattformen - vor dem Gelaende gezeichnet, damit
    # er dahinter liegt. Ohne ihn schweben Plattformen als Bretter in der
    # Luft, und genau daran erkennt man ein Kachelbild.
    for y in range(h):
        x = 0
        while x < w:
            if tiles[y][x] != "=":
                x += 1
                continue
            start = x
            while x < w and tiles[y][x] == "=":
                x += 1
            # Alle drei Kacheln einer, damit auch lange Plattformen
            # durchgehend auf etwas sitzen - genau wie im Spiel.
            breite = x - start
            anzahl = max(1, round(breite / 3))
            for k in range(anzahl):
                mitte = start + breite * (k + 0.5) / anzahl
                img, pivot = tile_atlas.frame(
                    f"sockel_{region}_{variante(int(mitte), y, 3, 6 + k)}")
                if img is not None:
                    canvas.alpha_composite(
                        img, (int(mitte * TS - img.width / 2), int(y * TS + 4)))

    # Gelaende
    for y in range(h):
        for x in range(w):
            ch = tiles[y][x]
            if ch == ".":
                continue
            if ch in CEILS:
                name = f"{region}_ceil_{CEILS[ch]}_{variante(x, y, 4, 2)}"
            elif ch in SLOPES:
                name = f"{region}_slope_{SLOPES[ch]}_{variante(x, y, 4, 3)}"
            elif ch == "#":
                name = f"{region}_solid_{edge_key(tiles, x, y, w, h)}_{variante(x, y, 6)}"
            elif ch == "=":
                cap = ""
                if x == 0 or tiles[y][x - 1] != "=":
                    cap += "l"
                if x == w - 1 or tiles[y][x + 1] != "=":
                    cap += "r"
                name = f"{region}_platform_{cap or 'mid'}_{variante(x, y, 4, 1)}"
            elif ch in SPIKES:
                name = f"{region}_spike{SPIKES[ch]}"
            elif ch == "D":
                name = "dissowall_0"
            else:
                continue
            img, pivot = tile_atlas.frame(name)
            if img is not None:
                # Der Ueberhang der Bodenkacheln steht ueber dem Raster.
                canvas.alpha_composite(img, (x * TS, int(y * TS - img.height * pivot[1])))

    # Requisiten auf den Kachelnaehten. Sie sind der eigentliche Grund,
    # warum handgezeichnete Karten kein Raster zeigen.
    def is_surface(x: int, y: int) -> bool:
        return (0 <= x < w and 0 < y < h
                and tiles[y][x] == "#" and tiles[y - 1][x] == ".")

    eigene_kulisse = room.get("backdrop") is not None
    for y in range(1, h):
        for x in range(1, w):
            # Raeume mit eigener Kulisse bekommen keine Regionsrequisiten -
            # sonst waechst im Tempel Gras auf den Bodenplatten.
            if eigene_kulisse:
                break
            if not (is_surface(x, y) and is_surface(x - 1, y)):
                continue
            if (x * 2654435761 + y * 40503) % 100 >= 34:
                continue
            img, pivot = tile_atlas.frame(f"{region}_edge_{(x * 7 + y * 3) % 6}")
            if img is None:
                img, pivot = tile_atlas.frame(f"edge_{region}_{(x * 7 + y * 3) % 6}")
            if img is not None:
                canvas.alpha_composite(
                    img, (x * TS - img.width // 2, y * TS - int(img.height * pivot[1]) + 2))

    # Und dasselbe an der Decke: was dort haengt, bricht die Stufen, die
    # ein gerundetes Hoehenprofil beim Runden auf ganze Kacheln erzeugt.
    def is_ceiling(x: int, y: int) -> bool:
        return (0 <= x < w and 0 <= y < h - 1
                and tiles[y][x] == "#" and tiles[y + 1][x] == ".")

    for y in range(h - 1):
        for x in range(1, w):
            if eigene_kulisse or not is_ceiling(x, y):
                continue
            # An einer Stufe immer, sonst nur hier und da: die Kante ist
            # genau das, was verdeckt werden soll.
            stufe = not is_ceiling(x - 1, y) or not is_ceiling(x + 1, y)
            if not stufe and (x * 2654435761 + y * 40503) % 100 >= 22:
                continue
            img, pivot = tile_atlas.frame(f"hang_{region}_{(x * 5 + y * 11) % 6}_2")
            if img is not None:
                canvas.alpha_composite(
                    img, (x * TS - img.width // 2 + TS // 2, (y + 1) * TS - 2))

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
        name = (f"sigil_klinge_{pickup['id']}" if pickup["kind"] == "klinge"
                else f"sigil_{pickup['id']}")
        place(*props.frame(f"{name}_2"), pickup["x"], pickup["y"] + 0.5)

    # Kreaturen
    sprite_for = {
        "gabelmaus": "gabelmaus_husch_2",
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
        place(*chars.frame(f'{room["boss"]["type"]}_idle_2'),
              room["boss"]["x"], room["boss"]["y"])

    # Die Heldin an ihrem Startpunkt
    spawns = room["spawns"]
    start = spawns.get("start") or next(iter(spawns.values()), None)
    if start:
        place(*chars.frame("cadence_stimmgabel_mantel_idle_0"), start["x"], start["y"])

    # Inschriften als Funke
    for lore in room["lore"]:
        place(*fx.frame("mote_1"), lore["x"], lore["y"] - 0.7)

    # Vorderste Schicht: fast schwarze Massen, laufen vor allem anderen.
    fg_img, _ = backdrops.frame(f"{kulisse}_fg")
    if fg_img is not None:
        fg_gespiegelt = fg_img.transpose(Image.FLIP_LEFT_RIGHT)
        for i, ox in enumerate(range(0, w * TS, fg_img.width)):
            canvas.alpha_composite(fg_gespiegelt if i % 2 else fg_img,
                                   (ox, h * TS - fg_img.height))

    # Verdunklung tiefer Regionen
    if room.get("darkness", 0) > 0:
        veil = Image.new("RGBA", canvas.size, (0, 0, 0, int(255 * room["darkness"])))
        canvas.alpha_composite(veil)

    return canvas


# Was die Kamera im Spiel wirklich zeigt: GameScene.designSize, in
# Kacheln also 32 mal 18. Der Raumueberblick weiter oben zeigt zwei- bis
# fuenfmal so viel und laesst darum alles winzig wirken - das ist eine
# Eigenschaft des Werkzeugs, nicht des Spiels.
SICHT_W, SICHT_H = 512, 288


def kameraausschnitt(bild: Image.Image, room: dict, zoom: int = 3) -> Image.Image:
    """Schneidet den Bildausschnitt zu, den die Kamera im Spiel zeigt."""
    spawn = next(iter(room.get("spawns", {}).values()), None)
    cx = (spawn["x"] * TS if spawn else bild.width / 2)
    cy = (spawn["y"] * TS - 40 if spawn else bild.height / 2)
    x0 = int(max(0, min(bild.width - SICHT_W, cx - SICHT_W / 2)))
    y0 = int(max(0, min(bild.height - SICHT_H, cy - SICHT_H / 2)))
    schnitt = bild.crop((x0, y0, x0 + SICHT_W, y0 + SICHT_H))
    return schnitt.resize((SICHT_W * zoom, SICHT_H * zoom), Image.NEAREST)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("room", nargs="?", help="Raumkennung, etwa A1")
    parser.add_argument("--out", default=None, help="Zieldatei")
    parser.add_argument("--alle", action="store_true", help="alle Raeume rendern")
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--kamera", action="store_true",
                        help="nur den Ausschnitt zeigen, den die Kamera im Spiel zeigt")
    args = parser.parse_args()

    index = json.loads((RES / "Levels" / "index.json").read_text())
    ids = [entry["id"] for entry in index["rooms"]] if args.alle else [args.room or "A1"]

    out_dir = Path(args.out).parent if args.out else ROOT / "vorschau"
    out_dir.mkdir(parents=True, exist_ok=True)

    for room_id in ids:
        image = render(room_id)
        if args.kamera:
            room = json.loads((RES / "Levels" / f"{room_id}.json").read_text())
            image = kameraausschnitt(image, room)
        elif args.scale > 1:
            image = image.resize((image.width * args.scale, image.height * args.scale),
                                 Image.NEAREST)
        target = Path(args.out) if (args.out and not args.alle) else out_dir / f"{room_id}.png"
        image.save(target)
        print(f"{room_id}: {image.width}x{image.height} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
