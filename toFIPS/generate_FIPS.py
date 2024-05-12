import pandas as pd
import googlemaps
from shapely.geometry import Point
import geopandas as gpd
import os

# Initialize Google Maps client
gmaps = googlemaps.Client(key='API key goes here')

# Geocode addresses function
def geocode_address(Address):
    try:
        geocode_result = gmaps.geocode(Address)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return Point(location['lng'], location['lat'])
    except Exception as e:
        print(f"Error geocoding {Address}: {e}")
        return None

# Load addresses from CSV
df_addresses = pd.read_excel('Path to data file.xlsx',dtype={'FIPS': str}, engine='openpyxl')

# Geocode each address
df_addresses['geometry'] = df_addresses['Address'].apply(geocode_address)

# Filter out any addresses that couldn't be geocoded
df_addresses = df_addresses.dropna(subset=['geometry'])

# Convert DataFrame to GeoDataFrame
gdf_addresses = gpd.GeoDataFrame(df_addresses, geometry='geometry')

# Load shapefiles and combine them into a single GeoDataFrame, put full path to folders separated by commas
shapefile_folders = ['path to first state folder', 'path to second state folder','path to third state folder', ...]
gdf_tracts = pd.concat([
    gpd.read_file(os.path.join(folder, f)) for folder in shapefile_folders for f in os.listdir(folder) if f.endswith('.shp')
], ignore_index=True)

# Ensure CRS match
gdf_addresses.crs = gdf_tracts.crs

# Perform spatial join
joined = gpd.sjoin(gdf_addresses, gdf_tracts, how="left", op='within')

# Assuming FIPS code is in 'GEOID' column
joined['FIPS'] = joined['GEOID'].astype(str)

# Save to new CSV
joined[['Address', 'FIPS']].to_excel('addresses_with_fips.xlsx', index=False, engine='openpyxl')
