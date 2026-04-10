"""
synthetic-histology-segmentation — deterministic scoring.

Scoring (100pts):
  - Dice (Hungarian matched, per region): 40pts continuous
  - Region count accuracy (±2): 15pts
  - Area accuracy (±10% per region): 15pts
  - Classification accuracy: 20pts
  - Perimeter accuracy (±10% per region): 10pts

All math-based. No LLM. Hungarian matching handles label permutation.
"""
import json, csv, pathlib, pytest
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment

TESTS_DIR  = pathlib.Path("/tests")
GT_FILE    = TESTS_DIR / "ground_truth.json"
GT_MASK    = TESTS_DIR / "solution/gt_mask.png"
MASK_OUT   = pathlib.Path("/task/labeled_mask.png")
CSV_OUT    = pathlib.Path("/task/measurements.csv")
SCORE_FILE = TESTS_DIR / "score.txt"

def load_gt():    return json.loads(GT_FILE.read_text())
def load_gtmask():return np.array(Image.open(GT_MASK))

def dice(a, b):
    inter = np.logical_and(a > 0, b > 0).sum()
    denom = (a > 0).sum() + (b > 0).sum()
    return float(2 * inter / denom) if denom > 0 else 0.0

def build_dice_matrix(gt_mask, agent_mask, gt_labels, agent_labels):
    mat = np.zeros((len(gt_labels), max(len(agent_labels),1)))
    for i, gl in enumerate(gt_labels):
        for j, al in enumerate(agent_labels):
            mat[i,j] = dice(gt_mask==gl, agent_mask==al)
    return mat

def load_agent_csv():
    rows = list(csv.DictReader(open(CSV_OUT)))
    return rows


class TestFormat:
    def test_mask_exists(self):
        assert MASK_OUT.exists(), "labeled_mask.png not found at /task/labeled_mask.png"

    def test_mask_size(self):
        img = Image.open(MASK_OUT)
        assert img.size == (800,800), f"labeled_mask.png must be 800x800, got {img.size}"

    def test_mask_has_regions(self):
        arr = np.array(Image.open(MASK_OUT))
        labels = [l for l in np.unique(arr) if l > 0]
        assert len(labels) >= 1, "labeled_mask.png has no labeled regions"

    def test_csv_exists(self):
        assert CSV_OUT.exists(), "measurements.csv not found at /task/measurements.csv"

    def test_csv_has_required_columns(self):
        rows = load_agent_csv()
        assert len(rows) >= 1, "measurements.csv is empty"
        required = {"label","area_px2","perimeter","eccentricity",
                    "mean_intensity","classification"}
        cols = set(rows[0].keys())
        missing = required - cols
        assert not missing, f"measurements.csv missing columns: {missing}"

    def test_csv_has_rows(self):
        rows = load_agent_csv()
        assert len(rows) >= 3, f"Expected at least 3 rows, got {len(rows)}"

    def test_classification_values_valid(self):
        rows = load_agent_csv()
        valid = {"normal","enlarged"}
        for r in rows:
            assert r.get("classification","").lower() in valid, \
                f"Invalid classification: {r.get('classification')}"


class TestAccuracy:
    def test_region_count_reasonable(self):
        gt = load_gt()
        arr = np.array(Image.open(MASK_OUT))
        n = len([l for l in np.unique(arr) if l > 0])
        tol = gt["scoring"]["count_tolerance"]
        assert abs(n - gt["n_regions"]) <= tol*2, \
            f"Region count {n} too far from GT {gt['n_regions']} (tolerance ±{tol*2})"

    def test_at_least_one_enlarged_found(self):
        rows = load_agent_csv()
        enlarged = [r for r in rows if r.get("classification","").lower()=="enlarged"]
        assert len(enlarged) >= 1, "No enlarged regions found in CSV"

    def test_avg_dice_above_threshold(self):
        gt = load_gt(); gt_mask = load_gtmask()
        agent_mask = np.array(Image.open(MASK_OUT))
        gt_labels = [m["label"] for m in gt["measurements"]]
        ag_labels = [l for l in np.unique(agent_mask) if l > 0]
        if not ag_labels:
            pytest.fail("No regions in mask")
        mat = build_dice_matrix(gt_mask, agent_mask, gt_labels, ag_labels)
        ri, ci = linear_sum_assignment(-mat)
        avg = float(np.mean([mat[r,c] for r,c in zip(ri,ci)]))
        assert avg >= 0.15, f"Average Dice {avg:.3f} < 0.15 — segmentation too poor"


