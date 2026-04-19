#!/usr/bin/env python3
# MIT License — generate_level.py
#
# Procedurally generates a Sokoban puzzle and all golden artifacts.
# All pixel assets are drawn from primitive shapes (no imported sprites).
#
# ═══════════════════════════════════════════════════════════════════════════
# RASTER SPECIFICATION (frozen — any change invalidates golden files)
# ═══════════════════════════════════════════════════════════════════════════
#   tile_size       : 40 × 40 px
#   margin          : 20 px padding on all four sides
#   image size      : margin*2 + grid_w*tile_size  by  margin*2 + grid_h*tile_size
#   color_mode      : RGB, solid fills, no antialiasing on large shapes
#   overlap render  : box-on-goal = box drawn ON TOP of goal (goal visible as border)
#   player-on-goal  : player drawn ON TOP of goal (goal visible as border)
# ═══════════════════════════════════════════════════════════════════════════
# CELL SCHEMA (for state.json and golden grid)
# ═══════════════════════════════════════════════════════════════════════════
#   Each cell is one of:
#     "wall"          solid wall, impassable
#     "floor"         empty walkable floor
#     "goal"          walkable floor marked as a target
#     "box"           box on a floor cell
#     "box_on_goal"   box that is already on a goal cell
#     "player"        the player, on a floor cell
#     "player_on_goal" the player, standing on a goal cell
#
#   Grid is row-major: grid[y][x] where y=0 is TOP row, x=0 is LEFT column.
# ═══════════════════════════════════════════════════════════════════════════
# SOKOBAN RULES (for simulation)
# ═══════════════════════════════════════════════════════════════════════════
#   Moves: U (up), D (down), L (left), R (right).
#   A move:
#     1. Determines the target cell in the movement direction from the player.
#     2. If target is wall → move is INVALID; simulation aborts with failure.
#     3. If target is empty floor/goal → player walks onto it.
#     4. If target is a box/box_on_goal → the cell BEYOND the box is checked:
#          • Beyond = wall or another box → move is INVALID; simulation aborts.
#          • Beyond = empty floor/goal   → box is pushed onto beyond-cell,
#                                          player walks onto target cell.
#   Push-only: boxes cannot be pulled. One box maximum per push.
#   Win condition: every box is on a goal cell.
#   Invalid moves terminate the simulation and zero the "puzzle solved" score.
# ═══════════════════════════════════════════════════════════════════════════

import argparse
import json
import random
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw

TILE           = 40
MARGIN         = 20
CELL_TYPES     = ["wall", "floor", "goal", "box", "box_on_goal",
                  "player", "player_on_goal"]

