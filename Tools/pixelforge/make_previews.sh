#!/usr/bin/env bash
# Regenerates everything: art, audio, and the preview frames in docs/previews.
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 Tools/pixelforge/build_assets.py --out Assets/generated --previews docs/previews
python3 Tools/pixelforge/soundforge.py --out Assets/generated/sfx

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for scenario in combat boss shop; do
  swift run -q PixelRogueSnapshot --scenario "$scenario" --seed GUNGEON \
    --frames 200 --out "$tmp/$scenario.json"
  python3 Tools/pixelforge/render_scene.py "$tmp/$scenario.json" \
    --out "docs/previews/frame_$scenario.png" --scale 2
done
