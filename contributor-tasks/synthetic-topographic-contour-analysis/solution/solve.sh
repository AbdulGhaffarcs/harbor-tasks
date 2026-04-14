#!/bin/bash
set -e

echo "=== Golden Solution: Synthetic Topographic Contour Analysis ==="
echo "Generating golden outputs from DEM..."

mkdir -p /task/outputs

# The golden solution uses the generator to produce all outputs,
# then copies them to the outputs directory.
# This is self-contained — no heredoc, no external downloads.

python3 << 'PYTHON_SCRIPT'
import numpy as np
from scipy.ndimage import gaussian_filter, label, minimum_filter, maximum_filter, distance_transform_edt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import csv
import json
import os

# === CONFIG (must match generate_map.py exactly) ===
SEED = 42
IMG_W, IMG_H = 1400, 1100
DEM_W, DEM_H = 700, 550
NUM_PEAKS = 4
NUM_SADDLES = 2
CONTOUR_INTERVAL = 50
PROFILE_SAMPLE_INTERVAL = 1

np.random.seed(SEED)

# === GENERATE DEM (identical to generator) ===
dem = np.zeros((DEM_H, DEM_W), dtype=np.float64)

quadrants = [
    (0.15, 0.45, 0.15, 0.45),
    (0.55, 0.85, 0.15, 0.45),
    (0.15, 0.45, 0.55, 0.85),
    (0.55, 0.85, 0.55, 0.85),
]
peak_params = []
for i in range(NUM_PEAKS):
    qx_lo, qx_hi, qy_lo, qy_hi = quadrants[i % len(quadrants)]
    cx = np.random.randint(int(DEM_W * qx_lo), int(DEM_W * qx_hi))
    cy = np.random.randint(int(DEM_H * qy_lo), int(DEM_H * qy_hi))
    height = np.random.uniform(400, 700)
    sigma_x = np.random.uniform(40, 80)
    sigma_y = np.random.uniform(40, 80)
    yy, xx = np.mgrid[0:DEM_H, 0:DEM_W]
    gaussian = height * np.exp(-(
        ((xx - cx)**2) / (2 * sigma_x**2) +
        ((yy - cy)**2) / (2 * sigma_y**2)
    ))
    dem += gaussian
    peak_params.append({'cx': int(cx), 'cy': int(cy), 'height': float(height),
                        'sigma_x': float(sigma_x), 'sigma_y': float(sigma_y)})

for i in range(min(NUM_SADDLES, NUM_PEAKS - 1)):
    p1, p2 = peak_params[i], peak_params[i+1]
    ridge_height = min(p1['height'], p2['height']) * 0.3
    for t in np.linspace(0, 1, 8):
        rx = p1['cx'] + t * (p2['cx'] - p1['cx'])
        ry = p1['cy'] + t * (p2['cy'] - p1['cy'])
        yy, xx = np.mgrid[0:DEM_H, 0:DEM_W]
        dem += ridge_height * np.exp(-((xx - rx)**2 + (yy - ry)**2) / (2 * 30**2))

noise = np.random.randn(DEM_H, DEM_W) * 30
noise = gaussian_filter(noise, sigma=25)
dem += noise
dem = np.clip(dem, 0, None)
dem = gaussian_filter(dem, sigma=3)

print(f"DEM: shape={dem.shape}, range=[{dem.min():.1f}, {dem.max():.1f}]")

# === FIND PEAKS ===
local_max = maximum_filter(dem, size=40)
peaks_mask = (dem == local_max) & (dem > 200)
labeled_pk, num_pk = label(peaks_mask)
peaks = []
for i in range(1, num_pk + 1):
    region = np.where(labeled_pk == i)
    idx = np.argmax(dem[region])
    py, px = region[0][idx], region[1][idx]
    peaks.append({'dem_x': int(px), 'dem_y': int(py), 'elevation': float(np.round(dem[py, px], 1))})
