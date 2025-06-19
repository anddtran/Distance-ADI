import pandas as pd
from geopy.geocoders import Nominatim
import usaddress
import os
from concurrent.futures import ThreadPoolExecutor

# Set paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
DATA_EXCEL_FILE_PATH = os.path.join(project_root, "data", "input", "data.xlsx")
ZIP_CENTROIDS_PATH = os.path.join(project_root, "data", "reference", '2023_Gaz_zcta_national.txt')
OUTPUT_COMPARISON_FILE = os.path.join(project_root, "data", "output", 'geocoding_comparison.xlsx')

# Initialize Nominatim geocoder
geolocator = Nominatim(user_agent="geo_comparison")

# Load ZIP code centroid data for local geocoding
zip_centroids_df = pd.read_csv(ZIP_CENTROIDS_PATH, sep='\t', dtype={'GEOID': str})
zip_centroids_df.columns = zip_centroids_df.columns.str.strip()  # Clean column names
zip_centroids_dict = {row['GEOID']: (row['INTPTLONG'], row['INTPTLAT']) for _, row in zip_centroids_df.iterrows()}

# Load the data Excel file (limit to first 10 addresses for comparison)
data_df = pd.read_excel(DATA_EXCEL_FILE_PATH, engine='openpyxl').head(10)

# Function to geocode using Nominatim API
def geocode_nominatim(address):
    if pd.isna(address):
        return None, None
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.longitude, location.latitude
    except Exception as e:
        print(f"Error geocoding with Nominatim {address}: {e}")
    return None, None

# Function to geocode using local ZIP centroid data
def geocode_local(address):
    if pd.isna(address):
        return None, None
    try:
        parsed = usaddress.tag(address)
        address_dict = parsed[0]
        zip_code = address_dict.get('ZipCode')
        if zip_code and zip_code in zip_centroids_dict:
            lng, lat = zip_centroids_dict[zip_code]
            return lng, lat
        else:
            print(f"ZIP code {zip_code} not found for address: {address}")
            return None, None
    except Exception as e:
        print(f"Error geocoding locally {address}: {e}")
        return None, None

# Geocode with both methods
print("Geocoding with Nominatim API...")
nominatim_results = []
for i, address in enumerate(data_df['Address']):
    print(f"Processing {i+1}/{len(data_df)}: {address}")
    result = geocode_nominatim(address)
    nominatim_results.append(result)
data_df['Nominatim_Longitude'], data_df['Nominatim_Latitude'] = zip(*nominatim_results)

print("Geocoding with local ZIP centroids...")
local_results = [geocode_local(addr) for addr in data_df['Address']]
data_df['Local_Longitude'], data_df['Local_Latitude'] = zip(*local_results)

# Calculate distance between the two geocoding methods
from geopy.distance import geodesic

def calculate_geocoding_difference(row):
    if (pd.notna(row['Nominatim_Longitude']) and pd.notna(row['Nominatim_Latitude']) and 
        pd.notna(row['Local_Longitude']) and pd.notna(row['Local_Latitude'])):
        nominatim_coords = (row['Nominatim_Latitude'], row['Nominatim_Longitude'])
        local_coords = (row['Local_Latitude'], row['Local_Longitude'])
        return geodesic(nominatim_coords, local_coords).miles
    return None

data_df['Geocoding_Difference_Miles'] = data_df.apply(calculate_geocoding_difference, axis=1)

# Select relevant columns for comparison
comparison_df = data_df[['Address', 
                        'Nominatim_Longitude', 'Nominatim_Latitude',
                        'Local_Longitude', 'Local_Latitude', 
                        'Geocoding_Difference_Miles']].copy()

# Add summary statistics
print("\nGeocoding Comparison Summary:")
print(f"Total addresses: {len(data_df)}")
print(f"Nominatim successful: {data_df['Nominatim_Longitude'].notna().sum()}")
print(f"Local successful: {data_df['Local_Longitude'].notna().sum()}")
print(f"Both successful: {comparison_df['Geocoding_Difference_Miles'].notna().sum()}")

if comparison_df['Geocoding_Difference_Miles'].notna().sum() > 0:
    print(f"\nDistance differences (miles):")
    print(f"Mean: {comparison_df['Geocoding_Difference_Miles'].mean():.3f}")
    print(f"Median: {comparison_df['Geocoding_Difference_Miles'].median():.3f}")
    print(f"Max: {comparison_df['Geocoding_Difference_Miles'].max():.3f}")
    print(f"Min: {comparison_df['Geocoding_Difference_Miles'].min():.3f}")

# Save comparison to Excel
comparison_df.to_excel(OUTPUT_COMPARISON_FILE, index=False, engine='openpyxl')
print(f"\nComparison saved to: {OUTPUT_COMPARISON_FILE}")