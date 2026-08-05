"""Composite shapes shared by every sprite generator."""

from __future__ import annotations

import math
from typing import Sequence

from .canvas import Canvas
from .palette import RGBA, Ramp, with_alpha


def rounded_rect(c: Canvas, x: int, y: int, w: int, h: int, color: RGBA,
                 radius: int = 1) -> None:
    """Rect with the corner pixels shaved off — the workhorse body shape."""
    x, y, w, h = round(x), round(y), round(w), round(h)
    radius = max(0, min(radius, min(w, h) // 2))
    c.rect(x, y + radius, w, h - 2 * radius, color)
    c.rect(x + radius, y, w - 2 * radius, radius, color)
    c.rect(x + radius, y + h - radius, w - 2 * radius, radius, color)
    if radius <= 0:
        return
    for i in range(radius):
        # A quarter-circle cut, computed per row so radius 2-4 all look right.
        inset = radius - int(round(math.sqrt(max(0.0, radius * radius -
                                                 (radius - i - 0.5) ** 2))))
        run = radius - inset
        if run <= 0:
            continue
        c.rect(x + inset, y + i, run, 1, color)
        c.rect(x + w - radius, y + i, run, 1, color)
        c.rect(x + inset, y + h - 1 - i, run, 1, color)
        c.rect(x + w - radius, y + h - 1 - i, run, 1, color)


def capsule(c: Canvas, x: int, y: int, w: int, h: int, color: RGBA) -> None:
    """Fully rounded on the short axis."""
    x, y, w, h = round(x), round(y), round(w), round(h)
    if w >= h:
        r = h // 2
        c.rect(x + r, y, w - 2 * r, h, color)
        c.ellipse(x + r - 0.5, y + h / 2.0, r, h / 2.0, color)
        c.ellipse(x + w - r - 0.5, y + h / 2.0, r, h / 2.0, color)
    else:
        r = w // 2
        c.rect(x, y + r, w, h - 2 * r, color)
        c.ellipse(x + w / 2.0, y + r - 0.5, w / 2.0, r, color)
        c.ellipse(x + w / 2.0, y + h - r - 0.5, w / 2.0, r, color)


def dome(c: Canvas, cx: float, y: int, rx: float, h: int, color: RGBA) -> None:
    """Half-ellipse opening downward — heads, helmets, turret caps."""
    y, h = round(y), round(h)
    for row in range(h):
        t = row / max(1, h - 1)
        half = rx * math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2))
        x0 = int(round(cx - half))
        x1 = int(round(cx + half))
        c.hline(x0, y + row, max(1, x1 - x0), color)


def star(c: Canvas, cx: float, cy: float, outer: float, inner: float,
         points: int, color: RGBA, rotation: float = -90.0) -> None:
    verts: list[tuple[int, int]] = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(rotation + i * 180.0 / points)
        verts.append((int(round(cx + math.cos(a) * r)),
                      int(round(cy + math.sin(a) * r))))
    c.polygon(verts, color)


def ring(c: Canvas, cx: float, cy: float, radius: float, thickness: float,
         color: RGBA) -> None:
    outer = radius + thickness / 2.0
    inner = radius - thickness / 2.0
    y0 = int(math.floor(cy - outer))
    y1 = int(math.ceil(cy + outer))
    x0 = int(math.floor(cx - outer))
    x1 = int(math.ceil(cx + outer))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if inner <= d <= outer:
                c.put(x, y, color)


def arc(c: Canvas, cx: float, cy: float, radius: float, start_deg: float,
        end_deg: float, color: RGBA, thickness: float = 1.0) -> None:
    steps = max(8, int(radius * 8))
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(start_deg + (end_deg - start_deg) * t)
        px = cx + math.cos(a) * radius
        py = cy + math.sin(a) * radius
        if thickness <= 1.0:
            c.put(int(round(px)), int(round(py)), color)
        else:
            c.disc(px, py, thickness / 2.0, color)


def gradient_disc(c: Canvas, cx: float, cy: float, radius: float,
                  ramp: Ramp, center_index: int = 4,
                  edge_index: int = 1) -> None:
    """Radial glow used for bullets, orbs and explosion cores."""
    span = center_index - edge_index
    y0 = int(math.floor(cy - radius))
    y1 = int(math.ceil(cy + radius))
    x0 = int(math.floor(cx - radius))
    x1 = int(math.ceil(cx + radius))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / max(0.001, radius)
            if d > 1.0:
                continue
            c.put(x, y, ramp[int(round(center_index - span * d))])


def soft_glow(c: Canvas, cx: float, cy: float, radius: float, color: RGBA,
              falloff: float = 2.0) -> None:
    """Additive-looking halo done with alpha, so it survives PNG export."""
    y0 = int(math.floor(cy - radius))
    y1 = int(math.ceil(cy + radius))
    x0 = int(math.floor(cx - radius))
    x1 = int(math.ceil(cx + radius))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / max(0.001, radius)
            if d > 1.0:
                continue
            a = int(round(color[3] * ((1.0 - d) ** falloff)))
            if a > 4:
                c.put(x, y, with_alpha(color, a))


def bevel(c: Canvas, x: int, y: int, w: int, h: int, ramp: Ramp,
          light_index: int = 4, dark_index: int = 1) -> None:
    """Classic UI bevel: lit top/left, shaded bottom/right."""
    c.hline(x, y, w, ramp[light_index])
    c.vline(x, y, h, ramp[light_index])
    c.hline(x, y + h - 1, w, ramp[dark_index])
    c.vline(x + w - 1, y, h, ramp[dark_index])


def contact_shadow(w: int, h: int, alpha: int = 110) -> Canvas:
    """The soft ellipse every entity sits on. Sold separately from the sprite
    so the renderer can squash it as the entity hops or falls."""
    c = Canvas(w, h)
    c.ellipse(w / 2.0, h / 2.0, w / 2.0, h / 2.0, (8, 6, 14, alpha))
    c.ellipse(w / 2.0, h / 2.0, w / 2.0 - 1, h / 2.0 - 0.5,
              (8, 6, 14, min(255, alpha + 45)))
    return c


def symmetric(width: int, height: int,
              draw) -> Canvas:
    """Draw only the left half, mirror it. Guarantees clean symmetry."""
    half = Canvas(width, height)
    draw(half)
    out = Canvas(width, height)
    out.blit(half, 0, 0)
    mirrored = half.flipped_x()
    out.blit(mirrored, 0, 0)
    return out


def path_polyline(c: Canvas, points: Sequence[tuple[int, int]], color: RGBA,
                  closed: bool = False) -> None:
    for i in range(len(points) - 1):
        c.line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1],
               color)
    if closed and len(points) > 2:
        c.line(points[-1][0], points[-1][1], points[0][0], points[0][1], color)
