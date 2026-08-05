"""A tiny pixel canvas — the drawing primitive every generator builds on.

Deliberately not numpy: sprites are at most a few thousand pixels, and plain
lists keep the whole pipeline dependency-free apart from Pillow (used only to
write PNGs at the very end).
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

from .palette import RGBA, TRANSPARENT, Ramp, with_alpha


def blend(dst: RGBA, src: RGBA) -> RGBA:
    """Standard source-over alpha blend."""
    sa = src[3]
    if sa == 255 or dst[3] == 0:
        return src
    if sa == 0:
        return dst
    a_s = sa / 255.0
    a_d = dst[3] / 255.0
    out_a = a_s + a_d * (1 - a_s)
    if out_a <= 0:
        return TRANSPARENT
    return (
        round((src[0] * a_s + dst[0] * a_d * (1 - a_s)) / out_a),
        round((src[1] * a_s + dst[1] * a_d * (1 - a_s)) / out_a),
        round((src[2] * a_s + dst[2] * a_d * (1 - a_s)) / out_a),
        round(out_a * 255),
    )


class Canvas:
    """Mutable RGBA raster with pixel-art drawing helpers."""

    __slots__ = ("w", "h", "px")

    def __init__(self, w: int, h: int, fill: RGBA = TRANSPARENT) -> None:
        self.w = w
        self.h = h
        self.px: list[RGBA] = [fill] * (w * h)

    # -- basics ------------------------------------------------------------

    def copy(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.px = list(self.px)
        return out

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x: int, y: int) -> RGBA:
        if not self.inside(x, y):
            return TRANSPARENT
        return self.px[y * self.w + x]

    def set(self, x: int, y: int, color: RGBA) -> None:
        """Hard write, ignoring alpha compositing."""
        if self.inside(x, y):
            self.px[y * self.w + x] = color

    def put(self, x: int, y: int, color: RGBA) -> None:
        """Alpha-blended write — the default for drawing."""
        x, y = round(x), round(y)
        if not self.inside(x, y) or color[3] == 0:
            return
        i = y * self.w + x
        self.px[i] = blend(self.px[i], color)

    def is_empty(self) -> bool:
        return all(p[3] == 0 for p in self.px)

    # -- shapes ------------------------------------------------------------

    def fill(self, color: RGBA) -> None:
        self.px = [color] * (self.w * self.h)

    def rect(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        """Filled rectangle. Width/height are inclusive of the origin pixel."""
        # Generators freely mix floats into coordinate maths; rounding here
        # instead of at every call site keeps the drawing DSL readable.
        x, y, w, h = round(x), round(y), round(w), round(h)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, color)

    def frame(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        """One-pixel outlined rectangle."""
        x, y, w, h = round(x), round(y), round(w), round(h)
        for xx in range(x, x + w):
            self.put(xx, y, color)
            self.put(xx, y + h - 1, color)
        for yy in range(y, y + h):
            self.put(x, yy, color)
            self.put(x + w - 1, yy, color)

    def hline(self, x: int, y: int, w: int, color: RGBA) -> None:
        x, y, w = round(x), round(y), round(w)
        for xx in range(x, x + w):
            self.put(xx, y, color)

    def vline(self, x: int, y: int, h: int, color: RGBA) -> None:
        x, y, h = round(x), round(y), round(h)
        for yy in range(y, y + h):
            self.put(x, yy, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: RGBA) -> None:
        """Bresenham — no anti-aliasing, this is pixel art."""
        x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, color: RGBA,
                filled: bool = True) -> None:
        """Ellipse by scanline test — rounder at small sizes than midpoint."""
        if rx <= 0 or ry <= 0:
            return
        y0 = int(math.floor(cy - ry))
        y1 = int(math.ceil(cy + ry))
        x0 = int(math.floor(cx - rx))
        x1 = int(math.ceil(cx + rx))
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                dx = (xx + 0.5 - cx) / rx
                dy = (yy + 0.5 - cy) / ry
                d = dx * dx + dy * dy
                if d <= 1.0:
                    if filled or d >= 0.45:
                        self.put(xx, yy, color)

    def disc(self, cx: float, cy: float, r: float, color: RGBA) -> None:
        self.ellipse(cx, cy, r, r, color)

    def triangle(self, p0: tuple[int, int], p1: tuple[int, int],
                 p2: tuple[int, int], color: RGBA) -> None:
        pts = [p0, p1, p2]
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)
        for y in range(min_y, max_y + 1):
            xs: list[float] = []
            for i in range(3):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 3]
                if ay == by:
                    continue
                if min(ay, by) <= y <= max(ay, by):
                    t = (y - ay) / (by - ay)
                    xs.append(ax + (bx - ax) * t)
            if len(xs) >= 2:
                for x in range(int(round(min(xs))), int(round(max(xs))) + 1):
                    self.put(x, y, color)

    def polygon(self, points: Sequence[tuple[int, int]], color: RGBA) -> None:
        if len(points) < 3:
            return
        for i in range(1, len(points) - 1):
            self.triangle(points[0], points[i], points[i + 1], color)

    # -- region operations -------------------------------------------------

    def flood_fill(self, x: int, y: int, color: RGBA) -> None:
        target = self.get(x, y)
        if target == color:
            return
        stack = [(x, y)]
        seen = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen or not self.inside(cx, cy):
                continue
            seen.add((cx, cy))
            if self.get(cx, cy) != target:
                continue
            self.set(cx, cy, color)
            stack.extend(((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)))

    def replace(self, old: RGBA, new: RGBA) -> None:
        self.px = [new if p == old else p for p in self.px]

    def map_pixels(self, fn: Callable[[int, int, RGBA], RGBA]) -> None:
        for y in range(self.h):
            row = y * self.w
            for x in range(self.w):
                self.px[row + x] = fn(x, y, self.px[row + x])

    def recolor(self, mapping: dict[RGBA, RGBA]) -> None:
        self.px = [mapping.get(p, p) for p in self.px]

    # -- compositing -------------------------------------------------------

    def blit(self, other: "Canvas", dx: int, dy: int,
             alpha: float = 1.0) -> None:
        dx, dy = round(dx), round(dy)
        for y in range(other.h):
            ty = dy + y
            if ty < 0 or ty >= self.h:
                continue
            for x in range(other.w):
                c = other.px[y * other.w + x]
                if c[3] == 0:
                    continue
                if alpha < 1.0:
                    c = with_alpha(c, round(c[3] * alpha))
                self.put(dx + x, ty, c)

    def blit_masked(self, other: "Canvas", dx: int, dy: int,
                    color: RGBA) -> None:
        """Stamp ``other``'s silhouette in a flat colour (shadows, flashes)."""
        for y in range(other.h):
            for x in range(other.w):
                if other.px[y * other.w + x][3] > 0:
                    self.put(dx + x, dy + y, color)

    # -- transforms --------------------------------------------------------

    def flipped_x(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                out.px[y * self.w + (self.w - 1 - x)] = self.px[y * self.w + x]
        return out

    def flipped_y(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            src = y * self.w
            dst = (self.h - 1 - y) * self.w
            out.px[dst:dst + self.w] = self.px[src:src + self.w]
        return out

    def translated(self, dx: int, dy: int) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.blit(self, dx, dy)
        return out

    def rotated(self, degrees: float) -> "Canvas":
        """Nearest-neighbour rotation about the centre, same canvas size."""
        rad = math.radians(-degrees)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        cx, cy = self.w / 2.0, self.h / 2.0
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                ox = x + 0.5 - cx
                oy = y + 0.5 - cy
                sx = int(math.floor(ox * cos_a - oy * sin_a + cx))
                sy = int(math.floor(ox * sin_a + oy * cos_a + cy))
                if self.inside(sx, sy):
                    out.px[y * self.w + x] = self.px[sy * self.w + sx]
        return out

    def scaled(self, factor: int) -> "Canvas":
        out = Canvas(self.w * factor, self.h * factor)
        for y in range(out.h):
            sy = y // factor
            for x in range(out.w):
                out.px[y * out.w + x] = self.px[sy * self.w + (x // factor)]
        return out

    def padded(self, left: int, top: int, right: int, bottom: int) -> "Canvas":
        out = Canvas(self.w + left + right, self.h + top + bottom)
        out.blit(self, left, top)
        return out

    def cropped(self, x: int, y: int, w: int, h: int) -> "Canvas":
        out = Canvas(w, h)
        for yy in range(h):
            for xx in range(w):
                out.set(xx, yy, self.get(x + xx, y + yy))
        return out

    def trimmed(self) -> tuple["Canvas", int, int]:
        """Crop away fully transparent borders; returns (canvas, offx, offy)."""
        min_x, min_y, max_x, max_y = self.w, self.h, -1, -1
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y * self.w + x][3] > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        if max_x < 0:
            return Canvas(1, 1), 0, 0
        return (self.cropped(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1),
                min_x, min_y)

    # -- stylistic passes --------------------------------------------------

    def outline(self, color: RGBA, diagonal: bool = False,
                only_below: bool = False) -> None:
        """Wrap the opaque silhouette in a 1px border.

        ``only_below`` draws the border on the bottom edge alone, which is how
        a top-down sprite gets its contact shadow without gaining a sticker
        outline all the way around.
        """
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            offsets += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        if only_below:
            offsets = [(0, 1)]
        edge: list[tuple[int, int]] = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y * self.w + x][3] > 0:
                    continue
                for ox, oy in offsets:
                    nx, ny = x - ox, y - oy
                    if self.inside(nx, ny) and self.px[ny * self.w + nx][3] > 0:
                        edge.append((x, y))
                        break
        for x, y in edge:
            self.set(x, y, color)

    def shade_edges(self, ramp: Ramp, light: tuple[int, int] = (-1, -1),
                    depth: int = 1) -> None:
        """Darken pixels facing away from the light, brighten those facing it.

        Works on ramp membership, so it only touches pixels that actually
        belong to ``ramp`` and leaves other materials alone.
        """
        index_of = {c: i for i, c in enumerate(ramp.colors)}
        lx, ly = light
        snapshot = list(self.px)

        def at(x: int, y: int) -> RGBA:
            if not self.inside(x, y):
                return TRANSPARENT
            return snapshot[y * self.w + x]

        for y in range(self.h):
            for x in range(self.w):
                c = snapshot[y * self.w + x]
                idx = index_of.get(c)
                if idx is None:
                    continue
                lit = at(x + lx * depth, y + ly * depth)[3] == 0
                dark = at(x - lx * depth, y - ly * depth)[3] == 0
                if lit and not dark:
                    self.set(x, y, ramp[idx + 1])
                elif dark and not lit:
                    self.set(x, y, ramp[idx - 1])

    def dither(self, x: int, y: int, w: int, h: int, color: RGBA,
               phase: int = 0, density: int = 2) -> None:
        """Checkerboard dither — used for gradients and glass."""
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if (xx + yy + phase) % density == 0:
                    self.put(xx, yy, color)

    def vertical_gradient(self, x: int, y: int, w: int, h: int,
                          ramp: Ramp, top_index: int = 4,
                          bottom_index: int = 1) -> None:
        """Banded gradient with a dithered seam between bands."""
        if h <= 0:
            return
        span = top_index - bottom_index
        for yy in range(h):
            t = yy / max(1, h - 1)
            exact = top_index - span * t
            low = int(math.floor(exact))
            frac = exact - low
            self.hline(x, y + yy, w, ramp[low])
            if frac > 0.5:
                self.dither(x, y + yy, w, 1, ramp[low + 1], phase=yy)

    def scanline_shade(self, ramp: Ramp, every: int = 3) -> None:
        """Subtle horizontal banding — reads as material texture at 1x zoom."""
        index_of = {c: i for i, c in enumerate(ramp.colors)}
        for y in range(self.h):
            if y % every:
                continue
            for x in range(self.w):
                idx = index_of.get(self.px[y * self.w + x])
                if idx is not None and idx > 0:
                    self.set(x, y, ramp[idx - 1])

    def speckle(self, rng, color: RGBA, count: int,
                area: tuple[int, int, int, int] | None = None) -> None:
        x0, y0, w, h = area or (0, 0, self.w, self.h)
        for _ in range(count):
            x = rng.randint(x0, x0 + w - 1)
            y = rng.randint(y0, y0 + h - 1)
            if self.get(x, y)[3] > 0:
                self.put(x, y, color)

    def drop_shadow(self, color: RGBA, dx: int = 0, dy: int = 1) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.blit_masked(self, dx, dy, color)
        out.blit(self, 0, 0)
        return out

    # -- export ------------------------------------------------------------

    def to_bytes(self) -> bytes:
        data = bytearray(self.w * self.h * 4)
        for i, (r, g, b, a) in enumerate(self.px):
            o = i * 4
            data[o] = r
            data[o + 1] = g
            data[o + 2] = b
            data[o + 3] = a
        return bytes(data)

    def to_image(self):
        from PIL import Image  # imported lazily so the module stays importable
        return Image.frombytes("RGBA", (self.w, self.h), self.to_bytes())

    def save(self, path: str) -> None:
        self.to_image().save(path)


def stack(canvases: Iterable[Canvas]) -> Canvas:
    """Composite several same-sized canvases bottom-to-top."""
    items = list(canvases)
    if not items:
        return Canvas(1, 1)
    out = Canvas(items[0].w, items[0].h)
    for c in items:
        out.blit(c, 0, 0)
    return out
