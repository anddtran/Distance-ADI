#!/usr/bin/env python3
"""
Complete OSM-based Distance and ADI Calculator

Integrates OSM geocoding and routing with existing ADI/COI lookup system.
Provides a complete alternative to the existing TIGER/ADDRFEAT methods.

Features:
- OSM-based address geocoding
- Road network distance calculations
- ADI/COI lookup integration
- Fallback to existing methods when needed
- Comparative analysis capabilities

Usage:
    python osm_distance_calculator.py
    # Enter target address and input file when prompted
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from osm_geocoder import OSMGeocoder, GeocodeResult
from osm_routing import OSMRouter, DistanceResult


class OSMDistanceCalculator:
    """Complete OSM-based distance and ADI calculation system."""
    
    def __init__(self, use_existing_data: bool = True):
        """Initialize with optional use of existing reference data."""
        self.use_existing_data = use_existing_data
        
        # Initialize OSM components
        self.geocoder = OSMGeocoder()
        self.router = OSMRouter()
        
        # Reference data (from existing system)
        self.adi_data = None
        self.coi_data = None
        self.block_groups_gdf = None
        self.zip_centroids = None
        
        # Results tracking
        self.geocoding_stats = {
            'total': 0,
            'osm_success': 0,
            'osm_exact': 0,
            'osm_interpolated': 0,
            'osm_approximate': 0,
            'fallback_used': 0
        }
        
        self.routing_stats = {
            'total': 0,
            'road_network_success': 0,
            'geodesic_only': 0
        }
    
    def setup(self, states: List[str], input_file: str, target_address: str) -> bool:
        """Setup the calculator with required data."""
        print("🔧 Setting up OSM Distance Calculator...")
        
        # Load OSM data
        print("📂 Loading OSM geocoding data...")
        if not self.geocoder.load_osm_data(states):
            print("❌ Failed to load OSM geocoding data")
            return False
        
        print("🛣️  Loading OSM road network...")
        if not self.router.load_road_network(states):
            print("❌ Failed to load OSM road network")
            return False
        
        # Load existing reference data if requested
        if self.use_existing_data:
            print("📊 Loading existing reference data...")
            if not self._load_existing_data():
                print("⚠️ Failed to load some reference data")
        
        # Load and validate input data
        print("📋 Loading input data...")
        if not self._load_input_data(input_file):
            print("❌ Failed to load input data")
            return False
        
        # Geocode target address
        print("🎯 Geocoding target address...")
        self.target_coords = self._geocode_target_address(target_address)
        if self.target_coords is None:
            print("❌ Failed to geocode target address")
            return False
        
        print("✅ Setup completed successfully!")
        return True
    
    def _load_existing_data(self) -> bool:
        """Load existing ADI/COI and geographic reference data."""
        try:
            # Paths to existing data
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / 'data'
            
            # Load ADI data
            adi_file = data_dir / 'reference' / 'US_2021_ADI_Census_Block_Group_v4_0_1.csv'
            if adi_file.exists():
                self.adi_data = pd.read_csv(adi_file)
                print(f"  Loaded {len(self.adi_data)} ADI records")
            
            # Load ZIP centroids
            zip_file = data_dir / 'reference' / '2023_Gaz_zcta_national.txt'
            if zip_file.exists():
                self.zip_centroids = pd.read_csv(zip_file, sep='\t')
                print(f"  Loaded {len(self.zip_centroids)} ZIP centroids")
            
            # Load census block groups
            shapefile_dir = data_dir / 'reference' / 'shapefiles'
            bg_file = shapefile_dir / 'cb_2020_us_bg_500k.shp'
            if bg_file.exists():
                self.block_groups_gdf = gpd.read_file(bg_file)
                print(f"  Loaded {len(self.block_groups_gdf)} census block groups")
            
            # Load COI data if available
            coi_dir = data_dir / 'reference' / 'COI'
            if coi_dir.exists():
                coi_files = list(coi_dir.glob('*.csv'))
                if coi_files:
                    self.coi_data = pd.read_csv(coi_files[0])
                    print(f"  Loaded {len(self.coi_data)} COI records")
            
            return True
            
        except Exception as e:
            print(f"Error loading existing data: {e}")
            return False
    
    def _load_input_data(self, input_file: str) -> bool:
        """Load input address data."""
        try:
            if not os.path.exists(input_file):
                print(f"Input file not found: {input_file}")
                return False
            
            # Load input file
            if input_file.endswith('.xlsx'):
                self.input_data = pd.read_excel(input_file)
            elif input_file.endswith('.csv'):
                self.input_data = pd.read_csv(input_file)
            else:
                print(f"Unsupported file format: {input_file}")
                return False
            
            # Validate required columns
            if 'Address' not in self.input_data.columns:
                print("Input file must contain 'Address' column")
                return False
            
            print(f"  Loaded {len(self.input_data)} addresses to process")
            return True
            
        except Exception as e:
            print(f"Error loading input data: {e}")
            return False
    
    def _geocode_target_address(self, target_address: str) -> Optional[Tuple[float, float]]:
        """Geocode the target address using OSM."""
        try:
            result = self.geocoder.geocode(target_address)
            if result:
                print(f"  Target coordinates: {result.latitude:.6f}, {result.longitude:.6f}")
                print(f"  Confidence: {result.confidence:.2f}")
                print(f"  Match type: {result.match_type}")
                return (result.latitude, result.longitude)
            else:
                print("  No match found for target address")
                return None
                
        except Exception as e:
            print(f"Error geocoding target address: {e}")
            return None
    
    def process_addresses(self) -> pd.DataFrame:
        """Process all addresses and calculate distances."""
        print(f"\n🔍 Processing {len(self.input_data)} addresses...")
        
        results = []
        
        for idx, row in self.input_data.iterrows():
            if idx % 50 == 0:
                print(f"  Progress: {idx}/{len(self.input_data)}")
            
            address = row['Address']
            result = self._process_single_address(address, row)
            results.append(result)
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Print statistics
        self._print_processing_stats()
        
        return results_df
    
    def _process_single_address(self, address: str, row: pd.Series) -> Dict:
        """Process a single address through the complete pipeline."""
        self.geocoding_stats['total'] += 1
        self.routing_stats['total'] += 1
        
        # Initialize result with input data
        result = {
            'MRN': row.get('MRN', ''),
            'Address': address,
            'Longitude': None,
            'Latitude': None,
            'Geocoding_Method': 'failed',
            'Geocoding_Confidence': 0.0,
            'FIPS': '',
            'ADI_NATRANK': None,
            'ADI_STATERNK': None,
            'Distance_Geodesic_Miles': None,
            'Distance_Road_Miles': None,
            'Travel_Time_Minutes': None,
            'Distance_Method': 'failed'
        }
        
        # Step 1: Geocode the address
        geocode_result = self._geocode_with_fallback(address)
        
        if geocode_result is None:
            return result
        
        # Update result with geocoding info
        result['Longitude'] = geocode_result.longitude
        result['Latitude'] = geocode_result.latitude
        result['Geocoding_Method'] = f"osm_{geocode_result.source}"
        result['Geocoding_Confidence'] = geocode_result.confidence
        
        # Update stats
        self.geocoding_stats['osm_success'] += 1
        if geocode_result.match_type == 'exact':
            self.geocoding_stats['osm_exact'] += 1
        elif geocode_result.match_type == 'interpolated':
            self.geocoding_stats['osm_interpolated'] += 1
        else:
            self.geocoding_stats['osm_approximate'] += 1
        
        # Step 2: Get FIPS code and ADI data
        fips = self._get_fips_code(geocode_result.latitude, geocode_result.longitude)
        if fips:
            result['FIPS'] = fips
            adi_info = self._get_adi_info(fips)
            if adi_info:
                result['ADI_NATRANK'] = adi_info.get('ADI_NATRANK')
                result['ADI_STATERNK'] = adi_info.get('ADI_STATERNK')
        
        # Step 3: Calculate distances
        address_coords = (geocode_result.latitude, geocode_result.longitude)
        distance_result = self.router.calculate_distance(self.target_coords, address_coords)
        
        result['Distance_Geodesic_Miles'] = distance_result.geodesic_distance_miles
        result['Distance_Method'] = distance_result.calculation_method
        
        if distance_result.road_distance_miles:
            result['Distance_Road_Miles'] = distance_result.road_distance_miles
            result['Travel_Time_Minutes'] = distance_result.travel_time_minutes
            self.routing_stats['road_network_success'] += 1
        else:
            self.routing_stats['geodesic_only'] += 1
        
        return result
    
    def _geocode_with_fallback(self, address: str) -> Optional[GeocodeResult]:
        """Geocode address with fallback to existing methods."""
        # Try OSM geocoding first
        result = self.geocoder.geocode(address)
        if result:
            return result
        
        # Fallback to ZIP centroid if available
        if self.zip_centroids is not None:
            fallback_result = self._fallback_zip_geocoding(address)
            if fallback_result:
                self.geocoding_stats['fallback_used'] += 1
                return fallback_result
        
        return None
    
    def _fallback_zip_geocoding(self, address: str) -> Optional[GeocodeResult]:
        """Fallback geocoding using ZIP centroids."""
        try:
            # Extract ZIP code from address
            import usaddress
            parsed, _ = usaddress.tag(address)
            zip_code = parsed.get('ZipCode')
            
            if not zip_code:
                return None
            
            # Look up ZIP centroid
            zip_match = self.zip_centroids[self.zip_centroids['GEOID'] == zip_code]
            if len(zip_match) == 0:
                return None
            
            zip_info = zip_match.iloc[0]
            return GeocodeResult(
                latitude=zip_info['INTPTLAT'],
                longitude=zip_info['INTPTLONG'],
                confidence=0.5,
                match_type='approximate',
                source='zip_centroid_fallback',
                matched_address=f"ZIP {zip_code}"
            )
            
        except Exception as e:
            return None
    
    def _get_fips_code(self, lat: float, lon: float) -> Optional[str]:
        """Get FIPS code from coordinates using spatial join."""
        if self.block_groups_gdf is None:
            return None
        
        try:
            point = Point(lon, lat)
            point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs='EPSG:4326')
            
            # Spatial join to find containing block group
            joined = gpd.sjoin(point_gdf, self.block_groups_gdf, how='left', predicate='within')
            
            if len(joined) > 0 and not pd.isna(joined.iloc[0]['GEOID']):
                return joined.iloc[0]['GEOID']
            
            return None
            
        except Exception as e:
            return None
    
    def _get_adi_info(self, fips: str) -> Optional[Dict]:
        """Get ADI information for FIPS code."""
        if self.adi_data is None:
            return None
        
        try:
            adi_match = self.adi_data[self.adi_data['FIPS'] == fips]
            if len(adi_match) > 0:
                return adi_match.iloc[0].to_dict()
            return None
            
        except Exception as e:
            return None
    
    def _print_processing_stats(self):
        """Print processing statistics."""
        print("\n📊 Processing Statistics:")
        print("=" * 40)
        
        # Geocoding stats
        total = self.geocoding_stats['total']
        if total > 0:
            print(f"Geocoding Success Rate: {self.geocoding_stats['osm_success']}/{total} ({self.geocoding_stats['osm_success']/total*100:.1f}%)")
            print(f"  Exact matches: {self.geocoding_stats['osm_exact']}")
            print(f"  Interpolated: {self.geocoding_stats['osm_interpolated']}")
            print(f"  Approximate: {self.geocoding_stats['osm_approximate']}")
            print(f"  Fallback used: {self.geocoding_stats['fallback_used']}")
        
        # Routing stats
        total = self.routing_stats['total']
        if total > 0:
            print(f"Road Network Routing: {self.routing_stats['road_network_success']}/{total} ({self.routing_stats['road_network_success']/total*100:.1f}%)")
            print(f"Geodesic Only: {self.routing_stats['geodesic_only']}")
    
    def save_results(self, results_df: pd.DataFrame, output_dir: str = None) -> str:
        """Save results to Excel file."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / 'data' / 'output'
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_osm_geocoding_{timestamp}.xlsx"
        filepath = output_dir / filename
        
        # Save to Excel
        results_df.to_excel(filepath, index=False)
        
        print(f"✅ Results saved to: {filepath}")
        return str(filepath)


