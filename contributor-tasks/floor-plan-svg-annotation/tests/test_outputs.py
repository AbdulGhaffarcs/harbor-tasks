"""
tests/test_outputs.py

Blind, deterministic geometric scoring for "Floor Plan SVG Annotation".

Rooms:   axis-aligned <rect> — IoU >= 0.40 (greedy nearest-neighbor matching)
Doors:   <circle> at hinge (<=15px) and leaf-end (<=20px)
Windows: <circle> at window midpoint (<=20px)
Paths:   <path> elements required for door arcs

Scoring: equal weight per component, averaged for final score.
No text content evaluated — coordinate-only.
"""

import json, math, pathlib, re, pytest

TESTS_DIR = pathlib.Path("/tests")
GT_FILE   = TESTS_DIR / "ground_truth.json"
OUTPUT    = pathlib.Path("/task/annotation.svg")
SCORE_FILE= TESTS_DIR / "score.txt"


def load_gt():
    return json.loads(GT_FILE.read_text())

def load_svg():
    return OUTPUT.read_text()

# ── Parsers ───────────────────────────────────────────────────────────────────

def _attr(attrs, key):
    m = re.search(rf'\b{key}\s*=\s*"([^"]*)"', attrs)
    return m.group(1) if m else None

def parse_circles(svg):
    out = []
    for m in re.finditer(r'<circle([^>]*)/?>', svg, re.IGNORECASE):
        a = m.group(1)
        cx, cy, r = _attr(a,"cx"), _attr(a,"cy"), _attr(a,"r")
        if cx and cy and r:
            try: out.append((float(cx), float(cy), float(r)))
            except: pass
    return out

def parse_rects(svg):
    out = []
    for m in re.finditer(r'<rect([^>]*)/?>', svg, re.IGNORECASE):
        a = m.group(1)
        x,y,w,h = _attr(a,"x"),_attr(a,"y"),_attr(a,"width"),_attr(a,"height")
        if x and y and w and h:
            try: out.append((float(x),float(y),float(w),float(h)))
            except: pass
    return out

def has_paths(svg):
    return bool(re.search(r'<path\b', svg, re.IGNORECASE))

# ── Geometry ──────────────────────────────────────────────────────────────────

def dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def iou(ax,ay,aw,ah, bx1,by1,bx2,by2):
    ax2,ay2 = ax+aw, ay+ah
    ix1=max(ax,bx1); iy1=max(ay,by1)
    ix2=min(ax2,bx2); iy2=min(ay2,by2)
    if ix2<=ix1 or iy2<=iy1: return 0.0
    inter=(ix2-ix1)*(iy2-iy1)
    return inter/(aw*ah+(bx2-bx1)*(by2-by1)-inter)

def greedy_match_proximity(gt_pts, circles, tol):
    """Greedy nearest-neighbor matching. Returns count of matched GT points."""
    used = set()
    matched = 0
    for gx,gy in gt_pts:
        best_d, best_i = float('inf'), -1
        for i,(cx,cy,r) in enumerate(circles):
            if i in used: continue
            d = dist((gx,gy),(cx,cy))
            if d < best_d:
                best_d, best_i = d, i
        if best_d <= tol:
            matched += 1
            used.add(best_i)
    return matched

def score_rooms(gt, rects):
    thresh = gt["scoring"]["room_rect_iou_threshold"]
    rooms  = list(gt["rooms"].values())
    used   = set()
    matched = 0
    for room in rooms:
        x1,y1,x2,y2 = room["bbox"]
        best_iou, best_i = 0.0, -1
        for i,(rx,ry,rw,rh) in enumerate(rects):
            if i in used: continue
            v = iou(rx,ry,rw,rh, x1,y1,x2,y2)
            if v > best_iou: best_iou, best_i = v, i
        if best_iou >= thresh:
            matched += 1
            if best_i >= 0: used.add(best_i)
    return matched / len(rooms)

