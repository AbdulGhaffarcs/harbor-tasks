#!/usr/bin/env python3
# MIT License — inspect_cell.py
# Agent helper: prints pixel statistics for a specific grid cell.
# Useful for distinguishing box vs box-on-goal, floor vs goal, etc.

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="/task/puzzle.png")
    ap.add_argument("--meta",  default="/task/meta.json",
                    help="Meta JSON with tile_size, margin, width, height")
    ap.add_argument("--col",   type=int, required=True, help="Cell column (x, 0-indexed)")
    ap.add_argument("--row",   type=int, required=True, help="Cell row (y, 0-indexed)")
    args = ap.parse_args()

    meta = json.loads(Path(args.meta).read_text())
    tile   = meta["tile_size"]
    margin = meta["margin"]
    w, h   = meta["width"], meta["height"]

    if not (0 <= args.col < w and 0 <= args.row < h):
        raise SystemExit(f"cell ({args.col},{args.row}) out of bounds {w}x{h}")

    img = np.array(Image.open(args.image).convert("RGB"))
    x0 = margin + args.col * tile
    y0 = margin + args.row * tile
    region = img[y0:y0 + tile, x0:x0 + tile]

    # Center patch (avoids borders)
    c = tile // 4
    center = region[c:tile - c, c:tile - c]

    # Ring patch (detects the goal ring)
    ring_mask = np.zeros((tile, tile), dtype=bool)
    cy, cx = tile // 2, tile // 2
    for yy in range(tile):
        for xx in range(tile):
            d = ((yy - cy) ** 2 + (xx - cx) ** 2) ** 0.5
            if tile / 3 <= d <= tile / 2 - 2:
                ring_mask[yy, xx] = True
    ring = region[ring_mask]

    print(f"Cell ({args.col},{args.row})   tile={tile}px  pixel bbox=[{x0},{y0}]-[{x0+tile},{y0+tile}]")
    print(f"  Center mean RGB : ({center.mean(0).mean(0)[0]:.1f}, "
          f"{center.mean(0).mean(0)[1]:.1f}, {center.mean(0).mean(0)[2]:.1f})")
    print(f"  Border mean RGB : tl=({region[2,2].tolist()}) "
          f"tr=({region[2,tile-3].tolist()}) "
          f"bl=({region[tile-3,2].tolist()}) "
          f"br=({region[tile-3,tile-3].tolist()})")
    if ring.size:
        print(f"  Ring-band mean  : ({ring.mean(0)[0]:.1f}, {ring.mean(0)[1]:.1f}, {ring.mean(0)[2]:.1f})")

    # Dominant colors in cell (top 5)
    flat = region.reshape(-1, 3)
    # Quantize to 32-level buckets for grouping
    q = (flat // 32) * 32
    unique, counts = np.unique(q, axis=0, return_counts=True)
    order = np.argsort(-counts)[:5]
    print("  Top 5 quantized colors:")
    for i in order:
        print(f"    RGB~({unique[i][0]:3d},{unique[i][1]:3d},{unique[i][2]:3d})   "
              f"{counts[i]:4d} px")


if __name__ == "__main__":
    main()
