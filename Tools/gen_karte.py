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
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pixelkit import Palette as P, hash01, hexc, mix, shade

WURZEL = Path(__file__).resolve().parent.parent
LEVELS = WURZEL / "Sources" / "ResonanzCore" / "Resources" / "Levels"
AUS = WURZEL / "vorschau" / "karte.png"
AUS_KUNST = WURZEL / "vorschau" / "karte_kunst.png"

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


# ------------------------------------------------------- Gezeichnete Karte
#
# Dieselbe Welt, andere Absicht.
#
# Die technische Karte oben zeigt jede Kachel, weil sie ein Pruefwerkzeug
# ist. Diese hier ist das, was eine Figur im Spiel in der Hand haelt:
# jemand ist durch die Hoehlen gelaufen und hat aufgezeichnet, was er
# gesehen hat. Also mit Tinte, auf Papier, mit zittriger Hand - und ohne
# Anspruch auf jede Kachel.
#
# Gefaelscht wird trotzdem nichts: die Umrisse werden aus dem echten
# Hohlraum der Raeume abgeleitet, nur geglaettet und angeraut. Wer die
# gezeichnete Karte neben die technische legt, sieht dieselbe Welt.

PAPIER = hexc("#e3d5b4")
TINTE = hexc("#2b2118")
TINTE_HELL = hexc("#6b5a44")

WASCHUNG = {
    "hain": hexc("#7d9668"),
    "kathedrale": hexc("#8f7ea6"),
    "grotten": hexc("#6d92ad"),
    "dissonanz": hexc("#b26a63"),
}


def schrift(groesse: int, fett: bool = False):
    for pfad in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf"
                 % ("-Bold" if fett else ""),
                 "/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf"
                 % ("Bold" if fett else "Regular")):
        try:
            return ImageFont.truetype(pfad, groesse)
        except OSError:
            continue
    return ImageFont.load_default(size=groesse)


def umriss(raum: dict, glaette: int = 4) -> tuple[list[float], list[float]]:
    """
    Die Form des Hohlraums, Spalte fuer Spalte.

    Nicht der Raum, sondern das Loch darin: oben die hoechste Luftkachel,
    unten die tiefste. Das ist es, was ein Kartograf zeichnen wuerde - er
    misst ja aus, wo er gehen konnte, nicht wie dick die Wand ist.
    """
    zeilen = raum["tiles"]
    oben: list[float] = []
    unten: list[float] = []
    letzte = (raum["height"] * 0.4, raum["height"] * 0.6)
    for x in range(raum["width"]):
        luft = [y for y in range(raum["height"]) if zeilen[y][x] == "."]
        if luft:
            letzte = (float(luft[0]), float(luft[-1]))
        oben.append(letzte[0])
        unten.append(letzte[1])

    def weich(werte: list[float]) -> list[float]:
        aus = []
        for i in range(len(werte)):
            a = max(0, i - glaette)
            b = min(len(werte), i + glaette + 1)
            aus.append(sum(werte[a:b]) / (b - a))
        return aus

    oben, unten = weich(oben), weich(unten)

    # Die Enden zusammenziehen. Ein Raum hoert an einer Wand auf, und eine
    # Wand quer durchs Bild sieht aus wie ein Regal - Hoehlen laufen an
    # ihren Enden zu, auch wenn die Kacheln das nicht tun.
    kegel = 4
    for i in range(len(oben)):
        d = min(i, len(oben) - 1 - i)
        if d >= kegel:
            continue
        t = 1 - (d + 0.5) / kegel * 0.82        # 1 = ganz zu, 0.18 = fast offen
        mitte = (oben[i] + unten[i]) / 2
        oben[i] = mitte + (oben[i] - mitte) * (1 - t * 0.75)
        unten[i] = mitte + (unten[i] - mitte) * (1 - t * 0.75)

    return oben, unten


def zittern(punkte, staerke: float, saat: int):
    """Nimmt einer Linie die Maschinengenauigkeit."""
    aus = []
    for i, (x, y) in enumerate(punkte):
        aus.append((x + (hash01(i, saat) - 0.5) * staerke,
                    y + (hash01(saat, i) - 0.5) * staerke))
    return aus


