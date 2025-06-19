#!/usr/bin/env python3
"""
Check current ADDRFEAT download status across all states
"""

import os
import glob

# Configuration
STATES = {
    'arkansas': {'fips': '05', 'counties': 75},
    'tennessee': {'fips': '47', 'counties': 95}, 
    'mississippi': {'fips': '28', 'counties': 82},
    'louisiana': {'fips': '22', 'counties': 64},
    'texas': {'fips': '48', 'counties': 254},
    'oklahoma': {'fips': '40', 'counties': 77},
    'missouri': {'fips': '29', 'counties': 115}
}

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
base_path = os.path.join(project_root, "data", "reference", "addrfeat")

def check_status():
    print("ADDRFEAT DOWNLOAD STATUS REPORT")
    print("=" * 80)
    
    total_target = sum(state['counties'] for state in STATES.values())
    total_downloaded = 0
    
    for state_name, state_info in STATES.items():
        state_path = os.path.join(base_path, state_name)
        
        if os.path.exists(state_path):
            zip_files = len(glob.glob(os.path.join(state_path, "*.zip")))
            shp_files = len(glob.glob(os.path.join(state_path, "*.shp")))
            target_counties = state_info['counties']
            
            completion_pct = (zip_files / target_counties) * 100
            total_downloaded += zip_files
            
            print(f"{state_name.capitalize():12} | {zip_files:3d}/{target_counties:3d} ZIP files | {shp_files:3d} SHP files | {completion_pct:5.1f}% complete")
        else:
            print(f"{state_name.capitalize():12} | No data directory")
    
    overall_pct = (total_downloaded / total_target) * 100
    remaining = total_target - total_downloaded
    
    print("=" * 80)
    print(f"OVERALL PROGRESS: {total_downloaded}/{total_target} counties ({overall_pct:.1f}% complete)")
    print(f"REMAINING TO DOWNLOAD: {remaining} counties")
    print("=" * 80)
    
    if remaining > 0:
        print(f"Ready to run smart_batch_downloader.py to complete remaining {remaining} counties")
    else:
        print("🎉 ALL COUNTIES DOWNLOADED! Ready for comprehensive ADDRFEAT geocoding.")

if __name__ == "__main__":
    check_status()