#!/usr/bin/env python3
"""
Smart Batch ADDRFEAT Downloader with Adaptive Rate Limiting

This enhanced downloader implements intelligent strategies to complete
the download of all 762 counties while respecting Census Bureau rate limits.

Features:
- Adaptive rate limiting with exponential backoff
- Progress tracking and resume capability
- Batch processing with circuit breaker pattern
- Comprehensive error handling and logging
- State-by-state completion strategy
"""

import os
import requests
import zipfile
import time
import json
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Base paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
base_path = os.path.join(project_root, "data", "reference", "addrfeat")
progress_file = os.path.join(script_dir, "download_progress.json")

class SmartDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Research Download Bot for Academic Use)'
        })
        
        # Rate limiting parameters
        self.base_delay = 2.0
        self.max_delay = 120.0
        self.rate_limit_delay = 30.0
        self.circuit_breaker_threshold = 10
        self.consecutive_failures = 0
        
        # Progress tracking
        self.progress = self.load_progress()
        self.session_stats = {
            'successful': 0,
            'skipped': 0,
            'errors': 0,
            'rate_limited': 0
        }
    
    def load_progress(self):
        """Load previous download progress"""
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                data = json.load(f)
                # Convert lists back to sets
                data['completed_counties'] = set(data.get('completed_counties', []))
                data['failed_counties'] = set(data.get('failed_counties', []))
                return data
        return {'completed_counties': set(), 'failed_counties': set()}
    
    def save_progress(self):
        """Save current download progress"""
        # Convert sets to lists for JSON serialization
        progress_data = {
            'completed_counties': list(self.progress['completed_counties']),
            'failed_counties': list(self.progress['failed_counties']),
            'last_updated': datetime.now().isoformat()
        }
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def get_existing_counties(self, state_name):
        """Get set of already downloaded counties for a state"""
        state_path = os.path.join(base_path, state_name)
        existing = set()
        
        if os.path.exists(state_path):
            for filename in os.listdir(state_path):
                if filename.endswith('.zip') and filename.startswith('tl_2023_'):
                    # Extract county FIPS from filename
                    county_fips = filename[9:12]
                    existing.add(f"{STATES[state_name]['fips']}{county_fips}")
        
        return existing
    
    def download_county_with_backoff(self, state_name, state_fips, county_fips, max_retries=5):
        """Download single county with intelligent backoff"""
        url = f"https://www2.census.gov/geo/tiger/TIGER2023/ADDRFEAT/tl_2023_{state_fips}{county_fips}_addrfeat.zip"
        filename = f"tl_2023_{state_fips}{county_fips}_addrfeat.zip"
        state_dir = os.path.join(base_path, state_name)
        filepath = os.path.join(state_dir, filename)
        county_id = f"{state_fips}{county_fips}"
        
        # Skip if already completed
        if county_id in self.progress.get('completed_counties', set()):
            return f"SKIP: {state_name} county {county_fips} (already completed)"
        
        # Skip if file already exists
        if os.path.exists(filepath):
            self.progress.setdefault('completed_counties', set()).add(county_id)
            return f"SKIP: {state_name} county {county_fips} (file exists)"
        
        # Circuit breaker check
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            time.sleep(self.max_delay)
            self.consecutive_failures = 0
            print(f"  Circuit breaker triggered, pausing...")
        
        for attempt in range(max_retries):
            try:
                # Calculate delay with jitter
                if attempt > 0:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    jitter = random.uniform(0.5, 1.5)
                    time.sleep(delay * jitter)
                
                response = self.session.get(url, timeout=60)
                
                if response.status_code == 200:
                    os.makedirs(state_dir, exist_ok=True)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract immediately
                    try:
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(state_dir)
                        
                        # Mark as completed
                        self.progress.setdefault('completed_counties', set()).add(county_id)
                        self.consecutive_failures = 0
                        self.session_stats['successful'] += 1
                        
                        return f"SUCCESS: {state_name} county {county_fips} ({len(response.content)//1024}KB)"
                    
                    except zipfile.BadZipFile:
                        os.remove(filepath)
                        self.session_stats['errors'] += 1
                        return f"ERROR: {state_name} county {county_fips} (corrupted file)"
                
                elif response.status_code == 404:
                    # County doesn't exist, mark as completed to avoid retrying
                    self.progress.setdefault('completed_counties', set()).add(county_id)
                    self.session_stats['skipped'] += 1
                    return f"SKIP: {state_name} county {county_fips} (does not exist)"
                
                elif response.status_code == 429:
                    self.session_stats['rate_limited'] += 1
                    self.consecutive_failures += 1
                    
                    if attempt < max_retries - 1:
                        # Longer delay for rate limiting
                        delay = self.rate_limit_delay * (2 ** attempt)
                        print(f"  Rate limited, waiting {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.progress.setdefault('failed_counties', set()).add(county_id)
                        return f"ERROR: {state_name} county {county_fips} (rate limited after {max_retries} attempts)"
                
                else:
                    self.consecutive_failures += 1
                    if attempt == max_retries - 1:
                        self.progress.setdefault('failed_counties', set()).add(county_id)
                        self.session_stats['errors'] += 1
                        return f"ERROR: {state_name} county {county_fips} (HTTP {response.status_code})"
            
            except Exception as e:
                self.consecutive_failures += 1
                if attempt == max_retries - 1:
                    self.progress.setdefault('failed_counties', set()).add(county_id)
                    self.session_stats['errors'] += 1
                    return f"ERROR: {state_name} county {county_fips} ({str(e)})"
        
        return f"ERROR: {state_name} county {county_fips} (max retries exceeded)"
    
    def download_state_batch(self, state_name, batch_size=15, max_workers=3):
        """Download counties for a state in batches"""
        state_info = STATES[state_name]
        state_fips = state_info['fips']
        
        # Get counties that need downloading
        all_counties = {f"{i:03d}" for i in range(1, state_info['counties'] + 1)}
        existing_counties = {county_id[-3:] for county_id in self.get_existing_counties(state_name)}
        completed_counties = {county_id[-3:] for county_id in self.progress.get('completed_counties', set()) if county_id.startswith(state_fips)}
        
        pending_counties = all_counties - existing_counties - completed_counties
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING {state_name.upper()} COUNTIES - BATCH MODE")
        print(f"State FIPS: {state_fips}, Total counties: {len(all_counties)}")
        print(f"Existing: {len(existing_counties)}, Completed: {len(completed_counties)}")
        print(f"Remaining to download: {len(pending_counties)}")
        print(f"{'='*80}")
        
        if not pending_counties:
            print(f"All {state_name} counties already downloaded!")
            return
        
        # Process in batches
        county_list = sorted(list(pending_counties))
        for batch_start in range(0, len(county_list), batch_size):
            batch = county_list[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(county_list) + batch_size - 1) // batch_size
            
            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} counties)...")
            
            # Download batch concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.download_county_with_backoff, state_name, state_fips, county_fips): county_fips
                    for county_fips in batch
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    print(f"  {result}")
                    
                    # Save progress after each download
                    self.save_progress()
            
            # Longer delay between batches
            if batch_start + batch_size < len(county_list):
                batch_delay = random.uniform(45, 75)
                print(f"  Batch complete. Waiting {batch_delay:.1f}s before next batch...")
                time.sleep(batch_delay)
        
        print(f"\n{state_name.upper()} BATCH DOWNLOAD COMPLETE")
    
    def download_all_states(self):
        """Download all remaining counties across all states"""
        print("SMART BATCH ADDRFEAT DOWNLOADER")
        print("=" * 80)
        print("Downloading remaining counties with intelligent rate limiting")
        print("Target: Complete coverage of all 762 counties")
        print("=" * 80)
        
        start_time = time.time()
        
        # Prioritize Arkansas (primary research state)
        priority_states = ['arkansas', 'tennessee', 'mississippi', 'louisiana']
        remaining_states = ['texas', 'oklahoma', 'missouri']
        
        all_states = priority_states + remaining_states
        
        for state_name in all_states:
            try:
                self.download_state_batch(state_name)
                
                # Longer delay between states
                if state_name != all_states[-1]:  # Don't delay after last state
                    state_delay = random.uniform(120, 180)
                    print(f"\nState complete. Waiting {state_delay:.1f}s before next state...")
                    time.sleep(state_delay)
                    
            except KeyboardInterrupt:
                print(f"\nDownload interrupted. Progress saved.")
                self.save_progress()
                break
            except Exception as e:
                print(f"\nError processing {state_name}: {e}")
                continue
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*80}")
        print(f"BATCH DOWNLOAD SESSION COMPLETE")
        print(f"{'='*80}")
        print(f"Session stats:")
        print(f"  Successfully downloaded: {self.session_stats['successful']}")
        print(f"  Skipped (existing): {self.session_stats['skipped']}")
        print(f"  Errors: {self.session_stats['errors']}")
        print(f"  Rate limited: {self.session_stats['rate_limited']}")
        print(f"  Session time: {duration/60:.1f} minutes")
        print(f"\nProgress saved to: {progress_file}")
        print(f"Run script again to continue downloading remaining counties.")

def main():
    downloader = SmartDownloader()
    downloader.download_all_states()

if __name__ == "__main__":
    main()