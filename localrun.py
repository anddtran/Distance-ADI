import pandas as pd
import geopandas as gpd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import math
import os
from concurrent.futures import ThreadPoolExecutor

# User input for configuration
TARGET_ADDRESS = input("Enter the target address: ")

# Set paths to data files
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_EXCEL_FILE_PATH = os.path.join(script_dir, "data.xlsx")
ADI_LOOKUP_CSV_PATH = os.path.join(script_dir, 'US_2021_ADI_Census_Block_Group_v4_0_1.csv')
SHAPEFILE_PATH = os.path.join(script_dir, "cb_2020_us_bg_500k.shp")  # Local shapefile for FIPS lookup
OUTPUT_EXCEL_FILE_PATH = os.path.join(script_dir, 'Updated_with_distance_ADI.xlsx')

# Initialize geocoder
geolocator = Nominatim(user_agent="geo_locator")

# Load the data Excel file
data_df = pd.read_excel(DATA_EXCEL_FILE_PATH, engine='openpyxl')

# Function to geocode addresses
def geocode_address(address):
    if pd.isna(address):
        return None, None
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.longitude, location.latitude
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
    return None, None

# Function to check if an address is a PO Box
def is_po_box(address):
    if not isinstance(address, str):
        return False
    po_box_pattern = r'\b[P|p][.\s]*[O|o][.\s]*[B|b][O|o|0][X|x]\b'
    return re.search(po_box_pattern, address) is not None

# Load shapefile for FIPS lookup
shapefile_gdf = gpd.read_file(SHAPEFILE_PATH)

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
        source_location = geolocator.geocode(source_address, timeout=10)
        target_location = geolocator.geocode(target_address, timeout=10)
        if source_location and target_location:
            return geodesic((source_location.latitude, source_location.longitude),
                            (target_location.latitude, target_location.longitude)).miles
    except Exception as e:
        print(f"Error fetching distance for {source_address}: {e}")
    return None

# Geocode addresses with threading
with ThreadPoolExecutor(max_workers=10) as executor:
    geocode_results = list(executor.map(geocode_address, data_df['Address']))
    data_df['Longitude'], data_df['Latitude'] = zip(*geocode_results)

# Find FIPS codes using shapefile
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
