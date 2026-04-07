# Floor Plan SVG Annotation

## Your Task

Annotate a synthetic architectural floor plan by producing an SVG file with
three layers: room rectangles, door elements, and window markers.

## Input

| File | Path | Size |
|------|------|------|
| Floor plan | `/task/floorplan.png` | 640 × 480 px |

## Coordinate System

- **Origin**: top-left corner
- **x** increases rightward, **y** increases downward
- **Units**: pixels
- **Room shape**: axis-aligned rectangles ONLY (no rotation)
- Your SVG **must** declare `viewBox="0 0 640 480"`

## Symbol Conventions

| Symbol | Description |
|--------|-------------|
| **Wall** | Filled black rectangle, ~7px thick |
| **Door** | Straight line (leaf) + quarter-circle arc from hinge point |
| **Hinge** | Small filled circle where door meets wall |
| **Leaf end** | Free end of the door leaf (end of the straight line) |
| **Window** | Double parallel lines in the wall (blue tint) |

## Required SVG Schema

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="640" height="480" viewBox="0 0 640 480">

  <!-- Layer 1: Room boundary rectangles -->
  <g id="rooms">
    <rect data-room="Living Room" x="20" y="20"
          width="250" height="210"
          fill="#4A90D9" fill-opacity="0.18" stroke="#4A90D9" stroke-width="2"/>
  </g>

  <!-- Layer 2: Door elements -->
  <g id="doors">
    <path data-door="1" d="M hx hy L lx ly"
          stroke="#222" stroke-width="2" fill="none"/>
    <path data-arc="1" d="M lx ly A r r 0 0 0 ex ey"
          stroke="#222" stroke-width="1" fill="none" stroke-dasharray="3,2"/>
    <!-- Hinge: SCORED within 15px of ground truth -->
    <circle data-hinge="1" cx="hx" cy="hy" r="4" fill="#222"/>
    <!-- Leaf end: SCORED within 20px of ground truth -->
    <circle data-leaf="1" cx="lx" cy="ly" r="3" fill="#555"/>
  </g>

  <!-- Layer 3: Window midpoint markers -->
  <g id="windows">
    <!-- Midpoint of each window: SCORED within 20px -->
    <circle data-window="1" cx="mx" cy="my" r="5" fill="#6495ED"/>
  </g>

</svg>
```

## Scoring (4 components, equal weight)

| Component | Scoring | Threshold |
|-----------|---------|-----------|
| Room rects | IoU vs GT bbox | >= 0.40 |
| Door hinges | Greedy nearest-neighbor proximity | <= 15 px |
| Door leaf ends | Greedy nearest-neighbor proximity | <= 20 px |
| Window midpoints | Greedy nearest-neighbor proximity | <= 20 px |

**Final score = average of 4 components × 100**

## Suggested Approach

1. Identify all rooms — estimate bounding rectangles in pixel coords
2. Find all door arc symbols — locate hinge and leaf-end positions
3. Find all window symbols (double blue lines in walls) — mark midpoints
4. Write the SVG
5. Re-examine the image and adjust any misaligned elements
