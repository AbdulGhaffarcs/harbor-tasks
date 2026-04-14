#!/usr/bin/env python3
"""
Synthetic Topographic Contour Map Generator
============================================
Generates a seed-locked topographic contour map image + all ground truth files.

Pinned dependencies: numpy, scipy, matplotlib (versions in Dockerfile)
Font: DejaVu Sans (bundled with matplotlib, deterministic)
Seed: 42 (fixed for reproducibility)

Outputs:
  - contour_map.png        (1400x1100 rendered map image)
  - metadata.csv           (A/B pixel coords, scale, seed info)
  - dem.npy                (raw DEM array for GT derivation)
  - gt_overlay.svg         (golden SVG overlay)
  - gt_watersheds.png      (golden watershed mask)
  - gt_profile.csv         (golden profile transect)
  - ground_truth.json      (scoring reference)
"""

import numpy as np
from scipy.ndimage import gaussian_filter, label, minimum_filter
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
import json
import csv
import os
import sys

# ============================================================
# CONFIGURATION
# ============================================================
SEED = 42
IMG_W, IMG_H = 1400, 1100
DEM_W, DEM_H = 700, 550          # DEM resolution (2x downsample from image)
NUM_PEAKS = 4
NUM_SADDLES = 2
CONTOUR_INTERVAL = 50             # meters between contour lines
MIN_ELEVATION = 0
MAX_ELEVATION = 800
SCALE_BAR_M = 500                 # scale bar in meters
PIXEL_PER_M = 1.0                 # 1 pixel in DEM = 1 meter
PROFILE_SAMPLE_INTERVAL = 1       # 1m intervals

# Font config — DejaVu Sans is bundled with matplotlib
FONT_NAME = 'DejaVu Sans'
FONT_SIZE_LABEL = 9
FONT_SIZE_TITLE = 14
FONT_SIZE_AXIS = 8

np.random.seed(SEED)

# ============================================================
# STEP 1: Generate DEM (Digital Elevation Model)
# ============================================================
def generate_dem():
    """Create synthetic terrain using sum of Gaussians + smooth noise."""
    dem = np.zeros((DEM_H, DEM_W), dtype=np.float64)
    
    # Place peaks (Gaussian bumps) — spread them across quadrants
    peak_params = []
    # Force peaks into separate quadrants for clear separation
    quadrants = [
        (0.15, 0.45, 0.15, 0.45),  # top-left
        (0.55, 0.85, 0.15, 0.45),  # top-right
        (0.15, 0.45, 0.55, 0.85),  # bottom-left
        (0.55, 0.85, 0.55, 0.85),  # bottom-right
    ]
    for i in range(NUM_PEAKS):
        qx_lo, qx_hi, qy_lo, qy_hi = quadrants[i % len(quadrants)]
        cx = np.random.randint(int(DEM_W * qx_lo), int(DEM_W * qx_hi))
        cy = np.random.randint(int(DEM_H * qy_lo), int(DEM_H * qy_hi))
        height = np.random.uniform(400, 700)
        sigma_x = np.random.uniform(40, 80)
        sigma_y = np.random.uniform(40, 80)
        
        yy, xx = np.mgrid[0:DEM_H, 0:DEM_W]
        gaussian = height * np.exp(-(
            ((xx - cx) ** 2) / (2 * sigma_x ** 2) +
            ((yy - cy) ** 2) / (2 * sigma_y ** 2)
        ))
        dem += gaussian
        peak_params.append({
            'cx': int(cx), 'cy': int(cy),
            'height': float(height),
            'sigma_x': float(sigma_x), 'sigma_y': float(sigma_y)
        })
    
    # Add saddle connections (ridges between some peaks)
    for i in range(min(NUM_SADDLES, NUM_PEAKS - 1)):
        p1 = peak_params[i]
        p2 = peak_params[i + 1]
        ridge_height = min(p1['height'], p2['height']) * 0.3
        # Create ridge by placing gaussians along the line
        num_ridge_pts = 8
        for t in np.linspace(0, 1, num_ridge_pts):
            rx = p1['cx'] + t * (p2['cx'] - p1['cx'])
            ry = p1['cy'] + t * (p2['cy'] - p1['cy'])
            sigma_r = 30
            yy, xx = np.mgrid[0:DEM_H, 0:DEM_W]
            ridge_g = ridge_height * np.exp(-(
                ((xx - rx) ** 2 + (yy - ry) ** 2) / (2 * sigma_r ** 2)
            ))
            dem += ridge_g
    
    # Add smooth background noise for texture
    noise = np.random.randn(DEM_H, DEM_W) * 30
    noise = gaussian_filter(noise, sigma=25)
    dem += noise
    
    # Clamp to valid range
    dem = np.clip(dem, MIN_ELEVATION, None)
    
    # Smooth the whole thing for natural-looking contours
    dem = gaussian_filter(dem, sigma=3)
    
    return dem, peak_params


