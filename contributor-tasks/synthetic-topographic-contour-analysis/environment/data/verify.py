#!/usr/bin/env python3
"""
verify.py — Schema and format checker for agent outputs.
CRITICAL: This file must NEVER leak ground truth data.
It checks structure/format only so the agent can self-check.
"""

import sys
import os
import csv
import json

def check_overlay_svg(path):
    """Check SVG overlay structure — no GT validation."""
    if not os.path.exists(path):
        print(f"FAIL: {path} not found")
        return False
    
    with open(path, 'r') as f:
        content = f.read()
    
    errors = []
    
    # Must be valid SVG
    if '<svg' not in content:
        errors.append("Missing <svg> root element")
    if '</svg>' not in content:
        errors.append("Missing </svg> closing tag")
    
    # Must have required layers
    if 'id="contours"' not in content:
        errors.append('Missing <g id="contours"> layer')
    if 'id="peaks"' not in content:
        errors.append('Missing <g id="peaks"> layer')
    if 'id="nesting"' not in content:
        errors.append('Missing <g id="nesting"> layer')
    
    # Must have data-elevation attributes
    if 'data-elevation' not in content:
        errors.append('No data-elevation attributes found')
    
    # Must have contour paths
    if '<path' not in content:
        errors.append('No <path> elements found in contours')
    
    # Must have peak circles
    if '<circle' not in content:
        errors.append('No <circle> elements found in peaks')
    
    # Nesting must have lines
    if 'data-child' not in content and 'data-parent' not in content:
        errors.append('No nesting <line> elements with data-child/data-parent found')
    
    if errors:
        for e in errors:
            print(f"FAIL: overlay.svg — {e}")
        return False
    
    print(f"OK: overlay.svg — valid structure (contours + peaks + nesting layers)")
    return True


def check_watersheds_png(path):
    """Check watershed PNG format — no GT validation."""
    if not os.path.exists(path):
        print(f"FAIL: {path} not found")
        return False
    
    try:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        
        if img.mode not in ('RGB', 'RGBA', 'P'):
            print(f"FAIL: watersheds.png — unexpected mode {img.mode}, need RGB/RGBA/P")
            return False
        
        if w < 100 or h < 100:
            print(f"FAIL: watersheds.png — too small ({w}x{h}), expected at least 100x100")
            return False
        
        # Check that there are multiple distinct colors (= multiple basins)
        import numpy as np
        arr = np.array(img.convert('RGB'))
        unique_colors = len(np.unique(arr.reshape(-1, 3), axis=0))
        
        if unique_colors < 2:
            print(f"FAIL: watersheds.png — only {unique_colors} color(s), need multiple basins")
            return False
        
        print(f"OK: watersheds.png — {w}x{h}, {unique_colors} distinct colors")
        return True
    except Exception as e:
        print(f"FAIL: watersheds.png — {e}")
        return False


def check_profile_csv(path):
    """Check profile CSV format — no GT validation."""
    if not os.path.exists(path):
        print(f"FAIL: {path} not found")
        return False
    
    try:
        with open(path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
        
        # Check header
        expected_cols = ['distance_m', 'elevation_m']
        if header != expected_cols:
            print(f"FAIL: profile.csv — header must be {expected_cols}, got {header}")
            return False
        
        # Check data rows
        rows = 0
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    d = float(row['distance_m'])
                    e = float(row['elevation_m'])
                except (ValueError, KeyError) as err:
                    print(f"FAIL: profile.csv row {rows+1} — {err}")
                    return False
                rows += 1
        
        if rows < 10:
            print(f"FAIL: profile.csv — only {rows} data rows, need at least 10")
            return False
        
        print(f"OK: profile.csv — {rows} data rows, columns: {expected_cols}")
        return True
    except Exception as e:
        print(f"FAIL: profile.csv — {e}")
        return False


def main():
    """Run all schema checks."""
    output_dir = sys.argv[1] if len(sys.argv) > 1 else '/task/outputs'
    
    print("=" * 50)
    print("SCHEMA VERIFICATION (format check only)")
    print("=" * 50)
    
    results = {
        'overlay_svg': check_overlay_svg(os.path.join(output_dir, 'overlay.svg')),
        'watersheds_png': check_watersheds_png(os.path.join(output_dir, 'watersheds.png')),
        'profile_csv': check_profile_csv(os.path.join(output_dir, 'profile.csv')),
    }
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n{'='*50}")
    print(f"RESULT: {passed}/{total} files passed schema check")
    print("=" * 50)
    
    if passed == total:
        print("All outputs have valid format. Ready for scoring.")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"Fix these files: {', '.join(failed)}")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
