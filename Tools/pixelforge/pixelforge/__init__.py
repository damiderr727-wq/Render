"""PixelForge — the procedural art pipeline for Pixel Rogue.

Nothing in the game ships a hand-drawn PNG. Every sprite, tile and UI frame in
``Assets/generated`` is produced by this package, packed into atlases and
described by a JSON manifest the Swift side loads at startup.

    python3 Tools/pixelforge/build_assets.py --out Assets/generated

Keeping art as code means a palette tweak or a new enemy variant is a diff,
not a binary blob.
"""

from .canvas import Canvas, stack  # noqa: F401
from .palette import ALL_RAMPS, Ramp  # noqa: F401

__version__ = "1.0.0"
