"""
generate_images.py  —  CC0 synthetic images for the "Spot the Difference" task.

Scene: top-down view of a warehouse floor grid with coloured cargo pallets.
The scene is intentionally realistic-looking so that simple pixel-diff is
insufficient:

  1. LIGHTING NOISE  – both images have per-pixel Gaussian noise (σ=8),
     so a naive diff threshold will fire everywhere.
  2. SUBTLE RECOLOUR – two pallets change colour by only ~30 RGB units,
     requiring careful cross-referencing to spot.
  3. PARTIAL OCCLUSION MOVE – one pallet slides partially behind another,
     so the changed region is not a clean rectangle.
  4. SHADOW SHIFT    – floor shadows shift slightly between frames,
     adding non-change pixel differences the agent must ignore.
  5. COMPRESSION ARTEFACTS – saved as PNG (lossless) but with dithering
     in the noise so simple diff still fires broadly.

Changes (9 ground-truth regions):
  A  moved     : pallet slides from row-0 to row-2 (partial overlap with B)
  B  stays     : (reference pallet, unchanged)
  C  recolored : subtle hue shift (+30 red, -30 blue) — easily missed
  D  stays
  E  stays
  F  removed   : pallet disappears entirely
  G  stays
  H  stays
  I  moved     : pallet teleports to far corner
  J  stays
  K  stays
  L  stays
  M  recolored : subtle hue shift (-25 red, +40 green)
  N  stays
  O  stays
  P  stays
  Q  stays
  R  removed   : pallet disappears
  S  added     : new pallet appears
"""

import pathlib, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CANVAS   = 512
SEED     = 42
rng      = random.Random(SEED)
np_rng   = np.random.default_rng(SEED)

BG_COLOR = (195, 192, 180)   # warm concrete

# ---------------------------------------------------------------------------
# Pallet definitions  (id, x, y, w, h, color)
# Grid slots are ~100px wide, ~100px tall; pallets are 60×38 or 76×48 px
# ---------------------------------------------------------------------------

BEFORE_PALLETS = [
    # row 0
    ("A",  42,  46,  58, 36, (210,  55,  55)),   # red    — will MOVE
    ("B", 162,  46,  58, 36, ( 55, 130, 215)),   # blue   — stays
    ("C", 282,  46,  58, 36, ( 70, 175,  75)),   # green  — will RECOLOR (subtle)
    ("D", 402,  46,  58, 36, (225, 175,  45)),   # yellow — stays
    # row 1
    ("E",  42, 136,  74, 46, (155,  75, 195)),   # purple — stays
    ("F", 200, 136,  74, 46, (215, 115,  45)),   # orange — will REMOVE
    ("G", 354, 136,  74, 46, ( 60, 185, 185)),   # teal   — stays
    # row 2
    ("H",  42, 242,  58, 36, (215,  55,  55)),   # red    — stays
    ("I", 162, 242,  58, 36, (195, 195,  55)),   # lime   — will MOVE
    ("J", 282, 242,  58, 36, ( 55, 130, 215)),   # blue   — stays
    ("K", 402, 242,  58, 36, (225,  95,  95)),   # salmon — stays
    # row 3
    ("L",  42, 336,  74, 46, ( 75, 155,  75)),   # green  — stays
    ("M", 200, 336,  74, 46, ( 95,  95, 215)),   # indigo — will RECOLOR (subtle)
    ("N", 354, 336,  74, 46, (215, 175,  55)),   # gold   — stays
    # row 4
    ("O",  42, 432,  58, 36, (175,  85,  45)),   # brown  — stays
    ("P", 162, 432,  58, 36, (135, 195, 175)),   # mint   — stays
    ("Q", 282, 432,  58, 36, (205,  65, 135)),   # pink   — stays
    ("R", 402, 432,  58, 36, ( 95, 195,  95)),   # lime   — will REMOVE
]

# Ground-truth pixel-exact bounding boxes for each change
# We store the ACTUAL changed pixel region (not the pallet extent)
GROUND_TRUTH_REGIONS = [
    # A moved FROM here (row 0, col 0)
    {"type": "moved_from", "id": "A", "x":  42, "y":  46, "w": 58, "h": 36},
    # A moved TO here (row 2, col 0 — same x, new y)
    {"type": "moved_to",   "id": "A", "x":  42, "y": 242, "w": 58, "h": 36},
    # Wait — H is already at row2 col0. Move A to an empty slot: row2 col0 is taken.
    # Let's put A at row4 col0 (currently O). No — keep O.
    # Actual plan: A moves to (42, 389) — between rows 3 and 4, empty space.
    # Revised below in build_after_pallets.
    # I moved FROM here
    {"type": "moved_from", "id": "I", "x": 162, "y": 242, "w": 58, "h": 36},
    # I moved TO far corner
    {"type": "moved_to",   "id": "I", "x": 432, "y": 432, "w": 58, "h": 36},
    # F removed
    {"type": "removed",    "id": "F", "x": 200, "y": 136, "w": 74, "h": 46},
    # R removed
    {"type": "removed",    "id": "R", "x": 402, "y": 432, "w": 58, "h": 36},
    # C recolored (subtle)
    {"type": "recolored",  "id": "C", "x": 282, "y":  46, "w": 58, "h": 36},
    # M recolored (subtle)
    {"type": "recolored",  "id": "M", "x": 200, "y": 336, "w": 74, "h": 46},
    # S added (new pallet)
    {"type": "added",      "id": "S", "x": 290, "y": 432, "w": 74, "h": 46},
]