def main():
    """Main execution function."""
    print("OSM Distance Calculator")
    print("=" * 50)
    
    # Get user input
    target_address = input("Enter target address: ").strip()
    if not target_address:
        print("Target address is required")
        return
    
    # Default input file path
    default_input = str(Path(__file__).parent.parent.parent / 'data' / 'input' / 'data.xlsx')
    input_file = input(f"Enter input file path (default: {default_input}): ").strip()
    if not input_file:
        input_file = default_input
    
    # States to load (default to Arkansas)
    states_input = input("Enter states to load (default: arkansas): ").strip()
    if not states_input:
        states = ['arkansas']
    else:
        states = [s.strip().lower() for s in states_input.split(',')]
    
    # Initialize calculator
    calculator = OSMDistanceCalculator()
    
    # Setup
    if not calculator.setup(states, input_file, target_address):
        print("Setup failed")
        return
    
    # Process addresses
    print("\n🚀 Processing addresses...")
    start_time = time.time()
    
    results_df = calculator.process_addresses()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Processing completed in {elapsed:.1f} seconds")
    
    # Save results
    output_file = calculator.save_results(results_df)
    
    print(f"\n✅ OSM distance calculation completed!")
    print(f"Output file: {output_file}")
    
    # Save router cache
    calculator.router.save_cache()


if __name__ == "__main__":
    main()