# ============================================================
# STEP 2: Extract contour data from DEM
# ============================================================
def extract_contours(dem):
    """Extract contour levels and find actual peak positions on DEM."""
    max_elev = np.max(dem)
    levels = np.arange(CONTOUR_INTERVAL, max_elev, CONTOUR_INTERVAL)
    return levels


def find_peaks(dem):
    """Find local maxima in DEM."""
    from scipy.ndimage import maximum_filter
    local_max = maximum_filter(dem, size=40)
    peaks_mask = (dem == local_max) & (dem > 200)
    
    # Label connected regions
    labeled, num_features = label(peaks_mask)
    peaks = []
    for i in range(1, num_features + 1):
        region = np.where(labeled == i)
        # Take the highest point in each region
        idx = np.argmax(dem[region])
        py, px = region[0][idx], region[1][idx]
        peaks.append({
            'dem_x': int(px),
            'dem_y': int(py),
            'elevation': float(np.round(dem[py, px], 1))
        })
    
    # Sort by elevation descending, keep top NUM_PEAKS+1
    peaks.sort(key=lambda p: p['elevation'], reverse=True)
    return peaks[:NUM_PEAKS + 1]


# ============================================================
# STEP 3: Compute watersheds from DEM
# ============================================================
def compute_watersheds(dem):
    """
    Compute drainage basins by assigning each pixel to the basin
    of the local minimum it flows to (steepest descent).
    """
    h, w = dem.shape
    
    # Find local minima (basin sinks)
    local_min = minimum_filter(dem, size=50)
    minima_mask = (dem == local_min) & (dem < np.percentile(dem, 30))
    labeled_minima, num_basins = label(minima_mask)
    
    # If too few or too many basins, adjust
    if num_basins < 3:
        local_min = minimum_filter(dem, size=30)
        minima_mask = (dem == local_min) & (dem < np.percentile(dem, 40))
        labeled_minima, num_basins = label(minima_mask)
    
    if num_basins > 8:
        # Merge small basins — keep only largest
        sizes = []
        for i in range(1, num_basins + 1):
            sizes.append((i, np.sum(labeled_minima == i)))
        sizes.sort(key=lambda x: x[1], reverse=True)
        keep = set([s[0] for s in sizes[:6]])
        for i in range(1, num_basins + 1):
            if i not in keep:
                labeled_minima[labeled_minima == i] = 0
        # Relabel
        labeled_minima_new = np.zeros_like(labeled_minima)
        new_id = 1
        for old_id in sorted(keep):
            labeled_minima_new[labeled_minima == old_id] = new_id
            new_id += 1
        labeled_minima = labeled_minima_new
        num_basins = len(keep)
    
    # Steepest descent flow assignment
    watershed = np.zeros((h, w), dtype=np.int32)
    
    # Assign minima pixels their basin ID
    watershed[labeled_minima > 0] = labeled_minima[labeled_minima > 0]
    
    # Sort all pixels by elevation (low to high) and propagate basin IDs
    flat_indices = np.argsort(dem.ravel())
    
    dy = [-1, -1, -1, 0, 0, 1, 1, 1]
    dx = [-1, 0, 1, -1, 1, -1, 0, 1]
    
    for idx in flat_indices:
        y, x = divmod(idx, w)
        if watershed[y, x] > 0:
            continue
        
        # Find lowest neighbor that has a basin assignment
        best_basin = 0
        best_elev = 1e9
        for d in range(8):
            ny, nx = y + dy[d], x + dx[d]
            if 0 <= ny < h and 0 <= nx < w:
                if watershed[ny, nx] > 0 and dem[ny, nx] < best_elev:
                    best_elev = dem[ny, nx]
                    best_basin = watershed[ny, nx]
        
        if best_basin > 0:
            watershed[y, x] = best_basin
    
    # Fill remaining unassigned pixels with nearest basin
    from scipy.ndimage import distance_transform_edt
    unassigned = watershed == 0
    if np.any(unassigned):
        # Use distance transform to find nearest assigned pixel
        _, nearest_indices = distance_transform_edt(unassigned, return_distances=True, return_indices=True)
        watershed[unassigned] = watershed[nearest_indices[0][unassigned], nearest_indices[1][unassigned]]
    
    return watershed, num_basins


