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
        "hain": (hexc("#15211f"), hexc("#6ea78f"), hexc("#ffc46b"),
                 hexc("#8d9c9a"), hexc("#3f5a56")),
        "kathedrale": (hexc("#1a1826"), hexc("#7a6f9e"), hexc("#ffd08a"),
                       hexc("#9a93a8"), hexc("#4b4468")),
        "grotten": (hexc("#141d28"), hexc("#5f8bad"), hexc("#9ee0ff"),
                    hexc("#8ea3b5"), hexc("#3d5a75")),
        "dissonanz": (hexc("#1d1116"), hexc("#8a4352"), hexc("#ff8a5c"),
                      hexc("#6b4b52"), hexc("#4d2b36")),
    }

    # Vordergrund - fast schwarz, in jeder Region gleich.
    FOREGROUND = hexc("#080a10")


def hash01(x: int, y: int = 0) -> float:
    """Deterministischer Wert 0..1 aus zwei ganzen Zahlen."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) & 0xFFFFFFFF
    h = (h * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFFFF) / 0xFFFFFFFF


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