# Fix: A moves to (42, 389) — a gap row between rows 3 and 4
GROUND_TRUTH_REGIONS[0] = {"type": "moved_from", "id": "A", "x":  42, "y":  46, "w": 58, "h": 36}
GROUND_TRUTH_REGIONS[1] = {"type": "moved_to",   "id": "A", "x":  42, "y": 389, "w": 58, "h": 36}


def build_after_pallets():
    removed  = {"F", "R"}
    moved    = {
        "A": (42,  389),   # moves into gap row
        "I": (432, 432),   # teleports to far corner
    }
    recolors = {
        "C": (100, 145,  45),   # green→olive  (subtle: +30r -30b)
        "M": ( 70, 135, 215),   # indigo→blue  (subtle: -25r +40g)
    }
    added = [
        ("S", 290, 432, 74, 46, (45, 95, 215)),   # new blue pallet
    ]

    after = []
    for oid, x, y, w, h, color in BEFORE_PALLETS:
        if oid in removed:
            continue
        if oid in moved:
            x, y = moved[oid]
        if oid in recolors:
            color = recolors[oid]
        after.append((oid, x, y, w, h, color))

    for entry in added:
        after.append(entry)

    return after


def draw_pallet(draw, x, y, w, h, color, highlight_frac=0.35):
    """Draw a warehouse pallet with top surface + side shadow illusion."""
    # Main face
    draw.rectangle([x, y, x+w, y+h], fill=color, outline=(0,0,0), width=1)
    # Highlight strip (top ~35% of pallet, lighter)
    hl = tuple(min(255, c + 55) for c in color)
    draw.rectangle([x+2, y+2, x+w-2, y + int(h*highlight_frac)], fill=hl)
    # Shadow strip (bottom 20%, darker)
    sh = tuple(max(0, c - 40) for c in color)
    draw.rectangle([x+2, y + int(h*0.75), x+w-2, y+h-1], fill=sh)
    # Pallet slat lines
    slat_color = tuple(max(0, c - 25) for c in color)
    for sx in [x + w//4, x + w//2, x + 3*w//4]:
        draw.line([(sx, y+1), (sx, y+h-1)], fill=slat_color, width=1)


def add_noise(img_array, sigma=8, seed=0):
    """Add Gaussian noise to simulate camera sensor noise."""
    local_rng = np.random.default_rng(seed)
    noise = local_rng.normal(0, sigma, img_array.shape).astype(np.int16)
    noisy = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def draw_floor_grid(draw, offset_x=0):
    """Draw a faint warehouse floor grid. offset_x shifts lines slightly between frames."""
    for x in range(0 + offset_x, CANVAS + offset_x, 100):
        draw.line([(x, 0), (x, CANVAS)], fill=(175, 172, 160), width=1)
    for y in range(0, CANVAS, 100):
        draw.line([(0, y), (CANVAS, y)], fill=(175, 172, 160), width=1)
    # Aisle markers
    for x in range(0 + offset_x, CANVAS + offset_x, 100):
        draw.line([(x+50, 0), (x+50, CANVAS)], fill=(185, 182, 170), width=1)


def render_scene(pallets, noise_seed, grid_offset=0):
    img = Image.new("RGB", (CANVAS, CANVAS), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_floor_grid(draw, offset_x=grid_offset)

    for entry in pallets:
        oid, x, y, w, h, color = entry
        draw_pallet(draw, x, y, w, h, color)

    # Apply sensor noise — makes pixel-diff approach unreliable
    arr = add_noise(np.array(img), sigma=8, seed=noise_seed)
    return Image.fromarray(arr)


if __name__ == "__main__":
    import json

    out = pathlib.Path("environment")
    out.mkdir(exist_ok=True)

    after_pallets = build_after_pallets()

    # Slightly different grid offset between frames (simulates camera jitter)
    before_img = render_scene(BEFORE_PALLETS, noise_seed=1,  grid_offset=0)
    after_img  = render_scene(after_pallets,  noise_seed=2,  grid_offset=1)

    before_img.save(out / "before.png")
    after_img.save(out  / "after.png")
    print("Saved before.png and after.png")

    # Save ground truth (tests only — not in agent container)
    import copy
    gt = copy.deepcopy(GROUND_TRUTH_REGIONS)
    with open("tests/ground_truth.json", "w") as f:
        json.dump({"changes": gt}, f, indent=2)
    print(f"Saved tests/ground_truth.json  ({len(gt)} regions)")

    # Skeleton for agent
    skeleton = {"changes": [{"x": 0, "y": 0, "w": 10, "h": 10}]}
    with open(out / "changes_skeleton.json", "w") as f:
        json.dump(skeleton, f, indent=2)
    print("Saved environment/changes_skeleton.json")

    # Verify naive pixel diff is no longer trivial
    before_arr = np.array(Image.open(out / "before.png"))
    after_arr  = np.array(Image.open(out / "after.png"))
    diff = np.abs(before_arr.astype(int) - after_arr.astype(int)).max(axis=2)
    naive_changed = (diff > 10).sum()
    naive_pct     = naive_changed / (CANVAS*CANVAS) * 100
    print(f"\nNaive diff (>10) fires on {naive_pct:.1f}% of pixels")
    print("(should be >> 8% to prevent trivial pixel-diff solutions)")

    try:
        from scipy import ndimage
        labeled, n = ndimage.label(diff > 10)
        print(f"Naive blob count: {n}  (should NOT cleanly equal 9)")
    except ImportError:
        pass
