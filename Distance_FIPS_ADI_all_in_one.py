import pandas as pd
import googlemaps as gm
import re
from shapely.geometry import Point
import geopandas as gpd
import os

# Insert google maps API key here
gmaps = gm.Client(key='API key')

# Specify the target address
target_address = 'Target Address'

# Load the data CSV file, may need to update the path/name. Make sure you have an Address column
data_df = pd.read_excel('data file with Address.xlsx', dtype={'FIPS': str}, engine='openpyxl')

# Initialize Google Maps client
gmaps = gm.Client(key='API key')

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

# Geocode each address
data_df['geometry'] = data_df['Address'].apply(geocode_address)

# Filter out any addresses that couldn't be geocoded
data_df = data_df.dropna(subset=['geometry'])

# Convert DataFrame to GeoDataFrame
gdf_addresses = gpd.GeoDataFrame(data_df, geometry='geometry')

# Load shapefiles and combine them into a single GeoDataFrame, put full path to folders separated by commas
shapefile_folders = ['path to first state folder', 'path to second state folder', 'path to third state folder']
gdf_tracts = pd.concat([
    gpd.read_file(os.path.join(folder, f)) for folder in shapefile_folders for f in os.listdir(folder) if f.endswith('.shp')
], ignore_index=True)

# Ensure CRS match
gdf_addresses.crs = gdf_tracts.crs

# Perform spatial join
joined = gpd.sjoin(gdf_addresses, gdf_tracts, how="left", op='within')

# Assuming FIPS code is in 'GEOID' column
joined['FIPS'] = joined['GEOID'].astype(str)

# Save intermediate result to CSV
joined[['Address', 'FIPS']].to_excel('addresses_with_fips.xlsx', index=False, engine='openpyxl')

# Load the lookup CSV file, may need to update the path
lookup_df = pd.read_csv('./US_2021_ADI_Census_Block_Group_v4_0_1.csv')

# Convert lookup_df to a dictionary with FIPS as keys and (ADI_NATRANK, ADI_STATERNK) as values
lookup_dict = {row['FIPS']: (row['ADI_NATRANK'], row['ADI_STATERNK']) for index, row in lookup_df.iterrows()}

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

# Iterate over the data_df
for index, row in joined.iterrows():
    # Check if the address is a PO Box
    if is_po_box(row['Address']):
        continue  # Skip this iteration if it's a PO Box
    # Calculate distance if not a PO Box
    distance = get_distance(row['Address'], target_address)
    joined.at[index, 'Distance'] = distance
    # Lookup ADI ranks if not a PO Box
    fips_code = row['FIPS']
    if fips_code in lookup_dict:
        joined.at[index, 'ADI_NATRANK'] = lookup_dict[fips_code][0]
        joined.at[index, 'ADI_STATERNK'] = lookup_dict[fips_code][1]

joined = joined.astype(str)

# Write the updated DataFrame to a new CSV file
joined.to_excel('Updated_with_distance_ADI.xlsx', index=False, engine='openpyxl')
