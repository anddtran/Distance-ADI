#!/usr/bin/env python3
"""
OSM Geocoding Setup and Installation Script

Installs required dependencies and sets up the OSM geocoding environment.
Provides options for different installation levels based on user needs.

Usage:
    python install.py [--minimal] [--full] [--check]
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"📦 {description}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version OK: {sys.version}")
    return True

def check_existing_dependencies():
    """Check which dependencies are already installed."""
    print("\n🔍 Checking existing dependencies...")
    
    dependencies = [
        'pandas', 'geopandas', 'geopy', 'usaddress', 'openpyxl', 'shapely'
    ]
    
    installed = []
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            installed.append(dep)
            print(f"✅ {dep} - already installed")
        except ImportError:
            missing.append(dep)
            print(f"❌ {dep} - needs installation")
    
    return installed, missing

def install_minimal():
    """Install minimal dependencies for basic OSM geocoding."""
    print("\n🎯 Installing minimal OSM geocoding dependencies...")
    
    # Core OSM dependencies
    packages = [
        'osmium>=3.2.0',
        'pyosmium>=3.2.0',
        'osmnx>=1.2.0',
        'networkx>=2.6.0',
        'rtree>=1.0.0'
    ]
    
    for package in packages:
        success = run_command(f"pip install '{package}'", f"Installing {package}")
        if not success:
            print(f"⚠️ Failed to install {package}")
            return False
    
    return True

def install_full():
    """Install all dependencies including optional ones."""
    print("\n🔧 Installing full OSM geocoding environment...")
    
    # Install from requirements file
    req_file = Path(__file__).parent / 'requirements.txt'
    if req_file.exists():
        success = run_command(f"pip install -r {req_file}", "Installing from requirements.txt")
        return success
    else:
        print("❌ requirements.txt not found")
        return False

def install_system_dependencies():
    """Install system-level dependencies (varies by OS)."""
    print("\n🖥️  System Dependencies Information")
    print("The following system packages may be needed:")
    print("  - GDAL/OGR (for spatial data processing)")
    print("  - GEOS (for geometric operations)")
    print("  - PROJ (for coordinate transformations)")
    print("  - Spatialindex (for rtree)")
    print()
    
    # Check OS and provide instructions
    import platform
    os_name = platform.system().lower()
    
    if os_name == 'darwin':  # macOS
        print("🍎 macOS Instructions:")
        print("  brew install gdal geos proj spatialindex")
        print("  pip install GDAL==$(gdal-config --version)")
    
    elif os_name == 'linux':
        print("🐧 Linux Instructions:")
        print("  # Ubuntu/Debian:")
        print("  sudo apt-get install gdal-bin libgdal-dev libgeos-dev proj-bin libproj-dev libspatialindex-dev")
        print("  # CentOS/RHEL:")
        print("  sudo yum install gdal gdal-devel geos geos-devel proj proj-devel spatialindex-devel")
    
    elif os_name == 'windows':
        print("🪟 Windows Instructions:")
        print("  Use conda for easier installation:")
        print("  conda install -c conda-forge gdal geos proj rtree")
    
    print("\n⚠️  Note: System dependencies may require administrator privileges")

def test_installation():
    """Test that all dependencies are working correctly."""
    print("\n🧪 Testing installation...")
    
    test_imports = [
        ('pandas', 'pd'),
        ('geopandas', 'gpd'),
        ('geopy', None),
        ('usaddress', None),
        ('shapely', None),
        ('osmium', None),
        ('osmnx', 'ox'),
        ('networkx', 'nx'),
        ('rtree', None)
    ]
    
    failed_imports = []
    
    for module, alias in test_imports:
        try:
            if alias:
                exec(f"import {module} as {alias}")
            else:
                exec(f"import {module}")
            print(f"✅ {module} imported successfully")
        except ImportError as e:
            print(f"❌ {module} import failed: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n⚠️ {len(failed_imports)} modules failed to import")
        return False
    else:
        print("\n✅ All dependencies imported successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description='Install OSM geocoding dependencies')
    parser.add_argument('--minimal', action='store_true', 
                       help='Install minimal dependencies only')
    parser.add_argument('--full', action='store_true', 
                       help='Install all dependencies')
    parser.add_argument('--check', action='store_true', 
                       help='Check current installation status')
    parser.add_argument('--system-info', action='store_true',
                       help='Show system dependency information')
    
    args = parser.parse_args()
    
    print("OSM Geocoding Setup")
    print("==================")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check existing dependencies
    installed, missing = check_existing_dependencies()
    
    if args.check:
        print(f"\n📊 Status: {len(installed)}/{len(installed) + len(missing)} base dependencies installed")
        test_installation()
        return
    
    if args.system_info:
        install_system_dependencies()
        return
    
    if not args.minimal and not args.full:
        print("\n🤔 Choose installation type:")
        print("  --minimal: Install only OSM-specific packages")
        print("  --full: Install all dependencies from requirements.txt")
        print("  --check: Check current installation status")
        print("  --system-info: Show system dependency information")
        return
    
    # Install dependencies
    if args.minimal:
        success = install_minimal()
    elif args.full:
        success = install_full()
    
    if success:
        print("\n✅ Installation completed!")
        print("Testing installation...")
        if test_installation():
            print("\n🎉 OSM geocoding environment is ready!")
            print("\nNext steps:")
            print("1. Download OSM data: python download_osm_data.py --all")
            print("2. Run geocoding tests: python ../tests/test_osm_geocoding.py")
        else:
            print("\n⚠️ Installation completed but some tests failed")
    else:
        print("\n❌ Installation failed")
        print("Try running with --system-info for dependency information")

if __name__ == '__main__':
    main()