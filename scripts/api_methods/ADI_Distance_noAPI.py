import pandas as pd
import googlemaps
from shapely.geometry import Point
import geopandas as gpd
import re
import os
from concurrent.futures import ThreadPoolExecutor
import math

# User input for configuration
GOOGLE_MAPS_API_KEY = input("Enter your Google Maps API Key: ")
TARGET_ADDRESS = input("Enter the target address: ")
# Set the paths to the data files in the same folder as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_EXCEL_FILE_PATH = os.path.join(script_dir, "data.xlsx")
PARENT_FOLDER_SHAPEFILES = os.path.join(script_dir, "toFIPS")
ADI_LOOKUP_CSV_PATH = os.path.join(script_dir, 'US_2021_ADI_Census_Block_Group_v4_0_1.csv')
OUTPUT_EXCEL_FILE_PATH = os.path.join(script_dir, 'Updated_with_distance_ADI.xlsx')

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Load the data Excel file, make sure you have an Address column
data_df = pd.read_excel(DATA_EXCEL_FILE_PATH, engine='openpyxl')

# Function to geocode addresses
def geocode_address(Address):
    try:
        geocode_result = gmaps.geocode(Address)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return Point(location['lng'], location['lat'])
    except Exception as e:
        print(f"Error geocoding {Address}: {e}")
        return None

# Geocode each address with ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as executor:
    data_df['geometry'] = list(executor.map(geocode_address, data_df['Address']))

# Filter out any addresses that couldn't be geocoded
data_df = data_df.dropna(subset=['geometry'])

# Convert DataFrame to GeoDataFrame
gdf_addresses = gpd.GeoDataFrame(data_df, geometry='geometry')

# Load shapefiles and combine them into a single GeoDataFrame
shapefile_folders = [os.path.join(PARENT_FOLDER_SHAPEFILES, folder) for folder in os.listdir(PARENT_FOLDER_SHAPEFILES) if os.path.isdir(os.path.join(PARENT_FOLDER_SHAPEFILES, folder))]
gdf_tracts = pd.concat([
    gpd.read_file(os.path.join(folder, f)) for folder in shapefile_folders for f in os.listdir(folder) if f.endswith('.shp')
], ignore_index=True)

# Ensure the GeoDataFrame has a geometry column
if 'geometry' not in gdf_tracts:
    raise ValueError("The shapefiles do not contain a 'geometry' column.")

# Set the geometry column explicitly
gdf_tracts = gdf_tracts.set_geometry('geometry')

# Ensure CRS match
gdf_addresses.crs = gdf_tracts.crs

# Perform spatial join with the predicate parameter
joined = gpd.sjoin(gdf_addresses, gdf_tracts, how="left", predicate='within')

# Assuming FIPS code is in 'GEOID' column
joined['FIPS'] = joined['GEOID'].astype(str)

# Load the lookup CSV file
lookup_df = pd.read_csv(ADI_LOOKUP_CSV_PATH)

# Ensure FIPS codes in lookup_df are strings and zero-padded to 12 characters
lookup_df['FIPS'] = lookup_df['FIPS'].astype(str).str.zfill(12)

# Convert lookup_df to a dictionary with FIPS as keys and (ADI_NATRANK, ADI_STATERNK) as values
lookup_dict = {row['FIPS']: (row['ADI_NATRANK'], row['ADI_STATERNK']) for index, row in lookup_df.iterrows()}

# Debugging print statements
print("Sample of lookup_dict keys:", list(lookup_dict.keys())[:5])
print("Sample of FIPS codes in joined DataFrame:", joined['FIPS'].head())

# Initialize columns for Distance, ADI_NATRANK, and ADI_STATERNK
joined['ADI_NATRANK'] = pd.NA
joined['ADI_STATERNK'] = pd.NA
joined['Distance'] = pd.NA

# Function to check if an address is a PO Box
def is_po_box(address):
    # Define a regex pattern for a PO Box
    po_box_pattern = r'\b[P|p][.|\s]*[O|o][.|\s]*[B|b][O|o|0][X|x]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[O|o][F|f|0][F|f][I|i][Cc][E|e]\b|\b[P|p][O|o|0][S|s][T|t][.|\s]*[B|b][O|o|0][X|x]\b'
    return re.search(po_box_pattern, address) is not None

# Function to fetch distance
def get_distance(source_address, target_address):
    try:
        # Get distance between source and target addresses
        distance_result = gmaps.distance_matrix(source_address, target_address, mode="driving", units='imperial')['rows'][0]['elements'][0]
        distance = distance_result['distance']['text']
        return distance
    except Exception as e:
        print(f"Error fetching distance for {source_address}: {e}")
        return None

# Iterate over the joined dataframe
for index, row in joined.iterrows():
    # Check if the address is a PO Box
    if is_po_box(row['Address']):
        continue  # Skip this iteration if it's a PO Box
    # Calculate distance if not a PO Box
    distance = get_distance(row['Address'], TARGET_ADDRESS)
    joined.at[index, 'Distance'] = distance
    # Lookup ADI ranks if not a PO Box
    fips_code = row['FIPS'].zfill(12)  # Ensure FIPS is zero-padded to 12 characters
    if fips_code in lookup_dict:
        joined.at[index, 'ADI_NATRANK'] = lookup_dict[fips_code][0]
        joined.at[index, 'ADI_STATERNK'] = lookup_dict[fips_code][1]
    else:
        print(f"FIPS code {fips_code} not found in lookup_dict")

# Combine original columns with the new columns
final_df = pd.concat([data_df, joined[['FIPS', 'ADI_NATRANK', 'ADI_STATERNK', 'Distance']]], axis=1)

# Write the updated DataFrame to a new labeled Excel file
final_df.to_excel(OUTPUT_EXCEL_FILE_PATH, index=False, engine='openpyxl')
