"""
Synthetic CC0 floor plan generator v3.
Fixed seed=42, axis-aligned rooms only, standard symbols.
Includes windows. Generator code included in task.
"""
import pathlib, json, math
from PIL import Image, ImageDraw, ImageFont

SEED = 42
W, H = 640, 480
WALL_T = 7
BG = (250, 248, 242)
WALL_C = (18, 18, 18)
DOOR_C = (18, 18, 18)
WIN_C  = (100, 160, 220)
TEXT_C = (35, 35, 35)

ROOMS = [
    ("Living Room",  20,  20, 270, 230),
    ("Kitchen",     270,  20, 470, 170),
    ("Dining Room", 270, 170, 470, 290),
    ("Bedroom 1",    20, 230, 215, 420),
    ("Bedroom 2",   215, 230, 410, 420),
    ("Bathroom",    410, 230, 520, 340),
    ("Hallway",     410, 340, 520, 420),
    ("Laundry",     470,  20, 620, 130),
    ("Garage",       20, 420, 330, 475),
]

# Doors: (room_a, room_b, hinge_x, hinge_y, sweep_dir)
# sweep_dir: "cw" or "ccw", door always 32px long
DOOR_LEN = 32
DOORS_DEF = [
    ("Living Room", "Kitchen",      270,  90, "cw"),
    ("Living Room", "Bedroom 1",    120, 230, "cw"),
    ("Living Room", "Dining Room",  270, 210, "cw"),
    ("Bedroom 1",   "Bedroom 2",    215, 320, "cw"),
    ("Bedroom 2",   "Bathroom",     410, 270, "cw"),
    ("Bathroom",    "Hallway",      410, 370, "cw"),
    ("Hallway",     "Dining Room",  470, 370, "ccw"),
    ("Kitchen",     "Laundry",      470,  85, "cw"),
    ("Bedroom 1",   "Garage",       120, 420, "cw"),
    ("Dining Room", "Bedroom 2",    360, 290, "cw"),
]

# Windows: (room, wall_side, wx1, wy1, wx2, wy2)
WINDOWS_DEF = [
    ("Living Room",  "top",    60,   20,  120,  20),
    ("Living Room",  "left",   20,   80,   20, 140),
    ("Kitchen",      "top",   310,   20,  380,  20),
    ("Bedroom 1",    "left",   20,  280,   20, 340),
    ("Bedroom 2",    "bottom", 260, 420,  340, 420),
    ("Laundry",      "right",  620,  55,  620,  95),
]

def get_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

def draw_room(draw, x1, y1, x2, y2):
    draw.rectangle([x1+WALL_T, y1+WALL_T, x2-WALL_T, y2-WALL_T], fill=(255,255,255))
    draw.rectangle([x1, y1, x2, y1+WALL_T], fill=WALL_C)
    draw.rectangle([x1, y2-WALL_T, x2, y2], fill=WALL_C)
    draw.rectangle([x1, y1, x1+WALL_T, y2], fill=WALL_C)
    draw.rectangle([x2-WALL_T, y1, x2, y2], fill=WALL_C)

def compute_door(hx, hy, sweep):
    """Returns (hinge_x, hinge_y, leaf_x, leaf_y, arc_cx, arc_cy)"""
    L = DOOR_LEN
    # Determine wall orientation from hinge position relative to rooms
    # For vertical walls (hx is boundary): leaf extends horizontally
    # For horizontal walls (hy is boundary): leaf extends vertically
    # Use sweep direction
    if sweep == "cw":
        lx, ly = hx + L, hy
        acx, acy = hx, hy - L
    else:
        lx, ly = hx - L, hy
        acx, acy = hx, hy - L
    return hx, hy, lx, ly, acx, acy

def draw_door(draw, hx, hy, lx, ly, acx, acy):
    L = DOOR_LEN
    # Gap in wall
    gap = L + 4
    # Detect wall orientation
    if abs(lx - hx) > abs(ly - hy):  # horizontal door = vertical wall
        draw.rectangle([hx-WALL_T-1, hy-2, hx+WALL_T+1, hy+gap], fill=(255,255,255))
    else:
        draw.rectangle([hx-2, hy-WALL_T-1, hx+gap, hy+WALL_T+1], fill=(255,255,255))
    # Door leaf
    draw.line([(hx,hy),(lx,ly)], fill=DOOR_C, width=2)
    # Arc
    r = L
    bbox = [acx-r, acy-r, acx+r, acy+r]
    draw.arc(bbox, start=0, end=90, fill=DOOR_C, width=1)
    # Hinge dot
    draw.ellipse([hx-3,hy-3,hx+3,hy+3], fill=DOOR_C)

