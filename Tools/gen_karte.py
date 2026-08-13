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
    "bruecke": "DIE GROSSE BRUECKE",
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

    def entwirren(runden: int) -> bool:
        for _ in range(runden):
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
                return True
        return False

    # Gebiete bleiben beieinander.
    #
    # Das Auseinanderschieben allein kennt nur Raeume, keine Gegenden -
    # und schob deshalb einen Hainraum mitten zwischen die Kathedrale,
    # sobald dort Platz war. Auf der Karte stand dann ein gruener Fleck
    # im violetten Feld, und die Regionsnamen lagen quer ueber fremden
    # Raeumen.
    #
    # Also abwechselnd: alle Raeume ein Stueck zu ihrer eigenen Region
    # hin ziehen, dann wieder entwirren. Der Zug ist schwach genug, dass
    # die Anordnung aus den Tueren erhalten bleibt - er sortiert nur,
    # was sonst willkuerlich danebenrutscht.
    for durchgang in range(24):
        mitten: dict[str, tuple[float, float, int]] = {}
        for rid in ids:
            reg = raeume[rid]["region"]
            x, y = pos[rid]
            mx, my, n = mitten.get(reg, (0.0, 0.0, 0))
            mitten[reg] = (mx + x + raeume[rid]["width"] / 2,
                           my + y + raeume[rid]["height"] / 2, n + 1)
        for rid in ids:
            reg = raeume[rid]["region"]
            mx, my, n = mitten[reg]
            mx, my = mx / n, my / n
            x, y = pos[rid]
            zx = x + raeume[rid]["width"] / 2
            zy = y + raeume[rid]["height"] / 2
            pos[rid] = (int(round(x + (mx - zx) * 0.05)),
                        int(round(y + (my - zy) * 0.05)))
        if entwirren(120) and durchgang > 6:
            break
    entwirren(400)
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

# Die Karte ist dunkel, nicht hell.
#
# Der erste Anlauf war Tinte auf Pergament, und das war der falsche
# Gedanke: eine Karte auf hellem Grund macht aus einer Hoehlenwelt eine
# Wanderkarte. Die Vorbilder machen es umgekehrt - fast schwarzer Grund,
# und die Gebiete leuchten daraus hervor, jedes in seiner eigenen Farbe.
# Damit liest sich die Karte wie das Spiel: Licht in einer dunklen Welt.
GRUND = hexc("#080b14")
GRUND_HELL = hexc("#141b2c")
TINTE = hexc("#e8eef6")
TINTE_HELL = hexc("#7d8ba4")