def zeichne_raum_kunst(bild: Image.Image, raum: dict, ox: float, oy: float,
                       m: float, saat: int) -> list[tuple[float, float]]:
    oben, unten = umriss(raum)
    breite = raum["width"]

    punkte = [(ox + x * m, oy + oben[x] * m) for x in range(breite)]
    punkte += [(ox + x * m, oy + (unten[x] + 1) * m) for x in reversed(range(breite))]
    punkte = zittern(punkte, m * 0.55, saat)

    # Die Waschung wird eine Spur groesser als der Umriss angelegt und
    # dann weichgezeichnet - so laeuft die Farbe ueber die Tintenlinie
    # hinaus, wie es Farbe auf Papier eben tut.
    farbe = WASCHUNG[raum["region"]]
    wasch = Image.new("RGBA", bild.size, (0, 0, 0, 0))
    ImageDraw.Draw(wasch, "RGBA").polygon(punkte, fill=(*farbe[:3], 96))
    wasch = wasch.filter(ImageFilter.GaussianBlur(m * 0.5))
    bild.alpha_composite(wasch)

    z = ImageDraw.Draw(bild, "RGBA")
    # Die Tinte wird zweimal gezogen, leicht versetzt: eine Hand trifft
    # die eigene Linie nie genau, und genau das sieht man.
    for versatz, breite_l, alpha in ((0.0, max(2, int(m * 0.45)), 210),
                                     (m * 0.22, max(1, int(m * 0.25)), 90)):
        linie = [(x + versatz, y + versatz * 0.6) for x, y in punkte]
        z.line(linie + [linie[0]], fill=(*TINTE[:3], alpha), width=breite_l,
               joint="curve")

    # Schraffur am Boden: kurze Striche unter der Unterkante. Das ist die
    # eine Geste, die eine Umrisszeichnung nach Hoehle aussehen laesst.
    for x in range(2, breite - 2, 3):
        if hash01(x, saat + 7) > 0.45:
            hx = ox + x * m
            hy = oy + (unten[x] + 1) * m
            laenge = m * (0.6 + hash01(saat, x) * 0.9)
            z.line([hx, hy, hx - laenge * 0.4, hy + laenge],
                   fill=(*TINTE_HELL[:3], 120), width=max(1, int(m * 0.16)))

    return punkte


