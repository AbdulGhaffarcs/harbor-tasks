# Sokoban from Image

## Goal

A rendered Sokoban puzzle PNG is at `/task/puzzle.png`. Parse every cell
visually and produce a valid solution. Write two files:

- `/output/state.json` — your parsed grid
- `/output/moves.txt` — move string that solves the puzzle

---

## Raster specification

| Property | Value |
|----------|-------|
| Tile size | 40 x 40 pixels |
| Margin | 20 pixels on all four sides |
| Cell at column c, row r | pixels `[20+40·c, 20+40·r]` to `[59+40·c, 59+40·r]` |
| Grid dimensions | `meta.json` fields `width` x `height` |
| Exact palette hex | `meta.json` field `palette` |

## Cell types and how to classify them

Read `/task/meta.json`. It contains `tile_size`, `margin`, `width`, `height`,
and a `palette` dict with exact hex colors for each cell type.

For each cell at `(col, row)`:
1. Sample the **corner pixel** at `(x0+2, y0+2)` — if it matches `palette.wall`, cell is `wall`
2. Sample the **center patch** `[cy-8:cy+8, cx-8:cx+8]` and compute mean RGB
3. **Goal ring detection:** scan every pixel at radius 10%–50% of tile from center
   for any pixel within L2 distance 25 of `palette.goal_ring` → `has_ring = True`
4. Classify by center distance to palette colors:
   - Center close to `palette.player` → `player` (or `player_on_goal` if `has_ring`)
   - Center close to `palette.box_on_goal` AND closer than `palette.box` → `box_on_goal`
   - Center close to `palette.box` → `box`
   - `has_ring` is True → `goal`
   - Otherwise → `floor`

| Cell | Visual cue |
|------|-----------|
| `wall` | Solid dark fill. Corner matches `palette.wall`. |
| `floor` | Light fill. Center matches `palette.floor`. |
| `goal` | Floor + circular ring outline (`palette.goal_ring`). |
| `box` | Floor + warm inner square (`palette.box`). |
| `box_on_goal` | Floor + goal ring (always visible) + teal inner square (`palette.box_on_goal`). |
| `player` | Floor + violet/blue circle (`palette.player`). |
| `player_on_goal` | Floor + goal ring (always visible) + player circle. |

**`box` vs `box_on_goal`:** completely different hue — warm/brown vs cool/teal.

**Goal ring:** only 3px wide. Must scan for a single matching pixel, not average.

## state.json schema

```json
{"width": 16, "height": 11, "grid": [["wall",...], ["wall","floor",...]]}
```

`grid[y][x]` — y=0 is top row. Valid values: `wall`, `floor`, `goal`, `box`,
`box_on_goal`, `player`, `player_on_goal`. Must have exactly 1 player;
box count must equal goal count.

## moves.txt format

One line of characters from {U, D, L, R}. No spaces. Example: `UURDDL`

## Sokoban rules

- U/D/L/R moves the player one tile in that direction
- **Wall** in destination → invalid move → simulation halts (partial credit may still apply for boxes placed so far)
- **Floor/goal** in destination → player walks there
- **Box** in destination → check one cell further:
  - Wall or box beyond → invalid
  - Empty beyond → box pushed, player follows
- Boxes cannot be pulled. One box per move.
- **Solved:** no `box` cells remain (all are `box_on_goal`)

## Scoring (100 pts maximum)

| Component | Weight | Method |
|-----------|--------|--------|
| Format floor | 5 pts | Awarded for any structurally valid `state.json` with the correct grid dimensions |
| Grid parse | 25 pts | `25 × correct_cells / total_cells` |
| Puzzle solved | 50 pts | Full 50 pts **only** if every box reaches a goal cell with all moves valid. Partial solves receive 0 pts — the puzzle must be fully solved to score this component |
| Solution length | 20 pts | Only if fully solved: `20 × min(1, optimal/agent_len)` |

## Helper tools

```bash
# Inspect a single cell's pixel colors
python3 /task/tools/inspect_cell.py --col 3 --row 2

# Simulate your move string against your state.json  
python3 /task/tools/simulate_moves.py --state /output/state.json --moves /output/moves.txt -v
```

Available: `python3`, `Pillow==10.3.0`, `numpy==1.26.4`
