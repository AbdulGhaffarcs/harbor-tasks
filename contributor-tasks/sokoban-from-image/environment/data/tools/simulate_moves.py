#!/usr/bin/env python3
# MIT License — simulate_moves.py
# Agent helper: simulate a move string against a state JSON and report result.

import argparse
import json
from pathlib import Path


DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}


def find_player(grid):
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("player", "player_on_goal"):
                return (x, y)
    return None


def goal_positions(grid):
    out = set()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("goal", "box_on_goal", "player_on_goal"):
                out.add((x, y))
    return out


def apply_move(grid, move):
    if move not in DIRECTIONS:
        return grid, False, "unknown move letter"
    dx, dy = DIRECTIONS[move]
    pos = find_player(grid)
    if pos is None:
        return grid, False, "no player on grid"
    px, py = pos
    h, w = len(grid), len(grid[0])
    tx, ty = px + dx, py + dy
    if not (0 <= tx < w and 0 <= ty < h):
        return grid, False, "player would leave grid"
    target = grid[ty][tx]
    if target == "wall":
        return grid, False, "blocked by wall"

    new = [row[:] for row in grid]
    goals = goal_positions(grid)

    def clear(x, y):
        new[y][x] = "goal" if (x, y) in goals else "floor"

    def put_player(x, y):
        new[y][x] = "player_on_goal" if (x, y) in goals else "player"

    def put_box(x, y):
        new[y][x] = "box_on_goal" if (x, y) in goals else "box"

    if target in ("floor", "goal"):
        clear(px, py); put_player(tx, ty)
        return new, True, "ok"

    if target in ("box", "box_on_goal"):
        bx, by = tx + dx, ty + dy
        if not (0 <= bx < w and 0 <= by < h):
            return grid, False, "box would leave grid"
        beyond = grid[by][bx]
        if beyond in ("wall", "box", "box_on_goal"):
            return grid, False, f"cannot push box into {beyond}"
        clear(px, py); put_player(tx, ty); put_box(bx, by)
        return new, True, "pushed box"

    return grid, False, f"unknown target cell type {target}"


def is_solved(grid):
    for row in grid:
        for cell in row:
            if cell == "box":
                return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="/output/state.json",
                    help="State JSON with {width, height, grid}")
    ap.add_argument("--moves", required=True,
                    help="Move string file (e.g. /output/moves.txt) "
                         "or literal move string via --literal")
    ap.add_argument("--literal", action="store_true",
                    help="Treat --moves as a literal string, not a file path")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    state = json.loads(Path(args.state).read_text())
    grid  = state["grid"]

    if args.literal:
        moves = args.moves.strip()
    else:
        moves = Path(args.moves).read_text().strip()

    print(f"Starting state: {len(grid[0])}x{len(grid)} grid, {len(moves)} moves")

    for i, m in enumerate(moves):
        grid, ok, reason = apply_move(grid, m)
        if not ok:
            print(f"  move #{i} ({m}): INVALID — {reason}")
            print(f"Halted at move {i}. Puzzle solved: {is_solved(grid)}")
            return
        elif args.verbose:
            print(f"  move #{i} ({m}): {reason}")

    print(f"All {len(moves)} moves valid.")
    print(f"Puzzle solved: {is_solved(grid)}")

    # Count boxes still off goals
    boxes_off = sum(row.count("box") for row in grid)
    boxes_on  = sum(row.count("box_on_goal") for row in grid)
    print(f"  boxes on goal: {boxes_on}   boxes off goal: {boxes_off}")


if __name__ == "__main__":
    main()
