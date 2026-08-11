"""
pixelkit - winzige Pixel-Art-Bibliothek fuer die Asset-Pipeline von RESONANZ.

Alle Grafiken des Spiels werden hier prozedural erzeugt: keine binaeren
Assets im Repository, nur der Code der sie herstellt. Das haelt das Repo
klein und macht Farbstimmungen global anpassbar.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

RGBA = tuple[int, int, int, int]


# --------------------------------------------------------------- Farbwelt

def hexc(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))  # type: ignore[return-value]


def shade(c: RGBA, amount: float) -> RGBA:
    """amount < 0 dunkler, > 0 heller."""
    target: RGBA = (255, 255, 255, c[3]) if amount > 0 else (0, 0, 0, c[3])
    return mix(c, target, abs(amount))


class Palette:
    """Die Farbwelt der Regionen. Kalt, tief, mit Glasur aus Klanglicht."""

    # Grundtoene
    VOID = hexc("#05060c")
    INK = hexc("#0a0d18")
    INK2 = hexc("#131a2e")
    STONE = hexc("#243047")
    STONE_HI = hexc("#3a4a68")
    STONE_LO = hexc("#161e30")

    # Klanglicht
    GLOW = hexc("#7fe8d8")
    GLOW_DIM = hexc("#3f8f88")
    BLOOM = hexc("#e6b3ff")
    BLOOM_DIM = hexc("#8a5fae")
    WARM = hexc("#ffd9a0")
    GOLD = hexc("#f2b955")

    # Dissonanz
    ROT = hexc("#c2415f")
    ROT_DIM = hexc("#6d2338")
    BILE = hexc("#8fa03c")

    # Cadence.
    #
    # Sie ist keine Person, sie ist eine Form: bleiche Maske, ein Auge,
    # darueber die zwei Zinken einer Stimmgabel. Das liest sich auch bei
    # zwanzig Pixeln noch - ein Gesicht taete das nicht.
    BONE = hexc("#e9e3d2")
    BONE_SH = hexc("#a89f8b")
    BONE_LO = hexc("#6e6757")
    CLOAK = hexc("#161923")
    CLOAK_HI = hexc("#272d3d")
    CLOAK_LO = hexc("#0a0c12")
    EYE = hexc("#090a10")
    AMBER = hexc("#ffb454")
    TRIM = hexc("#7fe8d8")

    # Regionsfarben: Boden, Kante, Akzent, Himmel, Ferne.
    #
    # Die Ordnung der Helligkeiten traegt das ganze Bild. Der Himmel ist
    # der hellste Wert, davor stehen die fernen Silhouetten, dann der
    # begehbare Fels, und ganz vorn liegt Fast-Schwarz. Wer alles gleich
    # dunkel haelt, bekommt Matsch - egal wie sauber die Kacheln sind.
    REGIONS = {
        # Der begehbare Fels ist dunkel; sichtbar wird er ueber seine
        # beleuchtete Oberkante. Das ist der Griff, der Vordergrund von
        # Hintergrund trennt, ohne dass Nebel noetig waere.
        # Der Dunst ist kalt, das Holz ist warm. Dieser eine Gegensatz
        # traegt mehr als jede zusaetzliche Farbe: kuehler Hintergrund,
        # warme Masse davor - und ein einziger warmer Akzent im Licht.
        "hain": (hexc("#16211d"), hexc("#79a78c"), hexc("#ffc46b"),
                 hexc("#7d8d95"), hexc("#6b4f3c")),
        "kathedrale": (hexc("#1b1824"), hexc("#8c7ba0"), hexc("#ffd08a"),
                       hexc("#8f8ba0"), hexc("#5a4148")),
        "grotten": (hexc("#141d28"), hexc("#6a9bc0"), hexc("#9ee0ff"),
                    hexc("#8ea3b5"), hexc("#3c4a66")),
        "dissonanz": (hexc("#1d1116"), hexc("#a04d5c"), hexc("#ff8a5c"),
                      hexc("#6e5158"), hexc("#54303a")),
    }

    # Vordergrund - fast schwarz, in jeder Region gleich.
    FOREGROUND = hexc("#080a10")


def hash01(x: int, y: int = 0) -> float:
    """Deterministischer Wert 0..1 aus zwei ganzen Zahlen."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) & 0xFFFFFFFF
    h = (h * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFFFF) / 0xFFFFFFFF



