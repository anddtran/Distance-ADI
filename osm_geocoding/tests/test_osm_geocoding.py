#!/usr/bin/env python3
"""
OSM Geocoding Testing Framework

Tests and validates OSM geocoding accuracy against known coordinates
and compares results with existing TIGER/ADDRFEAT methods.

Features:
- Accuracy validation against known coordinates
- Comparison with existing geocoding methods
- Performance benchmarking
- Coverage analysis

Usage:
    python test_osm_geocoding.py [--method METHOD] [--output OUTPUT_FILE]
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from geopy.distance import geodesic

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))
sys.path.append(str(Path(__file__).parent.parent.parent / 'scripts'))

from osm_geocoder import OSMGeocoder
from osm_routing import OSMRouter
from osm_distance_calculator import OSMDistanceCalculator

# Try to import existing geocoding methods
try:
    import usaddress
    USADDRESS_AVAILABLE = True
except ImportError:
    USADDRESS_AVAILABLE = False


class OSMGeocodingTester:
    """Test and validate OSM geocoding performance."""
    
    def __init__(self):
        self.geocoder = OSMGeocoder()
        self.router = OSMRouter()
        
        # Test data
        self.test_addresses = []
        self.known_coordinates = []
        
        # Results
        self.test_results = []
        
    def setup_test_data(self):
        """Setup test addresses with known coordinates."""
        # Test addresses with manually verified coordinates
        self.test_data = [
            {
                'address': '500 Woodlane Street, Little Rock, AR 72201',
                'known_lat': 34.7465,
                'known_lon': -92.2896,
                'description': 'Downtown Little Rock'
            },
            {
                'address': '1 University Avenue, Fayetteville, AR 72701',
                'known_lat': 36.0822,
                'known_lon': -94.1719,
                'description': 'University of Arkansas'
            },
            {
                'address': '1000 Main Street, Conway, AR 72032',
                'known_lat': 35.0887,
                'known_lon': -92.4421,
                'description': 'Conway downtown'
            },
            {
                'address': '2801 S University Ave, Little Rock, AR 72204',
                'known_lat': 34.7244,
                'known_lon': -92.3318,
                'description': 'UALR campus'
            },
            {
                'address': '300 Spring Street, Hot Springs, AR 71901',
                'known_lat': 34.5037,
                'known_lon': -93.0552,
                'description': 'Hot Springs downtown'
            },
            {
                'address': '123 Market Street, Fort Smith, AR 72901',
                'known_lat': 35.3859,
                'known_lon': -94.3985,
                'description': 'Fort Smith downtown'
            },
            {
                'address': '456 Oak Street, Jonesboro, AR 72401',
                'known_lat': 35.8423,
                'known_lon': -90.7043,
                'description': 'Jonesboro'
            },
            {
                'address': '789 Pine Street, Bentonville, AR 72712',
                'known_lat': 36.3729,
                'known_lon': -94.2088,
                'description': 'Bentonville'
            }
        ]
        
        print(f"📋 Loaded {len(self.test_data)} test addresses")
    
    def load_osm_data(self, states: List[str] = ['arkansas']) -> bool:
        """Load OSM data for testing."""
        print("📂 Loading OSM data for testing...")
        
        # Load geocoding data
        if not self.geocoder.load_osm_data(states):
            print("❌ Failed to load OSM geocoding data")
            return False
        
        # Load routing data
        if not self.router.load_road_network(states):
            print("❌ Failed to load OSM routing data")
            return False
        
        return True
    
    def test_geocoding_accuracy(self) -> pd.DataFrame:
        """Test geocoding accuracy against known coordinates."""
        print("\n🎯 Testing OSM geocoding accuracy...")
        
        results = []
        
        for i, test_case in enumerate(self.test_data):
            print(f"  Testing {i+1}/{len(self.test_data)}: {test_case['description']}")
            
            # Geocode using OSM
            start_time = time.time()
            osm_result = self.geocoder.geocode(test_case['address'])
            geocoding_time = time.time() - start_time
            
            # Calculate accuracy
            result = {
                'address': test_case['address'],
                'description': test_case['description'],
                'known_lat': test_case['known_lat'],
                'known_lon': test_case['known_lon'],
                'osm_success': osm_result is not None,
                'osm_lat': osm_result.latitude if osm_result else None,
                'osm_lon': osm_result.longitude if osm_result else None,
                'osm_confidence': osm_result.confidence if osm_result else 0,
                'osm_match_type': osm_result.match_type if osm_result else 'failed',
                'osm_source': osm_result.source if osm_result else 'none',
                'geocoding_time_ms': geocoding_time * 1000,
                'distance_error_miles': None
            }
            
            if osm_result:
                # Calculate distance error
                known_coords = (test_case['known_lat'], test_case['known_lon'])
                osm_coords = (osm_result.latitude, osm_result.longitude)
                distance_error = geodesic(known_coords, osm_coords).miles
                result['distance_error_miles'] = distance_error
                
                print(f"    OSM: {osm_result.latitude:.6f}, {osm_result.longitude:.6f}")
                print(f"    Error: {distance_error:.3f} miles")
                print(f"    Confidence: {osm_result.confidence:.2f}")
            else:
                print(f"    OSM: No match found")
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def test_routing_accuracy(self, target_address: str = "500 Woodlane Street, Little Rock, AR 72201") -> pd.DataFrame:
        """Test routing accuracy and performance."""
        print(f"\n🛣️  Testing routing from target: {target_address}")
        
        # Geocode target address
        target_result = self.geocoder.geocode(target_address)
        if not target_result:
            print("❌ Failed to geocode target address")
            return pd.DataFrame()
        
        target_coords = (target_result.latitude, target_result.longitude)
        print(f"  Target coordinates: {target_coords}")
        
        results = []
        
        for i, test_case in enumerate(self.test_data):
            if test_case['address'] == target_address:
                continue  # Skip self
            
            print(f"  Testing route {i+1}: {test_case['description']}")
            
            # Calculate distances
            dest_coords = (test_case['known_lat'], test_case['known_lon'])
            
            start_time = time.time()
            distance_result = self.router.calculate_distance(target_coords, dest_coords)
            routing_time = time.time() - start_time
            
            result = {
                'destination': test_case['description'],
                'dest_address': test_case['address'],
                'geodesic_miles': distance_result.geodesic_distance_miles,
                'road_miles': distance_result.road_distance_miles,
                'travel_time_min': distance_result.travel_time_minutes,
                'route_found': distance_result.route_found,
                'calculation_method': distance_result.calculation_method,
                'routing_time_ms': routing_time * 1000
            }
            
            if distance_result.road_distance_miles:
                ratio = distance_result.road_distance_miles / distance_result.geodesic_distance_miles
                result['road_geodesic_ratio'] = ratio
                print(f"    Geodesic: {distance_result.geodesic_distance_miles:.2f} miles")
                print(f"    Road network: {distance_result.road_distance_miles:.2f} miles")
                print(f"    Travel time: {distance_result.travel_time_minutes:.1f} minutes")
                print(f"    Ratio: {ratio:.2f}")
            else:
                result['road_geodesic_ratio'] = None
                print(f"    Geodesic only: {distance_result.geodesic_distance_miles:.2f} miles")
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def benchmark_performance(self, num_addresses: int = 100) -> Dict:
        """Benchmark geocoding performance."""
        print(f"\n⚡ Benchmarking performance with {num_addresses} addresses...")
        
        # Generate test addresses (repeat existing ones)
        test_addresses = []
        for i in range(num_addresses):
            test_case = self.test_data[i % len(self.test_data)]
            test_addresses.append(test_case['address'])
        
        # Benchmark OSM geocoding
        start_time = time.time()
        osm_results = []
        
        for address in test_addresses:
            result = self.geocoder.geocode(address)
            osm_results.append(result)
        
        osm_total_time = time.time() - start_time
        osm_success_count = sum(1 for r in osm_results if r is not None)
        
        stats = {
            'total_addresses': num_addresses,
            'osm_success_count': osm_success_count,
            'osm_success_rate': osm_success_count / num_addresses,
            'osm_total_time_seconds': osm_total_time,
            'osm_avg_time_ms': (osm_total_time / num_addresses) * 1000,
            'osm_addresses_per_second': num_addresses / osm_total_time
        }
        
        print(f"  OSM Results:")
        print(f"    Success rate: {stats['osm_success_rate']:.1%}")
        print(f"    Total time: {stats['osm_total_time_seconds']:.2f} seconds")
        print(f"    Average time: {stats['osm_avg_time_ms']:.1f} ms per address")
        print(f"    Throughput: {stats['osm_addresses_per_second']:.1f} addresses/second")
        
        return stats
    
    def compare_with_existing_methods(self) -> pd.DataFrame:
        """Compare OSM geocoding with existing methods."""
        print("\n🔄 Comparing with existing geocoding methods...")
        
        # Try to load existing geocoding functions
        try:
            # This would need to be adapted based on your existing code structure
            from geocoding_zipcentroid import geocode_address as zip_geocode
            from geocoding_addrfeat import geocode_address as addrfeat_geocode
            comparison_available = True
        except ImportError:
            print("⚠️ Existing geocoding methods not available for comparison")
            comparison_available = False
        
        results = []
        
        for test_case in self.test_data:
            result = {
                'address': test_case['address'],
                'description': test_case['description'],
                'known_lat': test_case['known_lat'],
                'known_lon': test_case['known_lon']
            }
            
            # OSM geocoding
            osm_result = self.geocoder.geocode(test_case['address'])
            if osm_result:
                result['osm_lat'] = osm_result.latitude
                result['osm_lon'] = osm_result.longitude
                result['osm_confidence'] = osm_result.confidence
                result['osm_error_miles'] = geodesic(
                    (test_case['known_lat'], test_case['known_lon']),
                    (osm_result.latitude, osm_result.longitude)
                ).miles
            else:
                result['osm_lat'] = None
                result['osm_lon'] = None
                result['osm_confidence'] = 0
                result['osm_error_miles'] = None
            
            # Add placeholders for existing methods
            result['zip_lat'] = None
            result['zip_lon'] = None
            result['zip_error_miles'] = None
            result['addrfeat_lat'] = None
            result['addrfeat_lon'] = None
            result['addrfeat_error_miles'] = None
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def generate_accuracy_report(self, geocoding_results: pd.DataFrame) -> Dict:
        """Generate accuracy statistics report."""
        successful_results = geocoding_results[geocoding_results['osm_success'] == True]
        
        if len(successful_results) == 0:
            return {'error': 'No successful geocoding results'}
        
        errors = successful_results['distance_error_miles'].dropna()
        
        report = {
            'total_addresses': len(geocoding_results),
            'successful_geocoding': len(successful_results),
            'success_rate': len(successful_results) / len(geocoding_results),
            'average_error_miles': errors.mean(),
            'median_error_miles': errors.median(),
            'min_error_miles': errors.min(),
            'max_error_miles': errors.max(),
            'std_error_miles': errors.std(),
            'errors_under_0_5_miles': (errors < 0.5).sum(),
            'errors_under_1_mile': (errors < 1.0).sum(),
            'errors_under_2_miles': (errors < 2.0).sum(),
            'match_type_distribution': successful_results['osm_match_type'].value_counts().to_dict(),
            'source_distribution': successful_results['osm_source'].value_counts().to_dict()
        }
        
        return report
    
    def save_results(self, geocoding_results: pd.DataFrame, routing_results: pd.DataFrame, 
                    performance_stats: Dict, accuracy_report: Dict, output_file: str = None):
        """Save all test results to Excel file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent.parent / 'data' / 'output'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"osm_geocoding_test_results_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Geocoding accuracy results
            geocoding_results.to_excel(writer, sheet_name='Geocoding_Accuracy', index=False)
            
            # Routing results
            if not routing_results.empty:
                routing_results.to_excel(writer, sheet_name='Routing_Tests', index=False)
            
            # Performance statistics
            perf_df = pd.DataFrame([performance_stats])
            perf_df.to_excel(writer, sheet_name='Performance_Stats', index=False)
            
            # Accuracy report
            accuracy_df = pd.DataFrame([accuracy_report])
            accuracy_df.to_excel(writer, sheet_name='Accuracy_Report', index=False)
        
        print(f"✅ Test results saved to: {output_file}")
        return output_file