def draw_window(draw, wx1, wy1, wx2, wy2, side):
    # Draw window symbol: double line in wall
    if side in ("top","bottom"):
        y = wy1
        draw.rectangle([wx1, y-WALL_T//2-1, wx2, y+WALL_T//2+1], fill=(255,255,255))
        draw.line([(wx1, y-3),(wx2, y-3)], fill=WIN_C, width=2)
        draw.line([(wx1, y+3),(wx2, y+3)], fill=WIN_C, width=2)
        draw.line([(wx1, y-3),(wx1, y+3)], fill=WIN_C, width=2)
        draw.line([(wx2, y-3),(wx2, y+3)], fill=WIN_C, width=2)
    else:
        x = wx1
        draw.rectangle([x-WALL_T//2-1, wy1, x+WALL_T//2+1, wy2], fill=(255,255,255))
        draw.line([(x-3, wy1),(x-3, wy2)], fill=WIN_C, width=2)
        draw.line([(x+3, wy1),(x+3, wy2)], fill=WIN_C, width=2)
        draw.line([(x-3, wy1),(x+3, wy1)], fill=WIN_C, width=2)
        draw.line([(x-3, wy2),(x+3, wy2)], fill=WIN_C, width=2)

img  = Image.new("RGB", (W,H), BG)
draw = ImageDraw.Draw(img)

# Grid
for x in range(0,W,40): draw.line([(x,0),(x,H)],fill=(228,226,218),width=1)
for y in range(0,H,40): draw.line([(0,y),(W,y)],fill=(228,226,218),width=1)

# Rooms
for name,x1,y1,x2,y2 in ROOMS:
    draw_room(draw,x1,y1,x2,y2)

# Compute door geometry
DOORS_GT = []
for ra,rb,hx,hy,sweep in DOORS_DEF:
    hx2,hy2,lx,ly,acx,acy = compute_door(hx,hy,sweep)
    draw_door(draw,hx2,hy2,lx,ly,acx,acy)
    DOORS_GT.append({
        "rooms": [ra, rb],
        "hinge": [hx2, hy2],
        "leaf_end": [lx, ly],
        "arc_center": [acx, acy],
        "arc_radius": DOOR_LEN,
        "sweep": sweep,
    })

# Windows
WINDOWS_GT = []
for room,side,wx1,wy1,wx2,wy2 in WINDOWS_DEF:
    draw_window(draw,wx1,wy1,wx2,wy2,side)
    WINDOWS_GT.append({
        "room": room, "wall": side,
        "p1": [wx1,wy1], "p2": [wx2,wy2],
        "midpoint": [(wx1+wx2)//2, (wy1+wy2)//2],
    })

# Labels
font_sm = get_font(11)
for name,x1,y1,x2,y2 in ROOMS:
    cx,cy = (x1+x2)//2,(y1+y2)//2
    words = name.split()
    mid = max(1,len(words)//2)
    lines = [" ".join(words[:mid])," ".join(words[mid:])] if len(words)>1 else [name]
    for i,ln in enumerate(lines):
        bb = draw.textbbox((0,0),ln,font=font_sm)
        tw,th = bb[2]-bb[0],bb[3]-bb[1]
        oy = (i-len(lines)/2+0.5)*(th+2)
        draw.text((cx-tw//2,int(cy+oy-th//2)),ln,fill=TEXT_C,font=font_sm)

# Title + north + scale
draw.text((10,H-22),"FLOOR PLAN  —  SCALE 1:100  —  SEED 42",fill=(90,90,90),font=font_sm)
draw.text((W-60,8),"N",fill=(60,60,60),font=font_sm)
draw.line([(W-50,20),(W-50,8)],fill=(60,60,60),width=2)
draw.polygon([(W-50,6),(W-53,14),(W-47,14)],fill=(60,60,60))

out = pathlib.Path("/tmp/fp_v3/floor-plan-svg-annotation")
(out/"environment/data/tools").mkdir(parents=True,exist_ok=True)
(out/"solution").mkdir(parents=True,exist_ok=True)
(out/"tests/solution").mkdir(parents=True,exist_ok=True)

img.save(out/"environment/data/floorplan.png")

# Ground truth
GT = {
    "seed": SEED,
    "image_width": W, "image_height": H,
    "coordinate_system": "pixels, origin top-left, x-right y-down",
    "viewport": f"0 0 {W} {H}",
    "wall_thickness_px": WALL_T,
    "room_shape": "axis-aligned rectangles only",
    "rooms": {
        name: {
            "bbox": [x1,y1,x2,y2],
            "centroid": [(x1+x2)//2,(y1+y2)//2],
        }
        for name,x1,y1,x2,y2 in ROOMS
    },
    "doors": DOORS_GT,
    "windows": WINDOWS_GT,
    "adjacency": [[d["rooms"][0],d["rooms"][1]] for d in DOORS_GT],
    "scoring": {
        "matching": "greedy nearest-neighbor (Hungarian equivalent for small N)",
        "room_rect_iou_threshold": 0.40,
        "door_hinge_tolerance_px": 15,
        "door_leaf_tolerance_px": 20,
        "window_midpoint_tolerance_px": 20,
    }
}

with open(out/"tests/ground_truth.json","w") as f:
    json.dump(GT,f,indent=2)

print(f"Rooms:{len(ROOMS)} Doors:{len(DOORS_GT)} Windows:{len(WINDOWS_GT)}")
for d in DOORS_GT:
    print(f"  {d['rooms'][0]:<18} <-> {d['rooms'][1]:<14} hinge={d['hinge']} leaf={d['leaf_end']}")
