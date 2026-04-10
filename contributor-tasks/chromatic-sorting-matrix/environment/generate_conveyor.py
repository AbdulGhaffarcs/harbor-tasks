import json, pathlib
from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 800, 800
BG_COLOR = (240, 240, 240)

# Deterministic Seeded State
NODES = {
    0: {"x": 400, "y": 250, "color": "RED",   "arrow": "L", "left": 1, "right": 2},
    1: {"x": 250, "y": 400, "color": "BLUE",  "arrow": "R", "left": 3, "right": 4},
    2: {"x": 550, "y": 400, "color": "GREEN", "arrow": "L", "left": 4, "right": 5},
    3: {"x": 150, "y": 550, "color": "GREEN", "arrow": "R", "left": "BIN_A", "right": "BIN_B"},
    4: {"x": 400, "y": 550, "color": "RED",   "arrow": "L", "left": "BIN_B", "right": "BIN_C"},
    5: {"x": 650, "y": 550, "color": "BLUE",  "arrow": "L", "left": "BIN_C", "right": "BIN_D"},
}

COLORS = {"RED": (220, 50, 50), "BLUE": (50, 100, 220), "GREEN": (50, 180, 50)}
# Visual queue of packages dropping into Node 0 (Index 1 is first to drop)
PACKAGE_QUEUE = ["RED", "BLUE", "GREEN", "RED", "RED", "BLUE", "GREEN", "BLUE", "RED", "GREEN"]

def draw_network():
    out_dir = pathlib.Path("environment/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Draw Visual Package Queue (Top)
    draw.text((320, 20), "INCOMING QUEUE (Drops into Node 0)", fill=(0,0,0))
    draw.text((360, 40), "Last <-- First", fill=(100,100,100))
    for i, color_name in enumerate(PACKAGE_QUEUE):
        px = 400 + (i * -35) + 150 # Draw right to left so index 1 is above Node 0
        py = 70
        draw.rectangle([px, py, px+30, py+30], fill=COLORS[color_name], outline=(0,0,0), width=2)
        draw.text((px+10, py+8), str(i+1), fill=(255,255,255))
        
    draw.line([(415, 110), (415, 200)], fill=(0,0,0), width=4) # Drop chute
    draw.polygon([(405, 190), (425, 190), (415, 210)], fill=(0,0,0))

    # 2. Draw Bins (Bottom)
    bins = {"BIN_A": 100, "BIN_B": 300, "BIN_C": 500, "BIN_D": 700}
    for b_name, bx in bins.items():
        draw.rectangle([bx-40, 680, bx+40, 730], fill=(100, 100, 100))
        draw.text((bx-15, 700), b_name[-1], fill=(255,255,255))

    # 3. Draw Unambiguous Non-Overlapping Edges
    for nid, data in NODES.items():
        for child_key, side in [("left", -1), ("right", 1)]:
            child = data[child_key]
            cx, cy = (bins[child], 680) if isinstance(child, str) else (NODES[child]["x"], NODES[child]["y"])
            # Draw line
            draw.line([(data["x"], data["y"]), (cx, cy)], fill=(50,50,50), width=5)
            # Draw L/R Label clearly near the top of the branch
            mx, my = data["x"] + (cx - data["x"])*0.3, data["y"] + (cy - data["y"])*0.3
            draw.ellipse([mx-12, my-12, mx+12, my+12], fill=(255,255,255), outline=(0,0,0))
            draw.text((mx-4, my-6), "L" if side == -1 else "R", fill=(0,0,0))

    # 4. Draw Nodes and State Arrows
    for nid, data in NODES.items():
        r = 35
        nx, ny = data["x"], data["y"]
        draw.ellipse([nx-r, ny-r, nx+r, ny+r], fill=COLORS[data["color"]], outline=(0,0,0), width=3)
        draw.text((nx-4, ny-25), str(nid), fill=(255,255,255))
        
        # Unambiguous Visual State Encoding (Polygonal Arrows)
        if data["arrow"] == "L":
            draw.polygon([(nx-15, ny+5), (nx+15, ny-5), (nx+15, ny+15)], fill=(255,255,255))
        else:
            draw.polygon([(nx+15, ny+5), (nx-15, ny-5), (nx-15, ny+15)], fill=(255,255,255))

    img.save(out_dir / "sorting_network.png")
    print("Generated explicit deterministic topology at environment/data/sorting_network.png")

if __name__ == "__main__":
    draw_network()