#!/usr/bin/env python3
"""
Method Comparison Framework

Compares OSM geocoding method against existing TIGER/ADDRFEAT methods
using the same test addresses and evaluation criteria.

Features:
- Side-by-side accuracy comparison
- Performance benchmarking
- Coverage analysis
- Detailed reporting

Usage:
    python compare_methods.py [--test-file TEST_FILE] [--target-address TARGET]
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

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))
sys.path.append(str(Path(__file__).parent.parent.parent / 'scripts'))

from osm_geocoder import OSMGeocoder
from osm_routing import OSMRouter
from osm_distance_calculator import OSMDistanceCalculator


class MethodComparator:
    """Compare different geocoding methods systematically."""
    
    def __init__(self):
        # Initialize OSM components
        self.osm_geocoder = OSMGeocoder()
        self.osm_router = OSMRouter()
        
        # Initialize existing method components (if available)
        self.existing_methods_available = self._check_existing_methods()
        
        # Comparison results
        self.comparison_results = []
        
    def _check_existing_methods(self) -> Dict[str, bool]:
        """Check which existing geocoding methods are available."""
        methods = {
            'zip_centroid': False,
            'addrfeat': False,
            'usaddress': False
        }
        
        try:
            # Try importing existing geocoding modules
            sys.path.append(str(Path(__file__).parent.parent.parent / 'scripts'))
            
            # Check for ZIP centroid method
            try:
                from geocoding_zipcentroid import main as zip_main
                methods['zip_centroid'] = True
                print("✅ ZIP centroid method available")
            except ImportError:
                print("⚠️ ZIP centroid method not available")
            
            # Check for ADDRFEAT method
            try:
                from geocoding_addrfeat import main as addrfeat_main
                methods['addrfeat'] = True
                print("✅ ADDRFEAT method available")
            except ImportError:
                print("⚠️ ADDRFEAT method not available")
            
            # Check for usaddress
            try:
                import usaddress
                methods['usaddress'] = True
                print("✅ usaddress library available")
            except ImportError:
                print("⚠️ usaddress library not available")
        
        except Exception as e:
            print(f"Error checking existing methods: {e}")
        
        return methods
    
    def setup(self, states: List[str] = ['arkansas']) -> bool:
        """Setup all geocoding methods."""
        print("🔧 Setting up comparison framework...")
        
        # Load OSM data
        print("📂 Loading OSM data...")
        if not self.osm_geocoder.load_osm_data(states):
            print("❌ Failed to load OSM geocoding data")
            return False
        
        if not self.osm_router.load_road_network(states):
            print("❌ Failed to load OSM routing data")
            return False
        
        print("✅ OSM components loaded successfully")
        return True
    
    def create_test_dataset(self, size: str = 'small') -> List[Dict]:
        """Create test dataset with various address types."""
        if size == 'small':
            test_addresses = [
                {
                    'address': '500 Woodlane Street, Little Rock, AR 72201',
                    'type': 'urban_street',
                    'expected_accuracy': 'high',
                    'description': 'Downtown Little Rock street address'
                },
                {
                    'address': '1 University Avenue, Fayetteville, AR 72701',
                    'type': 'institutional',
                    'expected_accuracy': 'high',
                    'description': 'University campus'
                },
                {
                    'address': '1000 Main Street, Conway, AR 72032',
                    'type': 'urban_street',
                    'expected_accuracy': 'medium',
                    'description': 'Mid-size city street'
                },
                {
                    'address': '300 Spring Street, Hot Springs, AR 71901',
                    'type': 'urban_street',
                    'expected_accuracy': 'medium',
                    'description': 'Tourist city downtown'
                },
                {
                    'address': '72701',  # ZIP only
                    'type': 'zip_only',
                    'expected_accuracy': 'low',
                    'description': 'ZIP code only'
                },
                {
                    'address': 'Walmart, Bentonville, AR',
                    'type': 'business_name',
                    'expected_accuracy': 'medium',
                    'description': 'Business name with city'
                },
                {
                    'address': 'Rural Route 1, Pocahontas, AR 72455',
                    'type': 'rural',
                    'expected_accuracy': 'low',
                    'description': 'Rural address'
                }
            ]
        elif size == 'medium':
            # Add more test cases
            test_addresses = self.create_test_dataset('small')
            test_addresses.extend([
                {
                    'address': '2801 S University Ave, Little Rock, AR 72204',
                    'type': 'urban_street',
                    'expected_accuracy': 'high',
                    'description': 'UALR campus address'
                },
                {
                    'address': '123 Market Street, Fort Smith, AR 72901',
                    'type': 'urban_street', 
                    'expected_accuracy': 'medium',
                    'description': 'Fort Smith downtown'
                },
                {
                    'address': '456 Oak Street, Jonesboro, AR 72401',
                    'type': 'urban_street',
                    'expected_accuracy': 'medium',
                    'description': 'Jonesboro street address'
                }
            ])
        
        return test_addresses
    
    def geocode_with_osm(self, address: str) -> Dict:
        """Geocode address using OSM method."""
        start_time = time.time()
        
        try:
            result = self.osm_geocoder.geocode(address)
            elapsed_time = time.time() - start_time
            
            if result:
                return {
                    'success': True,
                    'latitude': result.latitude,
                    'longitude': result.longitude,
                    'confidence': result.confidence,
                    'match_type': result.match_type,
                    'source': result.source,
                    'time_ms': elapsed_time * 1000,
                    'method': 'osm'
                }
            else:
                return {
                    'success': False,
                    'latitude': None,
                    'longitude': None,
                    'confidence': 0,
                    'match_type': 'failed',
                    'source': 'none',
                    'time_ms': elapsed_time * 1000,
                    'method': 'osm'
                }
        except Exception as e:
            return {
                'success': False,
                'latitude': None,
                'longitude': None,
                'confidence': 0,
                'match_type': 'error',
                'source': 'none',
                'time_ms': (time.time() - start_time) * 1000,
                'method': 'osm',
                'error': str(e)
            }
    
    def geocode_with_zip_centroid(self, address: str) -> Dict:
        """Geocode address using ZIP centroid method (simulated)."""
        start_time = time.time()
        
        try:
            # This would need to be implemented based on your existing ZIP centroid code
            # For now, return a placeholder
            elapsed_time = time.time() - start_time
            
            return {
                'success': False,
                'latitude': None,
                'longitude': None,
                'confidence': 0,
                'match_type': 'not_implemented',
                'source': 'zip_centroid',
                'time_ms': elapsed_time * 1000,
                'method': 'zip_centroid'
            }
        except Exception as e:
            return {
                'success': False,
                'latitude': None,
                'longitude': None,
                'confidence': 0,
                'match_type': 'error',
                'source': 'zip_centroid',
                'time_ms': (time.time() - start_time) * 1000,
                'method': 'zip_centroid',
                'error': str(e)
            }
    
    def geocode_with_addrfeat(self, address: str) -> Dict:
        """Geocode address using ADDRFEAT method (simulated)."""
        start_time = time.time()
        
        try:
            # This would need to be implemented based on your existing ADDRFEAT code
            # For now, return a placeholder
            elapsed_time = time.time() - start_time
            
            return {
                'success': False,
                'latitude': None,
                'longitude': None,
                'confidence': 0,
                'match_type': 'not_implemented',
                'source': 'addrfeat',
                'time_ms': elapsed_time * 1000,
                'method': 'addrfeat'
            }
        except Exception as e:
            return {
                'success': False,
                'latitude': None,
                'longitude': None,
                'confidence': 0,
                'match_type': 'error',
                'source': 'addrfeat',
                'time_ms': (time.time() - start_time) * 1000,
                'method': 'addrfeat',
                'error': str(e)
            }
    
    def compare_methods(self, test_addresses: List[Dict]) -> pd.DataFrame:
        """Compare all available methods on test addresses."""
        print(f"🔄 Comparing methods on {len(test_addresses)} test addresses...")
        
        results = []
        
        for i, test_case in enumerate(test_addresses):
            print(f"  Testing {i+1}/{len(test_addresses)}: {test_case['description']}")
            
            address = test_case['address']
            
            # Test OSM method
            osm_result = self.geocode_with_osm(address)
            
            # Test ZIP centroid method
            zip_result = self.geocode_with_zip_centroid(address)
            
            # Test ADDRFEAT method
            addrfeat_result = self.geocode_with_addrfeat(address)
            
            # Compile results
            result = {
                'address': address,
                'type': test_case['type'],
                'expected_accuracy': test_case['expected_accuracy'],
                'description': test_case['description'],
                
                # OSM results
                'osm_success': osm_result['success'],
                'osm_lat': osm_result['latitude'],
                'osm_lon': osm_result['longitude'],
                'osm_confidence': osm_result['confidence'],
                'osm_match_type': osm_result['match_type'],
                'osm_time_ms': osm_result['time_ms'],
                
                # ZIP centroid results
                'zip_success': zip_result['success'],
                'zip_lat': zip_result['latitude'],
                'zip_lon': zip_result['longitude'],
                'zip_confidence': zip_result['confidence'],
                'zip_match_type': zip_result['match_type'],
                'zip_time_ms': zip_result['time_ms'],
                
                # ADDRFEAT results
                'addrfeat_success': addrfeat_result['success'],
                'addrfeat_lat': addrfeat_result['latitude'],
                'addrfeat_lon': addrfeat_result['longitude'],
                'addrfeat_confidence': addrfeat_result['confidence'],
                'addrfeat_match_type': addrfeat_result['match_type'],
                'addrfeat_time_ms': addrfeat_result['time_ms']
            }
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def analyze_coverage(self, results_df: pd.DataFrame) -> Dict:
        """Analyze coverage statistics for each method."""
        total_addresses = len(results_df)
        
        analysis = {
            'total_addresses': total_addresses,
            'osm': {
                'success_count': results_df['osm_success'].sum(),
                'success_rate': results_df['osm_success'].mean(),
                'avg_confidence': results_df[results_df['osm_success']]['osm_confidence'].mean(),
                'avg_time_ms': results_df['osm_time_ms'].mean(),
                'match_types': results_df[results_df['osm_success']]['osm_match_type'].value_counts().to_dict()
            },
            'zip_centroid': {
                'success_count': results_df['zip_success'].sum(),
                'success_rate': results_df['zip_success'].mean(),
                'avg_confidence': results_df[results_df['zip_success']]['zip_confidence'].mean() if results_df['zip_success'].any() else 0,
                'avg_time_ms': results_df['zip_time_ms'].mean(),
                'match_types': results_df[results_df['zip_success']]['zip_match_type'].value_counts().to_dict()
            },
            'addrfeat': {
                'success_count': results_df['addrfeat_success'].sum(),
                'success_rate': results_df['addrfeat_success'].mean(),
                'avg_confidence': results_df[results_df['addrfeat_success']]['addrfeat_confidence'].mean() if results_df['addrfeat_success'].any() else 0,
                'avg_time_ms': results_df['addrfeat_time_ms'].mean(),
                'match_types': results_df[results_df['addrfeat_success']]['addrfeat_match_type'].value_counts().to_dict()
            }
        }
        
        return analysis
    
    def analyze_by_address_type(self, results_df: pd.DataFrame) -> Dict:
        """Analyze performance by address type."""
        type_analysis = {}
        
        for addr_type in results_df['type'].unique():
            type_data = results_df[results_df['type'] == addr_type]
            
            type_analysis[addr_type] = {
                'count': len(type_data),
                'osm_success_rate': type_data['osm_success'].mean(),
                'zip_success_rate': type_data['zip_success'].mean(),
                'addrfeat_success_rate': type_data['addrfeat_success'].mean(),
                'osm_avg_confidence': type_data[type_data['osm_success']]['osm_confidence'].mean() if type_data['osm_success'].any() else 0
            }
        
        return type_analysis
    
    def generate_comparison_report(self, results_df: pd.DataFrame, coverage_analysis: Dict, 
                                 type_analysis: Dict) -> Dict:
        """Generate comprehensive comparison report."""
        report = {
            'summary': {
                'total_addresses_tested': len(results_df),
                'test_date': datetime.now().isoformat(),
                'methods_compared': ['osm', 'zip_centroid', 'addrfeat']
            },
            'overall_performance': coverage_analysis,
            'performance_by_type': type_analysis,
            'recommendations': self._generate_recommendations(coverage_analysis, type_analysis)
        }
        
        return report
    
    def _generate_recommendations(self, coverage_analysis: Dict, type_analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Compare success rates
        osm_rate = coverage_analysis['osm']['success_rate']
        zip_rate = coverage_analysis['zip_centroid']['success_rate']
        addrfeat_rate = coverage_analysis['addrfeat']['success_rate']
        
        if osm_rate >= max(zip_rate, addrfeat_rate):
            recommendations.append("OSM method shows highest overall success rate")
        
        # Performance recommendations
        osm_time = coverage_analysis['osm']['avg_time_ms']
        zip_time = coverage_analysis['zip_centroid']['avg_time_ms']
        addrfeat_time = coverage_analysis['addrfeat']['avg_time_ms']
        
        if osm_time <= min(zip_time, addrfeat_time):
            recommendations.append("OSM method is fastest for geocoding")
        
        # Coverage recommendations
        for addr_type, stats in type_analysis.items():
            if stats['osm_success_rate'] > 0.8:
                recommendations.append(f"OSM method performs well for {addr_type} addresses")
        
        return recommendations
    
    def save_comparison_results(self, results_df: pd.DataFrame, analysis: Dict, 
                              report: Dict, output_file: str = None):
        """Save comparison results to Excel file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent.parent / 'data' / 'output'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"method_comparison_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main comparison results
            results_df.to_excel(writer, sheet_name='Comparison_Results', index=False)
            
            # Coverage analysis
            coverage_df = pd.DataFrame(analysis['overall_performance']).T
            coverage_df.to_excel(writer, sheet_name='Coverage_Analysis')
            
            # Type analysis
            type_df = pd.DataFrame(analysis['performance_by_type']).T
            type_df.to_excel(writer, sheet_name='Type_Analysis')
            
            # Recommendations
            rec_df = pd.DataFrame(report['recommendations'], columns=['Recommendation'])
            rec_df.to_excel(writer, sheet_name='Recommendations', index=False)
        
        print(f"✅ Comparison results saved to: {output_file}")
        return output_file


