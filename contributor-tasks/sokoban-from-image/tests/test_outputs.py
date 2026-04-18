"""
test_outputs.py — Deterministic blind tests for sokoban-from-image.

Scoring (100 pts):
  - Parse accuracy  : 30 pts  (per-cell match vs golden state)
  - Puzzle solved   : 50 pts  (simulate moves on GOLDEN state, fraction on-goal)
  - Solution length : 20 pts  (min(1, optimal / agent_length) × 20)

The solver is re-run from the golden state (same BFS code as the generator)
to derive the optimal length — reproducible and embedded in the test file
rather than read from any file the agent could tamper with.
"""

import json
import pathlib
from collections import deque

import pytest

# ─── Paths ─────────────────────────────────────────────────────────────────

TESTS_DIR        = pathlib.Path("/tests")
SCORE_FILE       = TESTS_DIR / "score.txt"
GOLDEN_STATE     = TESTS_DIR / "solution" / "state.json"
GOLDEN_SOLUTION  = TESTS_DIR / "solution" / "solution.txt"
AGENT_STATE      = pathlib.Path("/output/state.json")
AGENT_MOVES      = pathlib.Path("/output/moves.txt")

CELL_TYPES = {"wall", "floor", "goal", "box", "box_on_goal",
              "player", "player_on_goal"}

DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}


# ─── Pure-Python Sokoban simulator (mirrors generator) ─────────────────────

def find_player(grid):
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("player", "player_on_goal"):
                return (x, y)
    return None


def goal_positions(grid):
    goals = set()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell in ("goal", "box_on_goal", "player_on_goal"):
                goals.add((x, y))
    return goals


def box_positions(grid):
    return [(x, y)
            for y, row in enumerate(grid)
            for x, cell in enumerate(row)
            if cell in ("box", "box_on_goal")]


def is_solved(grid):
    for row in grid:
        for cell in row:
            if cell == "box":
                return False
    return True


def apply_move(grid, move):
    if move not in DIRECTIONS:
        return grid, False
    dx, dy = DIRECTIONS[move]
    pos = find_player(grid)
    if pos is None:
        return grid, False
    px, py = pos
    h, w = len(grid), len(grid[0])
    tx, ty = px + dx, py + dy
    if not (0 <= tx < w and 0 <= ty < h):
        return grid, False
    target = grid[ty][tx]
    new = [row[:] for row in grid]
    goals = goal_positions(grid)

    def clear(x, y):
        new[y][x] = "goal" if (x, y) in goals else "floor"

    def put_player(x, y):
        new[y][x] = "player_on_goal" if (x, y) in goals else "player"

    def put_box(x, y):
        new[y][x] = "box_on_goal" if (x, y) in goals else "box"

    if target == "wall":
        return grid, False
    if target in ("floor", "goal"):
        clear(px, py); put_player(tx, ty)
        return new, True
    if target in ("box", "box_on_goal"):
        bx, by = tx + dx, ty + dy
        if not (0 <= bx < w and 0 <= by < h):
            return grid, False
        beyond = grid[by][bx]
        if beyond in ("wall", "box", "box_on_goal"):
            return grid, False
        clear(px, py); put_player(tx, ty); put_box(bx, by)
        return new, True
    return grid, False


def simulate(initial, moves):
    """Return (final_grid, all_moves_valid, invalid_move_index)."""
    grid = [row[:] for row in initial]
    for i, m in enumerate(moves):
        grid, ok = apply_move(grid, m)
        if not ok:
            return grid, False, i
    return grid, True, None


def sig(grid):
    return (find_player(grid), frozenset(box_positions(grid)))


def bfs_optimal(initial, max_states=400_000):
    if is_solved(initial):
        return 0
    start = sig(initial)
    q = deque([(initial, 0)])
    seen = {start}
    while q:
        if len(seen) > max_states:
            return None
        grid, d = q.popleft()
        for m in "UDLR":
            nxt, ok = apply_move(grid, m)
            if not ok:
                continue
            s = sig(nxt)
            if s in seen:
                continue
            seen.add(s)
            if is_solved(nxt):
                return d + 1
            q.append((nxt, d + 1))
    return None


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def golden_state():
    assert GOLDEN_STATE.exists(), f"Golden state missing: {GOLDEN_STATE}"
    return json.loads(GOLDEN_STATE.read_text())


@pytest.fixture(scope="session")
def golden_grid(golden_state):
    return golden_state["grid"]


@pytest.fixture(scope="session")
def optimal_length(golden_grid):
    """Recompute optimal from golden grid. Embeds the test's own source-of-truth."""
    n = bfs_optimal(golden_grid)
    assert n is not None, "golden grid has no BFS solution (generator bug)"
    return n


@pytest.fixture(scope="session")
def agent_state_maybe():
    """Agent state may be missing/malformed; don't fail the whole suite."""
    if not AGENT_STATE.exists():
        return None
    try:
        data = json.loads(AGENT_STATE.read_text())
    except Exception:
        return None
    return data


@pytest.fixture(scope="session")
def agent_moves_maybe():
    if not AGENT_MOVES.exists():
        return None
    txt = AGENT_MOVES.read_text().strip()
    # Keep only valid characters
    return "".join(c for c in txt if c in "UDLR")


# ─── Format tests ───────────────────────────────────────────────────────────

