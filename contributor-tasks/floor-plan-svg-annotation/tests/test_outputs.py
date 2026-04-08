"""
Floor Plan SVG Annotation — geometric scoring.
Rooms: IoU>=0.35. Hinges: <=25px. Leaves: <=15px. Windows: <=30px.
Score = mean(rooms, hinges, leaves, windows) * 100
"""
import json, math, pathlib, re, pytest

TESTS_DIR  = pathlib.Path("/tests")
GT_FILE    = TESTS_DIR / "ground_truth.json"
OUTPUT     = pathlib.Path("/task/annotation.svg")
SCORE_FILE = TESTS_DIR / "score.txt"

def load_gt():   return json.loads(GT_FILE.read_text())
def load_svg():  return OUTPUT.read_text()

def _get(a, k):
    m = re.search(rf'\b{k}\s*=\s*"([^"]*)"', a)
    return m.group(1) if m else None

def parse_circles(svg):
    out = []
    for m in re.finditer(r'<circle([^>]*)/?>', svg, re.IGNORECASE):
        a = m.group(1)
        cx, cy, r = _get(a,"cx"), _get(a,"cy"), _get(a,"r")
        if cx and cy and r:
            try: out.append((float(cx), float(cy), float(r)))
            except ValueError: pass
    return out

def parse_rects(svg):
    out = []
    for m in re.finditer(r'<rect([^>]*)/?>', svg, re.IGNORECASE):
        a = m.group(1)
        x, y, w, h = _get(a,"x"), _get(a,"y"), _get(a,"width"), _get(a,"height")
        if x and y and w and h:
            try: out.append((float(x), float(y), float(w), float(h)))
            except ValueError: pass
    return out

def has_paths(svg): return bool(re.search(r'<path\b', svg, re.IGNORECASE))
def dist(a, b): return math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)

def iou(ax,ay,aw,ah,bx1,by1,bx2,by2):
    ax2,ay2=ax+aw,ay+ah
    ix1=max(ax,bx1);iy1=max(ay,by1);ix2=min(ax2,bx2);iy2=min(ay2,by2)
    if ix2<=ix1 or iy2<=iy1: return 0.0
    inter=(ix2-ix1)*(iy2-iy1)
    union=aw*ah+(bx2-bx1)*(by2-by1)-inter
    return inter/union if union>0 else 0.0

def greedy(gt_pts, circles, tol):
    used=set(); matched=0
    for gx,gy in gt_pts:
        best_d,best_i=float('inf'),-1
        for i,(cx,cy,r) in enumerate(circles):
            if i in used: continue
            d=dist((gx,gy),(cx,cy))
            if d<best_d: best_d,best_i=d,i
        if best_d<=tol: matched+=1; used.add(best_i)
    return matched

def score_rooms(gt,rects):
    thresh=gt["scoring"]["room_rect_iou_threshold"]
    used=set(); matched=0
    for room in gt["rooms"].values():
        x1,y1,x2,y2=room["bbox"]; best,bi=0.0,-1
        for i,(rx,ry,rw,rh) in enumerate(rects):
            if i in used: continue
            v=iou(rx,ry,rw,rh,x1,y1,x2,y2)
            if v>best: best,bi=v,i
        if best>=thresh: matched+=1
        if bi>=0 and best>=thresh: used.add(bi)
    return matched/len(gt["rooms"])

def score_hinges(gt,circles):
    tol=gt["scoring"]["door_hinge_tolerance_px"]
    return greedy([d["hinge"] for d in gt["doors"]],circles,tol)/len(gt["doors"])

def score_leaves(gt,circles):
    tol=gt["scoring"]["door_leaf_tolerance_px"]
    return greedy([d["leaf_end"] for d in gt["doors"]],circles,tol)/len(gt["doors"])

def score_windows(gt,circles):
    tol=gt["scoring"]["window_midpoint_tolerance_px"]
    pts=[w["midpoint"] for w in gt["windows"]]
    return greedy(pts,circles,tol)/len(pts) if pts else 1.0


class TestFormat:
    def test_output_exists(self):
        assert OUTPUT.exists(),"annotation.svg not found at /task/annotation.svg"
    def test_is_valid_svg(self):
        assert "<svg" in load_svg().lower()
    def test_has_correct_viewbox(self):
        assert load_gt()["viewport"] in load_svg()
    def test_has_rooms_layer(self):
        assert 'id="rooms"' in load_svg()
    def test_has_doors_layer(self):
        assert 'id="doors"' in load_svg()
    def test_has_rect_elements(self):
        assert len(parse_rects(load_svg()))>=1
    def test_has_circle_elements(self):
        assert len(parse_circles(load_svg()))>=1
    def test_has_path_elements(self):
        assert has_paths(load_svg())


class TestAccuracy:
    def test_at_least_one_room(self):
        gt=load_gt()
        assert score_rooms(gt,parse_rects(load_svg()))>0,"No room matched GT (IoU>=0.35)"
    def test_majority_rooms(self):
        gt=load_gt(); s=score_rooms(gt,parse_rects(load_svg()))
        assert s>=0.50,f"{s*100:.0f}% rooms correct — need >=50%"
    def test_at_least_one_hinge(self):
        gt=load_gt()
        assert score_hinges(gt,parse_circles(load_svg()))>0,"No hinge within 25px of GT"
    def test_majority_hinges(self):
        gt=load_gt(); s=score_hinges(gt,parse_circles(load_svg()))
        assert s>=0.40,f"{s*100:.0f}% hinges — need >=40%"


class TestScore:
    def test_print_final_score(self,capsys):
        gt=load_gt()
        if not OUTPUT.exists(): score=0.0
        else:
            svg=load_svg(); rects=parse_rects(svg); circles=parse_circles(svg)
            r=score_rooms(gt,rects); h=score_hinges(gt,circles)
            l=score_leaves(gt,circles); w=score_windows(gt,circles)
            # Weighted: leaves(0.50) + windows(0.25) + rooms(0.15) + hinges(0.10)
            score=round((0.15*r + 0.10*h + 0.50*l + 0.25*w)*100,2)
            with capsys.disabled():
                print(f"\n{'='*60}")
                print(f"  FINAL SCORE      : {score:.2f} / 100  (weights: rooms=15%, hinges=10%, leaves=50%, windows=25%)")
                print(f"  Room rects       : {r*100:.0f}%  ({len(rects)} rects)")
                print(f"  Door hinges      : {h*100:.0f}%  ({len(circles)} circles, tol={gt['scoring']['door_hinge_tolerance_px']}px)")
                print(f"  Door leaf-ends   : {l*100:.0f}%  (tol={gt['scoring']['door_leaf_tolerance_px']}px)")
                print(f"  Window midpoints : {w*100:.0f}%  (tol={gt['scoring']['window_midpoint_tolerance_px']}px)")
                print(f"{'='*60}")
        SCORE_FILE.write_text(str(score))
        assert True
