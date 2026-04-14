# Synthetic Topographic Contour Map Analysis

## Objective

You are given a synthetic topographic contour map image (`contour_map.png`) showing terrain with multiple peaks, contour lines at regular elevation intervals, marked reference points, and a coordinate grid. Your task is to analyze this map and produce three output files.

## Input Files

| File | Description |
|------|-------------|
| `contour_map.png` | 1400×1100px topographic contour map image |
| `metadata.csv` | Key-value pairs: A/B pixel coordinates, scale, DEM dimensions |
| `verify.py` | Schema checker — run to validate your output format |

### Key Map Features
- **Contour lines**: Brown curves labeled with elevation in meters (e.g., "250 m")
- **Peaks**: Red triangle markers labeled PK1, PK2, ... with elevation
- **Points A and B**: Colored circle markers connected by a dashed transect line
- **Scale bar**: Located at bottom-right, showing distance in meters
- **Coordinate grid**: X (horizontal) and Y (vertical) axes in meters

### Metadata CSV
The `metadata.csv` file contains exact coordinates to avoid OCR ambiguity:
```
key,value
point_a_dem_x,80
point_a_dem_y,100
point_b_dem_x,620
point_b_dem_y,450
dem_width,700
dem_height,550
scale_pixel_per_meter,1.0
contour_interval_m,50
...
```

The image is rendered at 2× the DEM resolution (image pixel = DEM coord × 2).

## Required Outputs

You must produce exactly **3 files** in `/task/outputs/`:

### 1. `overlay.svg` — Layered SVG Overlay

An SVG file with three named layers:

#### Layer: `<g id="contours">`
For each visible contour line, create a group containing a path:
```xml
<g id="contour_0_0" data-elevation="250">
  <path d="M 100.0 200.0 L 105.0 198.0 L ... Z"
        fill="none" stroke="#4a3728" stroke-width="1.5" />
</g>
```
- `data-elevation`: integer elevation in meters
- Path coordinates are in **image pixel space** (1400×1100)
- Each contour ring is a separate `<g>` element

#### Layer: `<g id="peaks">`
For each peak, create a circle:
```xml
<circle id="peak_1" cx="400.0" cy="300.0" r="8"
        fill="red" stroke="darkred" stroke-width="2"
        data-elevation="750.0" />
```
- `cx`, `cy` in image pixel coordinates
- `data-elevation` is the peak's elevation

#### Layer: `<g id="nesting">`
For each contour nesting relationship (a higher contour enclosed by a lower one), draw a line connecting their centroids:
```xml
<line x1="400" y1="300" x2="350" y2="280"
      stroke="blue" stroke-width="1" stroke-dasharray="4,4"
      data-child="contour_5_0" data-parent="contour_3_0" />
```
- `data-child`: the higher-elevation (inner) contour ID
- `data-parent`: the next-lower-elevation contour that contains it

### 2. `watersheds.png` — Drainage Basin Segmentation

A color-coded image where each pixel is assigned to a drainage basin:
- Each basin has a unique, distinct RGB color
- Basins are determined by downhill flow: water at each point flows to the steepest descent neighbor until reaching a local minimum
- Connected regions draining to the same minimum form one basin
- Output dimensions: **1400×1100** pixels (same as input image)

### 3. `profile.csv` — Elevation Profile Along Transect A→B

A CSV file with columns:
```
distance_m,elevation_m
0,123.45
1,124.10
2,125.30
...
```
- Sample at **1-meter intervals** from point A to point B
- `distance_m`: distance from A in meters (0, 1, 2, ...)
- `elevation_m`: estimated elevation at that point (float, 2 decimal places)
- Use the coordinates from `metadata.csv`

## Worked Example (DUMMY DATA — not from this task)

Suppose you have a simple 3-peak terrain with 100m contour interval:

**Step 1**: Read the map. Identify contour lines at 100m, 200m, 300m. Find peaks PK1 (500m), PK2 (400m).

**Step 2**: Build the SVG. For the 300m contour around PK1:
```xml
<g id="contour_2_0" data-elevation="300">
  <path d="M 50 60 L 80 55 L 100 70 L 90 90 L 55 85 Z"
        fill="none" stroke="#4a3728" stroke-width="1.5" />
</g>
```

**Step 3**: Build nesting. The 300m contour is inside the 200m contour:
```xml
<line x1="75" y1="72" x2="120" y2="110"
      stroke="blue" stroke-width="1" stroke-dasharray="4,4"
      data-child="contour_2_0" data-parent="contour_1_0" />
```

**Step 4**: Watershed. Identify low points at map edges/valleys. Flood-fill upward assigning basin IDs by steepest descent.

**Step 5**: Profile. Read A=(10,20), B=(90,80) from metadata. Sample elevation every 1m along the line.

## Verification

Run `python3 /task/verify.py /task/outputs` to check your output format before final submission. This checks structure only, not correctness.

## Scoring

Your outputs are scored continuously (not pass/fail):
- **SVG contour paths**: How well your contour paths match the true contour positions
- **SVG elevations**: Accuracy of `data-elevation` attributes (±5m tolerance)
- **Nesting hierarchy**: F1 score of parent-child edges
- **Peak locations**: Euclidean distance (Hungarian-matched, full credit within 20px)
- **Watershed segmentation**: Dice coefficient per basin (Hungarian-matched)
- **Profile accuracy**: RMSE of elevation values along the transect

## Tips
- Start by reading `metadata.csv` for exact coordinates
- The DEM-to-image scale is 2× (multiply DEM coords by 2 for image pixel coords)
- Contour labels have white backgrounds for readability
- Run `verify.py` early and often to catch format issues
- The watershed should cover the entire image (no unassigned pixels)