# Jedes Gebiet hat eine Leuchtfarbe und eine dunklere Fuellung. Der Umriss
# leuchtet, die Flaeche bleibt zurueck - sonst blendet die Karte.
WASCHUNG = {
    "hain": (hexc("#8fd8a0"), hexc("#16301f")),
    "kathedrale": (hexc("#b9a6ef"), hexc("#211a35")),
    "grotten": (hexc("#7fd4f0"), hexc("#122736")),
    "dissonanz": (hexc("#f08a7a"), hexc("#2e1418")),
    "bruecke": (hexc("#b8c4d8"), hexc("#242b3a")),
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

    leucht, fuellung = WASCHUNG[raum["region"]]

    # Erst ein Schein nach aussen: der Raum leuchtet in den schwarzen
    # Grund hinein, statt scharf darin zu liegen.
    schein = Image.new("RGBA", bild.size, (0, 0, 0, 0))
    ImageDraw.Draw(schein, "RGBA").polygon(punkte, fill=(*leucht[:3], 70))
    bild.alpha_composite(schein.filter(ImageFilter.GaussianBlur(m * 1.6)))

    # Dann die Flaeche, dunkel und ruhig.
    flaeche = Image.new("RGBA", bild.size, (0, 0, 0, 0))
    ImageDraw.Draw(flaeche, "RGBA").polygon(punkte, fill=(*fuellung[:3], 246))
    bild.alpha_composite(flaeche)

    z = ImageDraw.Draw(bild, "RGBA")
    # Der Umriss ist die Lichtquelle: zweimal gezogen, innen hell, aussen
    # als weicher Saum.
    z.line(punkte + [punkte[0]], fill=(*leucht[:3], 120),
           width=max(3, int(m * 0.8)), joint="curve")
    z.line(punkte + [punkte[0]], fill=(*leucht[:3], 255),
           width=max(1, int(m * 0.32)), joint="curve")

    # Der Boden bekommt eine hellere Kante als die Decke: so sieht man,
    # wo in einem Raum gelaufen wird.
    boden = [(ox + x * m, oy + (unten[x] + 1) * m) for x in range(breite)]
    z.line(zittern(boden, m * 0.3, saat + 5), fill=(*leucht[:3], 200),
           width=max(2, int(m * 0.5)), joint="curve")

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

    bild = Image.new("RGBA", (breite, hoehe), GRUND)

    # Der Grund ist nicht einfach schwarz: ein paar sehr dunkle Schwaden
    # darin geben ihm Tiefe, ohne dass etwas darauf ablenkt.
    dunst = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    dz = ImageDraw.Draw(dunst, "RGBA")
    for i in range(70):
        x = hash01(i, 41) * breite
        y = hash01(i, 53) * hoehe
        r = 60 + hash01(i, 67) * 200
        dz.ellipse([x - r, y - r * 0.5, x + r, y + r * 0.5],
                   fill=(*GRUND_HELL[:3], 26))
    bild.alpha_composite(dunst.filter(ImageFilter.GaussianBlur(40)))

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
            leucht = WASCHUNG[raum["region"]][0]
            # Gesperrte Wege gestrichelt: da kam man beim ersten Mal nicht
            # durch.
            schritte = max(2, int(math.dist(a, b) / (m * 2)))
            for k in range(schritte):
                if gesperrt and k % 2:
                    continue
                t0, t1 = k / schritte, (k + 1) / schritte
                z.line([a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                        a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1],
                       fill=(*leucht[:3], 90), width=max(1, int(m * 0.3)))

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
            gabel = hexc("#ffe9a8")
            z.line([bx - m, by, bx + m, by], fill=gabel, width=max(2, int(m * 0.4)))
            z.line([bx - m * 0.7, by, bx - m * 0.7, by + m * 0.8], fill=gabel,
                   width=max(1, int(m * 0.3)))
            z.line([bx + m * 0.7, by, bx + m * 0.7, by + m * 0.8], fill=gabel,
                   width=max(1, int(m * 0.3)))
            z.line([bx, by, bx, by - m * 1.3], fill=gabel, width=max(1, int(m * 0.3)))
            z.ellipse([bx - m * 0.5, by - m * 2.1, bx + m * 0.5, by - m * 1.1],
                      outline=gabel, width=max(1, int(m * 0.25)))
        if raum.get("boss"):
            b = raum["boss"]
            bx, by = ox + b["x"] * m, oy + b["y"] * m
            for k in range(3):
                rr = m * (1.6 + k * 1.5)
                z.ellipse([bx - rr, by - rr, bx + rr, by - rr + rr * 2],
                          outline=(*hexc("#ff6a5c")[:3], 210 - k * 55),
                          width=max(1, int(m * 0.3)))

    # Beschriftung: Raumnamen klein an den Umriss, Regionsnamen gross und
    # schraeg quer darueber - wie ein Kartograf sie hinschreibt.
    klein = schrift(max(9, int(m * 2.1)))
    for rid, raum in sorted(raeume.items()):
        ox, oy = ort[rid]
        z.text((ox + 3, oy - m * 2.6), f'{rid}  {raum["name"].title()}',
               fill=(*TINTE_HELL[:3], 235), font=klein)

    gross = schrift(max(16, int(m * 5.2)), fett=True)
    for region, name in REGIONSNAMEN.items():
        drin = [r for r in raeume if raeume[r]["region"] == region]
        if not drin:
            continue
        # Ueber das Gebiet geschrieben, nicht mittendurch: quer ueber die
        # Raeume gelegt war der Name unlesbar und die Raeume auch.
        # Ueber die Mitte des Gebiets, aber ueber *seinen* obersten Raum -
        # nicht ueber den obersten Raum an dieser Stelle. Sonst schreibt
        # sich der Name eines Gebiets in ein anderes hinein.
        cx = sum(ort[r][0] + raeume[r]["width"] * m / 2 for r in drin) / len(drin)
        cy = min(ort[r][1] for r in drin) - m * 9

        # Und wenn dort schon ein Raum steht, weiter nach oben, bis frei
        # ist. Ein Titel quer ueber einem Umriss macht beide unlesbar.
        breite = len(name) * m * 2.2
        for _ in range(30):
            frei = True
            for rid, raum in raeume.items():
                rx, ry = ort[rid]
                if (abs(rx + raum["width"] * m / 2 - cx) < (breite + raum["width"] * m) / 2
                        and ry - m * 3 < cy < ry + raum["height"] * m + m * 3):
                    frei = False
                    break
            if frei:
                break
            cy -= m * 3
        marke = Image.new("RGBA", (int(len(name) * m * 4), int(m * 9)), (0, 0, 0, 0))
        ImageDraw.Draw(marke, "RGBA").text((0, 0), name,
                                           fill=(*WASCHUNG[region][0][:3], 190),
                                           font=gross)
        marke = marke.rotate(-4, expand=True, resample=Image.BICUBIC)
        bild.alpha_composite(marke, (int(cx - marke.width / 2),
                                     int(cy - marke.height / 2)))

    kopf = schrift(max(20, int(m * 6)), fett=True)
    z.text((rand, 26), "RESONANZ", fill=TINTE, font=kopf)
    z.text((rand, 26 + int(m * 7)),
           "Die ganze Welt.  Gestrichelt: verschlossen.  Gabel: eine Bank.",
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
