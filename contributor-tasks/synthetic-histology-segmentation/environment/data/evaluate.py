#!/usr/bin/env python3
"""
Evaluation callback — agents call this to get feedback on their segmentation.
Prints per-region Dice scores and measurement errors.
Usage: python3 evaluate.py labeled_mask.png measurements.csv
"""
import sys, json, csv, pathlib, numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment

GT_DIR = pathlib.Path("/tests")

def dice(a, b):
    inter = np.logical_and(a, b).sum()
    return 2*inter / (a.sum() + b.sum()) if (a.sum()+b.sum()) > 0 else 0.0

def main():
    if len(sys.argv) < 3:
        print("Usage: evaluate.py labeled_mask.png measurements.csv")
        sys.exit(1)

    mask_path = pathlib.Path(sys.argv[1])
    csv_path  = pathlib.Path(sys.argv[2])

    if not mask_path.exists():
        print(f"ERROR: {mask_path} not found"); sys.exit(1)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found"); sys.exit(1)

    gt = json.loads((GT_DIR/"ground_truth.json").read_text())
    gt_mask = np.array(Image.open(GT_DIR/"solution/gt_mask.png"))

    agent_mask = np.array(Image.open(mask_path))
    agent_labels = [l for l in np.unique(agent_mask) if l > 0]
    gt_labels    = [m["label"] for m in gt["measurements"]]
    N_gt = len(gt_labels); N_ag = len(agent_labels)

    print(f"\n{'='*56}")
    print(f"  GT regions  : {N_gt}")
    print(f"  Your regions: {N_ag}  (target: {N_gt}±2)")

    # Build Dice matrix
    cost = np.zeros((N_gt, max(N_ag, 1)))
    for i, gl in enumerate(gt_labels):
        gt_bin = gt_mask == gl
        for j, al in enumerate(agent_labels):
            ag_bin = agent_mask == al
            cost[i,j] = dice(gt_bin, ag_bin)

    # Hungarian matching
    row_ind, col_ind = linear_sum_assignment(-cost)
    matched = [(gt_labels[r], agent_labels[c], cost[r,c])
               for r,c in zip(row_ind, col_ind)]
    avg_dice = np.mean([d for _,_,d in matched]) if matched else 0

    print(f"  Avg Dice    : {avg_dice:.3f}  (aim for >0.5)")
    print(f"\n  Per-region Dice (top matches):")
    for gl, al, d in sorted(matched, key=lambda x:-x[2])[:8]:
        status = "✓" if d >= 0.5 else "✗"
        print(f"    {status} GT-{gl:02d} ↔ Agent-{al:02d}: Dice={d:.3f}")

    # CSV check
    rows = list(csv.DictReader(open(csv_path)))
    print(f"\n  CSV rows: {len(rows)} (expected {N_gt})")
    if rows:
        print(f"  Columns: {list(rows[0].keys())}")

    print(f"{'='*56}\n")

if __name__ == "__main__":
    main()
