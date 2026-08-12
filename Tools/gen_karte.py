"""
Zeichnet die ganze Welt auf ein Blatt.

Das ist kein Bild, das jemand gemalt hat, sondern eines, das aus den echten
Raumdaten faellt: jede Kachel, jede Tuer, jeder Fund steht da, wo er im
Spiel steht. Damit ist es zugleich Konzeptbild und Pruefwerkzeug - eine
Karte, die luegen kann, waere beides nicht.

Die Anordnung wird nicht von Hand gesetzt, sondern aus den Tueren
abgeleitet: eine Tuer in der linken Wand haengt den Nachbarraum links an,
ein Schacht nach oben haengt ihn darueber. Wenn die Welt also umgebaut
wird, ordnet sich die Karte neu, ohne dass jemand nachzieht.

    python3 Tools/gen_karte.py
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

from pixelkit import Palette as P, hexc, mix, shade

WURZEL = Path(__file__).resolve().parent.parent
LEVELS = WURZEL / "Sources" / "ResonanzCore" / "Resources" / "Levels"
AUS = WURZEL / "vorschau" / "karte.png"

# Ein Kachel wird zu so vielen Bildpunkten. Klein genug, dass die ganze
# Welt auf ein Blatt passt, gross genug, dass man Gaenge noch sieht.
M = 3
LUFT = 9 * M          # Abstand zwischen zwei Raeumen

SOLID, PLATFORM, SPIKE, DWALL = "#", "=", "^", "D"
SCHRAEG = set("/\\1234")

REGIONSFARBEN = {
    "hain": (P.REGIONS["hain"][0], P.REGIONS["hain"][1]),
    "kathedrale": (P.REGIONS["kathedrale"][0], P.REGIONS["kathedrale"][1]),
    "grotten": (P.REGIONS["grotten"][0], P.REGIONS["grotten"][1]),
    "dissonanz": (P.REGIONS["dissonanz"][0], P.REGIONS["dissonanz"][1]),
}

REGIONSNAMEN = {
    "hain": "DER SCHLAFENDE HAIN",
    "kathedrale": "DIE KATHEDRALE DER FUGEN",
    "grotten": "DIE RESONANZKAVERNEN",
    "dissonanz": "DAS HERZ DER DISSONANZ",
}


def lade() -> tuple[dict, dict]:
    index = json.loads((LEVELS / "index.json").read_text())
    raeume = {}
    for eintrag in index["rooms"]:
        raeume[eintrag["id"]] = json.loads((LEVELS / f"{eintrag['id']}.json").read_text())
    return index, raeume


def richtung(raum: dict, tuer: dict) -> tuple[int, int]:
    """In welche Richtung fuehrt diese Tuer aus dem Raum heraus?"""
    if tuer["x"] <= 1:
        return (-1, 0)
    if tuer["x"] + tuer["w"] >= raum["width"] - 1:
        return (1, 0)
    return (0, -1) if tuer["y"] < raum["height"] / 2 else (0, 1)


def anordnen(raeume: dict, start: str) -> dict[str, tuple[int, int]]:
    """
    Setzt die Raeume nebeneinander, wie die Tueren es vorgeben.

    Kein Kraeftespiel, keine Optimierung: der Nachbar haengt genau an der
    Seite, an der die Tuer liegt, und faengt dort an, wo der Nachbarraum
    aufhoert. Das ergibt keine schoene, aber eine ehrliche Karte.
    """
    pos = {start: (0, 0)}
    warte = deque([start])
    while warte:
        rid = warte.popleft()
        raum = raeume[rid]
        x0, y0 = pos[rid]
        for tuer in raum["doors"]:
            ziel = tuer["target"]
            if ziel in pos or ziel not in raeume:
                continue
            dx, dy = richtung(raum, tuer)
            nachbar = raeume[ziel]
            if dx > 0:
                nx, ny = x0 + raum["width"] + LUFT // M, y0 + (tuer["y"] - nachbar["height"] // 2)
            elif dx < 0:
                nx, ny = x0 - nachbar["width"] - LUFT // M, y0 + (tuer["y"] - nachbar["height"] // 2)
            elif dy < 0:
                nx, ny = x0 + (tuer["x"] - nachbar["width"] // 2), y0 - nachbar["height"] - LUFT // M
            else:
                nx, ny = x0 + (tuer["x"] - nachbar["width"] // 2), y0 + raum["height"] + LUFT // M
            pos[ziel] = (nx, ny)
            warte.append(ziel)

    # Die Tueren sagen nur, in welche Richtung es weitergeht - nicht, dass
    # dort schon jemand steht. Also werden die Raeume anschliessend
    # auseinandergeschoben, bis sich keine zwei mehr ueberdecken. Immer
    # entlang der Achse, auf der sie sich am wenigsten ueberlappen: so
    # bleibt die Anordnung, die aus den Tueren kam, weitgehend erhalten.
    ids = list(pos)
    for _ in range(400):
        ruhe = True
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                ax, ay = pos[a]
                bx, by = pos[b]
                aw, ah = raeume[a]["width"] + 6, raeume[a]["height"] + 6
                bw, bh = raeume[b]["width"] + 6, raeume[b]["height"] + 6
                ueberx = min(ax + aw, bx + bw) - max(ax, bx)
                uebery = min(ay + ah, by + bh) - max(ay, by)
                if ueberx <= 0 or uebery <= 0:
                    continue
                ruhe = False
                if ueberx < uebery:
                    schub = (ueberx + 1) // 2
                    if ax < bx:
                        pos[a] = (ax - schub, ay); pos[b] = (bx + schub, by)
                    else:
                        pos[a] = (ax + schub, ay); pos[b] = (bx - schub, by)
                else:
                    schub = (uebery + 1) // 2
                    if ay < by:
                        pos[a] = (ax, ay - schub); pos[b] = (bx, by + schub)
                    else:
                        pos[a] = (ax, ay + schub); pos[b] = (bx, by - schub)
        if ruhe:
            break
    return pos


def zeichne_raum(bild: Image.Image, raum: dict, ox: int, oy: int) -> None:
    body, edge = REGIONSFARBEN[raum["region"]]
    fels = mix(body, P.INK, 0.35)
    kante = mix(edge, P.INK, 0.25)
    plattform = mix(edge, body, 0.4)
    dorn = P.ROT
    sperre = mix(P.ROT_DIM, P.INK, 0.2)
    zeichner = ImageDraw.Draw(bild, "RGBA")

    zeilen = raum["tiles"]
    for y, zeile in enumerate(zeilen):
        for x, ch in enumerate(zeile):
            if ch == ".":
                continue
            if ch == SOLID or ch in SCHRAEG:
                farbe = fels
                # Die oberste Reihe einer Masse bekommt Licht - sonst ist
                # die Karte ein Klumpen ohne Oberflaeche.
                if y > 0 and zeilen[y - 1][x] == ".":
                    farbe = kante
            elif ch == PLATFORM:
                farbe = plattform
            elif ch == SPIKE:
                farbe = dorn
            elif ch == DWALL:
                farbe = sperre
            else:
                continue
            px, py = ox + x * M, oy + y * M
            zeichner.rectangle([px, py, px + M - 1, py + M - 1], fill=farbe)


def zeichne_marken(bild: Image.Image, raum: dict, ox: int, oy: int) -> None:
    z = ImageDraw.Draw(bild, "RGBA")

    def punkt(x: float, y: float, farbe, r: int = 3) -> None:
        px, py = ox + x * M, oy + y * M
        z.ellipse([px - r, py - r, px + r, py + r], fill=farbe)

    for bank in raum.get("benches", []):
        punkt(bank["x"], bank["y"] - 1, P.TRIM, 4)
        z.line([ox + bank["x"] * M, oy + (bank["y"] - 3) * M,
                ox + bank["x"] * M, oy + (bank["y"] - 1) * M], fill=P.TRIM, width=2)

    farben = {"ability": P.BLOOM, "kern": P.GOLD, "equipment": P.BONE,
              "siegel": hexc("#9fe8ff"), "klinge": hexc("#ff7ad0")}
    for fund in raum.get("pickups", []):
        punkt(fund["x"], fund["y"] - 1, farben.get(fund["kind"], P.BONE), 3)

    for tuer in raum["doors"]:
        farbe = P.GOLD if tuer.get("requires") else mix(P.BONE, P.INK, 0.35)
        px = ox + tuer["x"] * M
        py = oy + tuer["y"] * M
        z.rectangle([px - 1, py - 1, px + tuer["w"] * M, py + tuer["h"] * M],
                    outline=farbe, width=2)

    if raum.get("boss"):
        b = raum["boss"]
        punkt(b["x"], b["y"] - 2, P.ROT, 7)


def beschriften(bild: Image.Image, raum: dict, ox: int, oy: int) -> None:
    z = ImageDraw.Draw(bild, "RGBA")
    z.text((ox + 2, oy - 14), f'{raum["id"]}  {raum["name"]}',
           fill=mix(P.BONE, P.INK, 0.25))


def build() -> None:
    index, raeume = lade()
    pos = anordnen(raeume, index["startRoom"])

    minx = min(x for x, _ in pos.values())
    miny = min(y for _, y in pos.values())
    maxx = max(x + raeume[r]["width"] for r, (x, _) in pos.items())
    maxy = max(y + raeume[r]["height"] for r, (_, y) in pos.items())

    rand = 40
    breite = (maxx - minx) * M + rand * 2
    hoehe = (maxy - miny) * M + rand * 2 + 60

    bild = Image.new("RGBA", (breite, hoehe), hexc("#080a12"))
    z = ImageDraw.Draw(bild, "RGBA")

    # Verbindungen zuerst, damit sie hinter den Raeumen liegen.
    for rid, raum in raeume.items():
        x0, y0 = pos[rid]
        for tuer in raum["doors"]:
            ziel = tuer["target"]
            if ziel not in pos:
                continue
            zx, zy = pos[ziel]
            a = (rand + (x0 - minx + tuer["x"]) * M,
                 rand + 60 + (y0 - miny + tuer["y"]) * M)
            b = (rand + (zx - minx + raeume[ziel]["width"] // 2) * M,
                 rand + 60 + (zy - miny + raeume[ziel]["height"] // 2) * M)
            farbe = P.GOLD if tuer.get("requires") else mix(P.STONE_HI, P.INK, 0.3)
            z.line([a, b], fill=(farbe[0], farbe[1], farbe[2], 120), width=2)

    for rid, raum in raeume.items():
        x0, y0 = pos[rid]
        ox = rand + (x0 - minx) * M
        oy = rand + 60 + (y0 - miny) * M
        zeichne_raum(bild, raum, ox, oy)
        zeichne_marken(bild, raum, ox, oy)
        beschriften(bild, raum, ox, oy)

    z.text((rand, 24), "RESONANZ - DIE GANZE WELT", fill=P.BONE)
    z.text((rand, 40),
           "gelb: verschlossene Tuer   -   tuerkis: Stimmgabel   -   "
           "punkte: Faehigkeit, Kern, Fassung, Siegel, Klinge",
           fill=mix(P.BONE, P.INK, 0.45))

    AUS.parent.mkdir(exist_ok=True)
    bild.save(AUS)
    print(f"karte -> {AUS} ({bild.width}x{bild.height})")


if __name__ == "__main__":
    build()