peaks.sort(key=lambda p: p['elevation'], reverse=True)
peaks = peaks[:NUM_PEAKS + 1]
print(f"Peaks: {len(peaks)}")

# === CONTOUR EXTRACTION ===
max_elev = np.max(dem)
levels = np.arange(CONTOUR_INTERVAL, max_elev, CONTOUR_INTERVAL)

fig, ax = plt.subplots(1, 1, figsize=(DEM_W/100, DEM_H/100), dpi=100)
ax.set_xlim(0, DEM_W); ax.set_ylim(DEM_H, 0)
cs = ax.contour(dem, levels=levels)
plt.close()

scale = IMG_W / DEM_W

# === OUTPUT 1: overlay.svg ===
svg_lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{IMG_W}" height="{IMG_H}" viewBox="0 0 {IMG_W} {IMG_H}">']
svg_lines.append('  <g id="contours">')

contour_data = []
for i, level_val in enumerate(cs.levels):
    segments = cs.allsegs[i]
    for j, seg in enumerate(segments):
        vertices = seg * scale
        if len(vertices) < 3:
            continue
        d_parts = [f'M {vertices[0][0]:.1f} {vertices[0][1]:.1f}']
        for v in vertices[1:]:
            d_parts.append(f'L {v[0]:.1f} {v[1]:.1f}')
        d_parts.append('Z')
        cid = f'contour_{i}_{j}'
        svg_lines.append(f'    <g id="{cid}" data-elevation="{level_val:.0f}">')
        svg_lines.append(f'      <path d="{" ".join(d_parts)}" fill="none" stroke="#4a3728" stroke-width="1.5" />')
        svg_lines.append(f'    </g>')
        contour_data.append({
            'id': cid, 'elevation': float(level_val),
            'vertices': vertices.tolist(),
            'centroid': [float(np.mean(vertices[:,0])), float(np.mean(vertices[:,1]))]
        })

svg_lines.append('  </g>')

svg_lines.append('  <g id="peaks">')
for i, pk in enumerate(peaks):
    px, py = pk['dem_x'] * scale, pk['dem_y'] * scale
    svg_lines.append(f'    <circle id="peak_{i+1}" cx="{px:.1f}" cy="{py:.1f}" r="8" '
                     f'fill="red" stroke="darkred" stroke-width="2" data-elevation="{pk["elevation"]:.1f}" />')
svg_lines.append('  </g>')

# Nesting
svg_lines.append('  <g id="nesting">')
contour_data.sort(key=lambda c: c['elevation'])
nesting_edges = []
for child in contour_data:
    best_parent = None
    best_elev = -1
    for parent in contour_data:
        if parent['elevation'] >= child['elevation']:
            continue
        if len(parent['vertices']) < 3:
            continue
        try:
            mpl_path = MplPath(parent['vertices'])
            if mpl_path.contains_point(child['centroid']):
                if parent['elevation'] > best_elev:
                    best_elev = parent['elevation']
                    best_parent = parent
        except:
            continue
    if best_parent:
        nesting_edges.append({'child_id': child['id'], 'parent_id': best_parent['id']})
        svg_lines.append(
            f'    <line x1="{child["centroid"][0]:.1f}" y1="{child["centroid"][1]:.1f}" '
            f'x2="{best_parent["centroid"][0]:.1f}" y2="{best_parent["centroid"][1]:.1f}" '
            f'stroke="blue" stroke-width="1" stroke-dasharray="4,4" '
            f'data-child="{child["id"]}" data-parent="{best_parent["id"]}" />')

svg_lines.append('  </g>')
svg_lines.append('</svg>')

with open('/task/outputs/overlay.svg', 'w') as f:
    f.write('\n'.join(svg_lines))
print("Wrote overlay.svg")

# === OUTPUT 2: watersheds.png ===
local_min = minimum_filter(dem, size=50)
minima_mask = (dem == local_min) & (dem < np.percentile(dem, 30))
labeled_minima, num_basins = label(minima_mask)