class TestFormat:
    def test_state_file_present(self):
        assert AGENT_STATE.exists(), (
            f"{AGENT_STATE} missing. The agent must write its parsed grid."
        )

    def test_moves_file_present(self):
        assert AGENT_MOVES.exists(), (
            f"{AGENT_MOVES} missing. The agent must write its move sequence."
        )

    def test_state_is_valid_json(self):
        try:
            json.loads(AGENT_STATE.read_text())
        except Exception as e:
            pytest.fail(f"state.json not valid JSON: {e}")

    def test_state_has_required_keys(self, agent_state_maybe):
        if agent_state_maybe is None:
            pytest.fail("state.json unreadable")
        for k in ("width", "height", "grid"):
            assert k in agent_state_maybe, f"state.json missing key {k!r}"

    def test_state_dimensions_match(self, agent_state_maybe, golden_state):
        if agent_state_maybe is None:
            pytest.skip("no agent state")
        assert agent_state_maybe["width"]  == golden_state["width"], \
            "state.json width does not match the rendered puzzle"
        assert agent_state_maybe["height"] == golden_state["height"], \
            "state.json height does not match the rendered puzzle"

    def test_state_cells_are_valid_types(self, agent_state_maybe):
        if agent_state_maybe is None:
            pytest.skip("no agent state")
        bad = []
        for y, row in enumerate(agent_state_maybe["grid"]):
            for x, cell in enumerate(row):
                if cell not in CELL_TYPES:
                    bad.append((x, y, cell))
        assert not bad, f"Invalid cell types (first 5): {bad[:5]}"

    def test_moves_are_valid_chars(self, agent_moves_maybe):
        if agent_moves_maybe is None:
            pytest.skip("no agent moves")
        assert len(agent_moves_maybe) > 0, "moves.txt is empty"


# ─── Accuracy gate ──────────────────────────────────────────────────────────

class TestAccuracy:
    def test_at_least_some_parse_correct(self, agent_state_maybe, golden_grid):
        if agent_state_maybe is None:
            pytest.skip("no agent state")
        agrid = agent_state_maybe["grid"]
        gh, gw = len(golden_grid), len(golden_grid[0])
        ah = len(agrid)
        aw = len(agrid[0]) if ah > 0 else 0
        if (ah, aw) != (gh, gw):
            pytest.fail(f"Grid shape mismatch: agent {aw}x{ah}  golden {gw}x{gh}")
        correct = sum(1
                      for y in range(gh) for x in range(gw)
                      if agrid[y][x] == golden_grid[y][x])
        total = gh * gw
        frac = correct / total
        assert frac >= 0.40, (
            f"Only {correct}/{total} cells correct ({frac:.1%}); "
            "parse is far below the accuracy floor."
        )


# ─── Final weighted score ──────────────────────────────────────────────────

class TestScore:
    def test_compute_and_write_final_score(self, agent_state_maybe,
                                           agent_moves_maybe, golden_state,
                                           golden_grid, optimal_length, capsys):

        # ─── 1. Parse accuracy: 30 pts ─────────────────────────────────────
        gh, gw = len(golden_grid), len(golden_grid[0])
        total_cells = gh * gw

        parse_pts = 0.0
        correct   = 0
        if agent_state_maybe is not None:
            agrid = agent_state_maybe.get("grid")
            if agrid and len(agrid) == gh and all(len(r) == gw for r in agrid):
                for y in range(gh):
                    for x in range(gw):
                        if agrid[y][x] == golden_grid[y][x]:
                            correct += 1
                parse_pts = 30.0 * correct / total_cells

        # ─── 2. Puzzle solved: 50 pts ──────────────────────────────────────
        solved_pts      = 0.0
        boxes_on_goal   = 0
        total_boxes     = len(box_positions(golden_grid))
        invalid_at      = None
        all_valid       = False
        solved_ratio    = 0.0

        if agent_moves_maybe and total_boxes > 0:
            final, all_valid, invalid_at = simulate(golden_grid, agent_moves_maybe)
            if all_valid:
                boxes_on_goal = sum(row.count("box_on_goal") for row in final)
                # player_on_goal occupies a goal cell but does not count as a placed box
                solved_ratio = boxes_on_goal / total_boxes
                solved_pts = 50.0 * solved_ratio
            else:
                solved_pts = 0.0  # invalid move halts everything

        # ─── 3. Solution length: 20 pts ────────────────────────────────────
        length_pts = 0.0
        agent_len  = len(agent_moves_maybe) if agent_moves_maybe else 0
        if agent_moves_maybe and all_valid and solved_ratio == 1.0 and agent_len > 0:
            length_pts = 20.0 * min(1.0, optimal_length / agent_len)

        total = round(parse_pts + solved_pts + length_pts, 2)
        total = max(0.0, min(100.0, total))

        with capsys.disabled():
            print(f"\n{'=' * 62}")
            print(f"  FINAL SCORE           : {total:.2f} / 100")
            print(f"  Parse accuracy (30pt) : {parse_pts:.2f}  "
                  f"cells={correct}/{total_cells}")
            print(f"  Puzzle solved  (50pt) : {solved_pts:.2f}  "
                  f"boxes_on_goal={boxes_on_goal}/{total_boxes}  "
                  f"all_valid={all_valid}  invalid_at={invalid_at}")
            print(f"  Solution length(20pt) : {length_pts:.2f}  "
                  f"agent_len={agent_len}  optimal={optimal_length}")
            print(f"  Deterministic : YES — blind simulation on golden state")
            print(f"{'=' * 62}")

        SCORE_FILE.write_text(str(total))
        assert True
