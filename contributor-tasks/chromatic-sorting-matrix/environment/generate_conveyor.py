import json, pathlib
from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 800, 600
BG_COLOR = (240, 240, 240)

# The deterministic ground truth of the visual graph
NODES = {
    0: {"x": 400, "y": 100, "color": "RED",   "arrow": "L", "left": 1, "right": 2},
    1: {"x": 250, "y": 250, "color": "BLUE",  "arrow": "R", "left": 3, "right": 4},
    2: {"x": 550, "y": 250, "color": "GREEN", "arrow": "L", "left": 4, "right": 5},
    3: {"x": 150, "y": 400, "color": "GREEN", "arrow": "R", "left": "BIN_A", "right": "BIN_B"},
    4: {"x": 400, "y": 400, "color": "RED",   "arrow": "L", "left": "BIN_B", "right": "BIN_C"},
    5: {"x": 650, "y": 400, "color": "BLUE",  "arrow": "L", "left": "BIN_C", "right": "BIN_D"},
}

COLORS = {"RED": (220, 50, 50), "BLUE": (50, 100, 220), "GREEN": (50, 180, 50)}

def draw_network():
    # Ensure data directory exists
    out_dir = pathlib.Path("environment/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw Bin targets
    bins = {"BIN_A": 100, "BIN_B": 300, "BIN_C": 500, "BIN_D": 700}
    for b_name, bx in bins.items():
        draw.rectangle([bx-40, 500, bx+40, 550], fill=(100, 100, 100))
        draw.text((bx-15, 520), b_name[-1], fill=(255,255,255))

    # Draw Lines & Nodes
    for nid, data in NODES.items():
        for child_key, side in [("left", -1), ("right", 1)]:
            child = data[child_key]
            if isinstance(child, str):  
                cx, cy = bins[child], 500
            else:
                cx, cy = NODES[child]["x"], NODES[child]["y"]
            draw.line([(data["x"], data["y"]), (cx, cy)], fill=(50,50,50), width=4)
            # Label branch L/R
            draw.text(((data["x"]+cx)//2, (data["y"]+cy)//2 - 10), "L" if side == -1 else "R", fill=(0,0,0))

    for nid, data in NODES.items():
        r = 30
        draw.ellipse([data["x"]-r, data["y"]-r, data["x"]+r, data["y"]+r], fill=COLORS[data["color"]])
        txt = "<--" if data["arrow"] == "L" else "-->"
        draw.text((data["x"]-10, data["y"]-5), txt, fill=(255,255,255))
        draw.text((data["x"]-5, data["y"]-25), str(nid), fill=(255,255,255))

    img.save(out_dir / "sorting_network.png")
    print(f"Generated {out_dir / 'sorting_network.png'}")

if __name__ == "__main__":
    draw_network()