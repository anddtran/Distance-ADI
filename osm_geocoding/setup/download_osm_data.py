#!/usr/bin/env python3
"""
OSM Data Download Automation Script

Downloads OpenStreetMap data for target states from Geofabrik.
Stores data locally for offline geocoding and routing operations.

Usage:
    python download_osm_data.py [--all] [--state STATE_NAME]
    
Examples:
    python download_osm_data.py --all                    # Download all states
    python download_osm_data.py --state arkansas         # Download specific state
    python download_osm_data.py --state arkansas --force # Force re-download
"""

import argparse
import os
import sys
import urllib.request
import hashlib
from datetime import datetime
from pathlib import Path

# Target states configuration
STATES = {
    'arkansas': {
        'url': 'https://download.geofabrik.de/north-america/us/arkansas-latest.osm.pbf',
        'expected_size_mb': 50,
        'priority': 1  # Primary research state
    },
    'tennessee': {
        'url': 'https://download.geofabrik.de/north-america/us/tennessee-latest.osm.pbf',
        'expected_size_mb': 120,
        'priority': 2
    },
    'mississippi': {
        'url': 'https://download.geofabrik.de/north-america/us/mississippi-latest.osm.pbf',
        'expected_size_mb': 80,
        'priority': 2
    },
    'louisiana': {
        'url': 'https://download.geofabrik.de/north-america/us/louisiana-latest.osm.pbf',
        'expected_size_mb': 90,
        'priority': 2
    },
    'texas': {
        'url': 'https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf',
        'expected_size_mb': 800,
        'priority': 3  # Largest file
    },
    'oklahoma': {
        'url': 'https://download.geofabrik.de/north-america/us/oklahoma-latest.osm.pbf',
        'expected_size_mb': 110,
        'priority': 2
    },
    'missouri': {
        'url': 'https://download.geofabrik.de/north-america/us/missouri-latest.osm.pbf',
        'expected_size_mb': 150,
        'priority': 2
    }
}

def get_data_directory():
    """Get the OSM data directory path."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data' / 'osm_extracts'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def calculate_file_hash(filepath):
    """Calculate MD5 hash of file for integrity checking."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_with_progress(url, filepath):
    """Download file with progress reporting."""
    print(f"Downloading: {url}")
    print(f"Destination: {filepath}")
    
    def progress_hook(block_num, block_size, total_size):
        if total_size > 0:
            percent = min(100, (block_num * block_size * 100) / total_size)
            downloaded_mb = (block_num * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(f"\rProgress: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)", end='')
        else:
            downloaded_mb = (block_num * block_size) / (1024 * 1024)
            print(f"\rDownloaded: {downloaded_mb:.1f} MB", end='')
    
    try:
        urllib.request.urlretrieve(url, filepath, progress_hook)
        print("\nDownload completed successfully!")
        return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        # Clean up partial download
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def validate_download(filepath, expected_size_mb):
    """Validate downloaded file size and basic integrity."""
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    # Check file size
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    size_tolerance = 0.2  # 20% tolerance
    
    if file_size_mb < expected_size_mb * (1 - size_tolerance):
        return False, f"File too small: {file_size_mb:.1f}MB (expected ~{expected_size_mb}MB)"
    
    if file_size_mb > expected_size_mb * (1 + size_tolerance + 1):  # Allow larger files
        return False, f"File unexpectedly large: {file_size_mb:.1f}MB (expected ~{expected_size_mb}MB)"
    
    # Basic PBF format check (should start with blob header)
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if not header:
                return False, "Empty file"
            # PBF files don't have a standard magic number, but we can check it's not obviously corrupt
    except Exception as e:
        return False, f"File read error: {e}"
    
    return True, f"Valid file: {file_size_mb:.1f}MB"

def download_state(state_name, force=False):
    """Download OSM data for a specific state."""
    if state_name not in STATES:
        print(f"Error: Unknown state '{state_name}'")
        print(f"Available states: {', '.join(STATES.keys())}")
        return False
    
    state_config = STATES[state_name]
    data_dir = get_data_directory()
    filename = f"{state_name}-latest.osm.pbf"
    filepath = data_dir / filename
    
    # Check if file already exists and is valid
    if filepath.exists() and not force:
        is_valid, message = validate_download(filepath, state_config['expected_size_mb'])
        if is_valid:
            print(f"✅ {state_name}: Already downloaded and valid ({message})")
            return True
        else:
            print(f"⚠️  {state_name}: Existing file is invalid ({message}), re-downloading...")
    
    # Download the file
    success = download_with_progress(state_config['url'], filepath)
    
    if success:
        # Validate the download
        is_valid, message = validate_download(filepath, state_config['expected_size_mb'])
        if is_valid:
            print(f"✅ {state_name}: {message}")
            
            # Create metadata file
            metadata_file = data_dir / f"{state_name}-latest.osm.pbf.meta"
            with open(metadata_file, 'w') as f:
                f.write(f"Downloaded: {datetime.now().isoformat()}\n")
                f.write(f"URL: {state_config['url']}\n")
                f.write(f"File size: {os.path.getsize(filepath)} bytes\n")
                f.write(f"MD5 hash: {calculate_file_hash(filepath)}\n")
            
            return True
        else:
            print(f"❌ {state_name}: Download validation failed ({message})")
            return False
    else:
        print(f"❌ {state_name}: Download failed")
        return False

def main():
    parser = argparse.ArgumentParser(description='Download OSM data for geocoding')
    parser.add_argument('--all', action='store_true', help='Download all states')
    parser.add_argument('--state', help='Download specific state')
    parser.add_argument('--force', action='store_true', help='Force re-download existing files')
    parser.add_argument('--list', action='store_true', help='List available states')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available states:")
        for state, config in sorted(STATES.items(), key=lambda x: (x[1]['priority'], x[0])):
            print(f"  {state:<12} (~{config['expected_size_mb']} MB)")
        return
    
    if not args.all and not args.state:
        parser.print_help()
        return
    
    print("OSM Data Downloader")
    print("==================")
    print(f"Data directory: {get_data_directory()}")
    print()
    
    success_count = 0
    total_count = 0
    
    if args.all:
        # Download all states, ordered by priority
        states_to_download = sorted(STATES.keys(), key=lambda x: (STATES[x]['priority'], x))
        for state in states_to_download:
            total_count += 1
            if download_state(state, args.force):
                success_count += 1
            print()
    
    elif args.state:
        total_count = 1
        if download_state(args.state.lower(), args.force):
            success_count = 1
    
    # Summary
    print("=" * 50)
    print(f"Download Summary: {success_count}/{total_count} successful")
    if success_count == total_count:
        print("✅ All downloads completed successfully!")
    else:
        print(f"⚠️  {total_count - success_count} downloads failed")
    
    # Show total disk usage
    data_dir = get_data_directory()
    total_size = sum(f.stat().st_size for f in data_dir.glob('*.pbf') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    print(f"Total disk usage: {total_size_mb:.1f} MB")

if __name__ == '__main__':
    main()