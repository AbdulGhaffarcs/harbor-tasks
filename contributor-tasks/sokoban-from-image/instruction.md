# Sokoban from Image

## Goal

A rendered PNG at `/task/puzzle.png` shows a Sokoban puzzle: a grid of tiles
containing walls, floor, boxes, goal cells, and exactly one player. Recover the
puzzle state from the image and produce a move sequence that pushes every box
onto a goal cell.

You must produce **two** output files:

- `/output/state.json` — your parsed interpretation of the grid
- `/output/moves.txt` — the move sequence that solves the puzzle

## Raster specification

The image follows a fixed spec. Use this to locate cells precisely:

- Tile size: **40 × 40 pixels**
- Margin: **20 pixels** on all four sides of the grid
- Grid origin: the top-left cell is at pixel `(20, 20)` (margin, margin)
- A cell at column `c`, row `r` occupies pixels
  `[20 + 40·c, 20 + 40·r]` to `[59 + 40·c, 59 + 40·r]`
- Grid dimensions are available in `/task/meta.json`

## Cell types

Each cell is one of seven types, with these visual cues:

| Cell           | Visual cue                                                           |
|----------------|----------------------------------------------------------------------|
| `wall`         | Solid dark-tone rectangle filling the entire tile                    |
| `floor`        | Light-tone rectangle with thin border                                |
| `goal`         | Floor tile with a colored circular ring                              |
| `box`          | Floor tile with a mid-tone **square** drawn on top (warm color)      |
| `box_on_goal`  | Same as box but **different fill color** (cool/green tone), indicating it is correctly placed. The goal ring may or may not remain visible |
| `player`       | Floor tile with a colored **circle** (blue or violet) on top         |
| `player_on_goal` | Player circle on a goal tile; the goal ring frames the player      |

A single PNG uses one visual skin (one of three) with its own color scheme.
All seven cell types always appear with the same relative ordering of tones:
walls are the darkest, floor is mid-light, boxes are mid-tone warm, boxes on
goals are distinctly colored (cool/green), and the player is a saturated circle.

## `state.json` schema

```json
{
  "width":  <int>,
  "height": <int>,
  "grid": [
    ["wall", "wall", "wall", ...],
    ["wall", "floor", "goal", ...],
    ...
  ]
}
```

- `grid[y][x]` is the cell at column `x`, row `y`. `y = 0` is the **top** row.
- Every string must be one of:
  `wall`, `floor`, `goal`, `box`, `box_on_goal`, `player`, `player_on_goal`.
- Outer dimensions must match `width × height`.

## `moves.txt` format

A single line of characters drawn from `{U, D, L, R}`. Case-sensitive,
no separators, no trailing newline required. Example: `UULLDDRDDRRRUU`.

## Sokoban rules (for simulation)

- Moves `U`, `D`, `L`, `R` move the player **one tile** up/down/left/right.
- If the destination is **wall** → the move is **invalid** and simulation
  halts immediately, zeroing the puzzle-solved component of your score.
- If the destination is empty (`floor`, `goal`) → the player walks onto it.
- If the destination contains a **box** (or `box_on_goal`) → check the cell
  **one further step** in the same direction:
  - If that cell is wall, box, or box-on-goal → the move is **invalid**.
  - Otherwise → the box is pushed one tile, the player follows.
- Boxes cannot be pulled. At most one box moves per step.
- The puzzle is solved when no `box` cells remain (all boxes are `box_on_goal`).

## Scoring (100 pts total)

| Component | Weight | Method |
|-----------|--------|--------|
| Grid parse | 30 pts | Per-cell match against golden `state.json`. `30 × (correct_cells / total_cells)` |
| Puzzle solved | 50 pts | Simulate your moves on the **golden** state. `50` if all boxes reach goals; partial credit `50 × (boxes_on_goal / total_boxes)` at final position; `0` if any move is invalid |
| Solution length | 20 pts | `20 × min(1, optimal_length / your_length)` — the optimal length is pre-computed by BFS over the golden state |

The final score is written to `/tests/score.txt` as a number in `[0, 100]`.

## Helper tools

**Inspect a single cell** (dominant colors, border samples):
```bash
python3 /task/tools/inspect_cell.py --col 3 --row 2
```

**Simulate your move string against your own state.json**:
```bash
python3 /task/tools/simulate_moves.py \
    --state /output/state.json \
    --moves /output/moves.txt -v
```

## Approach

1. Read `/task/meta.json` to get grid dimensions and tile size
2. Iterate every `(col, row)` — sample pixel colors at the center, border,
   and ring band to classify the cell
3. Pay special attention to distinguishing **`box` vs `box_on_goal`**:
   on-goal boxes have a visibly different fill hue from off-goal boxes
4. Write `/output/state.json` with your parsed grid
5. Implement or run a Sokoban solver (BFS is sufficient for these puzzle sizes)
   against your parsed state
6. Verify your sequence with `simulate_moves.py`
7. Write the solution to `/output/moves.txt`

Available Python packages: `Pillow==10.3.0`, `numpy==1.26.4`.
