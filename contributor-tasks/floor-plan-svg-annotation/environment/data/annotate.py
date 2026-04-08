#!/usr/bin/env python3
"""
annotate.py — Edit DOORS and WINDOWS, then run:
  python3 /task/annotate.py

Writes /task/annotation.svg.
Room rects are filled from room_boxes.json automatically.
You must find door hinge+leaf positions and window midpoints from floorplan.png.
"""
import json

rooms = json.load(open("/task/room_boxes.json"))["rooms"]

# EDIT: each door as [hinge_x, hinge_y, leaf_x, leaf_y]
# Look at floorplan.png — find each door arc symbol:
#   hinge = filled dot at wall  |  leaf = free end of door line
DOORS = [
    # [hinge_x, hinge_y, leaf_x, leaf_y],
]

# EDIT: each window as [midpoint_x, midpoint_y]
# Look at floorplan.png — double parallel blue lines in walls
WINDOWS = [
    # [midpoint_x, midpoint_y],
]

COLORS = ["#4A90D9","#E8652A","#2CA02C","#9467BD","#D62728","#8C564B",
          "#E377C2","#7F7F7F","#BCBD22","#17BECF","#AEC7E8","#F7B6D2"]

lines = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">',
    '  <image href="floorplan.png" x="0" y="0" width="800" height="600" opacity="0.45"/>',
    '  <g id="rooms">',
]
for i, (name, bbox) in enumerate(rooms.items()):
    x1, y1, x2, y2 = bbox
    c = COLORS[i % len(COLORS)]
    lines.append(
        f'    <rect data-room="{name}" x="{x1}" y="{y1}" '
        f'width="{x2-x1}" height="{y2-y1}" '
        f'fill="{c}" fill-opacity="0.18" stroke="{c}" stroke-width="2"/>'
    )
lines += ['  </g>', '  <g id="doors">']

for i, door in enumerate(DOORS):
    if len(door) >= 4:
        hx, hy, lx, ly = door[0], door[1], door[2], door[3]
        n = i + 1
        lines += [
            f'    <path data-door="{n}" d="M {hx} {hy} L {lx} {ly}" stroke="#222" stroke-width="2" fill="none"/>',
            f'    <circle data-hinge="{n}" cx="{hx}" cy="{hy}" r="4" fill="#222"/>',
            f'    <circle data-leaf="{n}" cx="{lx}" cy="{ly}" r="3" fill="#555"/>',
        ]

lines += ['  </g>', '  <g id="windows">']
for i, win in enumerate(WINDOWS):
    if len(win) >= 2:
        lines.append(f'    <circle data-window="{i+1}" cx="{win[0]}" cy="{win[1]}" r="5" fill="#6495ED"/>')

lines += ['  </g>', '</svg>']

with open("/task/annotation.svg", "w") as f:
    f.write("\n".join(lines))
print(f"annotation.svg written — rooms:{len(rooms)}, doors:{len(DOORS)}, windows:{len(WINDOWS)}")
