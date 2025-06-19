#!/usr/bin/env python3
"""
Complete Multi-State ADDRFEAT Downloader

Downloads all ADDRFEAT files for Arkansas + 6 surrounding states
for comprehensive address-to-FIPS geocoding coverage.

Total Coverage: 762 counties across 7 states
"""

import os
import requests
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# State FIPS codes and county counts
STATES = {
    'arkansas': {'fips': '05', 'counties': 75},
    'tennessee': {'fips': '47', 'counties': 95}, 
    'mississippi': {'fips': '28', 'counties': 82},
    'louisiana': {'fips': '22', 'counties': 64},
    'texas': {'fips': '48', 'counties': 254},
    'oklahoma': {'fips': '40', 'counties': 77},
    'missouri': {'fips': '29', 'counties': 115}
}

# Base paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
base_path = os.path.join(project_root, "data", "reference", "addrfeat")

def get_county_fips_codes(state_fips):
    """Get all county FIPS codes for a state (001 to max counties)"""
    max_counties = STATES[next(k for k, v in STATES.items() if v['fips'] == state_fips)]['counties']
    return [f"{i:03d}" for i in range(1, max_counties + 1)]

def download_county_addrfeat(state_name, state_fips, county_fips, max_retries=3):
    """Download a single county ADDRFEAT file with retry logic"""
    url = f"https://www2.census.gov/geo/tiger/TIGER2023/ADDRFEAT/tl_2023_{state_fips}{county_fips}_addrfeat.zip"
    filename = f"tl_2023_{state_fips}{county_fips}_addrfeat.zip"
    state_dir = os.path.join(base_path, state_name)
    filepath = os.path.join(state_dir, filename)
    
    # Skip if already exists
    if os.path.exists(filepath):
        return f"SKIP: {state_name} county {county_fips} (already exists)"
    
    for attempt in range(max_retries):
        try:
            # Add delay to respect rate limits
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff: 2, 4, 8 seconds
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                os.makedirs(state_dir, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Extract immediately
                try:
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(state_dir)
                    return f"SUCCESS: {state_name} county {county_fips} ({len(response.content)//1024}KB)"
                except zipfile.BadZipFile:
                    os.remove(filepath)  # Remove bad file
                    return f"ERROR: {state_name} county {county_fips} (bad zip file)"
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(10)  # Wait longer for rate limiting
                    continue
                else:
                    return f"ERROR: {state_name} county {county_fips} (HTTP 429 - rate limited)"
            elif response.status_code == 404:
                return f"SKIP: {state_name} county {county_fips} (county does not exist)"
            else:
                return f"ERROR: {state_name} county {county_fips} (HTTP {response.status_code})"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                return f"ERROR: {state_name} county {county_fips} ({str(e)})"
    
    return f"ERROR: {state_name} county {county_fips} (max retries exceeded)"

def download_state_counties(state_name, max_workers=5):
    """Download all counties for a state with reduced concurrency"""
    state_info = STATES[state_name]
    state_fips = state_info['fips']
    county_codes = get_county_fips_codes(state_fips)
    
    print(f"\n{'='*80}")
    print(f"DOWNLOADING {state_name.upper()} COUNTIES")
    print(f"State FIPS: {state_fips}, Counties: {len(county_codes)}")
    print(f"{'='*80}")
    
    successful = 0
    skipped = 0
    errors = 0
    
    # Reduce concurrency to be more respectful to Census servers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_county_addrfeat, state_name, state_fips, county_fips): county_fips 
            for county_fips in county_codes
        }
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
            
            if result.startswith("SUCCESS"):
                successful += 1
            elif result.startswith("SKIP"):
                skipped += 1
            else:
                errors += 1
            
            # Add small delay between requests to avoid overwhelming server
            time.sleep(0.1)
    
    print(f"\n{state_name.upper()} SUMMARY: {successful} downloaded, {skipped} skipped, {errors} errors")
    return successful, skipped, errors

def main():
    print("COMPREHENSIVE MULTI-STATE ADDRFEAT DOWNLOADER")
    print("=" * 80)
    print("Downloading ALL counties for Arkansas + 6 surrounding states")
    print("Total target: 762 counties")
    print("Estimated size: ~1.4GB")
    print("=" * 80)
    
    # Create base directories
    for state_name in STATES.keys():
        os.makedirs(os.path.join(base_path, state_name), exist_ok=True)
    
    total_successful = 0
    total_skipped = 0
    total_errors = 0
    
    start_time = time.time()
    
    # Download each state
    for state_name in STATES.keys():
        successful, skipped, errors = download_state_counties(state_name)
        total_successful += successful
        total_skipped += skipped
        total_errors += errors
        
        # Longer pause between states to respect rate limits
        time.sleep(5)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{'='*80}")
    print(f"DOWNLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"Total files downloaded: {total_successful}")
    print(f"Total files skipped: {total_skipped}")
    print(f"Total errors: {total_errors}")
    print(f"Success rate: {total_successful/(total_successful+total_errors)*100:.1f}%")
    print(f"Total time: {duration/60:.1f} minutes")
    print(f"Coverage: {len(STATES)} states, 762 counties")
    print(f"\nADDRFEAT data ready for comprehensive geocoding!")

if __name__ == "__main__":
    main()