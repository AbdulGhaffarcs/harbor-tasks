"""
generate_chart.py — CC0 synthetic chart generator

Produces:
  environment/chart.png      — the chart the agent must reconstruct
  tests/ground_truth.json    — bar values, colours, labels (tests only, NOT in container)

Chart: grouped bar chart with 2 series, 4 categories.
Values chosen to be readable but non-trivial (not round numbers).
Colours, title, axis labels are all visually distinct and must be reproduced.
"""

import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

SEED = 42
rng  = np.random.default_rng(SEED)

# ── Ground truth data ─────────────────────────────────────────────────────────
CATEGORIES  = ["North", "South", "East", "West"]
SERIES      = ["2023", "2024"]
COLORS      = ["#3A7DC9", "#E8652A"]   # blue, orange

# Values: integers 10–95, chosen to be visually readable but non-trivial
VALUES = {
    "2023": [47, 63, 28, 81],
    "2024": [55, 39, 74, 62],
}

TITLE   = "Regional Sales by Year"
XLABEL  = "Region"
YLABEL  = "Sales (units)"
YLIM    = (0, 100)


def generate(out_png: pathlib.Path):
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=120)

    n_cats  = len(CATEGORIES)
    n_ser   = len(SERIES)
    x       = np.arange(n_cats)
    width   = 0.35
    offsets = np.linspace(-(n_ser - 1) * width / 2,
                           (n_ser - 1) * width / 2, n_ser)

    for i, (series, offset) in enumerate(zip(SERIES, offsets)):
        ax.bar(x + offset, VALUES[series], width,
               label=series, color=COLORS[i],
               edgecolor="white", linewidth=0.8)

    ax.set_title(TITLE, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel(XLABEL, fontsize=11)
    ax.set_ylabel(YLABEL, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(CATEGORIES, fontsize=10)
    ax.set_ylim(*YLIM)
    ax.set_yticks(range(0, 101, 20))
    ax.legend(fontsize=10, framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_png}")


if __name__ == "__main__":
    env_dir   = pathlib.Path("environment")
    tests_dir = pathlib.Path("tests")
    env_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)

    generate(env_dir / "chart.png")

    gt = {
        "title":      TITLE,
        "xlabel":     XLABEL,
        "ylabel":     YLABEL,
        "ylim":       list(YLIM),
        "categories": CATEGORIES,
        "series":     SERIES,
        "colors":     COLORS,
        "values":     VALUES,
    }
    with open(tests_dir / "ground_truth.json", "w") as f:
        json.dump(gt, f, indent=2)
    print(f"Saved tests/ground_truth.json")