# --------------------------------------------------------- Zeichenwerkzeug
#
# Was hier steht, ist der Pinselkasten. Streuung allein macht noch kein Bild -
# es braucht Striche, die sich verjuengen, Massen, die Beulen haben, und
# Verlaeufe, die im Raster gerastert sind statt weichgezeichnet.

BAYER8 = [
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]


def bezier(p0, p1, p2, p3, steps: int = 24):
    """Punkte einer kubischen Bezierkurve."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = (u ** 3 * p0[0] + 3 * u * u * t * p1[0]
             + 3 * u * t * t * p2[0] + t ** 3 * p3[0])
        y = (u ** 3 * p0[1] + 3 * u * u * t * p1[1]
             + 3 * u * t * t * p2[1] + t ** 3 * p3[1])
        out.append((x, y))
    return out


# --------------------------------------------------------------- Leinwand

class Canvas:
    """Ein kleines RGBA-Pixelraster mit zeichnerischen Grundformen."""

    def __init__(self, w: int, h: int, fill: RGBA = (0, 0, 0, 0)):
        self.w = w
        self.h = h
        self.px = [list(fill) for _ in range(w * h)]

    # ---- Grundoperationen

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x: int, y: int, c: RGBA | None) -> None:
        if c is None or not self.inside(int(x), int(y)):
            return
        self.px[int(y) * self.w + int(x)] = list(c)

    def get(self, x: int, y: int) -> RGBA:
        if not self.inside(int(x), int(y)):
            return (0, 0, 0, 0)
        return tuple(self.px[int(y) * self.w + int(x)])  # type: ignore[return-value]

    def blend(self, x: int, y: int, c: RGBA) -> None:
        """Alpha-Blending eines Pixels."""
        if not self.inside(int(x), int(y)):
            return
        dst = self.get(x, y)
        sa = c[3] / 255.0
        if sa <= 0:
            return
        da = dst[3] / 255.0
        out_a = sa + da * (1 - sa)
        if out_a <= 0:
            self.set(x, y, (0, 0, 0, 0))
            return
        out = tuple(
            int(round((c[i] * sa + dst[i] * da * (1 - sa)) / out_a)) for i in range(3)
        )
        self.set(x, y, (out[0], out[1], out[2], int(round(out_a * 255))))

    # ---- Formen

    def rect(self, x: int, y: int, w: int, h: int, c: RGBA) -> None:
        for j in range(int(y), int(y + h)):
            for i in range(int(x), int(x + w)):
                self.set(i, j, c)

    def rect_blend(self, x: int, y: int, w: int, h: int, c: RGBA) -> None:
        for j in range(int(y), int(y + h)):
            for i in range(int(x), int(x + w)):
                self.blend(i, j, c)

    def frame(self, x: int, y: int, w: int, h: int, c: RGBA) -> None:
        self.rect(x, y, w, 1, c)
        self.rect(x, y + h - 1, w, 1, c)
        self.rect(x, y, 1, h, c)
        self.rect(x + w - 1, y, 1, h, c)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c: RGBA, blend: bool = False) -> None:
        if rx <= 0 or ry <= 0:
            return
        for j in range(int(math.floor(cy - ry)), int(math.ceil(cy + ry)) + 1):
            for i in range(int(math.floor(cx - rx)), int(math.ceil(cx + rx)) + 1):
                dx = (i + 0.5 - cx) / rx
                dy = (j + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    if blend:
                        self.blend(i, j, c)
                    else:
                        self.set(i, j, c)

    def ring(self, cx: float, cy: float, r: float, thickness: float, c: RGBA) -> None:
        outer = r + thickness / 2
        inner = max(0.0, r - thickness / 2)
        for j in range(int(cy - outer) - 1, int(cy + outer) + 2):
            for i in range(int(cx - outer) - 1, int(cx + outer) + 2):
                d = math.hypot(i + 0.5 - cx, j + 0.5 - cy)
                if inner <= d <= outer:
                    self.blend(i, j, c)

    def line(self, x0: float, y0: float, x1: float, y1: float, c: RGBA) -> None:
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def glow(self, cx: float, cy: float, radius: float, c: RGBA, power: float = 2.0) -> None:
        """Weicher radialer Schein - additive Anmutung ueber Alpha."""
        for j in range(int(cy - radius) - 1, int(cy + radius) + 2):
            for i in range(int(cx - radius) - 1, int(cx + radius) + 2):
                d = math.hypot(i + 0.5 - cx, j + 0.5 - cy) / radius
                if d >= 1:
                    continue
                a = (1 - d) ** power
                self.blend(i, j, (c[0], c[1], c[2], int(c[3] * a)))


    # ---- Malerische Werkzeuge

    def dither_v(self, x: int, y: int, w: int, h: int, top: RGBA, bottom: RGBA,
                 levels: int = 6) -> None:
        """
        Senkrechter Verlauf, im Raster gerastert.

        Ein weicher Verlauf sieht in Pixelgrafik nach Weichzeichner aus. Mit
        einer geordneten Rasterung bleibt die Kante hart, und man sieht dem
        Bild an, dass es aus Pixeln besteht - das ist der Punkt.
        """
        for j in range(int(y), int(y + h)):
            t = (j - y) / max(1, h - 1)
            step = t * (levels - 1)
            low = int(math.floor(step))
            frac = step - low
            c_low = mix(top, bottom, low / max(1, levels - 1))
            c_high = mix(top, bottom, min(levels - 1, low + 1) / max(1, levels - 1))
            for i in range(int(x), int(x + w)):
                threshold = BAYER8[j % 8][i % 8] / 64.0
                self.set(i, j, c_high if frac > threshold else c_low)

    def stroke(self, points, w0: float, w1: float, c: RGBA,
               taper: float = 1.0) -> None:
        """Ein Strich entlang einer Kurve, der sich verjuengt."""
        n = max(1, len(points) - 1)
        for i, (px, py) in enumerate(points):
            t = (i / n) ** taper
            w = w0 + (w1 - w0) * t
            if w <= 0:
                continue
            self.ellipse(px, py, max(0.5, w / 2), max(0.5, w / 2), c)

    def blob(self, cx: float, cy: float, r: float, c: RGBA, rng: "Rng",
             lumps: int = 7, squash: float = 1.0) -> None:
        """
        Eine organische Masse aus ueberlappenden Beulen.

        Ein Kreis wirkt gestanzt, ein Rechteck tot. Erst die unregelmaessige
        Kante laesst etwas gewachsen aussehen.
        """
        self.ellipse(cx, cy, r, r * squash, c)
        for i in range(lumps):
            a = i / lumps * math.tau + rng.range(-0.3, 0.3)
            d = r * rng.range(0.45, 0.85)
            rr = r * rng.range(0.35, 0.62)
            self.ellipse(cx + math.cos(a) * d, cy + math.sin(a) * d * squash,
                         rr, rr * squash, c)

    def branch(self, x: float, y: float, angle: float, length: float,
               width: float, depth: int, c: RGBA, rng: "Rng",
               leaf: RGBA | None = None, curve: float = 0.35) -> None:
        """
        Ein Ast, der sich verzweigt und dabei duenner wird.

        Rekursiv, weil Baeume das auch sind. Die Kruemmung kommt aus einer
        Bezierkurve - gerade Aeste sehen aus wie Streichhoelzer.
        """
        if depth <= 0 or length < 3:
            if leaf is not None:
                self.blob(x, y, max(2.0, width * 2.2), leaf, rng, lumps=5, squash=0.8)
            return

        bend = rng.range(-curve, curve)
        ex = x + math.cos(angle) * length
        ey = y + math.sin(angle) * length
        cx1 = x + math.cos(angle + bend * 0.5) * length * 0.4
        cy1 = y + math.sin(angle + bend * 0.5) * length * 0.4
        cx2 = x + math.cos(angle + bend) * length * 0.75
        cy2 = y + math.sin(angle + bend) * length * 0.75
        pts = bezier((x, y), (cx1, cy1), (cx2, cy2), (ex, ey), max(6, int(length / 3)))
        self.stroke(pts, width, width * 0.55, c)

        tip_x, tip_y = pts[-1]
        forks = 2 if depth > 1 else rng.int(1, 2)
        for k in range(forks):
            spread = rng.range(0.28, 0.72) * (1 if k % 2 == 0 else -1)
            self.branch(tip_x, tip_y, angle + bend + spread,
                        length * rng.range(0.55, 0.78), width * 0.62,
                        depth - 1, c, rng, leaf, curve)

    def chain(self, x: float, y0: float, y1: float, c: RGBA,
              link: int = 4) -> None:
        """Eine Kette aus einzelnen Gliedern, nicht aus einem Strich."""
        y = y0
        i = 0
        while y < y1:
            if i % 2 == 0:
                self.rect(int(x), int(y), 1, min(link, int(y1 - y)), c)
            else:
                self.rect(int(x) - 1, int(y), 3, 1, c)
                self.rect(int(x) - 1, int(y + link - 1), 3, 1, c)
                self.set(int(x) - 1, int(y + 1), c)
                self.set(int(x) + 1, int(y + 1), c)
            y += link
            i += 1

    def gothic_arch(self, cx: float, top: float, w: float, h: float,
                    c: RGBA, filled: bool = True) -> None:
        """Ein Spitzbogen. Fuellt nach unten, wenn `filled`."""
        half = w / 2
        for j in range(int(h)):
            t = j / max(1, h)
            # Zwei Kreisboegen, die sich oben treffen: der Spitzbogen.
            span = half * math.sqrt(max(0.0, 1 - (1 - t) ** 2))
            if filled:
                self.rect(int(cx - span), int(top + j), max(1, int(span * 2)), 1, c)
            else:
                self.set(int(cx - span), int(top + j), c)
                self.set(int(cx + span), int(top + j), c)

    def rough_edge(self, x: int, y: int, w: int, amount: int, c: RGBA | None,
                   seed: int = 0) -> None:
        """Franst eine waagerechte Kante aus, damit sie nicht gestanzt wirkt."""
        for i in range(w):
            d = int(hash01(x + i, seed) * amount)
            for k in range(d):
                self.set(x + i, y + k, c)

    # ---- Nachbearbeitung

    def outline(self, c: RGBA, diagonal: bool = False) -> None:
        """Legt eine Kontur um alle undurchsichtigen Pixel."""
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            offsets += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        todo = []
        for y in range(self.h):
            for x in range(self.w):
                if self.get(x, y)[3] > 0:
                    continue
                for ox, oy in offsets:
                    if self.inside(x + ox, y + oy) and self.get(x + ox, y + oy)[3] > 128:
                        todo.append((x, y))
                        break
        for x, y in todo:
            self.set(x, y, c)

    def shadow_pass(self, direction: tuple[int, int] = (0, 1), amount: float = -0.28) -> None:
        """Dunkelt Pixel ab, ueber denen bereits Material liegt (Fake-AO)."""
        dx, dy = direction
        snapshot = [tuple(p) for p in self.px]

        def sget(x: int, y: int) -> RGBA:
            if not self.inside(x, y):
                return (0, 0, 0, 0)
            return snapshot[y * self.w + x]  # type: ignore[return-value]

        for y in range(self.h):
            for x in range(self.w):
                cur = sget(x, y)
                if cur[3] < 200:
                    continue
                above = sget(x - dx, y - dy)
                if above[3] > 200:
                    self.set(x, y, shade(cur, amount))

    def mirrored(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                out.set(self.w - 1 - x, y, self.get(x, y))
        return out

    def to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h))
        img.putdata([tuple(p) for p in self.px])  # type: ignore[arg-type]
        return img

    def paste_into(self, dst: "Canvas", ox: int, oy: int) -> None:
        for y in range(self.h):
            for x in range(self.w):
                c = self.get(x, y)
                if c[3] > 0:
                    dst.blend(ox + x, oy + y, c)


# --------------------------------------------------------------- Atlas

@dataclass
class Frame:
    name: str
    canvas: Canvas
    pivot: tuple[float, float] = (0.5, 1.0)  # Fusspunkt-Ursprung
    meta: dict = field(default_factory=dict)


class Atlas:
    """Packt Frames zeilenweise in eine Textur und schreibt ein JSON dazu."""

    def __init__(self, name: str, padding: int = 1, max_width: int = 512):
        self.name = name
        self.padding = padding
        self.max_width = max_width
        self.frames: list[Frame] = []

    def add(self, name: str, canvas: Canvas, pivot=(0.5, 1.0), **meta) -> None:
        self.frames.append(Frame(name, canvas, pivot, meta))

    def add_sequence(self, base: str, canvases: list[Canvas], pivot=(0.5, 1.0), **meta) -> None:
        for i, c in enumerate(canvases):
            self.add(f"{base}_{i}", c, pivot, **meta)

    def pack(self) -> tuple[Image.Image, dict]:
        pad = self.padding
        rows: list[list[Frame]] = []
        row: list[Frame] = []
        x = pad
        row_h = 0
        for f in sorted(self.frames, key=lambda f: -f.canvas.h):
            if x + f.canvas.w + pad > self.max_width and row:
                rows.append(row)
                row = []
                x = pad
            row.append(f)
            x += f.canvas.w + pad
            row_h = max(row_h, f.canvas.h)
        if row:
            rows.append(row)

        total_h = pad
        for r in rows:
            total_h += max(f.canvas.h for f in r) + pad
        width = self.max_width

        sheet = Canvas(width, max(total_h, 1))
        entries = {}
        y = pad
        for r in rows:
            x = pad
            h = max(f.canvas.h for f in r)
            for f in r:
                f.canvas.paste_into(sheet, x, y)
                entries[f.name] = {
                    "x": x, "y": y, "w": f.canvas.w, "h": f.canvas.h,
                    "pivotX": f.pivot[0], "pivotY": f.pivot[1],
                    **f.meta,
                }
                x += f.canvas.w + pad
            y += h + pad

        meta = {
            "atlas": self.name,
            "width": width,
            "height": sheet.h,
            "frames": entries,
        }
        return sheet.to_image(), meta

    def write(self, out_dir: Path) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        img, meta = self.pack()
        png = out_dir / f"{self.name}.png"
        js = out_dir / f"{self.name}.json"
        img.save(png)
        js.write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return png, js


# --------------------------------------------------------------- Zufall

class Rng:
    """Deterministischer PRNG, damit Builds reproduzierbar sind."""

    def __init__(self, seed: int = 1):
        self.s = seed & 0xFFFFFFFF or 1

    def next(self) -> float:
        self.s ^= (self.s << 13) & 0xFFFFFFFF
        self.s ^= self.s >> 17
        self.s ^= (self.s << 5) & 0xFFFFFFFF
        self.s &= 0xFFFFFFFF
        return self.s / 0xFFFFFFFF

    def range(self, a: float, b: float) -> float:
        return a + self.next() * (b - a)

    def int(self, a: int, b: int) -> int:
        return int(math.floor(self.range(a, b + 1 - 1e-9)))

    def chance(self, p: float) -> bool:
        return self.next() < p

    def pick(self, seq):
        return seq[self.int(0, len(seq) - 1)]
