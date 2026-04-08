# Floor Plan SVG Annotation

## Task

Produce **`/task/annotation.svg`** annotating a synthetic floor plan with:
- Room boundary rectangles
- Door arc elements (hinge and leaf-end circles)
- Window midpoint circles

## Files at `/task/`

| File | Contents |
|------|----------|
| `floorplan.png` | 800×600px floor plan image |
| `room_boxes.json` | Room bounding boxes `[x1,y1,x2,y2]` |
| `annotate.py` | Ready-to-run script — edit DOORS and WINDOWS, then run |

## Steps

**Step 1** — Open `floorplan.png` and examine the floor plan.

**Step 2** — Edit `/task/annotate.py`:
- Fill `DOORS` with `[hinge_x, hinge_y, leaf_x, leaf_y]` for each door arc
  - **Hinge** = filled dot where door meets wall
  - **Leaf** = free swinging end of the door line
- Fill `WINDOWS` with `[midpoint_x, midpoint_y]` for each window
  - Windows appear as double parallel blue lines in the walls

**Step 3** — Run:
```bash
python3 /task/annotate.py
```

Room rects are auto-filled from `room_boxes.json`. You only need to find doors and windows.

## Output Schema

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="800" height="600" viewBox="0 0 800 600">
  <g id="rooms">
    <rect data-room="Living Room" x="20" y="20" width="260" height="220" .../>
  </g>
  <g id="doors">
    <path data-door="1" d="M hx hy L lx ly" stroke="#222" stroke-width="2" fill="none"/>
    <circle data-hinge="1" cx="hx" cy="hy" r="4" fill="#222"/>
    <circle data-leaf="1" cx="lx" cy="ly" r="3" fill="#555"/>
  </g>
  <g id="windows">
    <circle data-window="1" cx="mx" cy="my" r="5" fill="#6495ED"/>
  </g>
</svg>
```

## Scoring

| Component | Tolerance | Pass threshold |
|-----------|-----------|---------------|
| Room rects (IoU≥0.35) | — | 50% of 12 rooms |
| Door hinges | ≤25 px | 40% of 13 doors |
| Door leaf-ends | ≤15 px | bonus |
| Window midpoints | ≤30 px | bonus |

**Score = average of 4 components × 100**

Coordinate system: origin top-left, x right, y down, pixels. viewBox="0 0 800 600".