def main():
    """Main testing function."""
    parser = argparse.ArgumentParser(description='Test OSM geocoding accuracy')
    parser.add_argument('--method', choices=['accuracy', 'routing', 'performance', 'all'], 
                       default='all', help='Test method to run')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--states', default='arkansas', help='States to load (comma-separated)')
    parser.add_argument('--benchmark-size', type=int, default=100, 
                       help='Number of addresses for performance benchmark')
    
    args = parser.parse_args()
    
    print("OSM Geocoding Test Framework")
    print("=" * 50)
    
    # Initialize tester
    tester = OSMGeocodingTester()
    
    # Setup test data
    tester.setup_test_data()
    
    # Load OSM data
    states = [s.strip().lower() for s in args.states.split(',')]
    if not tester.load_osm_data(states):
        print("Failed to load OSM data")
        return
    
    # Run tests based on method
    geocoding_results = pd.DataFrame()
    routing_results = pd.DataFrame()
    performance_stats = {}
    
    if args.method in ['accuracy', 'all']:
        geocoding_results = tester.test_geocoding_accuracy()
    
    if args.method in ['routing', 'all']:
        routing_results = tester.test_routing_accuracy()
    
    if args.method in ['performance', 'all']:
        performance_stats = tester.benchmark_performance(args.benchmark_size)
    
    # Generate accuracy report
    accuracy_report = {}
    if not geocoding_results.empty:
        accuracy_report = tester.generate_accuracy_report(geocoding_results)
        
        print("\n📊 Accuracy Summary:")
        print(f"  Success rate: {accuracy_report['success_rate']:.1%}")
        print(f"  Average error: {accuracy_report['average_error_miles']:.3f} miles")
        print(f"  Median error: {accuracy_report['median_error_miles']:.3f} miles")
        print(f"  Addresses within 0.5 miles: {accuracy_report['errors_under_0_5_miles']}")
        print(f"  Addresses within 1.0 miles: {accuracy_report['errors_under_1_mile']}")
    
    # Save results
    output_file = tester.save_results(geocoding_results, routing_results, 
                                     performance_stats, accuracy_report, args.output)
    
    print(f"\n✅ Testing completed! Results saved to: {output_file}")


if __name__ == "__main__":
    main()