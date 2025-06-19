#!/usr/bin/env python3
"""
Smart Batch ADDRFEAT Downloader with Real-Time Progress Bar

Enhanced version with live progress tracking and visual status updates.
"""

import os
import requests
import zipfile
import time
import json
import random
import sys
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

class ProgressBar:
    def __init__(self, total, prefix='Progress', suffix='Complete', length=50):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.current = 0
        
    def update(self, current):
        self.current = current
        percent = f"{100 * current / self.total:.1f}"
        filled_length = int(self.length * current // self.total)
        bar = '█' * filled_length + '-' * (self.length - filled_length)
        
        # Clear line and print progress
        sys.stdout.write(f'\r{self.prefix} |{bar}| {current}/{self.total} ({percent}%) {self.suffix}')
        sys.stdout.flush()
        
    def finish(self):
        print()  # New line after completion

class SmartDownloaderWithProgress:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Research Download Bot for Academic Use)'
        })
        
        # Rate limiting parameters
        self.base_delay = 1.0  # Faster for progress visibility
        self.max_delay = 60.0
        self.rate_limit_delay = 20.0
        self.circuit_breaker_threshold = 10
        self.consecutive_failures = 0
        
        # Progress tracking
        self.progress = self.load_progress()
        self.total_target = sum(state['counties'] for state in STATES.values())
        self.session_stats = {
            'successful': 0,
            'skipped': 0,
            'errors': 0,
            'rate_limited': 0,
            'processed': 0
        }
        
        # Create main progress bar
        existing_files = self.count_existing_files()
        self.progress_bar = ProgressBar(
            total=self.total_target,
            prefix='Overall Progress',
            suffix=f'counties downloaded (Target: {self.total_target})'
        )
        self.progress_bar.update(existing_files)
    
    def count_existing_files(self):
        """Count total existing ZIP files across all states"""
        total = 0
        for state_name in STATES.keys():
            state_path = os.path.join(base_path, state_name)
            if os.path.exists(state_path):
                total += len([f for f in os.listdir(state_path) if f.endswith('.zip')])
        return total
    
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
        progress_data = {
            'completed_counties': list(self.progress['completed_counties']),
            'failed_counties': list(self.progress['failed_counties']),
            'last_updated': datetime.now().isoformat()
        }
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def update_status_line(self, message):
        """Print status message while preserving progress bar"""
        print(f"\n{message}")
        current_files = self.count_existing_files()
        self.progress_bar.update(current_files)
    
    def download_county_with_backoff(self, state_name, state_fips, county_fips, max_retries=3):
        """Download single county with progress updates"""
        url = f"https://www2.census.gov/geo/tiger/TIGER2023/ADDRFEAT/tl_2023_{state_fips}{county_fips}_addrfeat.zip"
        filename = f"tl_2023_{state_fips}{county_fips}_addrfeat.zip"
        state_dir = os.path.join(base_path, state_name)
        filepath = os.path.join(state_dir, filename)
        county_id = f"{state_fips}{county_fips}"
        
        self.session_stats['processed'] += 1
        
        # Skip if already completed
        if county_id in self.progress.get('completed_counties', set()):
            self.session_stats['skipped'] += 1
            return f"SKIP: {state_name} county {county_fips} (already completed)"
        
        # Skip if file already exists
        if os.path.exists(filepath):
            self.progress.setdefault('completed_counties', set()).add(county_id)
            self.session_stats['skipped'] += 1
            current_files = self.count_existing_files()
            self.progress_bar.update(current_files)
            return f"SKIP: {state_name} county {county_fips} (file exists)"
        
        # Circuit breaker check
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            time.sleep(self.max_delay)
            self.consecutive_failures = 0
            self.update_status_line(f"Circuit breaker triggered, pausing...")
        
        for attempt in range(max_retries):
            try:
                # Calculate delay with jitter
                if attempt > 0:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    jitter = random.uniform(0.8, 1.2)
                    time.sleep(delay * jitter)
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    os.makedirs(state_dir, exist_ok=True)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract immediately
                    try:
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(state_dir)
                        
                        # Mark as completed and update progress
                        self.progress.setdefault('completed_counties', set()).add(county_id)
                        self.consecutive_failures = 0
                        self.session_stats['successful'] += 1
                        
                        # Update progress bar
                        current_files = self.count_existing_files()
                        self.progress_bar.update(current_files)
                        
                        return f"SUCCESS: {state_name} county {county_fips} ({len(response.content)//1024}KB)"
                    
                    except zipfile.BadZipFile:
                        os.remove(filepath)
                        self.session_stats['errors'] += 1
                        return f"ERROR: {state_name} county {county_fips} (corrupted file)"
                
                elif response.status_code == 404:
                    # County doesn't exist, mark as completed
                    self.progress.setdefault('completed_counties', set()).add(county_id)
                    self.session_stats['skipped'] += 1
                    return f"SKIP: {state_name} county {county_fips} (does not exist)"
                
                elif response.status_code == 429:
                    self.session_stats['rate_limited'] += 1
                    self.consecutive_failures += 1
                    
                    if attempt < max_retries - 1:
                        delay = self.rate_limit_delay * (2 ** attempt)
                        self.update_status_line(f"Rate limited, waiting {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.progress.setdefault('failed_counties', set()).add(county_id)
                        return f"ERROR: {state_name} county {county_fips} (rate limited)"
                
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
    
    def download_state_batch(self, state_name, batch_size=10, max_workers=2):
        """Download counties for a state in batches with progress"""
        state_info = STATES[state_name]
        state_fips = state_info['fips']
        
        # Get counties that need downloading
        all_counties = {f"{i:03d}" for i in range(1, state_info['counties'] + 1)}
        existing_counties = set()
        
        state_path = os.path.join(base_path, state_name)
        if os.path.exists(state_path):
            for filename in os.listdir(state_path):
                if filename.endswith('.zip') and filename.startswith('tl_2023_'):
                    county_fips = filename[9:12]
                    existing_counties.add(county_fips)
        
        completed_counties = {county_id[-3:] for county_id in self.progress.get('completed_counties', set()) if county_id.startswith(state_fips)}
        pending_counties = all_counties - existing_counties - completed_counties
        
        self.update_status_line(f"\n🏛️  {state_name.upper()}: {len(existing_counties)} existing, {len(pending_counties)} to download")
        
        if not pending_counties:
            self.update_status_line(f"✅ All {state_name} counties completed!")
            return
        
        # Process in batches
        county_list = sorted(list(pending_counties))
        for batch_start in range(0, len(county_list), batch_size):
            batch = county_list[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(county_list) + batch_size - 1) // batch_size
            
            self.update_status_line(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} counties)...")
            
            # Download batch concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.download_county_with_backoff, state_name, state_fips, county_fips): county_fips
                    for county_fips in batch
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    # Save progress after each download
                    self.save_progress()
            
            # Delay between batches
            if batch_start + batch_size < len(county_list):
                batch_delay = random.uniform(30, 45)
                for i in range(int(batch_delay), 0, -1):
                    self.update_status_line(f"⏳ Next batch in {i}s...")
                    time.sleep(1)
    
    def download_all_states(self):
        """Download all remaining counties with progress tracking"""
        print("🚀 SMART BATCH ADDRFEAT DOWNLOADER WITH PROGRESS")
        print("=" * 80)
        print(f"Target: Complete coverage of all {self.total_target} counties")
        print("=" * 80)
        
        start_time = time.time()
        initial_files = self.count_existing_files()
        
        # Prioritize Arkansas first
        priority_states = ['arkansas', 'tennessee', 'mississippi', 'louisiana']
        remaining_states = ['texas', 'oklahoma', 'missouri']
        all_states = priority_states + remaining_states
        
        try:
            for state_name in all_states:
                self.download_state_batch(state_name)
                
                # Delay between states
                if state_name != all_states[-1]:
                    state_delay = random.uniform(60, 90)
                    for i in range(int(state_delay), 0, -5):
                        self.update_status_line(f"🔄 Next state in {i}s...")
                        time.sleep(5)
                        
        except KeyboardInterrupt:
            self.update_status_line("\n⏹️  Download interrupted by user. Progress saved.")
            self.save_progress()
        
        # Final summary
        self.progress_bar.finish()
        end_time = time.time()
        duration = end_time - start_time
        final_files = self.count_existing_files()
        files_gained = final_files - initial_files
        
        print(f"\n{'='*80}")
        print(f"📊 SESSION COMPLETE")
        print(f"{'='*80}")
        print(f"Files at start: {initial_files}/{self.total_target}")
        print(f"Files at end: {final_files}/{self.total_target}")
        print(f"Files gained this session: {files_gained}")
        print(f"Overall completion: {(final_files/self.total_target)*100:.1f}%")
        print(f"Session time: {duration/60:.1f} minutes")
        print(f"Counties processed: {self.session_stats['processed']}")
        print(f"Successful downloads: {self.session_stats['successful']}")
        print(f"Skipped (existing/nonexistent): {self.session_stats['skipped']}")
        print(f"Errors: {self.session_stats['errors']}")
        print(f"Rate limited: {self.session_stats['rate_limited']}")
        print("=" * 80)

def main():
    downloader = SmartDownloaderWithProgress()
    downloader.download_all_states()

if __name__ == "__main__":
    main()