def build_kunst() -> None:
    index, raeume = lade()
    pos = anordnen(raeume, index["startRoom"])
    m = 5.0

    minx = min(x for x, _ in pos.values())
    miny = min(y for _, y in pos.values())
    maxx = max(x + raeume[r]["width"] for r, (x, _) in pos.items())
    maxy = max(y + raeume[r]["height"] for r, (_, y) in pos.items())

    rand = 70
    breite = int((maxx - minx) * m) + rand * 2
    hoehe = int((maxy - miny) * m) + rand * 2 + 70

    bild = Image.new("RGBA", (breite, hoehe), PAPIER)

    # Papier: Koernung, ein paar Flecken, dunkle Raender. Ohne das bleibt
    # es eine Zeichnung auf Weiss, und Weiss gibt es auf Papier nicht.
    korn = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    kz = ImageDraw.Draw(korn, "RGBA")
    for i in range(breite * hoehe // 900):
        x = int(hash01(i, 3) * breite)
        y = int(hash01(i, 11) * hoehe)
        t = hash01(i, 29)
        kz.point((x, y), fill=(90, 70, 45, int(14 + t * 26)))
    for i in range(90):
        x = hash01(i, 41) * breite
        y = hash01(i, 53) * hoehe
        r = 12 + hash01(i, 67) * 46
        kz.ellipse([x - r, y - r, x + r, y + r], fill=(120, 96, 60, 10))
    bild.alpha_composite(korn.filter(ImageFilter.GaussianBlur(0.6)))

    vignette = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    vz = ImageDraw.Draw(vignette, "RGBA")
    for i in range(26):
        a = int(4 + i * 1.6)
        vz.rectangle([i * 3, i * 3, breite - 1 - i * 3, hoehe - 1 - i * 3],
                     outline=(70, 52, 30, a), width=3)
    bild.alpha_composite(vignette.filter(ImageFilter.GaussianBlur(9)))

    z = ImageDraw.Draw(bild, "RGBA")
    ort = {rid: (rand + (pos[rid][0] - minx) * m,
                 rand + 70 + (pos[rid][1] - miny) * m) for rid in raeume}

    # Verbindungen zuerst - sie liegen unter den Raeumen wie Bleistift
    # unter Tinte.
    for rid, raum in raeume.items():
        ox, oy = ort[rid]
        for tuer in raum["doors"]:
            ziel = tuer["target"]
            if ziel not in ort:
                continue
            zx, zy = ort[ziel]
            a = (ox + tuer["x"] * m, oy + tuer["y"] * m)
            # Von Tuer zu Tuer, nicht von Tuer zur Raummitte: sonst
            # laufen die Gaenge quer durch die Raeume, durch die sie gar
            # nicht fuehren.
            gegen = next((t for t in raeume[ziel]["doors"] if t["target"] == rid), None)
            b = ((zx + gegen["x"] * m, zy + gegen["y"] * m) if gegen else
                 (zx + raeume[ziel]["width"] / 2 * m,
                  zy + raeume[ziel]["height"] / 2 * m))
            gesperrt = bool(tuer.get("requires"))
            # Gesperrte Wege gestrichelt: der Kartograf kam da nicht durch.
            schritte = max(2, int(math.dist(a, b) / (m * 2)))
            for k in range(schritte):
                if gesperrt and k % 2:
                    continue
                t0, t1 = k / schritte, (k + 1) / schritte
                z.line([a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                        a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1],
                       fill=(*TINTE_HELL[:3], 110), width=max(1, int(m * 0.3)))

    for i, (rid, raum) in enumerate(sorted(raeume.items())):
        ox, oy = ort[rid]
        zeichne_raum_kunst(bild, raum, ox, oy, m, saat=i * 13 + 3)

    # Baenke: das Einzige, was auf so einer Karte wirklich eingezeichnet
    # gehoert. Man sucht darauf ja keine Kacheln, sondern den naechsten
    # Ort zum Ausruhen.
    for rid, raum in raeume.items():
        ox, oy = ort[rid]
        for bank in raum.get("benches", []):
            bx, by = ox + bank["x"] * m, oy + bank["y"] * m
            z.line([bx - m, by, bx + m, by], fill=TINTE, width=max(2, int(m * 0.4)))
            z.line([bx - m * 0.7, by, bx - m * 0.7, by + m * 0.8], fill=TINTE,
                   width=max(1, int(m * 0.3)))
            z.line([bx + m * 0.7, by, bx + m * 0.7, by + m * 0.8], fill=TINTE,
                   width=max(1, int(m * 0.3)))
            z.line([bx, by, bx, by - m * 1.3], fill=TINTE, width=max(1, int(m * 0.3)))
            z.ellipse([bx - m * 0.5, by - m * 2.1, bx + m * 0.5, by - m * 1.1],
                      outline=TINTE, width=max(1, int(m * 0.25)))
        if raum.get("boss"):
            b = raum["boss"]
            bx, by = ox + b["x"] * m, oy + b["y"] * m
            for k in range(3):
                rr = m * (1.6 + k * 1.5)
                z.ellipse([bx - rr, by - rr, bx + rr, by - rr + rr * 2],
                          outline=(*hexc("#8e2f36")[:3], 150 - k * 40),
                          width=max(1, int(m * 0.3)))

    # Beschriftung: Raumnamen klein an den Umriss, Regionsnamen gross und
    # schraeg quer darueber - wie ein Kartograf sie hinschreibt.
    klein = schrift(max(9, int(m * 2.1)))
    for rid, raum in sorted(raeume.items()):
        ox, oy = ort[rid]
        z.text((ox + 3, oy - m * 2.6), f'{rid}  {raum["name"].title()}',
               fill=(*TINTE[:3], 205), font=klein)

    gross = schrift(max(16, int(m * 5.2)), fett=True)
    for region, name in REGIONSNAMEN.items():
        drin = [r for r in raeume if raeume[r]["region"] == region]
        if not drin:
            continue
        # Ueber das Gebiet geschrieben, nicht mittendurch: quer ueber die
        # Raeume gelegt war der Name unlesbar und die Raeume auch.
        cx = sum(ort[r][0] + raeume[r]["width"] * m / 2 for r in drin) / len(drin)
        cy = min(ort[r][1] for r in drin) - m * 8
        marke = Image.new("RGBA", (int(len(name) * m * 4), int(m * 9)), (0, 0, 0, 0))
        ImageDraw.Draw(marke, "RGBA").text((0, 0), name,
                                           fill=(*TINTE[:3], 120), font=gross)
        marke = marke.rotate(-4, expand=True, resample=Image.BICUBIC)
        bild.alpha_composite(marke, (int(cx - marke.width / 2),
                                     int(cy - marke.height / 2)))

    kopf = schrift(max(20, int(m * 6)), fett=True)
    z.text((rand, 26), "RESONANZ", fill=TINTE, font=kopf)
    z.text((rand, 26 + int(m * 7)),
           "Aufgezeichnet, so weit die Gaenge trugen.  "
           "Gestrichelt: verschlossen.  Gabel: eine Bank.",
           fill=(*TINTE_HELL[:3], 220), font=klein)

    AUS_KUNST.parent.mkdir(exist_ok=True)
    bild.convert("RGB").save(AUS_KUNST)
    print(f"karte (gezeichnet) -> {AUS_KUNST} ({bild.width}x{bild.height})")


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
    build_kunst()
