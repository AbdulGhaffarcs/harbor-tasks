# Synthetic Histology Segmentation

## Overview

Analyze a synthetic grayscale histology slide, segment all cell nuclei,
measure their morphological properties, and classify each region.

## Input

| File | Path |
|------|------|
| Histology slide | `/task/slide.png` |
| Evaluation script | `/task/evaluate.py` |

`slide.png` is an 800×800 grayscale image. Darker regions (lower pixel
values) represent cell nuclei. Brighter regions are cytoplasm background.

## Required Outputs

**`/task/labeled_mask.png`** — 8-bit grayscale PNG, 800×800px  
- Background pixels = 0  
- Each segmented region = unique integer label 1, 2, 3, ... N  
- Use 8-connected labeling  

**`/task/measurements.csv`** — one row per region, exact schema:
```
label,area_px2,perimeter,eccentricity,mean_intensity,classification
1,452,85.3,0.612,48.2,normal
2,1243,142.7,0.441,36.8,enlarged
```

Column definitions:
- `label`: integer, matches label in labeled_mask.png
- `area_px2`: integer, pixel count of region
- `perimeter`: float 4dp, skimage regionprops perimeter (subpixel, 8-connected)
- `eccentricity`: float 4dp, skimage regionprops eccentricity (0=circle, 1=line)
- `mean_intensity`: float 4dp, mean of slide.png pixel values within region
- `classification`: `"normal"` if area is 200–800 px², `"enlarged"` if area > 800 px²

## Segmentation Approach

Use `/task/evaluate.py` to check your segmentation against GT after each attempt:

```bash
python3 /task/evaluate.py /task/labeled_mask.png /task/measurements.csv
```

This prints per-region Dice scores and measurement errors so you can
iteratively refine your threshold and morphological parameters.

## Technical Conventions

- **Threshold**: pixels with intensity < T are foreground (nuclei)
- **Morphological cleanup**: use `skimage.morphology.opening` before labeling
- **Connectivity**: 8-connected (`connectivity=2` in `skimage.measure.label`)
- **Minimum region**: ignore regions with area < 200 px²
- **Measurements**: use `skimage.measure.regionprops` on the final labeled mask
  with `intensity_image=slide_array` for mean_intensity

## Scoring

| Component | Weight |
|-----------|--------|
| Per-region Dice (Hungarian matched) | 40% |
| Region count accuracy (±2 tolerance) | 15% |
| Area measurement accuracy (±10%) | 15% |
| Classification accuracy | 20% |
| Perimeter accuracy (±10%) | 10% |