def score_hinges(gt, circles):
    tol = gt["scoring"]["door_hinge_tolerance_px"]
    pts = [d["hinge"] for d in gt["doors"]]
    return greedy_match_proximity(pts, circles, tol) / len(pts)

def score_leaves(gt, circles):
    tol = gt["scoring"]["door_leaf_tolerance_px"]
    pts = [d["leaf_end"] for d in gt["doors"]]
    return greedy_match_proximity(pts, circles, tol) / len(pts)

def score_windows(gt, circles):
    tol = gt["scoring"]["window_midpoint_tolerance_px"]
    pts = [w["midpoint"] for w in gt["windows"]]
    n   = greedy_match_proximity(pts, circles, tol)
    return n / len(pts) if pts else 1.0

# ── Format tests ──────────────────────────────────────────────────────────────

class TestFormat:

    def test_output_exists(self):
        assert OUTPUT.exists(), f"annotation.svg not found at {OUTPUT}"

    def test_is_svg(self):
        assert "<svg" in load_svg().lower()

    def test_has_viewbox(self):
        gt  = load_gt()
        vp  = gt["viewport"]
        assert vp in load_svg(), f'SVG must contain viewBox="{vp}"'

    def test_has_rooms_layer(self):
        assert 'id="rooms"' in load_svg()

    def test_has_doors_layer(self):
        assert 'id="doors"' in load_svg()

    def test_has_rects(self):
        assert len(parse_rects(load_svg())) >= 1

    def test_has_circles(self):
        assert len(parse_circles(load_svg())) >= 1

    def test_has_paths(self):
        assert has_paths(load_svg())

# ── Accuracy tests ────────────────────────────────────────────────────────────

class TestAccuracy:

    def test_majority_rooms_correct(self):
        gt    = load_gt()
        rects = parse_rects(load_svg())
        s = score_rooms(gt, rects)
        assert s >= 0.50, f"Only {s*100:.0f}% of rooms correct — need >=50%"

    def test_at_least_one_room_correct(self):
        gt    = load_gt()
        rects = parse_rects(load_svg())
        s = score_rooms(gt, rects)
        assert s > 0, "No room rect matched any ground truth (IoU >= 0.40)"

    def test_at_least_one_hinge_correct(self):
        gt      = load_gt()
        circles = parse_circles(load_svg())
        s = score_hinges(gt, circles)
        assert s > 0, "No door hinge circle within 15px of ground truth"

    def test_majority_hinges_correct(self):
        gt      = load_gt()
        circles = parse_circles(load_svg())
        s = score_hinges(gt, circles)
        assert s >= 0.50, f"Only {s*100:.0f}% of hinges found — need >=50%"

    def test_leaf_ends_present(self):
        gt      = load_gt()
        circles = parse_circles(load_svg())
        s = score_leaves(gt, circles)
        assert s >= 0.30, f"Only {s*100:.0f}% of leaf ends found — need >=30%"

# ── Score ─────────────────────────────────────────────────────────────────────

class TestScore:
    def test_print_final_score(self, capsys):
        gt = load_gt()
        if not OUTPUT.exists():
            score = 0.0
        else:
            svg     = load_svg()
            rects   = parse_rects(svg)
            circles = parse_circles(svg)
            r = score_rooms(gt, rects)
            h = score_hinges(gt, circles)
            l = score_leaves(gt, circles)
            w = score_windows(gt, circles)
            score = round((r+h+l+w)/4*100, 2)
            with capsys.disabled():
                print(f"\n{'='*58}")
                print(f"  FINAL SCORE      : {score:.2f} / 100")
                print(f"  Room rects       : {r*100:.0f}%  ({len(rects)} rects)")
                print(f"  Door hinges      : {h*100:.0f}%  ({len(circles)} circles total)")
                print(f"  Door leaf ends   : {l*100:.0f}%")
                print(f"  Window midpoints : {w*100:.0f}%")
                print(f"{'='*58}")
        SCORE_FILE.write_text(str(score))
        assert True