class TestScore:
    def test_print_final_score(self, capsys):
        gt = load_gt()
        if not MASK_OUT.exists() or not CSV_OUT.exists():
            SCORE_FILE.write_text("0.0"); return

        gt_mask    = load_gtmask()
        agent_mask = np.array(Image.open(MASK_OUT))
        gt_meas    = gt["measurements"]
        gt_labels  = [m["label"] for m in gt_meas]
        ag_labels  = [l for l in np.unique(agent_mask) if l > 0]
        N_gt = len(gt_labels); N_ag = len(ag_labels)

        # ── 1. Dice score: 40pts ──────────────────────────────────────────
        if ag_labels:
            mat = build_dice_matrix(gt_mask, agent_mask, gt_labels, ag_labels)
            ri, ci = linear_sum_assignment(-mat)
            matched_dice = [mat[r,c] for r,c in zip(ri,ci)]
            # Unmatched GT regions get dice=0
            all_dice = matched_dice + [0.0]*(N_gt - len(ri))
            avg_dice = float(np.mean(all_dice))
        else:
            avg_dice = 0.0
        dice_pts = avg_dice * 40

        # ── 2. Count accuracy: 15pts ──────────────────────────────────────
        tol = gt["scoring"]["count_tolerance"]
        diff = abs(N_ag - N_gt)
        if diff == 0:     count_pts = 15.0
        elif diff <= tol: count_pts = 15.0 * (1 - diff/(tol+1))
        else:             count_pts = max(0, 15.0 - diff*2)

        # ── 3. Area accuracy: 15pts ───────────────────────────────────────
        # Match agent CSV rows to GT by label via mask matching
        agent_rows = {int(r["label"]): r for r in load_agent_csv()
                      if r.get("label","").isdigit()}
        gt_by_lbl  = {m["label"]: m for m in gt_meas}

        area_pts = 0.0
        if ag_labels and matched_dice:
            area_tol = gt["scoring"]["area_tolerance_pct"] / 100
            pts_each = 15.0 / N_gt
            for r_idx, c_idx in zip(ri, ci):
                gl = gt_labels[r_idx]; al = ag_labels[c_idx]
                if mat[r_idx,c_idx] < gt["scoring"]["dice_threshold"]:
                    continue
                gt_area = gt_by_lbl[gl]["area_px2"]
                ag_row = agent_rows.get(al)
                if ag_row:
                    try:
                        ag_area = float(ag_row["area_px2"])
                        err = abs(ag_area - gt_area) / max(gt_area,1)
                        if err <= area_tol:             area_pts += pts_each
                        elif err <= area_tol * 2:       area_pts += pts_each * 0.5
                    except: pass

        # ── 4. Classification accuracy: 20pts ─────────────────────────────
        class_pts = 0.0
        if ag_labels and matched_dice:
            pts_each = 20.0 / N_gt
            for r_idx, c_idx in zip(ri, ci):
                gl = gt_labels[r_idx]; al = ag_labels[c_idx]
                if mat[r_idx,c_idx] < gt["scoring"]["dice_threshold"]:
                    continue
                gt_cls = gt_by_lbl[gl]["classification"]
                ag_row = agent_rows.get(al)
                if ag_row and ag_row.get("classification","").lower() == gt_cls:
                    class_pts += pts_each

        # ── 5. Perimeter accuracy: 10pts ──────────────────────────────────
        peri_pts = 0.0
        if ag_labels and matched_dice:
            peri_tol = gt["scoring"]["perimeter_tolerance_pct"] / 100
            pts_each = 10.0 / N_gt
            for r_idx, c_idx in zip(ri, ci):
                gl = gt_labels[r_idx]; al = ag_labels[c_idx]
                if mat[r_idx,c_idx] < gt["scoring"]["dice_threshold"]:
                    continue
                gt_peri = gt_by_lbl[gl]["perimeter"]
                ag_row = agent_rows.get(al)
                if ag_row:
                    try:
                        ag_peri = float(ag_row["perimeter"])
                        err = abs(ag_peri - gt_peri) / max(gt_peri,1)
                        if err <= peri_tol:         peri_pts += pts_each
                        elif err <= peri_tol*2:     peri_pts += pts_each * 0.5
                    except: pass

        total = dice_pts + count_pts + area_pts + class_pts + peri_pts
        score = round(min(100.0, total), 2)

        with capsys.disabled():
            print(f"\n{'='*60}")
            print(f"  FINAL SCORE        : {score:.2f} / 100")
            print(f"  Dice (40pts)       : {dice_pts:.1f}  avg={avg_dice:.3f}")
            print(f"  Count (15pts)      : {count_pts:.1f}  gt={N_gt} agent={N_ag}")
            print(f"  Area (15pts)       : {area_pts:.1f}")
            print(f"  Classification(20) : {class_pts:.1f}")
            print(f"  Perimeter (10pts)  : {peri_pts:.1f}")
            print(f"  Deterministic      : YES — Hungarian matched Dice")
            print(f"{'='*60}")

        SCORE_FILE.write_text(str(score))
        assert True