# ============================================================
# STEP 4: Render contour map image
# ============================================================
def render_map(dem, levels, peaks, point_a, point_b, output_path):
    """Render the topographic contour map with all annotations."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 11), dpi=100)
    
    # Use a terrain colormap for background
    terrain_cmap = LinearSegmentedColormap.from_list('terrain_custom', [
        (0.0, '#d4e6c3'),    # low: green
        (0.3, '#f5e6ab'),    # mid-low: yellow
        (0.6, '#e8c07a'),    # mid: tan
        (0.8, '#c49a6c'),    # mid-high: brown
        (1.0, '#8b6f47'),    # high: dark brown
    ])
    
    # Background elevation shading
    ax.imshow(dem, cmap=terrain_cmap, origin='upper', aspect='equal', alpha=0.4)
    
    # Draw contour lines
    cs = ax.contour(dem, levels=levels, colors='#4a3728', linewidths=0.8, alpha=0.9)
    
    # Label contours with high-contrast backgrounds
    clabels = ax.clabel(cs, inline=True, fontsize=FONT_SIZE_LABEL,
                         fmt='%d m', colors='#2a1a0a',
                         inline_spacing=8)
    
    # Add white background to labels for legibility
    if clabels:
        for lbl in clabels:
            lbl.set_bbox(dict(
                boxstyle='round,pad=0.15',
                facecolor='white',
                edgecolor='none',
                alpha=0.85
            ))
    
    # Mark peaks
    for i, pk in enumerate(peaks):
        ax.plot(pk['dem_x'], pk['dem_y'], '^', color='red',
                markersize=12, markeredgecolor='darkred', markeredgewidth=1.5)
        ax.annotate(f"PK{i+1}\n{pk['elevation']:.0f}m",
                    (pk['dem_x'], pk['dem_y']),
                    textcoords="offset points", xytext=(10, 10),
                    fontsize=FONT_SIZE_LABEL, fontweight='bold', color='darkred',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              edgecolor='darkred', alpha=0.9))
    
    # Mark points A and B
    for label_text, point, color in [('A', point_a, '#0066cc'), ('B', point_b, '#cc0066')]:
        ax.plot(point[0], point[1], 'o', color=color,
                markersize=14, markeredgecolor='white', markeredgewidth=2)
        ax.annotate(label_text,
                    (point[0], point[1]),
                    textcoords="offset points", xytext=(12, 12),
                    fontsize=13, fontweight='bold', color=color,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor=color, alpha=0.95))
    
    # Draw transect line A-B (dashed)
    ax.plot([point_a[0], point_b[0]], [point_a[1], point_b[1]],
            '--', color='#666666', linewidth=1.5, alpha=0.7)
    
    # Coordinate grid
    ax.set_xticks(np.arange(0, DEM_W, 100))
    ax.set_yticks(np.arange(0, DEM_H, 100))
    ax.grid(True, alpha=0.3, linestyle=':', color='gray')
    ax.tick_params(labelsize=FONT_SIZE_AXIS)
    
    # Scale bar
    bar_x = DEM_W - 180
    bar_y = DEM_H - 40
    bar_len = int(SCALE_BAR_M * PIXEL_PER_M)
    ax.plot([bar_x, bar_x + bar_len], [bar_y, bar_y], 'k-', linewidth=3)
    ax.plot([bar_x, bar_x], [bar_y - 5, bar_y + 5], 'k-', linewidth=2)
    ax.plot([bar_x + bar_len, bar_x + bar_len], [bar_y - 5, bar_y + 5], 'k-', linewidth=2)
    ax.text(bar_x + bar_len / 2, bar_y - 12, f'{SCALE_BAR_M}m',
            ha='center', fontsize=10, fontweight='bold',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))
    
    # Title
    ax.set_title('SYNTHETIC TOPOGRAPHIC SURVEY — SECTOR 42',
                 fontsize=FONT_SIZE_TITLE, fontweight='bold', pad=15)
    ax.set_xlabel('X (meters)', fontsize=10)
    ax.set_ylabel('Y (meters)', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"  Saved: {output_path}")


# ============================================================
# STEP 5: Generate golden SVG overlay
# ============================================================
def generate_golden_svg(dem, levels, peaks, watershed, num_basins, output_path):
    """Generate the golden SVG overlay with contour paths, peaks, and nesting."""
    
    # Use matplotlib to extract contour paths
    fig, ax = plt.subplots(1, 1, figsize=(DEM_W / 100, DEM_H / 100), dpi=100)
    ax.set_xlim(0, DEM_W)
    ax.set_ylim(DEM_H, 0)
    cs = ax.contour(dem, levels=levels)
    plt.close()
    
    # Scale factor: DEM coords -> image coords (2x)
    scale = IMG_W / DEM_W
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                     f'width="{IMG_W}" height="{IMG_H}" '
                     f'viewBox="0 0 {IMG_W} {IMG_H}">')
    
    # --- Contour layer ---
    svg_lines.append('  <g id="contours">')
    contour_data = []  # for nesting computation
    
    # Use allsegs (works on all matplotlib versions)
    for i, level_val in enumerate(cs.levels):
        segments = cs.allsegs[i]
        for j, seg in enumerate(segments):
            vertices = seg * scale
            if len(vertices) < 3:
                continue
            
            # Build SVG path string
            d_parts = [f'M {vertices[0][0]:.1f} {vertices[0][1]:.1f}']
            for v in vertices[1:]:
                d_parts.append(f'L {v[0]:.1f} {v[1]:.1f}')
            d_parts.append('Z')
            d_str = ' '.join(d_parts)
            
            cid = f'contour_{i}_{j}'
            svg_lines.append(
                f'    <g id="{cid}" data-elevation="{level_val:.0f}">'
                f'      <path d="{d_str}" fill="none" stroke="#4a3728" '
                f'stroke-width="1.5" />'
                f'    </g>'
            )
            
            # Store for nesting
            contour_data.append({
                'id': cid,
                'elevation': float(level_val),
                'vertices': vertices.tolist(),
                'centroid': [float(np.mean(vertices[:, 0])),
                             float(np.mean(vertices[:, 1]))]
            })
    
    svg_lines.append('  </g>')
    
    # --- Peaks layer ---
    svg_lines.append('  <g id="peaks">')
    for i, pk in enumerate(peaks):
        px = pk['dem_x'] * scale
        py = pk['dem_y'] * scale
        svg_lines.append(
            f'    <circle id="peak_{i+1}" cx="{px:.1f}" cy="{py:.1f}" r="8" '
            f'fill="red" stroke="darkred" stroke-width="2" '
            f'data-elevation="{pk["elevation"]:.1f}" />'
        )
    svg_lines.append('  </g>')
    
    # --- Nesting layer ---
    # Build nesting: for each contour, its parent is the next-lower elevation
    # contour that contains its centroid
    svg_lines.append('  <g id="nesting">')
    
    nesting_edges = []
    from matplotlib.path import Path as MplPath
    
    # Sort contours by elevation
    contour_data.sort(key=lambda c: c['elevation'])
    
    for i, child in enumerate(contour_data):
        child_centroid = child['centroid']
        best_parent = None
        best_elev = -1
        
        for j, parent in enumerate(contour_data):
            if parent['elevation'] >= child['elevation']:
                continue
            if len(parent['vertices']) < 3:
                continue
            
            # Check if child centroid is inside parent contour
            try:
                mpl_path = MplPath(parent['vertices'])
                if mpl_path.contains_point(child_centroid):
                    if parent['elevation'] > best_elev:
                        best_elev = parent['elevation']
                        best_parent = parent
            except:
                continue
        
        if best_parent:
            nesting_edges.append({
                'child_id': child['id'],
                'parent_id': best_parent['id'],
                'child_centroid': child['centroid'],
                'parent_centroid': best_parent['centroid']
            })
            svg_lines.append(
                f'    <line x1="{child["centroid"][0]:.1f}" '
                f'y1="{child["centroid"][1]:.1f}" '
                f'x2="{best_parent["centroid"][0]:.1f}" '
                f'y2="{best_parent["centroid"][1]:.1f}" '
                f'stroke="blue" stroke-width="1" stroke-dasharray="4,4" '
                f'data-child="{child["id"]}" data-parent="{best_parent["id"]}" />'
            )
    
    svg_lines.append('  </g>')
    svg_lines.append('</svg>')
    
    svg_content = '\n'.join(svg_lines)
    with open(output_path, 'w') as f:
        f.write(svg_content)
    print(f"  Saved: {output_path}")
    
    return contour_data, nesting_edges


# ============================================================
# STEP 6: Generate golden watershed PNG
# ============================================================
def generate_golden_watershed_png(watershed, output_path):
    """Render watershed basins as color-coded PNG."""
    num_basins = int(np.max(watershed))
    
    # Distinct colors for each basin
    basin_colors = [
        [31, 119, 180],    # blue
        [255, 127, 14],    # orange
        [44, 160, 44],     # green
        [214, 39, 40],     # red
        [148, 103, 189],   # purple
        [140, 86, 75],     # brown
        [227, 119, 194],   # pink
        [127, 127, 127],   # gray
    ]
    
    h, w = watershed.shape
    img = np.zeros((h, w, 3), dtype=np.uint8)
    
    for basin_id in range(1, num_basins + 1):
        color = basin_colors[(basin_id - 1) % len(basin_colors)]
        mask = watershed == basin_id
        img[mask] = color
    
    # Scale up to image resolution
    from PIL import Image
    pil_img = Image.fromarray(img)
    pil_img = pil_img.resize((IMG_W, IMG_H), Image.NEAREST)
    pil_img.save(output_path)
    print(f"  Saved: {output_path}")
    
    return num_basins


# ============================================================
# STEP 7: Generate golden profile CSV
# ============================================================
def generate_golden_profile(dem, point_a, point_b, output_path):
    """Sample elevation along A→B transect at 1m intervals."""
    ax, ay = point_a
    bx, by = point_b
    
    distance = np.sqrt((bx - ax) ** 2 + (by - ay) ** 2)
    num_samples = int(distance / PROFILE_SAMPLE_INTERVAL) + 1
    
    rows = []
    for i in range(num_samples):
        t = i / max(num_samples - 1, 1)
        x = ax + t * (bx - ax)
        y = ay + t * (by - ay)
        
        # Bilinear interpolation
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        x1, y1 = min(x0 + 1, DEM_W - 1), min(y0 + 1, DEM_H - 1)
        xf, yf = x - x0, y - y0
        
        elev = (dem[y0, x0] * (1 - xf) * (1 - yf) +
                dem[y0, x1] * xf * (1 - yf) +
                dem[y1, x0] * (1 - xf) * yf +
                dem[y1, x1] * xf * yf)
        
        dist_m = i * PROFILE_SAMPLE_INTERVAL
        rows.append([dist_m, round(float(elev), 2)])
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['distance_m', 'elevation_m'])
        writer.writerows(rows)
    
    print(f"  Saved: {output_path} ({len(rows)} samples)")
    return rows


# ============================================================
# STEP 8: Generate metadata.csv
# ============================================================
def generate_metadata(point_a, point_b, peaks, num_basins, output_path):
    """Write metadata CSV with A/B coordinates and scale info."""
    # Convert DEM coords to image pixel coords
    scale = IMG_W / DEM_W
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['key', 'value'])
        writer.writerow(['seed', SEED])
        writer.writerow(['image_width_px', IMG_W])
        writer.writerow(['image_height_px', IMG_H])
        writer.writerow(['dem_width', DEM_W])
        writer.writerow(['dem_height', DEM_H])
        writer.writerow(['scale_pixel_per_meter', PIXEL_PER_M])
        writer.writerow(['contour_interval_m', CONTOUR_INTERVAL])
        writer.writerow(['point_a_dem_x', point_a[0]])
        writer.writerow(['point_a_dem_y', point_a[1]])
        writer.writerow(['point_a_img_x', int(point_a[0] * scale)])
        writer.writerow(['point_a_img_y', int(point_a[1] * scale)])
        writer.writerow(['point_b_dem_x', point_b[0]])
        writer.writerow(['point_b_dem_y', point_b[1]])
        writer.writerow(['point_b_img_x', int(point_b[0] * scale)])
        writer.writerow(['point_b_img_y', int(point_b[1] * scale)])
        writer.writerow(['num_peaks', len(peaks)])
        writer.writerow(['num_basins', num_basins])
        writer.writerow(['profile_sample_interval_m', PROFILE_SAMPLE_INTERVAL])
    
    print(f"  Saved: {output_path}")


# ============================================================
# STEP 9: Generate ground_truth.json
# ============================================================
def generate_ground_truth(peaks, contour_data, nesting_edges, watershed,
                          num_basins, profile_rows, output_path):
    """Compile all ground truth into a single JSON for scoring."""
    scale = IMG_W / DEM_W
    
    gt = {
        'peaks': [{
            'id': f'peak_{i+1}',
            'img_x': round(pk['dem_x'] * scale, 1),
            'img_y': round(pk['dem_y'] * scale, 1),
            'elevation': pk['elevation']
        } for i, pk in enumerate(peaks)],
        'contours': [{
            'id': c['id'],
            'elevation': c['elevation']
        } for c in contour_data],
        'nesting_edges': [{
            'child': e['child_id'],
            'parent': e['parent_id']
        } for e in nesting_edges],
        'num_basins': num_basins,
        'basin_pixel_counts': {},
        'profile_length': len(profile_rows)
    }
    
    # Basin pixel counts (for watershed validation)
    for basin_id in range(1, num_basins + 1):
        count = int(np.sum(watershed == basin_id))
        gt['basin_pixel_counts'][str(basin_id)] = count
    
    with open(output_path, 'w') as f:
        json.dump(gt, f, indent=2)
    print(f"  Saved: {output_path}")
    
    return gt


# ============================================================
# MAIN
# ============================================================
def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out_dir, exist_ok=True)
    
    print("=" * 60)
    print("GENERATING SYNTHETIC TOPOGRAPHIC MAP (seed=42)")
    print("=" * 60)
    
    # 1. Generate DEM
    print("\n[1/8] Generating DEM...")
    dem, peak_params = generate_dem()
    np.save(os.path.join(out_dir, 'dem.npy'), dem)
    print(f"  DEM shape: {dem.shape}, range: [{dem.min():.1f}, {dem.max():.1f}]")
    
    # 2. Extract features
    print("\n[2/8] Extracting contours and peaks...")
    levels = extract_contours(dem)
    peaks = find_peaks(dem)
    print(f"  Contour levels: {len(levels)} (interval={CONTOUR_INTERVAL}m)")
    print(f"  Peaks found: {len(peaks)}")
    for pk in peaks:
        print(f"    Peak at ({pk['dem_x']}, {pk['dem_y']}) = {pk['elevation']:.1f}m")
    
    # 3. Define transect points A and B
    print("\n[3/8] Setting transect points A, B...")
    # Place A and B to cross interesting terrain
    point_a = (80, 100)      # top-left area
    point_b = (620, 450)     # bottom-right area
    print(f"  A=({point_a[0]}, {point_a[1]}), B=({point_b[0]}, {point_b[1]})")
    
    # 4. Compute watersheds
    print("\n[4/8] Computing watersheds...")
    watershed, num_basins = compute_watersheds(dem)
    print(f"  Basins: {num_basins}")
    for i in range(1, num_basins + 1):
        count = np.sum(watershed == i)
        pct = 100.0 * count / watershed.size
        print(f"    Basin {i}: {count} px ({pct:.1f}%)")
    
    # 5. Render map image
    print("\n[5/8] Rendering contour map image...")
    render_map(dem, levels, peaks, point_a, point_b,
               os.path.join(out_dir, 'contour_map.png'))
    
    # 6. Generate golden SVG
    print("\n[6/8] Generating golden SVG overlay...")
    contour_data, nesting_edges = generate_golden_svg(
        dem, levels, peaks, watershed, num_basins,
        os.path.join(out_dir, 'gt_overlay.svg'))
    
    # 7. Generate golden watershed
    print("\n[7/8] Generating golden watershed PNG...")
    generate_golden_watershed_png(watershed,
                                  os.path.join(out_dir, 'gt_watersheds.png'))
    
    # 8. Generate golden profile
    print("\n[8/8] Generating golden profile CSV...")
    profile_rows = generate_golden_profile(dem, point_a, point_b,
                                            os.path.join(out_dir, 'gt_profile.csv'))
    
    # Metadata
    print("\n[+] Generating metadata.csv...")
    generate_metadata(point_a, point_b, peaks, num_basins,
                      os.path.join(out_dir, 'metadata.csv'))
    
    # Ground truth
    print("\n[+] Generating ground_truth.json...")
    gt = generate_ground_truth(peaks, contour_data, nesting_edges,
                               watershed, num_basins, profile_rows,
                               os.path.join(out_dir, 'ground_truth.json'))
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print(f"  Files in: {out_dir}")
    print(f"  Peaks: {len(peaks)}")
    print(f"  Contour levels: {len(levels)}")
    print(f"  Basins: {num_basins}")
    print(f"  Profile samples: {len(profile_rows)}")
    print(f"  Nesting edges: {len(nesting_edges)}")
    print("=" * 60)


if __name__ == '__main__':
    main()
