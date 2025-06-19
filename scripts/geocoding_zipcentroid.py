#!/usr/bin/env python3
"""
=============================================================================
GEOCODING METHOD: ZIP CODE CENTROID LOOKUP
=============================================================================

PURPOSE:
    Calculate distances between addresses and determine Area Deprivation Index 
    (ADI) rankings using ZIP code centroid-based geocoding.

METHODOLOGY:
    1. Parse addresses to extract ZIP codes using usaddress library
    2. Look up ZIP code centroids from Census Bureau data
    3. Use centroid coordinates for distance calculations
    4. Perform spatial join with census block groups to get FIPS codes
    5. Look up ADI rankings from census block group FIPS codes

ACCURACY LEVEL:
    • Good (0.5-2 mile precision from actual location)
    • Sufficient for ADI analysis at census block group level
    • ZIP centroids represent geographic center of ZIP code area

ADVANTAGES:
    ✅ Works completely offline (no external API calls)
    ✅ Fast processing (no rate limits or network delays)
    ✅ Covers all US ZIP codes
    ✅ Privacy-safe (no data transmitted externally)
    ✅ Consistent, reproducible results

DISADVANTAGES:
    ❌ Lower precision than street-level geocoding
    ❌ May be less accurate for large rural ZIP codes

WHEN TO USE:
    • Research projects requiring privacy and offline capability
    • Large batch processing (100+ addresses)
    • When 0.5-2 mile accuracy is acceptable
    • Geographic analysis at census block group level

DATA REQUIREMENTS:
    • Input: Excel file with 'Address' column
    • Reference: 2023_Gaz_zcta_national.txt (ZIP centroids)
    • Reference: US_2021_ADI_Census_Block_Group_v4_0_1.csv (ADI data)
    • Shapefiles: cb_2020_us_bg_500k.shp (census block groups)

EXAMPLE USAGE:
    cd scripts/
    python geocoding_zipcentroid.py
    # Enter target address when prompted

OUTPUT:
    results_zipcentroid_YYYYMMDD.xlsx containing:
    - Original address data
    - Geocoded coordinates (longitude/latitude)
    - FIPS codes (census block group)
    - ADI rankings (national and state)
    - Distance to target address (miles)

=============================================================================
"""

import pandas as pd
import geopandas as gpd
from geopy.distance import geodesic
import usaddress
import re
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# User input for configuration
TARGET_ADDRESS = input("Enter the target address: ")

# Set paths to data files
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
DATA_EXCEL_FILE_PATH = os.path.join(project_root, "data", "input", "data.xlsx")
ADI_LOOKUP_CSV_PATH = os.path.join(project_root, "data", "reference", 'US_2021_ADI_Census_Block_Group_v4_0_1.csv')
SHAPEFILE_PATH = os.path.join(project_root, "shapefiles", "cb_2020_us_bg_500k.shp")

# Generate output filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d")
OUTPUT_EXCEL_FILE_PATH = os.path.join(project_root, "data", "output", f'results_zipcentroid_{timestamp}.xlsx')

# Load ZIP code centroid data for local geocoding
ZIP_CENTROIDS_PATH = os.path.join(project_root, "data", "reference", '2023_Gaz_zcta_national.txt')
zip_centroids_df = pd.read_csv(ZIP_CENTROIDS_PATH, sep='\t', dtype={'GEOID': str})
zip_centroids_df.columns = zip_centroids_df.columns.str.strip()  # Clean column names
zip_centroids_dict = {row['GEOID']: (row['INTPTLONG'], row['INTPTLAT']) for _, row in zip_centroids_df.iterrows()}

# Load census block group shapefile for FIPS lookup
print("Loading census block group data...")
shapefile_gdf = gpd.read_file(SHAPEFILE_PATH)

# Load the data Excel file
data_df = pd.read_excel(DATA_EXCEL_FILE_PATH, engine='openpyxl')

# Function to geocode addresses using local ZIP centroid data
def geocode_address(address):
    if pd.isna(address):
        return None, None
    try:
        # Parse the address to extract ZIP code
        parsed = usaddress.tag(address)
        address_dict = parsed[0]
        
        # Look for ZIP code in parsed address
        zip_code = address_dict.get('ZipCode')
        if zip_code and zip_code in zip_centroids_dict:
            lng, lat = zip_centroids_dict[zip_code]
            return lng, lat
        else:
            print(f"ZIP code not found or not available for address: {address}")
            return None, None
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None, None