if num_basins < 3:
    local_min = minimum_filter(dem, size=30)
    minima_mask = (dem == local_min) & (dem < np.percentile(dem, 40))
    labeled_minima, num_basins = label(minima_mask)

if num_basins > 8:
    sizes = [(i, np.sum(labeled_minima == i)) for i in range(1, num_basins + 1)]
    sizes.sort(key=lambda x: x[1], reverse=True)
    keep = set([s[0] for s in sizes[:6]])
    new_labeled = np.zeros_like(labeled_minima)
    new_id = 1
    for old_id in sorted(keep):
        new_labeled[labeled_minima == old_id] = new_id
        new_id += 1
    labeled_minima = new_labeled
    num_basins = len(keep)

h, w = dem.shape
watershed = np.zeros((h, w), dtype=np.int32)
watershed[labeled_minima > 0] = labeled_minima[labeled_minima > 0]

flat_indices = np.argsort(dem.ravel())
dy = [-1, -1, -1, 0, 0, 1, 1, 1]
dx = [-1, 0, 1, -1, 1, -1, 0, 1]

for idx in flat_indices:
    y, x = divmod(idx, w)
    if watershed[y, x] > 0:
        continue
    best_basin, best_elev = 0, 1e9
    for d in range(8):
        ny, nx = y + dy[d], x + dx[d]
        if 0 <= ny < h and 0 <= nx < w:
            if watershed[ny, nx] > 0 and dem[ny, nx] < best_elev:
                best_elev = dem[ny, nx]
                best_basin = watershed[ny, nx]
    if best_basin > 0:
        watershed[y, x] = best_basin

unassigned = watershed == 0
if np.any(unassigned):
    _, nearest_indices = distance_transform_edt(unassigned, return_distances=True, return_indices=True)
    watershed[unassigned] = watershed[nearest_indices[0][unassigned], nearest_indices[1][unassigned]]

basin_colors = [
    [31, 119, 180], [255, 127, 14], [44, 160, 44], [214, 39, 40],
    [148, 103, 189], [140, 86, 75], [227, 119, 194], [127, 127, 127],
]
img = np.zeros((h, w, 3), dtype=np.uint8)
for bid in range(1, int(np.max(watershed)) + 1):
    img[watershed == bid] = basin_colors[(bid - 1) % len(basin_colors)]

from PIL import Image
pil_img = Image.fromarray(img).resize((IMG_W, IMG_H), Image.NEAREST)
pil_img.save('/task/outputs/watersheds.png')
print(f"Wrote watersheds.png ({num_basins} basins)")

# === OUTPUT 3: profile.csv ===
point_a = (80, 100)
point_b = (620, 450)
ax_c, ay = point_a
bx, by = point_b
distance = np.sqrt((bx - ax_c)**2 + (by - ay)**2)
num_samples = int(distance / PROFILE_SAMPLE_INTERVAL) + 1

with open('/task/outputs/profile.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['distance_m', 'elevation_m'])
    for i in range(num_samples):
        t = i / max(num_samples - 1, 1)
        x = ax_c + t * (bx - ax_c)
        y = ay + t * (by - ay)
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        x1, y1 = min(x0 + 1, DEM_W - 1), min(y0 + 1, DEM_H - 1)
        xf, yf = x - x0, y - y0
        elev = (dem[y0, x0] * (1 - xf) * (1 - yf) +
                dem[y0, x1] * xf * (1 - yf) +
                dem[y1, x0] * (1 - xf) * yf +
                dem[y1, x1] * xf * yf)
        writer.writerow([i * PROFILE_SAMPLE_INTERVAL, round(float(elev), 2)])

print(f"Wrote profile.csv ({num_samples} samples)")
print("=== Golden solution complete ===")
PYTHON_SCRIPT

echo "Done. Outputs in /task/outputs/"
ls -la /task/outputs/