def main():
    """Main comparison function."""
    parser = argparse.ArgumentParser(description='Compare geocoding methods')
    parser.add_argument('--test-size', choices=['small', 'medium'], default='small',
                       help='Size of test dataset')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--states', default='arkansas', help='States to load')
    
    args = parser.parse_args()
    
    print("Method Comparison Framework")
    print("=" * 50)
    
    # Initialize comparator
    comparator = MethodComparator()
    
    # Setup
    states = [s.strip().lower() for s in args.states.split(',')]
    if not comparator.setup(states):
        print("Setup failed")
        return
    
    # Create test dataset
    test_addresses = comparator.create_test_dataset(args.test_size)
    print(f"📋 Created test dataset with {len(test_addresses)} addresses")
    
    # Run comparison
    results_df = comparator.compare_methods(test_addresses)
    
    # Analyze results
    coverage_analysis = comparator.analyze_coverage(results_df)
    type_analysis = comparator.analyze_by_address_type(results_df)
    
    # Generate report
    report = comparator.generate_comparison_report(results_df, coverage_analysis, type_analysis)
    
    # Print summary
    print("\n📊 Comparison Summary:")
    print(f"OSM Success Rate: {coverage_analysis['osm']['success_rate']:.1%}")
    print(f"ZIP Success Rate: {coverage_analysis['zip_centroid']['success_rate']:.1%}")
    print(f"ADDRFEAT Success Rate: {coverage_analysis['addrfeat']['success_rate']:.1%}")
    
    print(f"\nAverage Processing Time:")
    print(f"OSM: {coverage_analysis['osm']['avg_time_ms']:.1f} ms")
    print(f"ZIP: {coverage_analysis['zip_centroid']['avg_time_ms']:.1f} ms")
    print(f"ADDRFEAT: {coverage_analysis['addrfeat']['avg_time_ms']:.1f} ms")
    
    # Save results
    output_file = comparator.save_comparison_results(results_df, coverage_analysis, report, args.output)
    
    print(f"\n✅ Method comparison completed!")
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()