# Function to check if an address is a PO Box
def is_po_box(address):
    if not isinstance(address, str):
        return False
    po_box_pattern = r'\b[P|p][.\s]*[O|o][.\s]*[B|b][O|o|0][X|x]\b'
    return re.search(po_box_pattern, address) is not None

# Function to get FIPS code using shapefile lookup
def get_fips_from_shapefile(lng, lat):
    if lng is None or lat is None:
        return None
    point = gpd.GeoDataFrame(geometry=[gpd.points_from_xy([lng], [lat])[0]], crs=shapefile_gdf.crs)
    match = gpd.sjoin(point, shapefile_gdf, how='left', predicate='intersects')
    return match.iloc[0]['GEOID'] if not match.empty else None

# Function to calculate distance between two addresses
def get_distance(source_address, target_address):
    try:
        source_lng, source_lat = geocode_address(source_address)
        target_lng, target_lat = geocode_address(target_address)
        if source_lng and source_lat and target_lng and target_lat:
            return geodesic((source_lat, source_lng), (target_lat, target_lng)).miles
    except Exception as e:
        print(f"Error fetching distance for {source_address}: {e}")
    return None

# Geocode addresses with threading
print("Geocoding addresses using ZIP code centroids...")
with ThreadPoolExecutor(max_workers=10) as executor:
    geocode_results = list(executor.map(geocode_address, data_df['Address']))
    data_df['Longitude'], data_df['Latitude'] = zip(*geocode_results)

# Find FIPS codes using shapefile
print("Looking up FIPS codes from coordinates...")
with ThreadPoolExecutor(max_workers=10) as executor:
    fips_codes = list(executor.map(lambda coords: get_fips_from_shapefile(*coords), zip(data_df['Longitude'], data_df['Latitude'])))
    data_df['FIPS'] = fips_codes

# Load lookup CSV file
lookup_df = pd.read_csv(ADI_LOOKUP_CSV_PATH)
lookup_df['FIPS'] = lookup_df['FIPS'].astype(str).str.zfill(12)
lookup_dict = {row['FIPS']: (row['ADI_NATRANK'], row['ADI_STATERNK']) for index, row in lookup_df.iterrows()}

data_df['ADI_NATRANK'] = pd.NA
data_df['ADI_STATERNK'] = pd.NA
data_df['Distance'] = pd.NA

# Iterate over DataFrame
print("Calculating distances and looking up ADI rankings...")
for index, row in data_df.iterrows():
    if is_po_box(row['Address']):
        data_df.at[index, 'ADI_NATRANK'] = pd.NA
        data_df.at[index, 'ADI_STATERNK'] = pd.NA
        data_df.at[index, 'Distance'] = pd.NA
        continue
    distance = get_distance(row['Address'], TARGET_ADDRESS)
    data_df.at[index, 'Distance'] = distance
    fips_code = row['FIPS']
    if fips_code in lookup_dict:
        data_df.at[index, 'ADI_NATRANK'] = lookup_dict[fips_code][0]
        data_df.at[index, 'ADI_STATERNK'] = lookup_dict[fips_code][1]
    else:
        data_df.at[index, 'ADI_NATRANK'] = pd.NA
        data_df.at[index, 'ADI_STATERNK'] = pd.NA

# Write updated DataFrame to Excel
data_df.to_excel(OUTPUT_EXCEL_FILE_PATH, index=False, engine='openpyxl')

# Print summary
successful_geocodes = data_df['Longitude'].notna().sum()
successful_fips = data_df['FIPS'].notna().sum()
successful_adi = data_df['ADI_NATRANK'].notna().sum()

print(f"\n" + "="*80)
print(f"ZIP CODE CENTROID GEOCODING COMPLETE")
print(f"="*80)
print(f"Total addresses processed: {len(data_df)}")
print(f"Successfully geocoded: {successful_geocodes}")
print(f"Successfully matched to FIPS: {successful_fips}")
print(f"Successfully matched to ADI: {successful_adi}")
print(f"Success rate: {(successful_geocodes/len(data_df)*100):.1f}%")
print(f"\nResults saved to: {OUTPUT_EXCEL_FILE_PATH}")
print(f"Method: ZIP Code Centroid (0.5-2 mile accuracy)")