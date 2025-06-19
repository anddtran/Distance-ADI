#!/usr/bin/env python3
"""
Quick test to check ADDRFEAT coverage with current downloaded files
"""

import pandas as pd
import geopandas as gpd
import os
import glob

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
ADDRFEAT_BASE_PATH = os.path.join(project_root, "data", "reference", "addrfeat")

print("ADDRFEAT Coverage Test")
print("=" * 50)

# Count files by state
states = ['arkansas', 'tennessee', 'mississippi', 'louisiana', 'texas', 'oklahoma', 'missouri']

total_shp_files = 0
for state in states:
    state_path = os.path.join(ADDRFEAT_BASE_PATH, state)
    if os.path.exists(state_path):
        shp_files = glob.glob(os.path.join(state_path, "*.shp"))
        print(f"{state.capitalize()}: {len(shp_files)} shapefile(s)")
        total_shp_files += len(shp_files)
    else:
        print(f"{state.capitalize()}: No data directory")

print(f"\nTotal ADDRFEAT files available: {total_shp_files}")

# Test loading a few files
print("\nTesting file loading...")
test_count = 0
for state in states:
    state_path = os.path.join(ADDRFEAT_BASE_PATH, state)
    if os.path.exists(state_path):
        shp_files = glob.glob(os.path.join(state_path, "*.shp"))
        if shp_files and test_count < 3:  # Test first 3 files
            try:
                test_file = shp_files[0]
                gdf = gpd.read_file(test_file)
                print(f"✅ Successfully loaded {os.path.basename(test_file)}: {len(gdf)} address records")
                test_count += 1
            except Exception as e:
                print(f"❌ Error loading {os.path.basename(test_file)}: {e}")

print(f"\nCoverage test complete. With {total_shp_files} ADDRFEAT files, blank cells should be significantly reduced.")