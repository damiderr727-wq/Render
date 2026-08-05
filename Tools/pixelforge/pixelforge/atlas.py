"""Atlas packing and manifest emission.

Sprites are packed untrimmed on purpose. Trimming would shave a few hundred
kilobytes, but every animation frame would then need its own offset applied at
draw time, and a single sign error there makes a character jitter in a way
that is miserable to debug. Untrimmed frames all share one anchor.

A 1px transparent gutter around each sprite stops neighbours bleeding in when
the GPU samples at non-integer scale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .canvas import Canvas

GUTTER = 1
MAX_SIZE = 2048


@dataclass
class Entry:
    name: str
    canvas: Canvas
    x: int = 0
    y: int = 0
    page: int = 0


@dataclass
class Animation:
    name: str
    frames: list[str]
    fps: float = 8.0
    loop: bool = True


class AtlasBuilder:
    """Shelf packer: sprites are sorted tall-first and laid out in rows.

    Good enough for a few thousand small sprites, and it produces a layout a
    human can actually read when debugging the sheet by eye.
    """

    def __init__(self, name: str = "atlas") -> None:
        self.name = name
        self.entries: list[Entry] = []
        self.animations: list[Animation] = []
        self.meta: dict = {}

    # -- registration ------------------------------------------------------

    def add(self, name: str, canvas: Canvas) -> str:
        self.entries.append(Entry(name, canvas))
        return name

    def add_frames(self, base: str, frames: list[Canvas], fps: float = 8.0,
                   loop: bool = True) -> str:
        names = []
        for i, frame in enumerate(frames):
            names.append(self.add(f"{base}/{i}", frame))
        self.animations.append(Animation(base, names, fps, loop))
        return base

    # -- packing -----------------------------------------------------------

    def pack(self) -> list[tuple[int, int]]:
        """Assign every entry a page and position. Returns page sizes."""
        ordered = sorted(self.entries,
                         key=lambda e: (-e.canvas.h, -e.canvas.w, e.name))
        pages: list[tuple[int, int]] = []
        page = 0
        cursor_x = GUTTER
        cursor_y = GUTTER
        shelf_h = 0
        width = MAX_SIZE
        used_h = 0

        for entry in ordered:
            w = entry.canvas.w + GUTTER
            h = entry.canvas.h + GUTTER
            if cursor_x + w > width:
                cursor_x = GUTTER
                cursor_y += shelf_h
                shelf_h = 0
            if cursor_y + h > MAX_SIZE:
                pages.append((width, _po2(used_h)))
                page += 1
                cursor_x, cursor_y, shelf_h, used_h = GUTTER, GUTTER, 0, 0
            entry.page = page
            entry.x = cursor_x
            entry.y = cursor_y
            cursor_x += w
            shelf_h = max(shelf_h, h)
            used_h = max(used_h, cursor_y + shelf_h)

        pages.append((width, _po2(used_h)))
        return pages

    def render_pages(self, sizes: list[tuple[int, int]]) -> list[Canvas]:
        pages = [Canvas(w, h) for w, h in sizes]
        for entry in self.entries:
            pages[entry.page].blit(entry.canvas, entry.x, entry.y)
        return pages

    # -- output ------------------------------------------------------------

    def manifest(self, sizes: list[tuple[int, int]],
                 files: list[str]) -> dict:
        sprites = {}
        for e in self.entries:
            sprites[e.name] = {
                "page": e.page,
                "x": e.x,
                "y": e.y,
                "w": e.canvas.w,
                "h": e.canvas.h,
            }
        return {
            "version": 1,
            "generator": "pixelforge",
            "pages": [
                {"file": files[i], "width": sizes[i][0], "height": sizes[i][1]}
                for i in range(len(sizes))
            ],
            "sprites": sprites,
            "animations": {
                a.name: {"frames": a.frames, "fps": a.fps, "loop": a.loop}
                for a in self.animations
            },
            **self.meta,
        }

    def write(self, out_dir: str) -> dict:
        import os

        os.makedirs(out_dir, exist_ok=True)
        sizes = self.pack()
        pages = self.render_pages(sizes)
        files = []
        for i, page in enumerate(pages):
            fname = f"{self.name}{i}.png"
            page.save(os.path.join(out_dir, fname))
            files.append(fname)
        data = self.manifest(sizes, files)
        with open(os.path.join(out_dir, f"{self.name}.json"), "w") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
        return data


def _po2(value: int) -> int:
    size = 16
    while size < value:
        size *= 2
    return min(MAX_SIZE, size)
