import pandas as pd
import googlemaps
import re
import requests
import math
from concurrent.futures import ThreadPoolExecutor
import os
import time

# User input for configuration
GOOGLE_MAPS_API_KEY = input("Enter your Google Maps API Key: ")
TARGET_ADDRESS = input("Enter the target address: ")

# Set the paths to the data, ADI lookup CSV, and the output Excel file in the same folder as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_EXCEL_FILE_PATH = os.path.join(script_dir, "data.xlsx")
ADI_LOOKUP_CSV_PATH = os.path.join(script_dir, 'US_2021_ADI_Census_Block_Group_v4_0_1.csv')
OUTPUT_EXCEL_FILE_PATH = os.path.join(script_dir, 'Updated_with_distance_ADI.xlsx')

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Load the data Excel file, make sure you have an Address column
data_df = pd.read_excel(DATA_EXCEL_FILE_PATH, engine='openpyxl')

# Function to geocode addresses
def geocode_address(address):
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lng'], location['lat']
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
    return None, None

# Function to convert latitude and longitude to Web Mercator projection
def lat_lng_to_web_mercator(lng, lat):
    web_mercator_lng = lng * 20037508.34 / 180.0
    web_mercator_lat = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    web_mercator_lat = web_mercator_lat * 20037508.34 / 180.0
    return web_mercator_lng, web_mercator_lat

# Function to query TIGERweb API for FIPS code with retry logic
def query_tigerweb_api(lng, lat, retries=3, backoff_factor=0.3):
    web_mercator_lng, web_mercator_lat = lat_lng_to_web_mercator(lng, lat)
    url = (
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/5/query"
        f"?geometry={web_mercator_lng},{web_mercator_lat}"
        "&geometryType=esriGeometryPoint"
        "&spatialRel=esriSpatialRelIntersects"
        "&outFields=GEOID"
        "&returnGeometry=false"
        "&f=json"
        "&inSR=3857"
        "&outSR=3857"
    )
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                return data['features'][0]['attributes']['GEOID']
        except requests.exceptions.RequestException as e:
            print(f"Error querying TIGERweb API: {e}")
            time.sleep(backoff_factor * (2 ** attempt))  # Exponential backoff
    return None

# Function to check if an address is a PO Box
def is_po_box(address):
    po_box_pattern = r'\b[P|p][.|\s]*[O|o][.|\s]*[B|b][O|o|0][X|x]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[O|o][F|f|0][F|f][I|i][Cc][E|e]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[B|b][O|o|0][X|x]\b'
    return re.search(po_box_pattern, address) is not None

# Function to fetch distance
def get_distance(source_address, target_address):
    try:
        distance_result = gmaps.distance_matrix(source_address, target_address, mode="driving", units='imperial')['rows'][0]['elements'][0]
        distance = distance_result['distance']['text']
        return distance
    except Exception as e:
        print(f"Error fetching distance for {source_address}: {e}")
        return None

# Geocode each address with ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as executor:
    geocode_results = list(executor.map(geocode_address, data_df['Address']))
    data_df['Longitude'], data_df['Latitude'] = zip(*[(lng, lat) if lng is not None and lat is not None else (None, None) for lng, lat in geocode_results])

# Filter out any addresses that couldn't be geocoded
data_df = data_df.dropna(subset=['Longitude', 'Latitude'])

# Query TIGERweb API for each geocoded address with ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as executor:
    fips_codes = list(executor.map(lambda coords: query_tigerweb_api(*coords), zip(data_df['Longitude'], data_df['Latitude'])))
    data_df['FIPS'] = fips_codes

# Load the lookup CSV file
lookup_df = pd.read_csv(ADI_LOOKUP_CSV_PATH)
lookup_df['FIPS'] = lookup_df['FIPS'].astype(str).str.zfill(12)

# Convert lookup_df to a dictionary with FIPS as keys and (ADI_NATRANK, ADI_STATERNK) as values
lookup_dict = {row['FIPS']: (row['ADI_NATRANK'], row['ADI_STATERNK']) for index, row in lookup_df.iterrows()}

# Initialize columns for ADI_NATRANK, ADI_STATERNK, and Distance
data_df['ADI_NATRANK'] = pd.NA
data_df['ADI_STATERNK'] = pd.NA
data_df['Distance'] = pd.NA

# Iterate over the data_df
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

# Write the updated DataFrame to a new labeled Excel file
data_df.to_excel(OUTPUT_EXCEL_FILE_PATH, index=False, engine='openpyxl')