# Three distinct visual skins. Each maps the 7 cell types to fill colors.
# Skin selection is deterministic from seed.
SKINS = {
    "slate": {
        "bg":             "#E5E1D8",
        "wall":           "#3A4454",
        "wall_border":    "#242B36",
        "floor":          "#D7D2C7",
        "floor_border":   "#BCB6A8",
        "goal_ring":      "#C25050",
        "box":            "#8A6B3E",
        "box_border":     "#5C4628",
        "box_goal":       "#4D8A5E",
        "box_goal_border":"#2F5B3D",
        "player":         "#2A6DB5",
        "player_border":  "#174A85",
    },
    "moss": {
        "bg":             "#F0EAD8",
        "wall":           "#4A5A3A",
        "wall_border":    "#2F3C24",
        "floor":          "#E3D9BF",
        "floor_border":   "#C7B998",
        "goal_ring":      "#B85C2E",
        "box":            "#9A7344",
        "box_border":     "#6B4E2A",
        "box_goal":       "#5F8F4E",
        "box_goal_border":"#3B5E30",
        "player":         "#3A5AA0",
        "player_border":  "#223872",
    },
    "dusk": {
        "bg":             "#DCD6E2",
        "wall":           "#4C4057",
        "wall_border":    "#2F2738",
        "floor":          "#CCC3D3",
        "floor_border":   "#AFA2B8",
        "goal_ring":      "#AE4377",
        "box":            "#7F6A4B",
        "box_border":     "#54442F",
        "box_goal":       "#4F8A84",
        "box_goal_border":"#2F5854",
        "player":         "#5A4BAE",
        "player_border":  "#382F72",
    },
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ─── Level generation ──────────────────────────────────────────────────────
# Seed → hand-curated or procedurally arranged grid. We use a library of three
# hand-authored solvable layouts per difficulty and pick by seed. This ensures
# every level has an actual solution AND a known optimal path.

LEVEL_LIBRARY = {
    "easy": [
        [
            "#######",
            "#.....#",
            "#.$.@.#",
            "#.*...#",
            "#.....#",
            "#######",
        ],
        [
            "#######",
            "#.....#",
            "#..$..#",
            "#.*.@.#",
            "#.....#",
            "#######",
        ],
        [
            "########",
            "#......#",
            "#.@.$.*#",
            "#......#",
            "########",
        ],
    ],
    "medium": [
        [
            "############",
            "#..........B",
            "#.########.#",
            "#..........#",
            "########$#.#",
            "#.........*#",
            "#.#.########",
            "#..........#",
            "#.########.#",
            "#....P..$..#",
            "############",
        ],
    ],
}
# Level string symbols (de facto Sokoban text format):
#   #  wall
#   .  floor
#   *  goal
#   $  box  (on floor)
#   @  player (on floor)
#   B  box on a goal cell (already placed)
#   P  player standing on a goal cell

SYMBOL_TO_CELL = {
    "#": "wall",
    ".": "floor",
    "*": "goal",
    "$": "box",
    "@": "player",
    "B": "box_on_goal",
    "P": "player_on_goal",
}


def parse_level_strings(rows):
    """Convert list of strings to a grid of cell-type names."""
    h = len(rows)
    w = max(len(r) for r in rows)
    grid = [["floor"] * w for _ in range(h)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in SYMBOL_TO_CELL:
                raise ValueError(f"unknown level symbol {ch!r} at ({x},{y})")
            grid[y][x] = SYMBOL_TO_CELL[ch]
    return grid


# ─── Simulation ────────────────────────────────────────────────────────────

DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}


def find_player(grid):
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("player", "player_on_goal"):
                return (x, y)
    return None


def find_boxes(grid):
    out = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("box", "box_on_goal"):
                out.append((x, y))
    return out


def goal_positions(grid):
    """Return set of (x,y) that are goal cells (goal, box_on_goal, player_on_goal)."""
    goals = set()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("goal", "box_on_goal", "player_on_goal"):
                goals.add((x, y))
    return goals


def grid_signature(grid):
    """Compact hashable state for BFS: (player_pos, frozenset(box_positions))."""
    return (find_player(grid), frozenset(find_boxes(grid)))


def is_solved(grid):
    # All boxes sit on goals.
    for row in grid:
        for cell in row:
            if cell == "box":       # box NOT on a goal
                return False
    # And every goal cell exists (no stray boxes); implicitly all goals must
    # have something on them if box count == goal count (maintained by solver).
    return True


def apply_move(grid, move):
    """
    Return (new_grid, ok). ok=False if the move is invalid (wall bump or
    pushing into wall/box). Never mutates the input grid.
    """
    if move not in DIRECTIONS:
        return grid, False
    dx, dy = DIRECTIONS[move]
    px, py = find_player(grid)
    if px is None:
        return grid, False
    h, w = len(grid), len(grid[0])

    new = [row[:] for row in grid]
    goals = goal_positions(grid)

    def in_bounds(x, y):
        return 0 <= x < w and 0 <= y < h

    tx, ty = px + dx, py + dy
    if not in_bounds(tx, ty):
        return grid, False

    target = grid[ty][tx]

    def clear_player(x, y):
        if (x, y) in goals:
            new[y][x] = "goal"
        else:
            new[y][x] = "floor"

    def place_player(x, y):
        if (x, y) in goals:
            new[y][x] = "player_on_goal"
        else:
            new[y][x] = "player"

    def place_box(x, y):
        if (x, y) in goals:
            new[y][x] = "box_on_goal"
        else:
            new[y][x] = "box"

    if target == "wall":
        return grid, False

    if target in ("floor", "goal"):
        clear_player(px, py)
        place_player(tx, ty)
        return new, True

    if target in ("box", "box_on_goal"):
        bx, by = tx + dx, ty + dy
        if not in_bounds(bx, by):
            return grid, False
        beyond = grid[by][bx]
        if beyond in ("wall", "box", "box_on_goal"):
            return grid, False
        # push
        clear_player(px, py)
        place_player(tx, ty)
        place_box(bx, by)
        return new, True

    return grid, False


def simulate(initial_grid, moves):
    """
    Returns (final_grid, solved: bool, invalid_at: Optional[int]).
    invalid_at = index of first invalid move, or None if all valid.
    """
    grid = [row[:] for row in initial_grid]
    for i, m in enumerate(moves):
        grid, ok = apply_move(grid, m)
        if not ok:
            return grid, False, i
    return grid, is_solved(grid), None


# ─── BFS solver (optimal move count) ───────────────────────────────────────

def bfs_solve(initial_grid, max_states=400_000):
    """Return the shortest move string that solves the puzzle, or None."""
    start_sig = grid_signature(initial_grid)
    if is_solved(initial_grid):
        return ""

    frontier = deque([(initial_grid, "")])
    seen     = {start_sig}

    while frontier:
        if len(seen) > max_states:
            return None
        grid, path = frontier.popleft()
        for move in "UDLR":
            nxt, ok = apply_move(grid, move)
            if not ok:
                continue
            sig = grid_signature(nxt)
            if sig in seen:
                continue
            seen.add(sig)
            if is_solved(nxt):
                return path + move
            frontier.append((nxt, path + move))
    return None


# ─── Rendering ─────────────────────────────────────────────────────────────

def render(grid, skin_name, tile=TILE, margin=MARGIN):
    skin = SKINS[skin_name]
    h, w = len(grid), len(grid[0])
    img_w = margin * 2 + w * tile
    img_h = margin * 2 + h * tile
    img = Image.new("RGB", (img_w, img_h), hex_to_rgb(skin["bg"]))
    draw = ImageDraw.Draw(img)

    def cell_bbox(x, y):
        x0 = margin + x * tile
        y0 = margin + y * tile
        return (x0, y0, x0 + tile - 1, y0 + tile - 1)

    # Two passes: floor layer first, then features on top.
    for y in range(h):
        for x in range(w):
            cell = grid[y][x]
            x0, y0, x1, y1 = cell_bbox(x, y)

            if cell == "wall":
                draw.rectangle([x0, y0, x1, y1],
                               fill=hex_to_rgb(skin["wall"]),
                               outline=hex_to_rgb(skin["wall_border"]), width=2)
            else:
                # Floor base
                draw.rectangle([x0, y0, x1, y1],
                               fill=hex_to_rgb(skin["floor"]),
                               outline=hex_to_rgb(skin["floor_border"]), width=1)

                # Goal ring (drawn on the floor layer)
                if cell in ("goal", "box_on_goal", "player_on_goal"):
                    inset = 6
                    draw.ellipse([x0 + inset, y0 + inset,
                                  x1 - inset, y1 - inset],
                                 outline=hex_to_rgb(skin["goal_ring"]), width=3)

                # Box on top of goal (or on floor)
                if cell == "box":
                    inset = 5
                    draw.rectangle([x0 + inset, y0 + inset,
                                    x1 - inset, y1 - inset],
                                   fill=hex_to_rgb(skin["box"]),
                                   outline=hex_to_rgb(skin["box_border"]), width=2)
                elif cell == "box_on_goal":
                    inset = 5
                    draw.rectangle([x0 + inset, y0 + inset,
                                    x1 - inset, y1 - inset],
                                   fill=hex_to_rgb(skin["box_goal"]),
                                   outline=hex_to_rgb(skin["box_goal_border"]), width=2)

                # Player on top (circle)
                if cell in ("player", "player_on_goal"):
                    inset = 8
                    draw.ellipse([x0 + inset, y0 + inset,
                                  x1 - inset, y1 - inset],
                                 fill=hex_to_rgb(skin["player"]),
                                 outline=hex_to_rgb(skin["player_border"]), width=2)

    return img


# ─── Entry point ───────────────────────────────────────────────────────────

def pick_level(seed):
    rng = random.Random(seed)
    difficulty = rng.choice(["easy", "medium"])
    library = LEVEL_LIBRARY[difficulty]
    return rng.choice(library), difficulty


def pick_skin(seed):
    rng = random.Random(seed + 7919)  # independent RNG stream
    return rng.choice(list(SKINS.keys()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed",          type=int, default=31)
    ap.add_argument("--out-png",       default="/task/puzzle.png")
    ap.add_argument("--out-state",     default=None,
                    help="Golden state JSON (parsed grid). tests/solution only.")
    ap.add_argument("--out-solution",  default=None,
                    help="Optimal move string file. tests/solution only.")
    ap.add_argument("--out-meta",      default=None,
                    help="Meta JSON with skin, difficulty, dims. tests/solution only.")
    args = ap.parse_args()

    rows, difficulty = pick_level(args.seed)
    skin_name        = pick_skin(args.seed)
    grid             = parse_level_strings(rows)

    h, w = len(grid), len(grid[0])
    assert w <= 15 and h <= 12, "level too big for solver budget"

    img = render(grid, skin_name)
    Path(args.out_png).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out_png, "PNG")

    if args.out_state:
        state = {
            "width":  w,
            "height": h,
            "grid":   grid,
        }
        Path(args.out_state).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_state).write_text(json.dumps(state, indent=2))

    if args.out_solution:
        sol = bfs_solve(grid)
        assert sol is not None, "level has no solution; cannot be golden"
        Path(args.out_solution).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_solution).write_text(sol)

    if args.out_meta:
        meta = {
            "seed":       args.seed,
            "difficulty": difficulty,
            "skin":       skin_name,
            "width":      w,
            "height":     h,
            "tile_size":  TILE,
            "margin":     MARGIN,
            "num_boxes":  len(find_boxes(grid)),
            "num_goals":  len(goal_positions(grid)),
        }
        Path(args.out_meta).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_meta).write_text(json.dumps(meta, indent=2))

    print(f"seed={args.seed}  difficulty={difficulty}  skin={skin_name}  grid={w}x{h}")
    print(f"  boxes={len(find_boxes(grid))}  goals={len(goal_positions(grid))}")
    print(f"  PNG  → {args.out_png}")
    if args.out_state:    print(f"  state → {args.out_state}")
    if args.out_solution: print(f"  sol   → {args.out_solution}")


if __name__ == "__main__":
    main()
