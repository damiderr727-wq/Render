#!/usr/bin/env python3
"""
Baut saemtliche Assets: Grafik, Raeume, Partituren.

    python3 Tools/build_assets.py

Alles darunter ist erzeugter Inhalt. Wer die Welt aendern will, aendert
die Generatoren - nicht die Dateien in Assets/.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_backdrops
import gen_characters
import gen_levels
import gen_score
import gen_world


def main() -> int:
    t0 = time.time()
    print("RESONANZ - Assets werden gebaut\n")
    gen_characters.build()
    gen_world.build()
    gen_backdrops.build()
    gen_levels.build()
    gen_score.build()

    root = Path(__file__).resolve().parent.parent / "Sources" / "ResonanzCore" / "Resources"
    size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    print(f"\nfertig in {time.time() - t0:.1f}s - {size / 1024:.0f} KiB in Sources/ResonanzCore/Resources/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
