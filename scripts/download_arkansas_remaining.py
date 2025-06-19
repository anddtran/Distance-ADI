#!/usr/bin/env python3
"""
Continue downloading remaining Arkansas counties with improved rate limiting
"""

import os
import requests
import zipfile
import time
import glob

# Arkansas state info
STATE_FIPS = '05'
STATE_NAME = 'arkansas'
TOTAL_COUNTIES = 75

# Base paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
base_path = os.path.join(project_root, "data", "reference", "addrfeat", STATE_NAME)

def get_existing_counties():
    """Get list of county FIPS codes already downloaded"""
    existing_files = glob.glob(os.path.join(base_path, "*.zip"))
    existing_counties = set()
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        # Extract county FIPS from filename like tl_2023_05001_addrfeat.zip
        if filename.startswith(f'tl_2023_{STATE_FIPS}'):
            county_fips = filename[9:12]  # Extract 3-digit county code
            existing_counties.add(county_fips)
    return existing_counties

def download_missing_counties():
    """Download remaining Arkansas counties"""
    existing_counties = get_existing_counties()
    print(f"Found {len(existing_counties)} existing Arkansas counties")
    
    # Generate all possible county FIPS codes
    all_counties = {f"{i:03d}" for i in range(1, TOTAL_COUNTIES + 1)}
    missing_counties = all_counties - existing_counties
    
    print(f"Need to download {len(missing_counties)} remaining counties")
    
    successful = 0
    errors = 0
    
    for county_fips in sorted(missing_counties):
        url = f"https://www2.census.gov/geo/tiger/TIGER2023/ADDRFEAT/tl_2023_{STATE_FIPS}{county_fips}_addrfeat.zip"
        filename = f"tl_2023_{STATE_FIPS}{county_fips}_addrfeat.zip"
        filepath = os.path.join(base_path, filename)
        
        print(f"Downloading county {county_fips}...")
        
        # Try with retries and delays
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(5 * attempt)  # Longer delays between retries
                
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract immediately
                    try:
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(base_path)
                        print(f"  SUCCESS: County {county_fips} ({len(response.content)//1024}KB)")
                        successful += 1
                        break
                    except zipfile.BadZipFile:
                        os.remove(filepath)
                        print(f"  ERROR: County {county_fips} (bad zip file)")
                        errors += 1
                        break
                elif response.status_code == 404:
                    print(f"  SKIP: County {county_fips} (does not exist)")
                    break
                elif response.status_code == 429:
                    print(f"  RATE LIMITED: County {county_fips}, attempt {attempt + 1}")
                    if attempt < 2:
                        time.sleep(15)  # Wait longer for rate limits
                        continue
                    else:
                        print(f"  ERROR: County {county_fips} (rate limited)")
                        errors += 1
                        break
                else:
                    print(f"  ERROR: County {county_fips} (HTTP {response.status_code})")
                    errors += 1
                    break
            except Exception as e:
                print(f"  ERROR: County {county_fips} ({str(e)})")
                if attempt == 2:
                    errors += 1
                    break
        
        # Delay between counties to be respectful
        time.sleep(2)
    
    print(f"\nARKANSAS DOWNLOAD COMPLETE:")
    print(f"Successfully downloaded: {successful}")
    print(f"Errors: {errors}")
    print(f"Total Arkansas counties now: {len(get_existing_counties())}/75")

if __name__ == "__main__":
    os.makedirs(base_path, exist_ok=True)
    download_missing_counties()