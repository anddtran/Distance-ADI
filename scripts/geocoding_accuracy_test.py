#!/usr/bin/env python3
"""
=============================================================================
GEOCODING ACCURACY VALIDATION TOOL
=============================================================================

PURPOSE:
    Test and validate the accuracy of local geocoding methods by comparing
    results against known approximate coordinates.

METHODOLOGY:
    1. Use sample addresses with manually verified approximate coordinates
    2. Test ZIP centroid geocoding method
    3. Calculate accuracy metrics (distance differences)
    4. Generate accuracy validation report

ACCURACY METRICS:
    • Distance differences between geocoded and known coordinates
    • Success rates for different address types
    • Validation of geocoding precision claims

WHEN TO USE:
    • Validate geocoding accuracy before production use
    • Test geocoding performance on new datasets
    • Compare different geocoding methods
    • Quality assurance for research projects

SAMPLE DATA:
    Uses pre-defined test addresses with known approximate coordinates
    for Little Rock, Arkansas area landmarks and addresses.

EXAMPLE USAGE:
    cd scripts/
    python geocoding_accuracy_test.py

OUTPUT:
    accuracy_validation_YYYYMMDD.xlsx containing:
    - Test addresses
    - Known approximate coordinates
    - Geocoded coordinates (from each method tested)
    - Distance differences in miles
    - Accuracy statistics

=============================================================================
"""

import pandas as pd
import usaddress
import os
from geopy.distance import geodesic
from datetime import datetime

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
ZIP_CENTROIDS_PATH = os.path.join(project_root, "data", "reference", '2023_Gaz_zcta_national.txt')

# Generate output filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d")
output_file = os.path.join(project_root, "data", "output", f'accuracy_validation_{timestamp}.xlsx')

# Load ZIP code centroid data for local geocoding
zip_centroids_df = pd.read_csv(ZIP_CENTROIDS_PATH, sep='\t', dtype={'GEOID': str})
zip_centroids_df.columns = zip_centroids_df.columns.str.strip()
zip_centroids_dict = {row['GEOID']: (row['INTPTLONG'], row['INTPTLAT']) for _, row in zip_centroids_df.iterrows()}

def geocode_local(address):
    """Geocode using local ZIP centroid data"""
    try:
        parsed = usaddress.tag(address)
        address_dict = parsed[0]
        zip_code = address_dict.get('ZipCode')
        if zip_code and zip_code in zip_centroids_dict:
            lng, lat = zip_centroids_dict[zip_code]
            return lng, lat
        else:
            return None, None
    except Exception as e:
        return None, None

# Sample addresses with manually verified approximate coordinates
sample_data = [
    {
        'Address': '1 State Capitol Plaza Little Rock AR 72201',
        'Known_Approx_Lng': -92.2809,
        'Known_Approx_Lat': 34.7465,
        'Description': 'Arkansas State Capitol Building'
    },
    {
        'Address': '500 President Clinton Ave Little Rock AR 72201', 
        'Known_Approx_Lng': -92.2737,
        'Known_Approx_Lat': 34.7448,
        'Description': 'Clinton Presidential Library'
    },
    {
        'Address': '1200 S Main St Little Rock AR 72202',
        'Known_Approx_Lng': -92.2721,
        'Known_Approx_Lat': 34.7302,
        'Description': 'South Main Street location'
    },
    {
        'Address': '4301 W Markham St Little Rock AR 72205',
        'Known_Approx_Lng': -92.3501,
        'Known_Approx_Lat': 34.7517,
        'Description': 'West Little Rock area'
    },
    {
        'Address': '2801 S University Ave Little Rock AR 72204',
        'Known_Approx_Lng': -92.3312,
        'Known_Approx_Lat': 34.7089,
        'Description': 'University Avenue corridor'
    }
]

# Create DataFrame
comparison_df = pd.DataFrame(sample_data)

# Get local geocoding results
print("Testing ZIP centroid geocoding accuracy...")
local_results = [geocode_local(addr) for addr in comparison_df['Address']]
comparison_df['Local_Longitude'], comparison_df['Local_Latitude'] = zip(*local_results)

# Calculate distance between known coordinates and local geocoding
def calculate_distance_difference(row):
    if (pd.notna(row['Local_Longitude']) and pd.notna(row['Local_Latitude'])):
        known_coords = (row['Known_Approx_Lat'], row['Known_Approx_Lng'])
        local_coords = (row['Local_Latitude'], row['Local_Longitude'])
        return geodesic(known_coords, local_coords).miles
    return None

comparison_df['Distance_Difference_Miles'] = comparison_df.apply(calculate_distance_difference, axis=1)

# Display results
print("\\n" + "="*100)
print("GEOCODING ACCURACY VALIDATION RESULTS")
print("="*100)

for _, row in comparison_df.iterrows():
    addr_short = row['Address'][:47] + "..." if len(row['Address']) > 50 else row['Address']
    local_coords = f"({row['Local_Latitude']:.4f}, {row['Local_Longitude']:.4f})" if pd.notna(row['Local_Latitude']) else "Failed"
    known_coords = f"({row['Known_Approx_Lat']:.4f}, {row['Known_Approx_Lng']:.4f})"
    diff = f"{row['Distance_Difference_Miles']:.2f}" if pd.notna(row['Distance_Difference_Miles']) else "N/A"
    
    print(f"{addr_short}: {local_coords} vs {known_coords} = {diff} miles")

print("\\n" + "="*100)
print("ACCURACY STATISTICS")
print("="*100)

if comparison_df['Distance_Difference_Miles'].notna().sum() > 0:
    mean_diff = comparison_df['Distance_Difference_Miles'].mean()
    median_diff = comparison_df['Distance_Difference_Miles'].median()
    max_diff = comparison_df['Distance_Difference_Miles'].max()
    min_diff = comparison_df['Distance_Difference_Miles'].min()
    success_rate = (comparison_df['Local_Longitude'].notna().sum() / len(comparison_df)) * 100
    
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average difference: {mean_diff:.2f} miles")
    print(f"Median difference:  {median_diff:.2f} miles") 
    print(f"Maximum difference: {max_diff:.2f} miles")
    print(f"Minimum difference: {min_diff:.2f} miles")

# Save detailed comparison
comparison_df.to_excel(output_file, index=False, engine='openpyxl')
print(f"\\nDetailed validation report saved to: {output_file}")
print("VALIDATION COMPLETE")